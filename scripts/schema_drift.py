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
