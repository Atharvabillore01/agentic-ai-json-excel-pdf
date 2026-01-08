from fastapi import APIRouter
from app.agents.agent import run_agent
from pydantic import BaseModel
from asyncio import Lock
router = APIRouter()
agent_lock = Lock()

class AskRequest(BaseModel):
    question: str

@router.post("/api/{state}/ask")
async def ask_question(state: str, payload: AskRequest):
    async with agent_lock:
        return run_agent(state, payload.question)