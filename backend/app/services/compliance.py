"""
services/compliance.py — Response codes (S/C/D/T/N) and compliance matrix.

Business logic for Level 2: Intelligent Compliance Matrix.
- Upsert / retrieve per-question response codes.
- Compute a requirement-by-requirement compliance matrix with compliance status
  and colour hints derived from answer confidence, approval status, and code.
"""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Answer,
    Question,
    QuestionResponseCode,
    Session as SessionModel,
)
from backend.app.schemas import (
    ComplianceMatrixOut,
    ComplianceMatrixRow,
    QuestionResponseCodeOut,
    QuestionResponseCodePut,
)

logger = logging.getLogger(__name__)

CODE_LABELS = {
    "S": "Standard capability",
    "C": "Configuration required",
    "D": "Development required",
    "T": "Third-party dependency",
    "N": "Not available",
}

# Codes that require a supporting explanation / estimate / attachment.
CODE_REQUIRES_EXPLANATION = {"C", "D", "T", "N"}


def _compliance_status(
    code: str | None,
    confidence: float,
    is_approved: bool,
    has_owner: bool,
    mandatory: bool,
) -> tuple[str, str]:
    """Return (compliance_label, css-style class) for a matrix row."""
    if is_approved:
        return "Compliant (Approved)", "text-green-700"
    if code == "N":
        return "Not Available", "text-red-600"
    if code in ("D", "T"):
        return "Gap — Action Required", "text-amber-700"
    if code == "C":
        return "Configuration Needed", "text-blue-600"
    if code == "S" and confidence >= 0.75:
        return "Compliant (Standard)", "text-green-600"
    if code == "S":
        return "Compliant (Draft)", "text-blue-600"
    if not code:
        return "Code Not Set", "text-gray-500"
    return "Pending Review", "text-gray-600"


async def _get_question(db: AsyncSession, question_id: int) -> Question | None:
    result = await db.execute(select(Question).where(Question.id == question_id))
    return result.scalar_one_or_none()


async def get_or_create_response_code(
    db: AsyncSession, session_id: int, question_id: int
) -> QuestionResponseCode:
    """Fetch the response code for a question, creating a default 'S' row if absent."""
    result = await db.execute(
        select(QuestionResponseCode).where(
            QuestionResponseCode.question_id == question_id
        )
    )
    code = result.scalar_one_or_none()
    if code is None:
        q = await _get_question(db, question_id)
        if q is None or q.session_id != session_id:
            raise ValueError(f"Question {question_id} not found in session {session_id}")
        code = QuestionResponseCode(
            session_id=session_id,
            question_id=question_id,
            code="S",
            explanation="",
            requires_explanation=False,
        )
        db.add(code)
        await db.flush()
    return code


async def set_response_code(
    db: AsyncSession, session_id: int, question_id: int, body: QuestionResponseCodePut
) -> QuestionResponseCodeOut:
    """Upsert a response code for a requirement."""
    q = await _get_question(db, question_id)
    if q is None or q.session_id != session_id:
        raise ValueError(f"Question {question_id} not found in session {session_id}")

    code_str = (body.code or "S").strip().upper()
    if code_str not in CODE_LABELS:
        code_str = "S"

    result = await db.execute(
        select(QuestionResponseCode).where(
            QuestionResponseCode.question_id == question_id
        )
    )
    row = result.scalar_one_or_none()
    requires_exp = code_str in CODE_REQUIRES_EXPLANATION
    explanation = body.explanation or ""

    if row is None:
        row = QuestionResponseCode(
            session_id=session_id,
            question_id=question_id,
            code=code_str,
            explanation=explanation,
            estimate=body.estimate,
            attachment_ref=body.attachment_ref,
            validated_by_se=bool(body.validated_by_se),
            requires_explanation=requires_exp,
        )
        db.add(row)
    else:
        row.code = code_str
        row.explanation = explanation
        row.estimate = body.estimate
        row.attachment_ref = body.attachment_ref
        row.validated_by_se = bool(body.validated_by_se)
        row.requires_explanation = requires_exp

    await db.commit()
    await db.refresh(row)
    return QuestionResponseCodeOut.model_validate(row)


async def list_response_codes(
    db: AsyncSession, session_id: int
) -> list[QuestionResponseCodeOut]:
    result = await db.execute(
        select(QuestionResponseCode).where(
            QuestionResponseCode.session_id == session_id
        )
    )
    return [QuestionResponseCodeOut.model_validate(r) for r in result.scalars()]


async def compute_compliance_matrix(
    db: AsyncSession, session_id: int
) -> ComplianceMatrixOut:
    """Build the full compliance matrix for a session."""
    # Verify session exists
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    q_res = await db.execute(
        select(Question).where(Question.session_id == session_id).order_by(Question.id)
    )
    questions = list(q_res.scalars())

    # Latest answer per question
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

    # Response codes per question
    rc_res = await db.execute(
        select(QuestionResponseCode).where(
            QuestionResponseCode.session_id == session_id
        )
    )
    codes_by_q: dict[int, QuestionResponseCode] = {
        r.question_id: r for r in rc_res.scalars()
    }

    rows: list[ComplianceMatrixRow] = []
    coded = 0
    flagged = 0
    not_available = 0

    for q in questions:
        ans = latest_answers.get(q.id)
        confidence = (ans.confidence if ans else 0.0) or 0.0
        is_approved = ans is not None and ans.status == "approved"
        code_row = codes_by_q.get(q.id)
        code = code_row.code if code_row else ""
        explanation = code_row.explanation if code_row else None

        compliance, compliance_class = _compliance_status(
            code, confidence, is_approved, bool(q.owner), bool(q.mandatory)
        )

        if code:
            coded += 1
        if code == "N":
            not_available += 1
        if compliance in ("Gap — Action Required", "Code Not Set") or (
            code in CODE_REQUIRES_EXPLANATION and not explanation
        ):
            flagged += 1

        rows.append(
            ComplianceMatrixRow(
                question_id=q.id,
                number=q.number,
                text=q.text,
                category=q.category,
                mandatory=bool(q.mandatory),
                status=q.status,
                owner=q.owner,
                code=code,
                code_label=CODE_LABELS.get(code, "—"),
                confidence=confidence,
                explanation=explanation,
                requires_explanation=bool(
                    code_row and code_row.requires_explanation
                ),
                compliance=compliance,
                compliance_class=compliance_class,
            )
        )

    return ComplianceMatrixOut(
        session_id=session_id,
        total=len(questions),
        coded=coded,
        flagged=flagged,
        not_available=not_available,
        rows=rows,
    )
