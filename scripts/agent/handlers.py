"""Default research handlers used by the public runtime.

Handlers deliberately distinguish executable work from a capability gap.  A
handler never returns a successful result merely because a node is present in
the plan; unavailable stages are blocked with an actionable explanation.
"""
import csv
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def _blocked(node, message, **extra):
    return {
        "status": "blocked",
        "message": message,
        "artifacts": [],
        "execution_mode": "capability_gap",
        "reason_code": extra.pop("reason_code", "CAPABILITY_GAP"),
        "next_action": extra.pop("next_action", "provide the missing contract input or registered handler"),
        "user_action_required": extra.pop("user_action_required", True),
        "provenance": {"execution_mode": "capability_gap", "node": node.get("id")},
        **extra,
    }


def _discover_sources(contract, node):
    """Resolve a source plan when a registry and topic are available."""
    registry = contract.get("source_registry_path") or "config/source_registry.yaml"
    if not Path(registry).exists():
        return _blocked(node, f"source registry not found: {registry}")
    try:
        from ..source_router import SourceRouter
    except ImportError:  # installed/script execution
        from source_router import SourceRouter
    try:
        router = SourceRouter.from_file(registry)
        plan = router.resolve(
            contract.get("target", contract.get("task", "financial data")),
            universe=contract.get("universe", []),
            required_capabilities=contract.get("required_capabilities", []),
            required_fields=contract.get("required_fields", []),
            authorization_status=contract.get("authorization_status", "unknown"),
            require_executable=bool(contract.get("execute_sources", False)),
        )
        return {"status": "passed", "message": "source plan resolved", "artifacts": [], "provenance": {"source_plan": plan}}
    except Exception as exc:
        return _blocked(node, f"source routing failed: {exc}")


def _preflight(contract, node):
    """Run the same preflight contract used by the CLI when a config is supplied."""
    config_path = contract.get("config_path")
    if not config_path:
        if contract.get("dataset_path") or contract.get("normalized_dataset_path"):
            return {"status": "passed", "message": "local dataset preflight passed; online source contract not requested", "artifacts": [], "provenance": {"mode": "local_dataset", "status": "ready"}}
        return _blocked(node, "config_path is required for executable preflight")
    try:
        try:
            from ..run_preflight import run_preflight
        except ImportError:
            from run_preflight import run_preflight
        result = run_preflight(config_path)
        if result.get("status") == "blocked":
            return _blocked(node, "preflight blocked: " + "; ".join(result.get("blocking_reasons", [])), preflight=result)
        return {"status": "passed", "message": f"preflight status: {result.get('status')}", "artifacts": [], "provenance": {"preflight": result}}
    except Exception as exc:
        return _blocked(node, f"preflight failed: {exc}")


def _data_capture(contract, node):
    local_path = contract.get("dataset_path") or contract.get("normalized_dataset_path")
    if local_path and Path(local_path).exists():
        return {"status": "passed", "message": "local dataset supplied; online capture skipped", "artifacts": [str(local_path)], "provenance": {"capture_mode": "local_dataset", "path": str(local_path)}}
    if not contract.get("refresh_plan") and not contract.get("source_url"):
        return _blocked(node, "source_url or refresh_plan is required for data capture")
    return _blocked(node, "data capture requires an executable source adapter; use scripts/execute_online_refresh.py")


def _artifact_dir(contract):
    path = contract.get("artifact_dir") or contract.get("output_dir")
    if not path:
        path = Path("artifacts") / "runs" / str(contract.get("run_id") or "minimum-closed-loop")
    result = Path(path)
    result.mkdir(parents=True, exist_ok=True)
    return result


def _load_rows(contract):
    path = contract.get("normalized_dataset_path") or contract.get("dataset_path")
    if path and Path(path).exists():
        target = Path(path)
        if target.suffix.lower() == ".csv":
            with target.open(newline="", encoding="utf-8-sig") as handle:
                return list(csv.DictReader(handle)), target
        payload = json.loads(target.read_text(encoding="utf-8"))
        rows = payload.get("observations", payload.get("rows", payload)) if isinstance(payload, dict) else payload
        return (rows if isinstance(rows, list) else []), target
    return [], None


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return str(path)


def _dataset_rows(contract):
    path = _artifact_dir(contract) / "canonical_dataset.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return (payload if isinstance(payload, list) else payload.get("observations", [])), path
    rows, source = _load_rows(contract)
    return rows, source


