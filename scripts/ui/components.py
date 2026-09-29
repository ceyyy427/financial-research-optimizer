"""Small presentation components; values are read-only artifact fields."""
import html
import json

from .status import status_badge


def _text(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def kpi_cards(data):
    forecast = data.get("forecast", {}) if isinstance(data.get("forecast"), dict) else {}
    online = data.get("online_status", {}) if isinstance(data.get("online_status"), dict) else {}
    tail = data.get("tail_risk", {}) if isinstance(data.get("tail_risk"), dict) else {}
    portfolio = data.get("portfolio_robustness", {}) if isinstance(data.get("portfolio_robustness"), dict) else {}
    cards = [
        ("预测值", _text(forecast.get("value")), forecast.get("forecast_status", forecast.get("direction", "not_available"))),
        ("预测模型", _text(forecast.get("model")), forecast.get("calibration_status", "uncalibrated")),
        ("来源新鲜度", _text(online.get("freshness_status", online.get("freshness", "not_available"))), online.get("freshness_status", "not_available")),
        ("组合求解", _text(portfolio.get("solver_status", "not_available")), portfolio.get("status", "not_available")),
        ("VaR / ES", f'{_text(tail.get("var"))} / {_text(tail.get("cvar", tail.get("es")))}', "risk"),
        ("实验 ID", _text(data.get("experiment_id")), data.get("reproducibility_status", "not_available")),
    ]
    return "".join(f'<div class="dashboard-kpi"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong>{status_badge(state)}</div>' for label, value, state in cards)


def source_matrix(data):
    sources = data.get("sources", []) if isinstance(data.get("sources"), list) else []
    rows = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        maturity = source.get("maturity_level", source.get("maturity", "not_available"))
        freshness = source.get("freshness_status", source.get("freshness", "not_available"))
        pit = source.get("point_in_time_status", "not_available")
        health = source.get("health_status", "not_available")
        fallback = source.get("fallback_used", False)
        rows.append(f'<tr data-source="{html.escape(_text(source.get("id")), quote=True)}"><td><strong>{html.escape(_text(source.get("label", source.get("id"))))}</strong><br><code>{html.escape(_text(source.get("id")))}</code></td><td>{status_badge(maturity)}</td><td>{status_badge(freshness)}</td><td>{status_badge(pit)}</td><td>{status_badge(health)}</td><td>{status_badge("degraded" if fallback else "fresh", "YES" if fallback else "NO")}</td></tr>')
    if not rows:
        rows.append('<tr><td colspan="6">—</td></tr>')
    return '<section class="source-matrix" id="provenance"><h2>来源可信度矩阵</h2><div class="table-wrap"><table><thead><tr><th>来源</th><th>执行级别</th><th>新鲜度</th><th>PIT</th><th>健康度</th><th>降级</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div></section>'


def explanation_cards(data):
    claims = data.get("knowledge_explanations", []) if isinstance(data.get("knowledge_explanations"), list) else []
    if not claims:
        return ""
    cards = []
    for claim in claims:
        formula = claim.get("formula", {}) if isinstance(claim.get("formula"), dict) else {}
        formula_asset = claim.get("formula_asset") if isinstance(claim.get("formula_asset"), dict) else {}
        asset = str(formula_asset.get("compiled_asset", ""))
        asset = asset if "/" in asset else ("formulas/" + asset if asset else "")
        formula_view = f'<img src="{html.escape(asset, quote=True)}" alt="{html.escape(_text(formula.get("alt_text")), quote=True)}">' if formula_asset.get("status") == "compiled" and asset else f'<span class="formula-unavailable">公式图像：{html.escape(_text(formula_asset.get("status", "not_available")))}</span>'
        variables = formula.get("variables", {}) if isinstance(formula.get("variables"), dict) else {}
        variable_html = "；".join(f"{html.escape(str(key))}={html.escape(_text(value))}" for key, value in variables.items()) or "—"
        cards.append(f'''<article class="explanation-card" data-claim-type="{html.escape(_text(claim.get("claim_type")), quote=True)}"><div class="module-head"><h3>{html.escape(_text(claim.get("title")))}</h3>{status_badge(claim.get("confidence", "not_available"))}</div><p>{html.escape(_text(claim.get("statement")))}</p><div class="formula-card"><span>公式：{html.escape(_text(formula.get("alt_text")))}</span>{formula_view}<details><summary>变量说明</summary><p>{variable_html}</p></details><details><summary>查看 TeX 源码</summary><code>{html.escape(_text(formula.get("tex")))}</code></details></div><details><summary>证据、限制与下一检查</summary><p>证据：{html.escape(_text(claim.get("evidence_refs")))}</p><p>计算：{html.escape(_text(claim.get("calculation_refs")))}</p><p>限制：{html.escape(_text(claim.get("caveats")))}</p><p>下一检查：{html.escape(_text(claim.get("next_check")))}</p></details></article>''')
    return '<section id="explainable" class="explainable"><h2>为什么模型得到这个结果？</h2><p class="muted">解释由已验证 artifact 生成；它描述预测关系，不自动宣称因果关系。</p><div class="modules">' + "".join(cards) + '</div></section>'
