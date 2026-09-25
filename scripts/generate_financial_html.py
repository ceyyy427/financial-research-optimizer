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


DECISION_FIELDS = [
    "priority", "module", "current_view", "action", "trigger",
    "evidence", "risk", "horizon", "next_check"
]


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
    for field in ("meta", "summary", "forecast", "modules", "decision_rows"):
        if field not in data:
            errors.append(f"missing top-level field: {field}")
    if not isinstance(data.get("modules"), list) or not data.get("modules"):
        errors.append("modules must be a non-empty list")
    if not isinstance(data.get("decision_rows"), list) or not data.get("decision_rows"):
        errors.append("decision_rows must be a non-empty list")
    forecast = data.get("forecast")
    if isinstance(forecast, dict):
        for field in ("label", "value", "interval", "probability", "model"):
            if not forecast.get(field):
                errors.append(f"forecast missing field: {field}")
    for index, module in enumerate(data.get("modules", [])):
        if not isinstance(module, dict):
            errors.append(f"module {index} must be an object")
            continue
        for field in ("module_id", "title", "status", "summary", "evidence_refs", "caveats", "next_check"):
            if field not in module:
                errors.append(f"module {index} missing field: {field}")
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


def normalize_rows(rows):
    normalized = []
    for row in rows if isinstance(rows, list) else []:
        normalized.append({field: text(row.get(field)) if isinstance(row, dict) else "—" for field in DECISION_FIELDS})
    if not normalized:
        normalized.append({field: "—" for field in DECISION_FIELDS})
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
        "risk": "风险", "horizon": "有效期", "next_check": "下一检查"
    }
    head = "".join(f"<th>{headers[field]}</th>" for field in DECISION_FIELDS)
    body = "".join("<tr>" + "".join(f"<td>{esc(row.get(field))}</td>" for field in DECISION_FIELDS) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def write_decision_table(rows, output_dir, fmt):
    written = []
    if fmt in {"csv", "both"}:
        path = output_dir / "decision_table.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=DECISION_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        written.append(path)
    if fmt in {"md", "both"}:
        path = output_dir / "decision_table.md"
        labels = ["优先级", "模块", "当前判断", "动作/姿态", "触发条件", "依据", "风险", "有效期", "下一检查"]
        lines = ["| " + " | ".join(labels) + " |", "|" + "|".join("---" for _ in labels) + "|"]
        lines.extend("| " + " | ".join(row[field].replace("|", "\\|") for field in DECISION_FIELDS) + " |" for row in rows)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)
    return written


def render_html(data):
    meta = data.get("meta", {})
    summary = data.get("summary", {})
    forecast = data.get("forecast", {})
    rows = normalize_rows(data.get("decision_rows"))
    modules = data.get("modules", []) if isinstance(data.get("modules", []), list) else []
    sources = data.get("sources", []) if isinstance(data.get("sources", []), list) else []
    reproducibility = data.get("reproducibility", {})
    spark = render_sparkline(data.get("series"))
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
:root{{--ink:#172033;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;--accent:#2563eb;--good:#15803d;--warn:#b45309;--bad:#b91c1c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1120px;margin:auto;padding:24px}}h1,h2,h3,p{{margin-top:0}}h1{{font-size:clamp(24px,4vw,36px);margin-bottom:6px}}h2{{font-size:18px;margin:24px 0 10px}}h3{{font-size:16px;margin:0}}.muted,small{{color:var(--muted)}}.meta{{color:var(--muted);display:flex;gap:8px;flex-wrap:wrap}}.hero,.module,.decision,.foot{{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 4px 18px #0f172a0a}}.hero{{padding:20px;display:grid;grid-template-columns:1.4fr 1fr;gap:16px;align-items:center}}.headline{{font-size:18px;font-weight:650}}.forecast{{padding:16px;border-radius:12px;background:#eff6ff;border:1px solid #bfdbfe}}.forecast .value{{font-size:28px;font-weight:750}}.badge{{display:inline-block;border-radius:999px;padding:2px 9px;font-size:12px;background:#e2e8f0;color:#475569}}.badge.ok{{background:#dcfce7;color:var(--good)}}.badge.warning{{background:#fef3c7;color:var(--warn)}}.badge.failed,.badge.not_available{{background:#fee2e2;color:var(--bad)}}.modules{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}.module{{padding:15px}}.module-head{{display:flex;justify-content:space-between;gap:8px;align-items:center}}.summary{{margin:9px 0;color:#334155}}.metrics{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}.metric{{background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:7px 9px;min-width:100px}}.metric span{{display:block;font-size:11px;color:var(--muted)}}.metric strong{{font-size:16px}}details{{color:#475569;font-size:13px}}summary{{cursor:pointer;color:var(--accent)}}ul{{padding-left:18px;margin:5px 0 10px}}.table-wrap{{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:14px}}table{{border-collapse:collapse;width:100%;min-width:900px}}th,td{{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}}th{{background:#f1f5f9;font-size:12px;white-space:nowrap}}td{{font-size:13px}}.foot{{padding:15px;color:#475569;font-size:12px}}.foot code{{word-break:break-word}}.spark{{width:100%;max-width:360px;height:64px;margin-top:10px}}.spark polyline{{fill:none;stroke:var(--accent);stroke-width:2.5}}@media(max-width:720px){{main{{padding:14px}}.hero{{grid-template-columns:1fr}}}}
</style></head><body><main>
<header><h1>{esc(title)}</h1><div class="meta"><span>As of: {esc(meta.get("as_of"))}</span><span>Generated: {esc(meta.get("generated_at"))}</span><span>Universe: {esc(meta.get("universe"))}</span><span>Target: {esc(meta.get("target"))}</span><span>Horizon: {esc(meta.get("horizon"))}</span></div></header>
<section class="hero"><div><p class="headline">{esc(summary.get("headline"))}</p><p>{esc(summary.get("risk_note"))}</p><span class="badge {status_class(summary.get("confidence"))}">置信度：{esc(summary.get("confidence"))}</span>{spark}</div><div class="forecast"><small>{esc(forecast.get("label"))} · {esc(forecast.get("model"))}</small><div class="value">{esc(forecast.get("value"))}</div><div>方向：<b>{esc(forecast.get("direction"))}</b> · 概率：{esc(forecast.get("probability"))}</div><div>区间：{esc(forecast.get("interval"))}</div><small>有效条件：{esc(forecast.get("validity"))}</small></div></section>
<h2>模块化分析</h2><section class="modules">{module_html}</section>
<h2>决策表</h2><section class="decision">{render_decisions(rows)}</section>
<h2>来源与复现</h2><footer class="foot"><ul>{source_html}</ul><div>数据快照：{esc(reproducibility.get("data_snapshot"))} · 代码：{esc(reproducibility.get("code"))} · 种子：{esc(reproducibility.get("seeds"))} · 评估窗口：{esc(reproducibility.get("evaluation_window"))}</div><div>局限：{esc(limitations)}</div><div>本页面是模型研究与决策支持摘要，不是收益保证或自动交易指令。</div></footer>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="structured analysis JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--decision-format", choices=["csv", "md", "both"], default="both")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("input JSON must be an object")
    validate_payload(data)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    html_path = args.output_dir / "financial_research_brief.html"
    html_path.write_text(render_html(data), encoding="utf-8")
    rows = normalize_rows(data.get("decision_rows"))
    outputs = [html_path] + write_decision_table(rows, args.output_dir, args.decision_format)
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