def _timestamp(value):
    if value in (None, ""):
        return None
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_records(rows, contract, source):
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest() if source and source.exists() else hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
    source_id = str(contract.get("source_id", "local_dataset"))
    profile = {"source_id": source_id, "authority": "user_supplied", "primary_method": "local_file", "parser": "local_csv_json", "base_urls": ["https://local.invalid/"]}
    snapshot = {"snapshot_hash": "sha256:" + source_hash, "request_url": "https://local.invalid/dataset", "retrieved_at": datetime.now(timezone.utc).isoformat()}
    records = []
    value_keys = ("value", "close", "price", "adjusted_close", "open", "high", "low", "volume")
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise ValueError(f"row {index} is not an object")
        observation = raw.get("observation_time", raw.get("observation_date", raw.get("date", raw.get("timestamp"))))
        if observation in (None, ""):
            raise ValueError(f"row {index} is missing observation date")
        availability = raw.get("availability_time", raw.get("available_time"))
        # Canonical schema requires a timestamp.  When it is absent, retain a
        # deterministic proxy but mark PIT as unavailable; audit will block if
        # the contract requires verified availability.
        availability_proxy = availability or observation
        effective = raw.get("effective_time") or observation
        key = next((key for key in value_keys if raw.get(key) not in (None, "")), None)
        if key is None:
            raise ValueError(f"row {index} has no supported numeric value field")
        record = {
            "instrument_id": str(raw.get("instrument_id", raw.get("ticker", raw.get("symbol", contract.get("universe", ["local"])[0] if contract.get("universe") else "local")))),
            "field": str(raw.get("field", key)), "value": raw[key], "unit": str(raw.get("unit", "unknown")),
            "observation_time": observation, "release_time": raw.get("release_time"), "availability_time": availability_proxy,
            "effective_time": effective, "vintage_time": raw.get("vintage_time"), "currency": raw.get("currency"),
            "adjustment": raw.get("adjustment", "unadjusted"), "source_url": raw.get("source_url", "https://local.invalid/dataset"),
            "access_method": raw.get("access_method", "local_file"), "point_in_time_status": "pass" if availability else "not_available",
            "revision_status": raw.get("revision_status", "not_available"), "parser_version": "local_csv_json_v1",
        }
        try:
            from ..normalize_observations import canonicalize_observation
        except ImportError:
            from normalize_observations import canonicalize_observation
        records.append(canonicalize_observation(record, profile, snapshot))
    return records


def _numeric_series(rows):
    values = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ("value", "close", "price", "adjusted_close"):
            try:
                if row.get(key) not in (None, ""):
                    values.append(float(row[key]))
                    break
            except (TypeError, ValueError):
                continue
    return values


def _minimum_analysis(contract, rows, source):
    values = _numeric_series(rows)
    if not values:
        return None
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest() if source and source.exists() else hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    code_version = "financial-research-optimizer-0.9.0"
    calc_id = "calc_" + hashlib.sha256((source_hash + code_version).encode()).hexdigest()[:12]
    mean_value = statistics.fmean(values)
    metric = {"metric_id": "baseline_mean", "value": mean_value, "calculation_id": calc_id, "input_hash": source_hash, "code_version": code_version, "formula": "mean(value[0:n])", "source_ids": [str(contract.get("source_id", "local_dataset"))], "input_files": [str(source)] if source else []}
    experiment_id = "exp_" + source_hash[:12]
    refs = [metric["metric_id"]]
    return {
        "experiment_id": experiment_id, "reproducibility_status": "partial", "mode": contract.get("mode", "forecasting"), "output_level": contract.get("output_level", "standard"),
        "meta": {"title": "Minimum auditable financial research loop", "as_of_time": datetime.now(timezone.utc).isoformat(), "universe": contract.get("universe", []), "target": contract.get("target", "value"), "horizon": contract.get("horizon", "unspecified")},
        "summary": {"headline": "Baseline forecast generated from the supplied dataset", "confidence": "baseline only", "limitations": ["This closed loop does not claim live certification or investment advice."]},
        "forecast": {"label": contract.get("target", "value"), "value": mean_value, "interval": "not_available", "probability": "not_calibrated", "model": "historical_mean_baseline", "direction": "warning", "lineage_refs": refs},
        "series": values[-60:], "series_lineage_refs": refs,
        "charts": [{"chart_id": "observed_values", "title": "Observed values and baseline", "type": "line", "labels": [str(i + 1) for i in range(len(values[-60:]))], "series": [{"name": "observed", "values": values[-60:]}, {"name": "baseline", "values": [mean_value] * len(values[-60:])}], "description": "Values read from the supplied dataset.", "lineage_refs": refs}],
        "modules": [{"module_id": "baseline", "title": "Baseline forecast", "status": "warning", "summary": "Historical mean baseline; no model comparison was run.", "evidence_refs": refs, "caveats": ["Use rolling evaluation before relying on the estimate."], "next_check": "run forecasting with a point-in-time dataset"}],
        "model_cards": [{"model_id": "historical_mean_baseline", "version": "0.9.0", "estimand": "conditional mean proxy", "objective": "baseline", "validation_protocol": "expanding_window", "overfitting_diagnostics": "not_applicable", "failure_mode": "regime change", "status": "challenger"}, {"model_id": "naive_last_value", "version": "0.9.0", "estimand": "one-step persistence", "objective": "baseline", "validation_protocol": "expanding_window", "overfitting_diagnostics": "not_applicable", "failure_mode": "price jump", "status": "challenger"}, {"model_id": "rolling_mean_baseline", "version": "0.9.0", "estimand": "trailing-window mean", "objective": "baseline", "validation_protocol": "expanding_window", "overfitting_diagnostics": "not_applicable", "failure_mode": "window sensitivity", "status": "challenger"}],
        "selection_protocol": {"layers": ["statistical_validity", "predictive_performance", "economic_effectiveness"], "criteria": ["statistical_validity", "predictive_performance", "economic_effectiveness", "regime_stability", "seed_window_sensitivity"], "primary_metric": "baseline_mean", "status": "baseline_only"},
        "decision_rows": [{"priority": "P1", "module": "forecast", "current_view": "baseline only", "action": "validate before use", "trigger": "new point-in-time data", "evidence": "baseline_mean", "risk": "model and data uncertainty", "horizon": str(contract.get("horizon", "unspecified")), "next_check": "rolling evaluation"}],
        "result_lineage": {"metrics": [metric], "status": "pass", "lineage_refs": refs}, "sources": [{"id": str(contract.get("source_id", "local_dataset")), "label": "supplied dataset"}],
    }


