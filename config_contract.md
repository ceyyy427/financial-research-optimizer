# Research configuration contract

`research_config.json` is the single source of truth for a research run. Data audit, feature audit, rolling evaluation, portfolio optimization, model selection, and HTML generation must receive the same file or the same validated object. Do not duplicate horizon, cutoff, cost, or constraint values in separate scripts.

Validate it with:

```bash
python scripts/validate_research_config.py research_config.json
```

## Required sections

| Section | Meaning | Consumers |
|---|---|---|
| `universe` | asset IDs in the exact research universe | source binding, survivorship audit, portfolio |
| `target` | estimand such as `excess_return` | label construction, model card, forecast |
| `horizon` | forecast horizon, e.g. `20d` | labels, purge/embargo, costs |
| `frequency` | observation frequency | calendar, aggregation, evaluation |
| `cutoff` | last information date permitted | all stages and HTML as-of |
| `costs` | transaction, slippage, and borrow assumptions | decision and portfolio layer |
| `constraints` | turnover, drawdown, leverage and weight limits | optimizer and decision table |
| `risk_measure` / `confidence_level` | risk objective and tail confidence | CVaR/ES, stress, HTML |
| `evaluation` | expanding/rolling protocol and window sizes | rolling ledger, overfitting tests |
| `models` | baselines, challengers and frozen selection metrics | model card, selection |
| `output` | canonical artifact paths | audit, HTML and downstream handoff |
| `source_policy` | reconciliation tolerances and source priority | source conflict detector and provenance |

## Example

```json
{
  "universe": ["SPY", "TLT", "GLD"],
  "target": "excess_return",
  "horizon": "20d",
  "frequency": "daily",
  "cutoff": "2026-09-26",
  "costs": {"transaction_cost_bps": 10},
  "constraints": {"max_turnover": 0.25, "max_drawdown": 0.20},
  "risk_measure": "cvar",
  "confidence_level": 0.95,
  "evaluation": {"method": "expanding_window", "train_period": 756, "validation_period": 126, "test_period": 252},
  "models": {
    "baselines": ["historical_mean", "arma_garch"],
    "challengers": ["lstm", "transformer", "ensemble"],
    "selection": {"primary_metric": "mae", "calibration_metric": "coverage", "economic_metric": "net_cvar_adjusted_return"}
  },
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
