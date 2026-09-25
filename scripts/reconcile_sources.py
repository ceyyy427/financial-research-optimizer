#!/usr/bin/env python3
"""Compare same-asset CSV observations from multiple sources."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from config_utils import load_config


REQUIRED = {"instrument_id", "observation_date", "close", "volume", "adjustment_code", "effective_timestamp"}
HARD_STATUSES = {"material_conflict", "timestamp_conflict", "adjustment_mismatch", "unresolved"}


def read_source(source_id, path):
    rows = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        for row in reader:
            key = (row["instrument_id"], row["observation_date"])
            rows[key] = {**row, "source_id": source_id}
    return rows


def within(a, b, abs_tol, rel_tol):
    try:
        x, y = float(a), float(b)
    except (TypeError, ValueError):
        return False, None
    delta = abs(x - y)
    return delta <= abs_tol + rel_tol * abs(y), delta


def reconcile(sources, config):
    policy = config.get("source_policy", {})
    price_abs = policy.get("price_abs_tolerance", 1e-8)
    price_rel = policy.get("price_rel_tolerance", 1e-4)
    volume_abs = policy.get("volume_abs_tolerance", 1.0)
    volume_rel = policy.get("volume_rel_tolerance", 0.005)
    priority = policy.get("priority", list(sources))
    data = {source_id: read_source(source_id, path) for source_id, path in sources.items()}
    keys = sorted(set().union(*(rows.keys() for rows in data.values())))
    records = []
    counts = Counter()
    for key in keys:
        observations = [rows[key] for rows in data.values() if key in rows]
        statuses = []
        fields = {}
        for field, abs_tol, rel_tol in (("close", price_abs, price_rel), ("volume", volume_abs, volume_rel)):
            values = {row["source_id"]: row[field] for row in observations}
            pairs = list(values.items())
            field_status = "match"
            delta = 0.0
            if len(pairs) < len(data):
                field_status = "missing_source"
            for (_, left), (_, right) in zip(pairs, pairs[1:]):
                ok, pair_delta = within(left, right, abs_tol, rel_tol)
                if pair_delta is not None:
                    delta = max(delta, pair_delta)
                if not ok:
                    field_status = "material_conflict"
            fields[field] = {"values": values, "status": field_status, "delta": delta, "abs_tolerance": abs_tol, "rel_tolerance": rel_tol}
            statuses.append(field_status)
        adjustment_values = {row["source_id"]: row["adjustment_code"] for row in observations}
        adjustment_status = "match" if len(set(adjustment_values.values())) <= 1 else "adjustment_mismatch"
        fields["adjustment_code"] = {"values": adjustment_values, "status": adjustment_status}
        statuses.append(adjustment_status)
        timestamps = {row["source_id"]: row["effective_timestamp"] for row in observations}
        timestamp_status = "match" if len(set(timestamps.values())) <= 1 else "timestamp_conflict"
        fields["effective_timestamp"] = {"values": timestamps, "status": timestamp_status}
        statuses.append(timestamp_status)
        status = "match"
        if "missing_source" in statuses:
            status = "missing_source"
        if "minor_difference" in statuses:
            status = "minor_difference"
        for candidate in ("adjustment_mismatch", "timestamp_conflict", "material_conflict"):
            if candidate in statuses:
                status = candidate
                break
        ranked = sorted(observations, key=lambda row: priority.index(row["source_id"]) if row["source_id"] in priority else len(priority))
        records.append({"instrument_id": key[0], "observation_date": key[1], "fields": fields, "source_priority": priority, "canonical_source": ranked[0]["source_id"] if ranked else None, "conflict_status": status})
        counts[status] += 1
    return {"records": records, "summary": {"total": len(records), "counts": dict(counts), "stop_dependency_analysis": any(record["conflict_status"] in HARD_STATUSES for record in records), "hard_statuses": sorted(HARD_STATUSES), "source_priority": priority}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--source", action="append", required=True, metavar="SOURCE_ID=CSV")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    sources = {}
    for item in args.source:
        if "=" not in item:
            raise SystemExit("--source must be SOURCE_ID=CSV")
        source_id, path = item.split("=", 1)
        sources[source_id] = path
    result = reconcile(sources, config)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
