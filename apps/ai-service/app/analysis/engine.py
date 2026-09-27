"""Deterministic Pandas/Numpy quantitative analysis engine (no LLM arithmetic)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.schemas.report import (
    AnalysisResult,
    AnalysisType,
    ChartData,
    ChartSeries,
    ChartSpec,
    DataPoint,
    DataQualityFlag,
    Dataset,
)
from app.tools.calculator import Calculator
from app.utils.logging import get_logger

logger = get_logger("researchx.analysis.engine")


def datapoints_to_frame(points: list[DataPoint]) -> pd.DataFrame:
    rows = []
    for p in points:
        rows.append(
            {
                "datapoint_id": p.datapoint_id,
                "metric": p.metric,
                "entity": p.entity or "",
                "value": p.normalized_value if p.normalized_value is not None else p.value,
                "raw_value": p.value,
                "unit": p.normalized_unit or p.unit or "",
                "period": p.period or "",
                "source_id": p.source_id,
                "evidence_id": p.evidence_id or "",
                "claim_id": p.claim_id or "",
                "confidence": p.confidence,
                "year": _extract_year(p.period),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "datapoint_id",
                "metric",
                "entity",
                "value",
                "raw_value",
                "unit",
                "period",
                "source_id",
                "evidence_id",
                "claim_id",
                "confidence",
                "year",
            ]
        )
    return pd.DataFrame(rows)


def _extract_year(period: str | None) -> int | None:
    if not period:
        return None
    digits = "".join(ch for ch in period if ch.isdigit())
    if len(digits) >= 4:
        try:
            return int(digits[:4])
        except ValueError:
            return None
    return None


def build_dataset(name: str, points: list[DataPoint], description: str = "") -> Dataset:
    df = datapoints_to_frame(points)
    rows = df.to_dict(orient="records") if not df.empty else []
    return Dataset(
        name=name,
        description=description,
        columns=list(df.columns) if not df.empty else [],
        rows=rows,
        source_ids=sorted({p.source_id for p in points}),
        datapoint_ids=[p.datapoint_id for p in points],
    )


def analyze_time_series(points: list[DataPoint]) -> list[AnalysisResult]:
    """YoY + CAGR per entity/metric group."""
    df = datapoints_to_frame(points)
    if df.empty:
        return [
            AnalysisResult(
                analysis_type=AnalysisType.INSUFFICIENT_DATA,
                metric="time_series",
                calculation="none",
                formula="",
                result=None,
                interpretation="No numerical datapoints available for time-series analysis.",
                status="insufficient_data",
                confidence=0.0,
            )
        ]

    results: list[AnalysisResult] = []
    grouped = df.groupby(["entity", "metric"], dropna=False)
    for (entity, metric), g in grouped:
        g2 = g.dropna(subset=["year"]).sort_values("year")
        if g2.empty:
            g2 = g.sort_values("period")
        if len(g2) < 2:
            continue

        # Deduplicate same year by mean (flag conflicts already set on points)
        if "year" in g2.columns and g2["year"].notna().any():
            g2 = g2.groupby("year", as_index=False).agg(
                {
                    "value": "mean",
                    "period": "first",
                    "datapoint_id": lambda s: list(s),
                    "source_id": lambda s: list(s),
                    "evidence_id": lambda s: list(s),
                    "claim_id": lambda s: list(s),
                }
            )
            g2 = g2.sort_values("year")

        values = [float(v) for v in g2["value"].tolist()]
        periods = [str(p) for p in g2["period"].tolist()]
        years = g2["year"].tolist() if "year" in g2.columns else [None] * len(values)

        yoy = Calculator.yoy_growth(values)
        flags: list[DataQualityFlag] = []
        cagr = None
        formula_cagr = "CAGR = (end/start)^(1/n) - 1"
        if len(values) >= 2:
            span = None
            if all(isinstance(y, (int, float)) and y == y for y in years):  # not NaN
                span = int(max(years) - min(years))  # type: ignore[arg-type]
            if span is None or span <= 0:
                span = len(values) - 1
            if span <= 0 or values[0] <= 0:
                flags.append(DataQualityFlag.INSUFFICIENT_FOR_CAGR)
            else:
                cagr = Calculator.cagr(values[0], values[-1], span)

        # Flatten id lists
        dp_ids: list[str] = []
        src_ids: list[str] = []
        ev_ids: list[str] = []
        cl_ids: list[str] = []
        for _, row in g2.iterrows():
            for field, bucket in (
                ("datapoint_id", dp_ids),
                ("source_id", src_ids),
                ("evidence_id", ev_ids),
                ("claim_id", cl_ids),
            ):
                val = row.get(field)
                if isinstance(val, list):
                    bucket.extend(str(x) for x in val if x)
                elif val:
                    bucket.append(str(val))

        chart_rows = [{"period": p, "value": v, "yoy_pct": y} for p, v, y in zip(periods, values, yoy)]
        chart = ChartSpec(
            type="line",
            title=f"{entity or 'Entity'} — {metric}",
            x="period",
            y="value",
            data=[{"period": r["period"], "value": r["value"]} for r in chart_rows],
            source_ids=sorted(set(src_ids)),
        )
        chart_data = ChartData(
            chart_type="line",
            title=chart.title,
            x_axis="Year / Period",
            y_axis=metric,
            series=[ChartSeries(name=str(entity or metric), data=values)],
            data=[{"period": p, str(entity or metric): v} for p, v in zip(periods, values)],
            source_ids=sorted(set(src_ids)),
        )

        results.append(
            AnalysisResult(
                analysis_type=AnalysisType.YOY,
                metric=f"{entity}:{metric}" if entity else str(metric),
                calculation="YoY + CAGR",
                formula="YoY = (current-previous)/previous*100; " + formula_cagr,
                result={"yoy_pct": yoy, "cagr": cagr, "periods": periods, "values": values},
                values=chart_rows,
                input_data=[
                    {
                        "period": p,
                        "value": v,
                        "datapoint_ids": dp_ids,
                    }
                    for p, v in zip(periods, values)
                ],
                chart=chart,
                chart_data=chart_data,
                source_ids=sorted(set(src_ids)),
                evidence_ids=sorted(set(x for x in ev_ids if x)),
                source_claim_ids=sorted(set(x for x in cl_ids if x)),
                datapoint_ids=sorted(set(dp_ids)),
                confidence=0.8,
                flags=flags,
                status="ok",
            )
        )
    if not results:
        results.append(
            AnalysisResult(
                analysis_type=AnalysisType.INSUFFICIENT_DATA,
                metric="time_series",
                calculation="none",
                interpretation="Insufficient time-series observations (need ≥2 periods per entity/metric).",
                status="insufficient_data",
                confidence=0.0,
                flags=[DataQualityFlag.INSUFFICIENT_FOR_CAGR],
            )
        )
    return results


def analyze_market_share(points: list[DataPoint]) -> list[AnalysisResult]:
    share_points = [p for p in points if "share" in (p.metric or "").lower()]
    if not share_points:
        return []

    # Prefer latest common period if available
    by_period: dict[str, list[DataPoint]] = {}
    for p in share_points:
        by_period.setdefault(p.period or "unknown", []).append(p)

    period = max(by_period.keys())  # lexical ok for years
    selected = by_period[period]
    shares: dict[str, float] = {}
    src_ids: list[str] = []
    ev_ids: list[str] = []
    cl_ids: list[str] = []
    dp_ids: list[str] = []
    for p in selected:
        entity = p.entity or "Unknown"
        shares[entity] = float(p.normalized_value if p.normalized_value is not None else p.value)
        src_ids.append(p.source_id)
        if p.evidence_id:
            ev_ids.append(p.evidence_id)
        if p.claim_id:
            cl_ids.append(p.claim_id)
        dp_ids.append(p.datapoint_id)

    ranked = Calculator.rank_desc(shares)
    data = [{"entity": k, "share": v} for k, v in ranked]
    chart = ChartSpec(
        type="bar",
        title=f"Market share comparison ({period})",
        x="entity",
        y="share",
        data=data,
        source_ids=sorted(set(src_ids)),
    )
    chart_data = ChartData(
        chart_type="bar",
        title=chart.title,
        x_axis="Entity",
        y_axis="Market Share (%)",
        series=[ChartSeries(name="share", data=[v for _, v in ranked])],
        data=data,
        source_ids=sorted(set(src_ids)),
    )
    # Also pie
    pie = ChartData(
        chart_type="pie",
        title=f"Market share distribution ({period})",
        x_axis="entity",
        y_axis="share",
        series=[ChartSeries(name="share", data=data)],
        data=data,
        source_ids=sorted(set(src_ids)),
    )
    return [
        AnalysisResult(
            analysis_type=AnalysisType.MARKET_SHARE,
            metric="market_share_ranking",
            calculation="rank_desc",
            formula="rank entities by reported share descending",
            result={"ranking": ranked, "period": period},
            values=data,
            input_data=[{"entity": k, "share": v} for k, v in ranked],
            chart=chart,
            chart_data=chart_data,
            source_ids=sorted(set(src_ids)),
            evidence_ids=sorted(set(ev_ids)),
            source_claim_ids=sorted(set(cl_ids)),
            datapoint_ids=dp_ids,
            confidence=0.75,
            status="ok",
        ),
        AnalysisResult(
            analysis_type=AnalysisType.MARKET_SHARE,
            metric="market_share_pie",
            calculation="distribution",
            formula="pie from reported shares",
            result={"period": period},
            values=data,
            chart_data=pie,
            source_ids=sorted(set(src_ids)),
            evidence_ids=sorted(set(ev_ids)),
            source_claim_ids=sorted(set(cl_ids)),
            datapoint_ids=dp_ids,
            confidence=0.7,
            status="ok",
        ),
    ]


def analyze_entity_comparison(points: list[DataPoint]) -> list[AnalysisResult]:
    """Compare entities on the same metric for a shared period (difference / pct)."""
    df = datapoints_to_frame(points)
    if df.empty or df["entity"].nunique() < 2:
        return []

    results: list[AnalysisResult] = []
    for metric, g in df.groupby("metric"):
        # Pick period with most entities
        if g["period"].nunique() == 0:
            continue
        period_counts = g.groupby("period")["entity"].nunique().sort_values(ascending=False)
        period = str(period_counts.index[0])
        slice_df = g[g["period"] == period]
        if slice_df["entity"].nunique() < 2:
            continue
        pivot = slice_df.groupby("entity")["value"].mean().sort_values(ascending=False)
        entities = list(pivot.index)
        values = [float(v) for v in pivot.tolist()]
        diffs = {}
        if len(values) >= 2 and values[1] != 0:
            diffs["leader_vs_second_pct"] = Calculator.pct_change(values[1], values[0])
        elif len(values) >= 2 and values[1] == 0:
            diffs["leader_vs_second_pct"] = None
            # flag division by zero for caller via result

        data = [{"entity": e, "value": v} for e, v in zip(entities, values)]
        src_ids = sorted(set(slice_df["source_id"].tolist()))
        chart_data = ChartData(
            chart_type="grouped_bar",
            title=f"{metric} comparison ({period})",
            x_axis="Entity",
            y_axis=str(metric),
            series=[ChartSeries(name=str(metric), data=values)],
            data=data,
            source_ids=src_ids,
        )
        results.append(
            AnalysisResult(
                analysis_type=AnalysisType.COMPARISON,
                metric=f"compare:{metric}:{period}",
                calculation="entity_difference",
                formula="pct_change(leader, second) = (leader-second)/second*100",
                result={"entities": entities, "values": values, **diffs},
                values=data,
                input_data=data,
                chart=ChartSpec(
                    type="bar",
                    title=chart_data.title,
                    x="entity",
                    y="value",
                    data=data,
                    source_ids=src_ids,
                ),
                chart_data=chart_data,
                source_ids=src_ids,
                evidence_ids=sorted(set(x for x in slice_df["evidence_id"].tolist() if x)),
                source_claim_ids=sorted(set(x for x in slice_df["claim_id"].tolist() if x)),
                datapoint_ids=list(slice_df["datapoint_id"].tolist()),
                confidence=0.75,
                flags=[DataQualityFlag.DIVISION_BY_ZERO]
                if diffs.get("leader_vs_second_pct") is None and len(values) >= 2
                else [],
                status="ok",
            )
        )
    return results


def summarize_descriptive(points: list[DataPoint]) -> list[AnalysisResult]:
    df = datapoints_to_frame(points)
    if df.empty:
        return []
    results = []
    for metric, g in df.groupby("metric"):
        vals = [float(v) for v in g["value"].tolist()]
        results.append(
            AnalysisResult(
                analysis_type=AnalysisType.SUMMARY,
                metric=f"summary:{metric}",
                calculation="descriptive",
                formula="sum / mean / min / max via numpy",
                result={
                    "sum": Calculator.total(vals),
                    "mean": Calculator.mean(vals),
                    "min": float(np.min(vals)),
                    "max": float(np.max(vals)),
                    "n": len(vals),
                },
                values=[{"entity": r.entity, "period": r.period, "value": r.value} for r in g.itertuples()],
                source_ids=sorted(set(g["source_id"].tolist())),
                evidence_ids=sorted(set(x for x in g["evidence_id"].tolist() if x)),
                source_claim_ids=sorted(set(x for x in g["claim_id"].tolist() if x)),
                datapoint_ids=list(g["datapoint_id"].tolist()),
                confidence=0.7,
                status="ok",
            )
        )
    return results


def run_quantitative_pipeline(points: list[DataPoint]) -> tuple[list[AnalysisResult], Dataset]:
    """Run the full deterministic analysis suite."""
    dataset = build_dataset(
        name="research_numeric_dataset",
        points=points,
        description="Normalized numerical observations extracted from verified claims.",
    )
    if not points:
        return (
            [
                AnalysisResult(
                    analysis_type=AnalysisType.INSUFFICIENT_DATA,
                    metric="quantitative",
                    calculation="none",
                    interpretation="INSUFFICIENT_DATA: no numerical datapoints extracted.",
                    status="insufficient_data",
                    confidence=0.0,
                )
            ],
            dataset,
        )

    results: list[AnalysisResult] = []
    results.extend(analyze_time_series(points))
    results.extend(analyze_market_share(points))
    results.extend(analyze_entity_comparison(points))
    # Only add descriptive if we don't already have richer results
    if not any(r.status == "ok" and r.analysis_type != AnalysisType.INSUFFICIENT_DATA for r in results):
        results.extend(summarize_descriptive(points))

    # Drop empty insufficient placeholders if we have real results
    real = [r for r in results if r.status == "ok"]
    if real:
        results = real + [r for r in results if r.status != "ok" and r.analysis_type != AnalysisType.INSUFFICIENT_DATA]
    logger.info("[Quant] Produced %d analysis results", len(results))
    return results, dataset
