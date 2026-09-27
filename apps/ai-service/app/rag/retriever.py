"""Retriever over the document vector store."""

from __future__ import annotations

from typing import Any

from app.rag.embeddings import EmbeddingModel, get_embedder
from app.rag.vector_store import VectorStore


class Retriever:
    """Similarity search over ingested PDF chunks."""

    def __init__(
        self,
        store: VectorStore | None = None,
        embedder: EmbeddingModel | None = None,
    ):
        self.store = store or VectorStore()
        self.embedder = embedder or get_embedder()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if self.store.count() == 0:
            return []
        vec = self.embedder.embed_query(query)
        where: dict[str, Any] | None = None
        if document_ids:
            unique = [d for d in dict.fromkeys(document_ids) if d]
            if len(unique) == 1:
                where = {"document_id": unique[0]}
            elif len(unique) > 1:
                where = {"document_id": {"$in": unique}}
        # Over-fetch slightly when filtering to keep quality after filter
        n = top_k if not where else min(top_k * 2, max(top_k, 12))
        try:
            raw = self.store.query(vec, n_results=n, where=where)
        except Exception:
            # Older Chroma / empty filter edge cases — fall back to unfiltered
            raw = self.store.query(vec, n_results=n, where=None)
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        ids = (raw.get("ids") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]
        results = []
        allowed = set(document_ids) if document_ids else None
        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            if allowed is not None and meta.get("document_id") not in allowed:
                continue
            results.append(
                {
                    "chunk_id": ids[i] if i < len(ids) else f"CHUNK_{i}",
                    "text": doc,
                    "metadata": meta,
                    "distance": dists[i] if i < len(dists) else None,
                }
            )
            if len(results) >= top_k:
                break
        return results
