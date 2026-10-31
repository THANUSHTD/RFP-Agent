"""
api/validation.py — Intelligent response validation endpoints.

Level 2: Intelligent response validation.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Session as SessionModel
from backend.app.schemas import RegenerateRequest, ValidationOut
from backend.app.services.validation import compute_validation, list_validation_issues

router = APIRouter(prefix="/sessions", tags=["validation"])


@router.get(
    "/{session_id}/validation",
    response_model=ValidationOut,
    summary="Get response validation issues for a session",
)
async def get_validation(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> ValidationOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await list_validation_issues(db, session_id)


@router.post(
    "/{session_id}/validation/regenerate",
    response_model=ValidationOut,
    summary="Regenerate response validation for a session",
)
async def regenerate_validation(
    session_id: int,
    body: RegenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> ValidationOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await compute_validation(db, session_id)
