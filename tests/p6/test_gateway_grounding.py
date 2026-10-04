import pandas as pd
import pytest

from finahinking.p6.gateway import P6QuantGateway, RegressionEvidence
from finahinking.p6.grounding import claims_from_result, ground_numeric_claim
from finahinking.p6.hypothesis import build_hypothesis
from finahinking.p6.planner import plan_experiment


def test_momentum_gateway_returns_linked_normalized_evidence() -> None:
    rows = []
    for date, a, b in [
        ("2020-01-01", 100, 100),
        ("2020-01-02", 110, 95),
        ("2020-01-03", 121, 90),
        ("2020-01-04", 120, 92),
        ("2020-01-05", 130, 88),
    ]:
        rows.extend(
            [
                {"date": date, "asset": "AAA", "close": a, "available_at": date},
                {"date": date, "asset": "BBB", "close": b, "available_at": date},
            ]
        )
    gateway = P6QuantGateway()
    hypothesis = build_hypothesis("Does momentum work in this dataset?")
    specification = plan_experiment(hypothesis, dataset_id="fixture_panel")
    gateway.register_plan(specification)
    response = gateway.run_momentum(
        pd.DataFrame(rows),
        question="Does momentum work in this dataset?",
        hypothesis="A lagged rank has separation",
        experiment_fingerprint=specification.fingerprint,
    )
    assert response.quant_run_id
    assert response.research_run_id
    assert response.result["evaluation"]["metrics"]["total_return"] is not None
    assert response.warnings


def test_grounded_numeric_claim_requires_approved_evidence_reference() -> None:
    claim = ground_numeric_claim(
        "The excess return was 0.02.", value=0.02, evidence_reference="quant-1", evidence_kind="QuantRun",
        source_fingerprint="0" * 64,
    )
    assert claim.value == 0.02
    assert claim.evidence_reference == "quant-1"
    with pytest.raises(ValueError, match="fingerprinted"):
        claims_from_result({"metrics": {"sharpe": 99}}, "quant-1", "QuantRun")


def test_regression_evidence_is_finahinking_owned() -> None:
    evidence = RegressionEvidence(
        parameters={"const": 1.0, "x": 2.0}, metrics={"r_squared": 0.9},
        dataset_fingerprint="d", research_run_id="research-1", quant_run_id="quant-1"
    )
    assert evidence.to_dict()["parameters"]["x"] == 2.0
