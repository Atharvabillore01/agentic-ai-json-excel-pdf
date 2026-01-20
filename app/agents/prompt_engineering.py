"""
Enhanced multi-stage prompt engineering to reduce hallucinations.
"""
from typing import List, Dict, Any, Optional
from enum import Enum


class PromptStage(Enum):
    """Stages of prompt engineering"""
    ANALYSIS = "analysis"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    RESPONSE = "response"
    VALIDATION = "validation"


class EnhancedPrompts:
    """Multi-stage prompts for reliable responses"""
    
    @staticmethod
    def get_system_prompt_analysis() -> str:
        """First stage: Analyze user question to identify intent"""
        return """You are an expert industrial policy analyst assistant.

Your task: Analyze the user's question to identify:
1. What specific information they're seeking
2. Which data sources might be relevant (policies, parks, plots, infrastructure)
3. Key entities mentioned (locations, industries, schemes)
4. The complexity level of the question

Be precise and factual. Do not speculate.

Output your analysis in a structured format:
- **Intent**: What the user wants to know
- **Required Data**: What information is needed
- **Entities**: Specific locations/schemes/industries mentioned
- **Query Terms**: Key search terms for the policy database
- **Complexity**: Simple/Medium/Complex"""
    
    @staticmethod
    def get_system_prompt_retrieval() -> str:
        """Second stage: Retrieve relevant information"""
        return """You are an information retrieval specialist.

Your task: Based on the analysis provided, determine:
1. Which tools need to be called to retrieve relevant data
2. The specific parameters for each tool call
3. The priority order of tool calls

Guidelines:
- Use search_policy for policy questions
- Use get_parks for park availability questions
- Use get_plots for plot/land availability questions
- Use find_nearby_pois for infrastructure questions
- Call tools in logical sequence
- Do not guess or assume results - fetch actual data

Be explicit about what you're looking for in each tool call."""
    
    @staticmethod
    def get_system_prompt_reasoning() -> str:
        """Third stage: Reason through retrieved data"""
        return """You are an analytical expert. Your task is to reason through the retrieved data.

Guidelines:
1. **Source Everything**: Every claim must reference retrieved data
2. **Compare Multiple Sources**: Cross-reference information from different tools
3. **Identify Gaps**: Note any missing information
4. **Flag Uncertainties**: Mark claims with lower confidence
5. **Create Connections**: Link policies to parks, parks to infrastructure
6. **Avoid Speculation**: Only state facts from data, not assumptions

Format your reasoning:
- **Fact**: [Claim]
- **Source**: [Which tool/data provided this]
- **Confidence**: High/Medium/Low
- **Supporting Evidence**: [Specific data point]"""
    
    @staticmethod
    def get_system_prompt_response() -> str:
        """Fourth stage: Generate final response"""
        return """You are a professional policy advisor. Generate a clear, well-structured response.

Requirements:
1. **Factual Accuracy**: Only state facts from provided data
2. **Clear Structure**: Use headers, bullet points for clarity
3. **Citation**: Reference specific policies, page numbers, or data points
4. **Actionability**: Provide practical, specific information
5. **Completeness**: Address all aspects of the question
6. **Honesty**: Clearly state limitations or missing information

Format:
- Use bullet points for lists
- Include specific policy references
- Mention relevant infrastructure/parks by name
- State any assumptions clearly
- Include a brief summary at the end"""
    
    @staticmethod
    def get_system_prompt_validation() -> str:
        """Fifth stage: Validate response before returning"""
        return """You are a quality assurance expert. Review the response for:

1. **Accuracy Check**: Are all facts supported by provided data?
2. **Hallucination Check**: Are any claims unsourced or speculative?
3. **Citation Check**: Are important claims properly cited?
4. **Completeness Check**: Does it answer the user's question?
5. **Clarity Check**: Is it easy to understand?

Return assessment:
- **Valid**: Yes/No
- **Confidence Score**: 0-100
- **Issues Found**: List any problems
- **Suggestions**: How to improve if needed
- **Final Version**: Corrected response if improvements made"""
    
    @staticmethod
    def get_data_context_prompt(
        policy_chunks: List[Dict[str, Any]],
        parks_data: List[Dict[str, Any]],
        plots_data: List[Dict[str, Any]],
        pois_data: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build context prompt with available data"""
        prompt = "\n## AVAILABLE DATA FOR THIS QUERY\n\n"
        
        if policy_chunks:
            prompt += "### Relevant Policies:\n"
            for chunk in policy_chunks[:5]:  # Limit to top 5
                prompt += f"- **Source**: {chunk.get('source', 'unknown')} "
                prompt += f"(Page {chunk.get('page', '?')})\n"
                prompt += f"  *Excerpt*: {chunk.get('text', '')[:200]}...\n\n"
        
        if parks_data:
            prompt += "### Industrial Parks:\n"
            for park in parks_data[:5]:
                prompt += f"- **{park.get('park_name', 'Unknown')}** "
                prompt += f"({park.get('district', '?')}), "
                prompt += f"Status: {park.get('status', 'Unknown')}\n"
        
        if plots_data:
            prompt += "### Available Plots:\n"
            prompt += f"  Total available: {len(plots_data)} plots\n"
            plot_sample = plots_data[:3]
            for plot in plot_sample:
                prompt += f"  - Plot {plot.get('plot_number', '?')}: "
                prompt += f"{plot.get('size_sq_m', '?')} sq.m\n"
        
        if pois_data:
            prompt += "### Nearby Infrastructure:\n"
            for poi in pois_data[:3]:
                props = poi.get("properties", {})
                prompt += f"- {props.get('name', 'Unknown')}: "
                prompt += f"{props.get('type', 'Unknown')}\n"
        
        prompt += "\n---\n"
        return prompt
    
    @staticmethod
    def get_guardrail_prompt() -> str:
        """Guardrails to prevent hallucination"""
        return """STRICT GUARDRAILS:

1. **FACT ONLY**: Never invent data, parks, policies, or benefits
2. **NO SPECULATION**: Don't use "probably", "likely", "seems like", "might"
3. **CITE SOURCES**: Reference specific policies or data points
4. **NO ASSUMPTIONS**: Don't assume information not explicitly provided
5. **ADMIT GAPS**: If data is unavailable, say so explicitly
6. **ONE TRUTH**: Don't provide multiple conflicting statements
7. **VERIFY CLAIMS**: Cross-check facts with data before including
8. **NO TRENDS**: Don't project future trends without explicit data

RED FLAGS to avoid:
- ❌ "Industrial parks in this region typically..."
- ❌ "Usually the government provides..."
- ❌ "It's reasonable to assume..."
- ❌ "There's likely a [policy/benefit]..."
- ❌ "Most investors find..."

GREEN FLAGS to use:
- ✅ "According to [Policy Name]..."
- ✅ "The data shows..."
- ✅ "There are [X] parks currently..."
- ✅ "Available plots include..."
- ✅ "This information is not currently available in our database"

If uncertain about ANY claim: DO NOT INCLUDE IT."""


class PromptBuilder:
    """Build context-aware prompts"""
    
    @staticmethod
    def build_analysis_prompt(user_question: str, state: str) -> str:
        """Build prompt for question analysis stage"""
        return f"""{EnhancedPrompts.get_system_prompt_analysis()}

State Context: {state}
User Question: {user_question}

Provide your analysis:"""
    
    @staticmethod
    def build_retrieval_prompt(
        user_question: str,
        analysis: str,
        state: str,
    ) -> str:
        """Build prompt for data retrieval stage"""
        return f"""{EnhancedPrompts.get_system_prompt_retrieval()}

State: {state}
User Question: {user_question}

Previous Analysis:
{analysis}

Based on this analysis, what tools should we call and how?"""
    
    @staticmethod
    def build_reasoning_prompt(
        user_question: str,
        retrieved_data: Dict[str, Any],
    ) -> str:
        """Build prompt for reasoning stage"""
        context = EnhancedPrompts.get_data_context_prompt(
            policy_chunks=retrieved_data.get("policies", []),
            parks_data=retrieved_data.get("parks", []),
            plots_data=retrieved_data.get("plots", []),
            pois_data=retrieved_data.get("pois"),
        )
        
        return f"""{EnhancedPrompts.get_system_prompt_reasoning()}

{context}

User Question: {user_question}

Now reason through the data:"""
    
    @staticmethod
    def build_response_prompt(
        user_question: str,
        reasoning: str,
        retrieved_data: Dict[str, Any],
    ) -> str:
        """Build prompt for response generation stage"""
        guardrails = EnhancedPrompts.get_guardrail_prompt()
        context = EnhancedPrompts.get_data_context_prompt(
            policy_chunks=retrieved_data.get("policies", []),
            parks_data=retrieved_data.get("parks", []),
            plots_data=retrieved_data.get("plots", []),
            pois_data=retrieved_data.get("pois"),
        )
        
        return f"""{EnhancedPrompts.get_system_prompt_response()}

{guardrails}

{context}

User Question: {user_question}

Previous Reasoning:
{reasoning}

Now generate the final response:"""
    
    @staticmethod
    def build_validation_prompt(
        user_question: str,
        response: str,
        retrieved_data: Dict[str, Any],
    ) -> str:
        """Build prompt for validation stage"""
        context = EnhancedPrompts.get_data_context_prompt(
            policy_chunks=retrieved_data.get("policies", []),
            parks_data=retrieved_data.get("parks", []),
            plots_data=retrieved_data.get("plots", []),
            pois_data=retrieved_data.get("pois"),
        )
        
        return f"""{EnhancedPrompts.get_system_prompt_validation()}

{context}

User Question: {user_question}

Response to Validate:
{response}

Provide your validation assessment:"""


def create_multi_stage_prompt(
    stage: PromptStage,
    user_question: str,
    state: str,
    analysis: Optional[str] = None,
    reasoning: Optional[str] = None,
    response: Optional[str] = None,
    retrieved_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a prompt for a specific stage of the multi-stage pipeline.
    
    Args:
        stage: Which stage of processing
        user_question: User's original question
        state: State context
        analysis: Previous analysis result
        reasoning: Previous reasoning result
        response: Response to validate
        retrieved_data: Retrieved data from tools
    
    Returns:
        Formatted prompt for LLM
    """
    builder = PromptBuilder()
    retrieved_data = retrieved_data or {}
    
    if stage == PromptStage.ANALYSIS:
        return builder.build_analysis_prompt(user_question, state)
    
    elif stage == PromptStage.RETRIEVAL:
        if not analysis:
            raise ValueError("Analysis required for retrieval stage")
        return builder.build_retrieval_prompt(user_question, analysis, state)
    
    elif stage == PromptStage.REASONING:
        return builder.build_reasoning_prompt(user_question, retrieved_data)
    
    elif stage == PromptStage.RESPONSE:
        if not reasoning:
            raise ValueError("Reasoning required for response stage")
        return builder.build_response_prompt(
            user_question,
            reasoning,
            retrieved_data
        )
    
    elif stage == PromptStage.VALIDATION:
        if not response:
            raise ValueError("Response required for validation stage")
        return builder.build_validation_prompt(
            user_question,
            response,
            retrieved_data
        )
    
    else:
        raise ValueError(f"Unknown stage: {stage}")
