"""
api/export.py — Export endpoints (Phase 0 stub).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Session as SessionModel
from backend.app.schemas import OKResponse

router = APIRouter(prefix="/sessions", tags=["export"])


@router.post("/{session_id}/export", response_model=OKResponse)
async def export_session(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> OKResponse:
    """Generate .docx and .xlsx exports (stub — Phase 5)."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return OKResponse(message="Export not yet implemented (Phase 0 stub).")
