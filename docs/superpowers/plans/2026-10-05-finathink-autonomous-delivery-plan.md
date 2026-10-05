# Finathink Autonomous Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a complete, local-first, paper-only Finathink research slice that can discover and evaluate bounded factor candidates, feed them into strategy/risk research, expose safe provider configuration status, and publish auditable HTML artifacts.

**Architecture:** Add a Finathink-native factor DSL and deterministic evaluator beside the existing factor registry. Add a bounded factor research loop that respects ResearchCharter freeze/test rules, then connect its artifacts to the existing multi-role orchestrator, provider boundary, workbench payload, and report renderer. External GitHub repositories remain isolated references; no external runtime dependency is admitted by this plan.

**Tech Stack:** Python 3.11+, frozen dataclasses, pandas/numpy already in the project, stdlib AST/HTML/JSON/SHA-256, existing pytest/ruff, existing Node frontend bundle and tests.

**Spec:** `docs/superpowers/specs/2026-10-05-finathink-factor-strategy-workbench-design.md` and `docs/FINATHINK_AUTONOMOUS_EXECUTION_REPORT.md`

## Global Constraints

- Research, learning, backtesting, OOS, paper simulation, and export only; no live broker, real-money execution, account management, or investment advice.
- Browser and model providers never recalculate or decide financial values; the deterministic local engine owns calculations and provenance.
- Factor expressions use an allow-listed DSL; no arbitrary `eval`, Python source, shell, SQL, URL, file path, callable, or broker operation.
- test/OOS data is inaccessible before explicit freeze; all attempts remain append-only; no “best strategy” label.
- API keys are never accepted into contracts, logs, prompts, reports, checkpoints, or exported artifacts; only non-secret credential references and configured/unconfigured status are visible.
- External GitHub code is reference-only and remains outside the repository runtime and dependency lock.
- Existing tests and public contracts remain compatible; every new public contract is JSON-safe, fingerprinted, immutable at the boundary, and bounded in size.

## Review Focus

- Malformed or adversarial factor expressions must reject before calculation — Task 1 parser/AST tests.
- Future leakage, missing data, constant factors, and too-small samples must produce explicit evaluation status — Task 2 evaluator tests.
- Candidate loops must not read test/OOS before freeze and must retain rejected attempts — Task 3 research-loop tests.
- Provider configuration must expose only readiness metadata and never a key value — Task 4 provider/UI tests.
- Reports and UI must preserve factor evidence, limitations, and paper-only language without network assets — Task 5 export/UI tests.

---

### Task 0: Execution report, reference inventory, and baseline ledger

**Files:**
- Create: `docs/FINATHINK_AUTONOMOUS_EXECUTION_REPORT.md`
- Create: `docs/superpowers/plans/2026-10-05-finathink-autonomous-delivery-plan.md`
- Modify: `docs/PROJECT_STATE.md`
- Test: `tests/validation/test_execution_report.py`

**Interfaces:**
- Consumes: approved workbench design, research-agent contracts, and `docs/GITHUB_REFERENCE_CATALOG.md`.
- Produces: a checked-in execution scope, stage gates, stop conditions, and a baseline record.

- [x] Write the execution report and this plan with the product boundary, current baseline, reference projects, stages, risks, and stop conditions.
- [x] Run `python3 -m pytest -q` and record the observed baseline.
- [ ] Add documentation tests for the required boundary phrases, plan link, and explicit deferred provider/live-trading scope.
- [ ] Run the focused documentation test and commit `docs: add autonomous delivery execution report`.

### Task 1: Safe Factor DSL and candidate generator

**Files:**
- Create: `src/finahinking/factors/dsl.py`
- Create: `src/finahinking/factors/mining.py`
- Modify: `src/finahinking/factors/__init__.py`
- Test: `tests/research/test_factor_dsl.py`

**Interfaces:**
- Produces `FactorExpression(expression: str, fields: tuple[str, ...], operators: tuple[str, ...], fingerprint: str)` with `parse_factor_expression(text, allowed_fields, allowed_operators) -> FactorExpression`.
- Produces `FactorCandidate(candidate_id, expression, hypothesis, source, metadata)` and `generate_candidates(hypothesis, field_catalog, operator_catalog, limits) -> tuple[FactorCandidate, ...]`.
- Produces `evaluate_expression(expression, frame, as_of, available_at) -> pandas.Series` using only registered operators: `return`, `lag`, `rolling_mean`, `rolling_std`, `zscore`, `rank`, `winsorize`, `combine`, and `negate`.

