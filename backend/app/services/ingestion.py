"""
backend/app/services/ingestion.py — Knowledge Base ingestion pipeline.

Pipeline workflow:
1. Scan KB folder (product_docs, past_sows, past_rfp_responses).
2. Extract text & metadata from MD, DOCX, and PDF.
3. Apply sensitive data / PII redaction if document is a SOW or past RFP response.
4. Chunk text with semantic headers preserved.
5. Index chunks into ChromaDB and build BM25 sparse index.
6. Record or update KBDocument entries in SQLite.
"""

import logging
import os
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models import KBDocument, SourceType
from backend.app.services.document_parser import (
    chunk_text,
    extract_text_from_file,
)
from backend.app.services.redaction import redact_text
from backend.app.services.retrieval import get_retriever

logger = logging.getLogger(__name__)
settings = get_settings()


async def ingest_file(
    file_path: str,
    db: AsyncSession,
    retriever=None,
) -> dict[str, Any]:
    """Ingest a single document into the knowledge base."""
    if retriever is None:
        retriever = get_retriever()

    filename = os.path.basename(file_path)
    parent_dir = os.path.basename(os.path.dirname(file_path)).lower()

    # Determine source_type from directory name or default to product_doc
    if "sow" in parent_dir or "sow" in filename.lower():
        source_type = SourceType.sow.value
    elif "rfp" in parent_dir or "past" in parent_dir or "resp" in filename.lower():
        source_type = SourceType.past_response.value
    else:
        source_type = SourceType.product_doc.value

    # Extract text and frontmatter metadata
    metadata, raw_text = extract_text_from_file(file_path)

    # Allow frontmatter override of source_type, product, product_version, doc_date
    source_type = metadata.get("source_type", source_type)
    product = metadata.get("product", "AzentioFinance")
    product_version = metadata.get("product_version", settings.current_product_version)
    doc_date = metadata.get("doc_date", datetime.now().strftime("%Y-%m-%d"))

    # Apply redaction if it is SOW or past RFP response
    needs_redaction = source_type in (SourceType.sow.value, SourceType.past_response.value)
    redacted = False
    if needs_redaction:
        raw_text, redacted = redact_text(raw_text)

    # Chunk text
    chunks = chunk_text(
        document_name=filename,
        source_type=source_type,
        text=raw_text,
        product=product,
        product_version=product_version,
        doc_date=doc_date,
    )

    if not chunks:
        return {"filename": filename, "chunks": 0, "status": "empty"}

    # Format for retriever
    chroma_payload = [
        {
            "id": c.chunk_id,
            "text": c.text,
            "metadata": {
                "document_name": c.document_name,
                "source_type": c.source_type,
                "product": c.product or "",
                "product_version": c.product_version or "",
                "doc_date": c.doc_date or "",
                "title": c.title,
                "chunk_index": c.chunk_index,
            },
        }
        for c in chunks
    ]

    await retriever.add_chunks(chroma_payload)

    # Check if KBDocument already exists in DB
    existing = await db.execute(select(KBDocument).where(KBDocument.document_name == filename))
    kb_doc = existing.scalar_one_or_none()

    if kb_doc is None:
        kb_doc = KBDocument(
            document_name=filename,
            source_type=source_type,
            product=product,
            product_version=product_version,
            doc_date=doc_date,
            reuse_permitted=True,
            redacted=redacted,
            chunk_count=len(chunks),
        )
        db.add(kb_doc)
    else:
        kb_doc.source_type = source_type
        kb_doc.product = product
        kb_doc.product_version = product_version
        kb_doc.doc_date = doc_date
        kb_doc.redacted = redacted
        kb_doc.chunk_count = len(chunks)
        kb_doc.ingested_at = datetime.now()

    await db.commit()

    return {
        "filename": filename,
        "source_type": source_type,
        "chunks": len(chunks),
        "redacted": redacted,
        "product_version": product_version,
        "status": "success",
    }


async def run_kb_ingestion(
    kb_dir: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Ingest all documents inside kb_dir and all its subfolders."""
    if not os.path.exists(kb_dir):
        os.makedirs(kb_dir, exist_ok=True)
        return {"processed": 0, "total_chunks": 0, "files": []}

    retriever = get_retriever()
    results = []
    total_chunks = 0

    for root, _, files in os.walk(kb_dir):
        for f in files:
            if f.startswith(".") or f.endswith(".tmp"):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in (".md", ".txt", ".docx", ".pdf"):
                path = os.path.join(root, f)
                res = await ingest_file(path, db, retriever=retriever)
                results.append(res)
                total_chunks += res.get("chunks", 0)

    return {
        "processed": len(results),
        "total_chunks": total_chunks,
        "files": results,
    }
