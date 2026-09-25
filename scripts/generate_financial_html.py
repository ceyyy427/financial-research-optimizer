#!/usr/bin/env python3
"""Generate a compact offline HTML brief and decision table from analysis JSON.

The script renders presentation artifacts only. It does not fit models, fetch data,
or turn a forecast into an unconditional trade instruction.
"""
import argparse
import csv
import json
import html
from pathlib import Path
from urllib.parse import urlparse
from config_utils import load_config
from manifest_utils import load_manifest


DECISION_FIELDS = [
    "priority", "module", "current_view", "action", "trigger",
    "evidence", "risk", "horizon", "next_check"
]
DECISION_METADATA_FIELDS = ["experiment_id", "reproducibility_status"]
DECISION_OUTPUT_FIELDS = DECISION_FIELDS + DECISION_METADATA_FIELDS


def text(value, fallback="—"):
    if value is None or value == "":
        return fallback
    if isinstance(value, (list, tuple)):
        return "; ".join(text(v, "") for v in value if v is not None)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def esc(value, fallback="—"):
    return html.escape(text(value, fallback))


def safe_url(value):
    """Allow only ordinary web links in the generated document."""
    if not value:
        return None
    parsed = urlparse(str(value))
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return html.escape(str(value), quote=True)
    return None


def validate_payload(data):
    """Fail early when the mandatory reader-facing contract is incomplete."""
    errors = []
    for field in ("meta", "summary", "forecast", "charts", "modules", "model_cards", "backtest_overfitting", "portfolio_robustness", "decision_rows"):
        if field not in data:
            errors.append(f"missing top-level field: {field}")
    if not isinstance(data.get("modules"), list) or not data.get("modules"):
        errors.append("modules must be a non-empty list")
    if not isinstance(data.get("decision_rows"), list) or not data.get("decision_rows"):
        errors.append("decision_rows must be a non-empty list")
    if not isinstance(data.get("charts"), list) or not data.get("charts"):
        errors.append("charts must be a non-empty list; metric figures are mandatory")
    if not isinstance(data.get("model_cards"), list) or not data.get("model_cards"):
        errors.append("model_cards must be a non-empty list")
    diagnostics = data.get("backtest_overfitting")
    if not isinstance(diagnostics, dict) or not isinstance(diagnostics.get("methods"), list) or len(diagnostics.get("methods", [])) != 5:
        errors.append("backtest_overfitting.methods must contain DM, WRC, SPA, DSR, and PBO records")
    robustness = data.get("portfolio_robustness")
    if not isinstance(robustness, dict) or not isinstance(robustness.get("covariance_models"), list) or not robustness.get("covariance_models"):
        errors.append("portfolio_robustness.covariance_models must be a non-empty list")
    forecast = data.get("forecast")
    if isinstance(forecast, dict):
        for field in ("label", "value", "interval", "probability", "model"):
            if not forecast.get(field):
                errors.append(f"forecast missing field: {field}")
    for index, chart in enumerate(data.get("charts", [])):
        if not isinstance(chart, dict):
            errors.append(f"chart {index} must be an object")
            continue
        for field in ("chart_id", "title", "type", "labels", "series", "description"):
            if field not in chart:
                errors.append(f"chart {index} missing field: {field}")
        if chart.get("type") not in {"line", "bar"}:
            errors.append(f"chart {index} type must be line or bar")
    for index, module in enumerate(data.get("modules", [])):
        if not isinstance(module, dict):
            errors.append(f"module {index} must be an object")
            continue
        for field in ("module_id", "title", "status", "summary", "evidence_refs", "caveats", "next_check"):
            if field not in module:
                errors.append(f"module {index} missing field: {field}")
    for index, card in enumerate(data.get("model_cards", [])):
        if not isinstance(card, dict):
            errors.append(f"model card {index} must be an object")
            continue
        for field in ("model_id", "version", "estimand", "objective", "validation_protocol", "overfitting_diagnostics", "failure_mode", "status"):
            if field not in card:
                errors.append(f"model card {index} missing field: {field}")
    if isinstance(diagnostics, dict):
        methods = {str(item.get("method", "")).upper() for item in diagnostics.get("methods", []) if isinstance(item, dict)}
        missing_methods = {"DM", "WRC", "SPA", "DSR", "PBO"} - methods
        if missing_methods:
            errors.append(f"backtest_overfitting missing methods: {sorted(missing_methods)}")
    for index, row in enumerate(data.get("decision_rows", [])):
        if not isinstance(row, dict):
            errors.append(f"decision row {index} must be an object")
            continue
        for field in DECISION_FIELDS:
            if not row.get(field):
                errors.append(f"decision row {index} missing field: {field}")
    if errors:
        raise SystemExit("input contract errors:\n- " + "\n- ".join(errors))


