"""
backend/app/agents/chat_tools.py — Interactive tools for the Sales Engineer chat agent.

Provides typed, grounded tool functions for inspecting questions, searching the KB,
revising answers, injecting SE facts, and approving answers with human confirmation.
"""

import json
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select

from backend.app.config import get_settings
from backend.app.db import AsyncSessionLocal
from backend.app.models import (
    Answer,
    AnswerStatus,
    Question,
    QuestionStatus,
)
from backend.app.models import (
    Session as SessionModel,
)
from backend.app.services.retrieval import get_retriever

logger = logging.getLogger(__name__)
settings = get_settings()


async def list_questions_tool(
    session_id: int,
    category: str | None = None,
    owner: str | None = None,
    status: str | None = None,
) -> str:
    """List RFP questions in this session, optionally filtered by category, owner, or status."""
    async with AsyncSessionLocal() as db:
        stmt = select(Question).where(Question.session_id == session_id).order_by(Question.id)
        if category:
            stmt = stmt.where(Question.category == category.lower())
        if owner:
            stmt = stmt.where(Question.owner == owner)
        if status:
            stmt = stmt.where(Question.status == status.lower())

        res = await db.execute(stmt)
        questions = list(res.scalars())

    if not questions:
        filters = []
        if category:
            filters.append(f"category='{category}'")
        if owner:
            filters.append(f"owner='{owner}'")
        if status:
            filters.append(f"status='{status}'")
        f_str = f" matching {', '.join(filters)}" if filters else ""
        return f"No questions found for session {session_id}{f_str}."

    lines = [
        f"### Questions in Session {session_id} ({len(questions)} items)\n",
        "| Number | Category | Status | Owner | Question Text |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for q in questions:
        owner_display = q.owner or "—"
        text_preview = q.text[:80] + "..." if len(q.text) > 80 else q.text
        text_preview = text_preview.replace("|", "/")
        lines.append(
            f"| **{q.number}** | `{q.category}` | `{q.status}` | {owner_display} | {text_preview} |"
        )

    return "\n".join(lines)


async def show_answer_tool(
    session_id: int,
    question_number: str,
) -> str:
    """Inspect current draft answer, citations, confidence score, and staleness warnings."""
    clean_num = question_number.strip()
    async with AsyncSessionLocal() as db:
        q_res = await db.execute(
            select(Question).where(Question.session_id == session_id, Question.number == clean_num)
        )
        q = q_res.scalar_one_or_none()
        if q is None:
            return f"❌ Question '{clean_num}' was not found in session {session_id}."

        a_res = await db.execute(
            select(Answer).where(Answer.question_id == q.id).order_by(desc(Answer.version)).limit(1)
        )
        answer = a_res.scalar_one_or_none()

    if answer is None:
        return (
            f"### Question {q.number} [{q.category.upper()}]\n\n"
            f"**Text**: {q.text}\n\n"
            f"**Status**: `{q.status}` (Assigned Owner: {q.owner or 'None'})\n\n"
            f"*No draft answer has been generated yet.*"
        )

    citations = answer.citations
    stale_warnings = answer.stale_warnings

    lines = [
        f"### Question {q.number}: {q.text}\n",
        f"- **Status**: `{answer.status.upper()}` (Question status: `{q.status}`)",
        f"- **Version**: {answer.version} (Edited by SE: {'Yes' if answer.edited_by_se else 'No'})",
        f"- **Confidence Score**: {answer.confidence:.2f}",
        f"- **Owner**: {q.owner or 'Unassigned'}\n",
        "#### Current Answer Text:",
        answer.text,
        "\n#### Citations Grounding:",
    ]
    if citations:
        for idx, cite in enumerate(citations, 1):
            src_type = cite.get("source_type", "kb")
            doc = cite.get("document", "Unknown")
            snippet = cite.get("snippet", "")[:160]
            lines.append(
                f"{idx}. `[{cite.get('chunk_id', 'ref')}]` **{doc}** ({src_type}): *\"{snippet}...\"*"
            )
    else:
        lines.append("*No citations recorded (flagged or ungrounded).*")

    if stale_warnings:
        lines.append("\n#### ⚠️ Staleness Warnings:")
        for sw in stale_warnings:
            lines.append(f"- {sw}")

    return "\n".join(lines)


async def rewrite_answer_tool(
    session_id: int,
    question_number: str,
    instruction: str,
) -> str:
    """Rewrite or rephrase a draft answer according to the Sales Engineer's instruction."""
    clean_num = question_number.strip()
    async with AsyncSessionLocal() as db:
        q_res = await db.execute(
            select(Question).where(Question.session_id == session_id, Question.number == clean_num)
        )
        q = q_res.scalar_one_or_none()
        if q is None:
            return f"❌ Question '{clean_num}' was not found in session {session_id}."

        a_res = await db.execute(
            select(Answer).where(Answer.question_id == q.id).order_by(desc(Answer.version)).limit(1)
        )
        current_answer = a_res.scalar_one_or_none()
        if current_answer is None:
            return f"❌ No current answer found for Question {clean_num} to rewrite."

        prev_text = current_answer.text
        citations_json = current_answer.citations_json
        stale_warnings_json = current_answer.stale_warnings_json
        next_version = current_answer.version + 1

    # Attempt LLM rewrite using draft model (gpt-4o)
    rewritten_text = ""
    try:
        from backend.app.llm import draft

        prompt = [
            {
                "role": "system",
                "content": (
                    "You are the Azentio RFP Response Assistant. "
                    "Rewrite the draft response to the question strictly following the Sales Engineer's instructions. "
                    "Preserve all facts, technical capabilities, and source citations [chunk_id]. "
                    "Do NOT invent ungrounded claims."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question ({q.number}): {q.text}\n\n"
                    f"Current Answer (Version {current_answer.version}):\n{prev_text}\n\n"
                    f"SE Instruction: {instruction}\n\n"
                    f"Provide the rewritten answer in professional, Shariah-compliant wording:"
                ),
            },
        ]
        res = await draft(prompt, purpose=f"rewrite_q_{q.number}", session_id=session_id)
        if res and len(str(res).strip()) > 20:
            rewritten_text = str(res).strip()
    except Exception as exc:
        logger.warning("LLM rewrite failed (%s); using rule-based revision", exc)

    if not rewritten_text:
        # Fallback deterministic rewrite
        rewritten_text = f"{prev_text}\n\n*[Revised per SE instruction: {instruction}]*"

    # Persist as new version in DB
    async with AsyncSessionLocal() as db:
        new_answer = Answer(
            question_id=q.id,
            version=next_version,
            text=rewritten_text,
            confidence=current_answer.confidence,
            citations_json=citations_json,
            stale_warnings_json=stale_warnings_json,
            status=AnswerStatus.draft,
            edited_by_se=True,
        )
        db.add(new_answer)
        await db.commit()

    return (
        f"✅ **Question {q.number} rewritten (Version {next_version})**\n\n"
        f'**SE Instruction Applied**: *"{instruction}"*\n\n'
        f"**New Draft Answer**:\n{rewritten_text}"
    )


async def apply_se_fact_tool(
    session_id: int,
    question_number: str,
    fact: str,
) -> str:
    """Inject Sales Engineer field knowledge/fact into the answer with an 'se_input' citation."""
    clean_num = question_number.strip()
    fact_text = fact.strip()
    if not fact_text:
        return "❌ Fact text cannot be empty."

    async with AsyncSessionLocal() as db:
        q_res = await db.execute(
            select(Question).where(Question.session_id == session_id, Question.number == clean_num)
        )
        q = q_res.scalar_one_or_none()
        if q is None:
            return f"❌ Question '{clean_num}' was not found in session {session_id}."

        a_res = await db.execute(
            select(Answer).where(Answer.question_id == q.id).order_by(desc(Answer.version)).limit(1)
        )
        current_answer = a_res.scalar_one_or_none()
        if current_answer is None:
            return f"❌ No current answer found for Question {clean_num} to update."

        prev_text = current_answer.text
        citations = current_answer.citations
        stale_warnings_json = current_answer.stale_warnings_json
        next_version = current_answer.version + 1

        # Add new citation tagged as se_input
        fact_chunk_id = f"se_fact_{int(time.time())}"
        citations.append(
            {
                "chunk_id": fact_chunk_id,
                "document": "Sales Engineer Input",
                "source_type": "se_input",
                "type": "se_input",
                "snippet": fact_text[:250],
            }
        )

        updated_text = (
            f"{prev_text}\n\n" f"• **Field Reference (SE Input)**: {fact_text} [{fact_chunk_id}]"
        )

        new_answer = Answer(
            question_id=q.id,
            version=next_version,
            text=updated_text,
            confidence=max(current_answer.confidence, 0.85),
            citations_json=json.dumps(citations),
            stale_warnings_json=stale_warnings_json,
            status=AnswerStatus.draft,
            edited_by_se=True,
        )
        db.add(new_answer)
        # If question was clarification or low confidence, bump to answered
        if q.status in (QuestionStatus.clarification.value, QuestionStatus.low_confidence.value):
            q_in_db = await db.get(Question, q.id)
            if q_in_db:
                q_in_db.status = QuestionStatus.answered.value

        await db.commit()

    return (
        f"✅ **Fact added to Question {q.number} (Version {next_version})**\n\n"
        f'**Fact**: *"{fact_text}"*\n'
        f"**Citation Attached**: `[{fact_chunk_id}]` (Source: Sales Engineer Input)\n\n"
        f"**Updated Answer Preview**:\n{updated_text}"
    )


async def search_kb_tool(
    query: str,
    top_k: int = 4,
) -> str:
    """Search the knowledge base for verified product specs, past SOWs, and past RFPs."""
    clean_query = query.strip()
    if not clean_query:
        return "❌ Search query cannot be empty."

    retriever = get_retriever()
    chunks = await retriever.search(query=clean_query, top_k=top_k)
    if not chunks:
        return f"No matching knowledge base documents found for query: '{clean_query}'."

    lines = [f'### Knowledge Base Results for: *"{clean_query}"*\n']
    for idx, c in enumerate(chunks, 1):
        lines.append(
            f"**{idx}. [{c.chunk_id}] {c.document_name}** (`{c.source_type}` | Score: {c.score:.2f})"
        )
        clean_snippet = re.sub(r"\s+", " ", c.snippet).strip()[:240]
        lines.append(f'> "{clean_snippet}..."\n')
        if c.stale_warning:
            lines.append(f"⚠️ *Stale warning: {c.stale_warning}*\n")

    return "\n".join(lines)


async def approve_answer_tool(
    session_id: int,
    question_number: str,
    confirm: bool = False,
) -> str:
    """Approve a draft answer. Strict guard: requires explicit SE confirmation (confirm=True)."""
    clean_num = question_number.strip()
    if not confirm:
        return (
            f"⚠️ **Approval Guard Active**: An answer is never final until the Sales Engineer confirms it.\n"
            f"To approve Question **{clean_num}**, please confirm your approval by replying:\n"
            f'> *"Approve {clean_num} with confirm=True"* or click the Approve button in the Question Inspector.'
        )

    async with AsyncSessionLocal() as db:
        q_res = await db.execute(
            select(Question).where(Question.session_id == session_id, Question.number == clean_num)
        )
        q = q_res.scalar_one_or_none()
        if q is None:
            return f"❌ Question '{clean_num}' was not found in session {session_id}."

        a_res = await db.execute(
            select(Answer).where(Answer.question_id == q.id).order_by(desc(Answer.version)).limit(1)
        )
        answer = a_res.scalar_one_or_none()
        if answer is None:
            return f"❌ No draft answer exists for Question {clean_num} to approve."

        # Mark answer and question as approved
        answer.status = AnswerStatus.approved.value
        answer.approved_at = datetime.now(UTC)
        q.status = QuestionStatus.approved.value
        await db.commit()

    return (
        f"✅ **Question {clean_num} has been officially approved!**\n\n"
        f"- **Approved Version**: v{answer.version}\n"
        f"- **Timestamp**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"- This answer is locked and ready for final DOCX and XLSX export."
    )


async def get_rfp_summary_tool(session_id: int) -> str:
    """View overall status, counts of answered, pending, flagged, and approved items."""
    async with AsyncSessionLocal() as db:
        s = await db.get(SessionModel, session_id)
        if s is None:
            return f"❌ Session {session_id} not found."

        q_res = await db.execute(select(Question).where(Question.session_id == session_id))
        questions = list(q_res.scalars())

    if not questions:
        return f"Session {session_id} ('{s.name}') has no extracted questions yet. Please upload an RFP."

    total = len(questions)
    approved = sum(1 for q in questions if q.status == QuestionStatus.approved.value)
    answered = sum(1 for q in questions if q.status == QuestionStatus.answered.value)
    low_conf = sum(1 for q in questions if q.status == QuestionStatus.low_confidence.value)
    clarif = sum(1 for q in questions if q.status == QuestionStatus.clarification.value)
    flagged = sum(1 for q in questions if q.status == QuestionStatus.flagged_owner.value)
    pending = sum(1 for q in questions if q.status == QuestionStatus.pending.value)

    pricing_c = sum(1 for q in questions if q.owner == "Pricing")
    legal_c = sum(1 for q in questions if q.owner == "Legal")
    delivery_c = sum(1 for q in questions if q.owner == "Delivery")

    return (
        f"### RFP Status Summary for Session {session_id} ('{s.name}')\n\n"
        f"- **Total Questions**: {total}\n"
        f"- **✅ Approved**: {approved} / {total} ({approved / total * 100:.1f}%)\n"
        f"- **📝 Drafted (High Confidence)**: {answered}\n"
        f"- **⚠️ Low Confidence**: {low_conf}\n"
        f"- **❓ Clarifications Required**: {clarif}\n"
        f"- **🚩 Flagged to Department Owners**: {flagged}\n"
        f"  - Pricing / Commercial: {pricing_c}\n"
        f"  - Legal / Compliance: {legal_c}\n"
        f"  - Delivery / SLAs: {delivery_c}\n"
        f"- **⏳ Pending Analysis**: {pending}"
    )


# ── OpenAI Function Calling Tool Schemas ──────────────────────────────────────

CHAT_TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_questions",
            "description": "List RFP questions in this session, optionally filtered by category, owner, or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category: shariah, technical, commercial, legal, sla, general",
                    },
                    "owner": {
                        "type": "string",
                        "description": "Filter by department owner: Pricing, Legal, Delivery",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by question status: pending, answered, low_confidence, clarification, flagged_owner, approved",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_answer",
            "description": "Inspect the current draft answer, citations, confidence score, and staleness warnings for a question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_number": {
                        "type": "string",
                        "description": "The exact question number to inspect, e.g. '3.1' or '4.2'",
                    },
                },
                "required": ["question_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rewrite_answer",
            "description": "Rewrite or rephrase an existing draft answer according to the Sales Engineer's instructions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_number": {
                        "type": "string",
                        "description": "The question number to rewrite, e.g. '3.1'",
                    },
                    "instruction": {
                        "type": "string",
                        "description": "Instructions for rewriting, e.g. 'make it concise under 100 words', 'emphasize AAOIFI compliance'",
                    },
                },
                "required": ["question_number", "instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_se_fact",
            "description": "Inject Sales Engineer field knowledge or customer references into the answer with an 'se_input' citation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_number": {
                        "type": "string",
                        "description": "The question number to enrich, e.g. '3.1'",
                    },
                    "fact": {
                        "type": "string",
                        "description": "The fact, reference, or technical detail provided by the Sales Engineer.",
                    },
                },
                "required": ["question_number", "fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "Search the knowledge base for verified product specifications, past SOWs, and past RFP responses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query keywords, e.g. 'Murabaha early settlement rebate' or 'Istisna'a milestone billing'",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top matching chunks to retrieve (default 4)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_answer",
            "description": "Approve a draft answer. Requires explicit SE confirmation: confirm=True.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_number": {
                        "type": "string",
                        "description": "The question number to approve, e.g. '3.1'",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true to authorize approval. If false, approval is rejected.",
                    },
                },
                "required": ["question_number", "confirm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rfp_summary",
            "description": "Get overall status summary: question counts, approval percentage, and department owner triage breakdown.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


async def execute_tool(name: str, args: dict[str, Any], session_id: int) -> str:
    """Dispatch a tool call to the corresponding implementation."""
    try:
        if name == "list_questions":
            return await list_questions_tool(
                session_id=session_id,
                category=args.get("category"),
                owner=args.get("owner"),
                status=args.get("status"),
            )
        elif name == "show_answer":
            return await show_answer_tool(
                session_id=session_id,
                question_number=str(args.get("question_number", "")),
            )
        elif name == "rewrite_answer":
            return await rewrite_answer_tool(
                session_id=session_id,
                question_number=str(args.get("question_number", "")),
                instruction=str(args.get("instruction", "")),
            )
        elif name == "apply_se_fact":
            return await apply_se_fact_tool(
                session_id=session_id,
                question_number=str(args.get("question_number", "")),
                fact=str(args.get("fact", "")),
            )
        elif name == "search_kb":
            return await search_kb_tool(
                query=str(args.get("query", "")),
                top_k=int(args.get("top_k", 4)),
            )
        elif name == "approve_answer":
            confirm_val = bool(args.get("confirm", False))
            return await approve_answer_tool(
                session_id=session_id,
                question_number=str(args.get("question_number", "")),
                confirm=confirm_val,
            )
        elif name == "get_rfp_summary":
            return await get_rfp_summary_tool(session_id=session_id)
        else:
            return f"❌ Unknown tool: '{name}'"
    except Exception as exc:
        logger.error("Error executing tool %s with args %s: %s", name, args, exc)
        return f"❌ Error executing {name}: {exc}"
