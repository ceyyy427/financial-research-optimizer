# P5 Dependency Decision

**Decision date:** 2026-10-02

**Status:** No dependency approved or installed. Human approval is required
before P5 implementation.

No candidate is approved for installation in the P4 Architecture Freeze.

## Candidates

### vectorbt — conditional candidate

Vectorbt is a strong candidate for vectorized signal, portfolio, and parameter
experiments. Its Pandas/NumPy orientation could fit the current data contracts,
but an adapter would be required to preserve ResearchRun fingerprints,
timestamp-safe execution, and explicit cost assumptions. Its upstream project
documents an Apache 2.0 license with Commons Clause, so legal/distribution
compatibility and optional dependency licenses must be checked before adoption.

**Decision:** Candidate for a deterministic fixture comparison only; not
approved for installation.

### Pyfolio Reloaded — conditional reporting candidate

Pyfolio Reloaded is a candidate for portfolio performance and risk reporting
after a ledger and return series exist. It is not a backtest engine and must not
define order semantics or research validity. Its Apache-2.0 license is a useful
starting point, but its report semantics, dependency versions, and maintenance
must be reviewed against the project's reproducibility requirements.

**Decision:** Candidate as an optional post-ledger reporting layer; not
approved for installation.

## Rejected as the default

### Backtrader — rejected for default adoption

Backtrader has a useful event-oriented strategy/order/position model, but the
upstream repository is GPL-3.0. That license may not fit Finahinking's intended
distribution model without a separate compatibility decision. Its stateful
execution model also increases integration and audit complexity relative to a
small, explicit P5 ledger boundary.

**Decision:** Rejected as the default P5 dependency. It may only be reconsidered
after human legal, maintenance, and architecture approval.

## No additional statistics package yet

Existing NumPy, Pandas, SciPy, and Statsmodels should be preferred. An extra
statistics package is not justified until a named research-validity requirement
cannot be met by the current environment and a dedicated dependency proposal
records version, purpose, license, security, maintenance, and rollback.

## Evaluation sources

- [vectorbt](https://github.com/polakowo/vectorbt)
- [Backtrader](https://github.com/mementum/backtrader)
- [Pyfolio Reloaded](https://github.com/stefan-jansen/pyfolio-reloaded)

All source facts and licenses must be rechecked at the time of P5 approval.
This document does not authorize package installation.
