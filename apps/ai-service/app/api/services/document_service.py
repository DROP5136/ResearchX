"""Document processing service — wraps existing DocumentRAGPipeline."""

from __future__ import annotations

from pathlib import Path

from app.api.errors import APIError
from app.api.schemas.documents import DocumentProcessRequest
from app.config import get_settings
from app.rag.pipeline import DocumentRAGPipeline
from app.utils.logging import get_logger

logger = get_logger("researchx.api.documents")


class DocumentService:
    def process(self, body: DocumentProcessRequest) -> dict:
        settings = get_settings()
        path = Path(body.path)
        if not path.is_absolute():
            # Resolve relative paths against monorepo documents dir
            path = (settings.documents_dir / path).resolve()
        else:
            path = path.resolve()

        # Constrain to documents_dir (or its parents under data/) for safety
        docs_root = settings.documents_dir.resolve()
        try:
            path.relative_to(docs_root)
        except ValueError as exc:
            raise APIError(
                "INVALID_DOCUMENT_PATH",
                "Document path is outside the allowed documents directory",
                status_code=400,
            ) from exc

        if not path.exists():
            raise APIError("DOCUMENT_NOT_FOUND", "PDF file not found on disk", status_code=404)

        try:
            rag = DocumentRAGPipeline(settings=settings)
            parsed = rag.ingest_pdf(
                path,
                document_id=body.document_id,
                original_filename=body.original_filename,
                force=body.force,
            )
        except ValueError as exc:
            raise APIError("DOCUMENT_INVALID", str(exc), status_code=400) from exc
        except FileNotFoundError as exc:
            raise APIError("DOCUMENT_NOT_FOUND", str(exc), status_code=404) from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("Document processing failed: %s", exc)
            raise APIError("DOCUMENT_PROCESS_FAILED", "Failed to process document", status_code=500) from exc

        chunk_count = int(parsed.get("chunk_count") or 0)
        if chunk_count == 0 and not parsed.get("skipped_reembed"):
            raise APIError(
                "DOCUMENT_EMPTY",
                "No extractable text found in PDF (scanned/image-only PDFs are not supported)",
                status_code=422,
            )

        return {
            "document_id": str(parsed["document_id"]),
            "status": "ready",
            "page_count": int(parsed.get("page_count") or 0),
            "chunk_count": chunk_count,
            "skipped_reembed": bool(parsed.get("skipped_reembed")),
            "stage": "completed",
            "error": None,
            "title": str(parsed.get("title") or ""),
        }

    def delete(self, document_id: str) -> dict:
        rag = DocumentRAGPipeline(settings=get_settings())
        deleted = rag.delete_document(document_id)
        return {"document_id": document_id, "deleted_chunks": deleted}
