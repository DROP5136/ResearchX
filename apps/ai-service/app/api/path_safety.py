"""Shared path helpers — confine PDF access to the documents directory."""

from __future__ import annotations

from pathlib import Path

from app.api.errors import APIError
from app.config import Settings, get_settings


def resolve_documents_path(raw: str, settings: Settings | None = None) -> Path:
    """Resolve a path and ensure it stays under settings.documents_dir."""
    settings = settings or get_settings()
    path = Path(raw)
    if not path.is_absolute():
        path = (settings.documents_dir / path).resolve()
    else:
        path = path.resolve()

    docs_root = settings.documents_dir.resolve()
    try:
        path.relative_to(docs_root)
    except ValueError as exc:
        raise APIError(
            "INVALID_DOCUMENT_PATH",
            "Document path is outside the allowed documents directory",
            status_code=400,
        ) from exc
    return path


def sanitize_pdf_paths(paths: list[str], settings: Settings | None = None) -> list[str]:
    """Validate and normalize a list of PDF paths; drop empties."""
    out: list[str] = []
    for raw in paths or []:
        cleaned = (raw or "").strip()
        if not cleaned:
            continue
        resolved = resolve_documents_path(cleaned, settings)
        if not resolved.exists():
            raise APIError("DOCUMENT_NOT_FOUND", "PDF file not found on disk", status_code=404)
        out.append(str(resolved))
    return out
