# P6.6 Backtest Configuration Studio

`BacktestConfiguration` groups typed settings for data/universe/period and
frequency, starting capital, signal and execution timing, rebalance timing,
fees, transaction cost, slippage, long-only leverage and position limits,
benchmark, training/validation/test windows, OOS mode, and walk-forward steps.

Validation rejects negative costs, invalid date ordering, execution before a
signal can exist, leverage outside the supported long-only range, zero-length
validation windows, missing availability semantics, and an unfrozen selection
configuration. `ResearchPreview` renders the question, hypothesis, strategy,
features, windows, lags, costs, benchmark, OOS design, and limitations before
the existing P5 engine runs.
