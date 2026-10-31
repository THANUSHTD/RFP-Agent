"""
api/checklist.py — Submission checklist endpoints.

Level 2: Customer-specific formatting & submission checklist.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Session as SessionModel
from backend.app.schemas import (
    ChecklistSummary,
    SubmissionChecklistOut,
    SubmissionChecklistPut,
)
from backend.app.services.checklist import (
    compute_checklist,
    list_checklist,
    update_checklist_item,
)

router = APIRouter(prefix="/sessions", tags=["checklist"])


@router.get(
    "/{session_id}/checklist",
    response_model=ChecklistSummary,
    summary="Get the submission checklist for a session",
)
async def get_checklist(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> ChecklistSummary:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await list_checklist(db, session_id)


@router.post(
    "/{session_id}/checklist/regenerate",
    response_model=ChecklistSummary,
    summary="Regenerate submission checklist from current session state",
)
async def regenerate_checklist(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> ChecklistSummary:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await compute_checklist(db, session_id)


@router.put(
    "/{session_id}/checklist/{item_key}",
    response_model=SubmissionChecklistOut,
    summary="Update a checklist item's status (done/pending)",
)
async def put_checklist_item(
    session_id: int,
    item_key: str,
    body: SubmissionChecklistPut,
    db: AsyncSession = Depends(get_db),
) -> SubmissionChecklistOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        return await update_checklist_item(db, session_id, item_key, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
