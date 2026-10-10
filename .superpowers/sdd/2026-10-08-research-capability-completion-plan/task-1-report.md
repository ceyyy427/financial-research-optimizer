# Task 1 implementation report

Status: DONE

## Review fix round 1

The matrix now validates its repository sources at load time. Every evidence
path must exist, each capability must have a marker in its checklist or state
document, and focused test evidence must remain present. `load_release_matrix`
accepts an optional project root so drift checks are deterministic and
testable; missing or contradictory source evidence raises `ValueError` rather
than returning a stale matrix. Constructor boundary tests also cover
immutability-related invariants and invalid flag/task combinations.

## Delivered

- Added `CapabilityStatus`, immutable `CapabilityRecord`, and
  `load_release_matrix()` in `src/finahinking/research/release_matrix.py`.
- Frozen the nine requested capability categories: provider, Codex, factor,
  engine, risk, portfolio, learning, queue, and UI.
- Explicitly recorded `data_vendor_sdk` and
  `unattended_self_improvement` as `NOT_IN_SCOPE`.
- Kept provider and browser UI external evidence as `EXTERNAL_UNVERIFIED`,
  and optional engines as `ISOLATED_DEFERRED`; no deferred/unverified item can
  resolve to `OFFLINE_PASS`.
- Added the human-readable acceptance matrix at
  `docs/RESEARCH_CAPABILITY_BACKLOG.md` and linked its frozen state from
  `docs/PROJECT_STATE.md`.
- Added focused tests covering category membership, boundary states, and the
  fail-closed status invariant.

## TDD evidence

The required red phase was run before production code existed:

```text
python3 -m pytest tests/research/test_release_matrix.py -q
ModuleNotFoundError: No module named 'finahinking.research.release_matrix'
```

After implementation:

```text
python3 -m pytest tests/research/test_release_matrix.py -q
2 passed
```

## Verification

```text
python3 -m pytest tests/research/test_release_matrix.py tests/research/test_engine_registry.py tests/research/test_capability_vertical_slice.py -q
16 passed

python3 -m compileall -q src/finahinking/research/release_matrix.py tests/research/test_release_matrix.py
PASS

python3 -m ruff check src/finahinking/research/release_matrix.py tests/research/test_release_matrix.py
All checks passed!
```

Review-fix verification reran the focused and relevant suite:

```text
18 passed
```

The full repository gate was not run because Task 1 is scoped to the matrix
and its relevant research checks. No provider SDK, broker, live trading, or
secret-bearing integration was introduced.
