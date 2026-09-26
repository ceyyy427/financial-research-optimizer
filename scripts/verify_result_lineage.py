#!/usr/bin/env python3
"""Verify that numerical output entering reader-facing artifacts has lineage."""
import argparse
import hashlib
import json
from pathlib import Path


REQUIRED = ("metric_id", "value", "calculation_id", "input_hash", "code_version", "formula", "source_ids")
LINEAGE_CONTAINER_KEYS = (
    "selection_protocol", "backtest_overfitting", "source_reconciliation",
    "feature_label_audit", "portfolio_robustness", "online_status"
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calculation_fingerprint(metric):
    payload = {key: metric.get(key) for key in ("metric_id", "input_hash", "code_version", "formula", "source_ids")}
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:16]


def _has_numeric(values):
    if isinstance(values, bool) or values is None:
        return False
    if isinstance(values, (int, float)):
        return True
    if isinstance(values, list):
        return any(_has_numeric(item) for item in values)
    if isinstance(values, dict):
        return any(_has_numeric(item) for item in values.values())
    return False


def _refs(node):
    if not isinstance(node, dict):
        return []
    value = node.get("lineage_refs", [])
    return value if isinstance(value, list) else []


def verify_result_lineage(data, input_files=None, require_metric_for_empty=False):
    """Return a structured audit; callers should stop artifact generation on failure."""
    errors = []
    warnings = []
    result = data.get("result_lineage") if isinstance(data, dict) else None
    if not isinstance(result, dict):
        return {"status": "failed", "metric_count": 0, "errors": ["missing result_lineage object"], "warnings": []}
    metrics = result.get("metrics")
    if not isinstance(metrics, list):
        return {"status": "failed", "metric_count": 0, "errors": ["result_lineage.metrics must be a list"], "warnings": []}
    if require_metric_for_empty and not metrics:
        errors.append("result_lineage.metrics cannot be empty for a numerical run")
    metric_ids = set()
    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            errors.append(f"result_lineage.metrics[{index}] must be an object")
            continue
        missing = [field for field in REQUIRED if field not in metric or metric[field] in (None, "", [])]
        if missing:
            errors.append(f"result_lineage.metrics[{index}] missing {missing}")
            continue
        metric_id = str(metric["metric_id"])
        if metric_id in metric_ids:
            errors.append(f"duplicate metric_id: {metric_id}")
        metric_ids.add(metric_id)
        if input_files and metric.get("input_files"):
            for input_file in metric["input_files"]:
                path = Path(input_file)
                if not path.exists():
                    errors.append(f"{metric_id}: input file does not exist: {input_file}")
                elif hash_file(path) != metric["input_hash"]:
                    errors.append(f"{metric_id}: input_hash does not match {input_file}")
        declared_fp = metric.get("calculation_fingerprint")
        if declared_fp and declared_fp != calculation_fingerprint(metric):
            errors.append(f"{metric_id}: calculation_fingerprint mismatch")
    if "charts" in data:
        for index, chart in enumerate(data.get("charts", [])):
            if _has_numeric(chart.get("series", [])) or _has_numeric(chart.get("band", {})):
                refs = _refs(chart)
                if not refs:
                    errors.append(f"charts[{index}] has numerical values without lineage_refs")
                elif any(ref not in metric_ids for ref in refs):
                    errors.append(f"charts[{index}] references unknown metric IDs")
    if _has_numeric(data.get("series")):
        refs = data.get("series_lineage_refs", [])
        if not refs:
            errors.append("series has numerical values without series_lineage_refs")
        elif any(ref not in metric_ids for ref in refs):
            errors.append("series references unknown metric IDs")
    for key in LINEAGE_CONTAINER_KEYS:
        node = data.get(key)
        if node is not None and _has_numeric(node):
            refs = _refs(node)
            if not refs:
                errors.append(f"{key} has numerical values without lineage_refs")
            elif any(ref not in metric_ids for ref in refs):
                errors.append(f"{key} references unknown metric IDs")
    for index, module in enumerate(data.get("modules", [])):
        for metric_index, metric in enumerate(module.get("metrics", []) if isinstance(module, dict) else []):
            if isinstance(metric, dict) and _has_numeric(metric.get("value")):
                refs = _refs(metric)
                if not refs:
                    errors.append(f"modules[{index}].metrics[{metric_index}] has numerical value without lineage_refs")
                elif any(ref not in metric_ids for ref in refs):
                    errors.append(f"modules[{index}].metrics[{metric_index}] references unknown metric IDs")
    status = "failed" if errors else ("partial" if warnings else "pass")
    return {"status": status, "metric_count": len(metrics), "metric_ids": sorted(metric_ids), "errors": errors, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="analysis JSON")
    parser.add_argument("--input-file", action="append", default=[], help="optional raw input file whose hash must match a metric")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    audit = verify_result_lineage(data, args.input_file)
    rendered = json.dumps(audit, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if audit["status"] != "failed" else 2)


if __name__ == "__main__":
    main()
