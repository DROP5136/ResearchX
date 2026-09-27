"""Path confinement tests for document processing."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.api.errors import APIError
from app.api.path_safety import resolve_documents_path, sanitize_pdf_paths
from app.config import get_settings


@pytest.fixture()
def docs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    docs = tmp_path / "documents"
    docs.mkdir()
    monkeypatch.setenv("DOCUMENTS_PATH", str(docs))
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache"))
    monkeypatch.setenv("OUTPUT_PATH", str(tmp_path / "outputs"))
    get_settings.cache_clear()
    yield docs
    get_settings.cache_clear()


def test_resolve_allows_inside(docs_root: Path):
    f = docs_root / "a.pdf"
    f.write_bytes(b"%PDF-1.4\n")
    resolved = resolve_documents_path(str(f), get_settings())
    assert resolved == f.resolve()


def test_resolve_rejects_outside(docs_root: Path, tmp_path: Path):
    outside = tmp_path / "secret.pdf"
    outside.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(APIError) as exc:
        resolve_documents_path(str(outside), get_settings())
    assert exc.value.code == "INVALID_DOCUMENT_PATH"


def test_sanitize_rejects_missing(docs_root: Path):
    with pytest.raises(APIError) as exc:
        sanitize_pdf_paths([str(docs_root / "missing.pdf")], get_settings())
    assert exc.value.code == "DOCUMENT_NOT_FOUND"
