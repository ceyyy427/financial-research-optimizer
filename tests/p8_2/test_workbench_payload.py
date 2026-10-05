from __future__ import annotations

from finahinking.p6_6.workbench import (
    ExecutionPolicy,
    FaultPolicy,
    PositionPolicySpec,
    RiskStatePolicy,
)
from finahinking.p6_6.workbench_engine import run_workbench
from finahinking.p6_6.workbench_explanations import build_explanation_package
from finahinking.p8_2.data_sources import FixtureMarketDataSource
from finahinking.p8_2.research_view import build_research_payload, build_workbench_payload


def sample_workbench():
    rows = [
        {"id": "a1", "time": "2026-01-01T00:00:00+00:00", "available_at": "2026-01-01T00:00:00+00:00", "instrument": "AAA", "score": 0.2, "signal": True, "volatility": 0.1, "return": 0},
        {"id": "a2", "time": "2026-01-02T00:00:00+00:00", "available_at": "2026-01-02T00:00:00+00:00", "instrument": "AAA", "score": 0.3, "signal": True, "volatility": 0.1, "return": 0.01},
    ]
    run = run_workbench("payload-run", rows, PositionPolicySpec("position", "v1", "equal_weight"), RiskStatePolicy("risk", "v1"), ExecutionPolicy("execution", "v1"), FaultPolicy("fault", "v1"))
    explanation = build_explanation_package(run, strategy_id="strategy-1", parameter_changes={"lookback": {"before": 20, "after": 40}}, intent="Reduce noise", formula_before="m20", formula_after="m40", code_trace=("momentum",))
    return run, explanation


def test_research_payload_carries_workbench_layers_and_provenance() -> None:
    payload = build_research_payload(FixtureMarketDataSource(points=4).snapshot())
    workbench = payload["workbench"]
    for field in ("factor_observations", "signals", "raw_weights", "risk_scales", "final_weights", "exposure", "cash", "risk_states", "trades", "costs", "slippage", "fault_events", "explanation_refs", "baseline_variant_refs"):
        assert field in workbench
    assert workbench["provenance"]["dataset_fingerprint"] == payload["dataset"]["fingerprint"]
    assert workbench["paper_only"] is True
    assert workbench["factor_research"]["dataset_fingerprint"] == payload["dataset"]["fingerprint"]
    assert workbench["factor_candidates"]
    assert workbench["provider_status"]["secret_policy"]
    assert payload["payload_fingerprint"]


def test_workbench_payload_is_server_owned_and_sorted() -> None:
    run, explanation = sample_workbench()
    payload = build_workbench_payload(run, explanation)
    assert payload["schema_version"] == 1
    assert payload["points"][0]["time"] <= payload["points"][1]["time"]
    assert payload["provenance"]["policy_fingerprint"]
    assert payload["explanation_refs"][0]["id"] == "explanation-payload-run"
    assert payload["points"][0]["final_weight"] != payload["points"][0]["held_weight"]


def test_report_renderer_is_self_contained_publication_html(tmp_path) -> None:
    from finahinking.research.reports import render_workbench_report_html

    run, explanation = sample_workbench()
    html = render_workbench_report_html(build_workbench_payload(run, explanation), explanation)
    assert '<meta name="viewport"' in html
    assert "Factor / strategy workbench" in html
    assert "PAPER-ONLY" in html
    assert "<svg" in html and "<table" in html
    assert "Provider readiness" in html
    assert "http://" not in html and "https://" not in html
    assert "api_key" not in html.lower()
    assert 'aria-label="Research timeline"' in html
