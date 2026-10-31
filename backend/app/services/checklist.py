"""
services/checklist.py — Customer-specific submission checklist.

Derives a completion checklist from format rules and session state, and tracks
done/pending status per item so the SE can see what remains before submission.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Answer,
    FormatRule,
    Question,
    QuestionResponseCode,
    Session as SessionModel,
    SubmissionChecklist,
)
from backend.app.schemas import ChecklistSummary, SubmissionChecklistOut

logger = logging.getLogger(__name__)

# Default checklist items (key, label). Order matters for display.
DEFAULT_ITEMS = [
    ("rfp_uploaded", "RFP document uploaded and analyzed"),
    ("format_rules_confirmed", "Customer format rules reviewed and confirmed"),
    ("requirements_extracted", "All requirements extracted with IDs and section references"),
    ("response_codes_assigned", "Response codes assigned (S / C / D / T / N)"),
    ("answers_reviewed", "All answers reviewed and approved"),
    ("clarifications_resolved", "Clarifications resolved or deferred"),
    ("export_generated", "Consolidated response exported (DOCX + XLSX)"),
]


def _default_checklist(session_id: int) -> list[dict[str, Any]]:
    return [
        {
            "session_id": session_id,
            "item_key": key,
            "label": label,
            "status": "pending",
            "done_by": None,
            "done_at": None,
        }
        for key, label in DEFAULT_ITEMS
    ]


async def _seed_defaults(db: AsyncSession, session_id: int) -> None:
    """Ensure a default checklist row exists for every item key."""
    existing_keys = {
        r.item_key
        for r in (
            await db.execute(
                select(SubmissionChecklist.item_key).where(
                    SubmissionChecklist.session_id == session_id
                )
            )
        ).scalars()
    }
    for key, label in DEFAULT_ITEMS:
        if key not in existing_keys:
            db.add(
                SubmissionChecklist(
                    session_id=session_id,
                    item_key=key,
                    label=label,
                    status="pending",
                )
            )
    await db.flush()


async def compute_checklist(
    db: AsyncSession, session_id: int
) -> ChecklistSummary:
    """(Re)compute checklist status from current session state and return summary."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    await _seed_defaults(db, session_id)

    # Session state signals
    rfq_res = await db.execute(
        select(Question).where(Question.session_id == session_id)
    )
    questions = list(rfq_res.scalars())

    ans_res = await db.execute(
        select(Answer)
        .join(Question, Question.id == Answer.question_id)
        .where(Question.session_id == session_id)
        .order_by(Answer.version.desc())
    )
    latest_answers: dict[int, Answer] = {}
    for a in ans_res.scalars():
        if a.question_id not in latest_answers:
            latest_answers[a.question_id] = a

    format_rule_res = await db.execute(
        select(FormatRule).where(FormatRule.session_id == session_id)
    )
    format_rule = format_rule_res.scalar_one_or_none()

    rc_res = await db.execute(
        select(QuestionResponseCode).where(
            QuestionResponseCode.session_id == session_id
        )
    )
    response_codes = {r.question_id: r for r in rc_res.scalars()}

    # Clarification count
    from backend.app.models import Clarification
    clarif_res = await db.execute(
        select(Clarification).where(Clarification.session_id == session_id)
    )
    clarifications = list(clarif_res.scalars())

    rfp_analyzed = bool(questions)
    requirements_extracted = bool(questions)
    format_rules_confirmed = bool(format_rule and format_rule.confirmed_by_se)
    response_codes_assigned = bool(response_codes)
    answers_approved = all(
        (latest_answers.get(q.id) and latest_answers[q.id].status == "approved")
        for q in questions
    ) if questions else False
    clarifications_resolved = all(
        (c.status or "").lower() == "resolved" for c in clarifications
    ) if clarifications else True

    # Derived status per item key
    derived = {
        "rfp_uploaded": "done" if rfp_analyzed else "pending",
        "format_rules_confirmed": "done" if format_rules_confirmed else "pending",
        "requirements_extracted": "done" if requirements_extracted else "pending",
        "response_codes_assigned": "done" if response_codes_assigned else "pending",
        "answers_reviewed": "done" if answers_approved else "pending",
        "clarifications_resolved": "done" if clarifications_resolved else "pending",
        "export_generated": "pending",  # only the SE can mark this done via export
    }

    rows = (
        await db.execute(
            select(SubmissionChecklist).where(SubmissionChecklist.session_id == session_id)
        )
    ).scalars().all()
    by_key = {r.item_key: r for r in rows}

    done = pending = 0
    for key, status in derived.items():
        row = by_key.get(key)
        if row is None:
            continue
        if row.status != status:
            row.status = status
            if status == "done":
                row.done_by = "system"
                row.done_at = datetime.now(UTC)
            else:
                row.done_by = None
                row.done_at = None
        if row.status == "done":
            done += 1
        else:
            pending += 1

    await db.commit()
    for row in rows:
        await db.refresh(row)

    pct = round((done / len(rows)) * 100) if rows else 0
    return ChecklistSummary(
        session_id=session_id,
        total=len(rows),
        done=done,
        pending=pending,
        percent=pct,
        items=[SubmissionChecklistOut.model_validate(r) for r in rows],
    )


async def list_checklist(db: AsyncSession, session_id: int) -> ChecklistSummary:
    """Return checklist items (seeds defaults if missing)."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    await _seed_defaults(db, session_id)
    rows = (
        await db.execute(
            select(SubmissionChecklist).where(SubmissionChecklist.session_id == session_id)
        )
    ).scalars().all()
    done = sum(1 for r in rows if r.status == "done")
    pending = len(rows) - done
    pct = round((done / len(rows)) * 100) if rows else 0
    return ChecklistSummary(
        session_id=session_id,
        total=len(rows),
        done=done,
        pending=pending,
        percent=pct,
        items=[SubmissionChecklistOut.model_validate(r) for r in rows],
    )


async def update_checklist_item(
    db: AsyncSession, session_id: int, item_key: str, body
) -> SubmissionChecklistOut:
    """Mark a checklist item done/pending (manual SE override)."""
    result = await db.execute(
        select(SubmissionChecklist).where(
            SubmissionChecklist.session_id == session_id,
            SubmissionChecklist.item_key == item_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"Checklist item {item_key} not found for session {session_id}")

    row.status = body.status
    if body.status == "done":
        row.done_by = body.done_by or "system"
        row.done_at = datetime.now(UTC)
    else:
        row.done_by = None
        row.done_at = None

    await db.commit()
    await db.refresh(row)
    return SubmissionChecklistOut.model_validate(row)
