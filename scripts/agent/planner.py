"""Create a bounded research contract and executable Plan DAG."""
import hashlib
import json
from datetime import datetime, timezone

from .policy_guard import validate_task_scope


KNOWN_ENTITY_ALIASES = {
    "沪深300": {"entity_id": "000300.SH", "calendar": "XSHG", "currency": "CNY"},
    "csi300": {"entity_id": "000300.SH", "calendar": "XSHG", "currency": "CNY"},
    "sp500": {"entity_id": "SPX", "calendar": "XNYS", "currency": "USD"},
}
KNOWN_TARGETS = {
    "波动率": "realized_volatility",
    "收益率": "excess_return",
    "方向": "direction",
}


def resolve_contract_fields(task, universe, target, horizon, constraints):
    """Resolve high-value aliases and return explicit missing-input reasons."""
    resolved_universe = list(universe or [])
    resolution_notes = []
    for item in resolved_universe:
        alias = KNOWN_ENTITY_ALIASES.get(str(item).strip().lower())
        if alias:
            resolved_universe[resolved_universe.index(item)] = alias["entity_id"]
            resolution_notes.append({"input": item, **alias})
    resolved_target = target or ""
    if resolved_target:
        resolved_target = KNOWN_TARGETS.get(str(resolved_target).strip().lower(), resolved_target)
    resolved_horizon = horizon or ""
    missing = []
    if not resolved_universe:
        missing.append("universe")
    if not resolved_target or resolved_target == "unspecified":
        missing.append("target")
    if not resolved_horizon or resolved_horizon == "unspecified":
        missing.append("horizon")
    if not constraints.get("cutoff"):
        missing.append("cutoff")
    if not constraints.get("calendar") and not resolution_notes:
        missing.append("execution_calendar")
    return {
        "universe": resolved_universe,
        "target": resolved_target or "unspecified",
        "horizon": resolved_horizon or "unspecified",
        "resolution_notes": resolution_notes,
        "needs_user_input": missing,
        "resolution_status": "needs_user_input" if missing else "resolved",
    }


def _plan_id(task):
    digest = hashlib.sha256(json.dumps(task, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return f"plan_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{digest}"


def create_research_contract(task, mode="forecasting", output_level="research_grade", constraints=None, universe=None, target=None, horizon=None):
    scope = validate_task_scope(task)
    if not scope["allowed"]:
        raise ValueError(f"task violates policy: {scope['violations']}")
    if mode not in {"data_audit", "descriptive_analysis", "forecasting", "backtest", "portfolio_research"}:
        raise ValueError(f"unsupported research mode: {mode}")
    if output_level not in {"minimal", "standard", "research_grade", "portfolio_grade"}:
        raise ValueError(f"unsupported output level: {output_level}")
    if mode in {"backtest", "portfolio_research"} and output_level not in {"research_grade", "portfolio_grade"}:
        raise ValueError(f"{mode} requires output_level research_grade or portfolio_grade")
    constraints = dict(constraints or {})
    resolution = resolve_contract_fields(task, universe, target, horizon, constraints)
    return {
        "task": task,
        "mode": mode,
        "output_level": output_level,
        "universe": resolution["universe"],
        "target": resolution["target"],
        "horizon": resolution["horizon"],
        "constraints": constraints,
        "resolution": resolution,
        "needs_user_input": resolution["needs_user_input"],
        "global_budget": constraints.get("global_budget", {
            "max_network_requests": 200,
            "max_bytes_downloaded": 500_000_000,
            "max_artifacts": 100,
            "max_wall_time_seconds": 1_800,
            "max_browser_contexts": 3,
        }),
    }


def _node(node_id, tool, depends_on, success, failure, artifacts, allow_degraded=False, max_retries=2, timeout_seconds=300):
    return {"id": node_id, "tool": tool, "depends_on": depends_on, "success_condition": success, "failure_condition": failure, "max_retries": max_retries, "timeout_seconds": timeout_seconds, "budget": {"max_network_requests": 20, "max_artifacts": 20}, "allow_degraded": allow_degraded, "artifacts": artifacts}


def build_plan(contract):
    mode = contract["mode"]
    nodes = [
        _node("contract_resolution", "resolve_contract", [], "contract_fields_resolved", "needs_user_input", ["research_contract.json"]),
        _node("source_discovery", "discover_sources", ["contract_resolution"], "at_least_one_authoritative_source", "no_verified_source", ["source_registry.json"], allow_degraded=True),
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
