# Content contract

## Purpose

This contract defines how a financial research run is presented so that a reader can distinguish data, inference, forecast, and decision.

## Mandatory post-read deliverables

After a financial dataset has been read and audited, produce all of the following:

1. a structured `analysis.json` containing the contract, provenance, module records, forecast, model cards, overfitting diagnostics, portfolio robustness, decisions, and reproducibility footer;
2. a concise self-contained HTML file generated from that JSON;
3. a decision table in CSV and/or Markdown.

The HTML is the executive view, not the source of truth. The JSON, raw snapshot, audit report, model ledger, and forecast ledger remain the evidence trail.

## Module record contract

Use one record per applicable module. The default module set is data/provenance, descriptive market state, statistical structure, risk/tail, forecast/model comparison, and decision/scenarios. A module may be `not_available`, but must explain the missing field, time range, source, or quality gate.

```json
{
  "module_id": "risk_tail",
  "title": "Risk and tail",
  "status": "ok",
  "observed_facts": ["..."],
  "interpretation": ["..."],
  "forecast": {"target": "...", "horizon": "...", "value": "...", "interval": "...", "probability": 0.0},
  "confidence": "medium",
  "key_metrics": [{"label": "max_drawdown", "value": "...", "unit": "%"}],
  "evidence_refs": ["calc:volatility_rolling_20d"],
  "caveats": ["..."],
  "next_check": "..."
}
```

Keep `observed_facts`, `interpretation`, `forecast`, and `decision` separate. Do not place a model output in `observed_facts`.

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

| Model | Estimand | Objective | Main assumption | Validation | Overfitting diagnostics | Failure mode |
|---|---|---|---|---|---|---|
| Baseline | conditional mean/variance/etc. | explicit loss | stated statistical structure | rolling | DM/WRC/SPA/DSR/PBO | misspecification |
| Deep challenger | nonlinear conditional object | stated loss | capacity/regularization | rolling | DM/WRC/SPA/DSR/PBO | overfit/drift |
| Decision layer | utility/risk objective | constrained optimization | cost/risk model | stress | PBO/DSR + perturbation | infeasible/action mismatch |

Each model card must include `model_id`, `version`, `feature_version`, `derivation_refs`, training/evaluation windows, parameters, seeds, covariance model when relevant, and overfitting-diagnostic results.

### Forecast presentation

For every forecast, show point or distributional output, horizon, uncertainty, source/model version, and the condition under which it is valid. Never output a naked price target without the forecast origin and uncertainty.

### Portfolio presentation

Show objective, constraints, input forecast version, covariance/risk estimate, costs, solver status, active constraints, turnover, and fallback. If weights are produced, label them as model-implied or simulated and not as instructions to trade.

Compare sample covariance, Ledoit–Wolf, factor, and robust covariance. Show perturbation scenarios for expected returns, covariance, transaction costs, risk aversion, and constraint bounds, with weight/turnover intervals, objective changes, and infeasibility reasons.

### Reproducibility and source conflict

Show `experiment_id`, `reproducibility_status`, data snapshot hash, code/environment versions, seeds, feature version, training/evaluation windows, and output file hashes. Also show source reconciliation status, conflict counts, tolerance, source priority, and whether dependent analysis was stopped.

### Decision table

Use one row per material decision or monitoring item:

| Priority | Module | Current view | Action/stance | Trigger | Evidence | Risk | Horizon | Next check |
|---|---|---|---|---|---|---|---|---|
| high | forecast | model-implied downside | reduce exposure / wait | probability or threshold | forecast/model id | model drift | 20d | next close |

The table must include “wait/insufficient evidence” when gates fail. Never convert a forecast directly into an unconditional trade instruction.

### HTML presentation

The HTML should fit the reader's first screen plus a short scroll. Show, in order: as-of stamp and scope, one-line conclusion, forecast badge with interval/probability, 4–6 module cards, key metrics, decision table, and a compact sources/limitations footer. Use inline CSS and optional inline SVG only. Avoid remote assets, large tables, long derivations, or unqualified point estimates.

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
