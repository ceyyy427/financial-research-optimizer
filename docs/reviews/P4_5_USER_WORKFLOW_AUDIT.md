# P4.5 User Research Workflow Audit

**Result:** PASS with a notebook discoverability recommendation

## Simulated question

> Does volatility predict future returns?

The audit uses the checked-in deterministic fixture
`fixtures/p4_5/volatility_workflow.csv` and the regression test
`tests/experiments/test_p4_5_workflow.py`. The test builds a documented
`volatility_3d` FactorDefinition from the existing `returns` and `volatility`
features; no P5 source model or architecture was added.

## Seven-step journey

| Step | User action | System record |
| --- | --- | --- |
| 1. Create Question | Ask whether recent volatility predicts future returns. | `ResearchRun.question` |
| 2. Create Hypothesis | State that higher recent volatility is associated with different next-period returns. | `ResearchRun.hypothesis` |
| 3. Select Dataset | Use a validated, dated close-price fixture with fixture provenance. | Dataset payload and fingerprint |
| 4. Select Factor | Define rolling three-observation return volatility with meaning and limitations. | Factor name, definition, explanation, limitations |
| 5. Run Experiment | Execute IC with horizon 1 and factor shift 1. | Method and parameters |
| 6. Generate Result | Receive coverage and IC plus result fingerprint. | Result payload and fingerprint |
| 7. Create Insight | Record that larger samples and out-of-sample design are required. | Conclusion, insight, limitations |

## Observed end-to-end evidence

```text
factor: volatility_3d
method: information_coefficient
horizon: 1
factor_shift_periods: 1
coverage: 0.5833333333333334
information_coefficient: 0.09026243397759831
dataset_fingerprint: fe468014d020fbb3f59dd8b39a7b3edf8a45dab2ae414e5694ac16eab3df0a0a
result_fingerprint: 847427cc539ea85407134f06828b14790d0f4f9b5ee2466ac09408806eece6ba
storage_round_trip: true
reproduction_match: true
```

The conclusion remained deliberately narrow: the fixture provides descriptive
association only. The insight required a larger sample and out-of-sample
design. The engine also appended its no-advice limitation.

## Can a user understand the journey?

Yes when the API documentation, factor documentation, architecture freeze, and
ResearchRun record are read together. Every stage is inspectable and persisted.

The existing `notebooks/01_research_workflow.ipynb` predates P4 and demonstrates
only deterministic price/return feature exploration. It executes successfully,
but it does not teach the complete ResearchRun lifecycle. The checked-in
fixture/test preserves the complete workflow as durable evidence. A future
documentation change should add a P4 end-to-end tutorial notebook after human
approval; this is a discoverability improvement, not an architecture failure.

## Decision

The complete workflow is supported and reproducible through the API. **PASS.**
