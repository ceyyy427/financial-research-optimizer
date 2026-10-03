# Getting started

Finahinking is a local-first research and education workspace. The first
workflow is deliberately offline: open a captured BLS CPI event, follow its
evidence to a concept, run a deterministic quant example, and save learning
state. No market-data credential is needed.

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

See [INSTALLATION.md](INSTALLATION.md) for platform notes and clean-install
evidence.

## 2. Open the local application

```bash
python scripts/run_local_app.py --sample --port 8765
```

Visit <http://127.0.0.1:8765/>. The service binds to loopback by default and
stores state in the local application database. Stop it with `Ctrl-C`.

## 3. Complete the first journey

1. Choose the captured BLS CPI 2024–2025 event (label: `CAPTURED`).
2. Read the claim, source, retrieval/capture time, and limitation.
3. Open the linked Inflation concept and inspect intuition, equation, and
   financial interpretation.
4. Run the sample returns → volatility → beta → Sharpe experiment.
5. Save the learning note and close/reopen the application.

Every result should retain a source/provenance reference. A sample result is
not a live quote, forecast, or trading signal.

## 4. Development loop

```bash
python -m pytest -q
ruff check src tests scripts
python scripts/validate_governance.py .
python -m pip check
git diff --check
```

The `research` extra adds notebook tooling; PostgreSQL is only needed for the
disposable migration check. SQLite is the default local store.
