"""Cancel research job — soft stop at progress checkpoints."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.api.dependencies import get_research_service
from app.api.main import app
from app.config import get_settings


def test_cancel_research_job(tmp_path, monkeypatch):
    get_settings.cache_clear()
    get_research_service.cache_clear()
    monkeypatch.setenv("OUTPUT_PATH", str(tmp_path / "outputs"))
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache"))
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    (tmp_path / "outputs").mkdir()
    (tmp_path / "cache").mkdir()
    get_settings.cache_clear()
    get_research_service.cache_clear()

    with TestClient(app) as client:
        start = client.post(
            "/api/v1/research",
            json={"query": "Cancel me soon please", "mock_mode": True, "depth": "deep"},
        )
        assert start.status_code == 202
        rid = start.json()["research_id"]

        cancel = client.post(f"/api/v1/research/{rid}/cancel")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        # Allow background thread to notice cancel
        deadline = time.time() + 10
        last = cancel.json()
        while time.time() < deadline:
            last = client.get(f"/api/v1/research/{rid}/status").json()
            if last["status"] == "cancelled":
                break
            time.sleep(0.1)
        assert last["status"] == "cancelled"

    get_research_service.cache_clear()
    get_settings.cache_clear()
