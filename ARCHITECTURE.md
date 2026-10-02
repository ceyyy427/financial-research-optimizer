# Architecture

Finahinking is organized around small boundaries that keep network effects and
research transformations separate:

`provider -> dataset/provenance -> validation -> feature functions -> factors -> ExperimentEngine -> ResearchRun -> RunStore`

Providers are the only network boundary. They return normalized data and
immutable provenance metadata. Dataset validation checks schema, missingness,
time ordering, and duplicate observations before feature functions receive a
series. Features are pure transformations. Factors are named, documented
computations with explicit evaluation metrics and limitations.

P4 keeps execution, record modeling, and persistence separate. `ExperimentEngine`
binds a validated dataset and documented factor to an explicit method and
parameters; `ResearchRun` stores the question, hypothesis, dataset, result,
conclusion, insight, and limitations as canonical JSON with SHA-256
fingerprints; `RunStore` persists records locally with path-safe IDs and atomic
writes. Stored records are data only and never execute code.

## Research quality

Every result should identify its source, retrieval time, assumptions, and
known limitations. Reviews check for look-ahead bias, leakage, missing data,
survivorship bias, numerical edge cases, and multiple-testing concerns. The
codebase never emits investment advice or trade instructions.

## Phase boundary

The P0–P4 delivery ends with a descriptive, reproducible experiment foundation.
Backtesting, portfolio simulation, brokerage integration, and investment advice
are out of scope for P4. Any P5 change to this boundary requires human approval,
an approved gate design, a dependency review, and an independent gate review.

The current governed boundary is P6.5: a bounded, source-admitted
understanding journey layered on the frozen P6 guided, typed,
human-controlled research and learning contracts. The P6.5 path is
`official source → capture/replay → canonical observation → event →
claim/evidence → typed P6 quant → explanation → learning`; the AI layer
classifies and explains while Finahinking-owned services calculate and preserve
provenance. P6.5 stops at its Gate Review. P7, live execution, brokerage
integration, unrestricted strategy search, and automatic recommendations remain
out of scope pending explicit human approval.
