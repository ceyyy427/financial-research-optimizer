# Finathink Factor–Strategy Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the deterministic factor–strategy–position–risk workbench from the 2026-10-05 design and export an offline HTML report that feels like a deliberate research publication rather than a raw model dump.

**Architecture:** Keep factor signals, position policies, risk state, execution, faults, explanations, and rendering as separate JSON-safe immutable boundaries. The deterministic engine produces a single auditable workbench payload; the browser only renders server-owned values and links selections across panels. Reports are self-contained HTML files with no network, model, broker, or arbitrary-code dependency.

**Tech Stack:** Python 3.11+, frozen dataclasses, existing P6.6/P8.2 contracts, stdlib HTML escaping/SVG, ECharts/lightweight-charts only for the existing interactive workspace, Node 20 frontend tests.

**Spec:** `docs/superpowers/specs/2026-10-05-finathink-factor-strategy-workbench-design.md`

## Global Constraints

- The product boundary is research, learning, backtesting, OOS, paper simulation, and export; it does not connect to real funds, brokers, or automatic trading.
- The browser never recalculates prices, factors, positions, risk, or backtest metrics; it renders normalized server/local-engine payloads.
- Model output, if present later, can only become a validated structured proposal; this phase uses the local deterministic workflow and does not require user API keys.
- OOS/test data is not used for parameter tuning; no output may call a result a “best strategy” or promise future returns.
- Every public contract is JSON-safe, fingerprinted, immutable at the boundary, and rejects secrets, paths, callables, arbitrary code, and non-finite numbers.
- Existing P6.6/P5/P5.5/paper-only and research-agent tests must remain green.

## Review Focus

- Invalid position weights or exposure overflow must be rejected or projected deterministically — covered by Task 2 contract/engine tests.
- Risk transitions need hysteresis, minimum duration, and allow-listed actions — covered by Task 2 state-machine tests.
- Missing/stale data and excessive slippage must produce a recorded fault action, never a silent fill — covered by Task 2 fault tests.
- Multiple changed parameters must be labelled `ATTRIBUTION_CONFOUNDED`, not presented as causal — covered by Task 3 explanation tests.
- HTML and JSON exports must scrub secrets/absolute paths and remain usable offline with a keyboard/table fallback — covered by Tasks 4–6 export/UI tests.

---

### Task 1: Workbench contracts and research charter

**Files:**
- Create: `src/finahinking/p6_6/workbench.py`
- Modify: `src/finahinking/p6_6/__init__.py`
- Test: `tests/p6_6/test_workbench_contracts.py`

**Interfaces:**
- Consumes: existing `p6_6.models.digest` conventions and JSON-safe contract style.
- Produces: `PositionPolicySpec`, `RiskStatePolicy`, `ExecutionPolicy`, `FaultPolicy`, `ResearchCharter`, `PolicyProposal`, `ParameterChangeExplanation` data types with `to_dict()` and `fingerprint` properties.

- [ ] Write failing tests for immutable policy fields, allow-listed actions, frozen charter/test boundary, proposal diff limits, and stable fingerprints.
- [ ] Run `python3 -m pytest tests/p6_6/test_workbench_contracts.py -q` and observe the missing-contract failure.
- [ ] Implement the frozen contracts with finite-value, identifier, secret/path/callable, and hard-boundary validation.
- [ ] Re-run focused tests, then `python3 -m pytest tests/p6_6/test_workbench_contracts.py -q`.
- [ ] Commit `feat(workbench): add factor strategy policy contracts`.

### Task 2: Deterministic position, risk, execution, and fault engine

**Files:**
- Create: `src/finahinking/p6_6/workbench_engine.py`
- Modify: `src/finahinking/p6_6/__init__.py`
- Test: `tests/p6_6/test_workbench_engine.py`

