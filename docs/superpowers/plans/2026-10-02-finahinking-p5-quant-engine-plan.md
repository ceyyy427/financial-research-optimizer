# Finathink P5 Quant Engine Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a reproducible, research-only P5 quant runtime on top of the frozen P4 ResearchRun boundary.

**Architecture:** Use domain-only contracts for strategies, intents, ledger results, evaluation reports, artifacts, and QuantRun. Keep the backtest engine and metrics in-house with NumPy/Pandas; reserve an adapter package for optional third-party tools and document all admission decisions without adding a runtime dependency.

**Tech Stack:** Python 3.11+, existing NumPy/Pandas, pytest, Ruff, canonical JSON, SHA-256 fingerprints, offline CSV fixtures.

**Spec:** `docs/superpowers/specs/2026-10-02-finahinking-p5-quant-engine-design.md`

## Global Constraints

- P4 `ResearchRun`, artifact fingerprints, provenance, temporal integrity, and governance contracts remain additive and backward-compatible.
- P5 is historical research only: no broker API, live trading, order routing, automatic investment advice, trading agent, or black-box prediction model.
- Every external library, if later admitted, must be isolated behind `quant/adapters/`; no domain module imports a third-party quant object.
- No dependency is installed blindly; this implementation uses no new runtime dependency and records candidate review evidence.
- Every run records dataset version, strategy version, engine version, parameters, costs, slippage, benchmark, timestamp, artifact fingerprint, and ResearchRun linkage.
- Tests and default workflows are offline and deterministic.

## Review Focus

- Same-bar/look-ahead execution: a signal at `t` must execute no earlier than `t+1`; test with a deliberately changing signal.
- Cash conservation and costs: fees and slippage must reduce equity exactly; test ledger arithmetic and negative-cash policy.
- Degenerate metrics: constant, empty, one-point, zero-volatility, and all-loss series return `None` where undefined rather than NaN claims.
- Serialization/security: unsafe IDs, malformed artifacts, non-finite values, and executable-looking payloads are rejected.
- Provenance/replay: the same fixture and parameters produce identical trade, evaluation, artifact, and QuantRun fingerprints twice.

---

### Task 1: Record P5 admission and phase design

