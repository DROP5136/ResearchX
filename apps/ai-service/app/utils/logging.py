"""Structured logging for ResearchX agents and pipeline."""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Generator, Iterator

from app.config import get_settings


def setup_logging(level: str | None = None) -> logging.Logger:
    """Configure root logger for ResearchX."""
    settings = get_settings()
    log_level = (level or settings.log_level).upper()
    logger = logging.getLogger("researchx")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    return logger


def get_logger(name: str = "researchx") -> logging.Logger:
    """Get a named child logger."""
    setup_logging()
    return logging.getLogger(name)


@contextmanager
def log_event(
    agent: str,
    event: str,
    research_id: str = "",
    **extra: Any,
) -> Generator[dict[str, Any], None, None]:
    """Context manager that logs start/end with duration."""
    logger = get_logger(f"researchx.{agent}")
    payload: dict[str, Any] = {
        "research_id": research_id,
        "agent": agent,
        "event": event,
        "status": "started",
        **extra,
    }
    logger.info("%s | %s", event, _fmt(payload))
    start = time.perf_counter()
    try:
        yield payload
        payload["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "error"
        payload["error"] = str(exc)
        logger.exception("%s failed | %s", event, _fmt(payload))
        raise
    finally:
        payload["duration"] = round(time.perf_counter() - start, 3)
        if payload.get("status") == "ok":
            logger.info("%s done | %s", event, _fmt(payload))


def _fmt(payload: dict[str, Any]) -> str:
    safe = {
        k: v
        for k, v in payload.items()
        if k.lower() not in {"password", "api_key", "secret", "token", "key"}
    }
    return " | ".join(f"{k}={v}" for k, v in safe.items())