**Interfaces:**
- Consumes: Task 1 policy contracts and point-in-time factor observations.
- Produces: `WorkbenchPoint`, `WorkbenchRun`, `run_workbench()` and deterministic transitions `NORMAL → CAUTION → DEFENSIVE → FREEZE/FLATTEN → RECOVERY`.

- [ ] Write failing tests for equal/rank/inverse-volatility/risk-budget mapping, volatility scaling, long-only projection, turnover/cash/liquidity limits, risk transitions, and fault actions.
- [ ] Run the focused test file and observe missing engine behavior.
- [ ] Implement the engine as pure functions; keep factor score generation separate from target weight policy and execution/fault recording.
- [ ] Re-run focused tests and ensure repeated runs have identical payload fingerprints.
- [ ] Commit `feat(workbench): add deterministic portfolio policy engine`.

### Task 3: Algorithm trace, paired replay, and learning explanation package

**Files:**
- Modify: `src/finahinking/p6_6/workbench.py`
- Create: `src/finahinking/p6_6/workbench_explanations.py`
- Test: `tests/p6_6/test_workbench_explanations.py`

**Interfaces:**
- Consumes: `WorkbenchRun`, a baseline/variant parameter mapping, and existing `StrategyLearningTrace` conventions.
- Produces: nine-block trace records, paired metric attribution, `ParameterChangeExplanation`, and `build_explanation_package()`.

- [ ] Write failing tests for nine required sections, single-parameter paired attribution, multi-parameter confounding, and limitation/next-experiment fields.
- [ ] Run the focused file and observe failure.
- [ ] Implement explanation generation from engine-owned intermediate values; never infer causality from prose.
- [ ] Re-run focused tests and verify all fields serialize without secrets or executable source.
- [ ] Commit `feat(workbench): add algorithm explanation packages`.

### Task 4: Canonical workbench payload and offline report renderer

**Files:**
- Modify: `src/finahinking/p8_2/research_view.py`
- Modify: `src/finahinking/research/reports.py`
- Modify: `src/finahinking/research/ui.py`
- Test: `tests/p8_2/test_workbench_payload.py`
- Test: `tests/research/test_reports.py`

**Interfaces:**
- Consumes: `WorkbenchRun`, explanation package, existing dataset snapshot and report manifest.
- Produces: payload sections `factor_observations`, `signals`, `raw_weights`, `risk_scales`, `final_weights`, `exposure`, `cash`, `risk_states`, `trades`, `costs`, `slippage`, `fault_events`, `explanation_refs`, `baseline_variant_refs`; a self-contained polished report.

- [ ] Write failing tests for payload provenance, cross-section identity, report section headings, inline SVG/accessible tables, and offline/no-script rendering.
- [ ] Run focused tests and observe the old raw-JSON report behavior.
- [ ] Implement normalized payload assembly and a publication-style HTML template: evidence-led opening, asymmetric grid, restrained mineral palette, clear “historical/paper-only” boundary, inline SVG timeline, readable tables, and explicit limitations.
- [ ] Re-run focused tests and bundle verification; ensure report HTML does not contain secrets, absolute paths, CDN URLs, or generic “AI-generated” copy.
- [ ] Commit `feat(reports): render factor strategy workbench reports`.

### Task 5: Interactive research workspace linkage

**Files:**
- Modify: `frontend/src/research.js`
- Modify: `frontend/test/research.test.mjs`
- Modify: `src/finahinking/local_app.py`
- Test: `tests/research/test_ui.py`

**Interfaces:**
- Consumes: Task 4 normalized workbench payload.
- Produces: accessible workbench panels with point selection, table fallback, parameter preview state, and report links; no client-side financial recomputation.

- [ ] Write failing Node/Python tests for payload normalization, selected-point propagation, preview-is-not-saved semantics, and read-only workbench route.
- [ ] Run focused frontend/backend tests and observe missing workbench behavior.
- [ ] Implement render-only layers, using text/table fallbacks for every chart fact and `prefers-reduced-motion` compliance.
- [ ] Re-run focused frontend/backend tests and verify old research/knowledge journeys still work.
- [ ] Commit `feat(ui): add linked factor strategy workbench view`.

