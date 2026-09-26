---
name: financial-research-optimizer
description: Search public financial data, reconcile sources with point-in-time controls, audit and analyze it in modules, optionally retrieve data through a Java/MyBatis layer, compare statistical and deep-learning models with mathematical derivations and backtest-overfitting diagnostics, produce reproducible forecasts plus a concise self-contained HTML dashboard and decision table, and optimize portfolios with covariance robustness under explicit risk constraints. Use for evidence-backed financial forecasting or portfolio research; never use it to promise returns or place trades.
---

# Financial Research Optimizer

Use this skill when the user asks to discover financial data, analyze market direction, forecast prices/returns/volatility, compare statistical and deep-learning models, or optimize a portfolio from model outputs.

The objective is an auditable research result, not a guaranteed “best prediction.” Treat “best” as the model or portfolio that wins a pre-specified, risk-adjusted, out-of-sample comparison under stated costs and constraints. Every completed run that reads financial data must leave two reader-facing artifacts: a compact standalone HTML file and a decision table.

Use the declared `output_level` to control depth: `minimal` for a compact auditable read, `standard` for feature/model evidence, `research_grade` for reproducibility and applicable backtest diagnostics, and `portfolio_grade` for source reconciliation, covariance robustness and portfolio attribution. Run `scripts/run_preflight.py` before any dependent analysis.

## Research modes

Select exactly one mode before preflight:

| Mode | Minimum deliverables | Full overfitting/portfolio gate |
|---|---|---|
| `data_audit` | data dictionary, quality report, source list | no |
| `descriptive_analysis` | market state, risk metrics, charts | no |
| `forecasting` | baseline, rolling forecast, interval, calibration | no |
| `backtest` | costs, turnover, risk, applicable overfitting diagnostics | yes, overfitting only |
| `portfolio_research` | weights, constraints, covariance robustness, stress test and attribution | yes, overfitting and portfolio |

The mode controls required artifacts; `backtest` cannot run below `research_grade`, and `portfolio_research` cannot run below `research_grade`. The mode and output level are recorded in preflight and HTML.

## Introduction and positioning

This is a research and decision-support skill for financial time series. It combines financial statistics, multivariate analysis, regression, Bayesian uncertainty, mathematical finance, deep learning, and constrained portfolio optimization into one evidence-bound workflow.

It is designed to answer four linked questions:

1. What happened in the data and in the public information environment?
2. What conditional distribution or market state is supported by the data?
3. Which model is most stable under a pre-specified rolling out-of-sample protocol?
4. How does the forecast change a risk-constrained decision after costs and uncertainty?

The skill does not turn headlines into facts without source checking, does not treat a backtest as a guarantee, and does not place trades. It produces a traceable chain from source to dataset, model, forecast, decision, and limitation.

## Content presentation contract

Unless the user requests another format, present outputs in this order:

1. **Research contract** — universe, target, horizon, cutoff, costs, risk limits, and output type.
2. **Source and data audit** — URLs, retrieval time, fields, adjustments, missingness, revisions, and leakage checks.
3. **Module summaries** — one module per material analytical question; each has evidence, interpretation, forecast, confidence, and caveat.
4. **Feature and label construction** — formulas, information cutoff, transformations, and split logic.
5. **Model card table** — model, assumptions, objective, parameters, validation role, and known failure mode.
6. **Forecast evidence** — rolling metrics, uncertainty, calibration, regime slices, and challenger comparisons.
7. **Portfolio/decision layer** — objective, constraints, costs, solver status, active constraints, and fallback.
8. **Multi-round selection** — what changed per round, what improved, what failed, and why the selected model won.
9. **Scenario conclusion** — base, upside, and downside conditions; never write certainty as a fact.
10. **Limitations and reproducibility** — data snapshot, code, random seeds, version, and next monitoring actions.

The reader-facing HTML and decision table are mandatory, even when the user asks only for analysis. If a module cannot be supported by the data, render it as `not_available` with the exact reason instead of inventing a result.

## Mandatory modular analysis and artifacts

