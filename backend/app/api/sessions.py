"""
api/sessions.py — Session CRUD endpoints.

A session represents one RFP engagement. SEs create a session, upload an RFP,
and all subsequent work (questions, answers, chat) is scoped to that session.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Session as SessionModel
from backend.app.schemas import SessionCreate, SessionOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=201, summary="Create session")
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    """Create a new RFP engagement session."""
    session = SessionModel(name=body.name)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("Created session id=%d name=%s", session.id, session.name)
    return SessionOut.model_validate(session)


@router.get("", response_model=list[SessionOut], summary="List sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[SessionOut]:
    """Return all sessions ordered by most recent first."""
    result = await db.execute(select(SessionModel).order_by(SessionModel.updated_at.desc()))
    sessions = result.scalars().all()
    return [SessionOut.model_validate(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionOut, summary="Get session")
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    """Return a single session by ID."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut.model_validate(session)