- [ ] Write failing tests for valid nested expressions, stable canonical fingerprints, unknown fields/operators, malformed syntax, oversized windows, `eval`/Python injection, URL/path/callable input, and deterministic candidate ordering.
- [ ] Run `python3 -m pytest -q tests/research/test_factor_dsl.py` and observe the missing-contract failure.
- [ ] Implement a small parser using Python `ast` only for the declared expression grammar; reject every node outside the allow-list and never call Python `eval`.
- [ ] Implement bounded candidate templates for momentum, mean reversion, volatility, volume anomaly, and residual-style hypotheses; each candidate must include its data fields, direction, and limitations.
- [ ] Re-run the focused tests and commit `feat(factors): add safe factor expression and candidate mining`.

### Task 2: Factor evaluation, decay, and admission evidence

**Files:**
- Create: `src/finahinking/factors/evaluation.py`
- Modify: `src/finahinking/factors/registry.py`
- Modify: `src/finahinking/factors/__init__.py`
- Test: `tests/research/test_factor_evaluation.py`
- Test: `tests/research/test_factor_registry.py`

**Interfaces:**
- Produces `FactorEvaluation` with sample size, coverage, IC, ICIR, quantile returns, long-short return, turnover, transaction cost, decay profile, OOS status, warnings, and provenance.
- Produces `evaluate_factor_candidate(candidate, frame, forward_return, spec) -> FactorEvaluation` and `build_factor_admission(evaluation, spec) -> FactorAdmissionDecision`.
- Extends `FactorRegistry` with append-only candidate admission/rejection records without changing existing `FactorDefinition` or `evaluate_factor` behavior.

- [ ] Write failing tests for T+1 alignment, point-in-time availability, constant/empty samples, quantile ordering, IC/ICIR, turnover/cost, multi-horizon decay, train/validation/OOS split, and rejection reasons.
- [ ] Run the focused tests and observe missing evaluation behavior.
- [ ] Implement deterministic statistics with explicit `INSUFFICIENT_DATA`, `LEAKAGE_BLOCKED`, `UNSTABLE`, `REJECTED`, and `ADMITTED` statuses; never select solely on in-sample return.
- [ ] Preserve all candidate attempts and evidence references in registry history; do not overwrite old health or evaluation records.
- [ ] Re-run focused tests plus `tests/quant` and commit `feat(factors): add auditable evaluation and admission evidence`.

### Task 3: Bounded factor research loop and multi-agent handoff

**Files:**
- Create: `src/finahinking/research/factor_loop.py`
- Modify: `src/finahinking/research/contracts.py`
- Modify: `src/finahinking/research/workflow.py`
- Modify: `src/finahinking/research/__init__.py`
- Test: `tests/research/test_factor_loop.py`
- Test: `tests/research/test_workflow.py`

**Interfaces:**
- Produces `FactorResearchRound`, `FactorResearchRun`, and `run_factor_research(charter, candidates, dataset, limits) -> FactorResearchRun`.
- The loop has explicit states `CHARTER_FROZEN`, `CANDIDATE_GENERATED`, `TRAIN_EVALUATED`, `VALIDATION_EVALUATED`, `CANDIDATE_POOL`, `REJECTED`, `STRATEGY_FROZEN`, `TEST_EVALUATED`, and `RESEARCH_REVIEW`.
- Adds a `factor`/`learning` analyst handoff that returns structured hypotheses and evidence refs; risk and portfolio managers remain deterministic gates around the paper decision.

- [ ] Write failing tests for candidate ordering, budget exhaustion, rejected-attempt retention, freeze-before-test, once-only test evaluation, rollback to a frozen version, optional analyst failure, and core risk failure blocking paper decisions.
- [ ] Run focused tests and observe missing loop behavior.
- [ ] Implement the loop as a bounded pure coordinator over Task 1/2 outputs; no model call or arbitrary tool call can bypass the charter.
- [ ] Extend the default analyst set without making external providers mandatory; offline runs remain deterministic and complete.
- [ ] Re-run focused workflow tests and commit `feat(research): add bounded factor research loop`.

### Task 4: Provider readiness and API-key reference boundary

