"""Citation-Backed Executive AI Research Assistant Endpoint (Section 8 Page 8)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.assistant_service import ExecutiveAssistantService

router = APIRouter(prefix="/assistant", tags=["Executive AI Research Assistant"])


class AssistantQuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=2000)


@router.post("/ask")
def ask_research_assistant(
    payload: AssistantQuestionRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Ask the Executive AI Research Assistant any question on Nigerian, African,
    or global markets, fixed income, FX, competitors, regulations, or investment opportunities.
    Returns a citation-backed response grounded in verified database records and reports.
    """
    return ExecutiveAssistantService.answer_executive_question(
        db=db,
        question=payload.question,
    )
