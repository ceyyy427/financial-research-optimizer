# P6.5 Architecture

## Architectural promise

P6.5 turns one admitted external event into an inspectable understanding
journey. The architecture keeps the source, transport, canonical data,
quantitative analysis, explanation, and learning boundaries visible. It never
lets a provider object, free-form prompt, or derived statistic silently become
an authoritative fact.

```text
official BLS release/API
        │ source admission
        ▼
Source / Endpoint / Release
        │ bounded POST + capture
        ▼
TransportCapture ───────► immutable raw Artifact file
        │ parser + quality checks
        ▼
ObservationVersion(s) ─► Observation ─► Event
        │                         │
        │                         ├── Claim ── ClaimEvidenceLink ── Evidence
        │                         └── Concept ── ConceptRelation (mechanism)
        │
        └── event-scoped Hypothesis
                         │ typed P6 request
                         ▼
              ResearchRun / QuantRun / Artifact
                         │ normalized result
                         ▼
             Quant evidence → ConclusionLadder
                         │
                         ▼
      ProductJourney → Predict/Reveal/Explain → LearningCard/State
```

## Boundary ownership

| Boundary | Current owner | Responsibility | Must not do |
| --- | --- | --- | --- |
| Canonical records | `finahinking.p6_5.models` | Immutable, JSON-safe source, capture, observation, event, claim/evidence, concept, and hypothesis records | Import provider-specific models as facts |
| Admission | `p6_5.admission` | Tier and decision registry; immutable source admission record; product journey checks the authoritative BLS record before parsing | Grant authority based on convenience or library popularity |
| Temporal/revision | `p6_5.temporal` | ISO-8601 validation, append-only revisions, conflict records | Infer availability from local retrieval |
| BLS transport | `p6_5.bls` | Allowlisted endpoint, bounded retries, raw capture, replay, strict parser, quarantine | Follow redirects to unknown hosts or guess a changed response shape |
| Persistence | `p6_5.repository` + `001_p6_5_understanding.sql` | Parameterized writes/queries, raw-artifact atomic file write, normalized metadata | Accept dynamic SQL or store only a mutable latest value |
| Evidence resolution | `p6_5.claims` | Verify claim fingerprints against a supplied evidence bundle; expose Show Evidence | Treat a self-attested hash as provenance |
| Knowledge | `p6_5.knowledge` | Mechanism edges and five-level conclusion ladder | Collapse theory into causal fact |
| Product orchestration | `p6_5.product.UnderstandingEngine` | Compose the BLS event, claims, mechanism, typed quant, explanation, and learning | Create a second quant runtime or make a forecast |
| Evaluation | `p6_5.evaluation` | Deterministic data-quality and descriptive understanding-gain checks | Edit source values or claim causal treatment effects |

## Reuse of the frozen P6 foundation

`EventQuantBridge` constructs a P6 `ResearchQuestion`, builds a P6 hypothesis
and experiment specification, registers it with `P6QuantGateway`, and submits
a `TypedToolRequest`. The response carries the
existing request/run/result fingerprints, limitations, and provenance. P6.5
wraps that normalized response as `EvidenceStatus.QUANT_SUPPORTED`; it does
not instantiate another backtest engine.

The product journey calls the existing P6
`predict_reveal_explain(..., require_grounding=True)` contract and records the
existing P6 `LearningCard`/`LearningStore` state. P4/P5 artifacts and
provenance remain the system’s quant audit trail. P6.5’s SQL schema stores a
reference to that evidence; it is not a competing artifact store.

## Persistence topology

PostgreSQL is the intended system of record. The migration is deliberately
conservative SQL that can be exercised by SQLite: JSON-shaped metadata is text,
booleans are constrained integers in the portable definition, and the adapter
uses the standard library `sqlite3` connection. This adapter is deterministic
test/dev infrastructure, not a claim that SQLite is the production database.

Raw BLS bytes are written atomically beneath a caller-provided artifact root.
Relational rows retain the artifact path, byte length, payload hash, capture
metadata, and relationships. SQL methods use fixed statements with bound
parameters. Docker PostgreSQL 16 is used for migration verification; no host
PostgreSQL server or Python driver is required by the repository.

## Source and temporal trust model

BLS is Tier 0 for this first slice because the Bureau of Labor Statistics is the
original publisher and supplies both a public API and an official release
page. The API response is evidence of what was received, not proof of an
unseen vintage. `occurred_at`/`effective_at` identify the economic period;
`published_at` comes from the official release; `available_at` is a source-bound
consumer-availability time; `retrieved_at` is local capture time. The parser
only computes availability from an explicit release bound and first-observed
time. It never aliases `available_at` to `retrieved_at`.

If a provider later publishes a revision, P6.5 appends an
`ObservationVersion`, links `supersedes_version_id`, and retains a
`SOURCE_CONFLICT` record when values disagree. The current BLS API does not
expose a public vintage identifier; that limitation is carried into evidence
and the conclusion ladder rather than hidden.

## Product-facing progressive disclosure

The journey has five levels (`EVENT`, `MECHANISM`, `EVIDENCE`, `QUANT`,
`DEEP_KNOWLEDGE`). The first screen can state what happened and what changed;
the user can open the mechanism, inspect source artifacts and timing, test a
bounded idea, inspect the quant run, then read concepts and limitations. Every
important sentence is either a typed claim or an explicitly marked
interpretation, hypothesis, unknown, or limitation. The 11 narrative/action
slots in the contract plus the learning artifact are listed in
`P6_5_UNDERSTANDING_CONTRACT.md`.

## Security boundaries

- Only `https://api.bls.gov/publicAPI/v2/timeseries/data/` is admitted by the
  first client; requests are bounded by series count, year span, payload size,
  timeout, and retry count.
- Source payloads are inert data. No source string is evaluated as Python,
  Jinja, SQL, or a tool instruction.
- `TypedToolRequest` validates bounded JSON values and rejects unsafe URI
  schemes, SQL/Jinja markers, and oversized/deep payloads before the P6 gateway.
- SQL is fixed and parameterized; user input is never interpolated into table,
  column, or query text.
- Artifact identifiers are constrained and written through a temporary file plus
  atomic rename under the configured root.
- Claims cross the product boundary only after evidence/fingerprint resolution;
  absent evidence is represented as `INSUFFICIENT_EVIDENCE` rather than a
  confidence percentage.

## Known boundaries and future work

This is one vertical slice. Fed, SEC, A-share, consensus, and historical
analogue ingestion are architectural extension points, not admitted sources in
this release. The SQL migration intentionally leaves JSON metadata as text. A
production PostgreSQL driver/repository, richer revision-vintage
identifiers, and a UI are future work. None is silently substituted by the
SQLite test adapter or by an aggregator.
