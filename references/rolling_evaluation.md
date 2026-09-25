# Rolling evaluation and multi-round selection

## Default split

Use an expanding or rolling window. Within each window:

1. fit preprocessing on the training portion;
2. tune hyperparameters on the validation portion;
3. forecast a future block;
4. record the forecast before seeing the outcome;
5. move the window forward.

Never randomize temporal observations for a financial forecast.

## Minimum candidate set

Compare a naive or historical-mean baseline, a linear/ridge model, a time-series volatility model when relevant, and the requested deep model. For a distributional target, compare at least one parametric distribution and one quantile model.

## Metrics and uncertainty

Use a target-appropriate proper scoring rule. For dependent forecast errors, use block bootstrap or a serial-dependence-aware comparison. Report point estimate, uncertainty interval, number of forecasts, and effective evaluation period. For portfolios, separate gross returns, costs, turnover, capacity, and drawdown.

## Backtest-overfitting gate

Before final model selection, run and record DM, White Reality Check, SPA, Deflated Sharpe Ratio, and PBO as specified in `references/backtest_overfitting.md`. They consume the same frozen rolling ledger and candidate family. A failure, unavailable input, unresolved source conflict, point-in-time violation, or incomplete experiment manifest blocks a `selected` status and must produce a `wait/insufficient evidence` decision row.

## Multi-round rule

Freeze the evaluation window, metric definitions, costs, and risk constraints before comparing deep challengers. Use a Pareto selection set rather than selecting only the largest historical return. An optional utility may be

U = z(score) + a z(calibration) + b z(net_risk_adjusted_return)
    - c z(turnover) - d z(drawdown) - e z(model_instability),

where a,b,c,d,e are declared before final selection. If two consecutive rounds fail to improve out-of-sample utility or stability, stop searching.

## Portfolio layer

Given forecast mu_t and risk estimate Sigma_t, solve a constrained problem. Log solver status, active constraints, infeasibility, and fallback. Do not silently change constraints after observing results. Stress the result under higher costs, larger covariance, lower liquidity, and alternative windows.

Compare sample covariance, Ledoit–Wolf shrinkage, factor covariance, and robust covariance under the identical objective and constraints. Perturb expected returns, covariance, transaction costs, risk aversion, and constraint boundaries. Report componentwise weight intervals, turnover intervals, objective changes, active constraints, solver status, and the reason for any infeasibility. Use the pre-registered fallback when infeasible.

## Required final claims

State the selected model, selection rule, evaluation dates, source data, main uncertainty, and known failure boundary. Never use “optimal” without specifying the objective, constraints, and information set.
