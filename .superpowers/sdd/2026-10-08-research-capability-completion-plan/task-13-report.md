# Task 13 report: durable research runtime service

Implemented the reference-only `ResearchRuntimeService` composition boundary on top of the durable queue and bounded worker. Submission derives stable public task and idempotency references, repeated submissions are idempotent, and request/task material is resolved through an application-owned resolver after restart. Trusted stage runners publish only bounded references; completed stages are journaled and skipped during recovery.

The queue now persists task timeouts and stage checkpoint references. Stage checkpoint writes can carry the worker lease fence and reject stale workers, while repeated writes of the same checkpoint remain idempotent. The worker accepts checkpoint callbacks, persists the latest checkpoint, terminates timed-out child processes, handles cancellation, and keeps required-stage failures fail-closed without a result/decision reference.

Validation:

- `python3 -m pytest -q tests/research/test_runtime_service.py tests/research/test_job_queue.py tests/research/test_worker.py` — 23 passed.
- `python3 -m pytest -q` — 908 passed, 1 skipped, 1 unrelated existing failure in `tests/research/test_autonomous_runtime_vertical_slice.py::test_autonomous_runtime_vertical_slice_is_recoverable_and_public` (`DATA_UNAVAILABLE` vs `LEARNING_RECORDED`).

Follow-up concurrency hardening scopes each worker claim made by `run_until_terminal` to its requested `job_id`; the focused runtime/queue/worker suite now passes 24 tests, including a two-job regression that leaves the other job queued.

The autonomous vertical-slice failure was left unchanged for its separate diagnosis.
