#!/usr/bin/env python3
"""Run blocking checks before an executable research workflow starts."""
import argparse
import json
from pathlib import Path
try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - exercised in dependency-free environments
    raise SystemExit("run_preflight.py requires pandas; install with python3 -m pip install -e .") from exc

try:
    from .config_utils import load_config
    from .manifest_utils import load_manifest
    from .feature_label_audit import audit_feature_label_contract
    from .verify_result_lineage import verify_result_lineage
except ImportError:
    from config_utils import load_config
    from manifest_utils import load_manifest
    from feature_label_audit import audit_feature_label_contract
    from verify_result_lineage import verify_result_lineage


def _check(checks, check_id, status, message):
    checks.append({"check_id": check_id, "status": status, "message": message})


def run_preflight(config_path, manifest_path=None, analysis_path=None, dataset_path=None, reconciliation_path=None, freshness_path=None, monitoring_path=None):
    checks = []
    blocking = []
    try:
        config = load_config(config_path)
        _check(checks, "config", "pass", f"validated {config['_config_path']}")
    except Exception as exc:
        return {"status": "blocked", "mode": "unknown", "output_level": "unknown", "checks": [{"check_id": "config", "status": "fail", "message": str(exc)}], "blocking_reasons": [str(exc)]}
    level = config["output_level"]
    mode = config["mode"]
    required_manifest = config.get("preflight", {}).get("require_manifest", level in {"research_grade", "portfolio_grade"})
    required_dataset = config.get("preflight", {}).get("require_dataset", level == "portfolio_grade")
    required_reconciliation = config.get("preflight", {}).get("require_reconciliation", level == "portfolio_grade")
    manifest = None
    if manifest_path:
        try:
            manifest = load_manifest(manifest_path)
            _check(checks, "manifest", "pass", "experiment manifest is valid")
            if manifest.get("config_fingerprint") not in {config.get("_config_fingerprint"), "", None}:
                blocking.append("manifest.config_fingerprint does not match the validated config")
                _check(checks, "manifest_config_match", "fail", blocking[-1])
            else:
                _check(checks, "manifest_config_match", "pass", "manifest and config fingerprints match")
            for field in ("mode", "output_level"):
                if manifest.get(field) and manifest[field] != config.get(field):
                    blocking.append(f"manifest.{field} does not match the validated config")
                    _check(checks, f"manifest_{field}_match", "fail", blocking[-1])
                elif manifest.get(field):
                    _check(checks, f"manifest_{field}_match", "pass", f"manifest and config {field} match")
        except Exception as exc:
            blocking.append(str(exc))
            _check(checks, "manifest", "fail", str(exc))
    elif required_manifest:
        blocking.append("manifest is required for this output level")
        _check(checks, "manifest", "fail", blocking[-1])
    else:
        _check(checks, "manifest", "skip", "manifest not required for this output level")
    if analysis_path:
        try:
            data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
            required = {"meta", "summary", "modules", "decision_rows"}
            if mode == "data_audit":
                required.add("sources")
            if mode in {"descriptive_analysis", "forecasting", "backtest", "portfolio_research"}:
                required.add("charts")
            if mode in {"forecasting", "backtest", "portfolio_research"}:
                required.update({"forecast", "model_cards", "selection_protocol"})
            if mode in {"backtest", "portfolio_research"}:
                required.add("backtest_overfitting")
            if mode == "portfolio_research":
                required.add("portfolio_robustness")
            missing = sorted(required - set(data))
            if missing:
                raise ValueError(f"analysis missing fields: {missing}")
            if mode in {"backtest", "portfolio_research"} and data.get("backtest_overfitting", {}).get("gate_status") == "failed":
                raise ValueError("applicable backtest-overfitting gate failed")
            if mode == "portfolio_research" and data.get("portfolio_robustness", {}).get("fallback", {}).get("status") == "infeasible_unresolved":
                raise ValueError("portfolio fallback is unresolved")
            _check(checks, "analysis", "pass", "analysis JSON contains the executable output blocks")
            lineage = verify_result_lineage(data, require_metric_for_empty=mode != "data_audit")
            if lineage["status"] == "failed":
                raise ValueError("result lineage failed: " + "; ".join(lineage["errors"]))
            _check(checks, "result_lineage", "pass", f"verified {lineage['metric_count']} result-lineage metrics")
        except Exception as exc:
            blocking.append(str(exc))
            _check(checks, "analysis", "fail", str(exc))
    else:
        _check(checks, "analysis", "skip", "analysis JSON not supplied")
    if dataset_path:
        if Path(dataset_path).exists():
            frame = pd.read_csv(dataset_path)
            required_rows = config["evaluation"]["train_period"] + config["evaluation"]["validation_period"] + config["evaluation"]["test_period"]
            if len(frame) < required_rows:
                blocking.append(f"dataset has {len(frame)} rows but requires at least {required_rows}")
                _check(checks, "sample_size", "fail", blocking[-1])
            else:
                _check(checks, "sample_size", "pass", f"dataset has {len(frame)} rows; minimum is {required_rows}")
            availability_field = config["feature_label_contract"]["availability_time_field"]
            if availability_field in frame.columns:
                audit = audit_feature_label_contract(frame, config["feature_label_contract"], config["cutoff"])
                if not audit["safe"]:
                    blocking.append("feature/label audit found future availability or contract violations")
                    _check(checks, "feature_label", "fail", blocking[-1])
                else:
                    _check(checks, "feature_label", "pass", "availability and lineage audit passed")
            else:
                _check(checks, "feature_label", "warning", f"dataset does not expose {availability_field}; run feature audit on the derived table")
            _check(checks, "dataset", "pass", f"dataset path exists: {dataset_path}")
        else:
            blocking.append(f"dataset path missing: {dataset_path}")
            _check(checks, "dataset", "fail", blocking[-1])
    elif required_dataset:
        blocking.append("dataset is required for portfolio_grade")
        _check(checks, "dataset", "fail", blocking[-1])
    else:
        _check(checks, "dataset", "skip", "dataset not required for this preflight")
    if reconciliation_path:
        try:
            reconciliation = json.loads(Path(reconciliation_path).read_text(encoding="utf-8"))
            summary = reconciliation.get("summary", reconciliation)
            if summary.get("stop_dependency_analysis"):
                blocking.append("source reconciliation blocks dependent analysis")
                _check(checks, "source_reconciliation", "fail", blocking[-1])
            else:
                _check(checks, "source_reconciliation", "pass", "no blocking source conflict")
        except Exception as exc:
            blocking.append(str(exc))
            _check(checks, "source_reconciliation", "fail", str(exc))
    elif required_reconciliation:
        blocking.append("source reconciliation is required for portfolio_grade")
        _check(checks, "source_reconciliation", "fail", blocking[-1])
    else:
        _check(checks, "source_reconciliation", "skip", "source reconciliation not required for this preflight")
    dynamic_status = "ready"
    for check_id, path, label in (("freshness", freshness_path, "freshness"), ("monitoring", monitoring_path, "model monitoring")):
        if path:
            try:
                dynamic = json.loads(Path(path).read_text(encoding="utf-8"))
                state = dynamic.get("status", dynamic.get("data_status", dynamic.get("model_status", "ready")))
                if state == "blocked":
                    blocking.append(f"{label} status is blocked")
                    _check(checks, check_id, "fail", blocking[-1])
                else:
                    if state in {"stale", "degraded", "fallback", "retrain_required", "warning"} and dynamic_status == "ready":
                        dynamic_status = "fallback" if state == "fallback" else ("degraded" if state in {"degraded", "retrain_required", "warning"} else state)
                    _check(checks, check_id, "warning" if state != "ready" else "pass", f"{label} status: {state}")
            except Exception as exc:
                blocking.append(f"{label} status unreadable: {exc}")
                _check(checks, check_id, "fail", blocking[-1])
        elif config.get("online", {}).get("enabled"):
            dynamic_status = "degraded" if dynamic_status == "ready" else dynamic_status
            _check(checks, check_id, "warning", f"online mode enabled but {label} artifact was not supplied")
        else:
            _check(checks, check_id, "skip", f"online {label} not required")
    result = {"status": "blocked" if blocking else dynamic_status, "mode": mode, "output_level": level, "checks": checks, "blocking_reasons": blocking, "config_fingerprint": config.get("_config_fingerprint"), "manifest_fingerprint": (manifest or {}).get("_manifest_fingerprint")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--reconciliation", type=Path)
    parser.add_argument("--freshness", type=Path)
    parser.add_argument("--monitoring", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_preflight(args.config, args.manifest, args.analysis, args.dataset, args.reconciliation, args.freshness, args.monitoring)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] != "blocked" else 2)


if __name__ == "__main__":
    main()
