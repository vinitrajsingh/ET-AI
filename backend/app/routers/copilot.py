"""
Copilot endpoint.

  POST /copilot/ask   body {query, history?} -> a grounded, cited CopilotAnswer

Synchronous by design; streaming is not needed for the demo. The reasoning lives
in copilot_service.
"""

from pydantic import BaseModel, Field

from fastapi import APIRouter

from app.services.copilot_service import CopilotAnswer, answer_question

router = APIRouter(prefix="/copilot", tags=["copilot"])


class AskRequest(BaseModel):
    query: str
    # Prior turns as {role, content}, oldest first, so follow-up questions resolve.
    history: list[dict] = Field(default_factory=list)


@router.post("/ask", response_model=CopilotAnswer)
def ask(request: AskRequest) -> CopilotAnswer:
    return answer_question(request.query, request.history)
