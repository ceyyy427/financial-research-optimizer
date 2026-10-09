# Task 15 implementation report

## What changed

- Added `ReportBundleWriter.write_runtime_tree()` with a configured output root.
- Added redacted, server-rendered `experiments`, `risk_attribution`, and `learning_history` pages with cross-links and manifest digests.
- Added explicit `PENDING`, `CURRENT`, `COMPLETE`, or `BLOCKED` stage status to runtime pages and required those pages in bundle verification.
- Extended the runtime view model to schema version 3 while retaining server-owned `experiments`, `risk_attribution`, and `learning_history` fields.
- Extended local routes and frontend normalization/rendering for the new read-only stage data. No browser-side financial calculations were added.

## TDD evidence

- RED: `python3 -m pytest -q tests/research/test_report_tree.py` initially failed because the writer had no runtime-tree API and the new runtime fields/pages did not exist.
- GREEN: `python3 -m pytest -q tests/research/test_report_tree.py tests/research/test_reports.py tests/research/test_report_status_wall.py tests/research/test_ui.py` → 26 passed.
- GREEN: `node --test frontend/test/research.test.mjs` → 14 passed.

## Full suite

`python3 -m pytest -q` → 917 passed, 1 skipped, 2 unrelated failures in `test_autonomous_runtime_vertical_slice_is_recoverable_and_public` (fixture ended DATA_UNAVAILABLE) and `test_concurrent_runs_keep_independent_budgets_and_metrics` (retryable worker status).

## Files

`src/finahinking/research/reports.py`, `src/finahinking/research/ui.py`, `src/finahinking/local_app.py`, `frontend/src/research.js`, `frontend/test/research.test.mjs`, and `tests/research/test_report_tree.py`.
