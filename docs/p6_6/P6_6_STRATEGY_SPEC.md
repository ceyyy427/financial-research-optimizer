# P6.6 StrategySpec Contract

`StrategySpec` is the reviewed meaning of a user's idea. It contains strategy
identity/version, original idea, research question, hypothesis, universe,
dataset reference, FeatureVersions, FeatureGraph fingerprint, signal/filter/
ranking/selection rules, entry/exit, position sizing, portfolio construction,
rebalance and execution timing, risk constraints, cost/slippage models,
benchmark, validation design, parameters, limitations, and a fingerprint.

The interpreter supports two deterministic templates:

1. `lagged_momentum_low_volatility`: lagged momentum ranks assets, a realized
   volatility threshold removes the high-volatility tail, top selection is
   equal-weighted, and orders execute on the next valid period.
2. `moving_average_trend`: a lagged moving-average condition controls a single
   long-only target weight, with next-period execution.

The review object exposes every material assumption. Compilation requires an
explicit `reviewed=True` acknowledgement in the local API; the compiler never
assumes that an interpretation was accepted.