def _normalize_dataset(contract, node):
    rows, source = _load_rows(contract)
    if not rows:
        return _blocked(node, "a non-empty dataset_path or normalized_dataset_path is required", reason_code="DATASET_REQUIRED", next_action="supply dataset_path pointing to CSV or JSON")
    try:
        canonical = _canonical_records(rows, contract, source)
        required = {"instrument_id", "source_id", "field", "value", "observation_time", "availability_time", "effective_time", "snapshot_hash", "transformation_id", "point_in_time_status"}
        if any(not required.issubset(record) for record in canonical):
            raise ValueError("canonical observation is missing required fields")
        try:
            import jsonschema
            schema_path = Path(__file__).resolve().parents[2] / "schemas" / "canonical_observation.schema.json"
            if schema_path.exists():
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                for record in canonical:
                    jsonschema.validate(record, schema)
        except ImportError:
            pass
        path = _write_json(_artifact_dir(contract) / "canonical_dataset.json", canonical)
        manifest = {"transformation_id": "canonical_observation_v1", "input_file": str(source), "input_hash": hashlib.sha256(source.read_bytes()).hexdigest(), "rows": len(canonical), "source_id": contract.get("source_id", "local_dataset")}
        manifest_path = _write_json(_artifact_dir(contract) / "transformation_manifest.json", manifest)
        return {"status": "passed", "message": "dataset canonicalized into point-in-time observation records", "artifacts": [path, manifest_path], "provenance": manifest}
    except (ValueError, TypeError, OSError) as exc:
        return _blocked(node, f"canonicalization failed: {exc}", reason_code="CANONICALIZATION_FAILED", next_action="provide parseable dates and a supported value field")


def _audit_dataset(contract, node):
    rows, source = _dataset_rows(contract)
    if not rows:
        return _blocked(node, "normalized dataset is empty", reason_code="EMPTY_DATASET", next_action="fix normalization or provide a non-empty dataset")
    fields = sorted({key for row in rows if isinstance(row, dict) for key in row})
    missing = {field: sum(row.get(field) in (None, "") for row in rows if isinstance(row, dict)) for field in fields}
    dates = [_timestamp(row.get("observation_time")) for row in rows if isinstance(row, dict)]
    invalid_dates = sum(value is None for value in dates)
    duplicate_keys = len(rows) - len({(row.get("instrument_id"), row.get("observation_time"), row.get("field"), row.get("vintage_time")) for row in rows if isinstance(row, dict)})
    ordering_violation = any(left > right for left, right in zip([value for value in dates if value], [value for value in dates if value][1:]))
    units = sorted({str(row.get("unit")) for row in rows if isinstance(row, dict)})
    future_leakage = any(_timestamp(row.get("availability_time")) < _timestamp(row.get("observation_time")) for row in rows if isinstance(row, dict) and _timestamp(row.get("availability_time")) and _timestamp(row.get("observation_time")))
    negative_values = sum(1 for row in rows if isinstance(row, dict) and str(row.get("field", "")).lower() in {"close", "price", "adjusted_close"} and isinstance(row.get("value"), (int, float)) and row.get("value") < 0)
    has_availability = all(row.get("point_in_time_status") == "pass" for row in rows if isinstance(row, dict))
    pit_status = "verified" if has_availability else "not_available"
    blocked_reasons = []
    if invalid_dates: blocked_reasons.append("invalid observation_time")
    if duplicate_keys: blocked_reasons.append("duplicate grain")
    if ordering_violation: blocked_reasons.append("observation times are not sorted")
    if future_leakage: blocked_reasons.append("availability_time precedes observation_time")
    if negative_values: blocked_reasons.append("negative price")
    payload = {"status": "blocked" if blocked_reasons else "pass", "rows": len(rows), "columns": fields, "missingness": missing, "date_integrity": {"invalid": invalid_dates, "ordering_violation": ordering_violation}, "duplicate_grain_count": duplicate_keys, "units": units, "negative_price_count": negative_values, "point_in_time_status": pit_status, "future_leakage": future_leakage, "label_overlap": "not_checked", "source_file": str(source) if source else None, "blocking_reasons": blocked_reasons}
    path = _write_json(_artifact_dir(contract) / "data_quality.json", payload)
    if blocked_reasons:
        return _blocked(node, "dataset quality audit blocked: " + "; ".join(blocked_reasons), reason_code="DATA_QUALITY_BLOCKED", next_action="correct dates, grain, units, or anomalous values", artifacts=[path], provenance=payload)
    if contract.get("require_point_in_time") and not has_availability:
        return _blocked(node, "availability_time is required for this forecasting contract", reason_code="MISSING_AVAILABILITY_TIME", next_action="provide release/availability timestamps or use a vintage-aware source", artifacts=[path], provenance=payload)
    return {"status": "passed", "message": "dataset audit passed with PIT limitations declared", "artifacts": [path], "provenance": payload}


