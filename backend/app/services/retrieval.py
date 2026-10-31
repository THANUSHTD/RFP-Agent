"""
backend/app/services/retrieval.py — Hybrid dense + sparse search engine with staleness detection.

Components:
1. Dense vector search via ChromaDB
2. Sparse lexical search via BM25 (rank_bm25)
3. Reciprocal Rank Fusion (RRF) combining dense & sparse ranks
4. Staleness detection (semver check & age check)
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

from backend.app.config import get_settings
from backend.app.llm import embed
from backend.app.schemas import KBChunkResult

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "rfp_knowledge_base"


def _parse_semver(v: str) -> tuple[int, ...]:
    """Parse a semver string like '3.0.0' or '2.1' into a comparable integer tuple."""
    try:
        parts = re.findall(r"\d+", str(v))
        return tuple(int(p) for p in parts)
    except Exception:
        return (0, 0, 0)


def _tokenize(text: str) -> list[str]:
    """Simple alphanumeric tokenizer for BM25."""
    return re.findall(r"\w+", text.lower())


class HybridRetriever:
    """Manages dense vector index (ChromaDB) and sparse keyword index (BM25)."""

    def __init__(self, chroma_dir: str | None = None):
        self.chroma_dir = chroma_dir or settings.chroma_dir
        os.makedirs(self.chroma_dir, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        # In-memory BM25 cache
        self._bm25: BM25Okapi | None = None
        self._bm25_chunk_ids: list[str] = []
        self._bm25_corpus: list[str] = []
        self._bm25_metadata: list[dict[str, Any]] = []

        # Load existing collection into BM25 on startup
        self._rebuild_bm25_from_chroma()

    def _rebuild_bm25_from_chroma(self) -> None:
        """Sync BM25 index with documents currently stored in ChromaDB."""
        try:
            results = self.collection.get(include=["documents", "metadatas"])
            docs = results.get("documents") or []
            ids = results.get("ids") or []
            metadatas = results.get("metadatas") or []

            if docs:
                tokenized = [_tokenize(doc) for doc in docs]
                self._bm25 = BM25Okapi(tokenized)
                self._bm25_chunk_ids = ids
                self._bm25_corpus = docs
                self._bm25_metadata = metadatas
                logger.info("Initialized BM25 index with %d chunks", len(docs))
            else:
                self._bm25 = None
                self._bm25_chunk_ids = []
                self._bm25_corpus = []
                self._bm25_metadata = []
        except Exception as exc:
            logger.warning("Could not sync BM25 index from Chroma: %s", exc)

    def count(self) -> int:
        """Total chunks in the knowledge base."""
        return self.collection.count()

    def check_staleness(
        self,
        product_version: str | None,
        doc_date: str | None,
    ) -> str | None:
        """Determine if a document chunk is stale based on version or age."""
        reasons: list[str] = []

        # 1. Version staleness
        if product_version:
            curr_ver = _parse_semver(settings.current_product_version)
            doc_ver = _parse_semver(product_version)
            if doc_ver < curr_ver:
                reasons.append(
                    f"Document version {product_version} is superseded by current version {settings.current_product_version}"
                )

        # 2. Date staleness
        if doc_date:
            try:
                # Handle YYYY-MM-DD
                d = datetime.strptime(doc_date[:10], "%Y-%m-%d")
                max_age_days = settings.stale_after_months * 30
                if datetime.now() - d > timedelta(days=max_age_days):
                    reasons.append(
                        f"Document dated {doc_date[:10]} is older than {settings.stale_after_months} months"
                    )
            except Exception:
                pass

        if reasons:
            return " | ".join(reasons)
        return None

    async def add_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Add chunks to ChromaDB and rebuild the BM25 index.

        Each item in chunks must contain:
            - id: str
            - text: str
            - metadata: dict
        """
        if not chunks:
            return 0

        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        metas = [c["metadata"] for c in chunks]

        # Generate embeddings
        embeddings = await embed(texts)

        # Upsert into ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metas,
        )

        # Rebuild BM25 index with new chunks
        self._rebuild_bm25_from_chroma()
        return len(chunks)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        source_type: str | None = None,
        product_version: str | None = None,
    ) -> list[KBChunkResult]:
        """Perform hybrid search using Dense vector similarity + Sparse BM25.

        Merged using Reciprocal Rank Fusion (RRF).
        """
        if not query.strip() or self.count() == 0:
            return []

        # 1. Dense retrieval from Chroma
        chroma_where: dict[str, Any] | None = None
        filters = []
        if source_type:
            filters.append({"source_type": source_type})
        if product_version:
            filters.append({"product_version": product_version})

        if len(filters) == 1:
            chroma_where = filters[0]
        elif len(filters) > 1:
            chroma_where = {"$and": filters}

        q_embeddings = await embed([query])
        dense_results = self.collection.query(
            query_embeddings=q_embeddings,
            n_results=min(top_k * 3, max(self.count(), 1)),
            where=chroma_where,
            include=["documents", "metadatas", "distances"],
        )

        dense_ranked_ids: list[str] = []
        dense_docs_map: dict[str, tuple[str, dict[str, Any]]] = {}
        if dense_results and dense_results.get("ids") and dense_results["ids"][0]:
            for cid, doc, meta in zip(
                dense_results["ids"][0],
                dense_results["documents"][0],
                dense_results["metadatas"][0],
            ):
                dense_ranked_ids.append(cid)
                dense_docs_map[cid] = (doc, meta)

        # 2. Sparse retrieval from BM25
        sparse_ranked_ids: list[str] = []
        sparse_docs_map: dict[str, tuple[str, dict[str, Any]]] = {}

        if self._bm25 is not None and len(self._bm25_corpus) > 0:
            query_tokens = _tokenize(query)
            bm25_scores = self._bm25.get_scores(query_tokens)

            # Sort indices by score descending
            ranked_indices = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True,
            )

            for idx in ranked_indices:
                if bm25_scores[idx] <= 0:
                    continue
                cid = self._bm25_chunk_ids[idx]
                meta = self._bm25_metadata[idx]
                doc = self._bm25_corpus[idx]

                # Filter if requested
                if source_type and meta.get("source_type") != source_type:
                    continue
                if product_version and meta.get("product_version") != product_version:
                    continue

                sparse_ranked_ids.append(cid)
                sparse_docs_map[cid] = (doc, meta)
                if len(sparse_ranked_ids) >= top_k * 3:
                    break

        # 3. Reciprocal Rank Fusion (RRF)
        # score = 0.55 * (1 / (60 + dense_rank)) + 0.45 * (1 / (60 + sparse_rank))
        rrf_scores: dict[str, float] = {}
        all_candidate_ids = set(dense_ranked_ids) | set(sparse_ranked_ids)

        for cid in all_candidate_ids:
            score = 0.0
            if cid in dense_ranked_ids:
                rank_dense = dense_ranked_ids.index(cid) + 1
                score += 0.55 * (1.0 / (60.0 + rank_dense))
            if cid in sparse_ranked_ids:
                rank_sparse = sparse_ranked_ids.index(cid) + 1
                score += 0.45 * (1.0 / (60.0 + rank_sparse))
            rrf_scores[cid] = score

        # Sort candidate IDs by fused score descending
        sorted_cids = sorted(
            all_candidate_ids,
            key=lambda cid: rrf_scores[cid],
            reverse=True,
        )[:top_k]

        # 4. Construct results
        results: list[KBChunkResult] = []
        for cid in sorted_cids:
            if cid in dense_docs_map:
                doc_text, meta = dense_docs_map[cid]
            elif cid in sparse_docs_map:
                doc_text, meta = sparse_docs_map[cid]
            else:
                continue

            prod_ver = meta.get("product_version")
            doc_date = meta.get("doc_date")
            stale_warning = self.check_staleness(prod_ver, doc_date)

            # Normalize RRF score to 0..1 scale approximately
            # Max possible single RRF is 1/61 ~ 0.01639
            raw_score = rrf_scores[cid]
            norm_score = min(round(raw_score / 0.01639, 3), 1.0)

            results.append(
                KBChunkResult(
                    chunk_id=cid,
                    document_name=meta.get("document_name", "Unknown"),
                    source_type=meta.get("source_type", "unknown"),
                    product=meta.get("product"),
                    product_version=prod_ver,
                    doc_date=doc_date,
                    snippet=doc_text,
                    score=norm_score,
                    stale_warning=stale_warning,
                )
            )

        return results


# Module-level singleton
_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    """Return the singleton instance of HybridRetriever."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
