"""ChromaDB vector store wrapper."""

from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger("researchx.rag.vector_store")


class VectorStore:
    """Persistent Chroma collection for document chunks."""

    def __init__(self, collection_name: str = "researchx_docs", settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _ensure(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
        except ImportError as exc:
            raise RuntimeError("chromadb is not installed") from exc

        path = str(self.settings.chroma_dir)
        self._client = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def add(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        coll = self._ensure()
        coll.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def query(
        self,
        embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        coll = self._ensure()
        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        return coll.query(**kwargs)

    def count(self) -> int:
        return int(self._ensure().count())

    def count_for_document(self, document_id: str) -> int:
        """Return number of chunks already indexed for a document_id."""
        coll = self._ensure()
        try:
            result = coll.get(where={"document_id": document_id}, include=[])
            return len(result.get("ids") or [])
        except Exception:  # noqa: BLE001
            return 0

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document. Returns deleted count (best-effort)."""
        coll = self._ensure()
        try:
            existing = coll.get(where={"document_id": document_id}, include=[])
            ids = existing.get("ids") or []
            if ids:
                coll.delete(ids=ids)
            return len(ids)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to delete document %s from vector store: %s", document_id, exc)
            return 0
