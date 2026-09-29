#!/usr/bin/env python3
"""Record one reviewed adapter certification cycle without implicit promotion."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from .certify_adapter import evaluate
except ImportError:
    from certify_adapter import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=Path("config/adapter_evidence.json"))
    parser.add_argument("--max-consecutive-failures", type=int, default=3)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    smoke = json.loads(args.smoke.read_text(encoding="utf-8"))
    decision = evaluate(smoke)
    payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    source_id = smoke.get("source_id")
    dataset_id = smoke.get("dataset") or smoke.get("dataset_id")
    access_method = (smoke.get("source_capability") or {}).get("access_method") or "api"
    candidates = [item for item in payload.get("datasets", []) if item.get("source_id") == source_id and item.get("dataset_id") == dataset_id and item.get("access_method") == access_method]
    if len(candidates) != 1:
        decision.update({"eligible": False, "blockers": [f"evidence record is not unique for {source_id}:{dataset_id}:{access_method}"], "circuit_status": "unknown"})
    elif args.write:
        item = candidates[0]
        now = datetime.now(timezone.utc).isoformat()
        if decision["eligible"]:
            item.update({"live_smoke_status": "passed", "health_status": "healthy", "freshness_status": "fresh", "snapshot_hash": smoke.get("snapshot_hash"), "last_live_success_at": smoke.get("checked_at"), "consecutive_failures": 0, "circuit_status": "closed"})
        else:
            failures = int(item.get("consecutive_failures", 0)) + 1
            item.update({"last_failure_at": now, "consecutive_failures": failures, "circuit_status": "open" if failures >= args.max_consecutive_failures else "closed"})
        args.evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        decision.update({"written": str(args.evidence), "circuit_status": item.get("circuit_status"), "consecutive_failures": item.get("consecutive_failures", 0)})
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    raise SystemExit(0 if decision["eligible"] else 2)


if __name__ == "__main__":
    main()