def list_items(values):
    values = values if isinstance(values, list) else ([] if values is None else [values])
    if not values:
        return '<span class="muted">—</span>'
    return "<ul>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"


def status_class(status):
    value = str(status or "not_available").lower().replace(" ", "_")
    return value if value in {"ok", "warning", "failed", "not_available"} else "warning"


def normalize_rows(rows, experiment_id=None, reproducibility_status=None):
    normalized = []
    for row in rows if isinstance(rows, list) else []:
        normalized.append({field: text(row.get(field)) if isinstance(row, dict) else "—" for field in DECISION_FIELDS})
        normalized[-1]["experiment_id"] = text(experiment_id)
        normalized[-1]["reproducibility_status"] = text(reproducibility_status)
    if not normalized:
        normalized.append({field: "—" for field in DECISION_OUTPUT_FIELDS})
    return normalized


def render_sparkline(series):
    if not isinstance(series, list) or len(series) < 2:
        return ""
    try:
        values = [float(v) for v in series]
    except (TypeError, ValueError):
        return ""
    lo, hi = min(values), max(values)
    spread = hi - lo or 1.0
    points = []
    for i, value in enumerate(values):
        x = 4 + (i * 192 / (len(values) - 1))
        y = 44 - ((value - lo) / spread * 36)
        points.append(f"{x:.1f},{y:.1f}")
    return f'<svg class="spark" viewBox="0 0 200 48" role="img" aria-label="trend sparkline"><polyline points="{" ".join(points)}" /></svg>'


def render_metric_chart(chart, chart_index):
    """Render a small, labeled inline SVG chart for forecast metrics."""
    if not isinstance(chart, dict):
        return ""
    labels = chart.get("labels", [])
    series = chart.get("series", [])
    if not isinstance(labels, list) or len(labels) < 2 or not isinstance(series, list) or not series:
        return ""
    clean_series = []
    for item in series:
        if not isinstance(item, dict) or not isinstance(item.get("values"), list):
            continue
        try:
            values = [float(value) for value in item["values"]]
        except (TypeError, ValueError):
            continue
        if len(values) != len(labels):
            continue
        clean_series.append({"name": text(item.get("name")), "values": values})
    if not clean_series:
        return ""
    width, height = 680, 250
    left, right, top, bottom = 52, 18, 42, 38
    plot_w, plot_h = width - left - right, height - top - bottom
    flat = [value for item in clean_series for value in item["values"]]
    band = chart.get("band") if isinstance(chart.get("band"), dict) else None
    if band and isinstance(band.get("lower"), list) and isinstance(band.get("upper"), list):
        flat.extend(float(value) for value in band["lower"] if isinstance(value, (int, float)))
        flat.extend(float(value) for value in band["upper"] if isinstance(value, (int, float)))
    is_bar = chart.get("type") == "bar"
    lo = min(0.0, min(flat)) if is_bar else min(flat)
    hi = max(0.0, max(flat)) if is_bar else max(flat)
    spread = hi - lo or 1.0
    lo -= spread * 0.08
    hi += spread * 0.08

    def x(index):
        return left + (index * plot_w / max(1, len(labels) - 1))

    def y(value):
        return top + (hi - value) * plot_h / (hi - lo)

    grid = []
    for step in range(4):
        value = lo + (hi - lo) * step / 3
        yy = y(value)
        grid.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" class="chart-grid" />'
                    f'<text x="{left-8}" y="{yy+4:.1f}" text-anchor="end" class="chart-label">{value:.2f}</text>')
    x_labels = []
    for index, label in enumerate(labels):
        if len(labels) <= 7 or index in {0, len(labels) - 1}:
            x_labels.append(f'<text x="{x(index):.1f}" y="{height-12}" text-anchor="middle" class="chart-label">{esc(label)}</text>')

    marks = []
    palette = ["chart-series-1", "chart-series-2", "chart-series-3", "chart-series-4"]
    if is_bar:
        group_width = plot_w / len(labels)
        bar_width = min(26, group_width / max(1, len(clean_series)) * 0.68)
        for series_index, item in enumerate(clean_series):
            for index, value in enumerate(item["values"]):
                xx = left + index * group_width + group_width * 0.18 + series_index * bar_width
                yy = y(max(0, value))
                zero = y(0)
                marks.append(f'<rect x="{xx:.1f}" y="{min(yy, zero):.1f}" width="{bar_width:.1f}" height="{abs(zero-yy):.1f}" class="{palette[series_index % len(palette)]}" data-tooltip="{esc(item["name"])}: {value:.2f}" />')
    else:
        if band and len(band.get("lower", [])) == len(labels) and len(band.get("upper", [])) == len(labels):
            upper = " ".join(f"{x(i):.1f},{y(float(value)):.1f}" for i, value in enumerate(band["upper"]))
            lower = " ".join(f"{x(i):.1f},{y(float(value)):.1f}" for i, value in reversed(list(enumerate(band["lower"]))))
            marks.append(f'<polygon points="{upper} {lower}" class="chart-band" aria-label="prediction interval" />')
        for series_index, item in enumerate(clean_series):
            points = " ".join(f"{x(i):.1f},{y(value):.1f}" for i, value in enumerate(item["values"]))
            marks.append(f'<polyline points="{points}" class="{palette[series_index % len(palette)]}" fill="none" />')
            marks.extend(f'<circle cx="{x(i):.1f}" cy="{y(value):.1f}" r="3" class="{palette[series_index % len(palette)]}" data-tooltip="{esc(item["name"])}: {value:.2f}" />' for i, value in enumerate(item["values"]))
    legend = " ".join(f'<span><i class="legend-swatch {palette[i % len(palette)]}"></i>{esc(item["name"])}</span>' for i, item in enumerate(clean_series))
    desc = text(chart.get("description"), "预测指标图")
    return f'''<figure class="chart" aria-label="{esc(chart.get("title"))}">
      <figcaption><b>{esc(chart.get("title"))}</b><span>{esc(chart.get("unit"))}</span></figcaption>
      <svg viewBox="0 0 {width} {height}" role="img"><title>{esc(chart.get("title"))}</title><desc>{esc(desc)}</desc>
        {"".join(grid)}<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" class="chart-axis" />
        {"".join(marks)}{"".join(x_labels)}
      </svg><div class="legend">{legend}</div>
    </figure>'''


