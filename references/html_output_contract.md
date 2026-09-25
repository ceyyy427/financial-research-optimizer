# HTML, analysis JSON, and decision-table contract

This contract is for the mandatory reader-facing artifacts produced after financial data has been read and audited. It is intentionally small enough to be implemented by a script or another language.

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

The `analysis.json` must include a non-empty `charts` list. Metric figures are not decorative: at minimum include a forecast-vs-actual or forecast-distribution figure and the most decision-relevant risk or model-comparison figure. If a figure cannot be supported, record the reason and use a clearly labeled `not_available` chart rather than fabricating values.

## HTML acceptance criteria

- one standalone `.html` file; no CDN, remote JavaScript, font, or stylesheet;
- title, scope, as-of time, forecast target/horizon, uncertainty, and confidence visible above the fold;
- module cards show status, summary, key metrics, evidence IDs, caveats, and next check;
- decisions are visible as a compact table and do not read as unconditional trade instructions;
- source URLs and reproducibility fields appear in the footer;
- supplied forecast metrics are rendered as labeled inline SVG charts; a completed run cannot omit `charts`;
- values are escaped as HTML and missing values are shown as `—`, never invented;
- a reader can understand the result without opening the long mathematical report.

## Decision table acceptance criteria

Use one row per material decision or monitoring item. Required columns are `priority`, `module`, `current_view`, `action`, `trigger`, `evidence`, `risk`, `horizon`, and `next_check`. When the data-quality or calibration gate fails, include an explicit `wait` or `insufficient evidence` row.
