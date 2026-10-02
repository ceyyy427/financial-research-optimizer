# Finathink P6.6 Execution Plan

**Phase:** P6.6 Strategy Research & Simulation Lab  
**Baseline:** `9d32f31a0ee955bb320318b1ca7220ff5095ddf8`  
**Scope:** one deterministic strategy-learning laboratory with two supported
strategy forms, historical backtest, explicit OOS/walk-forward metadata,
forward paper replay, diagnostics, and safe research export.

## Objective

P6.6 turns a user's strategy idea into testable knowledge:

`idea → typed StrategySpec → FeatureDefinitions/Graph → Strategy IR →
review → existing P5 backtest → OOS/walk-forward → PaperRun → comparison →
learning → export`.

The first reference strategy is lagged momentum with a low-volatility filter.
A moving-average trend rule is the second deliberately simpler strategy used
to prove that the contracts are not hard-coded to one cross-sectional recipe.
All output is research and education. No broker, credential, live order, or
real-money portfolio path is introduced.

## Frozen foundations

- P4 `ResearchRun`, `RunStore`, `ExperimentEngine`, and artifact fingerprints;
- P5 `BacktestEngine`, `BacktestConfig`, `BacktestResult`, risk metrics, and
  portfolio allocation helpers;
- P5.5 validity, multiple-testing, OOS boundary, and multi-asset contracts;
- P6 `TypedToolRequest`, `P6QuantGateway`, prediction/reveal/explain, and
  `LearningStore`;
- P6.5 source admission, evidence, provenance, temporal semantics, SQLite
  repository, and capability policy.

P6.6 adds an isolated `finahinking.p6_6` package and additive documentation.
Any P5 change is an additive extension with regression tests; no execution
engine or database architecture is replaced.

## Work order

1. Confirm baseline, inspect capabilities, and freeze this plan and the
   strategy constitution.
2. Define immutable feature, graph, strategy, IR, configuration, paper, and
   export contracts.
3. Implement a small feature registry with point-in-time checks and lineage.
4. Implement natural-language interpretation for the two supported reference
   forms; require an explicit user-review object before compilation.
5. Compile validated specs into a constrained IR and a P5 `Strategy` adapter.
6. Add deterministic educational code plus code/math/finance learning traces.
7. Build a backtest studio that routes execution to the existing P5 engine and
   carries costs, benchmark, validity, OOS, and provenance.
8. Add deterministic OOS and minimal walk-forward evaluation using frozen
   configurations; disclose multiple testing.
9. Add PaperRun with a virtual clock, virtual orders/fills, portfolio state,
   restart/replay fingerprints, and no broker fields.
10. Add backtest-vs-paper comparison, feature drift diagnostics, learning
    cards, and a path-safe research package exporter.
11. Run focused tests, full regressions, security/validity/reproducibility
    reviews, and the 54-item P6.6 gate.
12. Update project state and stop at P7 readiness; do not start P7.

## Parallel-safe implementation boundaries

After the contracts in step 2 are stable, feature engineering, strategy
interpretation/IR, educational explanation, paper simulation, and export can be
implemented independently. They must share the same immutable fingerprints and
must not create separate data loaders or execution runtimes. Backtest/OOS
integration is sequenced after the IR compiler so the execution boundary has a
single source of truth.

## Security boundaries

- Strategy text is untrusted input and is parsed into a finite allowlist of
  operations; it never becomes executable Python.
- The IR contains only registered primitive names and JSON-safe parameters.
- Educational code is a rendered artifact. Static checks reject `eval`,
  `exec`, imports, subprocess, sockets, filesystem writes, broker names,
  credential access, and dynamic loading; it is never auto-executed.
- PaperRun has simulation-only fields and cannot represent broker accounts,
  tokens, exchange credentials, or real order IDs.
- Data access goes through approved/admitted `Dataset`/`MultiAssetDataset`
  objects and bounded artifact roots.
- SQL remains fixed and parameterized through the existing repository boundary.

## Gate evidence

The gate requires deterministic fixtures and tests for feature timing,
versioning, IR compilation, code traceability, cost handling, OOS boundaries,
virtual fills, freeze/replay, comparison, drift, export safety, and learning.
It also requires the full P0–P6.5 regression suite, Ruff, Notebook, governance,
both `pip check` commands, `git diff --check`, a clean worktree, and
`provenance.code_commit == git rev-parse HEAD`.

Live APIs, live markets, live LLM output, brokers, and package installation are
not prerequisites for deterministic P6.6 validation.

## Exit state

```text
Finathink P6.6 Strategy Research & Simulation Lab: COMPLETE
Feature Engineering Layer: VALIDATED
Strategy Research Pipeline: VALIDATED
Educational Code / Math / Finance Learning: VALIDATED
Historical Backtest: VALIDATED
Paper Research Simulation: VALIDATED
Real-Money Execution: OUT OF SCOPE
P7: WAITING FOR HUMAN APPROVAL
```
