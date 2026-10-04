# Quickstart: one useful journey

This path takes a new user from a real captured event to a reproducible
learning artifact in under ten minutes.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/run_local_app.py --sample --port 8765
```

Open `http://127.0.0.1:8765/` and follow:

```text
BLS CPI fixture → evidence/claim → Inflation concept
→ equation/derivation → returns/volatility/beta/Sharpe
→ saved learning note → restart and reopen
```

The fixture is labelled `CAPTURED` and its source, payload hash, capture time,
and limitations are visible. The experiment is deterministic and uses no
network or API key. To learn the same chain in prose, read the
[CPI tutorial](STRATEGY_RESEARCH_GUIDE.md#tutorial-1-understand-a-real-financial-event)
and [quant tutorial](STRATEGY_RESEARCH_GUIDE.md#tutorial-2-learn-quant-from-data).

If the app is unavailable, validate the package and fixtures directly:

```bash
python -m pytest -q
python -m pip check
```

Do not interpret sample output as investment advice or a live-market result.
