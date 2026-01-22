import json
import time
import logging
import uuid
from typing import Dict, Any, List

from app.services.llm_factory import LLMFactory
from app.agents.tool_schema import tools
from app.agents.tools_runtime import (
    tool_search_policy,
    tool_get_parks,
    tool_get_plots,
    tool_find_nearby_pois
)
from app.agents.tool_compressor import compress_tool_result
from app.agents.response_validation import validate_and_fix_response
from app.agents.prompt_engineering import (
    PromptStage,
    create_multi_stage_prompt,
    EnhancedPrompts
)
from app.core.citations import CitationTracker, HalluccinationDetector, SourceDocumentation
from app.core.validation import (
    ResponseValidator,
    ToolResultValidator,
    StateValidator,
    validate_and_log
)
from app.core.observability import (
    RequestLogger,
    get_performance_monitor,
    get_audit_logger,
    create_debug_report
)
from app.core.response_categorizer import get_response_categorizer
from app.core.fact_verification import get_fact_verifier, VerificationLevel
from app.utils.state import normalize_state
from app.core.cache import cache
from app.core import settings

logger = logging.getLogger(__name__)

TOOL_MAP = {
    "search_policy": tool_search_policy,
    "get_parks": tool_get_parks,
    "get_plots": tool_get_plots,
    "find_nearby_pois": tool_find_nearby_pois
}


