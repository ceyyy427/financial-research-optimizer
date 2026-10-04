# Finathink P8.2 Capability Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a local-first, evidence-bound interactive research workspace with Finathink-owned contracts, optional isolated research engines, a read-only QMT boundary, and truthful P8.2 validation.

**Architecture:** Keep the Python server and domain contracts authoritative. Add a bounded normalized research payload and a locally bundled visualization controller; optional Qlib/vectorbt/QMT capabilities are adapters or sandboxes with explicit fallbacks. No browser component performs quantitative calculations.

**Tech Stack:** Python 3.11+, pandas/numpy, stdlib HTTP/SQLite, pytest/Ruff, npm-pinned Lightweight Charts and ECharts bundles, headless Node checks, optional isolated Python environments.

**Spec:** `docs/superpowers/specs/2026-10-03-finathink-p82-capability-expansion-design.md` and the user-supplied P8.2 mission attachment.

## Global Constraints

- Computer Use is forbidden for this mission.
- External tools are replaceable providers; Finathink contracts remain authoritative.
- Qlib/vectorbt are optional isolated sandboxes; core starts without them.
- QMT is market-data-only, read-only, localhost/trusted-LAN gated, and never stores broker credentials.
- Preserve PIT/OOS/provenance/fingerprints, cost assumptions, and multiple-testing metadata.
- No live orders, broker actions, investment instructions, or automatic “best strategy” selection.
- Use TDD for behavior changes and `apply_patch` for repository text edits.

## Review Focus

- A chart point must be traceable to one canonical dataset fingerprint and timestamp; test malformed/duplicate/out-of-order points.
- Optional engines must be absent-safe; test capability detection and fallback when imports are unavailable.
- QMT payloads must be read-only and credential-free; test forbidden trading method names and invalid bridge tokens.
- Browser interaction must not calculate domain metrics; test the normalized payload, selected-point table, and script CSP/asset allow-list.
- Parameter sweeps must expose experiment count and OOS/multiple-testing context; test deterministic ordering and no “best strategy” label.

---

### Task 1: Baseline, capability inventory, and reference evidence

**Files:**
- Create: `docs/p8_2/P8_2_EXECUTION_PLAN.md`
- Create: `docs/p8_2/P8_2_CAPABILITY_MATRIX.md`
- Create: `docs/p8_2/P8_2_DEPENDENCY_TOPOLOGY.md`
- Create: `docs/p8_2/TRADINGAGENTS_REFERENCE_REVIEW.md`
- Create: `docs/p8_2/TRADINGAGENTS_REFERENCE.md`
- Create: `docs/p8_2/QLIB_REFERENCE.md`
- Create: `docs/p8_2/VECTORBT_REFERENCE.md`
- Create: `docs/p8_2/EXTERNAL_QUANT_TOOL_MATRIX.md`

**Interfaces:** Records exact versions/licenses/environments and fallback decisions; no source import depends on these reports.

- [ ] Record the 161 discovered local skill packages, selected skills, permissions, and actual usage.
- [ ] Record TradingAgents findings and classify Qlib/vectorbt/QMT/visualization libraries A–E.
- [ ] Record package versions and licenses before installation; mark unverified items deferred.
- [ ] Verify no reference repository is copied into `src/`.

### Task 2: Finathink research contracts

**Files:**
- Create: `src/finahinking/p8_2/contracts.py`
- Create: `src/finahinking/p8_2/__init__.py`
- Test: `tests/p8_2/test_contracts.py`

**Interfaces:** `MarketObservation`, `DatasetSnapshot`, `ResearchPoint`, `FeatureObservation`, `ParameterSweepSpecification`, `SweepResult`, and `MLResearchSpecification` expose `to_dict()` and deterministic `fingerprint` properties.

- [ ] Write failing tests for validation, round-trip JSON, PIT availability, bounds, and fingerprint changes.
- [ ] Run the focused tests and observe the expected failures.
- [ ] Implement immutable dataclasses using existing `canonical_json`/digest conventions; reject executable payload keys and non-finite values.
- [ ] Run focused tests, then the full suite.

### Task 3: Capability registry, fixture data, and read-only QMT boundary

**Files:**
- Create: `src/finahinking/p8_2/capabilities.py`
- Create: `src/finahinking/p8_2/data_sources.py`
- Create: `src/finahinking/p8_2/qmt.py`
- Test: `tests/p8_2/test_capabilities_and_qmt.py`

**Interfaces:** `CapabilityRegistry.detect()`, `FixtureMarketDataSource.snapshot()`, `QMTConnectionState`, `QMTBridgeClient.status()`, and `QMTBridgeClient.snapshot()` return Finathink-owned records only.

- [ ] Write failing tests for optional import absence, QMT state transitions, token/host checks, credential rejection, and deterministic fixture provenance.
- [ ] Implement capability detection with import/version probes that never raise on optional absence.
- [ ] Implement fixture source and a mock QMT bridge; omit any order/account method and enforce bounded read-only requests.
- [ ] Verify tests and secret scan.

### Task 4: Parameter sweep and ML adapter boundaries

**Files:**
- Create: `src/finahinking/p8_2/sweeps.py`
- Create: `src/finahinking/p8_2/ml.py`
- Create: `src/finahinking/p8_2/adapters.py`
- Test: `tests/p8_2/test_sweeps_and_adapters.py`

