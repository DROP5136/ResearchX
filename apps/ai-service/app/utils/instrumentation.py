"""Lightweight stage timing instrumentation for ResearchX workflow nodes."""

from __future__ import annotations

import time
from typing import Any, Callable


def timed_stage(
    meta: dict[str, Any],
    stage: str,
    fn: Callable[[], dict[str, Any]],
    *,
    items: int | None = None,
) -> dict[str, Any]:
    """Run fn, record success/failure + elapsed seconds into meta['stage_timings']."""
    timings = dict(meta.get("stage_timings") or {})
    start = time.perf_counter()
    success = True
    error = ""
    result: dict[str, Any] = {}
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001
        success = False
        error = str(exc)
        raise
    finally:
        elapsed = round(time.perf_counter() - start, 4)
        entry: dict[str, Any] = {
            "execution_time_sec": elapsed,
            "success": success,
        }
        if items is not None:
            entry["items_processed"] = items
        if error:
            entry["error"] = error
        prev = timings.get(stage)
        if isinstance(prev, dict) and "execution_time_sec" in prev:
            entry["execution_time_sec"] = round(
                float(prev["execution_time_sec"]) + elapsed, 4
            )
            entry["runs"] = int(prev.get("runs", 1)) + 1
            if items is not None:
                entry["items_processed"] = int(prev.get("items_processed", 0)) + items
        else:
            entry["runs"] = 1
        timings[stage] = entry

    out_meta = dict((result or {}).get("meta") or meta)
    out_meta["stage_timings"] = timings
    result = dict(result or {})
    result["meta"] = out_meta
    return result
