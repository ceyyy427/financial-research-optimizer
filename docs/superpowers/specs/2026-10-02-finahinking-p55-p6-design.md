# Finathink P5.5 + P6 Design

**Status:** Approved for sequential implementation from the user-supplied
P5.5/P6 mission brief

**Goal:** Stabilize the P5 research-only quant boundary, then add a guided,
human-controlled quant research and learning workflow. P5.5 must pass its gate
before any P6 code is enabled; the implementation stops after the P6 Gate
Review and does not enter P7.

## Scope and non-goals

P5.5 freezes six library-neutral services (`quant.run_backtest`,
`quant.run_regression`, `quant.evaluate_performance`, `quant.analyze_risk`,
`quant.compare_benchmark`, and `quant.inspect_run`), formalizes validity and
OOS boundaries, adds structured warnings, and ships a deterministic
cross-sectional lagged-momentum slice. `quant.optimize_portfolio` remains
DEFERRED because the existing deterministic allocator is sufficient.

P6 adds a Finathink-owned state machine, constrained classifier, typed
hypothesis and experiment specifications, an allow-listed tool gateway,
grounded explanations, predictable learning cards, and a small auditable
learning-state store. It is not a trading system, alpha-miner, autonomous
research agent, broker, recommendation engine, full knowledge graph, or
multi-agent framework.

## Architectural boundaries

```text
Human question
  -> P6 intake/classifier/hypothesis/planner
  -> explicit assumption review
  -> typed P5.5 tool gateway
  -> domain quant service / optional isolated adapter
  -> QuantRun + ResearchRun + Artifact + evidence
  -> grounded explanation
  -> learning card + minimal learning state
```

The P6 layer may structure and explain requests but never computes a metric or
imports a quant library directly. P5.5 services own calculations and return
normalized, serializable records. The Research OS owns provenance and
fingerprints. User text and external documents are data, not authority.

## P5.5 contracts

`quant.validity` owns `ValidityStatus`, the required validity dimensions,
structured warning codes, and an immutable `ResearchValidity` profile. Every
vertical-slice result carries the profile and explicitly marks unsupported
realism as LIMITED or UNSUPPORTED.

`quant.splits` owns `TrainingPeriod`, `ValidationPeriod`, `TestPeriod`,
`ParameterSelectionBoundary`, and `EvaluationBoundary`. A deterministic OOS
plan validates chronological, non-overlapping windows, records the hypothesis
and bounded search metadata, freezes a configuration fingerprint before the
test window, and refuses selection/evaluation leakage. No grid-search API is
provided.

`quant.multi_asset` owns a point-in-time-safe long-form panel contract and a
fixed cross-sectional lagged-momentum engine. Observations include `date`,
`asset`, `close`, and `available_at`; ranking uses only observations available
at the signal timestamp, ties are deterministic, targets are lagged to the
next period, and execution is long-only with explicit costs, slippage, cash,
turnover, benchmark, risk, and performance. Parameters are documented and
fixed, not optimized.

`quant.services` is the stable, library-neutral service boundary. Typed
requests contain identifiers, JSON-safe parameters, and registered strategy or
adapter names; they never contain Python source, callables, shell text, or
foreign library objects. Typed responses include status, normalized result,
ResearchRun/QuantRun IDs, artifact and result fingerprints, provenance,
warnings, limitations, and explicit failure codes.

The existing P5 single-asset API remains backward-compatible. The new panel
contract is additive rather than silently widening `Dataset` or
`BacktestEngine`.

## P6 models and state machine

`finahinking.p6.models` defines `TaskCategory`, `ResearchQuestion`,
`Hypothesis`, `Universe`, `Period`, `Factor`, `Benchmark`, assumptions,
`ExperimentSpecification`, typed tool envelopes, explanation sections,
learning-card fields, misconception records, and learning-state records.
`finahinking.p6.state_machine` admits only the ordered states:

```text
QUESTION_RECEIVED -> CLASSIFIED -> HYPOTHESIS_PROPOSED
-> EXPERIMENT_PROPOSED -> ASSUMPTIONS_ACCEPTED -> TOOL_EXECUTED
-> EVIDENCE_READY -> EXPLANATION_READY -> LEARNING_READY
```

Material hypothesis/universe/cost/benchmark/optimization changes require an
explicit assumption review. A deterministic classifier routes only genuinely
quantitative questions to QUANT and can return STAND_BACK. A planner cannot
silently mutate material assumptions.

`finahinking.p6.gateway` is the sole P6 execution path and delegates to the
P5.5 allow-list. Its security policy rejects dynamic code, shell/package
installation, source/provenance mutation, deletion, unapproved adapters, and
unknown tool names. A deterministic model protocol/stub is used in core tests;
there is no live model dependency.

The explanation layer accepts only approved normalized evidence and produces
separate sections for what was asked, tested, data, result, support/non-support,
limitations, and concepts. Every numeric claim carries an evidence reference.
The educational interaction is a pure `PREDICT -> REVEAL -> EXPLAIN` record;
it cannot alter a QuantRun. Learning cards and the minimal user/concept state
are immutable, bounded, and auditable; misconception records describe an
observed statement, correction, and evidence, never a psychological label.

## Vertical slices

P5.5's cross-sectional momentum slice and P6's primary guided workflow share a
deterministic fixture. The primary P6 path is:

```text
"Does momentum work in this dataset?"
 -> QUANT -> explicit hypothesis -> fixed experiment + assumptions
 -> typed multi-asset tool -> QuantRun/ResearchRun/evidence
 -> grounded explanation + limitations -> one learning card
 -> optional predict/reveal/explain -> state update
```

The second P6 path runs an approved regression request through the existing
statsmodels adapter in `.venv-quant`, normalizes coefficients/uncertainty, and
teaches beta/intercept/uncertainty without exposing a statsmodels object. The
main environment remains free of statsmodels and all other deferred libraries.

## Provenance, safety, and rollback

Every run records dataset/as-of information, code and dependency versions,
parameters, OOS boundaries, validity profile, warnings, limitations, and
fingerprints. Session audit records capture the user question, classification,
hypothesis, specification, assumptions, tool calls, run IDs, artifact/evidence
references, explanation version, and what the user saw. Existing P5 records are
not rewritten; additive envelopes preserve schema compatibility.

If a gate fails, the phase remains at the last passing state and P6 is not
started. New code is isolated in additive modules and can be reverted by the
phase commit without changing the P5 authoritative commit. Final provenance
must equal the final Git `HEAD`.

## Verification strategy

TDD is used for each contract: write focused failing tests, observe the red
failure, implement the smallest domain behavior, then run focused and full
gates. Tests cover temporal leakage, OOS boundaries, deterministic ranking and
ledger arithmetic, warning propagation, service authorization, fingerprints,
state transitions, claim grounding, learning updates, and prompt/tool security.
The final gate runs pytest, Ruff, notebook and governance gates, both `pip
check`s, isolated statsmodels smoke, old and new fixtures, forbidden import and
dependency scans, `git diff --check`, and a clean-worktree check. Independent
reviews cover architecture, quant boundary, validity, explanation integrity,
security, learning integrity, and reproducibility.

