# Finathink P5.5 + P6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use checkbox tracking and do not cross the P5.5 gate until its evidence is complete.

**Goal:** Freeze a safe, reproducible quant service boundary and then deliver
guided quant research and learning, stopping after P6 Gate Review.

**Architecture:** Additive domain modules over the frozen P5 APIs. P5.5 owns
validity, OOS, multi-asset execution, typed quant services, and structured
warnings. P6 owns orchestration, explanation, and learning; it can only call
the P5.5 allow-list. Optional statsmodels remains isolated in `.venv-quant`.

**Spec:** `docs/superpowers/specs/2026-10-02-finahinking-p55-p6-design.md`

## Global constraints

- Verify `HEAD == 358ade94bd26d246e907414fc3ac729dc5ae1d5e` before changes and
  document any approved difference.
- Preserve P5 `Dataset`, `BacktestEngine`, `ResearchRun`, `Artifact`, and
  `QuantRun` compatibility; use additive schemas.
- No new runtime dependency, MCP framework, agent framework, broker, live data,
  arbitrary Python, shell execution, generated code, or optimization grid.
- Keep all runs offline, deterministic, point-in-time explicit, and research
  only. Unsupported realism is visible as structured warnings.
- Use `apply_patch` for edits, run focused red/green tests, commit coherent
  milestones, and request independent review before each gate report.

## Review focus

- Temporal integrity: available-at filtering, lagged signal, next-period
  execution, strict OOS boundaries, and adversarial future-data fixtures.
- Provenance/replay: identical inputs reproduce result/artifact/QuantRun and
  final `code_commit` equals `git rev-parse HEAD`.
- Service safety: six allow-listed typed tools return normalized envelopes and
  reject unknown tools, callables, source/eval/exec/shell payloads, foreign
  objects, and unapproved adapters.
- Explanation integrity: every numeric claim references a normalized result;
  warnings/limitations survive into the user-facing record.
- Learning integrity: cards, quizzes, misconceptions, and progress are bounded,
  evidence-linked, deterministic, and never alter quant evidence.

## Phase 0: planning and capability evidence

- [ ] Add `docs/p5_5/P5_5_SKILL_CAPABILITY_MATRIX.md` with trusted skills,
  repository-native workflows, structured tools inspected, no-install decision,
  and deferred plugin/dependency candidates.
- [ ] Add this spec and plan; self-review for scope contradictions/placeholders.
- [ ] Commit planning artifacts before production code.

## Phase 1: P5.5 contract tests (red first)

- [ ] Add tests under `tests/p5_5/` for validity dimensions/statuses/warnings,
  OOS period ordering and freeze boundary, multiple-testing metadata, typed
  service schemas/authorization, and reproducibility.
- [ ] Add `fixtures/p5_5/oos_fixture.csv` and
  `fixtures/p5_5/momentum_multi_asset.csv` with deterministic `available_at`.
- [ ] Run focused tests and record the expected missing-symbol failures.

## Phase 2: P5.5 validity and OOS primitives

- [ ] Implement `src/finahinking/quant/validity.py`: immutable statuses,
  complete dimension registry, warning constants, JSON serialization,
  fingerprinting, and multiple-testing policy that rejects best-Sharpe-only
  selection.
- [ ] Implement `src/finahinking/quant/splits.py`: typed periods,
  `ParameterSelectionBoundary`, `EvaluationBoundary`, chronological validation,
  frozen configuration fingerprint, and deterministic OOS evaluation metadata.
- [ ] Add focused green tests, then run the unchanged P5 suite.

## Phase 3: P5.5 multi-asset vertical slice

- [ ] Implement `src/finahinking/quant/multi_asset.py` with long-form PIT panel
  validation, deterministic cross-sectional ranking/tie-break, lagged
  long-only weights, next-period execution, costs/slippage/turnover/cash,
  benchmark, risk/performance, and explicit realism warnings.
- [ ] Implement a high-level `run_cross_sectional_momentum_experiment` that
  creates normalized Artifact, QuantRun, and ResearchRun records with validity,
  OOS/search metadata, provenance, and fingerprints.
