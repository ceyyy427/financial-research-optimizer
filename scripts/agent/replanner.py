"""Bounded fallback selection after a plan node fails."""


FALLBACKS = {
    "capture_data": ["switch_source", "use_cached_snapshot", "mark_degraded"],
    "normalize_dataset": ["use_previous_schema_mapping", "stop_dependent_analysis"],
    "run_models": ["run_baseline_only", "stop_dependent_analysis"],
    "run_portfolio_optimization": ["prior_weights", "cash_fallback", "stop_dependent_analysis"],
}


def replan(plan, execution, max_replans=2):
    replans = int(execution.get("replan_count", 0))
    if replans >= max_replans:
        return {"status": "blocked", "reason": "replan budget exhausted", "next_action": "stop_dependent_analysis"}
    failed = next((item for item in execution.get("results", []) if item.get("status") in {"failed", "blocked"}), None)
    if not failed:
        return {"status": "no_change", "reason": "no failed node"}
    node = next((item for item in plan.get("nodes", []) if item.get("id") == failed.get("node_id")), {})
    options = FALLBACKS.get(node.get("tool"), ["stop_dependent_analysis"])
    chosen = options[min(replans, len(options) - 1)]
    if chosen == "stop_dependent_analysis":
        return {"status": "blocked", "reason": failed.get("message", "node failure"), "next_action": chosen}
    return {"status": "fallback", "reason": failed.get("message", "node failure"), "next_action": chosen, "replan_count": replans + 1}
