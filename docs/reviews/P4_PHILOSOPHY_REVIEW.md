# P4 Philosophy Review

**Verdict:** P4 preserves the Finahinking research loop, with explicit
limitations that must remain visible.

## Review question

Does the system still express:

```text
Question -> Experiment -> Evidence -> Insight
```

or has it degraded into:

```text
Factor -> Metric -> Number
```

## Strengths

- `ResearchRun` requires a question and hypothesis before a metric can be
  recorded, so the factor is subordinate to a research purpose.
- Dataset provenance, factor definition, method, parameters, result,
  conclusion, insight, and limitations travel together.
- The experiment engine makes the temporal alignment and factor shift explicit,
  rather than presenting an unqualified correlation.
- Fingerprints and local persistence make the evidence inspectable and
  reproducible, which is a prerequisite for research memory.
- The record is data-only JSON, so future graph or knowledge systems can ingest
  it without executing arbitrary stored code.

## Weaknesses

- Evidence is represented through a dataset payload, provenance, and result;
  there is not yet a first-class `Evidence` object or typed graph edge.
- Insight and conclusion are researcher-authored fields. P4 does not evaluate
  whether an interpretation is scientifically warranted.
- The current method is a descriptive information-coefficient experiment, not a
  causal design or a full out-of-sample evaluation.
- Environment identity, source version, validation report, and factor
  implementation digest are deferred provenance fields.
- The local store has no cross-run index, query language, or collaboration
  semantics.

## Future risks

- A user may mistake a descriptive metric for predictive performance or advice.
- A stable URL may serve changed upstream data even when the provider name is
  unchanged.
- A factor implementation can change while retaining its name.
- Future graph or agent layers could amplify weak conclusions unless they retain
  limitations and provenance as first-class data.
- A future backtest could silently introduce look-ahead, leakage, survivorship,
  cost, or corporate-action errors if the P5 gate is weakened.

## Assessment

P4 is a research record and experiment foundation, not a factor-to-number
pipeline. It is philosophically aligned because it preserves why the question
was asked, what evidence was used, how it was evaluated, and what the researcher
learned. The missing first-class evidence graph and stronger environment
provenance are future requirements, not reasons to unfreeze P4.

**Recommendation:** Keep P4 frozen. Require human approval and a dedicated
research-validity gate before any P5 implementation.
