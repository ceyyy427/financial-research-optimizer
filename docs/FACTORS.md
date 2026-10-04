# Factor documentation

## Trailing momentum

`momentum_factor(window)` computes the percentage change from the price at the
start of the trailing window to the current price. It is useful as a descriptive
strength signal, not as a prediction or recommendation.

`evaluate_factor` shifts the factor by one observation by default before
comparing it with forward returns. Keep that default (or document any explicit
override) and define the forecast horizon to avoid look-ahead bias or direct
data leakage. Results are also sensitive to transaction costs, regime changes,
survivorship bias, and multiple testing. Constant or insufficient history
inputs have an undefined information coefficient rather than a forced numeric
score. Factor and forward-return series must use the same unique, increasing
index; missing observations are dropped after the causal shift, while infinite
values and ambiguous alignment fail explicitly.
