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

    def ingest_pdf(
        self,
        path: str | Path,
        *,
        document_id: str | None = None,
        original_filename: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        path = Path(path)
        parsed = self.parser.parse_pdf(path, document_id=document_id)
        doc_id = str(parsed["document_id"])

        # Avoid re-embedding unchanged documents
        existing = self.store.count_for_document(doc_id)
        if existing > 0 and not force:
            logger.info("Skipping re-embed for %s (%d chunks already indexed)", doc_id, existing)
            parsed["chunk_count"] = existing
            parsed["skipped_reembed"] = True
            return parsed

        if existing > 0 and force:
            self.store.delete_document(doc_id)

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        display_title = (original_filename or parsed.get("title") or path.stem).replace(".pdf", "")

        for page in parsed["pages"]:
            page_chunks = chunk_text(page["text"])
            for idx, chunk in enumerate(page_chunks):
                chunk_id = f"{doc_id}_p{page['page']}_c{idx}"
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append(
                    {
                        "document_id": doc_id,
                        "page": int(page["page"]),
                        "chunk_id": chunk_id,
                        "title": display_title,
                        "filename": original_filename or path.name,
                        # Store relative-ish path key only — never bind clients to absolute FS paths
                        "storage_key": path.name,
                    }
                )

        if not documents:
            logger.warning("No text extracted from %s", path)
            parsed["chunk_count"] = 0
            return parsed

        embeddings = self.embedder.embed(documents)
        # Chroma rejects numpy scalar types — coerce to plain Python floats
        embeddings = [[float(x) for x in row] for row in embeddings]
        self.store.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        parsed["chunk_count"] = len(documents)
        parsed["title"] = display_title
        parsed["skipped_reembed"] = False
        logger.info("Ingested %s (%d chunks)", path, len(documents))
        return parsed

    def retrieve_sources(
        self,
        query: str,
        *,
        document_ids: list[str] | None = None,
        top_k: int = 6,
    ) -> list[Source]:
        hits = self.retriever.retrieve(query, top_k=top_k, document_ids=document_ids)
        sources: list[Source] = []
        for hit in hits:
            meta = hit.get("metadata") or {}
            filename = str(meta.get("filename") or meta.get("title") or "Uploaded PDF")
            page = meta.get("page")
            source = Source(
                source_id=new_id("SRC"),
                url="",
                title=filename,
                domain="local-pdf",
                source_type=SourceType.PDF,
                retrieved_at=utc_now(),
                content=hit.get("text") or "",
                snippet=(hit.get("text") or "")[:280],
                metadata={
                    "source_kind": "document",
                    "document_id": meta.get("document_id"),
                    "page": page,
                    "chunk_id": meta.get("chunk_id") or hit.get("chunk_id"),
                    "filename": filename,
                    "citation": f"[Document: {filename}, p. {page}]" if page else f"[Document: {filename}]",
                },
            )
            sources.append(enrich_source(source, query, preserve_type=True))
        return sources

    def ingest_and_retrieve(
        self,
        paths: list[str],
        query: str,
        top_k: int = 6,
        *,
        document_ids: list[str] | None = None,
        path_document_ids: dict[str, str] | None = None,
    ) -> list[Source]:
        ingested_ids: list[str] = []
        for p in paths:
            try:
                doc_id = None
                if path_document_ids:
                    doc_id = path_document_ids.get(p) or path_document_ids.get(str(Path(p).resolve()))
                parsed = self.ingest_pdf(p, document_id=doc_id)
                ingested_ids.append(str(parsed["document_id"]))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to ingest %s: %s", p, exc)
        filter_ids = document_ids or ingested_ids or None
        return self.retrieve_sources(query, document_ids=filter_ids, top_k=top_k)

    def delete_document(self, document_id: str) -> int:
        return self.store.delete_document(document_id)
