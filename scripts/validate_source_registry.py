#!/usr/bin/env python3
"""Validate source_registry.yaml profiles against source_profile.schema.json."""
import argparse
import json
from pathlib import Path

try:
    from .source_router import load_registry
    from .parsers import get_parser
    from .online.provider_registry import ADAPTER_IDS, PROVIDER_IDS
    from .adapters.factory import DATASETS, is_fetch_implemented
except ImportError:
    from source_router import load_registry
    from parsers import get_parser
    from online.provider_registry import ADAPTER_IDS, PROVIDER_IDS
    from adapters.factory import DATASETS, is_fetch_implemented


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
        if source_id not in DATASETS:
            errors.append(f"{source_id}: no dataset capability is registered in adapters.factory")
        if profile.get("provider_id", source_id) != source_id:
            errors.append(f"{source_id}: provider_id must equal source_id")
        if profile.get("adapter_id", source_id) != source_id:
            errors.append(f"{source_id}: adapter_id must equal source_id")
        if profile.get("parser_id", profile.get("parser")) != profile.get("parser"):
            errors.append(f"{source_id}: parser_id must equal parser")
        if profile.get("normalizer_id", profile.get("normalizer")) != profile.get("normalizer"):
            errors.append(f"{source_id}: normalizer_id must equal normalizer")
        if profile.get("implementation_status") == "production" and profile.get("parser_status") == "tested" and source_id not in (PROVIDER_IDS | ADAPTER_IDS):
            errors.append(f"{source_id}: production+tested source has no registered online provider or adapter")
        if profile.get("implementation_status") == "production" and profile.get("parser_status") == "tested" and not is_fetch_implemented(source_id, DATASETS.get(source_id), profile.get("primary_method")):
            errors.append(f"{source_id}: production+tested source has no implemented SourceRequest fetch")
        errors.extend(f"{source_id}: {error.message}" for error in validator.iter_errors(profile))
        if profile.get("parser_status") in {"available", "tested"} and get_parser(profile.get("parser")) is None:
            errors.append(f"{source_id}: parser_status={profile.get('parser_status')} but parser is not registered: {profile.get('parser')}")
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
