# Task 4 report: explicit Codex research dispatch

Implemented digest-only Codex dispatch and callback handling.

- Added immutable `CodexDispatchRecord` plus `CodexBridge.enqueue` and
  `record_external_result`.
- Invalid input fingerprints fail closed; accepted callbacks are idempotent,
  while rejected callbacks remain retryable.
- Added external queue jobs with a `task_type` marker. SQLite stores task,
  envelope, and result digests only; prompts, provider objects, and secrets are
  never persisted.
- Added `EXTERNAL_TURN_REQUIRED` as an explicit terminal workflow state so a
  missing Codex callback cannot become a successful research run.

## Verification

```text
PYTHONPATH=src python3 -m pytest tests/research/test_codex_dispatch.py tests/research/test_codex_bridge.py tests/research/test_job_queue.py tests/research/test_workflow.py tests/research/test_vertical_slice.py -q
41 passed

PYTHONPATH=src python3 -m pytest -q
799 passed, 1 skipped, 1 failed
```

The single full-suite failure is the pre-existing wheel installation probe in
`tests/validation/test_artifact_install.py`; its subprocess failure does not
touch the changed research dispatch paths. The suite also reports the existing
Python 3.13 multiprocessing fork deprecation warning.
