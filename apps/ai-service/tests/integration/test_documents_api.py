"""API-level document process + hybrid research wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import get_settings

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_report.pdf"
client = TestClient(app)


@pytest.fixture()
def docs_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    docs = tmp_path / "documents"
    chroma = tmp_path / "chroma"
    cache = tmp_path / "cache"
    outputs = tmp_path / "outputs"
    docs.mkdir()
    chroma.mkdir()
    cache.mkdir()
    outputs.mkdir()
    target = docs / "sample_report.pdf"
    target.write_bytes(FIXTURE.read_bytes())
    monkeypatch.setenv("CHROMA_PATH", str(chroma))
    monkeypatch.setenv("DOCUMENTS_PATH", str(docs))
    monkeypatch.setenv("CACHE_PATH", str(cache))
    monkeypatch.setenv("OUTPUT_PATH", str(outputs))
    get_settings.cache_clear()
    yield {"docs": docs, "target": target}
    get_settings.cache_clear()


def test_process_document_endpoint(docs_env: dict):
    target: Path = docs_env["target"]
    resp = client.post(
        "/api/v1/documents/process",
        json={
            "path": str(target.resolve()),
            "document_id": "507f1f77bcf86cd799439011",
            "original_filename": "sample_report.pdf",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ready"
    assert data["page_count"] >= 1
    assert data["chunk_count"] >= 1


def test_process_rejects_path_outside_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    docs = tmp_path / "allowed_docs"
    docs.mkdir()
    monkeypatch.setenv("DOCUMENTS_PATH", str(docs))
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma2"))
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache2"))
    monkeypatch.setenv("OUTPUT_PATH", str(tmp_path / "out2"))
    get_settings.cache_clear()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(FIXTURE.read_bytes())
    resp = client.post(
        "/api/v1/documents/process",
        json={"path": str(outside.resolve()), "document_id": "abc123"},
    )
    assert resp.status_code == 400


def test_hybrid_research_accepts_document_ids(docs_env: dict):
    target: Path = docs_env["target"]
    proc = client.post(
        "/api/v1/documents/process",
        json={
            "path": str(target.resolve()),
            "document_id": "507f191e810c19729de860ea",
            "original_filename": "sample_report.pdf",
        },
    )
    assert proc.status_code == 200, proc.text

    start = client.post(
        "/api/v1/research",
        json={
            "query": "What was DemoCo 2024 revenue?",
            "depth": "quick",
            "enable_web_search": False,
            "enable_document_research": True,
            "enable_pdf_rag": True,
            "mock_mode": True,
            "document_ids": ["507f191e810c19729de860ea"],
            "pdf_paths": [str(target.resolve())],
            "max_iterations": 0,
        },
    )
    assert start.status_code in (200, 202), start.text
    assert start.json()["research_id"]
