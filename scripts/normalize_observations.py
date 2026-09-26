#!/usr/bin/env python3
"""Normalize adapter records into the canonical point-in-time observation contract."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _iso(value, allow_null=True):
    if value is None and allow_null:
        return None
    if value is None:
        raise ValueError("timestamp is required")
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def canonicalize_observation(record, profile, snapshot, transformation_id="canonical_observation_v1"):
    required = ("instrument_id", "field", "value", "observation_time", "availability_time", "effective_time")
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError(f"observation missing required fields: {missing}")
    availability = _iso(record["availability_time"], allow_null=False)
    observation = _iso(record["observation_time"], allow_null=False)
    effective = _iso(record["effective_time"], allow_null=False)
    if availability < observation:
        raise ValueError("availability_time cannot precede observation_time")
    row = {
        "instrument_id": str(record["instrument_id"]),
        "source_id": profile["source_id"],
        "field": str(record["field"]),
        "value": record["value"],
        "unit": str(record.get("unit", "unknown")),
        "currency": record.get("currency"),
        "observation_time": observation,
        "release_time": _iso(record.get("release_time")),
        "availability_time": availability,
        "effective_time": effective,
        "vintage_time": _iso(record.get("vintage_time")),
        "adjustment": str(record.get("adjustment", "unadjusted")),
        "source_url": str(record.get("source_url") or profile.get("base_urls", ["https://invalid.local/"])[0]),
        "snapshot_hash": str(snapshot["snapshot_hash"]),
        "parser_version": str(record.get("parser_version") or profile.get("parser", "source_adapter_v1")),
        "transformation_id": transformation_id,
        "source_authority": profile.get("authority", "unknown"),
        "access_method": record.get("access_method") or profile.get("primary_method", "unknown"),
        "point_in_time_status": record.get("point_in_time_status") or ("pass" if profile.get("point_in_time") else "not_available"),
        "revision_status": record.get("revision_status") or ("vintage_aware" if profile.get("revision_aware") else "latest_only"),
    }
    row["transformation_hash"] = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()
    return row


def normalize(records, profile, snapshot, transformation_id="canonical_observation_v1"):
    return [canonicalize_observation(record, profile, snapshot, transformation_id) for record in records]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--transformation-id", default="canonical_observation_v1")
    args = parser.parse_args()
    records = json.loads(args.input.read_text(encoding="utf-8"))
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = records.get("observations", records.get("data", []))
    output = normalize(records, profile, snapshot, args.transformation_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(output), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
