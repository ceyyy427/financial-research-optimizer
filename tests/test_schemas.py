import json

from validate_schemas import validate_local_schemas


SCHEMAS = [
    "research_config.schema.json",
    "experiment_manifest.schema.json",
    "feature_label_contract.schema.json",
    "backtest_overfitting.schema.json",
    "model_selection.schema.json",
    "portfolio_output.schema.json",
    "feature_label_audit.schema.json",
    "source_reconciliation.schema.json",
    "preflight.schema.json",
    "analysis.schema.json",
    "result_lineage.schema.json",
    "online_snapshot.schema.json",
    "monitoring_status.schema.json",
    "refresh_policy.schema.json",
    "event_data.schema.json",
    "canonical_record.schema.json",
    "network_capture.schema.json",
    "agent_contracts/task.schema.json",
    "agent_contracts/plan.schema.json",
    "agent_contracts/node_result.schema.json",
    "agent_contracts/artifact.schema.json",
]


def test_all_contract_schemas_are_valid_json(ROOT):
    for name in SCHEMAS:
        data = json.loads((ROOT / name).read_text(encoding="utf-8"))
        assert data["$schema"].startswith("https://json-schema.org/")
        assert data["type"] == "object"


def test_demo_contains_every_new_contract_block(ROOT):
    data = json.loads((ROOT / "examples" / "demo_analysis.json").read_text(encoding="utf-8"))
    assert set(data["selection_protocol"]["criteria"]) == {
        "statistical_validity", "predictive_performance", "economic_effectiveness", "regime_stability", "seed_window_sensitivity"
    }
    assert {item["method"] for item in data["backtest_overfitting"]["methods"]} == {"DM", "WRC", "SPA", "DSR", "PBO"}
    for field in ("benchmark", "active_return", "risk_contribution", "factor_exposure", "turnover_attribution", "cost_attribution", "binding_constraints"):
        assert field in data["portfolio_robustness"]


def test_examples_validate_against_local_schemas(ROOT):
    result = validate_local_schemas(ROOT)
    assert result["valid"] is True
    assert result["examples_validated"] == 15
