"""Convert normalized records into the canonical point-in-time row contract."""
from datetime import datetime, timezone
import hashlib
import json


def _iso(value):
    if value is None:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def canonicalize_record(record, source_id, snapshot_hash, transformation_id="canonicalize_v1"):
    required = ("instrument_id", "observation_time", "field", "value")
    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError(f"canonical record missing {missing}")
    row = {
        "instrument_id": str(record["instrument_id"]),
        "observation_time": _iso(record["observation_time"]),
        "availability_time": _iso(record.get("availability_time") or record["observation_time"]),
        "effective_time": _iso(record.get("effective_time") or record["observation_time"]),
        "field": str(record["field"]),
        "value": record["value"],
        "unit": record.get("unit", "unknown"),
        "currency": record.get("currency"),
        "adjustment": record.get("adjustment", "unadjusted"),
        "source_id": source_id,
        "snapshot_hash": snapshot_hash,
        "transformation_id": transformation_id,
    }
    if _iso(row["availability_time"]) < _iso(row["observation_time"]):
        raise ValueError("availability_time cannot precede observation_time without an explicit release model")
    row["transformation_hash"] = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
    return row
