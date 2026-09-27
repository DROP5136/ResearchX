"""Unit tests for PDF chunking, parsing, and RAG metadata."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.rag.pipeline import DocumentRAGPipeline, chunk_text
from app.tools.document_parser import DocumentParser

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_report.pdf"


def test_chunk_text_overlap():
    text = " ".join(["word"] * 200)
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) >= 2
    assert all(chunks)


def test_parse_pdf_preserves_pages_and_stable_id():
    assert FIXTURE.exists()
    parsed = DocumentParser().parse_pdf(FIXTURE, document_id="doc_test_001")
    assert parsed["document_id"] == "doc_test_001"
    assert parsed["page_count"] >= 2
    assert any("2024 revenue" in p["text"] for p in parsed["pages"])
    assert any("Ignore previous instructions" in p["text"] for p in parsed["pages"])


def test_reject_non_pdf(tmp_path: Path):
    bad = tmp_path / "note.txt"
    bad.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        DocumentParser().parse_pdf(bad)


def test_ingest_keeps_page_chunk_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Use a temp chroma path so tests do not touch shared store."""
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("DOCUMENTS_PATH", str(tmp_path / "docs"))
    get_settings.cache_clear()

    settings = get_settings()
    rag = DocumentRAGPipeline(settings=settings)
    parsed = rag.ingest_pdf(FIXTURE, document_id="doc_test_002", original_filename="sample_report.pdf")
    assert parsed["chunk_count"] > 0

    # Second ingest should skip re-embed
    again = rag.ingest_pdf(FIXTURE, document_id="doc_test_002", original_filename="sample_report.pdf")
    assert again.get("skipped_reembed") is True

    sources = rag.retrieve_sources("DemoCo 2024 revenue", document_ids=["doc_test_002"], top_k=4)
    assert sources
    for s in sources:
        assert s.source_type.value == "pdf"
        assert s.metadata.get("document_id") == "doc_test_002"
        assert s.metadata.get("page") is not None
        assert s.metadata.get("chunk_id")
        assert "Document:" in str(s.metadata.get("citation") or "")
