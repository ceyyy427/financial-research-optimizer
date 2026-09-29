#!/usr/bin/env python3
"""Explicitly certify one adapter capability from a live smoke artifact.

The command is intentionally opt-in: a replay or a missing live evidence
field can never update the registry.  Use --write only after reviewing the
printed blockers and the underlying snapshot.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def evaluate(smoke):
    blockers = []
    if not smoke.get("live"):
        blockers.append("live smoke is required")
    if smoke.get("status") != "passed" or smoke.get("smoke_status", "passed") != "passed":
        blockers.append("smoke status is not passed")
    if not smoke.get("snapshot_hash"):
        blockers.append("snapshot_hash is required")
    if not smoke.get("rows"):
        blockers.append("live smoke must return at least one row")
    drift = smoke.get("schema_drift", {})
    if drift.get("schema_drift_detected"):
        blockers.append("schema drift detected")
    freshness = smoke.get("freshness", {})
    if freshness and freshness.get("status") not in {"ready", "fresh", "healthy"}:
        blockers.append("freshness is not ready")
    capability = smoke.get("source_capability", {})
    if isinstance(capability, dict) and not capability.get("automatic_execution_ready", False):
        blockers.append("source capability is not automatically executable")
    if smoke.get("health_status") not in {"healthy", "pass", "passed"}:
        blockers.append("health is not healthy")
    if smoke.get("point_in_time_status") not in {"verified", "vintage_aware"}:
        blockers.append("point-in-time status is not verified")
    if smoke.get("revision_status") in {None, "", "not_run", "not_available"}:
        blockers.append("revision status is not evidenced")
    return {"eligible": not blockers, "blockers": blockers, "checked_at": datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=Path("config/adapter_evidence.json"))
    parser.add_argument("--write", action="store_true", help="write only when all certification gates pass")
    parser.add_argument("--expires-at", required=True)
    args = parser.parse_args()
    smoke = json.loads(args.smoke.read_text(encoding="utf-8"))
    decision = evaluate(smoke)
    if decision["eligible"] and args.write:
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
        source_id = smoke.get("source_id")
        dataset_id = smoke.get("dataset") or smoke.get("dataset_id")
        candidates = [item for item in payload.get("datasets", []) if item.get("source_id") == source_id and item.get("dataset_id") == dataset_id]
        if len(candidates) != 1:
            decision["eligible"] = False
            decision["blockers"] = [f"evidence record is not unique for {source_id}:{dataset_id}"]
        else:
            item = candidates[0]
            item.update({"live_smoke_status": "passed", "health_status": "healthy", "freshness_status": "fresh", "snapshot_hash": smoke["snapshot_hash"], "last_live_success_at": smoke.get("checked_at"), "certification_expires_at": args.expires_at})
            args.evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            decision["written"] = str(args.evidence)
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    raise SystemExit(0 if decision["eligible"] else 2)


if __name__ == "__main__":
    main()
