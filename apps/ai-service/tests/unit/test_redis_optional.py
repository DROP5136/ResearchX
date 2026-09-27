"""Optional Redis + FileCache behavior."""

from __future__ import annotations

from app.config import get_settings
from app.storage.local_store import FileCache
from app.storage import redis_client


def test_file_cache_works_without_redis(tmp_path, monkeypatch):
    redis_client.reset_redis_state()
    get_settings.cache_clear()
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache"))
    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()
    redis_client.reset_redis_state()

    cache = FileCache("search")
    cache.set("q1", "duckduckgo", value=[{"url": "https://example.com"}])
    assert cache.get("q1", "duckduckgo") == [{"url": "https://example.com"}]
    assert redis_client.redis_ping() is False


def test_redis_unavailable_is_soft_fail(tmp_path, monkeypatch):
    redis_client.reset_redis_state()
    get_settings.cache_clear()
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache2"))
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:59999/0")
    get_settings.cache_clear()
    redis_client.reset_redis_state()

    assert redis_client.get_redis() is None
    assert redis_client.cache_set("k", {"v": 1}) is False
    assert redis_client.cache_get("k") is None

    cache = FileCache("page")
    cache.set("url", value="<html/>")
    assert cache.get("url") == "<html/>"
