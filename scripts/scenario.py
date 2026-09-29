"""Python-runtime scenario recalculation for MCP clients.

The browser can request a scenario, but it cannot compute one.  This module
reads the saved run artifacts, creates a new immutable scenario namespace, and
never overwrites the original analysis.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import numpy as np


ALLOWED_CHANGES = {"horizon", "volatility_shock", "transaction_cost_bps"}


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def preview_scenario(store, run_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(changes, dict) or not changes:
        return {"status": "blocked", "reason_code": "SCENARIO_CHANGES_REQUIRED", "next_action": "provide a bounded scenario change", "user_action_required": True}
    unsupported = sorted(set(changes) - ALLOWED_CHANGES)
    if unsupported:
        return {"status": "blocked", "reason_code": "SCENARIO_CHANGE_NOT_ALLOWED", "message": f"unsupported scenario fields: {unsupported}", "next_action": "use horizon, volatility_shock, or transaction_cost_bps", "user_action_required": True}
    try:
        analysis = store.read_json(run_id, "analysis.json")
    except Exception as exc:  # noqa: BLE001 - convert store failure to MCP contract
        return {"status": "blocked", "reason_code": "ANALYSIS_REQUIRED", "message": str(exc), "next_action": "complete the source and analysis stages", "user_action_required": True}
    scenario_id = "scenario_" + hashlib.sha256((run_id + json.dumps(changes, sort_keys=True, default=str)).encode()).hexdigest()[:16]
    input_hash = hashlib.sha256(json.dumps({"analysis": analysis, "changes": changes}, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    portfolio = analysis.get("portfolio_robustness", {}) if isinstance(analysis.get("portfolio_robustness"), dict) else {}
    returns = np.asarray(portfolio.get("return_matrix", []), dtype=float)
    weights = np.asarray(list(portfolio.get("weights", {}).values()), dtype=float)
    base = {"scenario_id": scenario_id, "run_id": run_id, "created_at": _now(), "changes": changes, "input_hash": input_hash}
    if returns.ndim != 2 or not returns.size or weights.size != returns.shape[1]:
        result = {**base, "status": "degraded", "reason_code": "SCENARIO_DATA_UNAVAILABLE", "next_action": "provide a portfolio artifact with return_matrix and weights", "user_action_required": True, "metrics": {}}
    else:
        shock = float(changes.get("volatility_shock", 0.0))
        cost_bps = float(changes.get("transaction_cost_bps", portfolio.get("transaction_cost_bps", 0.0)))
        series = returns @ weights
        shocked = series * (1.0 + shock)
        turnover = float(np.abs(weights - np.asarray(portfolio.get("prior_weights", weights), dtype=float)).sum())
        cost = turnover * cost_bps / 10000.0
        net = shocked - cost
        wealth = np.cumprod(1.0 + net)
        drawdown = wealth / np.maximum.accumulate(wealth) - 1.0
        losses = -net
        alpha = float(analysis.get("risk_measure", {}).get("confidence_level", 0.95)) if isinstance(analysis.get("risk_measure"), dict) else 0.95
        var = float(np.quantile(losses, alpha))
        result = {**base, "status": "completed", "reason_code": None, "next_action": "compare scenario artifacts", "user_action_required": False, "metrics": {"return": float(net.sum()), "volatility": float(net.std(ddof=1)) if net.size > 1 else None, "max_drawdown": float(drawdown.min()), "var": var, "es": float(losses[losses >= var].mean()), "turnover": turnover, "transaction_cost": cost, "horizon": changes.get("horizon", analysis.get("forecast", {}).get("horizon"))}}
    lineage = {"status": "pass" if result["status"] == "completed" else "not_available", "metrics": [{"metric_id": key, "value": value, "calculation_id": f"{scenario_id}:{key}", "input_hash": input_hash, "code_version": "1.2.0", "formula": "python_runtime_scenario_recalculation", "source_ids": [run_id]} for key, value in result.get("metrics", {}).items() if value is not None]}
    comparison = {"scenario_id": scenario_id, "run_id": run_id, "base_result_ref": "analysis.json", "result": result, "lineage": lineage, "result_hash": hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()}
    store.write_json(run_id, f"{scenario_id}_analysis.json", result)
    store.write_json(run_id, f"{scenario_id}_comparison.json", comparison)
    report = f"<!doctype html><meta charset='utf-8'><title>{scenario_id}</title><h1>Scenario {scenario_id}</h1><pre>{json.dumps(comparison, ensure_ascii=False, indent=2)}</pre>"
    run_dir = store.run_dir(run_id)
    (run_dir / f"{scenario_id}_report.html").write_text(report, encoding="utf-8")
    store.register_artifacts(run_id, [f"{scenario_id}_analysis.json", f"{scenario_id}_comparison.json", f"{scenario_id}_report.html"])
    return {"scenario_id": scenario_id, "run_id": run_id, "status": result["status"], "artifacts": [f"{scenario_id}_analysis.json", f"{scenario_id}_comparison.json", f"{scenario_id}_report.html"], "reason_code": result.get("reason_code"), "user_action_required": result.get("user_action_required", False), "result_hash": comparison["result_hash"]}
