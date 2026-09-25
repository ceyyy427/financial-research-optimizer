---
name: financial-research-optimizer
description: Search public financial data, validate time-series provenance, compare statistical and deep-learning models, run rolling forecasts, and optimize portfolios under explicit risk constraints. Use for evidence-backed financial forecasting or portfolio research; never use it to promise returns or place trades.
---

# Financial Research Optimizer

Use this skill when the user asks to discover financial data, analyze market direction, forecast prices/returns/volatility, compare statistical and deep-learning models, or optimize a portfolio from model outputs.

The objective is an auditable research result, not a guaranteed “best prediction.” Treat “best” as the model or portfolio that wins a pre-specified, risk-adjusted, out-of-sample comparison under stated costs and constraints.

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
3. **Market/content summary** — descriptive facts separated from interpretation; cite each external claim near its source.
4. **Feature and label construction** — formulas, information cutoff, transformations, and split logic.
5. **Model card table** — model, assumptions, objective, parameters, validation role, and known failure mode.
6. **Forecast evidence** — rolling metrics, uncertainty, calibration, regime slices, and challenger comparisons.
7. **Portfolio/decision layer** — objective, constraints, costs, solver status, active constraints, and fallback.
8. **Multi-round selection** — what changed per round, what improved, what failed, and why the selected model won.
9. **Scenario conclusion** — base, upside, and downside conditions; never write certainty as a fact.
10. **Limitations and reproducibility** — data snapshot, code, random seeds, version, and next monitoring actions.

Use tables for model comparisons and risk limits, equations for estimands and optimization problems, figures for time trends/calibration/regime structure, and short prose for interpretation. Do not hide sample size, denominator, units, or uncertainty in a footnote.

For a short answer, compress these sections but preserve the order and the distinction between observation, model output, scenario, and decision.

## Workflow construction

The workflow is a state machine with explicit handoffs:

`scope -> sources -> audit -> features -> baselines -> challengers -> rolling validation -> calibration -> portfolio optimization -> stress test -> selection -> report`

Each state must leave an artifact that can be inspected by the next state. A source list is not a data audit; a fitted model is not an out-of-sample forecast; a high forecast score is not a portfolio; and a portfolio backtest is not proof of future returns.

At every handoff, preserve the following invariants:

- the information cutoff is unchanged;
- all transformations are fit only on allowed historical data;
- the target definition and horizon are unchanged;
- the evaluation period remains untouched until selection;
- costs and constraints are not relaxed after seeing results;
- failed or rejected candidates remain recorded;
- every numerical claim can be traced to a source, calculation, or saved output.

Use the detailed workflow schema in `references/workflow_blueprint.md` and the output contract in `references/content_contract.md` when building a durable report or reusable dataset.

## Non-negotiable boundaries

- Do not promise profits, certainty, or a universally optimal forecast.
- Do not place orders, manage accounts, or send investment instructions unless a separate tool and explicit authorization cover that action.
- Separate descriptive facts, model-based forecasts, scenario projections, and investment decisions.
- Use public data only when the user has not provided authorized private data. Record source URL, access date, series/ticker, timezone, adjustment convention, and license/usage caveat.
- Never use future information: no random shuffling of time series, full-sample scaling, revised macro values unavailable at the forecast timestamp, final constituent lists for historical periods, or future-derived graphs/features.
- Do not invent missing observations, metrics, p-values, backtest returns, or model performance.
- If data are insufficient or sources conflict, stop dependent claims and report the exact gap.

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

If the user leaves these open, choose conservative defaults and state them. For directional questions, use lagged returns and volatility features; for risk questions, predict a distribution rather than only a point.

### 2. Search and bind public sources

Use web search for current, authoritative or reproducible sources. Prefer:

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

### 4. Establish statistical baselines

Always compare at least one interpretable baseline appropriate to the target:

- random walk or historical mean for prices/returns;
- ARMA/ARIMA for conditional means;
- GARCH or realized-volatility baseline for conditional variance;
- OLS/ridge/elastic-net for cross-sectional or factor models;
- logistic regression for direction;
- historical or parametric quantiles for tail risk.

Read references/model_derivations.md when deriving, explaining, or implementing a model. Use the assumptions and diagnostics there rather than describing a model as a black box.

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

For each candidate record parameter count, receptive field/context length, loss, constraints, random seeds, optimizer, early-stopping rule, and computational budget. Read the relevant derivation section before claiming why a model should work.

### 6. Run rolling, leakage-safe validation

Use expanding-window or rolling-window evaluation:

1. fit preprocessing and model selection on the past;
2. tune only inside the current development window;
3. forecast the next block;
4. apply a separately specified decision and cost layer;
5. move the window forward;
6. store forecasts, intervals, residuals, actions, costs, and model versions.

Do not select a model on the final test period and call that period out-of-sample. If the test period is used to revise the design, it becomes development data and a new untouched evaluation period is required.

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

Freeze the evaluation protocol before round 5. Select a Pareto set using out-of-sample forecast score, calibration, net risk-adjusted performance, turnover, capacity, and stability. If a single score is needed, publish its weights and normalization before selection. “Best” means best under that declared utility, not best historical return.

### 9. Optimize the portfolio transparently

Separate forecasting from optimization. Given predicted return \hat\mu_t and covariance/risk estimate \hat\Sigma_t, solve a constrained problem such as
\[
\max_w \; \hat\mu_t^\top w-\frac{\gamma}{2}w^\top\hat\Sigma_t w
-\kappa\|w-w_{t-1}\|_1
\]
subject to budget, leverage, bounds, liquidity, turnover, sector, factor, and ES/CVaR constraints. Record solver status, KKT residuals, active constraints, forecast version, and transaction-cost assumptions. If the optimization is infeasible, use a documented fallback: prior weights, minimum-risk portfolio, or cash; never silently relax constraints.

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
- reproducible code, metadata, charts, and timestamps.

Use language such as “under this sample and protocol” and “model-implied scenario,” not “the market will.”

## Failure and stopping rules

Stop and ask for direction when the target, horizon, asset identity, or risk limits materially change the task. Stop dependent analysis if a source cannot be verified, timestamps are unavailable, or the data cannot support the requested claim. Stop multi-round search when two consecutive rounds do not improve the pre-specified out-of-sample objective or when the remaining gains are smaller than the uncertainty and implementation cost. Do not continue optimization solely because a more favorable backtest might be found.

## Supporting references

- Read references/model_derivations.md for the mathematical assumptions and derivations behind each supported model.
- Read references/data_provenance.md before public-data retrieval or source selection.
- Read references/rolling_evaluation.md before any backtest, model selection, or portfolio optimization.
- Use the existing gao-multivariate-statistical-analysis, linear-regression-analysis, mao-tang-bayesian-statistics, ross-elementary-mathematical-finance, and tsay-financial-data-analysis skills when available; this skill provides the workflow and audit contract, while those skills provide domain-specific judgment.
