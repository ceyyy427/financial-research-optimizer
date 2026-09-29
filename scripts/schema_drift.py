#!/usr/bin/env python3
"""Compare the schema of two JSON schema manifests or CSV datasets."""
import argparse
import json
from pathlib import Path

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise SystemExit("schema_drift.py requires pandas; install with python3 -m pip install -e .") from exc

try:
    from .data_quality import compare_schema
except ImportError:
    from data_quality import compare_schema


def _load(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, nrows=100)
        return {column: {"type": str(frame[column].dtype)} for column in frame.columns}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "properties" in payload:
        properties = payload["properties"]
        return {name: {"type": spec.get("type"), "unit": spec.get("unit")} for name, spec in properties.items()}
    return payload


def schema_manifest(payload):
    """Build a comparable field/type manifest from a raw response or rows."""
    if isinstance(payload, dict):
        for key in ("observations", "data", "results", "rows"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if isinstance(payload, list):
        rows = [row for row in payload if isinstance(row, dict)]
        if not rows:
            return {}
        fields = sorted({key for row in rows for key in row})
        return {key: {"type": type(next((row[key] for row in rows if key in row and row[key] is not None), None)).__name__} for key in fields}
    if isinstance(payload, dict):
        return {key: {"type": type(value).__name__} for key, value in sorted(payload.items())}
    return {"value": {"type": type(payload).__name__}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    parser.add_argument("current")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare_schema(_load(args.reference), _load(args.current))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
