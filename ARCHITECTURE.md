# Architecture

Finahinking is organized around small boundaries that keep network effects and
research transformations separate:

`provider -> dataset/provenance -> validation -> feature functions -> factors`

Providers are the only network boundary. They return normalized data and
immutable provenance metadata. Dataset validation checks schema, missingness,
time ordering, and duplicate observations before feature functions receive a
series. Features are pure transformations. Factors are named, documented
computations with explicit evaluation metrics and limitations.

The current P3 boundary ends at descriptive feature and factor evaluation.
Later execution, record modeling, persistence, backtesting, and learning
modules remain historical artifacts and are not part of this delivery.

## Research quality

Every result should identify its source, retrieval time, assumptions, and
known limitations. Reviews check for look-ahead bias, leakage, missing data,
survivorship bias, numerical edge cases, and multiple-testing concerns. The
codebase never emits investment advice or trade instructions.

## Phase boundary

The current governed delivery is P0–P3: a descriptive, reproducible research
foundation. P4 experiment persistence, P5 backtesting, brokerage integration,
live execution, and investment advice are out of scope. Any P4+ change requires
a new human-approved phase request, an approved gate design, a dependency
review, and an independent gate review. Historical P4–P6.6 modules are retained
for traceability but do not change this current boundary.
