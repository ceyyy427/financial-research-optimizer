# Content contract

## Purpose

This contract defines how a financial research run is presented so that a reader can distinguish data, inference, forecast, and decision.

## Required sections

### Research contract

State:

- universe and identifiers;
- target variable and horizon;
- observation frequency and timezone;
- information cutoff;
- development, validation, and final evaluation dates;
- cost, liquidity, leverage, shorting, turnover, and risk constraints;
- whether the output is descriptive, predictive, or decision-support.

### Evidence table

Use one row per material claim:

| Claim | Evidence type | Source/calculation | Time scope | Uncertainty or caveat |
|---|---|---|---|---|
| Market movement | observed | source URL/field | timestamp | adjustment/revision |
| Model forecast | estimated | saved model output | forecast origin | interval/calibration |
| Scenario | conditional | assumptions + model | horizon | not a fact |
| Portfolio result | simulated | backtest ledger | evaluation period | costs/capacity |

### Model card

| Model | Estimand | Objective | Main assumption | Validation | Failure mode |
|---|---|---|---|---|---|
| Baseline | conditional mean/variance/etc. | explicit loss | stated statistical structure | rolling | misspecification |
| Deep challenger | nonlinear conditional object | stated loss | capacity/regularization | rolling | overfit/drift |
| Decision layer | utility/risk objective | constrained optimization | cost/risk model | stress | infeasible/action mismatch |

### Forecast presentation

For every forecast, show point or distributional output, horizon, uncertainty, source/model version, and the condition under which it is valid. Never output a naked price target without the forecast origin and uncertainty.

### Portfolio presentation

Show objective, constraints, input forecast version, covariance/risk estimate, costs, solver status, active constraints, turnover, and fallback. If weights are produced, label them as model-implied or simulated and not as instructions to trade.

## Writing rules

Use “the data show” for observed data, “the model estimates” for fitted quantities, “under this scenario” for conditional projections, and “the optimizer returns” for computed weights. Use “may,” “is consistent with,” or “is sensitive to” when the evidence does not support a stronger statement.

## Reproducibility footer

Every durable report should finish with:

- retrieval timestamp;
- source URLs and local snapshot identifiers;
- data-processing script;
- model configuration and seeds;
- evaluation window;
- cost/risk assumptions;
- known limitations and next monitoring check.

