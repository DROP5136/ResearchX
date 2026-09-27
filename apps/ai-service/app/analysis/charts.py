"""Chart-ready JSON builders."""

from __future__ import annotations

from typing import Any

from app.schemas.report import ChartData, ChartSeries, ChartSpec


def line_chart(title: str, x_key: str, y_key: str, data: list[dict[str, Any]]) -> ChartSpec:
    return ChartSpec(type="line", title=title, x=x_key, y=y_key, data=data)


def bar_chart(title: str, x_key: str, y_key: str, data: list[dict[str, Any]]) -> ChartSpec:
    return ChartSpec(type="bar", title=title, x=x_key, y=y_key, data=data)


def area_chart(title: str, x_key: str, y_key: str, data: list[dict[str, Any]]) -> ChartData:
    return ChartData(
        chart_type="area",
        title=title,
        x_axis=x_key,
        y_axis=y_key,
        data=data,
        series=[ChartSeries(name=y_key, data=[row.get(y_key) for row in data])],
    )


def grouped_bar_chart(
    title: str,
    x_axis: str,
    y_axis: str,
    series: list[ChartSeries],
    data: list[dict[str, Any]],
    source_ids: list[str] | None = None,
) -> ChartData:
    return ChartData(
        chart_type="grouped_bar",
        title=title,
        x_axis=x_axis,
        y_axis=y_axis,
        series=series,
        data=data,
        source_ids=source_ids or [],
    )
