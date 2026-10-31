"""
services/validation.py — Intelligent response validation.

Cross-checks drafted answers against source-derived signals (confidence,
staleness warnings, approval status, mandatory flag) and cross-requirement
consistency to surface unsupported claims, outdated info, contradictions, and
missing mandatory responses.
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Answer,
    Question,
    ValidationIssue,
    Session as SessionModel,
)
from backend.app.schemas import ValidationIssueOut, ValidationOut

logger = logging.getLogger(__name__)

ISSUE_LABELS = {
    "unsupported_claim": "Unsupported Claim",
    "outdated_info": "Outdated Information",
    "contradiction": "Contradiction",
    "missing_mandatory": "Missing Mandatory Response",
    "low_confidence": "Not Yet Approved",
}

SEV_ORDER = {"High": 3, "Medium": 2, "Low": 1}


def _parse_json_field(val) -> list:
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except Exception:
        return []


def _compute_issues(
    questions: list[Question], answers: dict[int, Answer]
) -> list[dict]:
    """Derive validation issues from questions + latest answers (pure logic)."""
    issues: list[dict] = []
    answers_by_text: dict[str, list[Question]] = {}

    for q in questions:
        a = answers.get(q.id)
        if not a:
            if q.mandatory:
                issues.append(
                    {
                        "question_id": q.id,
                        "requirement": q.text,
                        "number": q.number or q.id,
                        "issue_type": "missing_mandatory",
                        "detail": "Mandatory requirement has no drafted answer yet.",
                        "severity": "High",
                    }
                )
            continue

        confidence = (a.confidence or 0.0) or 0.0
        stale = _parse_json_field(a.stale_warnings_json)
        status = (a.status or "").lower()
        text = (a.text or "").strip()

        # Low confidence / potentially unsupported claim
        if confidence < 0.45:
            issues.append(
                {
                    "question_id": q.id,
                    "requirement": q.text,
                    "number": q.number or q.id,
                    "issue_type": "unsupported_claim",
                    "detail": (
                        f"Low confidence answer ({(confidence * 100):.0f}%) — "
                        "may be unsupported by source documentation."
                    ),
                    "severity": "High" if confidence < 0.3 else "Medium",
                }
            )

        # Stale / outdated information
        for i, w in enumerate(stale):
            issues.append(
                {
                    "question_id": q.id,
                    "requirement": q.text,
                    "number": q.number or q.id,
                    "issue_type": "outdated_info",
                    "detail": (
                        w if isinstance(w, str) else "Source information may be outdated."
                    ),
                    "severity": "Medium",
                }
            )

        # Not yet approved
        if "approved" not in status:
            issues.append(
                {
                    "question_id": q.id,
                    "requirement": q.text,
                    "number": q.number or q.id,
                    "issue_type": "low_confidence",
                    "detail": "Answer not yet approved — review before submission.",
                    "severity": "Low",
                }
            )

        # Track answer text for contradiction detection
        if text:
            answers_by_text.setdefault(text, []).append(q)

    # Contradiction detection: identical answers across different requirements
    for text, qs in answers_by_text.items():
        if len(qs) > 1:
            others = ", ".join(
                str(x.number or x.id)
                for x in qs
            )
            for q in qs:
                others_except = ", ".join(
                    str(x.number or x.id)
                    for x in qs
                    if str(x.number or x.id) != str(q.number or q.id)
                )
                if others_except:
                    issues.append(
                        {
                            "question_id": q.id,
                            "requirement": q.text,
                            "number": q.number or q.id,
                            "issue_type": "contradiction",
                            "detail": (
                                f"Identical response used for multiple requirements "
                                f"(shared with req {others_except}) — verify it fits "
                                "each requirement."
                            ),
                            "severity": "Medium",
                        }
                    )

    issues.sort(key=lambda i: -SEV_ORDER.get(i["severity"], 0))
    return issues


async def compute_validation(
    db: AsyncSession, session_id: int
) -> ValidationOut:
    """Run (or refresh) response validation for a session and persist results."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    q_res = await db.execute(
        select(Question).where(Question.session_id == session_id).order_by(Question.id)
    )
    questions = list(q_res.scalars())

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

    computed = _compute_issues(questions, latest_answers)

    # Build a question lookup for display fields.
    question_by_id: dict[int, Question] = {q.id: q for q in questions}

    # Replace existing validation issues for this session
    existing = (
        await db.execute(select(ValidationIssue).where(ValidationIssue.session_id == session_id))
    ).scalars().all()
    for v in existing:
        await db.delete(v)

    issue_rows: list[ValidationIssue] = []
    high = medium = 0
    for c in computed:
        row = ValidationIssue(
            session_id=session_id,
            question_id=c["question_id"],
            issue_type=c["issue_type"],
            detail=c["detail"],
            severity=c["severity"],
        )
        issue_rows.append(row)
        db.add(row)
        if c["severity"] == "High":
            high += 1
        elif c["severity"] == "Medium":
            medium += 1

    # Flush so generated IDs are available before building the response.
    await db.flush()

    issue_outs: list[ValidationIssueOut] = []
    for row, c in zip(issue_rows, computed):
        q = question_by_id.get(c["question_id"])
        issue_outs.append(
            ValidationIssueOut(
                id=row.id,
                session_id=session_id,
                question_id=c["question_id"],
                number=c.get("number", ""),
                requirement=q.text if q else c.get("requirement", ""),
                issue_type=c["issue_type"],
                detail=c["detail"],
                severity=c["severity"],
                resolved=False,
                created_at=row.created_at,
            )
        )

    await db.commit()
    for row in issue_rows:
        await db.refresh(row)

    return ValidationOut(
        session_id=session_id,
        total=len(issue_outs),
        high_severity=high,
        medium_severity=medium,
        issues=issue_outs,
    )


async def list_validation_issues(db: AsyncSession, session_id: int) -> ValidationOut:
    """Return previously computed issues (recomputes if none exist)."""
    result = await db.execute(
        select(ValidationIssue).where(ValidationIssue.session_id == session_id)
    )
    issues = list(result.scalars())
    if not issues:
        return await compute_validation(db, session_id)

    # Join with questions for display fields.
    q_res = await db.execute(
        select(Question).where(Question.session_id == session_id)
    )
    questions = {q.id: q for q in q_res.scalars()}

    high = medium = 0
    issue_outs: list[ValidationIssueOut] = []
    for i in issues:
        q = questions.get(i.question_id)
        issue_outs.append(
            ValidationIssueOut(
                id=i.id,
                session_id=i.session_id,
                question_id=i.question_id,
                number=q.number if q else "",
                requirement=q.text if q else "",
                issue_type=i.issue_type,
                detail=i.detail,
                severity=i.severity,
                resolved=i.resolved,
                created_at=i.created_at,
            )
        )
        if i.severity == "High":
            high += 1
        elif i.severity == "Medium":
            medium += 1

    return ValidationOut(
        session_id=session_id,
        total=len(issue_outs),
        high_severity=high,
        medium_severity=medium,
        issues=issue_outs,
    )
