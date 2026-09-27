#!/usr/bin/env python3
"""Report adapter maturity without claiming that planned sources execute."""
import argparse
import json
import sys
from pathlib import Path

try:
    from ..source_router import load_registry
except ImportError:
    # ``python3 scripts/adapters/status.py`` does not put ``scripts/`` on
    # sys.path; installed entry points use the package-relative import above.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from source_router import load_registry


def adapter_status(registry_path):
    profiles = load_registry(registry_path)
    rows = []
    for source_id, profile in sorted(profiles.items()):
        implementation = profile.get("implementation_status", "planned")
        parser = profile.get("parser_status", "unavailable")
        rows.append({
            "source_id": source_id,
            "implementation_status": implementation,
            "parser_status": parser,
            "execution_ready": implementation in {"partial", "production"} and parser in {"partial", "available", "tested"},
            "parser": profile.get("parser"),
        })
    return {"registry": str(registry_path), "profiles": rows, "execution_ready_count": sum(row["execution_ready"] for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    args = parser.parse_args()
    print(json.dumps(adapter_status(args.registry), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
