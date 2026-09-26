#!/usr/bin/env python3
"""Validate local JSON Schemas and selected example payloads without network access."""
import argparse
import json
from pathlib import Path


SCHEMA_FILES = [
    "research_config.schema.json", "experiment_manifest.schema.json", "feature_label_contract.schema.json",
    "backtest_overfitting.schema.json", "model_selection.schema.json", "portfolio_output.schema.json", "feature_label_audit.schema.json", "source_reconciliation.schema.json",
    "preflight.schema.json", "analysis.schema.json",
]


def validate_local_schemas(root):
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as exc:
        raise SystemExit("validate_schemas.py requires jsonschema; install with python3 -m pip install -r requirements-dev.txt") from exc
    schemas = {name: json.loads((root / name).read_text(encoding="utf-8")) for name in SCHEMA_FILES}
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
    registry = Registry()
    for name, schema in schemas.items():
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(name, resource)
        if schema.get("$id"):
            registry = registry.with_resource(schema["$id"], resource)
    examples = [
        ("research_config.schema.json", root / "examples" / "research_config.json"),
        ("experiment_manifest.schema.json", root / "examples" / "experiment_manifest.json"),
        ("feature_label_contract.schema.json", root / "examples" / "research_config.json"),
        ("backtest_overfitting.schema.json", root / "examples" / "demo_analysis.json"),
        ("model_selection.schema.json", root / "examples" / "demo_analysis.json"),
        ("portfolio_output.schema.json", root / "examples" / "demo_analysis.json"),
        ("feature_label_audit.schema.json", root / "examples" / "demo_analysis.json"),
        ("source_reconciliation.schema.json", root / "examples" / "demo_analysis.json"),
        ("analysis.schema.json", root / "examples" / "demo_analysis.json"),
    ]
    selectors = {"feature_label_contract.schema.json": "feature_label_contract", "backtest_overfitting.schema.json": "backtest_overfitting", "model_selection.schema.json": "selection_protocol", "portfolio_output.schema.json": "portfolio_robustness", "feature_label_audit.schema.json": "feature_label_audit", "source_reconciliation.schema.json": "source_reconciliation"}
    for schema_name, data_path in examples:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        if schema_name in selectors:
            data = data[selectors[schema_name]]
        errors = list(Draft202012Validator(schemas[schema_name], registry=registry).iter_errors(data))
        if errors:
            raise ValueError(f"{schema_name}: " + "; ".join(error.message for error in errors))
    return {"valid": True, "schemas": SCHEMA_FILES, "examples_validated": len(examples)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(validate_local_schemas(args.root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
