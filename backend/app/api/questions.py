"""
api/questions.py — Question and answer endpoints (Phase 0 stubs).

Full implementation comes in Phase 3 once the analysis graph populates the DB.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Answer, Question, Session as SessionModel
from backend.app.schemas import AnswerOut, AnswerPatch, ApproveRequest, OKResponse, QuestionOut

router = APIRouter(tags=["questions"])


@router.get("/sessions/{session_id}/questions", response_model=list[QuestionOut])
async def list_questions(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> list[QuestionOut]:
    """Return all questions for a session."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(Question).where(Question.session_id == session_id).order_by(Question.id)
    )
    return [QuestionOut.model_validate(q) for q in result.scalars()]


@router.get("/questions/{question_id}/answer", response_model=AnswerOut | None)
async def get_answer(question_id: int, db: AsyncSession = Depends(get_db)) -> AnswerOut | None:
    """Return the latest draft answer for a question."""
    result = await db.execute(
        select(Answer)
        .where(Answer.question_id == question_id)
        .order_by(Answer.version.desc())
        .limit(1)
    )
    answer = result.scalar_one_or_none()
    return AnswerOut.model_validate(answer) if answer else None


@router.patch("/questions/{question_id}/answer", response_model=AnswerOut)
async def patch_answer(
    question_id: int, body: AnswerPatch, db: AsyncSession = Depends(get_db)
) -> AnswerOut:
    """SE edits an answer text; marks edited_by_se=True and bumps version."""
    result = await db.execute(
        select(Answer)
        .where(Answer.question_id == question_id)
        .order_by(Answer.version.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        raise HTTPException(status_code=404, detail="No answer found for this question")

    # Create a new version rather than mutating the existing draft
    new_answer = Answer(
        question_id=question_id,
        version=existing.version + 1,
        text=body.text if body.text is not None else existing.text,
        confidence=existing.confidence,
        citations_json=existing.citations_json,
        stale_warnings_json=existing.stale_warnings_json,
        status="draft",
        edited_by_se=True,
    )
    db.add(new_answer)
    await db.commit()
    await db.refresh(new_answer)
    return AnswerOut.model_validate(new_answer)


@router.post("/questions/{question_id}/approve", response_model=OKResponse)
async def approve_answer(
    question_id: int, body: ApproveRequest, db: AsyncSession = Depends(get_db)
) -> OKResponse:
    """SE explicitly approves the current draft answer.

    The SE must send confirm=True to prevent accidental approvals.
    The agent itself never calls this endpoint.
    """
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm must be True to approve.")

    result = await db.execute(
        select(Answer)
        .where(Answer.question_id == question_id)
        .order_by(Answer.version.desc())
        .limit(1)
    )
    answer = result.scalar_one_or_none()
    if answer is None:
        raise HTTPException(status_code=404, detail="No answer found for this question")

    from datetime import datetime
    answer.status = "approved"
    answer.approved_at = datetime.utcnow()

    # Mark the question approved too
    question = await db.get(Question, question_id)
    if question:
        question.status = "approved"

    await db.commit()
    return OKResponse(message="Answer approved.")
