# Finahinking

Finahinking is a personal financial research laboratory for reproducible,
evidence-bound analysis. It is a research codebase, not a trading system or an
investment adviser.

The project provides no investment advice, trade instructions, or promise of
financial outcomes. Results are for research and learning; users are
responsible for their own decisions.

## Scope

The first delivery establishes a governed foundation through P3:

`provider -> dataset/provenance -> validation -> feature functions -> factors`

P4 experiment persistence and orchestration are explicitly out of scope.
Network access is isolated to documented data-provider code, and tests use
recorded fixtures by default.

## Repository map

- `src/finahinking/` — the Python package and its stable module boundaries.
- `fixtures/` — deterministic, reviewed input data for tests.
- `tests/` — unit and integration checks that do not require live network access.
- `docs/` — phase gates and the authoritative project state.
- `.agents/` — role contracts for orchestration, planning, architecture,
  implementation, security, dependency control, release, research, and review.

## Development

Use Python 3.11 or newer. The dependency record and lock file are the source
of truth for installed packages. Before proposing a change, run:

```text
python scripts/validate_governance.py
```

The complete test and lint commands are documented in `CONTRIBUTING.md` as
the research environment is added.
