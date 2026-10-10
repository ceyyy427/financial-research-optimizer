# Task 1 report — serializable runtime protocol

## RED

Command:

```text
python3 -m pytest -q tests/research/test_runtime_protocol.py
```

Result: collection failed as expected because `finahinking.research.runtime_protocol` did not yet exist (`ModuleNotFoundError`).

## GREEN

Implemented `WorkerInvocation`, `WorkerMessage`, bounded canonical JSON encode/decode, explicit message kinds, SHA-256 invocation digests, strict field/type validation, finite-number checks, recursive unsafe secret/path/prompt value rejection, immutable defensive copies, explicit digest validation, duplicate-key rejection, size limits, and job/digest validation. Added package exports and focused tests.

Commands:

```text
python3 -m pytest -q tests/research/test_runtime_protocol.py
# 20 passed

python3 -m ruff check src/finahinking/research/runtime_protocol.py tests/research/test_runtime_protocol.py src/finahinking/research/__init__.py
# All checks passed!
```

## Full-suite evidence

```text
python3 -m pytest -q
# 1 failed, 933 passed, 2 skipped
# Existing failure: tests/research/test_runtime_limits.py::test_concurrent_runs_keep_independent_budgets_and_metrics
# observed RETRYABLE where COMPLETED was expected.
```

The full-suite failure is unrelated to the new protocol files and was preserved for the parent task's concurrency investigation.
