"""Dashboard layout primitives."""
from .components import explanation_cards, kpi_cards, source_matrix
from .status import status_badge


def dashboard_chrome(data):
    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    online = data.get("online_status", {}) if isinstance(data.get("online_status"), dict) else {}
    status = data.get("status", online.get("data_status", "completed"))
    return f'''<section class="dashboard-topbar" aria-label="研究运行状态"><div><h1>{meta.get("title", "Financial research dashboard")}</h1><div class="meta">数据时点：{meta.get("as_of", meta.get("as_of_time", "—"))} · 运行：{data.get("experiment_id", "—")}</div></div><div class="dashboard-statuses">{status_badge(status)}{status_badge(online.get("freshness_status", "not_available"))}{status_badge(data.get("forecast", {}).get("calibration_status", "uncalibrated"))}</div></section><nav class="dashboard-nav" aria-label="研究区域"><a href="#overview">Overview</a><a href="#explainable">Explainable</a><a href="#forecast">Forecast</a><a href="#risk">Risk</a><a href="#portfolio">Portfolio</a><a href="#provenance">Provenance</a></nav><section id="overview" class="dashboard-kpis" aria-label="关键指标">{kpi_cards(data)}</section>{explanation_cards(data)}'''


def anchor_sections(html_text):
    replacements = [("<h2>预测指标图</h2>", '<h2 id="forecast">预测指标图</h2>'), ("<h2>尾部风险与分布敏感性</h2>", '<h2 id="risk">尾部风险与分布敏感性</h2>'), ("<h2>组合稳健性</h2>", '<h2 id="portfolio">组合稳健性</h2>')]
    for old, new in replacements:
        html_text = html_text.replace(old, new, 1)
    return html_text