def run_agent(state: str, user_question: str, conversation_context: str = "", is_voice_mode: bool = False) -> Dict[str, Any]:
    """
    Enhanced agent with multi-stage reasoning, validation, and citation tracking.
    
    Features:
    - Validates state and question
    - Multi-stage reasoning with guardrails
    - Tracks citations and sources
    - Validates responses for hallucinations
    - Comprehensive logging and observability
    
    Args:
        state: State code for context
        user_question: User's question
    
    Returns:
        Enhanced response with metadata
    """
    request_id = str(uuid.uuid4())[:8]
    request_logger = RequestLogger(request_id)
    perf_monitor = get_performance_monitor()
    audit_logger = get_audit_logger()
    
    start_time = time.time()
    
    try:
        # ---- VALIDATION STAGE ----
        request_logger.log_event("validation_start", {"type": "inputs"})
        
        # Validate state
        available_states = list(cache["states"].keys())
        state_validator = StateValidator()
        state_validation = state_validator.validate_state(state, available_states)
        
        if not state_validation.is_valid:
            request_logger.log_event("validation_error", {
                "type": "state",
                "errors": state_validation.errors
            }, level="ERROR")
            return _error_response(
                "Invalid state. Available states: " + ", ".join(available_states),
                request_logger,
                state,
                user_question,
                success=False
            )
        
        normalized_state = normalize_state(state)
        
        # ---- TOOL EXECUTION STAGE ----
        request_logger.log_event("tools_execution_start", {})
        
        retrieved_data = _execute_tools_intelligently(
            normalized_state,
            user_question,
            request_logger,
            perf_monitor
        )
        
        request_logger.log_event("tools_execution_complete", {
            "policies_retrieved": len(retrieved_data.get("policies", [])),
            "parks_retrieved": len(retrieved_data.get("parks", [])),
            "plots_retrieved": len(retrieved_data.get("plots", [])),
        })
        
        # ---- CITATION SETUP ----
        citation_tracker = CitationTracker()
        source_docs = SourceDocumentation()
        
        for policy in retrieved_data.get("policies", []):
            citation_tracker.register_source(
                policy.get("id", "unknown"),
                policy.get("source", "unknown"),
                policy.get("page", 0),
                policy.get("text", ""),
                policy.get("section")
            )
        
        # ---- RESPONSE GENERATION WITH GUARDRAILS ----
        request_logger.log_event("response_generation_start", {"is_voice_mode": is_voice_mode})
        
        # Choose system prompt based on mode
        if is_voice_mode:
            system_prompt = _get_voice_system_prompt()
        else:
            system_prompt = (
                EnhancedPrompts.get_system_prompt_response() + "\n\n" +
                EnhancedPrompts.get_guardrail_prompt()
            )
        
        context_prompt = EnhancedPrompts.get_data_context_prompt(
            policy_chunks=retrieved_data.get("policies", []),
            parks_data=retrieved_data.get("parks", []),
            plots_data=retrieved_data.get("plots", []),
            pois_data=retrieved_data.get("pois"),
        )
        
        # Add conversation context if provided (for voice calls)
        user_content = context_prompt + "\n\nQuestion: " + user_question
        if conversation_context:
            user_content = f"## Conversation Context\n{conversation_context}\n\n---\n\n{user_content}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # Use LLM Factory - switches between Groq and OpenAI based on configuration
        llm_client = LLMFactory.get_client()
        request_logger.log_event("llm_config", {
            "provider": settings.LLM_PROVIDER,
            "model": settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.OPENAI_MODEL
        })
        
        # For Groq compatibility
        if hasattr(llm_client, 'query'):
            # Groq-like client
            combined_prompt = messages[-1]["content"]
            answer = llm_client.query(combined_prompt, max_tokens=1500, temperature=0.7)
        else:
            # OpenAI-like client with chat completions
            response = llm_client.client.chat.completions.create(
                model=llm_client.model,
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            answer = response.choices[0].message.content
        
        request_logger.log_event("response_generated", {
            "length": len(answer),
            "provider": settings.LLM_PROVIDER
        })
        
        # ---- FACT VERIFICATION ----
        request_logger.log_event("fact_verification_start", {})
        fact_verifier = get_fact_verifier(VerificationLevel.STRICT)
        response_categorizer = get_response_categorizer()
        
        # Detect factual claims in response
        factual_claims = response_categorizer.detect_factual_claims(answer)
        
        # Check if response is safe (doesn't hallucinate facts)
        response_is_safe = response_categorizer.is_response_safe(answer)
        
        # Categorize response into verified/requires-input/unavailable
        categorized_response = response_categorizer.categorize(answer)
        
        request_logger.log_event("fact_verification", {
            "factual_claims_detected": sum(len(v) for v in factual_claims.values()),
            "response_safe": response_is_safe,
            "verified_info_count": len(categorized_response.verified_information),
            "requires_input_count": len(categorized_response.requires_user_input),
            "unavailable_count": len(categorized_response.unavailable_data)
        })
        
        # ---- CITATION VERIFICATION ----
        request_logger.log_event("citation_verification_start", {})
        
        citation_verification = citation_tracker.verify_citations_in_response(
            answer,
            retrieved_data.get("policies", [])
        )
        
        request_logger.log_event("citation_verification_complete", {
            "citations_found": len(citation_verification.citations),
            "verified_count": citation_verification.verified_count,
            "confidence": citation_verification.confidence_score
        })
        
        # ---- HALLUCINATION DETECTION ----
        request_logger.log_event("hallucination_detection_start", {})
        
        hal_risk, hal_indicators = HalluccinationDetector.score_hallucination_risk(
            answer,
            citation_verification.citations
        )
        
        request_logger.log_event("hallucination_detection_complete", {
            "risk_score": hal_risk,
            "indicators_count": len(hal_indicators)
        })
        
        # ---- RESPONSE VALIDATION ----
        request_logger.log_event("response_validation_start", {})
        
        validator = ResponseValidator()
        validated_response, validation_result = validate_and_fix_response(
            answer,
            user_question,
            retrieved_data,
            cache["states"][normalized_state].get("parks", []),
            cache["states"][normalized_state].get("plots", [])
        )
        
        request_logger.log_validation(
            validation_result.is_valid,
            validation_result.confidence_score,
            validation_result.issues,
            validation_result.warnings
        )
        
        # ---- ADD CITATIONS TO RESPONSE ----
        final_response = citation_tracker.add_citations_to_response(
            validated_response,
            citation_verification.citations
        )
        
        # ---- COMPILE RESULT ----
        execution_time = time.time() - start_time
        
        # Generate voice response (conversational, no tags)
        voice_response = _create_voice_response(final_response)
        
        result = {
            "answer": final_response,
            "text_response": final_response,
            "voice_response": voice_response,
            "state": normalized_state,
            "confidence_score": validation_result.confidence_score,
            "hallucination_risk": hal_risk,
            "tools_used": [],
            "citations": [c.to_dict() for c in citation_verification.citations],
            "validation": {
                "is_valid": validation_result.is_valid,
                "issues": validation_result.issues,
                "warnings": validation_result.warnings,
            },
            # ---- NEW: FACT VERIFICATION DATA ----
            "fact_verification": {
                "response_is_safe": response_is_safe,
                "factual_claims": factual_claims,
                "categorized_response": {
                    "verified_information": categorized_response.verified_information,
                    "requires_user_input": categorized_response.requires_user_input,
                    "unavailable_data": categorized_response.unavailable_data,
                    "sources": categorized_response.sources,
                    "follow_up_questions": categorized_response.follow_up_questions,
                }
            },
            "metadata": {
                "request_id": request_id,
                "execution_time_ms": round(execution_time * 1000, 2),
                "data_sources_count": sum(1 for d in retrieved_data.values() if d),
                "llm_provider": settings.LLM_PROVIDER,
                "llm_model": settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.OPENAI_MODEL,
            }
        }
        
        # ---- LOGGING & AUDIT ----
        perf_monitor.record_request_time(execution_time)
        
        audit_logger.log_request(
            user_id=None,
            state=normalized_state,
            question=user_question,
            response=final_response,
            confidence=validation_result.confidence_score,
            success=True
        )
        
        request_logger.log_event("completed", {
            "success": True,
            "confidence": validation_result.confidence_score,
            "execution_time_ms": round(execution_time * 1000, 2),
            "llm_provider": settings.LLM_PROVIDER
        })
        
        logger.info(f"[REQUEST {request_id}] Completed successfully. Confidence: {validation_result.confidence_score:.2f}, Provider: {settings.LLM_PROVIDER}")
        
        return result
        
    except Exception as e:
        request_logger.log_error(e)
        logger.error(f"[REQUEST {request_id}] Error: {str(e)}", exc_info=True)
        
        return _error_response(
            f"Error processing request: {str(e)}",
            request_logger,
            state,
            user_question,
            success=False,
            error=str(e)
        )


def _execute_tools_intelligently(
    state: str,
    question: str,
    request_logger: RequestLogger,
    perf_monitor: Any
) -> Dict[str, List[Any]]:
    """
    Execute tools intelligently based on question context.
    
    Returns:
        Dictionary with policies, parks, plots, pois
    """
    retrieved_data = {
        "policies": [],
        "parks": [],
        "plots": [],
        "pois": []
    }
    
    # Analyze question to determine which tools to call
    question_lower = question.lower()
    
    # Always search policies for industrial policy questions
    if any(word in question_lower for word in ["policy", "scheme", "incentive", "benefit", "rule", "regulation"]):
        tool_start = time.time()
        try:
            policies = tool_search_policy(state=state, query=question)
            execution_time = time.time() - tool_start
            
            # Validate results
            validator = ToolResultValidator()
            validation = validator.validate_search_results(policies)
            
            if validation.is_valid or len(policies) > 0:
                retrieved_data["policies"] = policies
                request_logger.log_tool_call("search_policy", {"query": question[:100]}, len(policies), execution_time)
                perf_monitor.record_tool_time("search_policy", execution_time)
            else:
                request_logger.log_event("tool_validation_warning", {
                    "tool": "search_policy",
                    "issues": validation.errors
                }, level="WARNING")
        except Exception as e:
            request_logger.log_event("tool_error", {
                "tool": "search_policy",
                "error": str(e)
            }, level="ERROR")
    
    # Search for parks if question mentions location, availability, or parks
    if any(word in question_lower for word in ["park", "industrial", "location", "where", "area"]):
        tool_start = time.time()
        try:
            parks = tool_get_parks(state=state, limit=20)
            execution_time = time.time() - tool_start
            
            validator = ToolResultValidator()
            validation = validator.validate_list_results(parks, "park")
            
            if validation.is_valid or len(parks) > 0:
                retrieved_data["parks"] = parks
                request_logger.log_tool_call("get_parks", {"state": state}, len(parks), execution_time)
                perf_monitor.record_tool_time("get_parks", execution_time)
        except Exception as e:
            request_logger.log_event("tool_error", {
                "tool": "get_parks",
                "error": str(e)
            }, level="ERROR")
    
    # Search for plots if question mentions land, plot, or availability
    if any(word in question_lower for word in ["plot", "land", "available", "size", "rate"]):
        tool_start = time.time()
        try:
            plots = tool_get_plots(state=state, limit=20)
            execution_time = time.time() - tool_start
            
            validator = ToolResultValidator()
            validation = validator.validate_list_results(plots, "plot")
            
            if validation.is_valid or len(plots) > 0:
                retrieved_data["plots"] = plots
                request_logger.log_tool_call("get_plots", {"state": state}, len(plots), execution_time)
                perf_monitor.record_tool_time("get_plots", execution_time)
        except Exception as e:
            request_logger.log_event("tool_error", {
                "tool": "get_plots",
                "error": str(e)
            }, level="ERROR")
    
    # Search for infrastructure if question mentions proximity, distance, or facilities
    if any(word in question_lower for word in ["near", "proximity", "infrastructure", "airport", "station", "distance"]):
        tool_start = time.time()
        try:
            # Use center coordinates if available
            pois = tool_find_nearby_pois(state=state, lat=23.1815, lng=79.9864, radius_km=50)
            execution_time = time.time() - tool_start
            
            if pois:
                retrieved_data["pois"] = pois
                request_logger.log_tool_call("find_nearby_pois", {"state": state}, len(pois), execution_time)
                perf_monitor.record_tool_time("find_nearby_pois", execution_time)
        except Exception as e:
            request_logger.log_event("tool_error", {
                "tool": "find_nearby_pois",
                "error": str(e)
            }, level="ERROR")
    
    return retrieved_data


def _error_response(
    error_msg: str,
    request_logger: RequestLogger,
    state: str,
    question: str,
    success: bool,
    error: str = None
) -> Dict[str, Any]:
    """Generate error response with proper logging"""
    request_id = request_logger.request_id
    
    response = {
        "answer": error_msg,
        "state": state,
        "confidence_score": 0.0,
        "error": error or error_msg,
        "tools_used": [],
        "metadata": {
            "request_id": request_id,
            "success": success
        }
    }
    
    get_audit_logger().log_request(
        user_id=None,
        state=state,
        question=question,
        response=error_msg,
        confidence=0.0,
        success=success
    )
    
    return response


def _create_voice_response(text_response: str) -> str:
    """
    Convert structured text response into natural voice response.
    
    - Removes [VERIFIED INFORMATION], [REQUIRES USER INPUT], [CANNOT DETERMINE] tags
    - Removes robotic disclaimers
    - Truncates to 2-4 sentences for voice (~150-200 words)
    - Makes it sound like a human consultant, not a chatbot
    """
    # Remove tag markers
    response = text_response.replace("[VERIFIED INFORMATION]", "")
    response = response.replace("[REQUIRES USER INPUT]", "")
    response = response.replace("[CANNOT DETERMINE]", "")
    response = response.replace("[POLICY DATA]", "")
    
    # Remove robotic phrases
    robotic_phrases = [
        "I must inform you that",
        "Please note that",
        "It is important to note that",
        "According to the data",
        "I am unable to provide",
        "I cannot determine",
        "requires user input",
    ]
    
    for phrase in robotic_phrases:
        response = response.replace(phrase, "", 1)
    
    # Remove extra whitespace
    response = " ".join(response.split())
    
    # Truncate to ~2-4 sentences for voice
    sentences = response.split(". ")
    if len(sentences) > 4:
        response = ". ".join(sentences[:4]) + "."
    elif len(sentences) == 0:
        response = response[:200]
    
    # Remove "Hmm" or "Well" artifacts
    response = response.lstrip("Hmm ").lstrip("Well ")
    
    return response.strip()


def _get_voice_system_prompt() -> str:
    """
    System prompt for voice mode - encourages natural, conversational responses.
    No tags, no disclaimers, sounds like a trained investor relationship manager.
    """
    return """You are a professional investor relationship manager speaking with a potential industrial investor.

CRITICAL VOICE BEHAVIORS:
1. SPEAK NATURALLY - Use conversational English, not technical jargon
2. ASK ONE QUESTION AT A TIME - Let the conversation flow naturally
3. NO DISCLAIMERS - Don't say "I must inform you" or "Please note that"
4. NO DATA DUMPS - Never list 10 things. Pick 2-3 most relevant ones
5. PERSONAL TOUCH - Use their preferences from conversation context
6. NO TAGS OR MARKERS - Never output [VERIFIED INFORMATION] or similar
7. SHORT RESPONSES - Keep sentences clear and punchy

STRUCTURE (INTERNAL ONLY - NOT VISIBLE):
Your response will be split into two versions:
1. VOICE: 2-4 sentences, conversational, for text-to-speech
2. TEXT: Structured with bullet points, for display if needed

VOICE GUIDELINES:
- "We have some great opportunities in pharmaceutical manufacturing..." (not "Pharmaceutical sector availability includes...")
- "Indore would be perfect for your timeline" (not "District suitability analysis shows...")
- "Let me ask - what's your investment horizon?" (not "Investment timeline is required for next steps")

ABSOLUTE RULES:
- NEVER say "According to policy..."
- NEVER list coordinates or technical specs
- NEVER output JSON or code
- NEVER use [BRACKETS] for anything
- NEVER say "I cannot determine" - instead say "I'd need to check on that"

Be warm, professional, and focused on helping them find the right opportunity."""


