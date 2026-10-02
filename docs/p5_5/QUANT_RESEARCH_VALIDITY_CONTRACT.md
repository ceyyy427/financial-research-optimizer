# P5.5 Quant Research Validity Contract

**Status:** Contract for the P5.5 Quant Platform boundary

**Scope:** Historical, deterministic research experiments only. This contract
does not establish live-market, institutional, predictive, or investment-advice
validity. A P5.5 run is evidence about a specified historical experiment.

## Contract principles

Every experiment records its assumptions, information set, execution timing,
evaluation boundary, and known limitations. A missing realism feature is visible
to the caller; it is never inferred from a performance number. A status is
required for every applicable validity dimension:

- **SUPPORTED** — enforced by the implementation and covered by a deterministic
  test for this run.
- **LIMITED** — partially represented or enforced; the limitation and residual
  risk are recorded.
- **UNSUPPORTED** — not modeled or not verified; the run carries a warning.
- **NOT_APPLICABLE** — the dimension does not apply to this experiment, with a
  recorded reason.

The status applies to one run and its exact dataset, configuration, engine
version, and result fingerprint. It is not a claim about all experiments.

## Required validity record

The normalized experiment record must include:

```text
validity:
  <dimension>:
    status: SUPPORTED | LIMITED | UNSUPPORTED | NOT_APPLICABLE
    rationale: non-empty explanation
    evidence_refs: [fingerprint or test/reference IDs]
    warning_codes: [structured warning codes]
```

`validity` is part of the experiment specification and provenance. A run cannot
be presented as complete if a required dimension has no status and rationale.
Warnings and limitations must survive in the `QuantRun`, `ResearchRun`,
`Artifact`, and user-facing explanation.

## Validity dimensions

The following dimensions are mandatory fields. The baseline classification is a
conservative default; an experiment may upgrade a field only when its evidence
supports that upgrade.

| Dimension | Baseline | Contract requirement |
| --- | --- | --- |
| Point-in-time correctness | LIMITED | State the information set available at each timestamp and provide a fixture or provenance check. |
| `available_at` semantics | UNSUPPORTED | Record whether source observations have an availability timestamp; never assume publication time equals observation time. |
| Look-ahead bias | LIMITED | Signal features must be shifted or otherwise proven causal; an adversarial future-peek test is required for SUPPORTED. |
| Signal timing | LIMITED | Record the bar/date used to compute a signal and its lag to execution. |
| Execution timing | SUPPORTED for the P5 next-period engine | Record the execution bar and reject same-bar execution unless a separate contract exists. |
| Rebalance timing | SUPPORTED when configured | Record frequency, rebalance rule, and the exact timestamps at which targets change. |
| Transaction costs | SUPPORTED when explicit | Record fee model, units, values, and the cost-model fingerprint. |
| Slippage | SUPPORTED when explicit | Record slippage model, units, values, and any unmodeled market impact. |
| Turnover | SUPPORTED when computed | Define numerator, denominator, and period; preserve the normalized metric. |
| Benchmark alignment | LIMITED | Record benchmark identity, date alignment, return convention, and missing observations. |
| Missing data | LIMITED | Record validation, dropped rows, imputation (if any), and impact on coverage. |
| Sample size | LIMITED | Record observation count and minimum-sample rules; undefined statistics remain `null`. |
| IS/OOS separation | UNSUPPORTED unless explicitly designed | Record training/specification, freeze, validation, and test periods with non-overlap evidence. |
| Parameter-search scope | LIMITED | Record every parameter selected, its source, and whether it was fixed before evaluation. |
| Multiple testing | UNSUPPORTED unless recorded | Record search-space size, number of experiments, selection method, and OOS validation. |
| Data snooping | LIMITED | State reuse of datasets, hypotheses, or results and the mitigation applied. |
| Survivorship bias | UNSUPPORTED by the baseline dataset | Record universe membership history; otherwise emit `SURVIVORSHIP_BIAS_NOT_MODELED`. |
| Delisting | UNSUPPORTED by the baseline dataset | Record delisting observations and treatment; otherwise emit `DELISTING_NOT_MODELED`. |
| Corporate actions | LIMITED | Record split/dividend adjustment policy and source coverage; emit `CORPORATE_ACTIONS_PARTIAL` when incomplete. |
| Liquidity | UNSUPPORTED by the baseline engine | Record volume/spread assumptions; otherwise emit `LIQUIDITY_NOT_MODELED`. |
| Capacity | UNSUPPORTED unless modeled | Record capital, participation, and capacity assumptions; otherwise emit `CAPACITY_UNKNOWN`. |
| Leverage | LIMITED | Record leverage limits, cash policy, and financing assumptions. |
| Shorting | LIMITED | Record whether short weights are allowed and the borrow/margin model; unsupported shorting is explicit. |
| Market impact | UNSUPPORTED by the baseline engine | Record impact assumptions; do not infer institutional execution realism. |

