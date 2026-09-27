"""FastAPI TestClient tests for ResearchX API (mock mode)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_research_service
from app.api.main import app
from app.api.services.research_service import ResearchService
from app.config import get_settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    get_settings.cache_clear()
    get_research_service.cache_clear()
    monkeypatch.setenv("OUTPUT_PATH", str(tmp_path / "outputs"))
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache"))
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "cache").mkdir(parents=True, exist_ok=True)
    get_settings.cache_clear()
    get_research_service.cache_clear()

    with TestClient(app) as c:
        yield c

    get_research_service.cache_clear()
    get_settings.cache_clear()


def _wait_completed(client: TestClient, research_id: str, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        resp = client.get(f"/api/v1/research/{research_id}/status")
        assert resp.status_code == 200
        last = resp.json()
        if last.get("status") in {"completed", "failed"}:
            return last
        time.sleep(0.1)
    return last


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "researchx"
    assert "providers" in data
    # secrets must not appear
    dumped = resp.text.lower()
    assert "gsk_" not in dumped
    assert "api_key" not in dumped or "configured" in dumped


def test_invalid_research_request(client: TestClient):
    resp = client.post("/api/v1/research", json={"query": ""})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "INVALID_REQUEST"


def test_research_not_found(client: TestClient):
    resp = client.get("/api/v1/research/RES_does_not_exist")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESEARCH_NOT_FOUND"


def test_mock_research_flow(client: TestClient):
    start = client.post(
        "/api/v1/research",
        json={
            "query": "Analyze the Indian EV market from 2022 to 2026",
            "mock_mode": True,
            "depth": "quick",
            "max_iterations": 1,
        },
    )
    assert start.status_code == 202
    payload = start.json()
    rid = payload["research_id"]
    assert payload["status"] == "started"
    assert rid.startswith("RES_")

    status = _wait_completed(client, rid)
    assert status["status"] == "completed"
    assert status["progress"] == 100

    result = client.get(f"/api/v1/research/{rid}")
    assert result.status_code == 200
    data = result.json()
    assert data["research_id"] == rid
    assert data["query"]
    assert isinstance(data.get("sources"), list)
    assert isinstance(data.get("claims"), list)
    meta = data.get("metadata") or {}
    assert "output_dir" not in meta

    sources = client.get(f"/api/v1/research/{rid}/sources")
    assert sources.status_code == 200
    assert isinstance(sources.json(), list)
    if sources.json():
        assert "source_id" in sources.json()[0]
        assert "url" in sources.json()[0]

    claims = client.get(f"/api/v1/research/{rid}/claims")
    assert claims.status_code == 200
    assert isinstance(claims.json(), list)

    report = client.get(f"/api/v1/research/{rid}/report")
    assert report.status_code == 200
    report_data = report.json()
    assert "executive_summary" in report_data or "markdown" in report_data

    listing = client.get("/api/v1/research", params={"limit": 5})
    assert listing.status_code == 200
    listed = listing.json()
    assert listed["total"] >= 1
    assert any(i["research_id"] == rid for i in listed["items"])


def test_evaluation_endpoints(client: TestClient, monkeypatch):
    # Keep evaluation short
    resp = client.post(
        "/api/v1/evaluation/run",
        json={"mock_mode": True, "limit": 1, "ids": ["B21"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["n"] == 1
    assert "overall" in data

    latest = client.get("/api/v1/evaluation/latest")
    assert latest.status_code == 200
    assert "overall" in latest.json()
