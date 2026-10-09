# Task 14 report: runtime limits and metrics

## Implemented

- Added `RuntimeBudget`, `RuntimeMetrics`, and fail-closed `RESOURCE_LIMIT` accounting with safe digests only.
- Added wall time, provider-call, byte, experiment, retry, and same-service concurrency enforcement to `ResearchRuntimeService`.
- Bound provider retries and response/request bytes through the active budget; provider failures normalize to `RESOURCE_LIMIT`.
- Bound factor pipeline and parameter experiments through the active budget while preserving paper-only behavior.
- Exported observability interfaces from `finahinking.research`.
- Added `tests/research/test_runtime_limits.py` covering provider calls/bytes, experiment and wall limits, and concurrency.

## TDD evidence

- RED: `python3 -m pytest -q tests/research/test_runtime_limits.py` failed during collection with `ModuleNotFoundError: finahinking.research.observability` before implementation.
- GREEN: `python3 -m pytest -q tests/research/test_runtime_limits.py tests/research/test_runtime_service.py tests/research/test_provider_adapters.py tests/research/test_factor_pipeline.py tests/research/test_factor_experiments.py tests/research/test_job_queue.py tests/research/test_worker.py` — 58 passed.

## Verification

- Focused and adjacent research tests: 58 passed.
- Full `tests/research`: 483 passed, 1 pre-existing/unrelated failure in `test_autonomous_runtime_vertical_slice_is_recoverable_and_public` (`DATA_UNAVAILABLE` vs `LEARNING_RECORDED`), plus existing multiprocessing fork deprecation warnings.

## Files

`src/finahinking/research/observability.py`, `runtime_service.py`, `provider_adapters.py`, `factor_pipeline.py`, `factor_experiments.py`, package exports, and `tests/research/test_runtime_limits.py`.

## Concerns

Metrics are intentionally count/digest-only; raw provider responses, secrets, and filesystem paths are never serialized. The full research suite retains the unrelated vertical-slice failure described above.
