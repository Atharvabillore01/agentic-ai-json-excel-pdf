"""
Call session management for voice-first, call-style interaction.

Handles:
- Call initiation (agent speaks first greeting)
- Call continuation (turn-by-turn with state tracking)
- Call termination (summary generation)
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
from app.agents.agent import run_agent
from app.services.tts.elevenlabs_client import ElevenLabsClient
from app.core.cache import cache
import base64
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory call sessions (in production, use persistent store)
call_sessions: Dict[str, Dict[str, Any]] = {}


class CallStartRequest(BaseModel):
    state: str = "madhya_pradesh"
    investor_sector: Optional[str] = None
    investor_location: Optional[str] = None


class CallSendRequest(BaseModel):
    call_id: str
    user_message: str


class CallEndRequest(BaseModel):
    call_id: str


def _get_or_create_session(call_id: str) -> Dict[str, Any]:
    """Get existing session or create new one"""
    if call_id not in call_sessions:
        call_sessions[call_id] = {
            "id": call_id,
            "created_at": datetime.utcnow().isoformat(),
            "state": "madhya_pradesh",
            "conversation_history": [],
            "investor_preferences": {},
            "turn_count": 0,
            "status": "active"
        }
    return call_sessions[call_id]


def _generate_initial_greeting(state: str, investor_context: Optional[str] = None) -> str:
    """
    Generate opening greeting for the agent.
    Sounds like a professional relationship manager.
    """
    greetings = {
        "madhya_pradesh": "Hi there! I'm your industrial investment advisor. I specialize in opportunities across Madhya Pradesh. Is this your first time exploring industrial investments with us, or are you looking for something specific?",
        "maharashtra": "Hello! I'm here to help you navigate industrial investment opportunities across Maharashtra. What brings you in today?"
    }
    
    greeting = greetings.get(state, greetings["madhya_pradesh"])
    
    if investor_context:
        greeting = f"Hi! I see you're interested in {investor_context}. Perfect – I can help you find the right opportunity. Let me start by understanding your needs better. What timeline are you working with?"
    
    return greeting


async def _synthesize_and_encode(text: str) -> Optional[str]:
    """
    Convert text to audio and return base64.
    
    Handles gracefully:
    - Missing API key
    - API errors
    - Empty text
    
    Returns base64 audio or None if TTS unavailable
    """
    try:
        if not text or len(text.strip()) == 0:
            return None
        
        from app.core import settings
        
        # Check if API key is configured
        if not settings.ELEVENLABS_API_KEY or not settings.ELEVENLABS_VOICE_ID:
            logger.warning("TTS not configured: Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID")
            return None
        
        tts = ElevenLabsClient()
        audio_bytes = tts.synthesize(text)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        logger.info(f"[TTS] Synthesized {len(text)} chars to {len(audio_base64)} base64 chars")
        return audio_base64
        
    except Exception as e:
        logger.error(f"[TTS] Synthesis failed: {e}")
        return None


@router.post("/api/call/start")
async def start_call(payload: CallStartRequest):
    """
    Start a new call session.
    
    Returns:
    - call_id: Session identifier for subsequent messages
    - agent_greeting: Initial greeting from agent
    - audio_base64: Audio of the greeting (for auto-playback)
    - voice_state: AGENT_SPEAKING (user should listen first)
    """
    call_id = str(uuid.uuid4())
    session = _get_or_create_session(call_id)
    session["state"] = payload.state
    session["investor_sector"] = payload.investor_sector
    session["investor_location"] = payload.investor_location
    
    # Generate initial greeting
    context = None
    if payload.investor_sector or payload.investor_location:
        context = f"{payload.investor_sector or 'industrial'} opportunities in {payload.investor_location or payload.state}"
    
    greeting = _generate_initial_greeting(payload.state, context)
    
    # Synthesize greeting to audio
    audio_base64 = await _synthesize_and_encode(greeting)
    
    session["conversation_history"].append({
        "turn": 0,
        "role": "agent",
        "voice_response": greeting,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    logger.info(f"[CALL {call_id}] Started in state={payload.state}")
    
    return {
        "call_id": call_id,
        "agent_greeting": greeting,
        "audio_base64": audio_base64,
        "voice_state": "AGENT_SPEAKING",
        "turn_count": 0
    }


@router.post("/api/call/send")
async def send_call_message(payload: CallSendRequest):
    """
    Send user message during active call.
    
    Returns:
    - agent_response: Voice response (2-4 sentences, conversational)
    - text_response: Detailed response (for display if needed)
    - audio_base64: Audio of agent response
    - voice_state: Next state (AGENT_SPEAKING, LISTENING, IDLE)
    - conversation_state: Updated preferences and context
    """
    session = _get_or_create_session(payload.call_id)
    
    if session["status"] != "active":
        return {
            "error": "Call is not active",
            "voice_state": "IDLE"
        }
    
    # Record user input
    session["turn_count"] += 1
    session["conversation_history"].append({
        "turn": session["turn_count"],
        "role": "user",
        "message": payload.user_message,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Build conversation context for agent
    recent_history = "\n".join([
        f"{h['role']}: {h.get('message', h.get('voice_response', ''))}"
        for h in session["conversation_history"][-5:]  # Last 5 turns
    ])
    
    # Query agent with conversation context
    try:
        agent_result = run_agent(
            state=session["state"],
            user_question=payload.user_message,
            conversation_context=recent_history,
            is_voice_mode=True
        )
        
        # Extract voice and text responses
        voice_response = agent_result.get("voice_response", agent_result.get("answer", ""))
        text_response = agent_result.get("text_response", agent_result.get("answer", ""))
        
        # For now, if separate voice_response doesn't exist, use answer
        if not voice_response:
            voice_response = _make_response_conversational(text_response)
        
        # Synthesize voice response
        audio_base64 = await _synthesize_and_encode(voice_response)
        
        # Record agent response
        session["conversation_history"].append({
            "turn": session["turn_count"],
            "role": "agent",
            "voice_response": voice_response,
            "text_response": text_response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Update investor preferences from conversation
        _extract_investor_context(session, payload.user_message)
        
        logger.info(f"[CALL {payload.call_id}] Turn {session['turn_count']}: Agent responded")
        
        return {
            "call_id": payload.call_id,
            "agent_response": voice_response,
            "text_response": text_response,
            "audio_base64": audio_base64,
            "voice_state": "AGENT_SPEAKING",  # After agent speaks, user listens
            "turn_count": session["turn_count"],
            "conversation_state": {
                "investor_sector": session.get("investor_sector"),
                "investor_location": session.get("investor_location"),
                "turn_count": session["turn_count"]
            }
        }
        
    except Exception as e:
        logger.error(f"[CALL {payload.call_id}] Error: {e}", exc_info=True)
        return {
            "error": str(e),
            "voice_state": "IDLE",
            "call_id": payload.call_id
        }


@router.post("/api/call/end")
async def end_call(payload: CallEndRequest):
    """
    End call and generate summary.
    
    Returns:
    - summary_text: Text summary of conversation
    - summary_audio: Spoken summary
    - call_summary: Structured summary with investor intent, opportunities discussed, next steps
    """
    session = _get_or_create_session(payload.call_id)
    session["status"] = "ended"
    session["ended_at"] = datetime.utcnow().isoformat()
    
    # Generate summary from conversation history
    summary = _generate_call_summary(session)
    
    # Synthesize summary
    summary_audio = await _synthesize_and_encode(summary["spoken_summary"])
    
    logger.info(f"[CALL {payload.call_id}] Ended. Summary: {summary['investor_intent']}")
    
    # Clean up session after small delay (in production, archive to DB)
    # del call_sessions[payload.call_id]
    
    return {
        "call_id": payload.call_id,
        "summary": summary["structured_summary"],
        "summary_text": summary["spoken_summary"],
        "summary_audio": summary_audio,
        "turn_count": session["turn_count"],
        "duration_seconds": (
            (datetime.fromisoformat(session["ended_at"]) - datetime.fromisoformat(session["created_at"])).total_seconds()
        )
    }


def _make_response_conversational(text: str) -> str:
    """
    Convert structured response with tags into natural voice response.
    Removes [VERIFIED INFORMATION], [REQUIRES USER INPUT], [CANNOT DETERMINE] tags.
    """
    # Remove tag markers
    response = text.replace("[VERIFIED INFORMATION]", "").replace("[REQUIRES USER INPUT]", "").replace("[CANNOT DETERMINE]", "")
    
    # Remove extra whitespace
    response = " ".join(response.split())
    
    # Truncate to ~2-4 sentences for voice (roughly 150-200 words)
    sentences = response.split(". ")
    if len(sentences) > 4:
        response = ". ".join(sentences[:4]) + "."
    
    return response.strip()


def _extract_investor_context(session: Dict[str, Any], message: str) -> None:
    """Extract investor preferences from user message"""
    message_lower = message.lower()
    
    # Simple extraction (in production, use NER/entity extraction)
    sectors = ["automotive", "pharmaceuticals", "textiles", "electronics", "metal", "food", "chemicals"]
    for sector in sectors:
        if sector in message_lower:
            session["investor_sector"] = sector
            break
    
    districts = ["indore", "ujjain", "bhopal", "pune", "mumbai", "nagpur"]
    for district in districts:
        if district in message_lower:
            session["investor_location"] = district
            break


def _generate_call_summary(session: Dict[str, Any]) -> Dict[str, str]:
    """Generate structured and spoken summary of the call"""
    history = session["conversation_history"]
    
    # Build summary text
    investor_intent = "Exploring industrial investment opportunities"
    if session.get("investor_sector"):
        investor_intent += f" in {session['investor_sector']}"
    if session.get("investor_location"):
        investor_intent += f" around {session['investor_location']}"
    
    # Extract discussed opportunities
    opportunities = []
    for turn in history:
        if turn["role"] == "agent" and "park" in turn.get("voice_response", "").lower():
            opportunities.append(turn.get("voice_response", "")[:100])
    
    spoken_summary = (
        f"Thank you for taking the time to speak with us today. "
        f"Here's what we discussed: You're interested in {session.get('investor_sector', 'industrial')} opportunities, "
        f"preferably around {session.get('investor_location', 'the region')}. "
        f"We explored a few suitable locations that match your needs. "
        f"I'll prepare detailed documentation and send it your way. Please expect a follow-up within 24 hours. "
        f"In the meantime, feel free to reach out if you have any questions."
    )
    
    structured_summary = {
        "investor_intent": investor_intent,
        "preferred_sector": session.get("investor_sector", "Not specified"),
        "preferred_location": session.get("investor_location", "Not specified"),
        "opportunities_discussed": len(opportunities),
        "total_turns": session["turn_count"],
        "suggested_next_steps": [
            "Review detailed park/plot data",
            "Schedule site visit",
            "Connect with local authorities",
            "Finalize investment timeline"
        ]
    }
    
    return {
        "investor_intent": investor_intent,
        "spoken_summary": spoken_summary,
        "structured_summary": structured_summary
    }
