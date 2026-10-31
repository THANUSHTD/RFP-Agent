"""
api/gaps.py — AI-driven gap analysis endpoints.

Level 2: AI-driven gap analysis.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Session as SessionModel
from backend.app.schemas import GapAnalysisOut, RegenerateRequest
from backend.app.services.gap_analysis import compute_gap_analysis, list_gaps

router = APIRouter(prefix="/sessions", tags=["gap-analysis"])


@router.get(
    "/{session_id}/gaps",
    response_model=GapAnalysisOut,
    summary="Get gap analysis results for a session",
)
async def get_gaps(session_id: int, db: AsyncSession = Depends(get_db)) -> GapAnalysisOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await list_gaps(db, session_id)


@router.post(
    "/{session_id}/gaps/regenerate",
    response_model=GapAnalysisOut,
    summary="Regenerate gap analysis for a session",
)
async def regenerate_gaps(
    session_id: int,
    body: RegenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> GapAnalysisOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await compute_gap_analysis(db, session_id)