def render_metric_charts(charts):
    if not isinstance(charts, list):
        return ""
    rendered = "".join(render_metric_chart(chart, index) for index, chart in enumerate(charts))
    return rendered


def render_model_cards(cards):
    rows = []
    for card in cards:
        diagnostics = card.get("overfitting_diagnostics", {})
        diag_text = ", ".join(f"{key}:{value}" for key, value in diagnostics.items()) if isinstance(diagnostics, dict) else text(diagnostics)
        rows.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in (
            card.get("model_id"), card.get("version"), card.get("estimand"), card.get("objective"),
            card.get("validation_protocol"), diag_text, card.get("failure_mode"), card.get("status")
        )) + "</tr>")
    return f'''<div class="table-wrap"><table><thead><tr><th>模型</th><th>版本</th><th>估计对象</th><th>目标</th><th>验证</th><th>过拟合诊断</th><th>失败边界</th><th>状态</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'''


def render_backtest_overfitting(diagnostics):
    methods = diagnostics.get("methods", []) if isinstance(diagnostics, dict) else []
    rows = []
    for item in methods:
        rows.append("<tr>" + "".join(f"<td>{esc(item.get(field))}</td>" for field in ("method", "status", "statistic", "p_value", "interpretation")) + "</tr>")
    gate = diagnostics.get("hard_gate", "not_available") if isinstance(diagnostics, dict) else "not_available"
    return f'''<div class="audit-banner"><b>反过拟合硬门槛：{esc(gate)}</b><span>{esc(diagnostics.get("note"))}</span></div>
      <div class="table-wrap"><table><thead><tr><th>方法</th><th>状态</th><th>统计量</th><th>p/概率</th><th>解释</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'''


