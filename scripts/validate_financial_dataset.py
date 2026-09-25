#!/usr/bin/env python3
"""Audit a time-indexed financial CSV without fitting a model."""
import argparse, json
from pathlib import Path
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--date-column", default="date")
    ap.add_argument("--target-column", default=None)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    path = Path(args.csv)
    df = pd.read_csv(path)
    report = {"file": str(path), "rows": int(len(df)), "columns": list(df.columns)}
    if args.date_column not in df.columns:
        report["error"] = f"missing date column: {args.date_column}"
    else:
        dt = pd.to_datetime(df[args.date_column], errors="coerce", utc=True)
        report["invalid_dates"] = int(dt.isna().sum())
        report["duplicate_dates"] = int(dt.duplicated().sum())
        report["sorted_non_decreasing"] = bool(dt.dropna().is_monotonic_increasing)
        report["date_start"] = None if dt.dropna().empty else str(dt.min())
        report["date_end"] = None if dt.dropna().empty else str(dt.max())
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
    out = Path(args.output) if args.output else path.with_name(path.stem + "_audit.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