### Task 6: Product shell and launch/report presentation pass

**Files:**
- Modify: `src/finahinking/local_app.py`
- Modify: `site/index.html`
- Modify: `frontend/build.mjs` if required by the bundled asset path
- Test: `tests/research/test_ui.py`
- Test: `frontend/test/research.test.mjs`

**Interfaces:**
- Consumes: report renderer and workbench payload from Tasks 4–5.
- Produces: `/workbench` entry point, consistent research navigation, and a first-screen narrative that leads with the research question and evidence chain.

- [ ] Write failing tests for the workbench link, report boundary copy, responsive shell classes, and no-network CSP.
- [ ] Run focused tests and observe missing route/presentation behavior.
- [ ] Implement the final copy and style tokens without adding a new runtime dependency; preserve keyboard focus, reduced motion, and mobile layout.
- [ ] Run browser-facing tests/build and inspect generated HTML/CSS for CSP and asset-path correctness.
- [ ] Commit `feat(ui): polish research launch and workbench shell`.

### Task 7: Documentation, release evidence, and final verification

**Files:**
- Create: `docs/FACTOR_STRATEGY_WORKBENCH_GUIDE.md`
- Create: `docs/FACTOR_STRATEGY_WORKBENCH_VALIDATION.md`
- Modify: `README.md`
- Modify: `README_CN.md` if present in the target branch
- Test: `tests/validation/test_workbench_docs.py`

**Interfaces:**
- Consumes: all completed contracts, payloads, report examples, and test outputs.
- Produces: user-facing implementation guide, explicit out-of-scope statement, and release evidence.

- [ ] Write failing documentation tests for phase coverage, paper-only boundary, API-key exclusion, and report entry points.
- [ ] Run focused docs tests and observe missing documents.
- [ ] Write the guide and validation report with completed/limited/unverified distinctions.
- [ ] Run `python3 -m ruff check src tests`, `python3 -m compileall -q src tests`, `python3 -m pytest -q`, `npm test`, `npm run build`, and `git diff --check`.
- [ ] Commit `docs(workbench): document implementation and validation`.

## Execution Notes

The implementation is deliberately offline-first. Dependencies may be obtained from official sources when needed and reviewed for license, safety, reproducibility, and compatibility; downloaded reference code is not automatically executed or admitted as a runtime dependency. User instruction controls this scope and authorizes GitHub publication after validation, without enabling paid APIs or real trading.

### Task 8: Controlled factor graph and bounded research history

**Files:**
- Create: `src/finahinking/p6_6/workbench_factors.py`
- Create: `src/finahinking/p6_6/workbench_research.py`
- Test: `tests/p6_6/test_workbench_research.py`

**Interfaces:**
- Consumes: policy contracts, engine, and explanation packages.
- Produces: `FactorGraphSpec`, `evaluate_factor_graph()`, `ResearchSession`, and content-addressed `WorkbenchStore`; frozen-test, all-attempt retention, and explicit freeze/evaluate boundaries.

- [ ] Write and watch failing tests for graph cycles/unknown primitives/PIT, immutable history, experiment budget, no test access before explicit freeze, once-only test evaluation, invalid proposal/hard-limit changes, and version reopen/rollback.
- [ ] Implement bounded primitives and the deterministic train/validation research loop, with failed attempts archived and no best-strategy label.
- [ ] Wire these contracts into the payload/UI before the final release gate.
- [ ] Run the focused tests, full regression, and serialization checks.
- [ ] Commit `feat(workbench): retain bounded research and factor history`.

Task 8 is executed after Task 3 and before Tasks 4–7; it covers design sections 14–16 missing from the first plan pass. Repository credential connections and external model calls remain deferred at the user's direction.