def render_reconciliation(reconciliation):
    if not isinstance(reconciliation, dict):
        return '<p class="muted">未提供数据源冲突审计。</p>'
    counts = reconciliation.get("counts", {})
    return f'''<div class="recon-grid"><div><b>状态</b><strong>{esc(reconciliation.get("status", reconciliation.get("overall_status")))}</strong></div><div><b>记录数</b><strong>{esc(reconciliation.get("records", reconciliation.get("total")))}</strong></div><div><b>冲突计数</b><strong>{esc(counts)}</strong></div><div><b>停止依赖分析</b><strong>{esc(reconciliation.get("stop_dependency_analysis"))}</strong></div></div>
      <p class="muted">容差：{esc(reconciliation.get("tolerance"))} · 来源优先级：{esc(reconciliation.get("source_priority"))}</p>'''


def render_portfolio_robustness(robustness):
    models = robustness.get("covariance_models", []) if isinstance(robustness, dict) else []
    rows = []
    for item in models:
        rows.append("<tr>" + "".join(f"<td>{esc(item.get(field))}</td>" for field in ("name", "solver_status", "objective", "turnover", "weight_interval", "active_constraints")) + "</tr>")
    fallback = robustness.get("fallback", {}) if isinstance(robustness, dict) else {}
    return f'''<div class="table-wrap"><table><thead><tr><th>协方差</th><th>求解状态</th><th>目标函数</th><th>换手率</th><th>权重区间</th><th>主动约束</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><p class="muted">扰动分析：{esc(robustness.get("perturbation_summary"))} · fallback：{esc(fallback)}</p>'''


def render_module(module):
    metrics = module.get("metrics", []) if isinstance(module, dict) else []
    metric_html = "".join(
        f'<div class="metric"><span>{esc(item.get("label"))}</span><strong>{esc(item.get("value"))}</strong></div>'
        for item in metrics if isinstance(item, dict)
    )
    evidence = module.get("evidence_refs", []) if isinstance(module, dict) else []
    evidence_html = ", ".join(esc(item) for item in evidence) or "—"
    status = status_class(module.get("status"))
    return f'''<article class="module {status}">
      <div class="module-head"><h3>{esc(module.get("title"))}</h3><span class="badge {status}">{esc(module.get("status"))}</span></div>
      <p class="summary">{esc(module.get("summary"))}</p>
      {f'<div class="metrics">{metric_html}</div>' if metric_html else ''}
      <details><summary>证据与限定</summary>
        <b>观察</b>{list_items(module.get("facts"))}
        <b>解释</b>{list_items(module.get("interpretation"))}
        <b>证据 ID</b><p>{evidence_html}</p>
        <b>置信度</b><p>{esc(module.get("confidence"))}</p>
        <b>限定</b>{list_items(module.get("caveats"))}
        <b>下一检查</b><p>{esc(module.get("next_check"))}</p>
      </details>
    </article>'''


def render_decisions(rows):
    headers = {
        "priority": "优先级", "module": "模块", "current_view": "当前判断",
        "action": "动作/姿态", "trigger": "触发条件", "evidence": "依据",
        "risk": "风险", "horizon": "有效期", "next_check": "下一检查",
        "experiment_id": "实验 ID", "reproducibility_status": "复现状态"
    }
    head = "".join(f"<th>{headers[field]}</th>" for field in DECISION_OUTPUT_FIELDS)
    body = "".join("<tr>" + "".join(f"<td>{esc(row.get(field))}</td>" for field in DECISION_OUTPUT_FIELDS) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def write_decision_table(rows, output_dir, fmt):
    written = []
    if fmt in {"csv", "both"}:
        path = output_dir / "decision_table.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=DECISION_OUTPUT_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        written.append(path)
    if fmt in {"md", "both"}:
        path = output_dir / "decision_table.md"
        labels = ["优先级", "模块", "当前判断", "动作/姿态", "触发条件", "依据", "风险", "有效期", "下一检查", "实验 ID", "复现状态"]
        lines = ["| " + " | ".join(labels) + " |", "|" + "|".join("---" for _ in labels) + "|"]
        lines.extend("| " + " | ".join(row[field].replace("|", "\\|") for field in DECISION_OUTPUT_FIELDS) + " |" for row in rows)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)
    return written