Additional limitations may be added, but the required dimensions cannot be
deleted or silently downgraded after execution.

## Structured warning codes

The following codes are stable, machine-readable warnings. They are emitted when
the corresponding limitation is not modeled or only partially modeled:

```text
SURVIVORSHIP_BIAS_NOT_MODELED
DELISTING_NOT_MODELED
CORPORATE_ACTIONS_PARTIAL
LIQUIDITY_NOT_MODELED
CAPACITY_UNKNOWN
AVAILABLE_AT_UNVERIFIED
OOS_BOUNDARY_MISSING
MULTIPLE_TESTING_UNRECORDED
DATA_SNOOPING_RISK
MARKET_IMPACT_NOT_MODELED
```

Warnings are evidence metadata, not errors by themselves. A gateway must reject
an experiment when a required boundary is absent for the requested operation,
and must return warnings when the operation can safely proceed with limitations.

## OOS and walk-forward foundation

The smallest valid OOS experiment has four explicit records:

1. **Training/specification period** — data used to define the hypothesis,
   factor, or parameters.
2. **Freeze boundary** — an immutable configuration and parameter fingerprint;
   no test-period data may alter it.
3. **Later test period** — observations strictly after the freeze boundary.
4. **Evaluation** — metrics computed only from the later period, with its own
   result and provenance fingerprints.

The typed period model should distinguish `TrainingPeriod`,
`ValidationPeriod`, and `TestPeriod`. Periods must be ordered, non-overlapping
unless a documented walk-forward policy permits a boundary convention, and
represented in the experiment provenance.

An optional minimal walk-forward run repeats:

```text
train window -> freeze configuration -> evaluate next window -> advance window
```

Each window records its own freeze and evaluation boundaries. A walk-forward
label cannot be used when the implementation only performs an in-sample run.

## Multiple-testing and parameter-search policy

P5.5 prohibits the following discovery claim:

```text
generate many strategies -> backtest everything -> choose best Sharpe -> call it discovery
```

When more than one specification, parameter, factor, or strategy is evaluated,
the run must record:

- the original hypothesis;
- the exact search space and parameter ranges;
- the number of attempted experiments, including failures;
- the selection rule and whether it used an OOS period;
- the validation method and OOS boundary;
- the final selected configuration fingerprint;
- any data reuse or researcher degrees of freedom.

The baseline P5.5 implementation does not perform large parameter-grid searches.
An unrecorded search must be classified `UNSUPPORTED` and carry
`MULTIPLE_TESTING_UNRECORDED`.

## Interpretation boundary

The following distinctions are part of the contract:

- a backtest is an experiment;
- a backtest result is evidence;
- a metric such as Sharpe is not truth or a forecast;
- statistical significance is not automatically economic significance;
- correlation is not automatically causation;
- historical simulation is not live performance;
- optimization output is not investment advice.

User-facing conclusions must state what the experiment supports, what it does
not support, and all material warnings and limitations.

## Validation and gate evidence

The P5.5 gate must include deterministic evidence for:

- point-in-time and no-look-ahead behavior;
- explicit next-period execution and cost semantics;
- OOS boundary or an explicit `UNSUPPORTED` classification;
- multiple-testing fields and rejection of unrecorded searches;
- warning propagation through Artifact, QuantRun, ResearchRun, and explanation;
- stable validity, result, and provenance fingerprints;
- reproducibility of the original P5 fixture and the second vertical slice.

This contract is a research boundary. It does not authorize brokerage, live
execution, autonomous strategy discovery, or financial recommendations.
