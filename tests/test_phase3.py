"""
tests/test_phase3.py — Comprehensive tests for Phase 3:
- Grounded answer drafting with knowledge base citations
- Verification and confidence scoring
- Owner-flagged questions protection (never auto-answered)
- Low confidence routing to Clarifications list
- Staleness warning attachments
- Human-in-the-loop: Answer edit (version bump) and explicit SE approval
- LangGraph analysis pipeline integration
"""
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.models import OwnerDept, Question, QuestionCategory, QuestionStatus
from backend.app.services.answer_drafter import draft_answer_for_question

SAMPLE_DOCX = "data/sample_rfp/sample_rfp.docx"


# ── Answer Drafting & Grounding Tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_grounded_answer_drafting_with_citations():
    q = Question(
        id=101,
        session_id=1,
        number="3.1.1",
        text="Describe how your platform supports Murabaha cost-plus financing and profit calculation.",
        mandatory=True,
        category=QuestionCategory.shariah.value,
        status=QuestionStatus.pending.value,
        owner=None,
    )
    ans_text, conf, cites, stales, status = await draft_answer_for_question(q)

    assert "Murabaha" in ans_text
    assert conf >= 0.45
    assert len(cites) > 0
    assert any("azentio" in c["document"].lower() or "specification" in c["document"].lower() for c in cites)
    assert status in (QuestionStatus.answered, QuestionStatus.low_confidence)


@pytest.mark.asyncio
async def test_flagged_owner_question_not_auto_answered():
    q = Question(
        id=102,
        session_id=1,
        number="6.1",
        text="Provide total cost of ownership (TCO) for a 5-year engagement.",
        mandatory=True,
        category=QuestionCategory.commercial.value,
        status=QuestionStatus.flagged_owner.value,
        owner=OwnerDept.pricing.value,
    )
    ans_text, conf, cites, stales, status = await draft_answer_for_question(q)

    assert "PENDING OWNER INPUT" in ans_text
    assert "Pricing" in ans_text
    assert len(cites) == 0
    assert status == QuestionStatus.flagged_owner


@pytest.mark.asyncio
async def test_insufficient_sources_routes_to_clarification():
    q = Question(
        id=103,
        session_id=1,
        number="99.9",
        text="Does Azentio manufacture space satellite hardware for orbital quantum communications?",
        mandatory=False,
        category=QuestionCategory.other.value,
        status=QuestionStatus.pending.value,
        owner=None,
    )
    ans_text, conf, cites, stales, status = await draft_answer_for_question(q)

    assert "does not contain sufficient" in ans_text or "clarification" in ans_text.lower()
    assert conf < 0.45
    assert status == QuestionStatus.clarification


@pytest.mark.asyncio
async def test_staleness_warning_propagated_to_answer():
    q = Question(
        id=104,
        session_id=1,
        number="1.2",
        text="Describe legacy WebLogic monolithic deployment and manual CSV commodity broker uploads in v2.1.",
        mandatory=False,
        category=QuestionCategory.technical.value,
        status=QuestionStatus.pending.value,
        owner=None,
    )
    ans_text, conf, cites, stales, status = await draft_answer_for_question(q)

    assert len(cites) > 0
    # Must contain staleness warning for legacy 2.1 doc
    assert len(stales) > 0
    assert any("superseded" in sw or "older than" in sw for sw in stales)


# ── Human-in-the-Loop & Approval API Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_answer_edit_and_approval_flow():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Create a session and upload RFP
        sess_resp = await client.post("/sessions", json={"name": "Approval Test Session"})
        assert sess_resp.status_code == 201
        session_id = sess_resp.json()["id"]

        with open(SAMPLE_DOCX, "rb") as f:
            docx_bytes = f.read()

        await client.post(
            f"/sessions/{session_id}/rfp",
            files={"file": ("sample_rfp.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )

        # 2. Trigger LangGraph analysis & answer drafting
        analyze_resp = await client.post(f"/sessions/{session_id}/analyze")
        assert analyze_resp.status_code == 200

        # 3. Get first question
        q_resp = await client.get(f"/sessions/{session_id}/questions")
        assert q_resp.status_code == 200
        questions = q_resp.json()
        assert len(questions) > 0
        first_q = questions[0]
        q_id = first_q["id"]

        # 4. Get draft answer
        ans_resp = await client.get(f"/questions/{q_id}/answer")
        assert ans_resp.status_code == 200
        ans = ans_resp.json()
        assert ans is not None
        assert ans["version"] == 1
        assert ans["status"] == "draft"

        # 5. SE edits the answer (creates version 2)
        edited_content = ans["text"] + "\n\n[SE Note: Verified with lead architect.]"
        patch_resp = await client.patch(
            f"/questions/{q_id}/answer",
            json={"text": edited_content},
        )
        assert patch_resp.status_code == 200
        v2 = patch_resp.json()
        assert v2["version"] == 2
        assert v2["edited_by_se"] is True
        assert "[SE Note:" in v2["text"]

        # 6. Attempt approval without explicit confirmation (must fail)
        reject_appr = await client.post(
            f"/questions/{q_id}/approve",
            json={"confirm": False},
        )
        assert reject_appr.status_code == 400

        # 7. Approve with explicit confirmation
        confirm_appr = await client.post(
            f"/questions/{q_id}/approve",
            json={"confirm": True},
        )
        assert confirm_appr.status_code == 200
        assert confirm_appr.json()["ok"] is True

        # 8. Verify answer and question are now approved
        final_ans = (await client.get(f"/questions/{q_id}/answer")).json()
        assert final_ans["status"] == "approved"
        assert final_ans["approved_at"] is not None

        updated_q_list = (await client.get(f"/sessions/{session_id}/questions")).json()
        appr_q = next(q for q in updated_q_list if q["id"] == q_id)
        assert appr_q["status"] == "approved"
