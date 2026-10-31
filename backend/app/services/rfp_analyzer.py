"""
backend/app/services/rfp_analyzer.py — End-to-end RFP analysis pipeline.

Orchestrates:
1. Loading uploaded RFP file (PDF or DOCX)
2. Extracting document structure and discrete questions
3. Extracting response formatting rules
4. Enforcing triage & department owner routing (Pricing, Legal, Delivery)
5. Persisting Sections, Questions, FormatRules, and summary ChatMessage
"""
import json
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    ChatMessage,
    FormatRule,
    Question,
    RFPDocument,
    Section,
)
from backend.app.models import (
    Session as SessionModel,
)
from backend.app.services.document_parser import extract_text_from_file
from backend.app.services.rfp_extractor import (
    extract_format_rules,
    extract_sections_and_questions,
)

logger = logging.getLogger(__name__)


async def run_rfp_analysis(session_id: int, db: AsyncSession) -> dict[str, Any]:
    """Execute Phase 2 analysis pipeline on the session's uploaded RFP."""
    # 1. Verify session exists
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Get the latest uploaded RFP document
    result = await db.execute(
        select(RFPDocument)
        .where(RFPDocument.session_id == session_id)
        .order_by(RFPDocument.uploaded_at.desc())
        .limit(1)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=400,
            detail="No RFP document uploaded for this session. Please upload a PDF or DOCX file first.",
        )

    # 3. Extract text from the uploaded file
    try:
        _, raw_text = extract_text_from_file(doc.file_path)
    except Exception as exc:
        logger.error("Failed to parse RFP file at %s: %s", doc.file_path, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Could not read uploaded document: {exc}",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=400,
            detail="The uploaded document contains no readable text.",
        )

    # 4. Extract format rules and persist
    rules = extract_format_rules(raw_text)
    format_rule_res = await db.execute(
        select(FormatRule).where(FormatRule.session_id == session_id)
    )
    format_rule = format_rule_res.scalar_one_or_none()
    if format_rule is None:
        format_rule = FormatRule(
            session_id=session_id,
            rules_json=json.dumps(rules),
            confirmed_by_se=False,
        )
        db.add(format_rule)
    else:
        format_rule.rules_json = json.dumps(rules)

    # 5. Extract sections and discrete questions
    sections = extract_sections_and_questions(raw_text)

    # Clear previously extracted questions and sections for this document
    await db.execute(
        delete(Question).where(Question.session_id == session_id)
    )
    await db.execute(
        delete(Section).where(Section.rfp_document_id == doc.id)
    )
    await db.flush()

    total_questions = 0
    mandatory_count = 0
    pricing_count = 0
    legal_count = 0
    delivery_count = 0

    for sec in sections:
        sec_record = Section(
            rfp_document_id=doc.id,
            title=sec.title,
            order_index=sec.order_index,
        )
        db.add(sec_record)
        await db.flush()  # populate sec_record.id

        for q in sec.questions:
            q_record = Question(
                session_id=session_id,
                section_id=sec_record.id,
                number=q.number,
                text=q.text,
                mandatory=q.mandatory,
                kind=q.kind.value,
                category=q.category.value,
                status=q.status.value,
                owner=q.owner.value if q.owner else None,
            )
            db.add(q_record)

            total_questions += 1
            if q.mandatory:
                mandatory_count += 1
            if q.owner:
                if q.owner.value == "Pricing":
                    pricing_count += 1
                elif q.owner.value == "Legal":
                    legal_count += 1
                elif q.owner.value == "Delivery":
                    delivery_count += 1

    # 6. Mark document analyzed
    doc.analyzed = True

    # 7. Post summary message in session chat
    summary_text = (
        f"📋 **RFP Analysis Complete for `{doc.filename}`**\n\n"
        f"- **Sections Extracted:** {len(sections)}\n"
        f"- **Total Questions Identified:** {total_questions} ({mandatory_count} Mandatory)\n"
        f"- **Owner Routing Flagged:**\n"
        f"  - 🏷️ **Pricing (Commercial):** {pricing_count} questions\n"
        f"  - ⚖️ **Legal:** {legal_count} questions\n"
        f"  - 🚚 **Delivery (SLA):** {delivery_count} questions\n"
        f"- **Formatting Constraints:** Word limit: {rules.get('word_limit', 'None')}, "
        f"Naming: `{rules.get('file_naming', 'Standard')}`\n\n"
        f"👉 Review the extracted requirements in the **❓ Questions** tab and verify constraints in **📐 Format Rules**."
    )
    chat_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=summary_text,
    )
    db.add(chat_msg)

    await db.commit()

    return {
        "document": doc.filename,
        "sections": len(sections),
        "total_questions": total_questions,
        "mandatory": mandatory_count,
        "flagged": {
            "pricing": pricing_count,
            "legal": legal_count,
            "delivery": delivery_count,
        },
        "format_rules": rules,
    }
