# P6.5 Product Journey: BLS CPI to Learning

## User-facing promise

For one official CPI release, Finathink should help a person answer “what
happened, why might it matter, what evidence supports that, and what could I
test next?” The journey demonstrates evidence-bound reasoning; it does not make
a market call or promise a future return.

## Input and deterministic fixture

The first journey uses the committed
`fixtures/p6_5/bls_cpi_2024_2025.json` fixture, which preserves the observed BLS
API `Results.series` response shape for `CUUR0000SA0` and `CUSR0000SA0`. The
fixture includes valid rows and a `"-"`/footnote row that must be quarantined.
Tests replay it offline with a fixed capture ID and times. A live BLS request is
optional smoke only and cannot mutate the fixture or make CI nondeterministic.

The release record associates the December 2024 reference period with the
official BLS release page and publication bound. `available_at` is kept
separate from local retrieval; where the release supplies an availability bound,
the adapter takes the later of that bound and first observation. The API does
not expose a public vintage identifier, so that uncertainty is shown.

## Journey stages

### 1. Capture reality

`BLSClient.replay` (or the bounded allowlisted `fetch`) creates a
`TransportCapture` before parsing. Request fingerprint, response hash, status,
relevant headers, parser version, `retrieved_at`, `first_observed_at`, and raw
artifact ID are retained. The product writes the raw bytes atomically below the
configured artifact root.

### 2. Canonicalize and quarantine

`BLSCPIAdapter.parse_capture` accepts only the observed BLS `Results` object
grammar. It maps admitted series/period rows to immutable observations and
versions. Missing/non-numeric values, duplicate logical keys, unadmitted series,
invalid periods, and schema drift are quarantined or fail closed; they are not
silently dropped. A release maps publication/availability metadata onto the
matching reference period.

### 3. Form the event

`BLSCPIAdapter.to_event` creates one `MACRO_RELEASE` event for the selected
period, linking observations and direct-source evidence. The event is not an
article and does not contain consensus, surprise, or market reaction fields.

### 4. Separate claims from mechanism

Direct facts become `FACT` claims grounded in the capture and release evidence.
The knowledge bridge defines CPI, inflation, policy rate, bond yield, discount
rate, and valuation concepts. Edges are typed as
`SUPPORTED_RELATIONSHIP` or `ECONOMIC_MECHANISM`/theory; the mechanism includes
an explicit “not causal or a price forecast” limitation.

### 5. Test one bounded idea

The engine asks a P6 `ResearchQuestion` about a fixed historical momentum
experiment in the event context, builds a P6 hypothesis/specification, registers
the plan, and submits a `TypedToolRequest` through `P6QuantGateway`. The existing
P6 `ResearchRun`/`QuantRun`/`Artifact`/fingerprint/provenance chain remains the
source of quantitative truth. The result is wrapped as `QUANT_SUPPORTED` evidence
with gateway limitations; no second quant runtime is created.

### 6. Explain progressively

The `ProductJourney` exposes:

```text
EVENT → MECHANISM → EVIDENCE → QUANT → DEEP_KNOWLEDGE
```

It supplies all Understanding Contract slots, `show_evidence`, the typed test
idea, a five-level `ConclusionLadder`, and P6
`predict_reveal_explain(require_grounding=True)`. The ladder explicitly states
that historical association is not causality and that the release alone does
not determine tomorrow’s equity return.

### 7. Close the learning loop

`make_learning_card` reuses the CPI/inflation formula, the quant evidence
reference, limitations, a common misconception (“hot CPI means stocks must
fall”), and a transfer question. `LearningStore.record_encounter` records the
user encounter with zero assumed confidence; it does not invent quiz answers or
turn engagement into knowledge.

## Show Evidence view

For a selected claim the user can inspect claim type/text, direct source or
quant evidence, publisher/reference, capture/artifact identity, publication and
availability timing where known, fingerprints, scope, and limitations. The
same projection is available in memory (`EvidenceBundle`) and through the
parameterized SQLite repository. An unresolved claim returns no fabricated
evidence.

## Failure and limitation behavior

- malformed BLS grammar: quarantine/fail closed;
- missing value/footnote: quarantine record remains visible;
- unavailable publication bound: `available_at` stays unknown;
- revision without a vintage identifier: preserve versions/conflict and state
  the unresolved-vintage limitation;
- failed typed quant: no quant claim is emitted;
- missing evidence/fingerprint: claim cannot cross the trusted boundary;
- unsupported causal/forecast conclusion: represented as `UNKNOWN` or
  `LIMITATION`.

## What this slice does not claim

It does not provide a production UI, point-in-time vintage reconstruction for
all BLS revisions, live A-share coverage, consensus data, an investment
recommendation, or a causal estimate. Those are explicit follow-up products,
not hidden assumptions in this journey.
