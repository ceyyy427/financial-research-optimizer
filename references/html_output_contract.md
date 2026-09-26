# HTML, analysis JSON, and decision-table contract

This contract is for the mandatory reader-facing artifacts produced after financial data has been read and audited. It is intentionally small enough to be implemented by a script or another language. The same contract is used by the offline HTML generator and the decision table writer.

## Input JSON

The generator accepts an object with these fields:

```json
{
  "meta": {
    "title": "CSI 300 forecast brief",
    "generated_at": "2026-09-26T10:00:00+08:00",
    "as_of": "2026-09-25",
    "universe": "CSI 300",
    "target": "next 20-trading-day return",
    "horizon": "20 trading days",
    "cutoff": "2026-09-25"
  },
  "summary": {
    "headline": "Evidence is mixed; downside risk remains elevated.",
    "stance": "neutral",
    "confidence": "medium",
    "risk_note": "Forecast is sensitive to volatility regime and costs."
  },
  "forecast": {
    "label": "20-day return",
    "direction": "downside",
    "value": "-2.1%",
    "interval": "[-8.4%, 4.7%]",
    "probability": "0.61",
    "model": "ensemble-v3",
    "validity": "under the current regime and frozen rolling protocol"
  },
  "experiment_id": "spy-tlt-gld-20260926-exp001",
  "reproducibility_status": "complete",
  "charts": [
    {
      "chart_id": "forecast_path",
      "title": "滚动预测与实际",
      "type": "line",
      "unit": "收益率（%）",
      "labels": ["T-4", "T-3", "T-2", "T-1", "T"],
      "series": [
        {"name": "实际", "values": [-1.2, 0.8, -0.4, 1.1, -0.7]},
        {"name": "模型均值", "values": [-0.6, 0.4, 0.1, 0.7, -0.2]}
      ],
      "band": {"lower": [-2.2, -1.3, -1.8, -0.8, -2.0], "upper": [1.0, 2.1, 2.0, 2.2, 1.6]},
      "description": "实际收益、模型均值和预测区间。"
    }
  ],
  "modules": [
    {
      "module_id": "risk_tail",
      "title": "Risk and tail",
      "status": "ok",
      "summary": "Volatility is above its trailing median.",
      "facts": ["20d realized volatility: 24.0%"],
      "interpretation": ["Risk budget should remain conservative."],
      "confidence": "medium",
      "metrics": [{"label": "Max drawdown", "value": "-12.4%"}],
      "evidence_refs": ["calc:rolling_vol_20d"],
      "caveats": ["Short sample in the current regime."],
      "next_check": "next daily close"
    }
  ],
  "model_cards": [
    {
      "model_id": "ensemble-v3",
      "version": "3.0.0",
      "estimand": "20d excess return",
      "objective": "rolling log score plus net utility",
      "validation_protocol": "expanding window",
      "overfitting_diagnostics": {"DM": "pass", "SPA": "warning"},
      "failure_mode": "regime shift",
      "status": "active"
    }
  ],
  "backtest_overfitting": {
    "candidate_count": 4,
    "trial_count": 8,
    "gate_status": "warning",
    "methods": [
      {"method": "DM", "applicable": true, "reason": "paired losses exist", "input_requirements": ["paired_loss"], "blocking_level": "selection_blocker", "status": "pass", "statistic": 1.2, "p_value": 0.23, "interpretation": "no significant loss difference"},
      {"method": "WRC", "applicable": false, "reason": "one candidate family only", "input_requirements": ["multiple_candidates"], "blocking_level": "none", "status": "not_applicable", "interpretation": "not triggered"},
      {"method": "SPA", "applicable": false, "reason": "one candidate family only", "input_requirements": ["multiple_candidates"], "blocking_level": "none", "status": "not_applicable", "interpretation": "not triggered"},
      {"method": "DSR", "applicable": false, "reason": "no strategy returns", "input_requirements": ["portfolio_returns"], "blocking_level": "none", "status": "not_applicable", "interpretation": "not triggered"},
      {"method": "PBO", "applicable": false, "reason": "no multiple trials", "input_requirements": ["multiple_trials"], "blocking_level": "none", "status": "not_applicable", "interpretation": "not triggered"}
    ]
  },
  "source_reconciliation": {
    "status": "minor_difference",
    "counts": {"match": 1420, "minor_difference": 3, "material_conflict": 0},
    "stop_dependency_analysis": false,
    "tolerance": {"price_rel": 0.0001, "volume_rel": 0.005},
    "source_priority": ["official_exchange", "documented_api", "public_aggregator"]
  },
  "portfolio_robustness": {
    "covariance_models": [
      {"name": "sample", "solver_status": "optimal", "objective": "0.018", "turnover": "0.14", "weight_interval": "SPY 0.40-0.55", "active_constraints": "turnover"}
    ],
    "perturbation_summary": "Weights remain feasible under declared return/cost/covariance shocks.",
    "fallback": {"status": "not_used", "reason": "—"}
  },
  "decision_rows": [
    {
      "priority": "high",
      "module": "risk_tail",
      "current_view": "downside risk is elevated",
      "action": "keep exposure below the declared risk budget",
      "trigger": "20d volatility falls below threshold",
      "evidence": "calc:rolling_vol_20d",
      "risk": "regime reversal / model drift",
      "horizon": "20 trading days",
      "next_check": "next daily close"
    }
  ],
  "sources": [{"id": "source_1", "label": "Official index history", "url": "https://example.org/data"}],
  "reproducibility": {
    "data_snapshot": "snapshot-2026-09-25",
    "code": "scripts/run_research.py@abc123",
    "seeds": [7, 11, 19],
    "evaluation_window": "2024-01-01/2026-09-25",
    "limitations": ["Public data may be revised."]
  }
}
```

