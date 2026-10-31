"""
api/format_rules.py — Format rules endpoints (Phase 0 stub).
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import FormatRule
from backend.app.models import Session as SessionModel
from backend.app.schemas import FormatRulesOut, FormatRulesPut

router = APIRouter(prefix="/sessions", tags=["format_rules"])


@router.get("/{session_id}/format-rules", response_model=FormatRulesOut | None)
async def get_format_rules(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> FormatRulesOut | None:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await db.execute(select(FormatRule).where(FormatRule.session_id == session_id))
    rule = result.scalar_one_or_none()
    return FormatRulesOut.model_validate(rule) if rule else None


@router.put("/{session_id}/format-rules", response_model=FormatRulesOut)
async def put_format_rules(
    session_id: int, body: FormatRulesPut, db: AsyncSession = Depends(get_db)
) -> FormatRulesOut:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(select(FormatRule).where(FormatRule.session_id == session_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        rule = FormatRule(session_id=session_id)
        db.add(rule)

    rule.rules_json = json.dumps(body.rules)
    rule.confirmed_by_se = body.confirmed_by_se
    rule.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rule)
    return FormatRulesOut.model_validate(rule)
