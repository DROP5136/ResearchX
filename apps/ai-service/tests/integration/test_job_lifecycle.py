"""Job lifecycle status mapping for research service."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.api.dependencies import get_research_service
from app.api.main import app
from app.config import get_settings


def test_research_job_lifecycle_statuses(tmp_path, monkeypatch):
    get_settings.cache_clear()
    get_research_service.cache_clear()
    monkeypatch.setenv("OUTPUT_PATH", str(tmp_path / "outputs"))
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache"))
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("REDIS_URL", "")
    (tmp_path / "outputs").mkdir()
    (tmp_path / "cache").mkdir()
    get_settings.cache_clear()
    get_research_service.cache_clear()

    with TestClient(app) as client:
        start = client.post(
            "/api/v1/research",
            json={"query": "Job lifecycle smoke test", "mock_mode": True, "depth": "quick"},
        )
        assert start.status_code in {200, 202}
        body = start.json()
        rid = body["research_id"]
        assert body["status"] in {"queued", "started", "running"}

        deadline = time.time() + 60
        seen = set()
        last = {}
        while time.time() < deadline:
            st = client.get(f"/api/v1/research/{rid}/status").json()
            last = st
            seen.add(st.get("status"))
            if st.get("status") in {"completed", "failed"}:
                break
            time.sleep(0.1)

        assert last.get("status") == "completed"
        assert last.get("progress") == 100
        assert "queued" in seen or "running" in seen or "started" in seen

        result = client.get(f"/api/v1/research/{rid}").json()
        assert result.get("report") or result.get("sources") is not None

    get_research_service.cache_clear()
    get_settings.cache_clear()
