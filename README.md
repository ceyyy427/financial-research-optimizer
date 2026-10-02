# Finahinking

Finahinking is a personal financial research laboratory for reproducible,
evidence-bound analysis. It is a research codebase, not a trading system or an
investment adviser.

The project provides no investment advice, trade instructions, or promise of
financial outcomes. Results are for research and learning; users are
responsible for their own decisions.

## Scope

The requested governed delivery boundary is P3, with P4 intentionally held
for human approval:

`provider -> dataset/provenance -> validation -> feature functions -> factors`

P0–P3 provide governance, a reproducible Python environment, an ECB-backed
fixture/provider boundary, validated datasets, descriptive feature functions,
and documented factor evaluation. They do not execute trades, provide
investment advice, or imply a forecasting result. Network access is isolated
to allowlisted provider code, and tests use recorded fixtures by default.

Later P4–P6.6 files remain in the repository as historical material from prior
work, but are outside this requested delivery boundary and are not endorsed by
the current P3 gate. P4+ may only become authoritative after a new human-
approved phase request.

## Repository map

- `src/finahinking/` — the Python package and its stable module boundaries.
- `fixtures/` — deterministic, reviewed input data for tests.
- `tests/` — unit and integration checks that do not require live network access.
- `docs/` — phase gates and the authoritative project state.
- `docs/p6_5/` and `docs/p6_6/` — retained historical later-phase material;
  not part of the current P3 delivery.
- `.agents/` — role contracts for orchestration, planning, architecture,
  implementation, security, dependency control, release, research, and review.

## Development

Use Python 3.11 or newer. The dependency record and lock file are the source
of truth for installed packages. Before proposing a change, run:

```text
python scripts/validate_governance.py
```

The complete P0–P3 test, lint, notebook, and governance commands are
documented in `CONTRIBUTING.md` and
`docs/FINAHINKING_P3_COMPLETION_REPORT.md`. The P3 gate review records the
current stop point before P4.
