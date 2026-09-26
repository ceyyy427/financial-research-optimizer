#!/usr/bin/env python3
"""Validate source_registry.yaml profiles against source_profile.schema.json."""
import argparse
import json
from pathlib import Path

try:
    from .source_router import load_registry
except ImportError:
    from source_router import load_registry


def validate_registry(registry_path, schema_path):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise SystemExit("validate_source_registry.py requires jsonschema; install with python3 -m pip install -r requirements-dev.txt") from exc
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    profiles = load_registry(registry_path)
    errors = []
    validator = Draft202012Validator(schema)
    for source_id, profile in profiles.items():
        errors.extend(f"{source_id}: {error.message}" for error in validator.iter_errors(profile))
    if errors:
        raise ValueError("source registry validation failed:\n- " + "\n- ".join(errors))
    return {"valid": True, "profile_count": len(profiles), "source_ids": sorted(profiles)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    parser.add_argument("--schema", type=Path, default=Path("schemas/source_profile.schema.json"))
    args = parser.parse_args()
    print(json.dumps(validate_registry(args.registry, args.schema), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
