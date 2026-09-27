"""Quantitative analysis package."""

from app.analysis.charts import bar_chart, line_chart
from app.analysis.detect import requires_quantitative_analysis
from app.analysis.engine import (
    analyze_entity_comparison,
    analyze_market_share,
    analyze_time_series,
    build_dataset,
    datapoints_to_frame,
    run_quantitative_pipeline,
)
from app.analysis.extract import claims_to_datapoints
from app.analysis.metrics import Calculator
from app.analysis.normalize import normalize_value, parse_numeric, units_compatible
from app.analysis.statistics import safe_mean, safe_std
from app.analysis.validate import validate_datapoints

__all__ = [
    "Calculator",
    "analyze_entity_comparison",
    "analyze_market_share",
    "analyze_time_series",
    "bar_chart",
    "build_dataset",
    "claims_to_datapoints",
    "datapoints_to_frame",
    "line_chart",
    "normalize_value",
    "parse_numeric",
    "requires_quantitative_analysis",
    "run_quantitative_pipeline",
    "safe_mean",
    "safe_std",
    "units_compatible",
    "validate_datapoints",
]
