#!/usr/bin/env python3
"""Execute only the data-refresh stage through the explicit adapter factory.

Feature refresh, forecast refresh and retraining are separate stages. Unknown
sources, undeclared datasets, missing authorization and partial adapters are
blocked; no generic HTTP provider is used as a silent fallback.
"""

import argparse
import json
from pathlib import Path

try:
    from .adapters.base import AdapterError
    from .adapters.evidence import evaluate_maturity, load_evidence, get_evidence
    from .adapters.factory import AdapterNotReady, build_adapter, build_request, fetch_with_adapter, is_fetch_implemented
    from .monitoring.freshness import check_freshness
    from .normalize_observations import normalize
    from .source_router import SourceRouter, SourceRoutingError
except ImportError:
    from adapters.base import AdapterError
    from adapters.evidence import evaluate_maturity, load_evidence, get_evidence
    from adapters.factory import AdapterNotReady, build_adapter, build_request, fetch_with_adapter, is_fetch_implemented
    from monitoring.freshness import check_freshness
    from normalize_observations import normalize
    from source_router import SourceRouter, SourceRoutingError


def execute_data_refresh(
    source_id,
    url=None,
    output_dir="artifacts/online",
    params=None,
    registry_path="config/source_registry.yaml",
    transport=None,
    retrain=False,
    allow_degraded=False,
    user_agent=None,
    navigation=None,
    authorization_status="unknown",
):
    if retrain:
        return {"status": "blocked", "stage": "model_retrain", "failure_class": "policy", "message": "retraining is a separate explicit stage and cannot be enabled by data refresh"}
    if not source_id:
        return {"status": "blocked", "stage": "data_refresh", "failure_class": "contract", "message": "source_id is required"}
    try:
        router = SourceRouter.from_file(registry_path)
        profile = router.profiles.get(source_id)
        if profile is None:
            return {"status": "blocked", "stage": "data_refresh", "failure_class": "source", "message": f"unknown source_id: {source_id}"}
        request = build_request(source_id, params or {}, requested_url=url)
        maturity = evaluate_maturity(
            profile, source_id, request.dataset, get_evidence(source_id, request.dataset, profile.get("primary_method")),
            factory_registered=True,
            fetch_implemented=is_fetch_implemented(source_id, request.dataset, profile.get("primary_method")),
        )
        if not maturity["automatic_execution_ready"] and not (allow_degraded and maturity["degraded_execution_ready"]):
            return {
                "status": "blocked",
                "stage": "data_refresh",
                "failure_class": "source",
                "message": f"adapter is not executable: {source_id}; maturity={maturity['maturity_level']} manual_review_only={maturity['manual_review_only']}",
                "source_capability": maturity,
            }
        root = Path(output_dir)
        adapter = build_adapter(
            source_id,
            profile,
            output_dir=root,
            transport=transport,
            navigation=navigation,
            user_agent=user_agent,
            authorization_status=authorization_status,
        )
        result = fetch_with_adapter(adapter, request)
        freshness = check_freshness(
            result.raw_snapshot,
            max_age_minutes=int((profile.get("slo") or {}).get("max_age_minutes", 1440)),
        )
        if freshness["status"] in {"blocked", "stale", "fallback", "degraded"} and not allow_degraded:
            return {"status": "blocked", "stage": "freshness", "failure_class": "freshness", "source_id": source_id, "freshness": freshness, "source_capability": maturity}
        if result.quality_status == "blocked":
            return {"status": "blocked", "stage": "quality", "failure_class": "quality", "source_id": source_id, "result": result.as_dict()}
        if not result.observations:
            return {"status": "blocked", "stage": "normalize", "failure_class": "empty_data", "source_id": source_id, "result": result.as_dict()}
        if not result.raw_snapshot or not result.raw_snapshot.get("snapshot_hash"):
            return {"status": "blocked", "stage": "snapshot", "failure_class": "provenance", "source_id": source_id, "message": "adapter returned observations without a snapshot hash"}
        canonical = normalize(result.observations, profile, result.raw_snapshot)
        normalized_dir = root / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)
        normalized_file = normalized_dir / f"{source_id}-{request.dataset}.json"
        normalized_file.write_text(json.dumps(canonical, ensure_ascii=False, indent=2), encoding="utf-8")
        snapshot = result.raw_snapshot
        health_dir = root / "health"
        health_dir.mkdir(parents=True, exist_ok=True)
        health_file = health_dir / f"{source_id}-{request.dataset}.json"
        health_payload = {
            "source_id": source_id,
            "source_health": "healthy" if freshness["status"] == "ready" else freshness["status"],
            "provider_status": "passed" if result.quality_status == "pass" else result.quality_status,
            "last_success_at": snapshot.get("retrieved_at"),
            "last_failure_at": None,
            "latency_ms": snapshot.get("latency_ms"),
            "schema_version": profile.get("parser"),
            "license_expiry": None,
            "health_multiplier": 1.0 if freshness["status"] == "ready" else 0.5,
            "evaluated_at": snapshot.get("retrieved_at"),
        }
        health_file.write_text(json.dumps(health_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        result.provenance["source_capability"] = maturity
        result.provenance["freshness"] = freshness
        result.source_capability = maturity
        result.freshness = freshness
        return {
            "status": "passed",
            "stage": "data_refresh",
            "execution_mode": "executed",
            "source_id": source_id,
            "dataset": request.dataset,
            "quality_status": result.quality_status,
            "limitations": result.limitations,
            "source_capability": maturity,
            "freshness": freshness,
            "provenance": result.provenance,
            "snapshot": snapshot,
            "normalized_file": str(normalized_file),
            "normalized_rows": len(canonical),
            "health_file": str(health_file),
            "from_cache": bool(snapshot.get("from_cache", False)),
            "stale": bool(snapshot.get("stale", False)),
            "network_requests": 0 if snapshot.get("from_cache") else 1,
            "message": "data snapshot captured and canonicalized; feature/model stages remain separate",
        }
    except (AdapterError, AdapterNotReady, SourceRoutingError, OSError, ValueError, KeyError) as exc:
        return {"status": "blocked", "stage": "data_refresh", "failure_class": "acquisition", "message": str(exc), "source_id": source_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--url", help="optional endpoint; the adapter must validate it against the source allowlist")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    parser.add_argument("--params", type=json.loads, default={})
    parser.add_argument("--authorization-status", choices=["unknown", "authorized", "expired", "not_required"], default="unknown")
    parser.add_argument("--retrain", action="store_true")
    parser.add_argument("--allow-degraded", action="store_true", help="allow partial provider with manual review")
    parser.add_argument("--user-agent", default=None, help="contact-bearing User-Agent for SEC")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = execute_data_refresh(
        args.source_id,
        args.url,
        args.output_dir,
        args.params,
        args.registry,
        retrain=args.retrain,
        allow_degraded=args.allow_degraded,
        user_agent=args.user_agent,
        authorization_status=args.authorization_status,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["status"] == "passed" else 2)


if __name__ == "__main__":
    main()