After data retrieval and quality checks, partition the analysis into the modules that are relevant to the target. Use these default modules unless the contract explicitly narrows scope:

1. **Data and provenance** — coverage, freshness, missingness, duplicates, adjustments, and leakage status.
2. **Descriptive market state** — returns, trend, liquidity, cross-sectional dispersion, and regime indicators.
3. **Statistical structure** — dependence, stationarity/transformations, factors, correlation, and volatility structure.
4. **Risk and tail** — realized volatility, drawdown, VaR/ES or quantiles, stress observations, and risk drivers.
5. **Forecast and model comparison** — baseline versus challengers, rolling metrics, calibration, and forecast distribution.
6. **Decision and scenarios** — base/upside/downside conditions, triggers, constraints, costs, and monitoring actions.

Each module must emit the same compact record:

```text
module_id, title, status, observed_facts, interpretation, forecast, confidence,
key_metrics, evidence_refs, caveats, next_check
```

Keep observed facts, fitted estimates, model-implied forecasts, and decisions in separate fields. A forecast record must include target, forecast origin, horizon, point or class output, interval or probability, model/version, and validity condition. A decision record must include priority, action/stance, trigger, rationale, risk, horizon, and owner/next check.

At the end of every run, call `scripts/generate_financial_html.py` with the structured analysis JSON. It writes:

- one self-contained, dependency-free HTML file with an executive summary, forecast badge, module cards, compact evidence metrics, and a decision table;
- embedded inline SVG metric figures for every completed prediction run, including the actual/model comparison, uncertainty or interval, and the most decision-relevant risk/model metric;
- one decision table in CSV and/or Markdown form for downstream use.

Read `references/html_output_contract.md` before producing or modifying the structured JSON, HTML, or decision table. The HTML must be concise, render offline, use no remote JavaScript or CSS, show the as-of timestamp and uncertainty, and link every material claim to a source or calculation identifier. The decision table is a decision-support artifact, not a trade instruction.

Use tables for model comparisons and risk limits, equations for estimands and optimization problems, figures for time trends/calibration/regime structure, and short prose for interpretation. Do not hide sample size, denominator, units, or uncertainty in a footnote. In HTML, prefer four to six summary cards and short module rows over a long narrative; include a small inline SVG trend plot only when a series is available and decision-relevant.

For a short answer, compress these sections but preserve the order and the distinction between observation, model output, scenario, and decision.

## Workflow construction

The workflow is a state machine with explicit handoffs:

`preflight -> scope -> sources -> reconciliation -> point-in-time audit -> feature/label contract -> features -> baselines -> challengers -> rolling validation -> applicability assessment -> calibration -> covariance robustness -> portfolio optimization -> stress test -> multi-criterion selection -> manifest -> modular summary -> HTML + decision table`

Each state must leave an artifact that can be inspected by the next state. A source list is not a data audit; a fitted model is not an out-of-sample forecast; a high forecast score is not a portfolio; and a portfolio backtest is not proof of future returns.

At every handoff, preserve the following invariants:

- the information cutoff is unchanged;
- all transformations are fit only on allowed historical data;
- the target definition and horizon are unchanged;
- the evaluation period remains untouched until selection;
- costs and constraints are not relaxed after seeing results;
- failed or rejected candidates remain recorded;
- every run has an experiment manifest with snapshot, code, environment, seeds, parameters, windows, and outputs;
- source conflicts are classified and material conflicts stop dependent analysis;
- output level is unchanged across all stages;
- every feature has availability time and lineage, every label has an overlap group, and purge/embargo are applied before evaluation;
- every numerical claim can be traced to a source, calculation, or saved output.

Use the detailed workflow schema in `references/workflow_blueprint.md`, the output contract in `references/content_contract.md`, the HTML artifact contract in `references/html_output_contract.md`, and the source routing rules in `references/data_provenance.md` when building a durable report or reusable dataset.

## Non-negotiable boundaries

