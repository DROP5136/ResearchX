"""Data quality validation for quantitative datapoints."""

from __future__ import annotations

from collections import defaultdict

from analysis.normalize import units_compatible
from schemas.report import DataPoint, DataQualityFlag


def validate_datapoints(points: list[DataPoint]) -> list[DataPoint]:
    """
    Flag (do not delete) quality issues on datapoints in-place.
    """
    # Group by entity+metric+period
    groups: dict[tuple[str, str, str], list[DataPoint]] = defaultdict(list)
    for p in points:
        key = (
            (p.entity or "").lower(),
            (p.metric or "").lower(),
            (p.period or "").lower(),
        )
        groups[key].append(p)

    for key, items in groups.items():
        if len(items) > 1:
            values = [i.normalized_value if i.normalized_value is not None else i.value for i in items]
            # duplicates same value
            if len(set(round(v, 6) for v in values)) == 1:
                for i in items:
                    if DataQualityFlag.DUPLICATE not in i.flags:
                        i.flags.append(DataQualityFlag.DUPLICATE)
            else:
                for i in items:
                    if DataQualityFlag.CONFLICTING not in i.flags:
                        i.flags.append(DataQualityFlag.CONFLICTING)

        # unit consistency within entity+metric
        units = {(i.normalized_unit or i.unit or "") for i in items}
        if len(units) > 1:
            unit_list = list(units)
            compatible = all(units_compatible(unit_list[0], u) for u in unit_list[1:])
            if not compatible:
                for i in items:
                    if DataQualityFlag.INCONSISTENT_UNIT not in i.flags:
                        i.flags.append(DataQualityFlag.INCONSISTENT_UNIT)

    for p in points:
        v = p.normalized_value if p.normalized_value is not None else p.value
        unit = (p.normalized_unit or p.unit or "").lower()
        if "percent" in unit or unit in {"%", "pct"}:
            if v < 0 or v > 100:
                # market share > 100 is impossible; growth can exceed 100 so only flag share-like
                if "share" in (p.metric or "").lower() and DataQualityFlag.IMPOSSIBLE_VALUE not in p.flags:
                    p.flags.append(DataQualityFlag.IMPOSSIBLE_VALUE)
        if v < 0 and "growth" not in (p.metric or "").lower() and "change" not in (p.metric or "").lower():
            if DataQualityFlag.NEGATIVE_UNEXPECTED not in p.flags:
                p.flags.append(DataQualityFlag.NEGATIVE_UNEXPECTED)

    # Simple outlier flag: within entity+metric, value > mean + 3*std-ish using range
    by_series: dict[tuple[str, str], list[DataPoint]] = defaultdict(list)
    for p in points:
        by_series[((p.entity or "").lower(), (p.metric or "").lower())].append(p)
    for _, items in by_series.items():
        if len(items) < 3:
            continue
        vals = [i.normalized_value if i.normalized_value is not None else i.value for i in items]
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / len(vals)
        std = var ** 0.5
        if std == 0:
            continue
        for i, v in zip(items, vals):
            if abs(v - mean) > 3 * std and DataQualityFlag.OUTLIER not in i.flags:
                i.flags.append(DataQualityFlag.OUTLIER)

    return points
