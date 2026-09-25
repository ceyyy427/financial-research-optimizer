#!/usr/bin/env python3
"""Audit a time-indexed financial CSV without fitting a model."""
import argparse, json
from pathlib import Path
import pandas as pd
from config_utils import load_config

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--date-column", default="date")
    ap.add_argument("--target-column", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--reconciliation", default=None)
    args = ap.parse_args()
    path = Path(args.csv)
    df = pd.read_csv(path)
    report = {"file": str(path), "rows": int(len(df)), "columns": list(df.columns)}
    config = load_config(args.config) if args.config else None
    if config:
        report["research_config"] = {"path": config["_config_path"], "fingerprint": config["_config_fingerprint"], "universe": config["universe"], "target": config["target"], "cutoff": config["cutoff"], "horizon": config["horizon"], "costs": config["costs"], "constraints": config["constraints"], "risk_measure": config["risk_measure"]}
    if args.date_column not in df.columns:
        report["error"] = f"missing date column: {args.date_column}"
    else:
        dt = pd.to_datetime(df[args.date_column], errors="coerce", utc=True)
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
                pit[field] = int(pd.to_datetime(df[field], errors="coerce", utc=True).isna().sum())
        report["point_in_time_invalid_dates"] = pit
        report["point_in_time_columns_present"] = sorted(pit_fields.intersection(df.columns))
    report["missing_by_column"] = {c: int(v) for c, v in df.isna().sum().items()}
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
    out = Path(args.output) if args.output else path.with_name(path.stem + "_audit.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