- Do not promise profits, certainty, or a universally optimal forecast.
- Do not place orders, manage accounts, or send investment instructions unless a separate tool and explicit authorization cover that action.
- Separate descriptive facts, model-based forecasts, scenario projections, and investment decisions.
- Use public data only when the user has not provided authorized private data. Record source URL, access date, series/ticker, timezone, adjustment convention, and license/usage caveat.
- Never use future information: no random shuffling of time series, full-sample scaling, revised macro values unavailable at the forecast timestamp, final constituent lists for historical periods, or future-derived graphs/features.
- Do not invent missing observations, metrics, p-values, backtest returns, or model performance.
- If data are insufficient or sources conflict, stop dependent claims and report the exact gap.
- Do not treat a favorable backtest as sufficient evidence: assess the applicability of DM, White Reality Check, SPA, Deflated Sharpe Ratio, and PBO. A method is `not_applicable` when its declared trigger conditions are absent; only applicable methods can block selection.

## Workflow

### 1. Define the research contract

Before fetching data, identify:

- asset universe and identifiers;
- forecast target: next-period return, direction, volatility, quantile, price, spread, or option value;
- forecast horizon and frequency;
- information cutoff and trading/execution timestamp;
- evaluation period;
- transaction costs, slippage, capacity, leverage, shorting, turnover, and liquidity limits;
- risk measure: volatility, drawdown, VaR, ES/CVaR, factor exposure, or custom utility;
- output: dataset, research report, charts, forecast table, or constrained portfolio weights.
- output level: `minimal`, `standard`, `research_grade`, or `portfolio_grade`.

If the user leaves these open, choose conservative defaults and state them. For directional questions, use lagged returns and volatility features; for risk questions, predict a distribution rather than only a point.

Run the preflight contract before retrieval, feature construction, or fitting:

```bash
python3 scripts/run_preflight.py --config examples/research_config.json --manifest examples/experiment_manifest.json --analysis examples/demo_analysis.json --output artifacts/preflight.json
```

Treat `blocked` as a stopping state. Do not make a dependent forecast or portfolio claim until the blocking reason is resolved.

### 2. Search and bind public sources

Use web search for current, authoritative or reproducible sources. Apply the source routing table in `references/data_provenance.md`. Prefer:

1. official exchange, central-bank, regulator, or index-provider data;
2. public APIs with documented fields and timestamps;
3. stable public CSV/Parquet repositories with a clear provenance note.

For each source create a provenance record with fields source_id, url, retrieved_at, series, field, frequency, timezone, adjustments, revision_policy, and access_notes. Download a local snapshot when allowed. If an official page is inaccessible, use a mirror only when the mirror identifies the original source and label it as a mirror.

### 3. Build and audit the dataset

Create a data dictionary and audit:

- date ordering, duplicate timestamps, missingness and gaps;
- splits, dividends, rollovers, stale prices, trading halts and timezone alignment;
- survivorship and look-ahead bias;
- unit consistency and outliers;
- whether each feature was observable at the forecast cutoff;
- label overlap and execution-price convention.

Use a time-based split. Fit every imputer, scaler, PCA, factor model, graph, and feature selector inside each training window. Keep raw, cleaned, feature, label, and split tables separate. Save a metadata JSON and a reproducible script where possible.

If the data are stored in a relational database or the user requests Java, read `references/java_data_layer.md` before retrieval. Treat Java/MyBatis as an optional, read-only source adapter: it must export a time-bounded raw/canonical snapshot and provenance manifest for the same audit used for CSV/API data. It must not perform model selection or hide point-in-time joins in SQL.

Read `references/point_in_time_data.md` and `references/source_reconciliation.md` whenever more than one source or a revised macro/filing dataset is involved. Compare timestamps, prices, volume, adjustment conventions, calendars, and missingness before feature construction; record the reconciliation result in the provenance manifest and stop dependent analysis on unresolved material conflicts.

Read `references/feature_label_contract.md` and validate `research_config.json.feature_label_contract` with `scripts/feature_label_audit.py`. Every feature must carry `availability_time` and lineage. Every forward label must carry start/end timestamps and an overlap group. Apply the declared purge and embargo to every rolling boundary.

### 4. Establish statistical baselines

Always compare at least one interpretable baseline appropriate to the target:

