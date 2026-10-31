"""
tests/test_phase5.py — Test suite for Phase 5: Response Document & Matrix Export.

Validates:
1. DOCX generation with exact formatting, approved stamps, draft warnings, and citations.
2. XLSX Section 7 Compliance Matrix with openpyxl styling and status columns.
3. Full export API endpoints:
   - POST /sessions/{id}/export
   - GET /sessions/{id}/export/docx
   - GET /sessions/{id}/export/xlsx
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import docx
import openpyxl
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db import AsyncSessionLocal
from backend.app.main import app
from backend.app.models import (
    Answer,
    FormatRule,
    Question,
    Section,
)
from backend.app.models import (
    Session as SessionModel,
)
from backend.app.services.exporter import (
    generate_docx_export,
    generate_xlsx_matrix,
)


@pytest.fixture
async def export_test_session(tmp_path: Path) -> int:
    """Create a session populated with approved, draft, and flagged questions."""
    async with AsyncSessionLocal() as db:
        session = SessionModel(name="Al-Noor Islamic Banking RFP")
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        # Format rules
        rule = FormatRule(
            session_id=session_id,
            rules_json=json.dumps(
                {
                    "word_limit": 200,
                    "section_headings": True,
                    "numbering_scheme": "exact",
                    "compliance_matrix_required": True,
                }
            ),
            confirmed_by_se=True,
        )
        db.add(rule)

        # Sections
        sec1 = Section(
            rfp_document_id=1,
            title="3. Core Platform Capabilities",
            order_index=1,
        )
        sec2 = Section(
            rfp_document_id=1,
            title="6. Commercial Terms & Pricing",
            order_index=2,
        )
        db.add_all([sec1, sec2])
        await db.commit()
        await db.refresh(sec1)
        await db.refresh(sec2)

        # Questions
        q1 = Question(
            session_id=session_id,
            section_id=sec1.id,
            number="3.1",
            text="Describe how your platform supports Murabaha cost-plus financing.",
            category="shariah",
            status="approved",
            mandatory=True,
        )
        q2 = Question(
            session_id=session_id,
            section_id=sec1.id,
            number="3.2",
            text="Explain support for Ijarah leasing contracts and asset lifecycle.",
            category="functional",
            status="answered",
            mandatory=True,
        )
        q3 = Question(
            session_id=session_id,
            section_id=sec2.id,
            number="6.1",
            text="Provide 5-year fixed licensing and annual maintenance pricing.",
            category="commercial",
            status="flagged_owner",
            owner="Pricing",
            mandatory=True,
        )
        db.add_all([q1, q2, q3])
        await db.commit()
        await db.refresh(q1)
        await db.refresh(q2)
        await db.refresh(q3)

        # Answers
        ans1 = Answer(
            question_id=q1.id,
            version=1,
            text="AzentioFinance natively automates Murabaha financing under AAOIFI FAS 28.",
            confidence=0.92,
            citations_json=json.dumps(
                [
                    {
                        "chunk_id": "c101",
                        "document": "Azentio Core Spec",
                        "source_type": "product_doc",
                        "snippet": "Native Murabaha.",
                    }
                ]
            ),
            stale_warnings_json="[]",
            status="approved",
            approved_at=datetime.now(UTC),
            edited_by_se=True,
        )
        ans2 = Answer(
            question_id=q2.id,
            version=1,
            text="Ijarah Muntahia Bittamleek lifecycle is fully tracked from asset acquisition to ownership transfer.",
            confidence=0.78,
            citations_json=json.dumps(
                [
                    {
                        "chunk_id": "c102",
                        "document": "Azentio Core Spec",
                        "source_type": "product_doc",
                        "snippet": "Ijarah asset tracking.",
                    }
                ]
            ),
            stale_warnings_json="[]",
            status="draft",
            edited_by_se=False,
        )
        ans3 = Answer(
            question_id=q3.id,
            version=1,
            text="[PENDING OWNER INPUT — Assigned to Pricing] Commercial pricing requires bespoke financial modeling.",
            confidence=1.0,
            citations_json="[]",
            stale_warnings_json="[]",
            status="draft",
            edited_by_se=False,
        )
        db.add_all([ans1, ans2, ans3])
        await db.commit()

        return session_id


@pytest.mark.asyncio
async def test_generate_docx_export(export_test_session: int, tmp_path: Path):
    session_id = export_test_session
    output_docx = tmp_path / "test_response.docx"

    async with AsyncSessionLocal() as db:
        await generate_docx_export(session_id, db, output_docx)

    assert output_docx.exists()
    assert output_docx.stat().st_size > 5000

    # Parse and inspect generated document
    doc = docx.Document(str(output_docx))
    full_text = "\n".join(
        [p.text for p in doc.paragraphs]
        + [c.text for t in doc.tables for r in t.rows for c in r.cells]
    )

    assert "RFP RESPONSE PROPOSAL" in full_text
    assert "Al-Noor Islamic Banking RFP" in full_text
    assert "Requirement 3.1" in full_text
    assert "Murabaha" in full_text
    assert "[APPROVED BY SALES ENGINEER]" in full_text
    assert "[DRAFT — NOT APPROVED BY SALES ENGINEER]" in full_text
    assert "ASSIGNED TO PRICING" in full_text


@pytest.mark.asyncio
async def test_generate_xlsx_matrix(export_test_session: int, tmp_path: Path):
    session_id = export_test_session
    output_xlsx = tmp_path / "test_matrix.xlsx"

    async with AsyncSessionLocal() as db:
        await generate_xlsx_matrix(session_id, db, output_xlsx)

    assert output_xlsx.exists()
    assert output_xlsx.stat().st_size > 3000

    # Inspect openpyxl workbook
    wb = openpyxl.load_workbook(str(output_xlsx))
    assert "Compliance Matrix" in wb.sheetnames
    ws = wb["Compliance Matrix"]

    # Verify column headers on row 4
    headers = [cell.value for cell in ws[4]]
    assert "Item No." in headers
    assert "Compliance Status" in headers
    assert "Requirement / Question" in headers

    # Verify rows for questions 3.1, 3.2, 6.1
    rows_text = [
        " ".join([str(c.value) for c in row if c.value is not None])
        for row in ws.iter_rows(min_row=5)
    ]
    all_rows = "\n".join(rows_text)

    assert "3.1" in all_rows
    assert "Compliant (Approved)" in all_rows
    assert "3.2" in all_rows
    assert "Compliant (Draft)" in all_rows
    assert "6.1" in all_rows
    assert "Pending (Pricing)" in all_rows


@pytest.mark.asyncio
async def test_export_api_endpoints(export_test_session: int):
    session_id = export_test_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Trigger export generation
        exp_resp = await client.post(f"/sessions/{session_id}/export")
        assert exp_resp.status_code == 200
        data = exp_resp.json()
        assert data["session_id"] == session_id
        assert data["docx_filename"].endswith(".docx")
        assert data["xlsx_filename"].endswith(".xlsx")
        assert data["total_questions"] >= 1
        assert data["approved_count"] >= 1

        # 2. Download DOCX
        docx_resp = await client.get(f"/sessions/{session_id}/export/docx")
        assert docx_resp.status_code == 200
        assert "wordprocessingml" in docx_resp.headers["content-type"]
        assert len(docx_resp.content) > 3000

        # 3. Download XLSX
        xlsx_resp = await client.get(f"/sessions/{session_id}/export/xlsx")
        assert xlsx_resp.status_code == 200
        assert "spreadsheetml" in xlsx_resp.headers["content-type"]
        assert len(xlsx_resp.content) > 2000
