"""Retriever over the document vector store."""

from __future__ import annotations

from typing import Any

from rag.embeddings import EmbeddingModel, get_embedder
from rag.vector_store import VectorStore


class Retriever:
    """Similarity search over ingested PDF chunks."""

    def __init__(
        self,
        store: VectorStore | None = None,
        embedder: EmbeddingModel | None = None,
    ):
        self.store = store or VectorStore()
        self.embedder = embedder or get_embedder()

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if self.store.count() == 0:
            return []
        vec = self.embedder.embed_query(query)
        raw = self.store.query(vec, n_results=top_k)
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        ids = (raw.get("ids") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]
        results = []
        for i, doc in enumerate(docs):
            results.append(
                {
                    "chunk_id": ids[i] if i < len(ids) else f"CHUNK_{i}",
                    "text": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else None,
                }
            )
        return results
