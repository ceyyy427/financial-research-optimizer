#!/usr/bin/env python3
"""Optional vectorbt sandbox smoke; run only from ``.venv-vectorbt``.

The result is intentionally a plain JSON summary.  No vectorbt Portfolio or
NumPy object is returned to Finathink's core domain or persisted as an app
artifact.  vectorbt's Apache-2.0 + Commons Clause license remains an explicit
admission constraint (see ``docs/p8_2/P8_2_VECTORBT_SANDBOX.md``).
"""

from __future__ import annotations

import json


def run() -> dict[str, object]:
    import pandas as pd
    import vectorbt as vbt

    close = pd.Series([100, 101, 99, 102, 103, 101], index=pd.date_range("2026-01-01", periods=6, freq="D"))
    entries = close > close.shift(1)
    exits = close < close.shift(1)
    portfolio = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10_000, fees=0.001)
    return {
        "status": "PASS",
        "version": str(vbt.__version__),
        "rows": len(close),
        "total_return": float(portfolio.total_return()),
        "max_drawdown": float(portfolio.max_drawdown()),
        "raw_objects_returned": False,
        "license_gate": "OPTIONAL / COMMONS CLAUSE REVIEW REQUIRED",
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
