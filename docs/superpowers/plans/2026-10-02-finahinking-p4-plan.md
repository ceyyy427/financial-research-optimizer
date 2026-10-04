# Finahinking P4 Experiment Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create, execute, persist, and reproduce a deterministic `ResearchRun`.

**Architecture:** A pure execution service consumes existing P2/P3 contracts and emits a JSON-compatible run record. A local atomic store persists records, while canonical hashes detect dataset or result drift.

**Tech Stack:** Python standard library plus existing pandas/numpy package APIs.

**Spec:** `docs/superpowers/specs/2026-10-02-finahinking-p4-experiment-design.md`

## Global Constraints

- No P5 functionality, external execution, or investment advice.
- No new dependency without `DEPENDENCY_PROPOSAL.md` and `DEPENDENCY_RECORD.md` updates.
- JSON storage must be local, deterministic, schema-validated, and safe from path traversal.
- All new behavior follows red-green TDD and has offline tests.

## Review Focus

- Dataset mutation after save → fingerprint mismatch test.
- Changed factor parameters → definition mismatch test.
- Empty/non-positive prices and zero/negative horizons → fail-closed tests.
- Malformed JSON and path traversal IDs → storage validation tests.
- NaN/undefined metrics → JSON-safe round-trip test.

### Task 1: P4 governance and contracts

**Files:** `DEPENDENCY_PROPOSAL.md`, `docs/phases/P4_GATE_DESIGN.md`, `.agents/p4-*`, `docs/PROJECT_STATE.md`.

- [ ] Record that P4 adds no third-party dependency.
- [ ] Define P4 gate criteria, forbidden scope, and role responsibilities.

### Task 2: ResearchRun model and canonical serialization

**Files:** `src/finahinking/experiments/models.py`, `tests/experiments/test_models.py`.

- [ ] Write failing tests for required fields, dict/JSON round-trip, stable fingerprints, and invalid input.
- [ ] Implement immutable run model, canonical JSON, data/result fingerprints, and schema checks.

### Task 3: Experiment engine and local RunStore

**Files:** `src/finahinking/experiments/engine.py`, `src/finahinking/experiments/storage.py`, `src/finahinking/experiments/__init__.py`, `tests/experiments/test_engine.py`, `tests/experiments/test_storage.py`.

- [ ] Write failing tests for execution, save/load, reproduction, drift detection, malformed records, and unsafe IDs.
- [ ] Implement deterministic IC execution, atomic local JSON persistence, and reproduction comparison.

### Task 4: P4 documentation and independent gate

**Files:** `docs/phases/P4_GATE_REVIEW.md`, `docs/FINAHINKING_P4_COMPLETION_REPORT.md`, `EVOLUTION_LOG.md`, `README.md`, `docs/PROJECT_STATE.md`.

- [ ] Run full verification and an independent reviewer.
- [ ] Fix findings, record PASS, write completion report, and stop at human review.
