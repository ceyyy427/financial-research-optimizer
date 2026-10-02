# Finathink P6.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver and validate the P6.5 Understanding Engine with one authoritative BLS CPI vertical slice and a product-facing evidence-to-learning journey.

**Architecture:** Add a small `finahinking.p6_5` package that owns canonical source/capture/event/claim/concept contracts, a BLS adapter, typed repository, and vertical-slice orchestration. Reuse P6’s typed gateway, QuantRun/ResearchRun/Artifact fingerprints, and LearningStore; add a PostgreSQL migration with SQLite tests and no new runtime dependency.

**Tech Stack:** Python 3.11+, dataclasses, pandas, standard-library urllib/json/sqlite3, existing P6/P5.5 services, Docker PostgreSQL for migration verification, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-03-finahinking-p65-design.md`; authoritative mission `/Users/mac/.codex/attachments/c58d816a-bb67-4f31-84eb-19c2e7e0a86a/pasted-text-1.txt`.

## Global Constraints

- P4–P6 contracts remain frozen and additive integration is required.
- BLS CPI is the first authoritative source; aggregators cannot support authoritative FACT claims.
- Preserve raw transport captures before canonicalization and make replay offline.
- Use explicit `occurred_at`, `effective_at`, `published_at`, `available_at`, and `retrieved_at`; never infer `available_at = retrieved_at` without source evidence.
- SQL is parameterized and bounded; no LLM free-form SQL, dynamic execution, prompt-injection authority, or unsafe HTTP.
- No new plugin/MCP/dependency/agent framework unless a documented trusted gap exists.
- P7 and all trading/brokerage/automatic recommendation scope remain out of scope.

## Review Focus

- BLS rows with missing `value` or footnotes must fail/quarantine rather than disappear — owned by capture/parser tests.
- A revised observation must preserve both versions and a supersession link — owned by temporal/revision tests.
- A source conflict must be visible and queryable — owned by repository/conflict tests.
- A forged self-consistent fingerprint without an approved run must not ground a claim — owned by claim/evidence tests.
- A prompt-injected source payload or SQL-like identifier must be treated as data/rejected — owned by security tests.

### Task 1: Architecture and capability evidence

**Files:**
- Create: `docs/p6_5/P6_5_EXECUTION_PLAN.md`, `docs/p6_5/P6_5_ARCHITECTURE.md`, `docs/p6_5/P6_5_CAPABILITY_MATRIX.md`
- Modify: `docs/PROJECT_STATE.md`, `ARCHITECTURE.md`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `DEPENDENCY_RECORD.md`, `EVOLUTION_LOG.md`, `.agents/orchestrator.md`, `.agents/release-manager.md`
- Test: `tests/validation/test_p6_5_docs.py`

**Interfaces:** Record current P6 boundaries, capability audit, plugin/MCP decisions, source tiers, owners, and immutable freeze. No production behavior is changed in this task.

- [ ] Write documentation tests that require all P6.5 deliverables and current-state markers.
- [ ] Run the focused documentation tests and confirm they fail because the files are absent.
- [ ] Write the architecture, capability matrix, execution order, parallelization boundaries, and state transitions.
- [ ] Update governance links without rewriting prior P4–P6 evidence.
- [ ] Run documentation/governance tests and commit the evidence-only task.

### Task 2: Canonical domain and source admission contracts

**Files:**
- Create: `src/finahinking/p6_5/models.py`, `src/finahinking/p6_5/admission.py`, `src/finahinking/p6_5/temporal.py`, `src/finahinking/p6_5/__init__.py`
- Test: `tests/p6_5/test_models.py`, `tests/p6_5/test_admission_temporal.py`

**Interfaces:** `Source`, `SourceEndpoint`, `SourceRelease`, `TransportCapture`, `Observation`, `ObservationVersion`, `Measurement`, `Event`, `Claim`, `Evidence`, `ClaimEvidenceLink`, `Concept`, `ConceptRelation`, `Hypothesis`, `SourceTier`, `AdmissionDecision`, `validate_temporal_order`, `record_revision`, `record_conflict`.

- [ ] Write failing tests for enum validation, deterministic fingerprints, explicit temporal fields, revision links, conflict visibility, and source-tier decisions.
- [ ] Run them to confirm the expected missing-contract failures.
- [ ] Implement immutable, JSON-safe canonical records and validation.
- [ ] Run focused tests, then the full existing suite; commit.

### Task 3: BLS source adapter and capture/replay

**Files:**
- Create: `src/finahinking/p6_5/bls.py`, `fixtures/p6_5/bls_cpi_2024_2025.json`, `tests/p6_5/test_bls_adapter.py`
- Modify: `src/finahinking/data/__init__.py` only if a compatibility export is useful.

**Interfaces:** `BLSClient.fetch`, `BLSClient.capture`, `BLSClient.replay`, `BLSCPIAdapter.parse_capture`, `BLSCPIAdapter.to_observations`, `BLSCPIAdapter.to_event`.

- [ ] Add parser/capture/replay tests first, including malformed schema, missing value, duplicate series-period, and footnote cases.
- [ ] Run them red.
- [ ] Implement allowlisted `api.bls.gov` POST with timeout, bounded transport retries, structured errors, request fingerprint, raw payload hash, parser version, and no semantic retries.
- [ ] Capture an official CPI fixture for `CUUR0000SA0` and `CUSR0000SA0`; associate the December 2024 official release page and schedule metadata.
- [ ] Re-run offline replay tests and live smoke separately; commit.

### Task 4: PostgreSQL schema, repository, and migration verification

**Files:**
- Create: `migrations/001_p6_5_understanding.sql`, `src/finahinking/p6_5/repository.py`, `tests/p6_5/test_repository.py`, `scripts/verify_p6_5_postgres.py`

**Interfaces:** `UnderstandingRepository`, `SQLiteUnderstandingRepository`, `apply_migration`, `save_source`, `save_capture`, `save_observation`, `save_event`, `save_claim`, `link_claim_evidence`, `show_evidence`, `find_conflicts`.

- [ ] Write failing tests for foreign keys, uniqueness, parameterized query behavior, evidence lookup, and conflict retrieval.
- [ ] Run them red.
- [ ] Implement the normalized PostgreSQL migration and a bounded SQLite adapter for deterministic tests; keep raw bytes outside relational columns except bounded metadata/hash.
- [ ] Run SQLite tests and apply the same migration semantics in an ephemeral Docker PostgreSQL container; record output.
- [ ] Commit.

### Task 5: Understanding Engine, mechanism, claims, and product journey

**Files:**
- Create: `src/finahinking/p6_5/engine.py`, `src/finahinking/p6_5/claims.py`, `src/finahinking/p6_5/knowledge.py`, `src/finahinking/p6_5/quant_bridge.py`, `src/finahinking/p6_5/product.py`
- Test: `tests/p6_5/test_engine.py`, `tests/p6_5/test_claims_knowledge.py`, `tests/p6_5/test_product_journey.py`

**Interfaces:** `UnderstandingEngine.ingest_cpi`, `build_claims`, `show_evidence`, `why_it_matters`, `knowledge_bridge`, `test_idea`, `conclusion_ladder`, `predict_reveal_explain`, `learning_state`; `ConclusionLadder`; `ProductJourney`; typed request flow through `P6QuantGateway`.

- [ ] Write failing end-to-end tests for the required chain and progressive-disclosure fields.
- [ ] Run them red.
- [ ] Implement the vertical slice from captured BLS event through verified claims/evidence and concept mechanism edges.
- [ ] Invoke existing P6 Quant Gateway via `TypedToolRequest` only; bind result to ResearchRun/QuantRun/Artifact and preserve limitations.
- [ ] Reuse `PredictionRevealExplain` and `LearningStore` with real evidence references; no invented quiz answers.
- [ ] Run focused and full tests; commit.

### Task 6: Quality, security, evaluation, and audit artifacts

**Files:**
- Create: `src/finahinking/p6_5/evaluation.py`, `tests/p6_5/test_security_quality_evaluation.py`
- Create required docs: `SOURCE_ADMISSION_POLICY.md`, `SOURCE_TIER_MODEL.md`, `BLS_SOURCE_ADMISSION.md`, `A_STOCK_DATA_DISCOVERY_REVIEW.md`, `AKSHARE_ADMISSION_REVIEW.md`, `TUSHARE_ADMISSION_REVIEW.md`, `P6_5_CANONICAL_DATA_MODEL.md`, `P6_5_TEMPORAL_MODEL.md`, `P6_5_SQL_SCHEMA.md`, `P6_5_EVENT_MODEL.md`, `P6_5_CLAIM_EVIDENCE_MODEL.md`, `P6_5_UNDERSTANDING_CONTRACT.md`, `P6_5_PRODUCT_JOURNEY.md`, `P6_5_EVALUATION_PLAN.md`, `P6_5_SECURITY_REVIEW.md`, `P6_5_DATA_QUALITY_REVIEW.md`

**Interfaces:** `run_data_quality_checks`, `understanding_gain`, `audit_p6_5`, `security_scan_targets`, and deterministic A–K audit result records.

- [ ] Write failing tests for all required quality checks, prompt-injection payloads, SQL safety, source-tier restrictions, and understanding-gain scoring.
- [ ] Run them red.
- [ ] Implement bounded checks, audit records, and source admission documentation with official BLS/a-stock-data/AKShare/Tushare evidence.
- [ ] Run AST/security/data-quality tests and record limitations.
- [ ] Commit.

### Task 7: Gate review, P7 readiness, and final validation

**Files:**
- Create: `docs/p6_5/P6_5_FINAL_VALIDATION_REPORT.md`, `docs/p6_5/P7_READINESS_REPORT.md`, `docs/p6_5/P6_5_GATE_REVIEW.md`
- Modify: `docs/PROJECT_STATE.md`, `EVOLUTION_LOG.md`, `README.md`, `ARCHITECTURE.md`, `CHANGELOG.md`

**Interfaces:** Final state is `Finathink P6.5 Understanding Engine: COMPLETE`, `Real-World Evidence Vertical Slice: VALIDATED`, `Multi-Tier Source Architecture: VALIDATED`, `P6 Foundation: FROZEN FOR PRODUCT CONSUMPTION`, and `P7: WAITING FOR HUMAN APPROVAL`.

- [ ] Add a 40-item gate checklist plus A–K independent audit results.
- [ ] Run full pytest in main and `.venv-quant`, Ruff, notebook, governance, both pip checks, all legacy gates, Docker PostgreSQL migration, security AST, replay/fingerprint, diff check, and clean status.
- [ ] Run the final provenance assertion after the implementation commit and compare every successful workflow response’s `provenance.code_commit` to `git rev-parse HEAD`.
- [ ] Write the final report and P7 readiness decision; stop at the P6.5 Gate Review.

