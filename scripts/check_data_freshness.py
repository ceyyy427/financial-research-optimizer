#!/usr/bin/env python3
"""Evaluate online snapshot freshness for dynamic preflight."""
import argparse
import json
from pathlib import Path

try:
    from .monitoring.freshness import check_freshness
except ImportError:
    from monitoring.freshness import check_freshness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--max-age-minutes", type=int, default=1440)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = check_freshness(json.loads(args.manifest.read_text(encoding="utf-8")), max_age_minutes=args.max_age_minutes)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] != "blocked" else 2)


if __name__ == "__main__":
    main()