def render_html(data, config=None, manifest=None):
    meta = data.get("meta", {})
    summary = data.get("summary", {})
    forecast = data.get("forecast", {})
    modules = data.get("modules", []) if isinstance(data.get("modules", []), list) else []
    sources = data.get("sources", []) if isinstance(data.get("sources", []), list) else []
    reproducibility = data.get("reproducibility", {})
    experiment_id = (manifest or {}).get("experiment_id", data.get("experiment_id"))
    reproducibility_status = (manifest or {}).get("reproducibility_status", data.get("reproducibility_status", "not_available"))
    rows = normalize_rows(data.get("decision_rows"), experiment_id, reproducibility_status)
    spark = render_sparkline(data.get("series"))
    charts_html = render_metric_charts(data.get("charts", []))
    model_cards_html = render_model_cards(data.get("model_cards", []))
    overfit_html = render_backtest_overfitting(data.get("backtest_overfitting", {}))
    reconciliation_html = render_reconciliation(data.get("source_reconciliation", {}))
    portfolio_html = render_portfolio_robustness(data.get("portfolio_robustness", {}))
    source_html = "".join(
        f'<li><code>{esc(source.get("id"))}</code> {esc(source.get("label"))}'
        + (f' — <a href="{safe_url(source.get("url"))}">source</a>' if safe_url(source.get("url")) else "")
        + "</li>"
        for source in sources if isinstance(source, dict)
    ) or "<li>—</li>"
    limitations = reproducibility.get("limitations", []) if isinstance(reproducibility, dict) else []
    module_html = "".join(render_module(module) for module in modules) or '<article class="module not_available"><p>没有可呈现的模块记录。</p></article>'
    title = text(meta.get("title"), "Financial research brief")
    forecast_direction = status_class(forecast.get("direction", "warning"))
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>
:root{{--ink:#172033;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;--accent:#2563eb;--good:#15803d;--warn:#b45309;--bad:#b91c1c;--series1:#2563eb;--series2:#f97316;--series3:#16a34a;--series4:#9333ea}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1120px;margin:auto;padding:24px}}h1,h2,h3,p{{margin-top:0}}h1{{font-size:clamp(24px,4vw,36px);margin-bottom:6px}}h2{{font-size:18px;margin:24px 0 10px}}h3{{font-size:16px;margin:0}}.muted,small{{color:var(--muted)}}.meta{{color:var(--muted);display:flex;gap:8px;flex-wrap:wrap}}.hero,.module,.decision,.foot{{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 4px 18px #0f172a0a}}.hero{{padding:20px;display:grid;grid-template-columns:1.4fr 1fr;gap:16px;align-items:center}}.headline{{font-size:18px;font-weight:650}}.forecast{{padding:16px;border-radius:12px;background:#eff6ff;border:1px solid #bfdbfe}}.forecast .value{{font-size:28px;font-weight:750}}.badge{{display:inline-block;border-radius:999px;padding:2px 9px;font-size:12px;background:#e2e8f0;color:#475569}}.badge.ok{{background:#dcfce7;color:var(--good)}}.badge.warning{{background:#fef3c7;color:var(--warn)}}.badge.failed,.badge.not_available{{background:#fee2e2;color:var(--bad)}}.modules{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}.module{{padding:15px}}.module-head{{display:flex;justify-content:space-between;gap:8px;align-items:center}}.summary{{margin:9px 0;color:#334155}}.metrics{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}.metric{{background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:7px 9px;min-width:100px}}.metric span{{display:block;font-size:11px;color:var(--muted)}}.metric strong{{font-size:16px}}details{{color:#475569;font-size:13px}}summary{{cursor:pointer;color:var(--accent)}}ul{{padding-left:18px;margin:5px 0 10px}}.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}}.chart{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin:0;min-width:0}}.chart figcaption{{display:flex;justify-content:space-between;gap:8px;margin-bottom:4px}}.chart figcaption span{{color:var(--muted);font-size:12px}}.chart svg{{display:block;width:100%;height:auto}}.chart-grid{{stroke:#e2e8f0;stroke-width:1}}.chart-axis{{stroke:#94a3b8;stroke-width:1}}.chart-label{{fill:#64748b;font-size:11px}}.chart-series-1{{stroke:var(--series1);fill:var(--series1)}}.chart-series-2{{stroke:var(--series2);fill:var(--series2)}}.chart-series-3{{stroke:var(--series3);fill:var(--series3)}}.chart-series-4{{stroke:var(--series4);fill:var(--series4)}}polyline.chart-series-1,polyline.chart-series-2,polyline.chart-series-3,polyline.chart-series-4{{fill:none;stroke-width:2.5}}.chart-band{{fill:var(--series1);opacity:.12;stroke:none}}.legend{{display:flex;gap:12px;flex-wrap:wrap;color:#475569;font-size:12px}}.legend-swatch{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}}.audit-banner,.recon-grid{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:10px}}.audit-banner{{display:flex;gap:16px;flex-wrap:wrap}}.recon-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}.recon-grid b,.recon-grid strong{{display:block}}.recon-grid b{{font-size:11px;color:var(--muted)}}.recon-grid strong{{font-size:15px}}.table-wrap{{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:14px}}table{{border-collapse:collapse;width:100%;min-width:900px}}th,td{{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}}th{{background:#f1f5f9;font-size:12px;white-space:nowrap}}td{{font-size:13px}}.foot{{padding:15px;color:#475569;font-size:12px}}.foot code{{word-break:break-word}}.spark{{width:100%;max-width:360px;height:64px;margin-top:10px}}.spark polyline{{fill:none;stroke:var(--accent);stroke-width:2.5}}@media(max-width:720px){{main{{padding:14px}}.hero{{grid-template-columns:1fr}}}}
</style></head><body><main>
<header><h1>{esc(title)}</h1><div class="meta"><span>As of: {esc(meta.get("as_of"))}</span><span>Generated: {esc(meta.get("generated_at"))}</span><span>Universe: {esc(meta.get("universe"))}</span><span>Target: {esc(meta.get("target"))}</span><span>Horizon: {esc(meta.get("horizon"))}</span><span>Experiment: {esc(experiment_id)}</span><span>Reproducibility: {esc(reproducibility_status)}</span></div></header>
<section class="hero"><div><p class="headline">{esc(summary.get("headline"))}</p><p>{esc(summary.get("risk_note"))}</p><span class="badge {status_class(summary.get("confidence"))}">置信度：{esc(summary.get("confidence"))}</span>{spark}</div><div class="forecast"><small>{esc(forecast.get("label"))} · {esc(forecast.get("model"))}</small><div class="value">{esc(forecast.get("value"))}</div><div>方向：<b>{esc(forecast.get("direction"))}</b> · 概率：{esc(forecast.get("probability"))}</div><div>区间：{esc(forecast.get("interval"))}</div><small>有效条件：{esc(forecast.get("validity"))}</small></div></section>
<h2>模块化分析</h2><section class="modules">{module_html}</section>
{f'<h2>预测指标图</h2><section class="charts">{charts_html}</section>' if charts_html else ''}
<h2>模型卡</h2><section class="decision">{model_cards_html}</section>
<h2>反过拟合审计</h2><section class="decision">{overfit_html}</section>
<h2>数据源冲突审计</h2><section class="decision">{reconciliation_html}</section>
<h2>组合稳健性</h2><section class="decision">{portfolio_html}</section>
<h2>决策表</h2><section class="decision">{render_decisions(rows)}</section>
<h2>来源与复现</h2><footer class="foot"><ul>{source_html}</ul><div>数据快照：{esc(reproducibility.get("data_snapshot"))} · 代码：{esc(reproducibility.get("code"))} · 种子：{esc(reproducibility.get("seeds"))} · 评估窗口：{esc(reproducibility.get("evaluation_window"))}</div><div>配置：{esc((config or {}).get("_config_fingerprint"))} · Manifest：{esc((manifest or {}).get("_manifest_fingerprint"))}</div><div>局限：{esc(limitations)}</div><div>本页面是模型研究与决策支持摘要，不是收益保证或自动交易指令。</div></footer>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="structured analysis JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--decision-format", choices=["csv", "md", "both"], default="both")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("input JSON must be an object")
    config = load_config(args.config) if args.config else None
    manifest = load_manifest(args.manifest) if args.manifest else None
    if not manifest and not data.get("experiment_id"):
        raise SystemExit("an experiment manifest or analysis.experiment_id is required")
    if manifest:
        data.setdefault("experiment_id", manifest["experiment_id"])
        data.setdefault("reproducibility_status", manifest["reproducibility_status"])
    validate_payload(data)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    html_path = args.output_dir / "financial_research_brief.html"
    html_path.write_text(render_html(data, config=config, manifest=manifest), encoding="utf-8")
    experiment_id = (manifest or {}).get("experiment_id", data.get("experiment_id"))
    reproducibility_status = (manifest or {}).get("reproducibility_status", data.get("reproducibility_status", "not_available"))
    rows = normalize_rows(data.get("decision_rows"), experiment_id, reproducibility_status)
    outputs = [html_path] + write_decision_table(rows, args.output_dir, args.decision_format)
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
