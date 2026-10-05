# Task 5 report: checkpoint, cancellation, recovery and queue boundary

Implemented `ResearchRunStore` and `RunControl` for the governed research contracts.

Changes:

- Added atomic, fsync-backed checkpoint JSON writes with stable JSON ordering.
- Added checkpoint schema, workflow, identity digest, dataset snapshot, analyst set and provider capability digest validation.
- Added typed failures for corrupt, incompatible, mismatched and completed checkpoints.
- Added append-only, fsync-backed `events.jsonl` storage and typed corruption handling.
- Added secret/prompt/raw-provider-response field rejection before persistence.
- Added process-local cancellation tokens and workflow cancellation checks. Cancellation yields `CANCELLED` and leaves artifacts/checkpoints untouched.
- Exported store and typed failure classes from `finahinking.research`.

TDD evidence:

- `tests/research/test_run_store.py` was written before `run_store.py`; the first run failed at collection because the module did not exist (RED).
- The focused suite now passes: **7 passed**.

Validation:

- `python3 -m pytest -q tests/research tests/p6 tests/p8_2 tests/p8_2b --disable-warnings --maxfail=1` → **222 passed, 1 skipped**.
- `python3 -m ruff check src/finahinking/research/run_store.py src/finahinking/research/workflow.py src/finahinking/research/__init__.py tests/research/test_run_store.py` → **All checks passed**.

Concerns:

- `RunControl` is intentionally process-local; no background worker or durable queue service was added.
- Checkpoint payloads contain contract state and identity only; final reports/artifacts remain outside the checkpoint store.
