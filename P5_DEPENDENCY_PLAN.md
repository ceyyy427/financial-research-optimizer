# P5 Dependency Plan

**Status:** Evaluation only; do not install during P4 review.
**Decision:** No P5 dependency is approved.

This plan compares possible tools for a future backtest/evaluation phase. It is
not a proposal to add them now. Versions, licenses, and maintenance must be
re-checked immediately before a human-approved P5 implementation because they
can change.

## Candidate comparison

| Candidate | Research purpose | Maintenance signal | License / integration concern | Tentative decision |
|---|---|---|---|---|
| **vectorbt** | Vectorized signal/portfolio exploration and parameter sweeps; useful for fast research fixtures. | Active public documentation and repository activity should be rechecked at P5 start. | The open-source repository documents Apache 2.0 with Commons Clause; the extra Commons Clause and optional-dependency licenses require legal review for an open-source project. API and performance assumptions need fixture validation. | Consider only after license review and an adapter boundary. |
| **Backtrader** | Event-oriented strategies, data feeds, analyzers, and explicit order/position flows. | Mature and widely used, but official documentation lists an old Python compatibility baseline; current maintenance and Python support must be verified before adoption. | Upstream repository is GPL-3.0, which may not fit the project's distribution model without a compatibility decision. More stateful integration and slower parameter sweeps are possible trade-offs. | Do not adopt without license and compatibility approval. |
| **Pyfolio Reloaded** | Portfolio performance and risk analytics/tear sheets after a ledger exists. | Public fork has releases and tests, but it is downstream of the original pyfolio and depends on a broader analytics stack. | Apache-2.0 is attractive, but report semantics and dependency versions must be checked against the project's reproducibility policy. It is an evaluator, not a backtest engine. | Consider as an optional reporting layer only. |
| **Additional statistical libraries** | Robust inference, bootstrap, multiple-testing correction, or time-series diagnostics. | Choose a narrowly scoped library only when a specific validity requirement is identified. | Every addition increases the lockfile, security, and numerical-reproducibility surface. Existing NumPy/Pandas/SciPy/Statsmodels should be preferred first. | No candidate approved now. |

## Decision framework

Before installing any candidate, create a phase-specific dependency proposal
with exact version, purpose, license, maintenance evidence, security review,
and rollback plan. Then compare the candidate against a minimal in-house
implementation using deterministic fixtures:

1. Can it enforce timestamp-safe execution and explicit costs?
2. Can its outputs be serialized and fingerprinted without executable state?
3. Can it preserve the P4 ResearchRun and provenance contracts?
4. Can it run offline with the project's supported Python versions?
5. Does its license permit the intended open-source distribution?
6. Can a reviewer audit its defaults and numerical assumptions?

## Sources to re-check at P5 start

- [vectorbt repository and license](https://github.com/polakowo/vectorbt)
- [Backtrader repository](https://github.com/mementum/backtrader)
- [Backtrader documentation](https://www.backtrader.com/docu/)
- [Pyfolio Reloaded repository](https://github.com/stefan-jansen/pyfolio-reloaded)

## Final constraint

No package from this document is installed, imported, or added to
`requirements.lock` by the P4 review. Human approval is required before any
P5 dependency proposal or implementation.
