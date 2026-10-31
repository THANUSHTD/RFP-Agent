"""
api/kb.py — Knowledge base management endpoints (Phase 0/1 stubs).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import KBDocument
from backend.app.schemas import KBDocumentOut, OKResponse

router = APIRouter(prefix="/kb", tags=["kb"])


@router.get("/documents", response_model=list[KBDocumentOut])
async def list_kb_documents(db: AsyncSession = Depends(get_db)) -> list[KBDocumentOut]:
    """List all documents ingested into the knowledge base."""
    result = await db.execute(select(KBDocument).order_by(KBDocument.ingested_at.desc()))
    return [KBDocumentOut.model_validate(d) for d in result.scalars()]


@router.post("/ingest", response_model=OKResponse)
async def ingest_kb() -> OKResponse:
    """Trigger KB ingestion (stub — full impl in Phase 1)."""
    return OKResponse(message="KB ingestion not yet implemented (Phase 0 stub).")