- [ ] Test no look-ahead, costs, constraints, old P5 fixture regression, and
  two identical runs producing identical fingerprints.

## Phase 4: P5.5 typed service boundary

- [ ] Implement `src/finahinking/quant/services.py` with typed request/response
  envelopes for the six frozen service names, explicit failure codes,
  ResearchRun/QuantRun linkage, provenance/warnings/limitations, and a fixed
  registry. Keep `quant.optimize_portfolio` explicitly DEFERRED.
- [ ] Ensure request validation is JSON-safe and rejects arbitrary Python,
  generated code, shell text, callables, and unregistered adapters.
- [ ] Add `docs/p5_5/QUANT_RESEARCH_VALIDITY_CONTRACT.md` and
  `docs/p5_5/P5_5_TOOL_API_SPEC.md` covering every required dimension and field.
- [ ] Run focused contract/security tests and commit P5.5 implementation.

## Phase 5: P5.5 gate and readiness

- [ ] Extend governance phase validation for P5.5/P6 and add documentation/gate
  tests without weakening earlier phase checks.
- [ ] Run independent architecture, security, quant-correctness, validity, and
  reproducibility reviews; inspect findings directly and resolve all important
  issues.
- [ ] Write `docs/p5_5/P5_5_FINAL_VALIDATION_REPORT.md` and
  `docs/p5_5/P6_READINESS_REPORT.md` with decision **A — READY FOR P6** only
  after every required command/evidence is green.
- [ ] Commit the P5.5 gate. If decision B/C, stop and do not create P6 modules.

## Phase 6: P6 red tests and domain models

- [ ] Add `tests/p6/` fixtures for classifier, hypothesis fidelity, planner
  assumption review, state transitions, tool authorization, grounding,
  learning, security, and both end-to-end workflows. Observe red failures.
- [ ] Implement `src/finahinking/p6/models.py` and `state_machine.py` with
  typed categories, question/hypothesis/specification, tool envelopes,
  explanations, prediction/reveal records, learning cards/state, and audit
  records.
- [ ] Implement `classifier.py`, `hypothesis.py`, and `planner.py` as
  deterministic constrained services; material changes require confirmation.

## Phase 7: P6 gateway and grounded explanation

- [ ] Implement `gateway.py` as the only execution path to the P5.5 service
  registry; add `security.py` policy checks and untrusted-text handling.
- [ ] Implement `grounding.py` and `explanation.py` so numeric claims are
  references to QuantRun/EvaluationReport/RegressionResult/RiskReport only,
  with WHAT/TESTED/DATA/RESULT/SUPPORTS/DOES NOT SUPPORT/LIMITATIONS/CONCEPTS
  sections and PREDICT → REVEAL → EXPLAIN records.
- [ ] Implement `audit.py` and verify complete per-session audit trails.

## Phase 8: P6 learning and workflows

- [ ] Implement `learning.py` with immutable cards, evidence-grounded quiz
  generation, misconception records, and deterministic progress/review updates.
- [ ] Implement `GuidedResearchService` primary momentum workflow and the
  regression-learning workflow through typed tools. Keep statsmodels calls in
  the existing lazy adapter and provide an isolated-environment smoke test.
- [ ] Add all required `docs/p6/*.md` contracts and evaluation plan.

## Phase 9: P6 independent audits and final gate

- [ ] Run independent passes A–G: architecture, quant boundary, validity,
  explanation, security, learning, reproducibility. Inspect source/tests and
  command output rather than trusting summaries.
- [ ] Update `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`,
  `docs/PROJECT_STATE.md`, `EVOLUTION_LOG.md`, and stale role/gate markers while
  preserving historical P0–P5 reports.
- [ ] Write `docs/p6/P6_FINAL_VALIDATION_REPORT.md` and
  `docs/p6/P6_GATE_REVIEW.md`; require all 24 gate items, clean worktree, and
  final provenance commit alignment.
- [ ] Run the full validation command set, commit final evidence, verify clean
  status and `code_commit == HEAD`, and stop with P7 waiting for human approval.

