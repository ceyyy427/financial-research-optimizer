# P4.5 Quant Research Validation

**Result:** PASS for the documented descriptive P4 scope

## Look-ahead bias

The shipped momentum factor uses trailing percentage change only. The engine
constructs forward returns with `pct_change(horizon).shift(-horizon)` and
`evaluate_factor` shifts factor values by one observation before alignment.
For the built-in path, the factor value available before a return interval is
compared with a later return, so future prices do not enter the factor.

The generic `FactorDefinition.compute` callable can be user-authored. P4 cannot
prove that an arbitrary callable is free of `shift(-n)` or other future-data
operations. Custom factors therefore require code review and documented input
semantics; the one-period shift is a safeguard, not a proof against malicious
or incorrectly written factor code.

## Data leakage

- Dataset validation requires non-empty, numeric, strictly positive prices and
  unique increasing dates.
- Provider output is normalized before it reaches research transformations.
- The factor is shifted and the forward-return horizon is explicit in the run.
- P4 does not train a model or select parameters, so train/test leakage is not
  created by the current engine.

Any future parameter selection, model fitting, or backtesting must introduce
explicit training/evaluation splits, walk-forward controls, and multiple-test
accounting before claiming predictive evidence.

## Factor meaning

The shipped momentum factor has:

- **Definition:** percentage change over a trailing observation window.
- **Mathematical meaning:** `price_t / price_(t-window) - 1`.
- **Input data:** validated close-price series.
- **Parameter:** positive integer window, embedded in its name and definition.
- **Limitations:** look-ahead/leakage caution, regime sensitivity, costs,
  survivorship bias, and multiple testing.
- **Evaluation method:** one-period-lagged Pearson information coefficient and
  aligned-sample coverage against a declared forward-return horizon.

`docs/FACTORS.md`, `src/finahinking/factors/core.py`, and factor tests agree on
these semantics. A future structured `factor_parameters` mapping would improve
machine-readable provenance.

## Statistical validity

- The engine rejects horizons below one and records the accepted horizon.
- `evaluate_factor` defaults to a one-period factor shift and rejects negative
  shifts.
- IC is the Pandas Pearson correlation of aligned non-missing factor and forward
  return values.
- Coverage is the aligned observation count divided by the factor-series count.
- Fewer than two aligned observations or constant factor/return input yields
  undefined IC, serialized as JSON `null`.

P4 does not report standard errors, p-values, confidence intervals, robust
covariance, multiple-testing correction, transaction costs, or out-of-sample
performance. Therefore IC is descriptive evidence only. The stored limitation
explicitly says it is not advice.

## Evidence

- Feature tests verify percentage returns, momentum, drawdown, rolling
  volatility, and correlation.
- Factor tests verify metadata, a known IC/coverage calculation, and constant
  input behavior.
- Experiment tests verify positive horizon enforcement, complete runs, and
  dataset-drift rejection.
- The deterministic notebook executes successfully offline.
- The complete suite contains 36 passing tests after the P4.5 governance and
  durable workflow tests.

## Decision

The built-in P4 quantitative path is temporally conservative, explicit about
its horizon and sample coverage, and appropriately limited to descriptive
research. **PASS.**
