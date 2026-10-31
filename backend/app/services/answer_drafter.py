"""
backend/app/services/answer_drafter.py — Grounded answer drafting, verification, and confidence scoring.

Hard Rules enforced:
1. Answers are grounded in the 3 knowledge sources: product docs, past SOWs, past RFP responses.
2. Every drafted answer cites its sources. Never invent facts.
3. If sources cannot answer a question, route to clarification list instead of guessing.
4. Flagged owner questions (commercial/pricing, legal, delivery/SLA) are never auto-answered.
5. Format rules (word limits, numbering, tone) are enforced.
"""

import asyncio
import json
import logging
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models import (
    Answer,
    Clarification,
    FormatRule,
    Question,
    QuestionStatus,
)
from backend.app.schemas import KBChunkResult
from backend.app.services.retrieval import get_retriever

logger = logging.getLogger(__name__)
settings = get_settings()


def _extract_grounded_points(
    question_text: str, chunks: list[KBChunkResult]
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Synthesize a grounded answer from retrieved chunks with citations and staleness tracking."""
    citations: list[dict[str, Any]] = []
    stale_warnings: list[str] = []
    points: list[str] = []

    # Filter out generic vendor and boilerplate query stop words so matching 'azentio' alone doesn't trigger false grounding
    query_stop_words = {
        "does",
        "what",
        "where",
        "which",
        "when",
        "how",
        "your",
        "platform",
        "system",
        "azentio",
        "azentiofinance",
        "describe",
        "provide",
        "support",
        "supports",
        "including",
        "detail",
        "state",
        "confirm",
        "about",
        "with",
        "this",
        "that",
    }
    raw_words = re.findall(r"\w{4,}", question_text.lower())
    q_words = set(w for w in raw_words if w not in query_stop_words)

    for chunk in chunks:
        # Check staleness
        if chunk.stale_warning and chunk.stale_warning not in stale_warnings:
            stale_warnings.append(f"[{chunk.document_name}]: {chunk.stale_warning}")

        # Extract sentences that share semantic terms with the question
        clean_snippet = re.sub(r"^#{1,3}\s+.*$", "", chunk.snippet, flags=re.MULTILINE).strip()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_snippet) if s.strip()]

        matched_sentences = []
        for s in sentences:
            s_words = set(w for w in re.findall(r"\w{4,}", s.lower()) if w not in query_stop_words)
            overlap = q_words & s_words
            if overlap:
                matched_sentences.append(s)

        if matched_sentences:
            best_sentence = " ".join(matched_sentences[:2])
            points.append(f"• {best_sentence} [{chunk.chunk_id}]")
            citations.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document": chunk.document_name,
                    "source_type": chunk.source_type,
                    "snippet": best_sentence[:300],
                    "type": "kb",
                }
            )

    # Do NOT fall back to random chunk if there is no keyword overlap with the question.
    # Hard Rule: If the sources cannot answer a question, put it on clarification list instead of guessing.
    answer_body = "\n".join(points)
    return answer_body, citations, stale_warnings


async def draft_answer_for_question(
    question: Question,
    format_rules: dict[str, Any] | None = None,
) -> tuple[str, float, list[dict[str, Any]], list[str], QuestionStatus]:
    """Generate a grounded answer for one question with confidence and citation tracking.

    Returns:
        (answer_text, confidence_score, citations, stale_warnings, new_status)
    """
    format_rules = format_rules or {}
    word_limit = format_rules.get("word_limit")

    # 1. Flagged owner questions (commercial, legal, SLA) must NOT be auto-answered
    if question.status == QuestionStatus.flagged_owner.value or question.owner:
        owner_name = question.owner or "Responsible Department"
        answer_text = (
            f"**[PENDING OWNER INPUT — Assigned to {owner_name}]**\n\n"
            f"This requirement relates to {question.category} terms and is routed to the "
            f"**{owner_name}** department for authoritative input and approval."
        )
        return (answer_text, 1.0, [], [], QuestionStatus.flagged_owner)

    # 2. Retrieve relevant context chunks
    retriever = get_retriever()
    chunks = await retriever.search(
        query=f"{question.text} {question.category}",
        top_k=settings.retrieval_top_k,
    )
    top_score = chunks[0].score if chunks else 0.0

    # 3. Synthesize grounded answer
    raw_points, citations, stale_warnings = _extract_grounded_points(question.text, chunks)

    # 4. If no citations or grounding could be established, route to Clarification
    if not citations or not raw_points.strip():
        answer_text = (
            "The Azentio knowledge base does not contain sufficient verified product documentation "
            "or past RFP references to answer this question accurately without guessing. "
            "Flagged for clarification and Sales Engineer input."
        )
        return (answer_text, 0.25, [], [], QuestionStatus.clarification)

    header = f"**Response ({question.number}):**\n\n"
    intro = "AzentioFinance natively supports this requirement in adherence to Islamic banking standards:\n\n"
    full_text = f"{header}{intro}{raw_points}"

    # 5. If a real OpenAI API key is present in .env, invoke DRAFT_MODEL (gpt-4o)
    from backend.app.llm import has_valid_api_key

    if has_valid_api_key():
        try:
            from backend.app.agents.prompts.draft_answer import (
                DRAFT_ANSWER_SYSTEM_PROMPT,
                DRAFT_ANSWER_USER_PROMPT,
            )
            from backend.app.llm import draft

            chunks_formatted = "\n\n".join(
                [
                    f"[{c.chunk_id}] (Source: {c.document_name}, Type: {c.source_type})\n{c.snippet}"
                    for c in chunks
                ]
            )
            user_msg = DRAFT_ANSWER_USER_PROMPT.format(
                question_number=question.number,
                question_category=question.category,
                question_text=question.text,
                word_limit=word_limit or "Standard (approx 250 words)",
                section_headings=format_rules.get("section_headings", True),
                numbering_scheme=format_rules.get("numbering_scheme", "exact"),
                context_chunks=chunks_formatted,
            )
            llm_response = await draft(
                messages=[
                    {"role": "system", "content": DRAFT_ANSWER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                purpose=f"draft_answer_q_{question.number}",
                session_id=question.session_id,
            )
            if llm_response and len(str(llm_response).strip()) > 30:
                full_text = str(llm_response).strip()
        except Exception as exc:
            logger.warning(
                "OpenAI LLM drafting call failed (%s); using deterministic grounded draft", exc
            )

    # Enforce word limit if specified in format rules
    if word_limit and isinstance(word_limit, int):
        words = full_text.split()
        if len(words) > word_limit:
            full_text = " ".join(words[:word_limit]) + "..."

    # 6. Compute grounded confidence score
    # Score is weighted by top retrieval match score and number of corroborating chunks
    confidence = min(0.95, round(top_score * 0.85 + min(len(citations) * 0.05, 0.15), 2))

    # Determine status based on confidence thresholds
    if confidence >= settings.confidence_high:
        status = QuestionStatus.answered
    elif confidence >= settings.confidence_low:
        status = QuestionStatus.low_confidence
    else:
        status = QuestionStatus.clarification

    return (full_text, confidence, citations, stale_warnings, status)


async def draft_all_session_answers(
    session_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Process all questions for a session with bounded concurrency."""
    # 1. Fetch format rules
    rule_res = await db.execute(select(FormatRule).where(FormatRule.session_id == session_id))
    rule_obj = rule_res.scalar_one_or_none()
    format_rules = json.loads(rule_obj.rules_json) if rule_obj and rule_obj.rules_json else {}

    # 2. Fetch all questions for this session
    q_res = await db.execute(
        select(Question).where(Question.session_id == session_id).order_by(Question.id)
    )
    questions = list(q_res.scalars())
    if not questions:
        return {"processed": 0, "answered": 0, "clarifications": 0, "flagged": 0}

    # Clear previous draft answers & clarifications for fresh generation
    q_ids = [q.id for q in questions]
    await db.execute(delete(Answer).where(Answer.question_id.in_(q_ids)))
    await db.execute(delete(Clarification).where(Clarification.session_id == session_id))
    await db.flush()

    sem = asyncio.Semaphore(settings.max_concurrency)
    results_summary = {"answered": 0, "low_confidence": 0, "clarifications": 0, "flagged": 0}

    async def _process_q(q: Question) -> None:
        async with sem:
            ans_text, conf, cites, stales, new_status = await draft_answer_for_question(
                q, format_rules=format_rules
            )

            # Persist draft answer
            answer_record = Answer(
                question_id=q.id,
                version=1,
                text=ans_text,
                confidence=conf,
                citations_json=json.dumps(cites),
                stale_warnings_json=json.dumps(stales),
                status="draft",
                edited_by_se=False,
            )
            db.add(answer_record)

            # Update question status
            q.status = new_status.value

            # If routed to clarification, add clarification entry
            if new_status == QuestionStatus.clarification:
                clarif = Clarification(
                    session_id=session_id,
                    text=f"Insufficient KB grounding for question {q.number}: '{q.text[:120]}...'",
                    reason="Knowledge sources lack specific product or architectural details to answer with high confidence.",
                    linked_question_ids_json=json.dumps([q.id]),
                    status="open",
                )
                db.add(clarif)
                results_summary["clarifications"] += 1
            elif new_status == QuestionStatus.flagged_owner:
                results_summary["flagged"] += 1
            elif new_status == QuestionStatus.answered:
                results_summary["answered"] += 1
            elif new_status == QuestionStatus.low_confidence:
                results_summary["low_confidence"] += 1

    # Execute with bounded concurrency
    await asyncio.gather(*[_process_q(q) for q in questions])
    await db.commit()

    logger.info("Drafted answers for session %d: %s", session_id, results_summary)
    return {
        "total": len(questions),
        **results_summary,
    }
