# Finahinking

Finahinking is a personal financial research laboratory for reproducible,
evidence-bound analysis. It is a research codebase, not a trading system or an
investment adviser.

The project provides no investment advice, trade instructions, or promise of
financial outcomes. Results are for research and learning; users are
responsible for their own decisions.

## Scope

The current governed delivery boundary is P7, with P8 intentionally held for
human approval:

`provider -> dataset/provenance -> validation -> feature functions -> factors`

P0–P6.6 provide governance, reproducible data/evidence and quant authorities,
guided learning, and a research-only strategy simulation lab. P7 adds private
personal continuity, explainable mastery, explicit projections, and
evidence-linked rooms. No phase executes trades, provides investment advice,
or implies a forecasting result. Tests use recorded fixtures by default.

P8 remains a readiness report only. Brokerage, live execution, credentials,
and autonomous community moderation are out of scope.

## Repository map

- `src/finahinking/` — the Python package and its stable module boundaries.
- `fixtures/` — deterministic, reviewed input data for tests.
- `tests/` — unit and integration checks that do not require live network access.
- `docs/` — phase gates and the authoritative project state.
- `docs/p6_5/`, `docs/p6_6/`, and `docs/p7/` — phase contracts, reviews, and
  final validation evidence.
- `.agents/` — role contracts for orchestration, planning, architecture,
  implementation, security, dependency control, release, research, and review.

## Development

Use Python 3.11 or newer. The dependency record and lock file are the source
of truth for installed packages. Before proposing a change, run:

```text
python scripts/validate_governance.py
```

The complete P0–P7 test, lint, notebook, migration, and governance commands
are documented in `CONTRIBUTING.md` and the phase final validation reports.
`docs/PROJECT_STATE.md` is the authoritative current gate record.
