# Finathink P6.5 Understanding Engine Design

**Date:** 2026-10-03  
**Status:** Approved for autonomous execution by the user’s continuation instruction.  
**Spec:** `/Users/mac/.codex/attachments/c58d816a-bb67-4f31-84eb-19c2e7e0a86a/pasted-text-1.txt`

## Intended outcome

P6.5 must prove one product-quality, evidence-bound journey: an official BLS
CPI release is captured, preserved, replayable offline, normalized into a
canonical observation and event, linked to typed claims and evidence, mapped to
concepts and a mechanism, tested through the existing P6 typed Quant Gateway,
explained with explicit uncertainty, and connected to the existing learning
state. The result must help a person reason better; it must not become a news
summarizer, prediction engine, trading system, data warehouse, or multi-agent
runtime.

## Fixed boundaries

- P4, P4.5, P5, P5.5, and the P6 Quant Gateway, ResearchRun, QuantRun,
  Artifact, fingerprint, provenance, and LearningState contracts remain valid.
- P6.5 adds an isolated `finahinking.p6_5` domain package and additive database
  migration; it does not duplicate or rewrite existing P6 abstractions.
- BLS is the first authoritative source. The API endpoint and official release
  page are preserved as source identity; aggregators never become facts.
- Raw transport payloads are immutable artifacts. Canonical models contain
  explicit `occurred_at`, `effective_at`, `published_at`, `available_at`, and
  `retrieved_at` semantics; missing time evidence remains missing.
- SQL is parameterized behind a typed repository. PostgreSQL is the target
  system of record; a built-in SQLite adapter is used for deterministic tests.
- No new Python dependency, plugin, MCP server, agent framework, live provider,
  vector database, or host PostgreSQL installation is required.
- All external source text is data, never instructions. Dynamic execution,
  arbitrary SQL, source mutation, package installation, and unrestricted HTTP
  are prohibited.
- P7 remains waiting for explicit human approval.

## Chosen architecture

The implementation uses six small boundaries:

1. `p6_5.models` owns canonical source, capture, observation, event,
   claim/evidence, concept, mechanism, conclusion, and product-journey records.
2. `p6_5.admission` owns source tiers, admission decisions, endpoint metadata,
   and conflict policy.
3. `p6_5.bls` owns the allowlisted BLS HTTP client, bounded retries, transport
   capture, fixture replay, parser, canonicalization, and release association.
4. `p6_5.repository` owns the typed parameterized repository and validates the
   PostgreSQL migration against an ephemeral Docker PostgreSQL instance plus a
   SQLite deterministic test adapter.
5. `p6_5.engine` owns the vertical slice and progressive-disclosure product
   journey. It delegates quantitative work to `P6QuantGateway` through a
   `TypedToolRequest` and emits only normalized evidence.
6. `p6_5.evaluation` owns quality, audit, and understanding-gain checks; it
   never recalculates or silently edits source facts.

The data flow is:

```text
BLS API / release page
  -> Source + SourceRelease
  -> TransportCapture + Artifact
  -> ObservationVersion / Measurement
  -> CPI Event
  -> Claim + ClaimEvidenceLink + Evidence
  -> Concept + MechanismEdge
  -> typed P6 Quant request
  -> ResearchRun -> QuantRun -> Artifact -> Quant Evidence
  -> conclusion ladder
  -> Predict -> Reveal -> Explain
  -> LearningCard -> LearningStore
```

## Temporal and revision decisions

`occurred_at` is the economic period or event occurrence; `effective_at` is the
period in which an observation applies; `published_at` is the official release
publication time; `available_at` is the earliest time a consumer could retrieve
the value under the source contract; `retrieved_at` is local capture time. The
BLS API does not itself provide a public-release timestamp for each series row,
so the parser does not infer `available_at` from `retrieved_at`; a release page
or schedule must supply it. Revision versions are append-only and linked by
`supersedes_observation_id`; a conflict is stored, not discarded.

## Database decision

The migration creates normalized tables for sources, endpoints, releases,
captures, artifacts, observations, measurements, events, claims, evidence,
claim-evidence links, concepts, concept relations, hypotheses, explanations,
and learning references. It uses foreign keys, composite uniqueness at source
grain, indexes for available-time and event lookup, and checks for valid enums
and temporal ordering. Production migration SQL is PostgreSQL-native; the
repository’s test adapter translates only the small type/placeholder differences
needed to exercise constraints deterministically in SQLite.

## Product decision

The first journey is one CPI event and one event-study hypothesis. The UI-facing
record is progressive: `what_happened`, `what_changed`, `show_evidence`,
`why_it_matters`, `knowledge_bridge`, `test_the_idea`, `quant_evidence`,
`conclusion_ladder`, `predict_reveal_explain`, `learning_card`, and
`learning_state`. Each statement carries a claim type and evidence status; the
ladder never collapses fact, interpretation, hypothesis, unknown, or limitation.

## Verification decision

The new deterministic tests cover capture/replay, parsing, temporal and revision
semantics, data quality, source conflicts, migration constraints, claims and
evidence, Show Evidence, mechanism edges, typed Quant bridging, conclusion
ladder, learning integration, prompt injection, SQL safety, and fingerprints.
Live BLS smoke is separate from CI. The final P6.5 gate reruns all P0–P6 gates,
the new suite, both Python environments, Ruff, notebook, governance, pip checks,
Docker PostgreSQL migration verification, security AST scan, provenance/HEAD
assertion, and clean-worktree checks.

