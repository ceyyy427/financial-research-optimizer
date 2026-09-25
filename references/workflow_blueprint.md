# Workflow blueprint

## State graph

scope -> source_discovery -> provenance_and_quality -> feature_label_build -> statistical_baselines -> deep_challengers -> rolling_forecasts -> calibration_and_robustness -> constrained_decision -> stress_and_sensitivity -> model_selection -> modular_summary -> html_and_decision_table -> report_and_monitor

A state may be skipped only when its output is already available, current, and verified. Record the reason for the skip.

## State input/output contract

| State | Inputs | Required output | Gate |
|---|---|---|---|
| scope | user question | research contract | target/horizon/cutoff defined |
| source discovery | contract | source registry | source identity and access verified |
| provenance and quality | raw snapshots | audit report | dates/units/missingness/leakage checked |
| feature-label build | clean data | versioned feature table | every feature has an information timestamp |
| statistical baselines | feature table | baseline forecasts | residual and assumption diagnostics |
| deep challengers | baselines + feature table | model cards/checkpoints | architecture justified |
| rolling forecasts | frozen protocol | forecast ledger | no test reuse |
| calibration | forecast ledger | coverage/reliability/stability | uncertainty assessed |
| constrained decision | forecasts + risk | decision ledger | costs/limits/solver status recorded |
| stress | decision ledger | sensitivity table | no silent constraint relaxation |
| model selection | all prior outputs | selection memo | rule frozen before comparison |
| report and monitor | selection memo | reader-facing report | claims trace to evidence |
| modular summary | all validated outputs | module records and forecast/decision JSON | facts, estimates, forecasts, and decisions separated |
| html and decision table | analysis JSON | offline HTML + CSV/Markdown table | as-of, uncertainty, module status, and sources visible |

## Multi-round loop

- Round 0 audits data and fixes only source/quality defects.
- Round 1 establishes naive, regression, and time-series baselines.
- Round 2 tests feature/label ablations.
- Round 3 tests deep architectures and uncertainty heads.
- Round 4 checks calibration, drift, regime slices, and seed sensitivity.
- Round 5 runs portfolio optimization under frozen costs and constraints.
- Round 6 stress-tests the selected candidate and one challenger.

Stop after two non-improving rounds, material evidence instability, or an unresolved source/label issue.

## Artifact gate

Do not mark a run complete after producing only a narrative answer. The completion gate requires:

- an analysis JSON with all applicable modules and explicit `not_available` records;
- an offline HTML file rendered from that JSON;
- a decision table with a row for each material action or monitoring item;
- a reproducibility footer linking source IDs, calculation IDs, model versions, and timestamps.

## Selection rule

Before inspecting final test results, define:

- primary forecast metric;
- calibration metric;
- economic metric;
- penalty for turnover, drawdown, instability, and capacity;
- tie-break rule;
- minimum data-quality and calibration gates.

Prefer a Pareto set if the objectives conflict. If a single score is required, normalize each component using development data only and save the weights before final selection.
