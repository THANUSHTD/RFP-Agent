# RFP Agent

> AI-assisted RFP response tool for Azentio Islamic banking sales engineers.
> **All sample data is SYNTHETIC / MOCK — labelled SAMPLE throughout.**

## Overview

The RFP Agent helps Sales Engineers (SEs) respond to Islamic banking and lending RFPs.
Upload an RFP → the agent extracts questions, drafts grounded answers with citations,
flags pricing/legal items to the right owner, and produces a formatted DOCX + compliance matrix XLSX.

Human approval is required for every answer. The agent never finalises anything.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Git

### 2. Clone and set up environment

```bash
git clone <repo-url>
cd rfp-agent
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key and choose models
```

### 4. Run the backend

```bash
uvicorn backend.app.main:app --reload
# API docs: http://localhost:8000/docs
# Health:   http://localhost:8000/health
```

### 5. Ingest the knowledge base

```bash
python scripts/ingest_kb.py
```

### 6. Run the Streamlit frontend

```bash
streamlit run frontend/streamlit_app.py
# Opens: http://localhost:8501
```

### 7. Run tests

```bash
pytest -v
```

### 8. Lint

```bash
ruff check .
```

---

## Environment Variables

All variables are documented in [`.env.example`](.env.example).

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `FAST_MODEL` | `gpt-4o-mini` | Model for triage, parsing, extraction, verification |
| `DRAFT_MODEL` | `gpt-4o` | Model for answer drafting, rewrites, chat |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `CURRENT_PRODUCT_VERSION` | `3.0.0` | Triggers stale warning for older source versions |
| `STALE_AFTER_MONTHS` | `18` | Triggers stale warning for older documents |
| `CONFIDENCE_HIGH` | `0.75` | >= this threshold → confident answer |
| `CONFIDENCE_LOW` | `0.45` | < this threshold → clarification |
| `RETRIEVAL_TOP_K` | `8` | Chunks retrieved per question |
| `MAX_CONCURRENCY` | `4` | Max simultaneous question-processing coroutines |
| `DATABASE_URL` | `sqlite+aiosqlite:///./rfp_agent.db` | SQLAlchemy async DB URL |
| `CHROMA_DIR` | `./chroma_db` | Local Chroma vector store directory |
| `MAX_UPLOAD_MB` | `50` | Maximum upload file size |
| `BACKEND_URL` | `http://localhost:8000` | Streamlit uses this to reach the API |

---

## Demo Walkthrough

1. Create a session in the Streamlit sidebar.
2. Upload `data/sample_rfp/sample_rfp.pdf` (or `.docx`).
3. Click **Analyze RFP** — watch the progress stream.
4. Review the Questions tab: see answers with confidence scores and citations.
5. Notice the stale-source warning on the answer citing an older product version.
6. Notice pricing/SLA questions flagged to owners with no auto-answer.
7. Notice unanswerable questions in the Clarifications tab (no invented answers).
8. Approve two answers using the Approve button.
9. Click **Export** → download the DOCX response and XLSX compliance matrix.
10. Close the browser, reopen → resume the session where you left off.

---

## Assumptions

1. **Product name**: The fictional Islamic lending platform is called **AzentioFinance**.
2. **Session scope**: One session = one RFP engagement. Multiple sessions are supported.
3. **Ports**: Streamlit on 8501, FastAPI on 8000.
4. **Version comparison**: Product versions are compared as simple string comparisons (e.g., "2.1.0" < "3.0.0" done lexicographically after semver parsing).
5. **Concurrent question processing**: Uses `asyncio` + a semaphore inside the LangGraph run — not distributed workers.
6. **Draft export**: Includes unapproved answers as clearly marked `[DRAFT — NOT APPROVED]` placeholders. The SE must confirm before export is generated.
7. **Redaction**: Applied at ingestion time for past RFP responses and SOWs. Only redacted text is stored in Chroma; originals are not retained.
8. **Glossary expansion**: The Islamic finance glossary is used to expand retrieval queries (e.g., Murabaha → "cost-plus financing, deferred payment sale").
9. **Auth**: No authentication in this prototype (hackathon scope). All endpoints are open.
10. **File storage**: Uploaded RFPs are saved to the `uploads/` directory (git-ignored). Exports go to `exports/` (also git-ignored).
