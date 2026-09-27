"""Optional Redis client for ResearchX AI service.

Redis is never required. If REDIS_URL is unset or unreachable, callers
receive None / False and must fall back to file/Mongo paths.
"""

from __future__ import annotations

import json
import threading
from typing import Any

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("researchx.redis")

_lock = threading.Lock()
_client: Any | None = None
_disabled = False
_hits = 0
_misses = 0


def reset_redis_state() -> None:
    """Test helper: clear cached client state."""
    global _client, _disabled, _hits, _misses
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:  # noqa: BLE001
                pass
        _client = None
        _disabled = False
        _hits = 0
        _misses = 0


def redis_enabled() -> bool:
    url = (get_settings().redis_url or "").strip()
    return bool(url) and not _disabled


def get_redis():
    """Return a Redis client or None when unavailable."""
    global _client, _disabled
    if not redis_enabled() and not (get_settings().redis_url or "").strip():
        return None
    if _disabled:
        return None
    with _lock:
        if _client is not None:
            return _client
        url = (get_settings().redis_url or "").strip()
        if not url:
            return None
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            client.ping()
            _client = client
            logger.info("Redis connected")
            return _client
        except Exception as exc:  # noqa: BLE001
            _disabled = True
            _client = None
            logger.warning("Redis unavailable; continuing without cache (%s)", type(exc).__name__)
            return None


def redis_ping() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:  # noqa: BLE001
        return False


def cache_get(key: str) -> Any | None:
    global _hits, _misses
    client = get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            _misses += 1
            return None
        _hits += 1
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Redis get failed: %s", exc)
        return None


def cache_set(key: str, value: Any, ttl_seconds: int | None = None) -> bool:
    client = get_redis()
    if client is None:
        return False
    ttl = ttl_seconds if ttl_seconds is not None else int(get_settings().redis_ttl_seconds)
    try:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        client.setex(key, max(1, ttl), payload)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("Redis set failed: %s", exc)
        return False


def cache_stats() -> dict[str, int]:
    return {"hits": _hits, "misses": _misses}


def job_progress_key(research_id: str) -> str:
    return f"research:progress:{research_id}"


def set_job_progress(research_id: str, payload: dict[str, Any], ttl_seconds: int = 7200) -> None:
    """Short-lived job progress mirror (Mongo/files remain source of truth)."""
    cache_set(job_progress_key(research_id), payload, ttl_seconds=ttl_seconds)


def get_job_progress(research_id: str) -> dict[str, Any] | None:
    data = cache_get(job_progress_key(research_id))
    return data if isinstance(data, dict) else None
