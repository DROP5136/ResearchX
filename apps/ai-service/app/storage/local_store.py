"""Simple file-based cache and research output store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.utils.helpers import hash_key, utc_now
from app.utils.logging import get_logger

logger = get_logger("researchx.storage")


class FileCache:
    """JSON file cache under CACHE_PATH."""

    def __init__(self, namespace: str = "default"):
        settings = get_settings()
        self.root = settings.cache_dir / namespace
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, *parts: str) -> Any | None:
        key = hash_key(*parts)
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("value")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache read failed for %s: %s", key[:12], exc)
            return None

    def set(self, *parts: str, value: Any) -> str:
        key = hash_key(*parts)
        path = self._path(key)
        payload = {
            "key": key,
            "parts": list(parts),
            "cached_at": utc_now().isoformat(),
            "value": value,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
        return key

    def has(self, *parts: str) -> bool:
        return self._path(hash_key(*parts)).exists()


class LocalStore:
    """Save research artifacts as JSON/Markdown under OUTPUT_PATH."""

    def __init__(self, research_id: str):
        settings = get_settings()
        self.research_id = research_id
        self.dir = settings.output_dir / research_id
        self.dir.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.dir.exists() and (
            (self.dir / "session.json").exists()
            or (self.dir / "report.json").exists()
            or (self.dir / "sources.json").exists()
        )

    def write_json(self, name: str, data: Any) -> Path:
        path = self.dir / name
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path

    def write_text(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def read_json(self, name: str) -> Any | None:
        path = self.dir / name
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed reading %s: %s", path.name, exc)
            return None

    def read_text(self, name: str) -> str | None:
        path = self.dir / name
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed reading %s: %s", path.name, exc)
            return None

    def load_session(self) -> dict[str, Any] | None:
        data = self.read_json("session.json")
        return data if isinstance(data, dict) else None

    def save_session(self, session: dict[str, Any]) -> Path:
        session = dict(session)
        session.setdefault("research_id", self.research_id)
        session["updated_at"] = utc_now().isoformat()
        return self.write_json("session.json", session)

    def update_session(self, **fields: Any) -> dict[str, Any]:
        session = self.load_session() or {"research_id": self.research_id}
        session.update(fields)
        self.save_session(session)
        return session

    def save_run(
        self,
        *,
        report_md: str,
        report_json: dict[str, Any],
        sources: list[dict[str, Any]],
        claims: list[dict[str, Any]],
        contradictions: list[dict[str, Any]],
        analysis: list[dict[str, Any]],
        evidence: list[dict[str, Any]] | None = None,
        datapoints: list[dict[str, Any]] | None = None,
        dataset: dict[str, Any] | None = None,
    ) -> Path:
        self.write_text("report.md", report_md)
        self.write_json("report.json", report_json)
        self.write_json("sources.json", sources)
        self.write_json("evidence.json", evidence or [])
        self.write_json("claims.json", claims)
        self.write_json("contradictions.json", contradictions)
        self.write_json("analysis.json", analysis)
        self.write_json("datapoints.json", datapoints or [])
        if dataset is not None:
            self.write_json("dataset.json", dataset)
        logger.info("Saved research outputs to %s", self.dir)
        return self.dir

    @classmethod
    def list_sessions(
        cls,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return lightweight session metadata from OUTPUT_PATH (newest first)."""
        settings = get_settings()
        root = settings.output_dir
        if not root.exists():
            return [], 0

        items: list[dict[str, Any]] = []
        dirs = sorted(
            [p for p in root.iterdir() if p.is_dir() and p.name.startswith("RES_")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for d in dirs:
            store = cls(d.name)
            session = store.load_session()
            if session is None:
                report = store.read_json("report.json") or {}
                if not report and not (d / "sources.json").exists():
                    continue
                session = {
                    "research_id": d.name,
                    "query": report.get("query") or "",
                    "status": "completed" if report else "unknown",
                    "created_at": utc_now().isoformat(),
                    "updated_at": utc_now().isoformat(),
                }
            if status and str(session.get("status", "")).lower() != status.lower():
                continue
            items.append(
                {
                    "research_id": session.get("research_id", d.name),
                    "query": session.get("query", ""),
                    "status": session.get("status", "unknown"),
                    "created_at": session.get("created_at"),
                    "updated_at": session.get("updated_at"),
                    "current_stage": session.get("current_stage"),
                }
            )

        total = len(items)
        return items[offset : offset + limit], total
