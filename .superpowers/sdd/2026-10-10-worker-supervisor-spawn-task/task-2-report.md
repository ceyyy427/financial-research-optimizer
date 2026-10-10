# Task 2 report — static Stage Registry

## Scope

Added a code-owned `StageRegistry` and `StageSpec` contract for spawn-safe
research stages. Registration accepts only trusted module-level functions
that are exported by their declaring module; lambdas, closures, bound methods,
partials, dynamic imports, and task-supplied callable paths are rejected.

The registry enforces paper-only stages, stable public references, duplicate
name/runner-key rejection, deterministic sorted snapshots, and a canonical
registry digest that includes the trusted runner identity. The default registry
contains only the fixed top-level `run_default_workflow_stage`; it performs
application imports only when that stage is executed and converts blocked
workflow outcomes into an explicit blocked result.

## Verification

```text
PYTHONPATH=src python3 -m pytest -q tests/research/test_stage_registry.py
# 5 passed

PYTHONPATH=src python3 -m ruff check src/finahinking/research/stage_registry.py tests/research/test_stage_registry.py src/finahinking/research/__init__.py
# All checks passed!
```

## Notes

RuntimeService wiring and child reconstruction remain Task 3–5 work. This
task only establishes the trusted bootstrap registry and its admission tests.

## Fix round — review findings

- callable admission now checks code metadata and the source file/module
  binding, rejecting renamed/rebound functions that spoof `__module__` or
  `__qualname__`;
- the default workflow stage returns `WORKFLOW_ARTIFACT_UNAVAILABLE` unless a
  completed workflow includes a non-empty persisted manifest and safe run
  reference; malformed workflow objects fail closed;
- regression coverage expanded to seven focused tests.

Validation:

```text
PYTHONPATH=src python3 -m pytest -q tests/research/test_stage_registry.py
# 7 passed

PYTHONPATH=src python3 -m ruff check src/finahinking/research/stage_registry.py tests/research/test_stage_registry.py
# All checks passed!
```
