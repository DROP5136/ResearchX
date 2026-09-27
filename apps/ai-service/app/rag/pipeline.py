"""PDF → chunk → embed → Chroma → retrieve pipeline."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.evidence.source import enrich_source
from app.rag.embeddings import get_embedder
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.schemas.source import Source, SourceType
from app.tools.document_parser import DocumentParser
from app.utils.helpers import new_id, utc_now
from app.utils.logging import get_logger

logger = get_logger("researchx.rag.pipeline")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


class DocumentRAGPipeline:
    """Ingest PDFs and retrieve relevant passages as Source objects."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.parser = DocumentParser()
        self.embedder = get_embedder()
        self.store = VectorStore(settings=self.settings)
        self.retriever = Retriever(store=self.store, embedder=self.embedder)

    def ingest_pdf(self, path: str | Path) -> dict[str, Any]:
        parsed = self.parser.parse_pdf(path)
        doc_id = parsed["document_id"]
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for page in parsed["pages"]:
            page_chunks = chunk_text(page["text"])
            for idx, chunk in enumerate(page_chunks):
                chunk_id = f"{doc_id}_p{page['page']}_c{idx}"
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append(
                    {
                        "document_id": doc_id,
                        "page": page["page"],
                        "chunk_id": chunk_id,
                        "title": parsed["title"],
                        "path": parsed["path"],
                    }
                )

        if not documents:
            logger.warning("No text extracted from %s", path)
            return parsed

        embeddings = self.embedder.embed(documents)
        self.store.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        parsed["chunk_count"] = len(documents)
        logger.info("Ingested %s (%d chunks)", path, len(documents))
        return parsed

    def ingest_and_retrieve(self, paths: list[str], query: str, top_k: int = 6) -> list[Source]:
        for p in paths:
            try:
                self.ingest_pdf(p)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to ingest %s: %s", p, exc)
        hits = self.retriever.retrieve(query, top_k=top_k)
        sources: list[Source] = []
        for hit in hits:
            meta = hit.get("metadata") or {}
            source = Source(
                source_id=new_id("SRC"),
                url=f"file://{meta.get('path', '')}",
                title=str(meta.get("title") or "Uploaded PDF"),
                domain="local-pdf",
                source_type=SourceType.PDF,
                retrieved_at=utc_now(),
                content=hit.get("text") or "",
                snippet=(hit.get("text") or "")[:280],
                metadata={
                    "document_id": meta.get("document_id"),
                    "page": meta.get("page"),
                    "chunk_id": meta.get("chunk_id"),
                },
            )
            sources.append(enrich_source(source, query))
        return sources
