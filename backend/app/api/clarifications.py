"""
api/clarifications.py — Clarification list endpoints (Phase 0 stub).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Clarification
from backend.app.models import Session as SessionModel
from backend.app.schemas import ClarificationOut

router = APIRouter(prefix="/sessions", tags=["clarifications"])


@router.get("/{session_id}/clarifications", response_model=list[ClarificationOut])
async def list_clarifications(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> list[ClarificationOut]:
    """Return all clarifications for a session."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(Clarification)
        .where(Clarification.session_id == session_id)
        .order_by(Clarification.created_at)
    )
    return [ClarificationOut.model_validate(c) for c in result.scalars()]
