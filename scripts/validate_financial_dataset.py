#!/usr/bin/env python3
"""Audit a time-indexed financial CSV without fitting a model."""
import argparse, hashlib, json
from pathlib import Path
try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - exercised in dependency-free environments
    raise SystemExit("validate_financial_dataset.py requires pandas; install with python3 -m pip install -e .") from exc
try:
    from .config_utils import load_config
    from .data_quality import audit_grain, quality_score, compare_schema
except ImportError:
    from config_utils import load_config
    from data_quality import audit_grain, quality_score, compare_schema


def _parse_datetime(values):
    try:
        return pd.to_datetime(values, errors="coerce", utc=True, format="mixed")
    except TypeError:  # pandas versions before the mixed-format keyword
        return pd.to_datetime(values, errors="coerce", utc=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--date-column", default="date")
    ap.add_argument("--target-column", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--reconciliation", default=None)
    ap.add_argument("--reference-schema", default=None, help="CSV or JSON schema used for schema-drift comparison")
    args = ap.parse_args()
    path = Path(args.csv)
    df = pd.read_csv(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {"file": str(path), "rows": int(len(df)), "columns": list(df.columns), "lineage_refs": [f"dataset:{digest}"], "input_hash": digest}
    config = load_config(args.config) if args.config else None
    if config:
        report["research_config"] = {"path": config["_config_path"], "fingerprint": config["_config_fingerprint"], "universe": config["universe"], "target": config["target"], "cutoff": config["cutoff"], "horizon": config["horizon"], "costs": config["costs"], "constraints": config["constraints"], "risk_measure": config["risk_measure"]}
    if args.date_column not in df.columns:
        report["error"] = f"missing date column: {args.date_column}"
    else:
        dt = _parse_datetime(df[args.date_column])
        report["invalid_dates"] = int(dt.isna().sum())
        report["duplicate_dates"] = int(dt.duplicated().sum())
        report["sorted_non_decreasing"] = bool(dt.dropna().is_monotonic_increasing)
        report["date_start"] = None if dt.dropna().empty else str(dt.min())
        report["date_end"] = None if dt.dropna().empty else str(dt.max())
        if config:
            cutoff = pd.Timestamp(config["cutoff"], tz="UTC")
            report["rows_after_config_cutoff"] = int((dt > cutoff).sum())
            report["cutoff_pass"] = report["rows_after_config_cutoff"] == 0
    if config and "instrument_id" in df.columns:
        observed = set(df["instrument_id"].dropna().astype(str))
        requested = set(map(str, config["universe"]))
        report["universe_missing"] = sorted(requested - observed)
        report["universe_unexpected"] = sorted(observed - requested)
        report["universe_pass"] = not report["universe_missing"]
    pit_fields = {"observation_date", "release_date", "availability_date", "vintage_date", "effective_timestamp"}
    if pit_fields.intersection(df.columns):
        pit = {}
        for field in sorted(pit_fields):
            if field in df.columns:
                pit[field] = int(_parse_datetime(df[field]).isna().sum())
        report["point_in_time_invalid_dates"] = pit
        report["point_in_time_columns_present"] = sorted(pit_fields.intersection(df.columns))
    report["missing_by_column"] = {c: int(v) for c, v in df.isna().sum().items()}
    report["grain"] = audit_grain(df)
    if args.reference_schema:
        reference_path = Path(args.reference_schema)
        if reference_path.suffix.lower() == ".csv":
            reference = pd.read_csv(reference_path, nrows=100)
            reference_schema = {column: {"type": str(reference[column].dtype)} for column in reference.columns}
        else:
            reference_payload = json.loads(reference_path.read_text(encoding="utf-8"))
            reference_schema = reference_payload.get("properties", reference_payload)
        current_schema = {column: {"type": str(df[column].dtype)} for column in df.columns}
        report["schema_drift"] = compare_schema(reference_schema, current_schema)
    numeric = df.select_dtypes(include="number")
    report["numeric_summary"] = {
        c: {"min": None if numeric[c].dropna().empty else float(numeric[c].min()),
            "max": None if numeric[c].dropna().empty else float(numeric[c].max()),
            "mean": None if numeric[c].dropna().empty else float(numeric[c].mean()),
            "std": None if numeric[c].dropna().empty else float(numeric[c].std())}
        for c in numeric.columns
    }
    if args.target_column:
        report["target_present"] = args.target_column in df.columns
    if args.reconciliation:
        reconciliation = json.loads(Path(args.reconciliation).read_text(encoding="utf-8"))
        report["source_reconciliation"] = reconciliation.get("summary", reconciliation)
        report["dependency_analysis_blocked"] = bool(report["source_reconciliation"].get("stop_dependency_analysis", False))
    report["quality"] = quality_score(report)
    report["metric_lineage"] = [
        {"metric_id": f"quality_{key}", "value": value, "calculation_id": f"quality_{digest[:12]}",
         "input_hash": digest, "code_version": "validate_financial_dataset", "formula": f"quality_score.{key}",
         "source_ids": [f"dataset:{digest[:12]}"]}
        for key, value in report["quality"].items() if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    out = Path(args.output) if args.output else path.with_name(path.stem + "_audit.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
