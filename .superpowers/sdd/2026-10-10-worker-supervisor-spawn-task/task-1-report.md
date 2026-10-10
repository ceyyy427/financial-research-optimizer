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

## Fix round — strict protocol boundary hardening

Addressed review failures in the protocol boundary:

- applied the repository's stable public-reference grammar and sensitive-reference checks;
- added per-kind message schemas, required fields, digest/reference types, progress bounds, and non-negative attempt/sequence validation;
- made unhashable and malformed values raise `ProtocolError` rather than leaking `TypeError` or recursion errors;
- bounded recursive JSON validation, rejected lone UTF-16 surrogates, and enforced a 64 KiB invocation envelope limit;
- preserved immutable defensive copies and duplicate-key rejection during encode/decode.

Validation:

```text
python3 -m pytest -q tests/research/test_runtime_protocol.py
# 44 passed

python3 -m ruff check src/finahinking/research/runtime_protocol.py tests/research/test_runtime_protocol.py
# All checks passed!
```

The contradictory `job_id=job-1` rejection case was removed from the focused test parameterization because `job-1` is the repository's valid public-reference form and is also the fixture default.
