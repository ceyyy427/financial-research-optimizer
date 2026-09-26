#!/usr/bin/env python3
"""Shared configuration loader used by audit, evaluation, portfolio and HTML stages."""
import hashlib
import json
from pathlib import Path
from datetime import date


OUTPUT_LEVELS = {"minimal", "standard", "research_grade", "portfolio_grade"}
MODES = {"data_audit", "descriptive_analysis", "forecasting", "backtest", "portfolio_research"}
MIN_OUTPUT_LEVEL = {"minimal": 0, "standard": 1, "research_grade": 2, "portfolio_grade": 3}
MODE_MIN_LEVEL = {"data_audit": 0, "descriptive_analysis": 0, "forecasting": 1, "backtest": 2, "portfolio_research": 2}
SELECTION_CRITERIA = {"statistical_validity", "predictive_performance", "economic_effectiveness", "regime_stability", "seed_window_sensitivity"}
REQUIRED = ("mode", "universe", "target", "horizon", "frequency", "cutoff", "output_level", "costs", "constraints", "risk_measure", "confidence_level", "evaluation", "feature_label_contract", "models", "output")


def load_config(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_config(data)
    if errors:
        raise ValueError("invalid research config:\n- " + "\n- ".join(errors))
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    data["_config_path"] = str(path)
    data["_config_fingerprint"] = fingerprint
    return data


def validate_config(data):
    errors = []
    if not isinstance(data, dict):
        return ["config must be a JSON object"]
    missing = [key for key in REQUIRED if key not in data]
    errors.extend(f"missing top-level field: {key}" for key in missing)
    if data.get("mode") not in MODES:
        errors.append("mode must be data_audit, descriptive_analysis, forecasting, backtest, or portfolio_research")
    if not isinstance(data.get("universe"), list) or not data.get("universe") or len(set(data.get("universe", []))) != len(data.get("universe", [])):
        errors.append("universe must be a non-empty list of unique identifiers")
    if data.get("target") not in {"return", "excess_return", "direction", "price", "volatility", "quantile", "spread", "option_value"}:
        errors.append("target is not supported")
    if not isinstance(data.get("horizon"), (int, str)) or (isinstance(data.get("horizon"), int) and data["horizon"] < 1):
        errors.append("horizon must be a positive integer or a string such as 20d")
    if data.get("frequency") not in {"daily", "weekly", "monthly", "intraday"}:
        errors.append("frequency is not supported")
    if data.get("output_level") not in OUTPUT_LEVELS:
        errors.append("output_level must be minimal, standard, research_grade, or portfolio_grade")
    elif data.get("mode") in MODE_MIN_LEVEL and MIN_OUTPUT_LEVEL[data["output_level"]] < MODE_MIN_LEVEL[data["mode"]]:
        errors.append(f"output_level {data['output_level']} is below the minimum for mode {data['mode']}")
    try:
        date.fromisoformat(str(data.get("cutoff")))
    except ValueError:
        errors.append("cutoff must be YYYY-MM-DD")
    costs = data.get("costs", {})
    if not isinstance(costs, dict) or not isinstance(costs.get("transaction_cost_bps"), (int, float)) or costs.get("transaction_cost_bps") < 0:
        errors.append("costs.transaction_cost_bps must be non-negative")
    constraints = data.get("constraints", {})
    if not isinstance(constraints, dict):
        errors.append("constraints must be an object")
    else:
        for key in ("max_turnover", "max_drawdown"):
            if not isinstance(constraints.get(key), (int, float)) or constraints.get(key) < 0:
                errors.append(f"constraints.{key} must be non-negative")
        if constraints.get("max_drawdown", 0) > 1:
            errors.append("constraints.max_drawdown must be <= 1")
    if data.get("risk_measure") not in {"volatility", "var", "cvar", "drawdown", "utility"}:
        errors.append("risk_measure is not supported")
    if not isinstance(data.get("confidence_level"), (int, float)) or not 0 < data.get("confidence_level", 0) < 1:
        errors.append("confidence_level must be between 0 and 1")
    evaluation = data.get("evaluation", {})
    if not isinstance(evaluation, dict) or evaluation.get("method") not in {"expanding_window", "rolling_window", "blocked_time_series_cv"}:
        errors.append("evaluation.method is not supported")
    else:
        for key in ("train_period", "validation_period", "test_period"):
            if not isinstance(evaluation.get(key), int) or evaluation.get(key) < (1 if key != "validation_period" else 0):
                errors.append(f"evaluation.{key} must be a valid non-negative/positive integer")
    models = data.get("models", {})
    if not isinstance(models, dict) or not isinstance(models.get("baselines"), list) or not models.get("baselines") or not isinstance(models.get("challengers"), list) or not isinstance(models.get("selection"), dict):
        errors.append("models must define baselines, challengers, and selection")
    else:
        selection = models["selection"]
        if not all(selection.get(key) for key in ("primary_metric", "calibration_metric", "economic_metric", "stability_metric")):
            errors.append("models.selection must define primary, calibration, economic, and stability metrics")
        criteria = selection.get("criteria")
        if not isinstance(criteria, dict) or set(criteria) != SELECTION_CRITERIA:
            errors.append("models.selection.criteria must define the five model-selection dimensions")
        elif any(not isinstance(value, (int, float)) or value < 0 or value > 1 for value in criteria.values()):
            errors.append("models.selection.criteria values must be between 0 and 1")
    contract = data.get("feature_label_contract")
    if not isinstance(contract, dict):
        errors.append("feature_label_contract must be an object")
    else:
        for key in ("availability_time_field", "features", "labels"):
            if key not in contract:
                errors.append(f"feature_label_contract missing {key}")
        for key in ("purge_period", "embargo_period"):
            if not isinstance(contract.get(key), int) or contract.get(key) < 0:
                errors.append(f"feature_label_contract.{key} must be a non-negative integer")
        if not isinstance(contract.get("features"), list) or not contract.get("features"):
            errors.append("feature_label_contract.features must be non-empty")
        if not isinstance(contract.get("labels"), list) or not contract.get("labels"):
            errors.append("feature_label_contract.labels must be non-empty")
        for kind in ("features", "labels"):
            for index, item in enumerate(contract.get(kind, [])):
                required_fields = ("feature_id", "formula", "source_ids", "observation_time", "availability_time", "forecast_origin", "label_horizon", "purge_required", "embargo_required", "point_in_time_safe", "lineage") if kind == "features" else ("label_id", "formula", "source_ids", "observation_time", "availability_time", "forecast_origin", "label_horizon", "purge_required", "embargo_required", "point_in_time_safe", "label_start", "label_end", "overlap_group", "lineage")
                if not isinstance(item, dict) or any(field not in item for field in required_fields):
                    errors.append(f"feature_label_contract.{kind}[{index}] is missing a required timing or lineage field")
    output = data.get("output", {})
    if not isinstance(output, dict) or any(not output.get(key) for key in ("artifact_dir", "analysis_json", "html_file", "decision_table_csv", "decision_table_md")):
        errors.append("output must define artifact_dir and all artifact filenames")
    policy = data.get("source_policy", {})
    if policy:
        if not isinstance(policy, dict) or not isinstance(policy.get("priority"), list) or not policy.get("priority"):
            errors.append("source_policy.priority must be a non-empty list")
        for key in ("price_abs_tolerance", "price_rel_tolerance", "volume_abs_tolerance", "volume_rel_tolerance"):
            if key in policy and (not isinstance(policy[key], (int, float)) or policy[key] < 0):
                errors.append(f"source_policy.{key} must be non-negative")
    online = data.get("online", {})
    if online:
        if not isinstance(online, dict):
            errors.append("online must be an object")
        elif not isinstance(online.get("enabled", False), bool):
            errors.append("online.enabled must be boolean")
        elif online.get("max_staleness_minutes") is not None and (not isinstance(online["max_staleness_minutes"], int) or online["max_staleness_minutes"] < 0):
            errors.append("online.max_staleness_minutes must be a non-negative integer")
    refresh = data.get("refresh_policy", {})
    if refresh:
        required_refresh = {"prices", "macro_data", "features", "forecast", "retrain", "full_research"}
        if not isinstance(refresh, dict) or set(refresh) != required_refresh:
            errors.append("refresh_policy must define prices, macro_data, features, forecast, retrain, and full_research")
    return errors
