# P4 Final Architecture Review

**Review date:** 2026-10-02
**Scope:** P4 foundation only; no P5 implementation
**Verdict:** **P4 FOUNDATION STABLE**

## Review question

P4 is successful only if it preserves the Finahinking research loop rather than
turning the project into a factor calculator:

`Question -> Hypothesis -> Dataset -> Experiment -> Result -> Conclusion -> Insight`

`ResearchRun` carries each of those concepts. The factor is one input to the
experiment, not the research object itself. `ExperimentEngine` binds the
dataset, factor, method, parameters, and result, and `RunStore` preserves the
record as canonical JSON.

## Strengths

### Research meaning

- A run has a required question and hypothesis, so the output has an explicit
  reason to exist.
- The record includes conclusion, insight, and limitations rather than only a
  numeric metric.
- The factor definition, explanation, and limitations travel with the result,
  which makes the factor interpretable to a future reader.

### Reproducibility

- Dataset payloads include normalized columns, dated records, provider, source
  URL, retrieval metadata, license text, and a SHA-256 dataset fingerprint.
- Method and parameters are recorded; the current method records the forward
  return horizon and one-period factor shift.
- Result fingerprints cover the dataset fingerprint, factor definition, method,
  parameters, and result values.
- Reproduction rejects dataset drift and any resulting factor/method/parameter
  drift before treating a run as reproduced. It deliberately replays the
  recorded parameters; it does not yet accept a separate candidate parameter
  mapping for an explicit parameter-sensitivity comparison.
- Canonical JSON and local atomic writes make records portable and recoverable
  without pickle or stored-code execution.

### Research quality and safety

- Forward returns are aligned with a one-period factor shift by default; the
  design makes the look-ahead boundary visible in parameters and limitations.
- Constant or insufficient inputs produce an explicit undefined information
  coefficient instead of a fabricated statistic.
- Invalid horizons, malformed records, unsafe run IDs, and path traversal are
  rejected.
- The package remains a research laboratory: no brokerage calls, trading
  automation, portfolio execution, or investment advice are introduced.

## Weaknesses and deferred requirements

The following are real limitations, but none blocks the P4 foundation or
requires changing the frozen P4 API before human review:

1. **Source version is implicit.** A source URL and retrieval timestamp are
   recorded, but there is no provider release/version identifier or immutable
   remote snapshot reference.
2. **Factor implementation identity is descriptive.** The factor name and
   definition are recorded, but the source revision or implementation digest is
   not independently captured.
3. **Execution environment is absent.** Python, pandas, NumPy, and package
   versions are not part of the run record, so cross-environment reproduction
   can be harder to diagnose.
4. **Validation status is not a first-class field.** The engine validates its
   price input before execution, but the record does not preserve the exact
   validation report or warnings.
5. **The current method is intentionally narrow.** P4 supports descriptive
   information-coefficient experiments; it is not a backtest, portfolio
   simulator, causal estimator, or multiple-testing correction system.
6. **The storage boundary is local.** There is no index, graph edge model,
   remote collaboration, or conflict-resolution protocol.
7. **Parameter comparison is replay-only.** `reproduce` reuses the recorded
   configuration, so explicit alternate-parameter drift reporting remains a
   future requirement rather than a P4 API capability.

The provenance gaps and proposed future acceptance tests are recorded in
`docs/reviews/P4_PROVENANCE_IMPROVEMENT_PROPOSAL.md`; they are not implemented
in this phase.

## Architecture decisions frozen at P4

- Providers remain the only network boundary.
- P2 `Dataset`/`Provenance` and P3 `FactorDefinition` remain the input
  contracts.
- Execution, record modeling, and storage remain separate modules.
- ResearchRun records are canonical JSON with SHA-256 fingerprints.
- Stored records are data only; they never execute code.
- Local RunStore writes are atomic and run IDs are path-safe.
- P4 stays descriptive and reproducible; backtesting and portfolio behavior are
  future scope only.
- The no-advice and no-automation boundary remains invariant.

## Personal research memory / future graph review

The current architecture is a sound seed for a future Personal Research Graph:
`run_id`, fingerprints, question/hypothesis text, dataset metadata, factor
metadata, result, conclusion, and insight provide stable node attributes. A
future graph can add explicit edges such as `question -> run`, `run -> dataset`,
`run -> evidence`, and `run -> insight` without replacing the P4 record.

It is not yet a graph implementation. It lacks globally addressable evidence
nodes, explicit typed edges, merge semantics, and query/index contracts. Those
are future requirements, not reasons to redesign the P4 foundation now.

## Remaining risks

- Users can still write an invalid or overconfident conclusion; P4 stores text
  and limitations but cannot judge scientific validity automatically.
- A source can change behind a stable URL; the dataset fingerprint detects local
  drift but cannot create an immutable upstream archive.
- A factor implementation can change while retaining its name; a future
  implementation digest is needed for stronger auditability.
- Descriptive IC can be mistaken for predictive power; user-facing explanations
  must continue to state that it is not advice or a trading result.

## Future considerations

Before any P5 implementation, human review should decide whether to:

- add explicit source-version, environment, validation-report, and factor-code
  identity fields;
- define evidence and insight identifiers suitable for a research graph;
- specify data-splitting, transaction-cost, slippage, survivorship, and
  multiple-testing controls for any backtest;
- choose a dependency strategy that preserves reproducibility and license
  compatibility.

## Evidence reviewed

- `docs/phases/P4_GATE_DESIGN.md`
- `docs/phases/P4_GATE_REVIEW.md`
- `docs/FINAHINKING_P4_COMPLETION_REPORT.md`
- `src/finahinking/experiments/models.py`
- `src/finahinking/experiments/engine.py`
- `src/finahinking/experiments/storage.py`
- Full P0–P4 test, lint, governance, notebook, and dependency checks

## Recommendation

**P4 FOUNDATION STABLE.** Keep the current P4 boundary frozen and wait for
human review. P5 is only **READY FOR HUMAN APPROVAL**; it is not implemented or
authorized by this review.
