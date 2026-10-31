"""
services/gap_analysis.py — AI-driven gap analysis.

Compares customer requirements against available product capabilities (derived
from answers, confidence, staleness warnings, and requirement text/category).
Distinguishes a confirmed product gap from a knowledge gap and recommends the
internal team best placed to resolve each gap.
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Answer,
    Gap,
    Question,
    Session as SessionModel,
)
from backend.app.schemas import GapAnalysisOut, GapOut

logger = logging.getLogger(__name__)

GAP_TYPE_LABELS = {
    "functionality": "Functionality Gap",
    "integration": "Integration Dependency",
    "security": "Security Concern",
    "documentation": "Missing Documentation",
}

OWNER_LABELS = {
    "product": "Product Management",
    "engineering": "Engineering",
    "architecture": "Solution Architecture",
}

RECOMMENDATION_RULES = {
    ("security", False): "architecture",
    ("integration", False): "engineering",
    ("documentation", False): "architecture",
    ("functionality", True): "product",
    ("functionality", False): "architecture",
}


def _compute_gaps(questions: list[Question], answers: dict[int, Answer]) -> list[dict]:
    """Derive gap records from questions + latest answers (pure logic, no DB)."""
    gaps: list[dict] = []

    for q in questions:
        a = answers.get(q.id)
        confidence = (a.confidence if a else 0.0) or 0.0
        status = (q.status or "").lower()
        text = (q.text or "").lower()
        category = (q.category or "").lower()
        stale = []
        if a and a.stale_warnings_json:
            try:
                stale = json.loads(a.stale_warnings_json)
            except Exception:
                stale = []

        is_product_gap = (
            "not_supported" in status
            or "low_confidence" in status
            or confidence < 0.45
        )
        is_knowledge_gap = bool(stale) or (
            0.45 <= confidence < 0.75 and "approved" not in status
        )

        is_integration = any(k in text for k in ("third", "api", "integration", "external"))
        is_security = any(
            k in category or k in text
            for k in ("security", "compliance", "shariah")
        )
        is_missing_doc = bool(stale)

        gap_type = None
        if is_security:
            gap_type = "security"
        elif is_integration:
            gap_type = "integration"
        elif is_missing_doc:
            gap_type = "documentation"
        elif is_product_gap or is_knowledge_gap:
            gap_type = "functionality"

        if not gap_type:
            continue

        confirmed_gap = is_product_gap and not is_knowledge_gap
        owner = RECOMMENDATION_RULES.get((gap_type, confirmed_gap), "architecture")

        severity = "Medium"
        if q.mandatory and confidence < 0.45:
            severity = "High"
        if q.mandatory and "approved" not in status:
            severity = "High"

        gaps.append(
            {
                "question_id": q.id,
                "requirement": q.text,
                "number": q.number or q.id,
                "category": q.category,
                "mandatory": bool(q.mandatory),
                "type": gap_type,
                "confirmed_gap": confirmed_gap,
                "severity": severity,
                "owner": owner,
                "confidence": confidence,
                "stale": stale,
                "status": q.status,
            }
        )

    sev_order = {"High": 3, "Medium": 2, "Low": 1}
    gaps.sort(
        key=lambda g: (-sev_order.get(g["severity"], 0), -int(g["mandatory"]))
    )
    return gaps


async def compute_gap_analysis(
    db: AsyncSession, session_id: int
) -> GapAnalysisOut:
    """Run (or refresh) gap analysis for a session and persist results."""
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

    computed = _compute_gaps(questions, latest_answers)

    # Build a question lookup for display fields when constructing GapOut.
    question_by_id: dict[int, Question] = {q.id: q for q in questions}

    # Persist: replace existing gaps for this session (recompute on demand)
    existing = (
        await db.execute(select(Gap).where(Gap.session_id == session_id))
    ).scalars().all()
    for g in existing:
        await db.delete(g)

    gap_rows: list[Gap] = []
    high = confirmed = knowledge = 0
    for c in computed:
        row = Gap(
            session_id=session_id,
            question_id=c["question_id"],
            gap_type=c["type"],
            confirmed_gap=c["confirmed_gap"],
            severity=c["severity"],
            recommended_owner=c["owner"],
            details=c.get("details", ""),
        )
        gap_rows.append(row)
        db.add(row)
        if c["severity"] == "High":
            high += 1
        if c["confirmed_gap"]:
            confirmed += 1
        else:
            knowledge += 1

    # Flush so generated IDs are available before building the response.
    await db.flush()

    gap_outs: list[GapOut] = []
    for row, c in zip(gap_rows, computed):
        q = question_by_id.get(c["question_id"])
        gap_outs.append(
            GapOut(
                id=row.id,
                session_id=session_id,
                question_id=c["question_id"],
                number=c.get("number", ""),
                requirement=c.get("requirement", ""),
                category=q.category if q else c.get("category"),
                mandatory=bool(q.mandatory) if q else bool(c.get("mandatory")),
                gap_type=c["type"],
                confirmed_gap=c["confirmed_gap"],
                severity=c["severity"],
                recommended_owner=c["owner"],
                details=c.get("details", ""),
                confidence=c.get("confidence", 0.0),
                status=q.status if q else c.get("status", ""),
                created_at=row.created_at,
            )
        )

    await db.commit()
    for row in gap_rows:
        await db.refresh(row)

    return GapAnalysisOut(
        session_id=session_id,
        total=len(gap_outs),
        high_severity=high,
        confirmed_gaps=confirmed,
        knowledge_gaps=knowledge,
        gaps=gap_outs,
    )


async def list_gaps(db: AsyncSession, session_id: int) -> GapAnalysisOut:
    """Return previously computed gaps (recomputes if none exist)."""
    result = await db.execute(
        select(Gap).where(Gap.session_id == session_id)
    )
    gaps = list(result.scalars())
    if not gaps:
        return await compute_gap_analysis(db, session_id)

    # Join with questions for display fields.
    q_res = await db.execute(
        select(Question).where(Question.session_id == session_id)
    )
    questions = {q.id: q for q in q_res.scalars()}

    high = confirmed = knowledge = 0
    gap_outs: list[GapOut] = []
    for g in gaps:
        q = questions.get(g.question_id)
        gap_outs.append(
            GapOut(
                id=g.id,
                session_id=g.session_id,
                question_id=g.question_id,
                number=q.number if q else "",
                requirement=q.text if q else "",
                category=q.category if q else None,
                mandatory=bool(q.mandatory) if q else False,
                gap_type=g.gap_type,
                confirmed_gap=g.confirmed_gap,
                severity=g.severity,
                recommended_owner=g.recommended_owner,
                details=g.details,
                confidence=0.0,
                status=q.status if q else "",
                created_at=g.created_at,
            )
        )
        if g.severity == "High":
            high += 1
        if g.confirmed_gap:
            confirmed += 1
        else:
            knowledge += 1

    return GapAnalysisOut(
        session_id=session_id,
        total=len(gap_outs),
        high_severity=high,
        confirmed_gaps=confirmed,
        knowledge_gaps=knowledge,
        gaps=gap_outs,
    )
