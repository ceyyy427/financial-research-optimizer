#!/usr/bin/env python3
"""Execute only the data-refresh stage and persist an auditable snapshot.

Feature refresh, forecast refresh and retraining are separate stages.  This
command never retrains implicitly; ``--retrain`` is rejected unless an
explicitly validated retraining handler is supplied by a caller.
"""
import argparse
import json
from pathlib import Path

try:
    from .online.base_provider import BaseProvider, ProviderError
    from .online.http_cache import HttpCache
    from .online.snapshot_store import SnapshotStore
    from .normalize_observations import normalize
    from .parsers import parse
    from .source_router import SourceRouter, SourceRoutingError
except ImportError:
    from online.base_provider import BaseProvider, ProviderError
    from online.http_cache import HttpCache
    from online.snapshot_store import SnapshotStore
    from normalize_observations import normalize
    from parsers import parse
    from source_router import SourceRouter, SourceRoutingError


def execute_data_refresh(source_id, url, output_dir, params=None, registry_path="config/source_registry.yaml", transport=None, retrain=False):
    if retrain:
        return {"status": "blocked", "stage": "model_retrain", "failure_class": "policy", "message": "retraining is a separate explicit stage and cannot be enabled by data refresh"}
    if not source_id or not url:
        return {"status": "blocked", "stage": "data_refresh", "failure_class": "contract", "message": "source_id and url are required"}
    try:
        router = SourceRouter.from_file(registry_path)
        plan = router.resolve("online data refresh", required_capabilities=["api"], authorization_status="unknown", require_executable=True)
        profile = router.profiles.get(source_id)
        if profile is None:
            return {"status": "blocked", "stage": "data_refresh", "failure_class": "source", "message": f"unknown source_id: {source_id}"}
        if profile.get("implementation_status") == "planned" or profile.get("parser_status") == "unavailable":
            return {"status": "blocked", "stage": "data_refresh", "failure_class": "source", "message": f"adapter is not executable: {source_id}"}
        root = Path(output_dir)
        provider = BaseProvider(cache=HttpCache(root / "cache", transport=transport), snapshot_store=SnapshotStore(root / "snapshots"))
        provider.provider_name = source_id
        provider.provider_version = f"{source_id}-generic-v1"
        provider.license_name = profile.get("name", "source terms")
        provider.revision_policy = "vintage_aware" if profile.get("revision_aware") else "latest_only"
        response = provider.request(url, params=params or {}, ttl_seconds=3600, snapshot=True)
        try:
            payload = response.json()
        except (UnicodeDecodeError, ValueError):
            payload = response.body.decode("utf-8", errors="replace")
        parser_name = profile.get("parser")
        try:
            records = parse(parser_name, payload, instrument_id=(params or {}).get("series_id"), source_url=url)
            canonical = normalize(records, profile, response.snapshot or {})
        except Exception as exc:
            return {"status": "blocked", "stage": "normalize", "failure_class": "parser", "message": f"parser/canonicalization failed: {exc}", "source_id": source_id, "snapshot": response.snapshot}
        if not canonical:
            return {"status": "blocked", "stage": "normalize", "failure_class": "parser", "message": f"parser {parser_name} returned no canonical observations", "source_id": source_id, "snapshot": response.snapshot}
        normalized_dir = root / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)
        normalized_file = normalized_dir / f"{source_id}.json"
        normalized_file.write_text(json.dumps(canonical, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "status": "passed", "stage": "data_refresh", "execution_mode": "executed",
            "source_id": source_id, "snapshot": response.snapshot, "normalized_file": str(normalized_file), "normalized_rows": len(canonical), "from_cache": response.from_cache,
            "stale": response.stale, "network_requests": 0 if response.from_cache else 1,
            "message": "data snapshot captured; downstream stages remain separate",
        }
    except (ProviderError, SourceRoutingError, OSError, ValueError) as exc:
        return {"status": "blocked", "stage": "data_refresh", "failure_class": "acquisition", "message": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    parser.add_argument("--params", type=json.loads, default={})
    parser.add_argument("--retrain", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = execute_data_refresh(args.source_id, args.url, args.output_dir, args.params, args.registry, retrain=args.retrain)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["status"] == "passed" else 2)


if __name__ == "__main__":
    main()