**Interfaces:** `run_parameter_sweep(spec, evaluator) -> SweepResult`, `QlibResearchAdapter.available()`, and `QlibResearchAdapter.run(spec, dataset) -> MLResearchResult` (fallback/unsupported state when Qlib is absent).

- [ ] Write failing tests for deterministic grid enumeration, OOS labels, multiple-testing warnings, and no winner language.
- [ ] Implement an internal bounded sweep evaluator using Finathink contracts; record every experiment and robust/unstable regions.
- [ ] Implement a typed Qlib adapter seam and a deterministic baseline fallback without importing Qlib in core startup.
- [ ] Run focused and full tests.

### Task 5: Chart payload and research route

**Files:**
- Modify: `src/finahinking/local_app.py`
- Create: `src/finahinking/p8_2/research_view.py`
- Test: `tests/p8_2/test_research_view.py`

**Interfaces:** `build_research_payload()` returns the bounded chart schema from the spec; `GET /api/research/series` and `GET /research` expose normalized data and UI shell.

- [ ] Write failing tests for payload provenance, feature/event markers, route status, asset allow-list, and CSP.
- [ ] Implement the view-model from the fixture source; keep all calculations server-side and cap point counts.
- [ ] Add research navigation, selected-point table, inspector placeholders, capability cards, and parameter/ML links.
- [ ] Verify loopback routes and malformed query recovery.

### Task 6: Visualization bundle and interaction behavior

**Files:**
- Create: `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/research.js`, `frontend/build.mjs`
- Create: `site/assets/finathink-research.js`
- Create: `src/finahinking/_package_data/assets/finathink-research.js`
- Modify: `src/finahinking/local_app.py`, `site/index.html`
- Test: `tests/p8_2/test_chart_asset_contract.py`, `frontend/test/research.test.mjs`

**Interfaces:** Browser module mounts `[data-finathink-research]`, consumes `data-payload-url`, renders chart + accessible table, and dispatches `finathink:point-selected` with only a point ID.

- [ ] Pin and install only Lightweight Charts/ECharts in the isolated frontend workspace; record licenses and versions.
- [ ] Write failing headless DOM/module tests for mount, tooltip text, keyboard point selection, table fallback, and absent data.
- [ ] Implement the controller with local bundles, no remote fetches, no financial calculations, and reduced-motion-aware transitions.
- [ ] Build/copy the production bundle, verify CSP and asset hashes, and run headless tests.

### Task 7: P8.2 UI surfaces and settings

**Files:**
- Modify: `src/finahinking/local_app.py`
- Test: `tests/p8_2/test_p82_routes.py`

**Interfaces:** `/research`, `/ml`, `/parameter`, `/settings/engines`, `/settings/data-sources` are total HTML routes with explicit SAMPLE/NOT INSTALLED/READ-ONLY states.

- [ ] Add research density layout with chart, feature graph summary, inspector, history links, and progressive disclosure.
- [ ] Add ML Lab and Parameter Lab surfaces that show protocol/uncertainty/limitations and never claim automatic superiority.
- [ ] Add QMT settings/disconnect/data-health UI without credential or trading controls.
- [ ] Verify keyboard/focus, reduced motion, responsive layout, and empty/error states via parser and headless tests.

### Task 8: Isolated optional environment probes

**Files:**
- Create: `scripts/p8_2_probe_optional.py`
- Create: `docs/p8_2/QLIB_DEPENDENCY_REVIEW.md`
- Create: `docs/p8_2/QMT_INTEGRATION_REVIEW.md`
- Create: `docs/p8_2/P8_2_QLIB_ADAPTER.md`
- Create: `docs/p8_2/P8_2_VECTORBT_SANDBOX.md`

- [ ] Inspect Qlib/vectorbt compatibility and licenses before install.
- [ ] Create isolated environments only when the runtime supports the package; do not modify `.venv` or `.venv-quant`.
- [ ] Run import/sample/training/sweep smoke tests where install succeeds; otherwise record exact blocker and preserve fallback.
- [ ] Verify core app/test startup without optional environments.

### Task 9: Final audit and P8.2 report

**Files:**
- Create: `docs/p8_2/P8_2_VISUALIZATION_ARCHITECTURE.md`
- Create: `docs/p8_2/P8_2_RESEARCH_ENGINE_ARCHITECTURE.md`
- Create: `docs/p8_2/P8_2_DATA_SOURCE_ARCHITECTURE.md`
- Create: `docs/p8_2/P8_2_QMT_BRIDGE.md`
- Create: `docs/p8_2/P8_2_UI_INTERACTION_STANDARD.md`
- Create: `docs/p8_2/P8_2_PERFORMANCE_REVIEW.md`
- Create: `docs/p8_2/P8_2_SECURITY_REVIEW.md`
- Create: `docs/p8_2/P8_2_FINAL_VALIDATION_REPORT.md`

- [ ] Run full tests, adapter/UI/headless tests, Ruff, governance, notebook, pip checks, dependency audit, clean install, and diff checks.
- [ ] Measure chart payload/render interaction with 1k and 10k point synthetic inputs; record actual results and limitations.
- [ ] Audit CSP, generated code, optional dependency boundaries, QMT credentials/method surface, and provenance/PIT/OOS validity.
- [ ] Record final local commit/worktree and all remaining external blockers.
- [ ] Stop P8.2 here; do not begin P8.2B until the user reviews the final report.
