"""Quantitative analysis schemas — DataPoint, Dataset, ChartData, AnalysisResult."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AnalysisType(str, Enum):
    YOY = "yoy_growth"
    CAGR = "cagr"
    MARKET_SHARE = "market_share"
    RANKING = "ranking"
    COMPARISON = "comparison"
    TOTAL = "total"
    MEAN = "mean"
    PCT_CHANGE = "pct_change"
    INSUFFICIENT_DATA = "insufficient_data"
    SUMMARY = "summary"


class DataQualityFlag(str, Enum):
    DUPLICATE = "duplicate"
    CONFLICTING = "conflicting"
    MISSING_PERIOD = "missing_period"
    INCONSISTENT_UNIT = "inconsistent_unit"
    IMPOSSIBLE_VALUE = "impossible_value"
    NEGATIVE_UNEXPECTED = "negative_unexpected"
    OUTLIER = "outlier"
    INSUFFICIENT_FOR_CAGR = "insufficient_for_cagr"
    DIVISION_BY_ZERO = "division_by_zero"


class DataPoint(BaseModel):
    """A single numerical observation grounded in evidence."""

    datapoint_id: str
    metric: str
    entity: str | None = None
    value: float
    unit: str | None = None
    period: str | None = None
    source_id: str
    evidence_id: str | None = None
    claim_id: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    # Normalized representation
    normalized_value: float | None = None
    normalized_unit: str | None = None
    normalization_notes: str = ""
    flags: list[DataQualityFlag] = Field(default_factory=list)


class Dataset(BaseModel):
    """Tabular collection of related DataPoints."""

    name: str
    description: str = ""
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    datapoint_ids: list[str] = Field(default_factory=list)


class ChartSeries(BaseModel):
    name: str
    data: list[Any] = Field(default_factory=list)


class ChartData(BaseModel):
    """Frontend-ready chart JSON (Recharts-compatible)."""

    chart_type: str = "line"  # line | bar | grouped_bar | pie | donut | area
    title: str
    x_axis: str = ""
    y_axis: str = ""
    series: list[ChartSeries] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class ChartSpec(BaseModel):
    """Legacy chart shape kept for backward compatibility with report writer."""

    type: str = "line"
    title: str
    x: str = ""
    y: str = ""
    x_axis: str = ""
    y_axis: str = ""
    data: list[dict[str, Any]] = Field(default_factory=list)
    series: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sync_axis_aliases(self) -> ChartSpec:
        if not self.x_axis and self.x:
            self.x_axis = self.x
        if not self.y_axis and self.y:
            self.y_axis = self.y
        if not self.x and self.x_axis:
            self.x = self.x_axis
        if not self.y and self.y_axis:
            self.y = self.y_axis
        return self

    def to_chart_data(self) -> ChartData:
        return ChartData(
            chart_type=self.type,
            title=self.title,
            x_axis=self.x_axis or self.x,
            y_axis=self.y_axis or self.y,
            series=[ChartSeries(name=s, data=[]) for s in self.series],
            data=self.data,
            source_ids=self.source_ids,
        )


class AnalysisResult(BaseModel):
    """Structured quantitative analysis output with full traceability."""

    analysis_type: AnalysisType | str = AnalysisType.SUMMARY
    metric: str
    calculation: str = ""
    formula: str = ""
    result: float | dict[str, Any] | list[Any] | None = None
    values: list[Any] = Field(default_factory=list)
    input_data: list[dict[str, Any]] = Field(default_factory=list)
    interpretation: str = ""
    chart: ChartSpec | None = None
    chart_data: ChartData | None = None
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_claim_ids: list[str] = Field(default_factory=list)
    datapoint_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    flags: list[DataQualityFlag] = Field(default_factory=list)
    status: str = "ok"  # ok | insufficient_data | flagged


class ReportSection(BaseModel):
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    """Final citation-grounded research report."""

    research_id: str
    title: str
    query: str
    executive_summary: str = ""
    methodology: str = ""
    key_findings: list[str] = Field(default_factory=list)
    detailed_analysis: str = ""
    tables: list[dict[str, Any]] = Field(default_factory=list)
    trends: list[str] = Field(default_factory=list)
    contradictions_summary: str = ""
    limitations: list[str] = Field(default_factory=list)
    conclusion: str = ""
    references: list[dict[str, str]] = Field(default_factory=list)
    markdown: str = ""
    charts: list[ChartSpec] = Field(default_factory=list)
    chart_data: list[ChartData] = Field(default_factory=list)
    status_note: str = ""
