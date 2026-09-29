#!/usr/bin/env python3
"""Render the capability-aware source maturity grid for operators and MCP."""
import argparse
import json
from pathlib import Path

try:
    from .adapters.status import adapter_status
except ImportError:
    from adapters.status import adapter_status


def build_report(registry, evidence=None):
    report = adapter_status(registry, evidence)
    return {
        "report_version": "1.3.0",
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "counts": {key: value for key, value in report.items() if key.endswith("_count")},
        "profiles": report["profiles"],
        "routing_states": sorted({"L4" if row["live_certified"] else "L3" if row["automatic_execution_ready"] else "degraded" if row["degraded_execution_ready"] else "blocked" if row["blocked"] else "manual_review" for row in report["profiles"]}),
        "next_actions": ["continue" if report["live_certified_count"] else "run live smoke", "use explicit verified snapshot for degraded sources", "stop dependent analysis on blocked or unresolved PIT sources"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    parser.add_argument("--evidence", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = build_report(args.registry, args.evidence)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
