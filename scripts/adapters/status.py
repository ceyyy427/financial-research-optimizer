#!/usr/bin/env python3
"""Report evidence-driven source/dataset maturity without overclaiming."""
import argparse
import json
import sys
from pathlib import Path

try:
    from ..source_router import load_registry
    from .evidence import evaluate_maturity, load_evidence
    from .factory import DATASETS, DATASET_CONTRACTS, IMPLEMENTED_ADAPTERS
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from source_router import load_registry
    from adapters.evidence import evaluate_maturity, load_evidence
    from adapters.factory import DATASETS, DATASET_CONTRACTS, IMPLEMENTED_ADAPTERS


def adapter_status(registry_path, evidence_path=None):
    profiles = load_registry(registry_path)
    evidence = load_evidence(evidence_path)
    rows = []
    for source_id, profile in sorted(profiles.items()):
        dataset_id = profile.get("dataset") or DATASETS.get(source_id, "default")
        maturity = evaluate_maturity(
            profile, source_id, dataset_id, evidence.get(source_id),
            factory_registered=source_id in DATASET_CONTRACTS,
            fetch_implemented=source_id in IMPLEMENTED_ADAPTERS,
        )
        row = {
            "source_id": source_id,
            "dataset_id": dataset_id,
            "access_method": profile.get("primary_method"),
            "implementation_status": profile.get("implementation_status", "planned"),
            "parser_status": profile.get("parser_status", "unavailable"),
            "factory_registered": source_id in DATASET_CONTRACTS,
            "fetch_implemented": source_id in IMPLEMENTED_ADAPTERS,
            "parser": profile.get("parser"),
            "source_health": maturity["evidence"]["health_status"],
            "provider_status": profile.get("provider_status", "unknown"),
            "last_success_at": maturity["evidence"]["last_live_success_at"],
            "last_failure_at": profile.get("last_failure_at"),
            "latency_ms": profile.get("latency_ms"),
            **{key: maturity[key] for key in (
                "maturity_level", "automatic_execution_ready", "live_certified",
                "degraded_execution_ready", "manual_review_only", "contract_only",
                "blocked", "authority_primary_allowed", "cross_check_only",
            )},
            "evidence": maturity["evidence"],
        }
        row["execution_ready"] = row["automatic_execution_ready"]
        row["degraded_ready"] = row["degraded_execution_ready"]
        row["automatic_primary_allowed"] = row["authority_primary_allowed"]
        row["manual_review_required"] = row["manual_review_only"]
        rows.append(row)
    counts = {
        "automatic_execution_count": sum(row["automatic_execution_ready"] for row in rows),
        "live_certified_count": sum(row["live_certified"] for row in rows),
        "degraded_execution_count": sum(row["degraded_execution_ready"] for row in rows),
        "manual_review_only_count": sum(row["manual_review_only"] for row in rows),
        "contract_only_count": sum(row["contract_only"] for row in rows),
        "blocked_count": sum(row["blocked"] for row in rows),
        "authority_primary_count": sum(row["authority_primary_allowed"] for row in rows),
        "cross_check_only_count": sum(row["cross_check_only"] for row in rows),
    }
    return {
        "registry": str(registry_path),
        "evidence": str(evidence_path or Path(__file__).resolve().parents[2] / "config" / "adapter_evidence.json"),
        "profiles": rows,
        **counts,
        "execution_ready_count": counts["automatic_execution_count"],
        "degraded_ready_count": counts["degraded_execution_count"],
        "automatic_primary_rule": "factory + request contract + fixture + integration + quality evidence + unexpired certification",
        "live_certification_rule": "automatic execution + live smoke + healthy + fresh + PIT + snapshot hash + last_live_success_at",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    parser.add_argument("--evidence", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(adapter_status(args.registry, args.evidence), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
