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
    code_version = "financial-research-optimizer-0.8.2"
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
        "model_cards": [{"model_id": "historical_mean_baseline", "version": "0.8.2", "estimand": "conditional mean proxy", "objective": "baseline", "validation_protocol": "expanding_window", "overfitting_diagnostics": "not_applicable", "failure_mode": "regime change", "status": "challenger"}, {"model_id": "naive_last_value", "version": "0.8.2", "estimand": "one-step persistence", "objective": "baseline", "validation_protocol": "expanding_window", "overfitting_diagnostics": "not_applicable", "failure_mode": "price jump", "status": "challenger"}],
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
    forecasts, actuals, mean_forecasts = [], [], []
    for index in range(1, len(values)):
        forecasts.append(values[index - 1])
        actuals.append(values[index])
        mean_forecasts.append(statistics.fmean(values[:index]))
    errors = [actual - forecast for actual, forecast in zip(actuals, forecasts)]
    mean_errors = [actual - forecast for actual, forecast in zip(actuals, mean_forecasts)]
    rmse = (statistics.fmean([error * error for error in errors]) ** 0.5) if errors else None
    mean_rmse = (statistics.fmean([error * error for error in mean_errors]) ** 0.5) if mean_errors else None
    selected = "naive_last_value" if rmse is not None and (mean_rmse is None or rmse <= mean_rmse) else "historical_mean_baseline"
    rolling = {"status": "pass" if errors else "not_available", "models": [{"model_id": "naive_last_value", "n_predictions": len(errors), "rmse": rmse, "lineage_refs": metric_refs}, {"model_id": "historical_mean_baseline", "n_predictions": len(mean_errors), "rmse": mean_rmse, "lineage_refs": metric_refs}], "selected_model": selected, "protocol": {"type": "expanding_window", "minimum_train": 1, "horizon": 1}, "uncertainty_status": "not_calibrated", "input_hash": source_hash}
    rolling_path = _write_json(_artifact_dir(contract) / "rolling_evaluation.json", rolling)
    forecast_contract = {"target": str(contract.get("target", "value")), "forecast_types": ["point", "interval"], "metrics": {"primary": ["rmse"], "calibration": ["not_calibrated"]}, "validity_conditions": ["point-in-time audit passes", "rolling evaluation is out of sample"], "known_failure_modes": ["regime change", "small sample"], "ood_status": "not_checked"}
    analysis["forecast_contract"] = forecast_contract
    analysis["model_cards"][0]["status"] = "selected" if selected == "historical_mean_baseline" else "challenger"
    analysis["model_cards"][1]["status"] = "selected" if selected == "naive_last_value" else "challenger"
    path = _write_json(_artifact_dir(contract) / "analysis.json", analysis)
    return {"status": "passed", "message": "naive and historical-mean baselines with rolling evaluation created", "artifacts": [path, rolling_path], "provenance": {"model": "historical_mean_baseline+naive_last_value", "experiment_id": analysis["experiment_id"], "uncertainty_status": "not_calibrated"}}


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
        validate_payload(data, {"mode": contract.get("mode", "forecasting"), "output_level": contract.get("output_level", "standard")})
        output_dir = _artifact_dir(contract)
        (output_dir / "financial_research_brief.html").write_text(render_html(data, contract, data), encoding="utf-8")
        rows = normalize_rows(data["decision_rows"], data.get("experiment_id"), data.get("reproducibility_status"), data.get("online_status", {}))
        paths = [str(output_dir / "financial_research_brief.html")] + [str(path) for path in write_decision_table(rows, output_dir, "both")]
        return {"status": "passed", "message": "offline HTML and decision tables rendered", "artifacts": paths, "provenance": {"experiment_id": data.get("experiment_id")}}
    except Exception as exc:
        return _blocked(node, f"artifact rendering failed: {exc}", reason_code="RENDER_FAILED", next_action="inspect analysis.json lineage and output contract")


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
    "run_overfitting_diagnostics": _unimplemented("run_overfitting_diagnostics"),
    "run_portfolio_optimization": _unimplemented("run_portfolio_optimization"),
    "post_selection_stress_test": _unimplemented("post_selection_stress_test"),
    "render_artifacts": _render_artifacts,
}


def validate_handlers(plan, handlers=None):
    registry = HANDLERS if handlers is None else handlers
    missing = sorted({node["tool"] for node in plan.get("nodes", []) if node["tool"] not in registry})
    return {"valid": not missing, "missing": missing, "registered": sorted(registry)}
