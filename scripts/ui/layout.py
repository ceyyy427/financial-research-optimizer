"""Dashboard layout primitives."""
from .components import explanation_cards, kpi_cards, source_matrix
from .charts import chart_controls
from .status import status_badge


def dashboard_chrome(data):
    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    online = data.get("online_status", {}) if isinstance(data.get("online_status"), dict) else {}
    status = data.get("status", online.get("data_status", "completed"))
    tabs = (("overview", "Overview"), ("why", "Why this forecast"), ("forecast", "Forecast"), ("risk", "Risk"), ("portfolio", "Portfolio"), ("provenance", "Provenance"), ("learning", "Learning mode"))
    tab_html = "".join(f'<button type="button" data-tab="{key}" aria-selected="{str(key == "overview").lower()}">{label}</button>' for key, label in tabs)
    forecast = data.get("forecast", {}) if isinstance(data.get("forecast"), dict) else {}
    return f'''<section class="dashboard-topbar" aria-label="研究运行状态"><div><h1>{meta.get("title", "Financial research dashboard")}</h1><div class="meta">数据时点：{meta.get("as_of", meta.get("as_of_time", "—"))} · 运行：{data.get("experiment_id", "—")}</div></div><div class="dashboard-statuses">{status_badge(status)}{status_badge(online.get("freshness_status", "not_available"))}{status_badge(forecast.get("calibration_status", "uncalibrated"))}</div></section><nav class="dashboard-nav" aria-label="研究区域">{tab_html}</nav>{chart_controls(data)}<section id="overview" data-panel="overview" class="dashboard-kpis" aria-label="关键指标">{kpi_cards(data)}</section><section id="why" data-panel="why">{explanation_cards(data)}</section><section id="learning" data-panel="learning" class="learning-mode"><h2>Learning mode</h2><p class="muted">展开解释卡查看模型机制、公式、证据引用和失败边界；本地交互不会创建新的金融结果。</p></section>'''


def anchor_sections(html_text):
    replacements = [("<h2>预测指标图</h2>", '<h2 id="forecast" data-panel="forecast">预测指标图</h2>'), ("<h2>尾部风险与分布敏感性</h2>", '<h2 id="risk" data-panel="risk">尾部风险与分布敏感性</h2>'), ("<h2>组合稳健性</h2>", '<h2 id="portfolio" data-panel="portfolio">组合稳健性</h2>'), ("<h2>来源与复现</h2>", '<h2 id="provenance" data-panel="provenance">来源与复现</h2>')]
    for old, new in replacements:
        html_text = html_text.replace(old, new, 1)
    return html_text
