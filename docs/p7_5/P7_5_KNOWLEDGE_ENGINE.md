# P7.5 Knowledge Engine

Status: implemented as the versioned `p7.5-reference-1` catalog.

The engine is an explicit Python domain model in
`src/finahinking/p7_5/knowledge.py`; Markdown is only a rendering/documentation
surface. `seed_reference_curriculum()` builds a deterministic, immutable
catalog and `DEFAULT_CATALOG` is the local default. A catalog fingerprint is
available for provenance and reproducibility.

## Contract

`KnowledgeConcept` carries a stable id, title, domain, intuition, formal
definition, typed prerequisites, equations, derivation steps, code examples,
financial interpretations, quant and strategy application links,
event links, misconceptions, source references, examples, assumptions, exercises, tags, and
an optional current-user-context slot. Every reference concept supports the
eight progressive levels: intuition, formal definition, equation,
derivation/proof, code, financial interpretation, quant/strategy application,
and current context.

`DomainCoverage` maps the requested mathematics (linear algebra, calculus,
optimisation), probability, statistics, econometrics/time series, quantitative
research, portfolio/risk, asset pricing, markets, accounting/fundamentals,
behavioral science, and computer science for finance to sourced concepts. It
marks whether a domain is `REFERENCE` or `SCHEMA_READY`, so the engine is
honest about depth while remaining extensible.

The first reference path is:

`Return → Compounding → Variance → Standard Deviation → Volatility → Covariance → Correlation → Regression → Beta → Sharpe → Drawdown → Momentum → Backtesting → OOS → Overfitting`

The engine validates unknown links and prerequisite cycles at construction
time. `search()` is deterministic and `prerequisite_closure()` returns a
topologically ordered, deduplicated path. User mastery, history, and privacy
remain in the existing P7 graph; the public catalog contains no owner or
mastery fields.

Suitable concepts (variance, correlation, regression, beta) also carry an
explicit proof note; a derivation is not silently promoted to a proof for
concepts where that claim would be irrelevant.

## Boundaries

The catalog never executes code or calls a provider. Examples are labelled
illustrations and must be run through the governed quant runtime. Financial
interpretations distinguish definitions, mathematical/theoretical claims,
conventions, and empirical findings. Raw model output cannot become
authoritative content without a source and review.
