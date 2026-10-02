# Dependency Record

This file is the authoritative record of why each third-party dependency is
present, who owns it, and which project phase first needs it. No dependency is
installed without an entry here. Versions are pinned in `requirements.lock`
when the P1 environment is created.

## P0 baseline

P0 uses only the Python standard library for governance validation. There are
no runtime or development package dependencies in this phase.

## P1–P3 dependencies

| Package | Role | Scope | Owner | Pinning status |
| --- | --- | --- | --- | --- |
| `numpy` | Numerical arrays for feature calculations | Runtime | Finahinking maintainers | `requirements.lock` |
| `pandas` | Indexed datasets and tabular transformations | Runtime | Finahinking maintainers | `requirements.lock` |
| `pytest` | Test runner | Development | Finahinking maintainers | `requirements.lock` |
| `ruff` | Static checks and formatting | Development | Finahinking maintainers | `requirements.lock` |
| `jupyterlab` | Reproducible research workspace | Research | Finahinking maintainers | `requirements.lock` |
| `ipykernel` | Notebook kernel | Research | Finahinking maintainers | `requirements.lock` |

Adding or upgrading a package requires a purpose, a compatibility note, a
review, and an update to this record and the lock file.

P4 adds no dependency; see DEPENDENCY_PROPOSAL.md.

## P5.5–P6 decision

P5.5 and P6 add no core package, plugin, or MCP server. The existing
`statsmodels==0.15.0` adapter remains admitted only in the isolated
`.venv-quant` environment; the primary `.venv` stays unpolluted. P6 reaches
the regression service through the Finahinking-owned normalized adapter seam,
never through a third-party object. PyPortfolioOpt, bt, vectorbt, Qlib,
Riskfolio, Alphalens, QuantStats/Pyfolio, LangGraph, Ollama, and live-data
providers remain deferred because no demonstrated capability gap requires them.

## P6.5 capability decision

P6.5 adds no package-manager dependency, plugin, MCP connector, provider SDK,
or host database service. The bounded BLS adapter uses the Python standard
library HTTP and hashing primitives; deterministic canonicalization and the
SQLite development adapter reuse the existing runtime, while Docker
`postgres:16-alpine` is used only as a disposable migration-verification
environment. The frozen P6 typed gateway, pandas fixtures, and existing
learning contracts are reused. A capability audit considered broader market
data connectors, browser/document extraction, production PostgreSQL drivers,
and agent frameworks; each was deferred because it would expand scope without
closing a demonstrated P6.5 gap. This decision is recorded in
`docs/p6_5/P6_5_CAPABILITY_MATRIX.md` and the final validation report.

## P6.6 capability decision

P6.6 adds no package-manager dependency, plugin, MCP connector, broker SDK,
market-data adapter, ML framework, or database driver. Python `ast`, pandas,
NumPy, the existing P5/P5.5 ledgers, P6 learning contracts, and P6.5
provenance boundaries close the demonstrated feature/strategy/paper/export
gaps. The decision and residual capability risks are recorded in
`docs/p6_6/P6_6_CAPABILITY_MATRIX.md`.
