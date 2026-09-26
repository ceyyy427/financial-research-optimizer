# Research configuration contract

`research_config.json` is the single source of truth for a research run. Preflight, data audit, feature/label audit, rolling evaluation, portfolio optimization, model selection, and HTML generation must receive the same file or the same validated object. Do not duplicate horizon, cutoff, cost, output level, or constraint values in separate scripts.

Validate it with:

```bash
python3 scripts/validate_research_config.py examples/research_config.json
```

## Required sections

| Section | Meaning | Consumers |
|---|---|---|
| `universe` | asset IDs in the exact research universe | source binding, survivorship audit, portfolio |
| `target` | estimand such as `excess_return` | label construction, model card, forecast |
| `horizon` | forecast horizon, e.g. `20d` | labels, purge/embargo, costs |
| `frequency` | observation frequency | calendar, aggregation, evaluation |
| `cutoff` | last information date permitted | all stages and HTML as-of |
| `output_level` | `minimal`, `standard`, `research_grade`, or `portfolio_grade` | preflight and artifact depth |
| `costs` | transaction, slippage, and borrow assumptions | decision and portfolio layer |
| `constraints` | turnover, drawdown, leverage and weight limits | optimizer and decision table |
| `risk_measure` / `confidence_level` | risk objective and tail confidence | CVaR/ES, stress, HTML |
| `evaluation` | expanding/rolling protocol and window sizes | rolling ledger, overfitting tests |
| `feature_label_contract` | availability time, lineage, purge, embargo, and label intervals | feature audit, rolling split, leakage gate |
| `models` | baselines, challengers and frozen selection metrics | model card, selection |
| `output` | canonical artifact paths | audit, HTML and downstream handoff |
| `source_policy` | reconciliation tolerances and source priority | source conflict detector and provenance |

## Example

```json
{
  "universe": ["SPY", "TLT", "GLD"],
  "mode": "forecasting",
  "target": "excess_return",
  "horizon": "20d",
  "frequency": "daily",
  "cutoff": "2026-09-26",
  "output_level": "research_grade",
  "costs": {"transaction_cost_bps": 10},
  "constraints": {"max_turnover": 0.25, "max_drawdown": 0.20},
  "risk_measure": "cvar",
  "confidence_level": 0.95,
  "evaluation": {"method": "expanding_window", "train_period": 756, "validation_period": 126, "test_period": 252},
  "models": {
    "baselines": ["historical_mean", "arma_garch"],
    "challengers": ["lstm", "transformer", "ensemble"],
    "selection": {"primary_metric": "mae", "calibration_metric": "coverage", "economic_metric": "net_cvar_adjusted_return", "stability_metric": "regime_seed_window_score", "criteria": {"statistical_validity": 0.20, "predictive_performance": 0.30, "economic_effectiveness": 0.25, "regime_stability": 0.15, "seed_window_sensitivity": 0.10}}
  },
  "feature_label_contract": {"availability_time_field": "availability_time", "purge_period": 20, "embargo_period": 5, "features": [{"feature_id": "lagged_return_5d", "formula": "log_return[t-4:t]", "source_ids": ["prices"], "observation_time": "t", "availability_time": "close_timestamp", "forecast_origin": "next_open_timestamp", "label_horizon": "20d", "purge_required": true, "embargo_required": true, "point_in_time_safe": true, "lineage": ["prices.close"]}], "labels": [{"label_id": "excess_return_20d", "formula": "sum(return[t+1:t+20])", "source_ids": ["prices"], "observation_time": "t", "availability_time": "label_end_close_timestamp", "forecast_origin": "next_open_timestamp", "label_horizon": "20d", "purge_required": true, "embargo_required": true, "point_in_time_safe": true, "name": "excess_return_20d", "target": "excess_return", "horizon": "20d", "label_start": "t+1", "label_end": "t+20", "overlap_group": "20d_forward_return", "lineage": ["prices.close"]}]},
  "output": {
    "artifact_dir": "artifacts",
    "analysis_json": "analysis.json",
    "html_file": "financial_research_brief.html",
    "decision_table_csv": "decision_table.csv",
    "decision_table_md": "decision_table.md"
  },
  "source_policy": {
    "price_abs_tolerance": 0.00000001,
    "price_rel_tolerance": 0.0001,
    "volume_abs_tolerance": 1,
    "volume_rel_tolerance": 0.005,
    "priority": ["official_exchange", "documented_api", "licensed_database", "public_aggregator"]
  }
}
```

## Configuration invariants

- `cutoff` is an information cutoff, not merely the last row in a revised dataset.
- `horizon` and `frequency` determine label overlap and therefore purge/embargo requirements.
- `transaction_cost_bps` and `max_turnover` are frozen before model selection.
- `max_drawdown` is a risk limit, not a promise that realized drawdown will stay below it.
- `evaluation` windows are applied chronologically; no random split is allowed for time series.
- `models.selection` is declared before final-test inspection.
- `output` paths are relative to the run directory and must be recorded in the provenance manifest.