def _build_features(contract, node):
    rows, source = _dataset_rows(contract)
    if not rows:
        return _blocked(node, "features require a normalized dataset", reason_code="FEATURE_INPUT_REQUIRED")
    availability = sorted({row.get("availability_time") for row in rows if isinstance(row, dict) and row.get("availability_time")})
    path = _write_json(_artifact_dir(contract) / "features.json", {"rows": rows, "lineage": {"source_file": str(source) if source else None, "availability_time": availability or ["not_available"], "point_in_time_status": "verified" if all(row.get("point_in_time_status") == "pass" for row in rows) else "not_available"}})
    return {"status": "passed", "message": "pass-through baseline features created", "artifacts": [path], "provenance": {"feature_count": len(rows[0]) if isinstance(rows[0], dict) else 0}}


def _run_models(contract, node):
    rows, source = _dataset_rows(contract)
    analysis = _minimum_analysis(contract, rows, source)
    if not analysis:
        return _blocked(node, "numeric value/close/price field is required for baseline forecast", reason_code="NUMERIC_SERIES_REQUIRED")
    values = _numeric_series(rows)
    source_hash = analysis["result_lineage"]["metrics"][0]["input_hash"]
    metric_refs = analysis["result_lineage"]["metric_ids"] if "metric_ids" in analysis["result_lineage"] else ["baseline_mean"]
    forecasts, actuals, mean_forecasts, rolling_forecasts = [], [], [], []
    rolling_window = max(2, min(20, len(values) // 4 or 2))
    for index in range(1, len(values)):
        forecasts.append(values[index - 1])
        actuals.append(values[index])
        mean_forecasts.append(statistics.fmean(values[:index]))
        rolling_forecasts.append(statistics.fmean(values[max(0, index - rolling_window):index]))
    errors = [actual - forecast for actual, forecast in zip(actuals, forecasts)]
    mean_errors = [actual - forecast for actual, forecast in zip(actuals, mean_forecasts)]
    rolling_errors = [actual - forecast for actual, forecast in zip(actuals, rolling_forecasts)]
    rmse = (statistics.fmean([error * error for error in errors]) ** 0.5) if errors else None
    mean_rmse = (statistics.fmean([error * error for error in mean_errors]) ** 0.5) if mean_errors else None
    rolling_rmse = (statistics.fmean([error * error for error in rolling_errors]) ** 0.5) if rolling_errors else None
    scores = {"naive_last_value": rmse, "historical_mean_baseline": mean_rmse, "rolling_mean_baseline": rolling_rmse}
    selected = min((key for key, value in scores.items() if value is not None), key=lambda key: scores[key], default="historical_mean_baseline")
    selected_errors = {"naive_last_value": errors, "historical_mean_baseline": mean_errors, "rolling_mean_baseline": rolling_errors}[selected]
    residual_std = statistics.stdev(selected_errors) if len(selected_errors) > 1 else None
    point = {"naive_last_value": forecasts[-1] if forecasts else values[-1], "historical_mean_baseline": mean_forecasts[-1] if mean_forecasts else statistics.fmean(values), "rolling_mean_baseline": rolling_forecasts[-1] if rolling_forecasts else statistics.fmean(values)}[selected]
    interval = [point - 1.645 * residual_std, point + 1.645 * residual_std] if residual_std is not None else None
    candidate_errors = {"naive_last_value": errors, "historical_mean_baseline": mean_errors, "rolling_mean_baseline": rolling_errors}
    rolling = {"status": "pass" if errors else "not_available", "models": [{"model_id": model, "n_predictions": len(errors), "rmse": score, "lineage_refs": metric_refs} for model, score in scores.items()], "selected_model": selected, "selection_metric": "rmse", "protocol": {"type": "expanding_window", "minimum_train": 1, "horizon": 1, "evaluation_window": len(errors)}, "residuals": selected_errors, "residual_interval": interval, "interval_method": "1.645 residual standard deviations", "calibration_status": "not_calibrated", "calibration_state": "uncalibrated", "calibration_warning": "interval coverage and interval score require a declared calibration split", "coverage": None, "interval_score": None, "ood_status": "not_checked", "regime_slice": "not_available", "research_grade_warning": "calibration and OOD checks are not available for this minimum baseline path", "candidate_losses": candidate_errors, "candidate_family": list(candidate_errors), "trial_count": 1, "bootstrap_block_length": max(2, min(10, len(errors) // 5 or 2)), "input_hash": source_hash}
    rolling_path = _write_json(_artifact_dir(contract) / "rolling_evaluation.json", rolling)
    forecast_contract = {"target": str(contract.get("target", "value")), "forecast_origin": datetime.now(timezone.utc).isoformat(), "horizon": contract.get("horizon", 1), "forecast_types": ["point", "interval"], "selected_model": selected, "selection_metric": "rmse", "evaluation_window": len(errors), "interval_method": "1.645 residual standard deviations", "calibration_status": "not_calibrated", "calibration_state": "uncalibrated", "metrics": {"primary": ["rmse"], "calibration": ["coverage", "interval_score"]}, "validity_conditions": ["point-in-time audit passes", "rolling evaluation is out of sample", "interval is an uncalibrated residual approximation"], "known_failure_modes": ["regime change", "small sample", "window sensitivity"], "ood_status": "not_checked", "regime_status": "not_available", "warning": "research grade output requires a calibration/OOD artifact before high-confidence use"}
    analysis["forecast"].update({"value": point, "interval": interval or "not_available", "model": selected, "calibration_status": "not_calibrated", "ood_status": "not_checked"})
    analysis["forecast_contract"] = forecast_contract
    for card in analysis["model_cards"]:
        card["status"] = "selected" if card["model_id"] == selected else "challenger"
    path = _write_json(_artifact_dir(contract) / "analysis.json", analysis)
    return {"status": "passed", "message": "naive, historical-mean and rolling-mean baselines with rolling evaluation created", "artifacts": [path, rolling_path], "provenance": {"model": "historical_mean_baseline+naive_last_value+rolling_mean_baseline", "experiment_id": analysis["experiment_id"], "uncertainty_status": "uncalibrated", "research_grade_warning": rolling["research_grade_warning"]}}


def _render_artifacts(contract, node):
    analysis_path = _artifact_dir(contract) / "analysis.json"
    if not analysis_path.exists():
        return _blocked(node, "analysis.json is required before rendering", reason_code="ANALYSIS_REQUIRED")
    try:
        try:
            from ..generate_financial_html import normalize_rows, render_html, write_decision_table, validate_payload
        except ImportError:
            from generate_financial_html import normalize_rows, render_html, write_decision_table, validate_payload
        data = json.loads(analysis_path.read_text(encoding="utf-8"))
        try:
            from ..knowledge.explanation_engine import build_explanations
            from ..tex.compile_formula import build_manifest
        except ImportError:
            from knowledge.explanation_engine import build_explanations
            from tex.compile_formula import build_manifest
        explanations = data.get("knowledge_explanations") if isinstance(data.get("knowledge_explanations"), list) else build_explanations(data)
        data["knowledge_explanations"] = explanations
        explanation_path = _write_json(_artifact_dir(contract) / "knowledge_explanations.json", explanations)
        formula_ids = [item.get("formula_id") for item in explanations if isinstance(item, dict) and item.get("formula_id")]
        formula_manifest = data.get("formula_manifest") if isinstance(data.get("formula_manifest"), dict) else build_manifest(_artifact_dir(contract) / "formulas", formula_ids)
        data["formula_manifest"] = formula_manifest
        formula_manifest_path = _write_json(_artifact_dir(contract) / "formula_manifest.json", formula_manifest)
        validate_payload(data, {"mode": contract.get("mode", "forecasting"), "output_level": contract.get("output_level", "standard")})
        output_dir = _artifact_dir(contract)
        (output_dir / "financial_research_brief.html").write_text(render_html(data, contract, data), encoding="utf-8")
        rows = normalize_rows(data["decision_rows"], data.get("experiment_id"), data.get("reproducibility_status"), data.get("online_status", {}))
        paths = [str(output_dir / "financial_research_brief.html")] + [str(path) for path in write_decision_table(rows, output_dir, "both")]
        return {"status": "passed", "message": "offline HTML, explanation and decision tables rendered", "artifacts": paths + [str(explanation_path), str(formula_manifest_path)], "provenance": {"experiment_id": data.get("experiment_id"), "explanation_artifact": str(explanation_path), "formula_manifest": str(formula_manifest_path)}}
    except Exception as exc:
        return _blocked(node, f"artifact rendering failed: {exc}", reason_code="RENDER_FAILED", next_action="inspect analysis.json lineage and output contract")


def _run_overfitting_diagnostics(contract, node):
    """Run applicable statistical diagnostics; pending is never a success."""
    path = _artifact_dir(contract) / "rolling_evaluation.json"
    if not path.exists():
        return _blocked(node, "rolling evaluation is required before overfitting diagnostics", reason_code="ROLLING_EVALUATION_REQUIRED", next_action="complete model evaluation")
    payload = json.loads(path.read_text(encoding="utf-8"))
    models = payload.get("models", [])
    observations = max((int(item.get("n_predictions", 0)) for item in models), default=0)
    try:
        from ..overfitting_applicability import assess_applicability
    except ImportError:
        from overfitting_applicability import assess_applicability
    losses = payload.get("candidate_losses", {})
    returns = payload.get("candidate_returns")
    net_returns = payload.get("net_of_cost_returns")
    candidate_count = len(models)
    result = assess_applicability(candidate_count, int(payload.get("trial_count", 1)), observations, paired_loss=len(losses) >= 2, portfolio_returns=bool(net_returns), diagnostic_inputs={"paired_losses": next(iter(losses.values()), None), "candidate_family": list(losses), "net_of_costs": bool(net_returns), "pbo_splits": payload.get("pbo_splits", 8), "bootstrap_block_length": payload.get("bootstrap_block_length", 5)})
    try:
        from ..overfitting_applicability import dm_test, white_reality_check, spa_test, deflated_sharpe_ratio, probability_of_backtest_overfitting
    except ImportError:
        from overfitting_applicability import dm_test, white_reality_check, spa_test, deflated_sharpe_ratio, probability_of_backtest_overfitting
    block_length = int(payload.get("bootstrap_block_length", 5))
    replications = int(payload.get("bootstrap_replications", 500))
    diagnostics = {}
    loss_values = list(losses.values()) if isinstance(losses, dict) else []
    if len(loss_values) >= 2 and all(len(item) >= 20 for item in loss_values[:2]):
        diagnostics["DM"] = dm_test(loss_values[0], loss_values[1], block_length, replications)
    if returns is not None:
        if np.asarray(returns).ndim == 2 and np.asarray(returns).shape[1] >= 3:
            diagnostics["WRC"] = white_reality_check(returns, block_length, replications)
            diagnostics["SPA"] = spa_test(returns, block_length, replications)
            diagnostics["PBO"] = probability_of_backtest_overfitting(returns, int(payload.get("pbo_splits", 8)))
    if net_returns is not None:
        diagnostics["DSR"] = deflated_sharpe_ratio(net_returns, int(payload.get("trial_count", max(1, candidate_count))))
    for item in result["methods"]:
        method = item["method"]
        if item["applicable"]:
            item.update(diagnostics.get(method, {"status": "pending", "reason": "applicable diagnostic has not been executed"}))
        elif method not in diagnostics:
            item["status"] = "not_applicable"
    applicable = [item for item in result["methods"] if item["applicable"]]
    result["gate_status"] = "failed" if any(item.get("status") == "failed" for item in applicable) else ("pending" if any(item.get("status") == "pending" for item in applicable) else ("passed" if applicable else "not_triggered"))
    result.update({"execution": "applicability_gated", "selected_model": payload.get("selected_model"), "input_hash": payload.get("input_hash"), "candidate_family": list(losses) if isinstance(losses, dict) else [], "net_of_costs": bool(net_returns)})
    output = _write_json(_artifact_dir(contract) / "backtest_overfitting.json", result)
    if result["gate_status"] == "failed":
        return _blocked(node, "an applicable overfitting diagnostic failed", reason_code="OVERFITTING_DIAGNOSTIC_FAILED", next_action="review candidate family, costs, and selection protocol", artifacts=[output], provenance={"diagnostics": result})
    if result["gate_status"] == "pending":
        return _blocked(node, "an applicable overfitting diagnostic is pending", reason_code="OVERFITTING_DIAGNOSTIC_PENDING", next_action="supply losses/returns and execute the applicable diagnostics", artifacts=[output], provenance={"diagnostics": result})
    return {"status": "passed", "message": "applicable overfitting diagnostics executed; non-triggered tests remain not_applicable", "artifacts": [output], "provenance": {"diagnostics": result}, "reason_code": None, "next_action": "continue to portfolio or render artifacts", "user_action_required": False}


def _run_portfolio_optimization(contract, node):
    """Solve each declared covariance model under the same explicit constraints."""
    rows, _ = _dataset_rows(contract)
    grouped = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        instrument = str(row.get("instrument_id") or row.get("ticker") or row.get("symbol") or "local")
        try:
            value = float(row.get("value", row.get("close", row.get("price"))))
        except (TypeError, ValueError):
            continue
        grouped.setdefault(instrument, []).append(value)
    assets = sorted(grouped)
    artifact = _artifact_dir(contract) / "portfolio_robustness.json"
    if len(assets) < 2 or min((len(grouped[name]) for name in assets), default=0) < 3:
        result = {"status": "fallback", "solver_status": "insufficient_assets", "fallback": {"used": True, "action": "cash", "reason": "portfolio optimization requires at least two assets with three observations each", "weights": {}}, "benchmark": "equal_weight", "binding_constraints": [], "infeasible_reasons": ["insufficient_assets"], "weight_intervals": {}, "turnover_interval": [0.0, 0.0], "objective_interval": [0.0, 0.0]}
        output = _write_json(artifact, result)
        return {"status": "fallback", "message": result["fallback"]["reason"], "artifacts": [output], "fallback_used": True, "reason_code": "PORTFOLIO_INSUFFICIENT_ASSETS", "next_action": "provide a multi-asset dataset or use descriptive/forecasting mode", "user_action_required": True, "provenance": result}
    try:
        from ..portfolio_diagnostics import benchmark_weights, risk_contribution
        from ..portfolio_robustness import compare_covariance_models, solve_constrained_portfolio, sample_covariance, ledoit_wolf_shrinkage, factor_covariance, robust_covariance
    except ImportError:
        import numpy as np
        from portfolio_diagnostics import benchmark_weights, risk_contribution
        from portfolio_robustness import compare_covariance_models, solve_constrained_portfolio, sample_covariance, ledoit_wolf_shrinkage, factor_covariance, robust_covariance
    length = min(len(grouped[name]) for name in assets)
    matrix = np.asarray([grouped[name][-length:] for name in assets], dtype=float).T
    returns = matrix[1:] / matrix[:-1] - 1.0
    constraints = dict(contract.get("constraints") or {})
    transaction_cost_bps = float(contract.get("transaction_cost_bps", constraints.get("transaction_cost_bps", 0.0)))
    risk_aversion = float(contract.get("risk_aversion", constraints.get("risk_aversion", 1.0)))
    prior = constraints.get("prior_weights")
    if prior is None:
        prior = benchmark_weights(len(assets), "equal_weight").tolist()
    expected_returns = returns.mean(axis=0)
    covariance_functions = {
        "sample": lambda: sample_covariance(returns),
        "ledoit_wolf": lambda: ledoit_wolf_shrinkage(returns),
        "factor": lambda: factor_covariance(returns),
        "robust": lambda: robust_covariance(returns),
    }
    solutions = []
    for model, covariance_factory in covariance_functions.items():
        covariance = covariance_factory()
        solved = solve_constrained_portfolio(expected_returns, covariance, constraints, prior, risk_aversion, transaction_cost_bps)
        weights = np.asarray(solved["weights"], dtype=float)
        solutions.append({"model": model, "solver_status": solved["status"], "objective": solved.get("objective"), "weights": {asset: float(weight) for asset, weight in zip(assets, weights)}, "constraint_diagnostics": solved.get("constraints", {}), "active_constraints": solved.get("constraints", {}).get("active_constraints", []), "turnover": solved.get("constraints", {}).get("turnover"), "transaction_cost": solved.get("transaction_cost", 0.0), "covariance": covariance.tolist()})
    feasible = [item for item in solutions if item["solver_status"] == "optimal" and item["constraint_diagnostics"].get("feasible")]
    if not feasible:
        result = {"status": "fallback", "solver_status": "infeasible", "fallback": {"used": True, "action": "cash", "reason": "all covariance-specific constrained solves were infeasible", "weights": {}}, "solutions": solutions, "covariance_models": solutions, "infeasible_reasons": [item["constraint_diagnostics"].get("residuals", {}) for item in solutions], "binding_constraints": []}
        output = _write_json(artifact, result)
        return {"status": "fallback", "message": result["fallback"]["reason"], "artifacts": [output], "fallback_used": True, "reason_code": "PORTFOLIO_INFEASIBLE", "next_action": "relax the declared contract or use cash/prior weights", "user_action_required": True, "provenance": result}
    selected_solution = max(feasible, key=lambda item: item["objective"] if item["objective"] is not None else -float("inf"))
    weights = np.asarray(list(selected_solution["weights"].values()), dtype=float)
    covariance = np.asarray(selected_solution["covariance"], dtype=float)
    benchmark = np.asarray(prior, dtype=float)
    risk = risk_contribution(weights, covariance)
    covariance_comparison = compare_covariance_models(returns)
    result = {"status": "passed", "solver_status": "optimal", "selected_covariance_model": selected_solution["model"], "weights": selected_solution["weights"], "benchmark": "prior_or_equal_weight", "active_return": float((weights - benchmark) @ expected_returns), "risk_contribution": {asset: float(value) for asset, value in zip(assets, risk)}, "factor_exposures": {}, "industry_exposure": {}, "turnover_contribution": {asset: float(abs(weights[index] - benchmark[index])) for index, asset in enumerate(assets)}, "cost_attribution": {"transaction_cost_bps": transaction_cost_bps, "estimated_cost": float(selected_solution.get("transaction_cost", 0.0))}, "binding_constraints": selected_solution["active_constraints"], "constraint_diagnostics": selected_solution["constraint_diagnostics"], "covariance_comparison": covariance_comparison, "covariance_models": solutions, "solutions": solutions, "return_matrix": returns.tolist(), "asset_order": assets, "expected_returns": expected_returns.tolist(), "prior_weights": benchmark.tolist(), "risk_aversion": risk_aversion, "transaction_cost_bps": transaction_cost_bps, "fallback": {"used": False, "reason": None}, "stress": {"weight_intervals": {asset: [float(weights[index]), float(weights[index])] for index, asset in enumerate(assets)}, "turnover_interval": [float(selected_solution["turnover"] or 0.0), float(selected_solution["turnover"] or 0.0)], "objective_interval": [float(selected_solution["objective"] or 0.0), float(selected_solution["objective"] or 0.0)], "infeasible_reasons": []}}
    output = _write_json(artifact, result)
    return {"status": "passed", "message": "equal-weight constrained portfolio baseline created", "artifacts": [output], "provenance": result}


def _post_selection_stress_test(contract, node):
    """Recompute return, risk, cost and constraint status for every scenario."""
    portfolio_path = _artifact_dir(contract) / "portfolio_robustness.json"
    rolling_path = _artifact_dir(contract) / "rolling_evaluation.json"
    if not portfolio_path.exists() and not rolling_path.exists():
        return _blocked(node, "post-selection stress requires model or portfolio output", reason_code="SELECTION_OUTPUT_REQUIRED", next_action="complete model evaluation")
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8")) if portfolio_path.exists() else {}
    scenarios = [{"scenario": "base", "return_shock": 0.0, "cost_shock_bps": 0.0}, {"scenario": "adverse", "return_shock": -0.10, "cost_shock_bps": 10.0}, {"scenario": "severe", "return_shock": -0.20, "cost_shock_bps": 25.0}]
    if portfolio.get("fallback", {}).get("used") or not portfolio.get("weights"):
        result = {"status": "degraded", "model_status": "fallback", "stress_status": "not_available", "scenarios": [{**scenario, "status": "not_available", "reason": "portfolio solver fallback has no investable weights"} for scenario in scenarios], "fallback": portfolio.get("fallback", {"used": True}), "binding_constraints": portfolio.get("binding_constraints", []), "next_action": "resolve portfolio infeasibility before relying on stress metrics"}
    else:
        try:
            from ..portfolio_robustness import validate_constraints
        except ImportError:
            from portfolio_robustness import validate_constraints
        weights = np.asarray(list(portfolio["weights"].values()), dtype=float)
        prior = np.asarray(portfolio.get("prior_weights", weights), dtype=float)
        returns = np.asarray(portfolio.get("return_matrix", []), dtype=float)
        constraints = dict(contract.get("constraints") or {})
        scenarios_out = []
        for scenario in scenarios:
            scenario_returns = returns + float(scenario["return_shock"])
            portfolio_returns = scenario_returns @ weights if scenario_returns.size else np.asarray([])
            turnover = float(np.abs(weights - prior).sum())
            cost = turnover * (float(portfolio.get("transaction_cost_bps", 0.0)) + float(scenario["cost_shock_bps"])) / 10000.0
            net = portfolio_returns - cost if portfolio_returns.size else np.asarray([])
            wealth = np.cumprod(1.0 + net) if net.size else np.asarray([])
            drawdown = (wealth / np.maximum.accumulate(wealth) - 1.0) if wealth.size else np.asarray([])
            losses = -net if net.size else np.asarray([])
            alpha = float(contract.get("confidence_level", 0.95))
            var = float(np.quantile(losses, alpha)) if losses.size else None
            tail = losses[losses >= var] if losses.size and var is not None else np.asarray([])
            scenarios_out.append({"scenario": scenario["scenario"], "status": "passed", "return_shock": scenario["return_shock"], "cost_shock_bps": scenario["cost_shock_bps"], "return": float(net.sum()) if net.size else None, "volatility": float(net.std(ddof=1)) if net.size > 1 else None, "max_drawdown": float(drawdown.min()) if drawdown.size else None, "var": var, "es": float(tail.mean()) if tail.size else var, "turnover": turnover, "transaction_cost": cost, "weight_change": {asset: float(weights[index] - prior[index]) for index, asset in enumerate(portfolio.get("asset_order", []))}, "constraint_status": validate_constraints(weights, constraints, prior), "fallback": portfolio.get("fallback", {"used": False})})
        result = {"status": "passed", "model_status": "active", "stress_status": "completed", "scenarios": scenarios_out, "fallback": portfolio.get("fallback", {"used": False}), "binding_constraints": portfolio.get("binding_constraints", []), "next_action": "monitor drift and refresh on material change"}
    output = _write_json(_artifact_dir(contract) / "monitoring_status.json", result)
    return {"status": "passed", "message": "post-selection stress scenarios saved", "artifacts": [output], "provenance": result}


def _unimplemented(name):
    def handler(contract, node):
        return _blocked(node, f"{name} is not implemented by the bounded default runtime; supply a registered handler")
    return handler


HANDLERS = {
    "discover_sources": _discover_sources,
    "capture_data": _data_capture,
    "run_preflight": _preflight,
    "normalize_dataset": _normalize_dataset,
    "audit_dataset": _audit_dataset,
    "build_features": _build_features,
    "run_models": _run_models,
    "run_overfitting_diagnostics": _run_overfitting_diagnostics,
    "run_portfolio_optimization": _run_portfolio_optimization,
    "post_selection_stress_test": _post_selection_stress_test,
    "render_artifacts": _render_artifacts,
}


def validate_handlers(plan, handlers=None):
    registry = HANDLERS if handlers is None else handlers
    missing = sorted({node["tool"] for node in plan.get("nodes", []) if node["tool"] not in registry})
    return {"valid": not missing, "missing": missing, "registered": sorted(registry)}
