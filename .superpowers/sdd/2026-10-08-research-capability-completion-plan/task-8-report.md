# Task 8 report: optional quant-engine admission and deterministic fallback

## TDD

Added `tests/research/test_optional_engine_admission.py` before implementing
the new resolution contract. The red phase failed because
`EngineRegistry.resolve` did not exist and admission metadata was not accepted.
The green phase covers normalized snapshot input, `NOT_INSTALLED` and
`DEFERRED` statuses, admitted execution, result metadata, timeout fallback,
restricted input rejection, and the explicit workflow seam.

## Implementation

- Added `EngineResolution` and `EngineRegistry.resolve(name, dataset)`, with
  dataset fingerprint binding and typed ML/sweep specifications.
- Kept the existing `EngineRegistry.run(name, FinathinkSpecification)` API as a
  compatibility wrapper over the new resolution path.
- Added bounded runner execution with deterministic Finathink fallback on
  timeout or adapter errors.
- Added optional version/license metadata recording in ML artifacts and sweep
  provenance fields. Results remain Finathink-owned contracts; unsafe payloads
  still fail closed.
- Added `ResearchOrchestrator.run_optional_engine` as an explicit opt-in seam;
  the normal workflow and startup path remain unchanged when optional engines
  are absent.

## Verification

```text
PYTHONPATH=src python3 -m pytest -q tests/research/test_optional_engine_admission.py tests/research/test_engine_registry.py tests/research/test_workflow.py
22 passed

python3 -m ruff check src/finahinking/research/engine_registry.py src/finahinking/research/workflow.py tests/research/test_optional_engine_admission.py
All checks passed

PYTHONPATH=src python3 -m pytest -q
850 passed, 1 skipped, 1 failed
```

The full-suite failure is the existing wheel-install integration test
`tests/validation/test_artifact_install.py::test_wheel_install_exposes_migrations_fixtures_and_local_routes`.
It occurs in the isolated wheel probe and is unrelated to the optional engine
files. The suite also reports the existing Python 3.13 multiprocessing fork
deprecation warning.

## Boundary

No vendor SDK was installed, no network or live trading path was enabled, and
no optional engine is marked available without the existing admission gates and
trusted external runner contract.
