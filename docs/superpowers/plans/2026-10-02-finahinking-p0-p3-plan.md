# Finahinking P0–P3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify Finahinking's governed research foundation through P3, then stop for human review.

**Architecture:** A dependency-light Python package separates official data access, dataset validation, pure feature functions, and documented factor evaluation. Governance is represented as auditable Markdown gate records and project state.

**Tech Stack:** Python 3.11+, pandas, numpy, pytest, ruff, JupyterLab, ipykernel.

**Spec:** `docs/superpowers/specs/2026-10-02-finahinking-p0-p3-design.md`

## Global Constraints

- No P4 experiment persistence or ResearchRun implementation.
- No secrets, trading automation, investment advice, or unsafe network shortcuts.
- Every dependency must be recorded in `DEPENDENCY_RECORD.md`.
- Every phase requires gate design and independent gate review.
- Tests must cover edge cases and must not require live network access by default.

## Review Focus

- ECB schema drift or malformed responses → provider schema/fixture tests.
- Time-index ordering and duplicate timestamps → dataset validation tests.
- Look-ahead bias in momentum/returns → feature alignment tests.
- Constant/empty series and zero volatility → numerical edge-case tests.
- Missing provenance or undocumented factor limitations → metadata/documentation tests.

### Task 1: P0 Governance and repository foundation

**Files:** README.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, LICENSE, CHANGELOG.md, DEPENDENCY_RECORD.md, EVOLUTION_LOG.md, UPGRADE_PROPOSAL.md, ARCHITECTURE.md, docs/PROJECT_STATE.md, docs/phases/P0_GATE_DESIGN.md, .agents/*.md, scripts/validate_governance.py, tests/validation/test_governance.py.

- [ ] Write failing governance validation tests.
- [ ] Implement dependency-free validation and governance documents.
- [ ] Run focused then full validation; record P0 review as PASS.

### Task 2: P1 Research environment

**Files:** pyproject.toml, requirements.lock, Makefile, src/finahinking/__init__.py, notebooks/01_research_workflow.ipynb, research_workspace/README.md, docs/phases/P1_GATE_DESIGN.md, tests/test_environment.py.

- [ ] Write environment and import tests.
- [ ] Install declared dependencies in `.venv`, pin them, and implement the package skeleton.
- [ ] Add a deterministic notebook workflow and run the P1 gate review.

### Task 3: P2 Data engine

**Files:** src/finahinking/data/{models.py,providers.py,validation.py,__init__.py}, tests/data/*, fixtures/ecb/*.csv, DATA_SOURCE_EVALUATION.md, docs/phases/P2_GATE_DESIGN.md.

- [ ] Write fixture-backed tests for provider normalization, provenance, validation, and failures.
- [ ] Implement ECB provider, dataset model, allowlisted request handling, and validators.
- [ ] Run fixture tests plus opt-in live smoke test and record P2 PASS.

### Task 4: P3 Quant research engine

**Files:** src/finahinking/features/*, src/finahinking/factors/*, tests/features/*, tests/factors/*, docs/phases/P3_GATE_DESIGN.md.

- [ ] Write failing tests for returns, volatility, momentum, drawdown, correlation, factor evaluation, and limitations.
- [ ] Implement pure feature functions and documented factors with deterministic metrics.
- [ ] Run the complete suite, independent review, and record P3 PASS / waiting for human review.