- random walk or historical mean for prices/returns;
- ARMA/ARIMA for conditional means;
- GARCH or realized-volatility baseline for conditional variance;
- OLS/ridge/elastic-net for cross-sectional or factor models;
- logistic regression for direction;
- historical or parametric quantiles for tail risk.

Read `references/model_derivations.md` before deriving, explaining, or implementing a model. Keep it in the Skill because it supplies the mathematical contract for model cards, assumptions, stability conditions, uncertainty, and diagnostics rather than describing a model as a black box.

### 5. Add deep candidates only when justified

Choose models by data geometry:

- LSTM/GRU for stateful sequential inputs;
- causal 1-D CNN for local temporal patterns;
- causal Transformer for long context or multimodal sequences;
- autoencoder/PCA or factor networks for dimensionality reduction;
- graph neural network only when a time-valid asset graph exists;
- Student-t, mixture, quantile, or distributional heads for uncertainty;
- deep ensembles or approximate Bayesian models for model uncertainty;
- reinforcement learning only when actions, rewards, transition assumptions, and offline evaluation are credible.

For each candidate record parameter count, receptive field/context length, loss, constraints, random seeds, optimizer, early-stopping rule, computational budget, derivation reference, assumption check, and failure mode. Read the relevant derivation section before claiming why a model should work.

### 6. Run rolling, leakage-safe validation

Use expanding-window or rolling-window evaluation:

1. fit preprocessing and model selection on the past;
2. tune only inside the current development window;
3. forecast the next block;
4. apply a separately specified decision and cost layer;
5. move the window forward;
6. store forecasts, intervals, residuals, actions, costs, and model versions.

Do not select a model on the final test period and call that period out-of-sample. If the test period is used to revise the design, it becomes development data and a new untouched evaluation period is required.

Read `references/backtest_overfitting.md` and run `scripts/overfitting_applicability.py` before executing tests. Store all five records, including `not_applicable` reasons. Only an applicable diagnostic with `failed` status is a selection blocker.

### 7. Evaluate forecasts statistically and economically

Use metrics matched to the target:

- point: MAE, RMSE, MASE, directional accuracy;
- probability: log score, CRPS, quantile loss, coverage, PIT/reliability;
- volatility: QLIKE, volatility forecast loss, residual ARCH diagnostics;
- classification: log loss, Brier score, calibration, AUC as secondary;
- portfolio: net return, volatility, Sharpe/Sortino with caveats, max drawdown, turnover, costs, capacity, tail loss, factor exposures.

Use paired or block-bootstrap uncertainty for dependent observations. Compare forecasts with a suitable predictive-accuracy test. Report all material candidate configurations or the pre-specified selection rule; do not only show the winner.

### 8. Perform multi-round model and portfolio optimization

Treat each round as a controlled experiment, not an invitation to keep searching until a high return appears.

- Round 0: data and leakage audit.
- Round 1: statistical baselines.
- Round 2: feature and target ablations.
- Round 3: deep architectures and uncertainty heads.
- Round 4: calibration and distribution-shift checks.
- Round 5: portfolio optimization with costs, constraints, and risk budget.
- Round 6: stress tests, sensitivity to seeds/windows/costs, and challenger comparison.

Freeze the evaluation protocol before round 5. Select a Pareto set using statistical validity, predictive performance, economic effectiveness, regime stability, and seed/window sensitivity. Publish weights, minimum stability thresholds, applicability decisions, and normalization before selection. “Best” means best under that declared utility, not best historical return.

### 9. Optimize the portfolio transparently

Separate forecasting from optimization. Given predicted return \hat\mu_t and covariance/risk estimate \hat\Sigma_t, compare sample covariance, Ledoit--Wolf shrinkage, factor covariance, and robust covariance before solving a constrained problem such as
\[
\max_w \; \hat\mu_t^\top w-\frac{\gamma}{2}w^\top\hat\Sigma_t w
-\kappa\|w-w_{t-1}\|_1
\]
subject to budget, leverage, bounds, liquidity, turnover, sector, factor, and ES/CVaR constraints. Record solver status, KKT residuals, active/binding constraints, forecast version, benchmark, active return, risk contribution, factor exposure, turnover attribution, cost attribution, and transaction-cost assumptions. If the optimization is infeasible, use a documented fallback: prior weights, minimum-risk portfolio, or cash; never silently relax constraints.

