# Finahinking P0–P3 Design Specification

## Purpose

Finahinking is a personal financial research laboratory. This first delivery
establishes a governed, reproducible research foundation through P3. It does
not build a trading system, investment adviser, or P4 experiment persistence.

## Phase boundaries

- **P0 — Development Foundation:** repository governance, architecture
  records, agent contracts, gate records, dependency and evolution policy.
- **P1 — Research Environment:** reproducible Python package, notebook
  workspace, sample research workflow, and deterministic setup checks.
- **P2 — Reality Data Engine:** provider abstraction, dataset/provenance
  models, validation, and one official reproducible public data provider.
- **P3 — Quant Research Engine:** returns, volatility, momentum, drawdown,
  correlation, factor definitions, limitations, and evaluation metrics.
- **P4 is explicitly out of scope.** No ResearchRun persistence or experiment
  orchestration is implemented in this delivery.

## Architecture

The package is a small typed Python library with stable boundaries:

`provider -> dataset/provenance -> validation -> feature functions -> factor
definitions/evaluation`.

Providers return normalized pandas DataFrames and immutable metadata. Feature
functions are pure transformations over indexed price series. Factors are
documented, named computations with explicit limitations and evaluation output.
The network boundary is isolated in the provider module and is never touched by
feature or factor code.

## Data source decision

Use the European Central Bank Data Portal SDMX REST API as the first provider.
It is an official public source, requires no credential for the selected public
series, provides stable CSV responses, and supports provenance through the
request URL and retrieval timestamp. The implementation must validate schema,
index monotonicity, missingness, and duplicate observations before returning a
dataset. Network tests use a recorded fixture; a separate opt-in smoke command
checks live availability.

## Technology and dependency policy

Python 3.11+; pandas and numpy are runtime dependencies; pytest, ruff,
jupyterlab, and ipykernel are development/research tools. No dependency is
installed without an entry in `DEPENDENCY_RECORD.md`. Versions are pinned in
`requirements.lock` after installation and the project uses a local virtual
environment.

## Security and research quality

No secrets are accepted by the first provider. URLs are allowlisted to the ECB
host, timeouts are bounded, and responses are schema-checked. Feature/factor
documentation calls out look-ahead bias, leakage, missing observations,
survivorship bias, and multiple-testing limitations. The package never emits
investment advice or trade instructions.

## Gate protocol

Each phase has a gate design before implementation and a gate review after
implementation. A review can be `PASS` or `REWORK REQUIRED`; only `PASS`
permits the next phase. `docs/PROJECT_STATE.md` is the authoritative status.

## Acceptance criteria

1. A clean checkout can create the documented environment and run the complete
   test suite.
2. A fixture-backed ECB dataset can be loaded, validated, and traced to source
   metadata.
3. A user can calculate and evaluate at least one documented factor without
   network access.
4. Every phase has a completed gate design and independent review.
5. The project stops at P3 with an explicit human-review status.

