"""
tests/test_phase4.py — Test suite for Phase 4: Interactive Chat Workspace & Agent Tools.

Validates:
1. list_questions tool with category/owner/status filtering
2. show_answer tool displaying answer, citations, and staleness warnings
3. rewrite_answer tool incrementing answer version and setting edited_by_se=True
4. apply_se_fact tool attaching 'se_input' citations
5. search_kb tool executing hybrid search
6. approve_answer guard enforcing explicit SE confirmation (confirm=True)
7. Full POST /sessions/{id}/chat API flow with LangGraph agent
"""

import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.agents.chat_tools import (
    apply_se_fact_tool,
    approve_answer_tool,
    list_questions_tool,
    rewrite_answer_tool,
    search_kb_tool,
    show_answer_tool,
)
from backend.app.db import AsyncSessionLocal
from backend.app.main import app
from backend.app.models import Answer, AnswerStatus, Question, QuestionStatus
from backend.app.models import Session as SessionModel


@pytest.fixture
async def populated_session():
    """Create a test session with seeded questions and draft answers."""
    async with AsyncSessionLocal() as db:
        session = SessionModel(name="Phase 4 Chat Test Session")
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        q1 = Question(
            session_id=session_id,
            number="3.1",
            text="Describe how your platform supports Murabaha cost-plus financing.",
            category="shariah",
            status="pending",
            owner=None,
            mandatory=True,
        )
        q2 = Question(
            session_id=session_id,
            number="6.1",
            text="Provide 5-year fixed licensing and maintenance fees.",
            category="commercial",
            status="flagged_owner",
            owner="Pricing",
            mandatory=True,
        )
        db.add_all([q1, q2])
        await db.commit()
        await db.refresh(q1)

        ans1 = Answer(
            question_id=q1.id,
            version=1,
            text="Azentio natively supports Murabaha cost-plus financing.",
            confidence=0.88,
            citations_json=json.dumps(
                [
                    {
                        "chunk_id": "test_chunk_1",
                        "document": "Azentio Core Spec",
                        "source_type": "product_doc",
                        "snippet": "Native Murabaha financing support.",
                        "type": "kb",
                    }
                ]
            ),
            stale_warnings_json="[]",
            status="draft",
            edited_by_se=False,
        )
        db.add(ans1)
        await db.commit()

        return session_id


@pytest.mark.asyncio
async def test_list_questions_tool(populated_session: int):
    session_id = populated_session

    # 1. List all
    all_q = await list_questions_tool(session_id)
    assert "Questions in Session" in all_q
    assert "3.1" in all_q

    # 2. Filter by owner
    pricing_q = await list_questions_tool(session_id, owner="Pricing")
    assert "Pricing" in pricing_q
    assert "6.1" in pricing_q


@pytest.mark.asyncio
async def test_show_answer_tool(populated_session: int):
    session_id = populated_session

    result = await show_answer_tool(session_id, "3.1")
    assert "Question 3.1" in result
    assert "Confidence Score" in result
    assert "Citations" in result


@pytest.mark.asyncio
async def test_rewrite_answer_tool(populated_session: int):
    session_id = populated_session

    result = await rewrite_answer_tool(
        session_id=session_id,
        question_number="3.1",
        instruction="Make it very concise and mention AAOIFI compliance.",
    )
    assert "rewritten (Version 2)" in result or "Version 2" in result

    # Check DB record
    async with AsyncSessionLocal() as db:
        q_res = await db.execute(
            select(Question).where(Question.session_id == session_id, Question.number == "3.1")
        )
        q = q_res.scalar_one()
        ans_res = await db.execute(
            select(Answer).where(Answer.question_id == q.id).order_by(Answer.version.desc())
        )
        answers = list(ans_res.scalars())
        assert len(answers) >= 2
        latest = answers[0]
        assert latest.version == 2
        assert latest.edited_by_se is True


@pytest.mark.asyncio
async def test_apply_se_fact_tool(populated_session: int):
    session_id = populated_session

    fact_content = (
        "Azentio has 4 Tier-1 Islamic bank installations in the UAE running live Murabaha."
    )
    result = await apply_se_fact_tool(
        session_id=session_id,
        question_number="3.1",
        fact=fact_content,
    )
    assert "Fact added to Question 3.1" in result
    assert "se_fact_" in result

    # Verify citation type in DB
    async with AsyncSessionLocal() as db:
        q_res = await db.execute(
            select(Question).where(Question.session_id == session_id, Question.number == "3.1")
        )
        q = q_res.scalar_one()
        ans_res = await db.execute(
            select(Answer).where(Answer.question_id == q.id).order_by(Answer.version.desc())
        )
        latest_ans = ans_res.scalars().first()
        assert latest_ans is not None
        cites = latest_ans.citations
        se_cites = [
            c for c in cites if c.get("source_type") == "se_input" or c.get("type") == "se_input"
        ]
        assert len(se_cites) >= 1
        assert "Azentio has 4 Tier-1" in se_cites[0]["snippet"]


@pytest.mark.asyncio
async def test_search_kb_tool():
    result = await search_kb_tool("Murabaha cost-plus financing rebate")
    assert "Knowledge Base Results" in result
    assert "Score:" in result


@pytest.mark.asyncio
async def test_approve_answer_guard(populated_session: int):
    session_id = populated_session

    # 1. Attempt approval without confirmation (must fail / prompt user)
    guard_msg = await approve_answer_tool(session_id, "3.1", confirm=False)
    assert "Approval Guard Active" in guard_msg or "⚠️" in guard_msg

    # 2. Approve with confirm=True
    appr_msg = await approve_answer_tool(session_id, "3.1", confirm=True)
    assert "officially approved" in appr_msg

    # Verify state in DB
    async with AsyncSessionLocal() as db:
        q_res = await db.execute(
            select(Question).where(Question.session_id == session_id, Question.number == "3.1")
        )
        q = q_res.scalar_one()
        assert q.status == QuestionStatus.approved.value

        ans_res = await db.execute(
            select(Answer).where(Answer.question_id == q.id).order_by(Answer.version.desc())
        )
        latest_ans = ans_res.scalars().first()
        assert latest_ans.status == AnswerStatus.approved.value
        assert latest_ans.approved_at is not None


@pytest.mark.asyncio
async def test_chat_api_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create a session via client API
        sess_resp = await client.post("/sessions", json={"name": "Chat API Endpoint Test"})
        assert sess_resp.status_code == 201
        session_id = sess_resp.json()["id"]

        # 2. Ask agent to show status summary
        chat_resp = await client.post(
            f"/sessions/{session_id}/chat",
            json={"content": "Show overall RFP summary"},
        )
        assert chat_resp.status_code == 200
        msg = chat_resp.json()
        assert msg["role"] == "assistant"
        assert "Session" in msg["content"] or "questions" in msg["content"].lower()

        # 3. Check messages history endpoint
        hist_resp = await client.get(f"/sessions/{session_id}/messages")
        assert hist_resp.status_code == 200
        messages = hist_resp.json()
        assert len(messages) >= 2