**Files:**
- Modify: `src/finahinking/research/providers.py`
- Create: `src/finahinking/research/provider_status.py`
- Modify: `src/finahinking/research/__init__.py`
- Modify: `src/finahinking/local_app.py`
- Test: `tests/research/test_provider_status.py`
- Test: `tests/research/test_ui.py`

**Interfaces:**
- Produces `ProviderCredentialRef(provider, env_var, keychain_label)` and `ProviderStatus(provider, model, enabled, configured, capabilities, reason)`; neither type may contain a secret value.
- Produces `provider_status_payload(config, environment) -> dict` and read-only `GET /api/research/providers`.
- The UI may show a local “configured/unconfigured” state and model/role mapping; it must not accept, echo, persist, or export raw keys.

- [ ] Write failing tests for environment-variable presence without value exposure, missing key references, unsupported provider fields, role-model mapping, and POST/GET mutation rejection.
- [ ] Run focused provider/UI tests and observe the missing status boundary.
- [ ] Implement status-only resolution; preserve `OfflineDriver`, `CodexInteractiveDriver`, and explicit `UserApiDriver` semantics with no SDK installation.
- [ ] Add a settings panel/link that explains how a future user can configure a local provider reference while retaining the offline fallback.
- [ ] Re-run focused tests and commit `feat(research): expose secret-free provider readiness status`.

### Task 5: Factor evidence in workbench payload and offline HTML

**Files:**
- Modify: `src/finahinking/p8_2/research_view.py`
- Modify: `src/finahinking/research/reports.py`
- Modify: `src/finahinking/local_app.py`
- Modify: `frontend/src/research.js`
- Test: `tests/research/test_factor_report.py`
- Test: `frontend/test/research.test.mjs`

**Interfaces:**
- Adds normalized payload sections `factor_candidates`, `factor_evaluations`, `factor_decay`, `factor_admission`, `research_rounds`, and `provider_status`.
- Adds a read-only factor research panel with a keyboard/table fallback; the browser renders server-owned values and never recomputes statistics.
- HTML includes an evidence-led opening, candidate/admission table, limitations, provenance and paper-only boundary, with no CDN/network dependency.

- [ ] Write failing tests for payload fingerprints, rejected candidates, decay rows, provider redaction, HTML escaping, offline asset checks, and keyboard selection.
- [ ] Run focused backend/frontend tests and observe missing factor sections.
- [ ] Implement payload/report/UI linkage using existing workbench styles and report writer; preserve all prior routes.
- [ ] Re-run focused tests and commit `feat(research): surface factor mining evidence in workbench`.

### Task 6: Full verification, documentation, and GitHub release evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/PROJECT_STATE.md`
- Modify: `docs/FACTOR_STRATEGY_WORKBENCH_GUIDE.md`
- Modify: `docs/RESEARCH_AGENT_GUIDE.md`
- Modify: `CHANGELOG.md`
- Create: `docs/FINATHINK_AUTONOMOUS_VALIDATION.md`
- Test: `tests/validation/test_autonomous_delivery_docs.py`

**Interfaces:**
- Produces an explicit completion matrix separating implemented, tested, isolated, deferred, and unverified capabilities.
- Produces reproducible commands and output references for Python, frontend, report, secret, dependency, and Git checks.

- [ ] Write failing documentation tests for factor DSL, factor evidence, provider status, API-key exclusion, multi-agent roles, HTML reports, and paper-only limits.
- [ ] Run `python3 -m ruff check src tests`.
- [ ] Run `python3 -m compileall -q src tests`.
- [ ] Run `python3 -m pytest -q`.
- [ ] Run `npm test` and `npm run build` in `frontend`.
- [ ] Run `python3 scripts/secret_scan.py`, `python3 scripts/validate_governance.py`, and `git diff --check`.
- [ ] Inspect a generated offline HTML report and verify no external network asset or secret is present.
- [ ] Commit `docs: record autonomous delivery validation` and push the branch; monitor CI and repair failures with fresh evidence.

## Execution ledger

- Ruling: keep external GitHub projects outside the runtime and dependency lock — preserves license, security, and reproducibility boundaries while retaining their code for study.
- Ruling: implement a native DSL/evaluator before any Qlib/RD-Agent adapter — the product needs a small auditable contract before optional integrations can be safe.
- Ruling: expose provider readiness, not raw API-key entry — prevents secrets entering browser, artifacts, logs, or reports while leaving a future user-owned adapter path.
- Ruling: offline deterministic execution remains the default — permits complete local research without user credentials or hosted model access.

