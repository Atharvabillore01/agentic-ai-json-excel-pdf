from fastapi import APIRouter
from app.agents.agent import run_agent
from pydantic import BaseModel
from asyncio import Lock
from app.core.cache import cache
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
agent_lock = Lock()

class AskRequest(BaseModel):
    question: str

def detect_state_from_question(question: str) -> str:
    """
    Auto-detect state from question.
    Looks for state names in the question.
    Falls back to default state if not found.
    """
    question_lower = question.lower()
    available_states = list(cache.get("states", {}).keys())
    
    # Check for state names in question
    for state in available_states:
        state_lower = state.lower()
        # Match full state name or common abbreviations
        if state_lower in question_lower or state.replace("_", " ").lower() in question_lower:
            logger.info(f"Auto-detected state: {state}")
            return state
    
    # Check for common references
    state_mappings = {
        "mp": "madhya_pradesh",
        "madhya pradesh": "madhya_pradesh",
        "maharashtra": "maharashtra",
        "mh": "maharashtra",
    }
    
    for ref, state in state_mappings.items():
        if ref in question_lower and state in available_states:
            logger.info(f"Auto-detected state from reference '{ref}': {state}")
            return state
    
    # Default to madhya_pradesh if no state detected
    default_state = "madhya_pradesh" if "madhya_pradesh" in available_states else available_states[0]
    logger.info(f"No state detected in question, using default: {default_state}")
    return default_state

@router.post("/api/{state}/ask")
async def ask_question(state: str, payload: AskRequest):
    """Traditional endpoint with explicit state selection"""
    async with agent_lock:
        return run_agent(state, payload.question)

@router.post("/api/ask")
async def ask_question_auto(payload: AskRequest):
    """
    Auto-detect state endpoint - no dropdown needed!
    System automatically identifies which state you're asking about.
    """
    detected_state = detect_state_from_question(payload.question)
    async with agent_lock:
        return run_agent(detected_state, payload.question)