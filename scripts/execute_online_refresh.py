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
    from .online.base_provider import ProviderError
    from .online.http_cache import HttpCache
    from .online.provider_registry import build_provider
    from .online.snapshot_store import SnapshotStore
    from .normalize_observations import normalize
    from .parsers import parse
    from .source_router import SourceRouter, SourceRoutingError
except ImportError:
    from online.base_provider import ProviderError
    from online.http_cache import HttpCache
    from online.provider_registry import build_provider
    from online.snapshot_store import SnapshotStore
    from normalize_observations import normalize
    from parsers import parse
    from source_router import SourceRouter, SourceRoutingError


def execute_data_refresh(source_id, url, output_dir, params=None, registry_path="config/source_registry.yaml", transport=None, retrain=False, allow_degraded=False, user_agent=None):
    if retrain:
        return {"status": "blocked", "stage": "model_retrain", "failure_class": "policy", "message": "retraining is a separate explicit stage and cannot be enabled by data refresh"}
    if not source_id or not url:
        return {"status": "blocked", "stage": "data_refresh", "failure_class": "contract", "message": "source_id and url are required"}
    try:
        router = SourceRouter.from_file(registry_path)
        profile = router.profiles.get(source_id)
        if profile is None:
            return {"status": "blocked", "stage": "data_refresh", "failure_class": "source", "message": f"unknown source_id: {source_id}"}
        production_ready = profile.get("implementation_status") == "production" and profile.get("parser_status") == "tested"
        degraded_ready = profile.get("implementation_status") == "partial" and profile.get("parser_status") in {"partial", "available", "tested"}
        if not production_ready and not (allow_degraded and degraded_ready):
            return {"status": "blocked", "stage": "data_refresh", "failure_class": "source", "message": f"provider is not production-ready: {source_id}; use --allow-degraded for manual-review execution"}
        root = Path(output_dir)
        cache = HttpCache(root / "cache", transport=transport)
        provider = build_provider(source_id, cache, SnapshotStore(root / "snapshots"), user_agent=user_agent)
        request_params = params or {}
        if source_id in {"fred", "alfred"}:
            payload_result = provider.fetch_series(
                request_params.get("series_id") or request_params.get("instrument_id"),
                observation_start=request_params.get("observation_start"),
                observation_end=request_params.get("observation_end"),
                realtime_start=request_params.get("realtime_start"),
                realtime_end=request_params.get("realtime_end"),
            )
        elif source_id == "sec_edgar":
            cik = request_params.get("cik") or request_params.get("instrument_id")
            payload_result = provider.company_facts(cik) if request_params.get("endpoint", "companyfacts") == "companyfacts" else provider.submissions(cik)
        elif source_id in {"ecb_sdmx", "bis_sdmx"}:
            payload_result = provider.fetch_data(request_params["flow_ref"], request_params.get("key", ""), request_params.get("start_period"), request_params.get("end_period"))
        elif source_id == "stats_gov_cn":
            payload_result = provider.fetch(url, request_params)
        else:
            raise ProviderError(f"no source-specific provider registered for {source_id}")
        response = payload_result["response"]
        try:
            payload = payload_result.get("data")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except ValueError:
                    pass
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
    parser.add_argument("--allow-degraded", action="store_true", help="allow partial provider with manual review")
    parser.add_argument("--user-agent", default=None, help="required contact-bearing User-Agent for SEC")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = execute_data_refresh(args.source_id, args.url, args.output_dir, args.params, args.registry, retrain=args.retrain, allow_degraded=args.allow_degraded, user_agent=args.user_agent)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["status"] == "passed" else 2)


if __name__ == "__main__":
    main()
