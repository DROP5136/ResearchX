"""Shared utility helpers."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """Generate a readable unique id like SRC_a1b2c3d4."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def research_id() -> str:
    stamp = utc_now().strftime("%Y%m%d_%H%M%S")
    return f"RES_{stamp}_{uuid.uuid4().hex[:6]}"


def hash_key(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:  # noqa: BLE001
        return ""


def safe_json_loads(text: str) -> Any:
    """Extract and parse JSON from LLM text that may include fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Find first JSON object/array
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
    if match:
        return json.loads(match.group(1))
    raise ValueError("No valid JSON found in LLM response")


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
