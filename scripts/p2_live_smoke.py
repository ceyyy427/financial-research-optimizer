#!/usr/bin/env python3
"""Run the opt-in ECB live smoke check without changing offline test defaults."""

from __future__ import annotations

import argparse
import os
import sys
from urllib.error import URLError

from finahinking.data.providers import ECBProvider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2024-01-05")
    args = parser.parse_args(argv)

    if os.environ.get("FINAHINKING_LIVE_SMOKE") != "1":
        print("SKIP: set FINAHINKING_LIVE_SMOKE=1 to enable the ECB live smoke")
        return 0

    try:
        dataset = ECBProvider.fetch_exchange_rate(
            currency=args.currency,
            start=args.start,
            end=args.end,
        )
    except (OSError, URLError, ValueError) as exc:  # pragma: no cover - network/provider dependent
        print(f"FAIL: ECB live smoke could not complete: {exc}")
        return 1

    if dataset.frame.empty or dataset.provenance.retrieved_at is None:
        print("FAIL: ECB live smoke returned no observations or retrieval timestamp")
        return 1
    print(
        "PASS: ECB live smoke retrieved "
        f"{len(dataset.frame)} observations from {dataset.provenance.source_url} "
        f"at {dataset.provenance.retrieved_at.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
