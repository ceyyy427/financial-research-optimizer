# Finathink P6.5 Execution Plan

**Status:** implementation plan and contract ledger for the P6.5 gate
**Date:** 2026-10-03
**Scope:** one evidence-bound BLS CPI vertical slice, from source capture to learning state

## Outcome

P6.5 is complete only when a person can follow one real-world CPI event through:

`REALITY → SOURCE → TRANSPORT CAPTURE → RAW ARTIFACT → CANONICAL OBSERVATION → EVENT → CLAIMS → EVIDENCE → CONCEPTS → MECHANISM → HYPOTHESIS → TYPED QUANT → CONCLUSION → EXPLANATION → PREDICT/REVEAL/EXPLAIN → LEARNING`.

The first implementation is deliberately narrow. It is not a news summarizer,
trading system, recommendation engine, data warehouse, unrestricted scraper, or
multi-agent runtime. A source response is data, not instructions; an LLM may
propose structure but cannot make an unverified fact authoritative.

## Starting point and frozen boundaries

The starting point is the P6-complete repository at commit
`d017440740b8bbebdd95a9b60ab4be14c30a17a0`. The following contracts remain
frozen and are consumed additively:

- P4/P4.5 `ResearchRun`, `QuantRun`, `Artifact`, provenance, and fingerprints;
- the P5/P5.5 experiment planner and validity rules;
- the P6 `TypedToolRequest`, `P6QuantGateway`, prediction/reveal/explain, and
  `LearningStore` contracts;
- existing Python environments and their dependency locks;
- the P0–P6 gate evidence and historical audit documents.

P6.5 adds an isolated `finahinking.p6_5` package and one additive migration. It
does not fork a second quant runtime, replace the persistence layer wholesale,
or rewrite prior phase evidence.

## Work products

1. **Source admission:** BLS CPI is Tier 0/authoritative for this slice. The
   endpoint, release page, usage assumptions, and unresolved-vintage limitation
   are recorded before parsing.
2. **Capture and replay:** the bounded BLS client preserves request fingerprint,
   response bytes, headers, parser version, payload hash, retrieval time, and
   first-observed time. The committed fixture can be replayed without a network.
3. **Canonical domain:** immutable `Source`, `SourceEndpoint`, `SourceRelease`,
   `TransportCapture`, `Observation`, `ObservationVersion`, `Event`, `Claim`,
   `Evidence`, `Concept`, `ConceptRelation`, and `Hypothesis` records.
4. **Persistence:** normalized PostgreSQL-compatible SQL plus a deterministic
   built-in SQLite adapter for tests. Raw payloads are stored as immutable files;
   SQL stores metadata, relationships, and hashes.
5. **Understanding journey:** progressive disclosure, Show Evidence, a
   mechanism map, one typed P6 quantitative experiment, a five-level conclusion
   ladder, prediction/reveal/explain, and a P6 learning card/state.
6. **Evaluation:** deterministic data-quality, temporal/revision, source
   integrity, claim grounding, SQL/prompt boundary, replay, and understanding-
   gain checks; live BLS smoke remains separate from deterministic CI.

## Required order

Shared domain contracts are resolved centrally before adapters or product code
consume them.

```text
architecture/capability audit
        ↓
source admission and tier policy
        ↓
canonical + temporal + revision contracts
        ↓
SQL schema and repository boundary
        ↓
BLS adapter + capture/replay fixture
        ↓
event + claim/evidence + concept/mechanism
        ↓
typed Quant bridge + conclusion ladder
        ↓
product journey + learning integration
        ↓
quality/security/evaluation
        ↓
independent A–K audits and gate review
        ↓
P7 waiting state
```

The first five steps are contract-producing. The product and evaluation steps
may run in parallel only after those contracts are stable. No parallel worker
may invent a different meaning for `available_at`, source tier, claim status,
or revision identity.

## Parallelization boundaries

Safe parallel workstreams are source-admission review, domain-model tests, SQL
review, claim/evidence tests, product journey tests, and security/evaluation
tests. They share the canonical model and therefore merge only through the
single P6.5 package, not by duplicating provider types. A final reviewer must
re-run the suite from a clean checkout and inspect the actual diff.

## Gate sequence

The gate is evidence-first:

1. Run focused P6.5 tests (capture/replay, temporal/revision, repository,
   claims, product, quality/security).
2. Run all existing P0–P6 tests and both Python environments.
3. Run Ruff, notebook and governance validators, and both `pip check` passes.
4. Apply the migration in an ephemeral Docker PostgreSQL 16 instance; run the
   same constraints through the SQLite adapter.
5. Run AST/security scans, replay/fingerprint checks, `git diff --check`, and
   provenance/HEAD assertions.
6. Complete independent audits A–K and the 40-item P6.5 checklist.
7. Record any limitation explicitly. Only then mark P6.5 complete and leave P7
   waiting for human approval.

Live network smoke is an observational check, never a prerequisite for
deterministic replay tests and never allowed to mutate the committed fixture.

## Current implementation ledger

Implemented boundaries are `p6_5.models`, `admission`, `temporal`, `bls`,
`repository`, `claims`, `knowledge`, `product`, and `evaluation`. The current
vertical slice is orchestrated by `UnderstandingEngine` in `product.py`; any
future `engine.py` or `quant_bridge.py` name must remain a thin compatibility
boundary over the existing P6 gateway, not a new runtime. The target database
is PostgreSQL; tests use SQLite because no host driver or database installation
is required.

The BLS API response grammar is intentionally strict: the observed `Results`
object containing a `series` list is admitted, while schema drift is quarantined
or rejected. A `"-"` value and its footnote are retained in the quarantine
record rather than silently disappearing. The BLS API does not provide a public
release timestamp per row, so `available_at` is never set to
`retrieved_at` by assumption. A release/schedule bound plus first observation is
used when available; otherwise availability remains unknown. Revision vintage
identity is not claimed when the source does not expose it.

## Explicit non-goals and exit condition

Do not install a plugin, MCP server, Python package, A-share bulk feed, vector
database, agent framework, broker, Qlib/LEAN/vectorbt production runtime, or
automatic recommendation capability. a-stock-data and AKShare remain discovery
or adapter candidates; Tushare remains a Tier 1 candidate pending endpoint,
licence, token, PIT, and revision review.

The exit state is:

```text
Finathink P6.5 Understanding Engine: COMPLETE
Real-World Evidence Vertical Slice: VALIDATED
Multi-Tier Source Architecture: VALIDATED
P6 Foundation: FROZEN FOR PRODUCT CONSUMPTION
P7: WAITING FOR HUMAN APPROVAL
```

Any failed gate leaves P6.5 in rework; it must not be papered over by changing
the acceptance definition.
