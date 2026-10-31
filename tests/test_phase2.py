"""
tests/test_phase2.py — Comprehensive tests for Phase 2:
- RFP Document extraction (PDF and DOCX)
- Section and question boundary detection
- Formatting rules extraction (word limits, file naming, tone)
- Triage & department owner routing (Pricing, Legal, Delivery)
- API endpoint integration: upload, analyze, list questions, format rules
"""
import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.models import OwnerDept, QuestionCategory, QuestionStatus
from backend.app.services.document_parser import extract_text_from_file
from backend.app.services.rfp_extractor import (
    classify_question,
    extract_format_rules,
    extract_sections_and_questions,
)

SAMPLE_DOCX = "data/sample_rfp/sample_rfp.docx"
SAMPLE_PDF = "data/sample_rfp/sample_rfp.pdf"


# ── Document Parsing Tests ───────────────────────────────────────────────────

def test_extract_from_sample_docx():
    assert os.path.exists(SAMPLE_DOCX), f"Missing {SAMPLE_DOCX}"
    meta, text = extract_text_from_file(SAMPLE_DOCX)
    assert len(text) > 1000
    assert "Islamic Lending" in text

    sections = extract_sections_and_questions(text)
    assert len(sections) >= 5
    total_q = sum(len(s.questions) for s in sections)
    assert total_q >= 20

    # Verify first question
    q1 = sections[0].questions[0]
    assert q1.number == "3.1.1"
    assert q1.mandatory is True
    assert "Murabaha" in q1.text


def test_extract_from_sample_pdf():
    assert os.path.exists(SAMPLE_PDF), f"Missing {SAMPLE_PDF}"
    meta, text = extract_text_from_file(SAMPLE_PDF)
    assert len(text) > 1000
    sections = extract_sections_and_questions(text)
    assert len(sections) >= 5
    total_q = sum(len(s.questions) for s in sections)
    assert total_q >= 20


# ── Format Rules Tests ────────────────────────────────────────────────────────

def test_extract_format_rules():
    _, text = extract_text_from_file(SAMPLE_DOCX)
    rules = extract_format_rules(text)

    assert rules["word_limit"] == 250
    assert "ABDB-RFP-2024-001" in str(rules["file_naming"])
    assert rules["compliance_matrix_required"] is True
    assert "English" in rules["language"]


# ── Triage & Owner Flagging Tests ─────────────────────────────────────────────

def test_triage_commercial_routed_to_pricing():
    text = "Provide total cost of ownership (TCO) for a 5-year engagement including implementation fees."
    cat, owner, status = classify_question(text, "6. Commercial Terms")
    assert cat == QuestionCategory.commercial
    assert owner == OwnerDept.pricing
    assert status == QuestionStatus.flagged_owner


def test_triage_sla_routed_to_delivery():
    text = "State your standard SLA commitments for platform uptime, incident response, and disaster recovery RTO/RPO."
    cat, owner, status = classify_question(text, "6. Commercial Terms, SLA and Legal")
    assert cat == QuestionCategory.sla
    assert owner == OwnerDept.delivery
    assert status == QuestionStatus.flagged_owner


def test_triage_legal_routed_to_legal():
    text = "Confirm whether your contract includes data residency guarantees and whether you accept DIFC law as governing law."
    cat, owner, status = classify_question(text, "6. Commercial Terms, SLA and Legal")
    assert cat == QuestionCategory.legal
    assert owner == OwnerDept.legal
    assert status == QuestionStatus.flagged_owner


def test_triage_shariah_pending_no_owner():
    text = "Describe how your platform supports Murabaha cost-plus financing and AAOIFI standards compliance."
    cat, owner, status = classify_question(text, "3. Core Platform Capabilities")
    assert cat == QuestionCategory.shariah
    assert owner is None
    assert status == QuestionStatus.pending


# ── Full Analysis Pipeline API Test ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_rfp_analysis_api_flow():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Create a session
        sess_resp = await client.post("/sessions", json={"name": "Al-Baraka Test RFP"})
        assert sess_resp.status_code == 201
        session_id = sess_resp.json()["id"]

        # 2. Upload RFP docx
        with open(SAMPLE_DOCX, "rb") as f:
            docx_bytes = f.read()

        upload_resp = await client.post(
            f"/sessions/{session_id}/rfp",
            files={"file": ("sample_rfp.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert upload_resp.status_code == 201

        # 3. Trigger analyze
        analyze_resp = await client.post(f"/sessions/{session_id}/analyze")
        assert analyze_resp.status_code == 200
        msg = analyze_resp.json()["message"]
        assert "questions" in msg.lower()
        assert "complete" in msg.lower() or "extracted" in msg.lower()


        # 4. Check questions list
        q_resp = await client.get(f"/sessions/{session_id}/questions")
        assert q_resp.status_code == 200
        questions = q_resp.json()
        assert len(questions) >= 20

        # Verify owner flagging in DB
        pricing_items = [q for q in questions if q.get("owner") == "Pricing"]
        legal_items = [q for q in questions if q.get("owner") == "Legal"]
        delivery_items = [q for q in questions if q.get("owner") == "Delivery"]
        assert len(pricing_items) >= 1
        assert len(legal_items) >= 1
        assert len(delivery_items) >= 1

        # 5. Check format rules endpoint
        rules_resp = await client.get(f"/sessions/{session_id}/format-rules")
        assert rules_resp.status_code == 200
        rules_obj = rules_resp.json()
        assert "word_limit" in rules_obj["rules_json"]

        # 6. Check summary chat message
        msg_resp = await client.get(f"/sessions/{session_id}/messages")
        assert msg_resp.status_code == 200
        messages = msg_resp.json()
        assert len(messages) >= 1
        assert "RFP Analysis Complete" in messages[0]["content"]