`facts` are observed values, `interpretation` is analysis, `forecast` is model output, and `decision_rows` are conditional research actions. Keep these namespaces separate. A missing or failed module must still be present with `status: "not_available"` or `status: "failed"` and a reason in `caveats`.

`experiment_id` and `reproducibility_status` are required for every completed run. The generator may obtain them from `experiment_manifest.json`, but the final HTML and decision table must expose them. A complete status means that snapshot hash, code version, environment, seeds, model parameters, feature version, train/evaluation windows, and output files are all recorded.

`model_cards`, `selection_protocol`, `backtest_overfitting`, `source_reconciliation`, and `portfolio_robustness` are required top-level audit blocks. The five backtest methods are exactly DM, WRC, SPA, DSR, and PBO; each method must declare `applicable`, `applicability_reason`, and `status`. `not_applicable` is not a failure. Source reconciliation must include tolerance, source priority, conflict status/counts, and `stop_dependency_analysis`. Portfolio robustness must include benchmark, active return, risk contribution, factor exposure, turnover/cost attribution, binding constraints, the four covariance families when applicable, perturbation results, and a documented infeasibility fallback.

The selected `output_level` is shown in the header and controls which blocks are required by preflight: `minimal`, `standard`, `research_grade`, or `portfolio_grade`.

The `analysis.json` must include a non-empty `charts` list. Metric figures are not decorative: at minimum include a forecast-vs-actual or forecast-distribution figure and the most decision-relevant risk or model-comparison figure. If a figure cannot be supported, record the reason and use a clearly labeled `not_available` chart rather than fabricating values.

## HTML acceptance criteria

- one standalone `.html` file; no CDN, remote JavaScript, font, or stylesheet;
- title, scope, as-of time, forecast target/horizon, uncertainty, and confidence visible above the fold;
- module cards show status, summary, key metrics, evidence IDs, caveats, and next check;
- decisions are visible as a compact table and do not read as unconditional trade instructions;
- source URLs and reproducibility fields appear in the footer;
- `experiment_id`, reproducibility status, manifest/config fingerprints, and source-conflict status are visible in the page header or audit sections;
- model cards, five-method overfitting diagnostics, source reconciliation, and covariance/perturbation results are visible as compact audit sections;
- supplied forecast metrics are rendered as labeled inline SVG charts; a completed run cannot omit `charts`;
- values are escaped as HTML and missing values are shown as `—`, never invented;
- a reader can understand the result without opening the long mathematical report.

## Decision table acceptance criteria

Use one row per material decision or monitoring item. Required columns are `priority`, `module`, `current_view`, `action`, `trigger`, `evidence`, `risk`, `horizon`, and `next_check`. Add `experiment_id` and `reproducibility_status` as table metadata or repeated fields in downstream systems. When the data-quality, source-reconciliation, or calibration gate fails, include an explicit `wait` or `insufficient evidence` row and do not present a dependent allocation as actionable.
