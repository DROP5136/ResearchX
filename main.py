#!/usr/bin/env python3
"""ResearchX CLI — Multi-Agent AI Research & Intelligence Platform (Python engine)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as `python main.py`
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_settings
from graph.workflow import ResearchWorkflow
from schemas.research import ResearchDepth, ResearchQuery
from utils.logging import setup_logging


BANNER = """ResearchX
--------------------------------"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="researchx",
        description="ResearchX multi-agent research engine (Python AI pipeline)",
    )
    parser.add_argument("query", nargs="?", default="", help="Research question")
    parser.add_argument(
        "--depth",
        choices=["quick", "standard", "deep"],
        default="standard",
        help="Research depth (default: standard)",
    )
    parser.add_argument(
        "--file",
        "-f",
        action="append",
        default=[],
        help="Optional PDF path for hybrid research (repeatable)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (no external LLM/search calls)",
    )
    parser.add_argument(
        "--requirement",
        "-r",
        action="append",
        default=[],
        help="Extra research requirement (repeatable)",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "groq", "gemini", "mock"],
        default=None,
        help="Override LLM_PROVIDER for this run",
    )
    parser.add_argument(
        "--search-provider",
        choices=["duckduckgo", "tavily", "serper"],
        default=None,
        help="Override SEARCH_PROVIDER for this run",
    )
    parser.add_argument(
        "--demo-quant",
        action="store_true",
        help="Run a deterministic quantitative-analysis demo (no LLM/search required)",
    )
    parser.add_argument(
        "--show-analysis",
        action="store_true",
        help="Print analysis / datapoint summary after a research run",
    )
    return parser


def run_quant_demo() -> int:
    """Offline demo of extract → normalize → pandas calc → chart JSON."""
    from analysis.engine import run_quantitative_pipeline
    from analysis.normalize import normalize_value
    from analysis.validate import validate_datapoints
    from schemas.report import DataPoint
    from utils.helpers import new_id

    print(BANNER)
    print("Quantitative Analysis Demo")
    print("Sample revenues 2022-2025 for three companies\n")

    raw_rows = [
        ("Company A", "revenue", 100, "million USD", "2022"),
        ("Company A", "revenue", 120, "million USD", "2023"),
        ("Company A", "revenue", 150, "million USD", "2024"),
        ("Company A", "revenue", 180, "million USD", "2025"),
        ("Company B", "revenue", 80, "million USD", "2022"),
        ("Company B", "revenue", 100, "million USD", "2023"),
        ("Company B", "revenue", 130, "million USD", "2024"),
        ("Company B", "revenue", 160, "million USD", "2025"),
        ("Company C", "revenue", 5.0, "billion USD", "2022"),  # = 5000 million
        ("Company C", "revenue", 5.5, "billion USD", "2023"),
        ("Company C", "revenue", 6.0, "billion USD", "2024"),
        ("Company C", "revenue", 6.5, "billion USD", "2025"),
    ]
    points: list[DataPoint] = []
    for entity, metric, value, unit, period in raw_rows:
        norm = normalize_value(float(value), unit)
        points.append(
            DataPoint(
                datapoint_id=new_id("DP"),
                metric=metric,
                entity=entity,
                value=float(value),
                unit=unit,
                period=period,
                source_id=f"SRC_{entity.replace(' ', '').lower()}",
                evidence_id=new_id("EVD"),
                confidence=0.9,
                normalized_value=norm.value,
                normalized_unit=norm.unit,
                normalization_notes=norm.notes,
            )
        )
    points = validate_datapoints(points)
    results, dataset = run_quantitative_pipeline(points)

    print(f"Datapoints: {len(points)}")
    for p in points[:4]:
        print(
            f"  - {p.entity} {p.metric} {p.period}: {p.value} {p.unit} "
            f"-> {p.normalized_value:g} {p.normalized_unit} [{p.source_id}]"
        )
    print(f"\nDataset rows: {len(dataset.rows)}")
    print(f"Analysis results: {len(results)}\n")
    for r in results:
        if r.status != "ok":
            continue
        print(f"[{r.analysis_type}] {r.metric}")
        print(f"  formula: {r.formula}")
        print(f"  result:  {r.result}")
        print(f"  sources: {r.source_ids}")
        if r.chart_data:
            print(
                f"  chart:   type={r.chart_data.chart_type} title={r.chart_data.title!r} "
                f"points={len(r.chart_data.data)}"
            )
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    # Avoid Windows cp1252 crashes on unicode progress glyphs
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.demo_quant:
        return run_quant_demo()

    if not args.query:
        parser.print_help()
        return 1

    setup_logging()
    # Clear cached settings so CLI flags take effect
    get_settings.cache_clear()
    settings = get_settings()

    if args.mock:
        settings.mock_mode = True
        settings.llm_provider = "mock"
    if args.provider:
        settings.llm_provider = args.provider
        if args.provider == "mock":
            settings.mock_mode = True
    if args.search_provider:
        settings.search_provider = args.search_provider

    print(BANNER)
    print(f"Query : {args.query}")
    print(f"Depth : {args.depth}")
    print(f"Mode  : {'MOCK' if settings.mock_mode else settings.llm_provider}")
    print(flush=True)

    def on_progress(msg: str) -> None:
        print(msg)

    import logging

    logging.getLogger("researchx.graph").setLevel(logging.WARNING)

    query = ResearchQuery(
        query=args.query,
        depth=ResearchDepth(args.depth),
        requirements=list(args.requirement or []),
        pdf_paths=list(args.file or []),
    )

    workflow = ResearchWorkflow(settings=settings, progress_callback=on_progress)
    try:
        state = workflow.run(query)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"\nResearch failed: {exc}", file=sys.stderr)
        return 2

    out = (state.get("meta") or {}).get("output_dir")
    if out:
        print(f"\nDone. Open: {Path(out) / 'report.md'}")

    if args.show_analysis:
        dps = state.get("datapoints") or []
        analysis = state.get("analysis") or []
        print(f"\n--- Analysis summary ---")
        print(f"Datapoints: {len(dps)}")
        for a in analysis:
            if getattr(a, "status", "") == "skipped":
                print(f"Skipped: {a.interpretation}")
                continue
            print(f"- {a.metric}: {a.result} (sources={a.source_ids})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
