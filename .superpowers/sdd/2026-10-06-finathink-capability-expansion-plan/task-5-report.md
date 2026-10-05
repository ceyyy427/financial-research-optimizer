# Task 5 report: checkpoint, cancellation, recovery and queue boundary

Implemented `ResearchRunStore` and `RunControl` for the governed research contracts.

Changes:

- Added atomic, fsync-backed checkpoint JSON writes with stable JSON ordering.
- Added checkpoint schema, workflow, identity digest, dataset snapshot, analyst set and provider capability digest validation.
- Added typed failures for corrupt, incompatible, mismatched and completed checkpoints.
- Added append-only, fsync-backed `events.jsonl` storage and typed corruption handling.
- Added secret/prompt/raw-provider-response field rejection before persistence.
- Added process-local cancellation tokens and workflow cancellation checks. Cancellation yields `CANCELLED` and leaves artifacts/checkpoints untouched.
- Allowed cancellation transitions from every resumable pre-completion workflow state, including evidence, plan, quant, risk, and paper-decision stages.
- Made `load_record()` enforce configured workflow and provider capability expectations, matching `load_checkpoint()`.
- Added recursive sensitive-string checks and strict unknown-field rejection for checkpoint and event payloads.
- Exported store and typed failure classes from `finahinking.research`.

TDD evidence:

- `tests/research/test_run_store.py` was written before `run_store.py`; the first run failed at collection because the module did not exist (RED).
- Review regressions were added first and observed RED (four failures: illegal cancellation transition, missing `load_record()` checks, sensitive strings persisted, and unknown fields accepted), then fixed.
- The focused suite now passes: **11 passed**.

Validation:

- `python3 -m pytest -q tests/research tests/p6 tests/p8_2 tests/p8_2b --disable-warnings --maxfail=1` → **226 passed, 1 skipped**.
- `python3 -m ruff check src/finahinking/research/contracts.py src/finahinking/research/run_store.py src/finahinking/research/workflow.py src/finahinking/research/__init__.py tests/research/test_run_store.py` → **All checks passed**.

Concerns:

- `RunControl` is intentionally process-local; no background worker or durable queue service was added.
- Checkpoint payloads contain contract state and identity only; final reports/artifacts remain outside the checkpoint store.
