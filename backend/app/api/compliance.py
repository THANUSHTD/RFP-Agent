"""
api/compliance.py — Response codes (S/C/D/T/N) and compliance matrix endpoints.

Level 2: Intelligent Compliance Matrix.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Session as SessionModel
from backend.app.schemas import (
    ComplianceMatrixOut,
    QuestionResponseCodeOut,
    QuestionResponseCodePut,
)
from backend.app.services.compliance import (
    compute_compliance_matrix,
    get_or_create_response_code,
    list_response_codes,
    set_response_code,
)

router = APIRouter(prefix="/sessions", tags=["compliance"])


@router.get(
    "/{session_id}/compliance-matrix",
    response_model=ComplianceMatrixOut,
    summary="Get the requirement-by-requirement compliance matrix",
)
async def get_compliance_matrix(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> ComplianceMatrixOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await compute_compliance_matrix(db, session_id)


@router.get(
    "/{session_id}/response-codes",
    response_model=list[QuestionResponseCodeOut],
    summary="List response codes for all questions in a session",
)
async def list_codes(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> list[QuestionResponseCodeOut]:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await list_response_codes(db, session_id)


@router.get(
    "/{session_id}/questions/{question_id}/response-code",
    response_model=QuestionResponseCodeOut,
    summary="Get the response code for a single question",
)
async def get_code(
    session_id: int, question_id: int, db: AsyncSession = Depends(get_db)
) -> QuestionResponseCodeOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        return await get_or_create_response_code(db, session_id, question_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put(
    "/{session_id}/questions/{question_id}/response-code",
    response_model=QuestionResponseCodeOut,
    summary="Set / update the response code for a question",
)
async def put_code(
    session_id: int,
    question_id: int,
    body: QuestionResponseCodePut,
    db: AsyncSession = Depends(get_db),
) -> QuestionResponseCodeOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        return await set_response_code(db, session_id, question_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
