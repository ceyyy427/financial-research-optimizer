# Architecture

Finahinking is organized around small boundaries that keep network effects and
research transformations separate:

`provider -> dataset/provenance -> validation -> feature functions -> factors`

Providers are the only network boundary. They return normalized data and
immutable provenance metadata. Dataset validation checks schema, missingness,
time ordering, and duplicate observations before feature functions receive a
series. Features are pure transformations. Factors are named, documented
computations with explicit evaluation metrics and limitations.

P6.6 remains the authority for strategy IR, feature graphs, backtest/OOS
metadata, paper simulation, and learning-card evidence. P7 adds a separate
privacy-first relational boundary for private graphs, mastery, history,
explicit projections, and evidence-linked rooms. P7 never recalculates or
overrides the earlier research authorities.
P4 experiment persistence and P5/P6 research services remain part of that
reviewed authority chain.

## Research quality

Every result should identify its source, retrieval time, assumptions, and
known limitations. Reviews check for look-ahead bias, leakage, missing data,
survivorship bias, numerical edge cases, and multiple-testing concerns. The
codebase never emits investment advice or trade instructions.

## Phase boundary

The current governed delivery is P0–P7: a descriptive, reproducible research
and private-continuity foundation. P7 tables use parameterized SQL and
fingerprinted projections. P8 is readiness-only. Brokerage integration, live
execution, investment advice, secrets, and autonomous community moderation are
out of scope and require a new human-approved phase request, dependency review,
and independent gate review.
