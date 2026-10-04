# Finahinking P7.5 + P8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a deterministic local-first Knowledge Engine and product shell, then prepare and verify the Finahinking open-source public beta.

**Architecture:** Typed knowledge content composes with existing P6.5/P6.6/P7 models. A standard-library local HTTP shell owns lifecycle and uses SQLite/fixtures; release artifacts and public documentation are versioned and CI-verifiable.

**Tech Stack:** Python 3.11+, SQLite, existing NumPy/Pandas engines, stdlib HTTP server, pytest, Ruff, Jupyter notebook checks, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-03-finahinking-p75-p8-design.md`

## Global Constraints

- P7 privacy/consent/provenance/deletion boundaries remain authoritative.
- SQLite is the default local runtime; PostgreSQL remains the advanced migration path.
- Sample/offline mode must work without credentials or outbound network.
- No real-money execution, broker integration, hosted accounts, or automatic cloud sync.
- Public-beta claims require fresh command output or a clearly documented conditional.

## Review Focus

- Deletion must remove thread metadata as well as nodes; regression test in P7 vertical slice.
- Knowledge prerequisite cycles and missing source labels must fail validation; tests in knowledge engine.
- Local HTTP errors must be actionable and must not leak secrets; tests in local app.
- Restart must preserve only owner-scoped state and consented projections; E2E restart test.
- Release docs must not imply an unpublished or unsigned asset exists; docs validation and clean-install report.

### Task 1: Restore P7 deletion invariant

**Files:** `src/finahinking/p7/repository.py`, `tests/p7/test_vertical_slices.py`, `docs/PROJECT_STATE.md`, `EVOLUTION_LOG.md`

- [x] Delete `p7_learning_threads` rows by owner in `delete_personal`.
- [x] Assert exported learning threads are empty after deletion.
- [ ] Re-run P7 focused tests and update evidence counts.

### Task 2: Implement typed Knowledge Engine

**Files:** `src/finahinking/p7_5/knowledge.py`, package exports, knowledge tests, P7.5 knowledge docs.

- [ ] Define immutable typed records for concepts, equations, derivations, code examples, interpretations, applications, misconceptions, source references, and paths.
- [ ] Seed the required 15-concept path with deterministic IDs and complete level 1–8 content.
- [ ] Implement prerequisite traversal, deterministic search, validation, and context links.
- [ ] Verify unit tests, Ruff, and docs contracts.

### Task 3: Implement supported local product shell

**Files:** `src/finahinking/p7_5/local_app.py`, `scripts/run_local_app.py`, tests, local-runtime/product docs.

- [ ] Add loopback HTTP server, SQLite initialization, fixture/sample labels, semantic navigation, and required API/UI routes.
- [ ] Wire event, quant, strategy, personal, and community summaries to existing modules without duplicating state.
- [ ] Add diagnostics, safe error responses, save/reopen, and restart behavior.
- [ ] Verify unit, HTTP, and E2E journey tests.

### Task 4: P7.5 gate evidence

**Files:** all `docs/p7_5/*` required by the mission, state/evolution docs, validation tests.

- [ ] Write capability matrix, architecture, information architecture, design/accessibility/performance/security reviews, E2E report, final validation, and P8 readiness.
- [ ] Run the 39-item P7.5 gate checklist and record command/output evidence.
- [ ] Confirm all ten independent audits A–J are explicit and pass/conditional.

### Task 5: Open-source public beta package

**Files:** root public docs, `docs/p8/*`, CI/release workflows, issue templates, validation tests.

- [ ] Add source-install quickstart/tutorials, contribution contracts, privacy/security/limitations, license/dependency inventory, and release plan.
- [ ] Add CI and release workflows with semver 0.x.y, checksums, clean-install, and secret/dependency scans.
- [ ] Record macOS packaging and GitHub publication as pass only when a real artifact is verified; otherwise state the exact conditional.

### Task 6: Final integration and P8 gate

- [ ] Run both Python environments' full suites and all existing P4–P7 gates.
- [ ] Run Ruff, notebook, governance, pip, migration, package/import, build smoke, diff, clean-worktree, and provenance checks.
- [ ] Reconcile `PROJECT_STATE.md`, `EVOLUTION_LOG.md`, final reports, and release commit/tag evidence.
- [ ] Stop after P8 Public Beta Gate; do not begin cloud sync, broker, or real-money work.

