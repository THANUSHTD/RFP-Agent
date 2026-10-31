"""
api/kb.py — Knowledge base management and hybrid search endpoints.
"""

import os

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import KBDocument
from backend.app.schemas import (
    KBChunkResult,
    KBDocumentOut,
    KBSearchRequest,
    OKResponse,
)
from backend.app.services.ingestion import run_kb_ingestion
from backend.app.services.retrieval import get_retriever

router = APIRouter(prefix="/kb", tags=["kb"])


@router.get("/documents", response_model=list[KBDocumentOut])
async def list_kb_documents(db: AsyncSession = Depends(get_db)) -> list[KBDocumentOut]:
    """List all documents ingested into the knowledge base."""
    result = await db.execute(select(KBDocument).order_by(KBDocument.ingested_at.desc()))
    return [KBDocumentOut.model_validate(d) for d in result.scalars()]


@router.post("/ingest", response_model=OKResponse)
async def ingest_kb(
    kb_path: str = Query(
        default="data/kb_sample", description="Relative or absolute path to KB directory"
    ),
    db: AsyncSession = Depends(get_db),
) -> OKResponse:
    """Trigger ingestion of synthetic knowledge base documents into Chroma and SQLite."""
    abs_path = os.path.abspath(kb_path)
    summary = await run_kb_ingestion(abs_path, db)
    return OKResponse(
        message=f"Ingested {summary['processed']} documents ({summary['total_chunks']} chunks total)."
    )


@router.post("/search", response_model=list[KBChunkResult])
async def search_kb(body: KBSearchRequest) -> list[KBChunkResult]:
    """Search the knowledge base using hybrid dense (Chroma) + sparse (BM25) retrieval."""
    retriever = get_retriever()
    results = await retriever.search(
        query=body.query,
        top_k=body.top_k,
        source_type=body.source_type,
        product_version=body.product_version,
    )
    return results
