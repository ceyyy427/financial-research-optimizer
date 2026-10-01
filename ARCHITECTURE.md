# Architecture

Finahinking is organized around small boundaries that keep network effects and
research transformations separate:

`provider -> dataset/provenance -> validation -> feature functions -> factors`

Providers are the only network boundary. They return normalized data and
immutable provenance metadata. Dataset validation checks schema, missingness,
time ordering, and duplicate observations before feature functions receive a
series. Features are pure transformations. Factors are named, documented
computations with explicit evaluation metrics and limitations.

## Research quality

Every result should identify its source, retrieval time, assumptions, and
known limitations. Reviews check for look-ahead bias, leakage, missing data,
survivorship bias, numerical edge cases, and multiple-testing concerns. The
codebase never emits investment advice or trade instructions.

## Phase boundary

The P0–P3 delivery ends with documented factor evaluation. P4 experiment
persistence and orchestration are explicitly out of scope. Any change to this
boundary needs an approved upgrade proposal and a new phase gate.
