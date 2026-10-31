"""
tests/test_phase1.py — Comprehensive tests for Phase 1:
- Sensitive data & PII redaction (clients, pricing, emails, phones)
- Document parsing & chunking
- Staleness warnings (version & age)
- Hybrid search (dense + sparse fusion)
- Knowledge Base API endpoints
"""
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.services.document_parser import (
    chunk_text,
    extract_frontmatter,
)
from backend.app.services.redaction import (
    TOKEN_CLIENT,
    TOKEN_EMAIL,
    TOKEN_PHONE,
    TOKEN_PRICING,
    redact_text,
)
from backend.app.services.retrieval import get_retriever

# ── Redaction Tests ──────────────────────────────────────────────────────────

def test_redaction_client_names():
    sample = "Bank Al-Noor contracted with Azentio for deployment at Al-Hilal Bank."
    redacted, was_redacted = redact_text(sample)
    assert was_redacted is True
    assert "Bank Al-Noor" not in redacted
    assert "Al-Hilal Bank" not in redacted
    assert TOKEN_CLIENT in redacted
    assert "Azentio" in redacted  # Vendor name is kept


def test_redaction_pricing():
    sample = "Total license fee is $1,250,000 with annual AMC of AED 450,000 and hourly rate $120/hr."
    redacted, was_redacted = redact_text(sample)
    assert was_redacted is True
    assert "$1,250,000" not in redacted
    assert "AED 450,000" not in redacted
    assert "$120/hr" not in redacted
    assert TOKEN_PRICING in redacted


def test_redaction_contact_info():
    sample = "Contact ahmed.khalil@bankalnoor.ae or call +971-4-555-0199 for inquiries."
    redacted, was_redacted = redact_text(sample)
    assert was_redacted is True
    assert "ahmed.khalil@bankalnoor.ae" not in redacted
    assert "+971-4-555-0199" not in redacted
    assert TOKEN_EMAIL in redacted
    assert TOKEN_PHONE in redacted


def test_redaction_clean_product_text():
    sample = "AzentioFinance v3.0 complies with AAOIFI Standard No. 8 for Murabaha financing."
    redacted, was_redacted = redact_text(sample)
    assert was_redacted is False
    assert redacted == sample


# ── Parsing & Chunking Tests ──────────────────────────────────────────────────

def test_frontmatter_extraction():
    raw = """---
source_type: product_doc
product: AzentioFinance
product_version: 3.0.0
---
# Main Content
Here is the specification text.
"""
    meta, body = extract_frontmatter(raw)
    assert meta["source_type"] == "product_doc"
    assert meta["product"] == "AzentioFinance"
    assert meta["product_version"] == "3.0.0"
    assert "Here is the specification text." in body


def test_semantic_chunking():
    text = """# Section 1
This is the first section explaining Murabaha details.

## Section 2
This is the second section detailing Ijarah leasing options.
"""
    chunks = chunk_text(
        document_name="spec.md",
        source_type="product_doc",
        text=text,
        product="AzentioFinance",
        product_version="3.0.0",
    )
    assert len(chunks) >= 2
    assert any("Murabaha" in c.text for c in chunks)
    assert any("Ijarah" in c.text for c in chunks)
    assert all(c.document_name == "spec.md" for c in chunks)


# ── Staleness Detection Tests ─────────────────────────────────────────────────

def test_staleness_detection():
    from datetime import datetime, timedelta

    retriever = get_retriever()

    # Older version 2.1.0 vs current 3.0.0 -> must trigger warning
    warning = retriever.check_staleness(product_version="2.1.0", doc_date="2026-01-01")
    assert warning is not None
    assert "superseded by current version" in warning

    # Current version 3.0.0 with recent date (within 18 months) -> no warning
    recent_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    warning_current = retriever.check_staleness(product_version="3.0.0", doc_date=recent_date)
    assert warning_current is None

    # Very old date (> 18 months) -> must trigger age warning
    warning_old = retriever.check_staleness(product_version="3.0.0", doc_date="2020-01-01")
    assert warning_old is not None
    assert "older than" in warning_old



# ── Hybrid Retrieval Search Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_search():
    retriever = get_retriever()
    assert retriever.count() > 0

    results = await retriever.search(
        query="Murabaha AAOIFI compliance dual contract sequence",
        top_k=3,
    )
    assert len(results) > 0
    top = results[0]
    assert top.score > 0
    assert top.document_name is not None
    assert "murabaha" in top.snippet.lower() or "aaoifi" in top.snippet.lower()


@pytest.mark.asyncio
async def test_hybrid_search_staleness_flag():
    retriever = get_retriever()
    results = await retriever.search(
        query="WebLogic monolithic legacy manual broker settlement",
        top_k=3,
    )
    assert len(results) > 0
    # Must find the legacy v2.1 notes and flag it as stale
    legacy_results = [r for r in results if r.product_version == "2.1.0"]
    assert len(legacy_results) > 0
    assert legacy_results[0].stale_warning is not None


# ── API Endpoint Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kb_api_list_and_search():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Ingest documents into test database
        ingest_resp = await client.post("/kb/ingest?kb_path=data/kb_sample")
        assert ingest_resp.status_code == 200

        # 2. List ingested documents
        resp = await client.get("/kb/documents")
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) >= 6
        assert any(d["redacted"] is True for d in docs)

        # 3. Search endpoint
        search_resp = await client.post(
            "/kb/search",
            json={"query": "Disaster recovery RTO and RPO availability", "top_k": 3},
        )
        assert search_resp.status_code == 200
        search_results = search_resp.json()
        assert len(search_results) > 0
        assert "snippet" in search_results[0]
        assert "score" in search_results[0]

