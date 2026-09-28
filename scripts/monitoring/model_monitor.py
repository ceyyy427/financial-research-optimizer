"""Model/feature drift checks with explicit retrain and fallback decisions."""
import argparse
import json
from pathlib import Path
import math


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _std(values):
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _psi(reference, current, bins=10):
    if not reference or not current:
        return None
    ordered = sorted(reference)
    edges = [ordered[min(len(ordered) - 1, int(i * len(ordered) / bins))] for i in range(bins)]
    def counts(values):
        result = [0] * bins
        for value in values:
            bucket = sum(value >= edge for edge in edges) - 1
            result[max(0, min(bins - 1, bucket))] += 1
        return result
    ref = counts(reference)
    cur = counts(current)
    total_ref, total_cur = len(reference), len(current)
    return sum(((c / total_cur + 1e-6) - (r / total_ref + 1e-6)) * math.log((c / total_cur + 1e-6) / (r / total_ref + 1e-6)) for r, c in zip(ref, cur))


def monitor_model(payload):
    thresholds = {"psi": 0.2, "mean_shift": 3.0, "residual_shift": 2.0, **payload.get("thresholds", {})}
    checks = []
    feature_psi_values = []
    for feature, reference in payload.get("reference_features", {}).items():
        current = payload.get("current_features", {}).get(feature, [])
        value = _psi(reference, current)
        if value is not None:
            feature_psi_values.append(value)
            checks.append({"check": f"feature_psi:{feature}", "value": value, "threshold": thresholds["psi"], "status": "warning" if value > thresholds["psi"] else "ok"})
    ref_pred = payload.get("reference_predictions", [])
    cur_pred = payload.get("current_predictions", [])
    if ref_pred and cur_pred:
        scale = _std(ref_pred) or 1.0
        shift = abs(_mean(cur_pred) - _mean(ref_pred)) / scale
        checks.append({"check": "prediction_mean_shift", "value": shift, "threshold": thresholds["mean_shift"], "status": "warning" if shift > thresholds["mean_shift"] else "ok"})
    residuals = payload.get("current_residuals", [])
    if residuals:
        residual_shift = abs(_mean(residuals)) / (_std(residuals) or 1.0)
        checks.append({"check": "residual_shift", "value": residual_shift, "threshold": thresholds["residual_shift"], "status": "warning" if residual_shift > thresholds["residual_shift"] else "ok"})
    warning = any(check["status"] == "warning" for check in checks)
    critical = any(check["value"] > check["threshold"] * 2 for check in checks if isinstance(check.get("value"), (int, float)))
    model_status = "fallback" if critical else ("retrain_required" if warning else "active")
    return {"model_id": payload.get("model_id", "unknown"), "model_status": model_status, "drift_status": "failed" if critical else ("warning" if warning else "ok"), "retrain_trigger": "; ".join(check["check"] for check in checks if check["status"] == "warning") or "none", "fallback": payload.get("fallback", "benchmark") if model_status == "fallback" else "none", "checks": checks, "data_status": "fallback" if critical else ("degraded" if warning else "ready")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = monitor_model(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
