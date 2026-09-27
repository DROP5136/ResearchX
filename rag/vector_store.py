"""ChromaDB vector store wrapper."""

from __future__ import annotations

from typing import Any

from config import Settings, get_settings
from utils.logging import get_logger

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

    def query(self, embedding: list[float], n_results: int = 5) -> dict[str, Any]:
        coll = self._ensure()
        return coll.query(query_embeddings=[embedding], n_results=n_results)

    def count(self) -> int:
        return int(self._ensure().count())