**Files:**
- Create: `docs/p5/COMPONENT_ADMISSION_MATRIX.md`
- Create: `docs/p5/DEPENDENCY_PLAN.md`
- Create: `docs/phases/P5_GATE_REVIEW.md`
- Modify: `docs/PROJECT_STATE.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: P4.5 audit documents and the user-supplied component list.
- Produces: documented classifications, license/security/maintenance review, no-install decision, and P5 gate checklist.

- [x] **Step 1: Write the failing documentation checks**
  Add tests that require all P5 candidate sections, classification labels, no-install policy, and P5 phase markers.
- [x] **Step 2: Run the documentation checks and verify they fail**
  Run `pytest tests/validation/test_p5_docs.py -q`; expect missing-file/marker failures.
- [x] **Step 3: Write the admission matrix, dependency plan, and gate review**
  Include repository URLs, license observations, Python/macOS arm64 compatibility risks, maintenance/security notes, and A/B/C/D decisions. Choose the in-house engine as the only P5 core runtime and mark external candidates optional/reference/rejected.
- [x] **Step 4: Update authoritative phase state**
  Set P5 Quant Engine Foundation as current, retain P0–P4 and P4.5 PASS, state that P6 is out of scope, and link the new documents.
- [x] **Step 5: Run documentation checks**
  Run `pytest tests/validation/test_p5_docs.py -q` and `python3 scripts/validate_governance.py`; expect PASS.
- [x] **Step 6: Commit**
  `git add docs tests/validation && git commit -m "docs: admit P5 quant components"`

### Task 2: Add domain contracts and safe artifacts

**Files:**
- Create: `src/finahinking/quant/__init__.py`
- Create: `src/finahinking/quant/interfaces.py`
- Create: `src/finahinking/quant/artifacts.py`
- Test: `tests/quant/test_contracts.py`, `tests/quant/test_artifacts.py`

**Interfaces:**
- Consumes: `Dataset`, frozen `ResearchRun`, canonical JSON helpers.
- Produces: `Strategy`, `StrategyIntent`, `BacktestConfig`, `Trade`, `BacktestResult`, `EvaluationReport`, `Artifact`, and `QuantRun`.

- [x] **Step 1: Write failing contract tests**
  Assert validation of weights, timestamps, fees, slippage, safe identifiers, schema versions, canonical fingerprints, and `QuantRun` round trips.
- [x] **Step 2: Run the tests and verify the expected missing-symbol failures**
  Run `pytest tests/quant/test_contracts.py tests/quant/test_artifacts.py -q`; expect collection failures because the contracts do not exist.
- [x] **Step 3: Implement minimal domain-only dataclasses and protocols**
  Keep all fields serializable and reject non-finite or unsafe values. Ensure no module imports an optional external quant library.
- [x] **Step 4: Run contract tests**
  Expect all contract and artifact tests to pass.
- [x] **Step 5: Commit**
  `git add src/finahinking/quant tests/quant && git commit -m "feat: add P5 quant contracts"`

### Task 3: Implement the deterministic backtest engine

**Files:**
- Create: `src/finahinking/quant/engines/__init__.py`
- Create: `src/finahinking/quant/engines/backtest.py`
- Create: `tests/quant/test_backtest_engine.py`

**Interfaces:**
- Consumes: `Dataset`, `Strategy`, `BacktestConfig`, `StrategyIntent`.
- Produces: `BacktestResult` with trades, positions, equity, returns, and fingerprints.

- [x] **Step 1: Write failing temporal and ledger tests**
  Test one-period signal shifting, target-weight rebalance, explicit fees/slippage, cash conservation, monotonic trades, negative-cash rejection, and deterministic fingerprints.
- [x] **Step 2: Run the focused tests and verify they fail**
  Run `pytest tests/quant/test_backtest_engine.py -q`; expect missing engine symbols.
- [x] **Step 3: Implement the in-house engine**
  Iterate normalized dates, execute prior-date target weights at current close adjusted by explicit slippage, debit fees, maintain cash/position/equity ledgers, and serialize only data.
- [x] **Step 4: Run focused and full tests**
  Run `pytest tests/quant/test_backtest_engine.py -q` then `pytest -q`; expect PASS.
- [x] **Step 5: Commit**
  `git add src/finahinking/quant/engines tests/quant/test_backtest_engine.py && git commit -m "feat: add deterministic quant backtest engine"`

### Task 4: Add evaluation and risk metrics

**Files:**
- Create: `src/finahinking/quant/evaluation/__init__.py`
- Create: `src/finahinking/quant/evaluation/metrics.py`
- Create: `src/finahinking/quant/risk/__init__.py`
- Create: `src/finahinking/quant/risk/metrics.py`
- Test: `tests/quant/test_evaluation.py`, `tests/quant/test_risk.py`

**Interfaces:**
- Consumes: `BacktestResult`, benchmark returns, annualization factor.
- Produces: `EvaluationReport` with descriptive return/risk/cost/turnover metrics and fingerprints.

- [x] **Step 1: Write failing evaluation/risk tests**
  Cover total/annualized return, volatility, Sharpe, Sortino, drawdown, CVaR, turnover, benchmark comparison, and degenerate series.
- [x] **Step 2: Run focused tests and verify they fail**
  Run `pytest tests/quant/test_evaluation.py tests/quant/test_risk.py -q`; expect missing functions.
- [x] **Step 3: Implement pure deterministic metrics**
  Return `None` for undefined values, use explicit annualization, and retain descriptive/non-advisory limitations.
- [x] **Step 4: Run focused and full tests**
  Run `pytest tests/quant/test_evaluation.py tests/quant/test_risk.py -q` and `pytest -q`.
- [x] **Step 5: Commit**
  `git add src/finahinking/quant/evaluation src/finahinking/quant/risk tests/quant/test_evaluation.py tests/quant/test_risk.py && git commit -m "feat: add quant evaluation and risk metrics"`

### Task 5: Add portfolio helpers and ResearchRun vertical slice

**Files:**
- Create: `src/finahinking/quant/portfolio/__init__.py`
- Create: `src/finahinking/quant/portfolio/allocation.py`
- Create: `src/finahinking/quant/runtime.py`
- Create: `fixtures/p5/quant_vertical_slice.csv`
- Test: `tests/quant/test_vertical_slice.py`, `tests/quant/test_portfolio.py`

**Interfaces:**
- Consumes: P5 contracts, backtest engine, evaluation metrics, P4 `ResearchRun.create` and `RunStore`.
- Produces: target-weight allocation validation, `QuantRun` creation linked to a `ResearchRun`, deterministic artifact and provenance chain.

- [x] **Step 1: Write failing portfolio and vertical-slice tests**
  Assert allocation sums/limits, full Dataset -> Factor -> Strategy -> Backtest -> Evaluation -> Artifact -> ResearchRun -> QuantRun flow, repeated fingerprints, and no investment-advice wording.
- [x] **Step 2: Run focused tests and verify they fail**
  Run `pytest tests/quant/test_portfolio.py tests/quant/test_vertical_slice.py -q`; expect missing runtime symbols/fixture.
- [x] **Step 3: Implement portfolio helper and runtime orchestration**
  Use an explicit long-only target-weight strategy for the fixture; create a P4-compatible ResearchRun whose result contains only normalized descriptive evidence and links the artifact fingerprint.
- [x] **Step 4: Run focused and full tests**
  Run focused tests, then `pytest -q`, `ruff check src tests scripts`, and `make notebook-check`.
- [x] **Step 5: Commit**
  `git add src/finahinking/quant/portfolio src/finahinking/quant/runtime.py fixtures/p5 tests/quant && git commit -m "feat: add P5 quant vertical slice"`

### Task 6: Add adapter seams and final gate evidence

**Files:**
- Create: `src/finahinking/quant/adapters/__init__.py`
- Create: `src/finahinking/quant/adapters/statsmodels_adapter.py`
- Create: `docs/p5/ADAPTER_ARCHITECTURE.md`
- Create: `docs/reviews/P5_FINAL_VALIDATION_REPORT.md`
- Modify: `docs/PROJECT_STATE.md`, `CHANGELOG.md`, `README.md`
- Test: `tests/quant/test_adapters.py`, `tests/validation/test_p5_gate.py`

**Interfaces:**
- Consumes: domain contracts and admission matrix.
- Produces: an optional, lazy adapter seam with no core import dependency; P5 gate report and final status.

- [x] **Step 1: Write failing adapter and gate tests**
  Assert importing core modules never imports optional libraries, adapter absence is reported clearly, all forbidden scope strings are absent from source, and the gate report links each acceptance criterion.
- [x] **Step 2: Run focused tests and verify they fail**
  Run `pytest tests/quant/test_adapters.py tests/validation/test_p5_gate.py -q`; expect missing adapter/report markers.
- [x] **Step 3: Implement lazy adapter seam and gate report**
  The statsmodels adapter must raise a clear optional-dependency error if unavailable; it may never return a third-party model object as a domain value. Record that no adapter package is installed in this gate.
- [x] **Step 4: Run the complete P5 gate**
  Run `python3 scripts/validate_governance.py`, `pytest -q`, `.venv/bin/ruff check src tests scripts`, `make p1-gate`, `.venv/bin/pip check`, forbidden import/package scans, and `git diff --check`.
- [x] **Step 5: Request independent review and resolve findings**
  Review architecture, correctness, security, dependency admission, temporal integrity, and research validity. Fix all Critical/Important findings and rerun the gate.
- [x] **Step 6: Commit and stop at P5**
  `git add . && git commit -m "feat: complete P5 quant engine foundation"`; update state to P5 Gate Review PASS and explicitly keep P6 out of scope.

## Execution status

All six tasks and their verification steps are complete. The independent final
review findings were resolved before the final gate, and the repository stops at
P5 with P6 waiting for human approval.
