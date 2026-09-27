"""PDF document parser using PyMuPDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import get_settings
from app.utils.helpers import new_id
from app.utils.logging import get_logger

logger = get_logger("researchx.tools.pdf")


class DocumentParser:
    """Parse PDFs into page-level text with metadata."""

    def parse_pdf(self, path: str | Path, *, document_id: str | None = None) -> dict[str, Any]:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported")

        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise RuntimeError("PyMuPDF (fitz) is not installed") from exc

        with path.open("rb") as fh:
            header = fh.read(5)
        if header != b"%PDF-":
            raise ValueError("File does not appear to be a valid PDF")

        doc_id = (document_id or "").strip() or new_id("DOC")
        max_pages = max(1, int(get_settings().max_pdf_pages))
        pages: list[dict[str, Any]] = []
        with fitz.open(path) as doc:
            if len(doc) > max_pages:
                raise ValueError(f"PDF exceeds maximum of {max_pages} pages")
            for i, page in enumerate(doc):
                text = page.get_text("text") or ""
                pages.append(
                    {
                        "page": i + 1,
                        "text": text,
                        "char_count": len(text),
                    }
                )
        full_text = "\n\n".join(p["text"] for p in pages if p["text"].strip())
        return {
            "document_id": doc_id,
            "path": str(path.resolve()),
            "title": path.stem,
            "page_count": len(pages),
            "pages": pages,
            "text": full_text,
        }
