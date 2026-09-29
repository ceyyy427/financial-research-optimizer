#!/usr/bin/env python3
"""Run the bounded, offline research-grade forecasting handler."""
import argparse
import asyncio
import json
from pathlib import Path

from financial_research.runtime import run_research


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target", default="value")
    parser.add_argument("--horizon", default=1)
    parser.add_argument("--require-point-in-time", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(run_research(task="research-grade baseline forecast", mode="forecasting", output_level="research_grade", target=args.target, horizon=args.horizon, dataset_path=str(args.dataset), artifact_dir=str(args.output_dir), require_point_in_time=args.require_point_in_time))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    raise SystemExit(0 if result.get("execution", {}).get("status") in {"completed", "degraded"} else 2)


if __name__ == "__main__":
    main()
