# Finahinking

Finahinking is a personal financial research laboratory for reproducible,
evidence-bound analysis. It is a research codebase, not a trading system or an
investment adviser.

The project provides no investment advice, trade instructions, or promise of
financial outcomes. Results are for research and learning; users are
responsible for their own decisions.

## Scope

The governed foundation is complete through P6.6, with P7 intentionally held
for human approval:

`provider -> dataset/provenance -> validation -> feature functions -> factors -> ExperimentEngine -> ResearchRun -> RunStore`

P4 provides local experiment persistence and orchestration through ResearchRun,
ExperimentEngine, and RunStore. P5 adds a research-only, in-house historical
backtest/evaluation runtime with explicit costs, slippage, provenance, and
fingerprints. P5.5 freezes the typed quant boundary and validity/OOS
contracts. P6 adds a guided, human-controlled question → hypothesis →
experiment → evidence → explanation → learning workflow, including a
normalized regression-learning slice. P6.5 adds a bounded Bureau of Labor
Statistics CPI capture/replay path, canonical event/claim/evidence models,
progressive disclosure, reviewed source admission, explicit temporal and
revision semantics, a normalized database schema, and a typed bridge back to
the frozen P6 quant and learning contracts. The first product journey is
bounded to one real BLS CPI event; discovery providers are never silently
promoted to authority. P6.6 adds versioned feature graphs, reviewed strategy
specifications, constrained educational code, P5/P5.5 backtest routing,
out-of-sample metadata, deterministic paper replay, drift diagnostics, and a
safe research export. It does not execute trades, provide investment advice,
or enter P7. Network access is isolated to allowlisted provider code, and
tests use recorded fixtures by default.

## Repository map

- `src/finahinking/` — the Python package and its stable module boundaries.
- `fixtures/` — deterministic, reviewed input data for tests.
- `tests/` — unit and integration checks that do not require live network access.
- `docs/` — phase gates and the authoritative project state.
- `docs/p6_5/` — source admission, temporal/SQL contracts, product journey,
  audits, final validation, and P7 readiness evidence.
- `docs/p6_6/` — strategy-lab contracts, audits, final validation, and P7
  readiness evidence.
- `.agents/` — role contracts for orchestration, planning, architecture,
  implementation, security, dependency control, release, research, and review.

## Development

Use Python 3.11 or newer. The dependency record and lock file are the source
of truth for installed packages. Before proposing a change, run:

```text
python scripts/validate_governance.py
```

The complete test, lint, migration, notebook, and governance commands are
documented in `CONTRIBUTING.md` and the P6.6 final validation report. The
P6.6 gate review records the independent A–J audits and the exact stop point
before P7.
