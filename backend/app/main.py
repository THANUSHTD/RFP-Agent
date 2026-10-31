"""
main.py — FastAPI application entrypoint.

Registers all routers, handles startup (DB init), CORS, and
global exception handling. Run with: uvicorn backend.app.main:app --reload
"""
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.chat import router as chat_router
from backend.app.api.clarifications import router as clarifications_router
from backend.app.api.export import router as export_router
from backend.app.api.format_rules import router as format_rules_router

# Import all routers
from backend.app.api.health import router as health_router
from backend.app.api.kb import router as kb_router
from backend.app.api.questions import router as questions_router
from backend.app.api.rfp import router as rfp_router
from backend.app.api.sessions import router as sessions_router
from backend.app.config import get_settings
from backend.app.db import init_db

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
settings = get_settings()

# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="RFP Agent API",
    description=(
        "Backend for the Azentio RFP Agent — helps Sales Engineers respond to "
        "Islamic banking and lending RFPs. All data is synthetic or mock (SAMPLE)."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow the Streamlit frontend (and local dev) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    """Create database tables on startup."""
    logger.info("Starting RFP Agent API v0.1.0")
    await init_db()
    logger.info("Database initialised. Fast model: %s | Draft model: %s",
                settings.fast_model, settings.draft_model)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(rfp_router)
app.include_router(questions_router)
app.include_router(chat_router)
app.include_router(clarifications_router)
app.include_router(kb_router)
app.include_router(export_router)
app.include_router(format_rules_router)
