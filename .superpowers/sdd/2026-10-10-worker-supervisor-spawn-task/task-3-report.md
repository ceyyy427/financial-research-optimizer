# Task 3 report — spawn worker and bounded IPC

## Scope

Implemented a module-level `run_spawn_worker` entrypoint and a parent-side
`SpawnWorkerHandle` using `multiprocessing.get_context("spawn")`. The child
receives only a JSON-shaped `WorkerInvocation` plus a trusted registry
bootstrap descriptor; it reconstructs allow-listed runners, sends bounded
protocol messages, and never receives a queue, request object, callable,
database connection, or task-supplied import path.

The worker emits `READY` followed by a strict `RESULT` containing
`result_ref` and `artifact_digest`, or a sequenced `FAILED`/`CANCELLED`
terminal message. Runner exceptions, unknown stages, invalid result
contracts, oversized results, timeout, cancellation, and malformed payloads
fail closed without leaking exception text.

## Verification

```text
PYTHONPATH=src python3 -m pytest -q tests/research/test_spawn_worker.py
# 8 passed

PYTHONPATH=src python3 -m ruff check \
  src/finahinking/research/worker_entrypoint.py \
  src/finahinking/research/worker.py \
  tests/research/test_spawn_worker.py
# All checks passed!
```

The full Supervisor lifecycle, durable queue ownership, retry/recovery, and
runtime-service migration remain Tasks 4–8. This task does not add a fork
fallback.
