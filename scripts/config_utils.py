#!/usr/bin/env python3
"""Shared configuration loader used by audit, evaluation, portfolio and HTML stages."""
import hashlib
import json
from pathlib import Path
from datetime import date


REQUIRED = ("universe", "target", "horizon", "frequency", "cutoff", "costs", "constraints", "risk_measure", "confidence_level", "evaluation", "models", "output")


def load_config(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_config(data)
    if errors:
        raise ValueError("invalid research config:\n- " + "\n- ".join(errors))
    data["_config_path"] = str(path)
    data["_config_fingerprint"] = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return data


def validate_config(data):
    errors = []
    if not isinstance(data, dict):
        return ["config must be a JSON object"]
    missing = [key for key in REQUIRED if key not in data]
    errors.extend(f"missing top-level field: {key}" for key in missing)
    if not isinstance(data.get("universe"), list) or not data.get("universe") or len(set(data.get("universe", []))) != len(data.get("universe", [])):
        errors.append("universe must be a non-empty list of unique identifiers")
    if data.get("target") not in {"return", "excess_return", "direction", "price", "volatility", "quantile", "spread", "option_value"}:
        errors.append("target is not supported")
    if not isinstance(data.get("horizon"), (int, str)) or (isinstance(data.get("horizon"), int) and data["horizon"] < 1):
        errors.append("horizon must be a positive integer or a string such as 20d")
    if data.get("frequency") not in {"daily", "weekly", "monthly", "intraday"}:
        errors.append("frequency is not supported")
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
    return errors
