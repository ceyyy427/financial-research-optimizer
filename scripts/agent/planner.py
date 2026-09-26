"""Create a bounded research contract and executable Plan DAG."""
import hashlib
import json
from datetime import datetime, timezone

from .policy_guard import validate_task_scope


def _plan_id(task):
    digest = hashlib.sha256(json.dumps(task, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return f"plan_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{digest}"


def create_research_contract(task, mode="forecasting", output_level="research_grade", constraints=None, universe=None, target=None, horizon=None):
    scope = validate_task_scope(task)
    if not scope["allowed"]:
        raise ValueError(f"task violates policy: {scope['violations']}")
    return {
        "task": task,
        "mode": mode,
        "output_level": output_level,
        "universe": universe or [],
        "target": target or "unspecified",
        "horizon": horizon or "unspecified",
        "constraints": dict(constraints or {}),
    }


def _node(node_id, tool, depends_on, success, failure, artifacts, allow_degraded=False, max_retries=2, timeout_seconds=300):
    return {"id": node_id, "tool": tool, "depends_on": depends_on, "success_condition": success, "failure_condition": failure, "max_retries": max_retries, "timeout_seconds": timeout_seconds, "budget": {"max_network_requests": 20, "max_artifacts": 20}, "allow_degraded": allow_degraded, "artifacts": artifacts}


def build_plan(contract):
    mode = contract["mode"]
    nodes = [
        _node("source_discovery", "discover_sources", [], "at_least_one_authoritative_source", "no_verified_source", ["source_registry.json"], allow_degraded=True),
        _node("data_capture", "capture_data", ["source_discovery"], "snapshot_saved", "no_snapshot", ["raw_snapshot", "provenance_manifest.json"], allow_degraded=True),
        _node("normalize_dataset", "normalize_dataset", ["data_capture"], "canonical_schema_valid", "schema_or_unit_failure", ["canonical_dataset.csv", "transformation_manifest.json"]),
        _node("preflight", "run_preflight", ["normalize_dataset"], "status_not_blocked", "blocking_contract_failure", ["preflight.json"]),
        _node("point_in_time_audit", "audit_dataset", ["preflight"], "no_blocking_leakage", "future_information_or_revision_leakage", ["data_quality.json", "feature_label_audit.json"]),
    ]
    if mode in {"forecasting", "backtest", "portfolio_research"}:
        nodes.extend([
            _node("features", "build_features", ["point_in_time_audit"], "feature_label_contract_pass", "availability_or_overlap_failure", ["features.parquet"]),
            _node("model_evaluation", "run_models", ["features"], "rolling_evaluation_saved", "insufficient_sample_or_model_failure", ["rolling_evaluation.json", "model_registry.json"]),
        ])
    if mode in {"backtest", "portfolio_research"}:
        nodes.append(_node("overfitting_diagnostics", "run_overfitting_diagnostics", ["model_evaluation"], "applicable_gates_pass_or_not_applicable", "applicable_gate_failed", ["backtest_overfitting.json"]))
    if mode == "portfolio_research":
        nodes.append(_node("portfolio", "run_portfolio_optimization", ["overfitting_diagnostics"], "feasible_or_documented_fallback", "unresolved_infeasibility", ["portfolio_robustness.json"], allow_degraded=True))
    final_dependency = nodes[-1]["id"]
    nodes.extend([
        _node("monitoring", "post_selection_stress_test", [final_dependency], "monitoring_status_saved", "stress_or_drift_failure", ["monitoring_status.json"], allow_degraded=True),
        _node("artifacts", "render_artifacts", ["monitoring"], "html_and_decision_table_saved", "artifact_or_lineage_failure", ["analysis.json", "financial_research_brief.html", "decision_table.csv", "decision_table.md", "experiment_manifest.json"]),
    ])
    return {"plan_id": _plan_id(contract), "goal": contract["task"], "mode": mode, "output_level": contract["output_level"], "immutable_contract": contract, "nodes": nodes}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task")
    parser.add_argument("--mode", default="forecasting")
    parser.add_argument("--output-level", default="research_grade")
    args = parser.parse_args()
    print(json.dumps(build_plan(create_research_contract(args.task, args.mode, args.output_level)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
