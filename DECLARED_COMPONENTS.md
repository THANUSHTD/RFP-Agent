# Declared Components

All third-party libraries and reused components used in the RFP Agent.

## Runtime Dependencies

| Library | Version | Purpose |
|---|---|---|
| fastapi | 0.115.0 | Web framework |
| uvicorn | 0.30.6 | ASGI server |
| pydantic | 2.9.2 | Data validation |
| pydantic-settings | 2.5.2 | Settings from env vars |
| python-dotenv | 1.0.1 | .env loading |
| sqlalchemy | 2.0.35 | ORM (async) |
| aiosqlite | 0.20.0 | Async SQLite driver |
| openai | 1.51.0 | OpenAI API client |
| tenacity | 9.0.0 | Retry with backoff |
| langgraph | 0.2.38 | Agent orchestration |
| langgraph-checkpoint-sqlite | 2.0.1 | Session persistence |
| chromadb | 0.5.12 | Vector store |
| rank_bm25 | 0.2.2 | BM25 keyword search |
| pymupdf | 1.24.11 | PDF text extraction |
| pdfplumber | 0.11.4 | PDF table extraction |
| python-docx | 1.1.2 | Word document parsing and export |
| openpyxl | 3.1.5 | Excel (.xlsx) export |
| httpx | 0.27.2 | HTTP client (Streamlit → FastAPI) |
| streamlit | 1.39.0 | Frontend |
| python-multipart | 0.0.9 | File upload support |
| tiktoken | 0.7.0 | Token counting |
| numpy | 1.26.4 | Numeric operations (RRF scoring) |

## Development Dependencies

| Library | Version | Purpose |
|---|---|---|
| pytest | 8.3.3 | Test runner |
| pytest-asyncio | 0.24.0 | Async test support |
| ruff | 0.6.9 | Linter |
| httpx | 0.27.2 | Test HTTP client |

## AI / LLM

| Component | Notes |
|---|---|
| OpenAI Chat Completions API | Structured outputs (beta) for typed responses |
| OpenAI Embeddings API | Semantic search embeddings |
