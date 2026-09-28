#!/usr/bin/env python3
"""Report adapter maturity without claiming that planned sources execute."""
import argparse
import json
import sys
from pathlib import Path

try:
    from ..source_router import load_registry
    from .factory import DATASETS, _CONTRACT_ONLY
except ImportError:
    # ``python3 scripts/adapters/status.py`` does not put ``scripts/`` on
    # sys.path; installed entry points use the package-relative import above.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from source_router import load_registry
    from adapters.factory import DATASETS, _CONTRACT_ONLY


IMPLEMENTED_ADAPTERS = frozenset({"stats_gov_cn", "10jqka", "sec_edgar", "fred", "alfred", "ecb_sdmx", "bis_sdmx"})


def adapter_status(registry_path):
    profiles = load_registry(registry_path)
    rows = []
    for source_id, profile in sorted(profiles.items()):
        implementation = profile.get("implementation_status", "planned")
        parser = profile.get("parser_status", "unavailable")
        execution_ready = implementation == "production" and parser == "tested"
        degraded_ready = implementation == "partial" and parser in {"partial", "available", "tested"}
        dataset = profile.get("dataset") or DATASETS.get(source_id, "default")
        factory_registered = source_id in DATASETS
        fetch_implemented = source_id in IMPLEMENTED_ADAPTERS
        rows.append({
            "source_id": source_id,
            "dataset": dataset,
            "access_method": profile.get("primary_method"),
            "implementation_status": implementation,
            "parser_status": parser,
            "factory_registered": factory_registered,
            "fetch_implemented": fetch_implemented,
            "execution_ready": execution_ready and factory_registered and fetch_implemented,
            "degraded_ready": degraded_ready,
            "automatic_primary_allowed": execution_ready and factory_registered and fetch_implemented,
            "manual_review_required": degraded_ready,
            "parser": profile.get("parser"),
            "source_health": profile.get("source_health", "unknown"),
            "provider_status": profile.get("provider_status", "unknown"),
            "last_success_at": profile.get("last_success_at"),
            "last_failure_at": profile.get("last_failure_at"),
            "latency_ms": profile.get("latency_ms"),
        })
    return {
        "registry": str(registry_path),
        "profiles": rows,
        "execution_ready_count": sum(row["execution_ready"] for row in rows),
        "degraded_ready_count": sum(row["degraded_ready"] for row in rows),
        "automatic_primary_rule": "implementation_status=production AND parser_status=tested AND factory_registered AND fetch_implemented",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    args = parser.parse_args()
    print(json.dumps(adapter_status(args.registry), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
