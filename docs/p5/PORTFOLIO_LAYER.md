# P5 Portfolio Layer

The P5 portfolio boundary contains two deliberately small, domain-owned
primitives:

- `validate_target_weights` validates finite asset weights, long-only policy,
  per-asset caps, and total exposure.
- `optimize_equal_weight_allocation` produces a deterministic sorted,
  equal-weight baseline subject to the same cap. If a cap prevents full
  investment, the residual is explicit cash rather than an implicit leverage
  assumption.

This is a transparent research allocation baseline, not an efficient-frontier
solver or expected-return forecast. This baseline is not an investment recommendation.
Sector,
liquidity, capacity, turnover, tax, corporate-action, and risk-budget
constraints remain future extension points. PyPortfolioOpt and Riskfolio-Lib
remain optional adapters and are not required by the P5 core.
