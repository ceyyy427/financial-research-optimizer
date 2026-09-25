#!/usr/bin/env python3
"""Shared experiment-manifest loader and lightweight contract validation."""
import hashlib
import json
from pathlib import Path


REQUIRED = ("experiment_id", "config_fingerprint", "data_snapshot_hash", "code_version", "environment", "random_seeds", "model_parameters", "feature_version", "train_window", "evaluation_window", "outputs", "reproducibility_status")


def validate_manifest(data):
    errors = []
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]
    errors.extend(f"missing manifest field: {key}" for key in REQUIRED if key not in data)
    if not isinstance(data.get("random_seeds"), list) or not data.get("random_seeds"):
        errors.append("random_seeds must be a non-empty list")
    if data.get("reproducibility_status") not in {"complete", "partial", "failed"}:
        errors.append("reproducibility_status must be complete, partial, or failed")
    for section, fields in (("data_snapshot_hash", ("algorithm", "value")), ("code_version", ("commit", "repository")), ("train_window", ("start", "end")), ("evaluation_window", ("start", "end", "method"))):
        value = data.get(section, {})
        if not isinstance(value, dict):
            errors.append(f"{section} must be an object")
        else:
            errors.extend(f"{section}.{field} is missing" for field in fields if not value.get(field))
    outputs = data.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("outputs must be a non-empty list")
    else:
        for index, output in enumerate(outputs):
            if not isinstance(output, dict) or not output.get("path") or not output.get("sha256"):
                errors.append(f"outputs[{index}] must contain path and sha256")
    return errors


def load_manifest(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_manifest(data)
    if errors:
        raise ValueError("invalid experiment manifest:\n- " + "\n- ".join(errors))
    data["_manifest_path"] = str(path)
    data["_manifest_fingerprint"] = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return data
