from fastapi import APIRouter
from app.agents.agent import run_agent
from pydantic import BaseModel

router = APIRouter()

class AskRequest(BaseModel):
    question: str

@router.post("/api/{state}/ask")
def ask_question(state: str, payload: AskRequest):
    return run_agent(state, payload.question)