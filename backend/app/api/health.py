"""
api/health.py — Health check endpoint.

Returns basic status: DB connectivity, configured model names, app version.
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.schemas import HealthOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthOut, summary="Health check")
async def health(db: AsyncSession = Depends(get_db)) -> HealthOut:
    """Return API health status.

    Verifies the database is reachable and echoes configured model names.
    """
    # Simple DB probe — just ping SQLite
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        db_status = "error"

    return HealthOut(
        status="ok",
        version="0.1.0",
        db=db_status,
        fast_model=settings.fast_model,
        draft_model=settings.draft_model,
    )
