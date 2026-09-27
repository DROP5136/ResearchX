"""Quantitative analysis unit + integration tests (deterministic, no LLM)."""

from __future__ import annotations

from app.analysis.detect import requires_quantitative_analysis
from app.analysis.engine import run_quantitative_pipeline
from app.analysis.extract import claims_to_datapoints
from app.analysis.normalize import normalize_value, parse_numeric, units_compatible
from app.analysis.validate import validate_datapoints
from app.schemas.claim import Claim, VerificationStatus
from app.schemas.report import AnalysisType, DataPoint, DataQualityFlag
from app.tools.calculator import Calculator
from app.utils.helpers import new_id


def test_parse_and_normalize_billion_million():
    assert parse_numeric("5.2") == 5.2
    assert parse_numeric("$5.2B") == 5.2e9
    a = normalize_value(5.2, "billion USD")
    b = normalize_value(5200, "million USD")
    assert abs(a.value - b.value) < 1e-6
    assert units_compatible(a.unit, b.unit)


def test_yoy_known_series():
    # Spec example: 100 → 120 → 150
    yoy = Calculator.yoy_growth([100, 120, 150])
    assert yoy[0] is None
    assert abs(yoy[1] - 20.0) < 1e-9
    assert abs(yoy[2] - 25.0) < 1e-9


def test_cagr_and_division_by_zero():
    assert Calculator.pct_change(0, 10) is None
    assert Calculator.cagr(0, 10, 2) is None
    assert abs(Calculator.cagr(100, 121, 2) - 0.1) < 1e-9


def test_market_share_and_ranking():
    assert abs(Calculator.market_share(25, 100) - 25.0) < 1e-9
    assert Calculator.market_share(1, 0) is None
    ranked = Calculator.rank_desc({"A": 10, "B": 30, "C": 20})
    assert ranked[0][0] == "B"


def test_detect_quant_vs_non_quant():
    assert requires_quantitative_analysis(
        "Analyze the Indian EV market from 2022 to 2026 and compare growth"
    )
    assert not requires_quantitative_analysis("What is the definition of an electric vehicle?")


def test_claims_to_datapoints_traceability():
    claims = [
        Claim(
            claim_id="CLM_1",
            claim="Company A revenue was 100 million USD in 2022.",
            entity="Company A",
            metric="revenue",
            value=100,
            unit="million USD",
            period="2022",
            source_ids=["SRC_1"],
            evidence_ids=["EVD_1"],
            confidence=0.9,
            verification_status=VerificationStatus.SUPPORTED,
        ),
        Claim(
            claim_id="CLM_2",
            claim="Company A revenue was 120 million USD in 2023.",
            entity="Company A",
            metric="revenue",
            value=120,
            unit="million USD",
            period="2023",
            source_ids=["SRC_1"],
            evidence_ids=["EVD_2"],
            confidence=0.9,
            verification_status=VerificationStatus.SUPPORTED,
        ),
    ]
    points = claims_to_datapoints(claims, question="Compare company revenue growth 2022-2023")
    assert len(points) == 2
    assert all(p.source_id == "SRC_1" for p in points)
    assert all(p.evidence_id for p in points)
    assert all(p.claim_id for p in points)


def test_duplicate_and_conflict_flags():
    pts = [
        DataPoint(
            datapoint_id=new_id("DP"),
            metric="share",
            entity="X",
            value=30,
            unit="%",
            period="2024",
            source_id="SRC_a",
            normalized_value=30,
            normalized_unit="percent",
        ),
        DataPoint(
            datapoint_id=new_id("DP"),
            metric="share",
            entity="X",
            value=30,
            unit="%",
            period="2024",
            source_id="SRC_b",
            normalized_value=30,
            normalized_unit="percent",
        ),
        DataPoint(
            datapoint_id=new_id("DP"),
            metric="share",
            entity="Y",
            value=40,
            unit="%",
            period="2024",
            source_id="SRC_c",
            normalized_value=40,
            normalized_unit="percent",
        ),
        DataPoint(
            datapoint_id=new_id("DP"),
            metric="share",
            entity="Y",
            value=55,
            unit="%",
            period="2024",
            source_id="SRC_d",
            normalized_value=55,
            normalized_unit="percent",
        ),
    ]
    pts = validate_datapoints(pts)
    assert any(DataQualityFlag.DUPLICATE in p.flags for p in pts if p.entity == "X")
    assert any(DataQualityFlag.CONFLICTING in p.flags for p in pts if p.entity == "Y")


def test_pipeline_yoy_and_chart_json():
    points = []
    for year, val in [(2022, 100), (2023, 120), (2024, 150)]:
        points.append(
            DataPoint(
                datapoint_id=new_id("DP"),
                metric="sales",
                entity="DemoCo",
                value=float(val),
                unit="units",
                period=str(year),
                source_id="SRC_demo",
                evidence_id=new_id("EVD"),
                claim_id=new_id("CLM"),
                confidence=0.9,
                normalized_value=float(val),
                normalized_unit="units",
            )
        )
    results, dataset = run_quantitative_pipeline(points)
    assert dataset.rows
    yoy_results = [r for r in results if r.analysis_type == AnalysisType.YOY and r.status == "ok"]
    assert yoy_results
    yoy = yoy_results[0].result["yoy_pct"]
    assert yoy[1] == 20.0
    assert yoy[2] == 25.0
    assert yoy_results[0].chart_data is not None
    assert yoy_results[0].chart_data.chart_type == "line"
    assert yoy_results[0].source_ids == ["SRC_demo"]
    assert yoy_results[0].datapoint_ids


def test_insufficient_data_no_fabrication():
    results, _ = run_quantitative_pipeline([])
    assert results
    assert results[0].status == "insufficient_data"
    assert results[0].analysis_type == AnalysisType.INSUFFICIENT_DATA