Read `references/portfolio_robustness.md` for the covariance definitions and perturb expected returns, covariance, costs, risk aversion, and constraint bounds. Report weight intervals, turnover intervals, objective changes, and the exact infeasibility reason for every stress cell.

### 10. Report the result

A complete output includes:

- source and data dictionary;
- leakage and quality audit;
- feature and label definitions;
- baseline and challenger model table;
- rolling forecast and calibration results;
- uncertainty and stress results;
- portfolio optimization problem and constraints;
- selected model/portfolio with selection rule;
- limitations, non-stationarity caveats, and no-guarantee statement;
- experiment manifest, model registry, source reconciliation, backtest-overfitting results, and covariance-robustness comparison;
- output level and preflight result;
- reproducible code, metadata, charts, and timestamps.

### 11. Produce the compact reader-facing artifacts

Create a structured `analysis.json` after model selection. It must contain the research contract, source registry, data quality facts, module records, forecast record, decision rows, and reproducibility footer. Run:

```bash
python3 scripts/validate_research_config.py examples/research_config.json
python3 scripts/validate_experiment_manifest.py examples/experiment_manifest.json
python3 scripts/validate_schemas.py
python3 scripts/run_preflight.py \
  --config examples/research_config.json \
  --manifest examples/experiment_manifest.json \
  --analysis examples/demo_analysis.json \
  --output artifacts/preflight.json
python3 scripts/generate_financial_html.py examples/demo_analysis.json \
  --config examples/research_config.json \
  --manifest examples/experiment_manifest.json \
  --output-dir artifacts \
  --decision-format both
```

Before delivery, open the generated HTML in a browser or render it with an available HTML renderer and verify that the key forecast, as-of time, uncertainty, module statuses, and decision table are visible without network access. Deliver the HTML and decision table alongside the detailed report; do not substitute the HTML for the audit trail.

Use language such as “under this sample and protocol” and “model-implied scenario,” not “the market will.”

## Failure and stopping rules

Stop and ask for direction when the target, horizon, asset identity, output level, or risk limits materially change the task. Stop dependent analysis if preflight is `blocked`, a source cannot be verified, timestamps/lineage are unavailable, labels cross a purge/embargo boundary, or the data cannot support the requested claim. Stop multi-round search when two consecutive rounds do not improve the pre-specified out-of-sample objective or when the remaining gains are smaller than the uncertainty and implementation cost. Do not continue optimization solely because a more favorable backtest might be found.

## Supporting references

- Read references/model_derivations.md for the mathematical assumptions and derivations behind each supported model.
- Read references/java_data_layer.md when the source is a SQL database or Java/MyBatis retrieval is requested; use it for schema, type, mapper, provenance, and read-only safeguards.
- Read references/data_provenance.md before public-data retrieval or source selection.
- Read references/rolling_evaluation.md before any backtest, model selection, or portfolio optimization.
- Read references/backtest_overfitting.md before comparing multiple backtests or model trials.
- Read references/preflight_contract.md before selecting an output level or starting a run.
- Read references/feature_label_contract.md before building features, labels, or rolling splits.
- Read references/model_selection_protocol.md before selecting a model across multiple criteria.
- Read references/point_in_time_data.md and references/source_reconciliation.md before joining revised, filing, or multi-source data.
- Read references/portfolio_robustness.md before covariance selection or perturbation analysis.
- Read references/model_registry.md and experiment_manifest.schema.json before registering models or declaring a run reproducible.
- Read references/experiment_manifest.md when creating or reviewing the immutable run ledger.
- Use the existing gao-multivariate-statistical-analysis, linear-regression-analysis, mao-tang-bayesian-statistics, ross-elementary-mathematical-finance, and tsay-financial-data-analysis skills when available; this skill provides the workflow and audit contract, while those skills provide domain-specific judgment.
