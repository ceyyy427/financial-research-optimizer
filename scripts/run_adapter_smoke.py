#!/usr/bin/env python3
"""Run an auditable adapter smoke or replay check.

Live mode calls the formal adapter entry point. Replay mode parses a saved raw
fixture and creates a snapshot, so CI can verify the full transformation path
without network access. Smoke output is evidence, not an automatic promotion
to live certification.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .adapters.factory import build_adapter, build_request, fetch_with_adapter
    from .adapters.evidence import evaluate_maturity, load_evidence
    from .monitoring.freshness import check_freshness
    from .normalize_observations import normalize
    from .parsers import parse
    from .source_router import SourceRouter
    from .source_snapshot import create_snapshot
except ImportError:
    from adapters.factory import build_adapter, build_request, fetch_with_adapter
    from adapters.evidence import evaluate_maturity, load_evidence
    from monitoring.freshness import check_freshness
    from normalize_observations import normalize
    from parsers import parse
    from source_router import SourceRouter
    from source_snapshot import create_snapshot


def _now():
    return datetime.now(timezone.utc).isoformat()


def replay(source_id, dataset_id, fixture, instrument, registry, output_dir, params):
    profile = SourceRouter.from_file(registry).profiles[source_id]
    raw_path = Path(fixture)
    payload = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.suffix.lower() == ".json" else raw_path.read_text(encoding="utf-8")
    snapshot = create_snapshot(source_id, raw_path, output_dir / "snapshots", profile.get("base_urls", ["https://invalid.local/"])[0], request_params=params, parser_version=profile.get("parser", "adapter_v1"), access_method=profile.get("primary_method", "fixture"), source_authority=profile.get("authority", "unknown"), point_in_time_status="verified" if profile.get("point_in_time") else "not_available", revision_status="revision_aware" if profile.get("revision_aware") else "latest_only")
    rows = parse(profile["parser"], payload, instrument_id=instrument, source_url=snapshot["request_url"])
    canonical = normalize(rows, profile, snapshot)
    return {
        "source_id": source_id, "dataset": dataset_id, "status": "passed" if canonical else "blocked", "live": False,
        "rows": len(canonical), "latency_ms": 0, "snapshot_hash": snapshot.get("snapshot_hash"),
        "quality_status": "pass" if canonical else "blocked", "schema_drift": False,
        "checked_at": _now(), "snapshot": snapshot, "normalized_rows": canonical,
        "source_capability": evaluate_maturity(profile, source_id, dataset_id, load_evidence().get(source_id), True, source_id in {"stats_gov_cn", "10jqka", "sec_edgar", "fred", "alfred", "ecb_sdmx", "bis_sdmx"}),
    }


def live(source_id, dataset_id, url, instrument, registry, output_dir, params, authorization_status):
    started = time.perf_counter()
    from execute_online_refresh import execute_data_refresh
    request_params = {**params, "dataset": dataset_id, "instrument": instrument}
    result = execute_data_refresh(source_id, url, output_dir, request_params, registry, authorization_status=authorization_status, allow_degraded=False)
    elapsed = round((time.perf_counter() - started) * 1000, 3)
    result["live"] = True
    result["checked_at"] = _now()
    result["latency_ms"] = elapsed
    result["schema_drift"] = False
    result["rows"] = result.get("normalized_rows", 0)
    result["snapshot_hash"] = (result.get("snapshot") or {}).get("snapshot_hash")
    result["quality_status"] = result.get("quality_status", result.get("status"))
    result["smoke_status"] = "passed" if result.get("status") == "passed" else "blocked"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--mode", choices=("live", "replay"), default="replay")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--url")
    parser.add_argument("--instrument", default=None)
    parser.add_argument("--params", type=json.loads, default={})
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/smoke"))
    parser.add_argument("--authorization-status", choices=("unknown", "authorized", "expired", "not_required"), default="unknown")
    args = parser.parse_args()
    # This is the shared dataset contract gate for both modes.
    request = build_request(args.source_id, {**args.params, "dataset": args.dataset, "instrument": args.instrument}, requested_url=args.url)
    if args.mode == "replay":
        if not args.fixture:
            raise SystemExit("replay mode requires --fixture")
        result = replay(args.source_id, request.dataset, args.fixture, request.instrument, args.registry, args.output_dir, dict(request.params))
    else:
        if not args.url:
            raise SystemExit("live mode requires --url")
        result = live(args.source_id, request.dataset, args.url, request.instrument, args.registry, args.output_dir, dict(request.params), args.authorization_status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result.get("status") in {"passed", "pass"} else 2)


if __name__ == "__main__":
    main()
