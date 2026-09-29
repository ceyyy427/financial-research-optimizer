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
        run_id = data.get("run_id", data.get("experiment_id", ""))
        rows.append(f'<tr data-source="{html.escape(_text(source.get("id")), quote=True)}" data-run-id="{html.escape(_text(run_id), quote=True)}" data-index="{len(rows)}"><td><strong>{html.escape(_text(source.get("label", source.get("id"))))}</strong><br><code>{html.escape(_text(source.get("id")))}</code></td><td>{status_badge(maturity)}</td><td>{status_badge(freshness)}</td><td>{status_badge(pit)}</td><td>{status_badge(health)}</td><td>{status_badge("degraded" if fallback else "fresh", "YES" if fallback else "NO")}</td></tr>')
    if not rows:
        rows.append('<tr><td colspan="6">—</td></tr>')
    return '<section class="source-matrix" id="provenance"><h2>来源可信度矩阵</h2><div class="table-wrap"><table><thead><tr><th>来源</th><th>执行级别</th><th>新鲜度</th><th>PIT</th><th>健康度</th><th>降级</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div></section>'


def explanation_cards(data):
    claims = data.get("knowledge_explanations", []) if isinstance(data.get("knowledge_explanations"), list) else []
    if not claims:
        return ""
    cards = []
    run_id = data.get("run_id", data.get("experiment_id", ""))
    for claim in claims:
        formula = claim.get("formula", {}) if isinstance(claim.get("formula"), dict) else {}
        formula_asset = claim.get("formula_asset") if isinstance(claim.get("formula_asset"), dict) else {}
        asset = str(formula_asset.get("compiled_asset", ""))
        asset = asset if "/" in asset else ("formulas/" + asset if asset else "")
        formula_view = f'<img src="{html.escape(asset, quote=True)}" alt="{html.escape(_text(formula.get("alt_text")), quote=True)}">' if formula_asset.get("status") == "compiled" and asset else f'<span class="formula-unavailable">公式图像：{html.escape(_text(formula_asset.get("status", "not_available")))}</span>'
        variables = formula.get("variables", {}) if isinstance(formula.get("variables"), dict) else {}
        variable_html = "".join(f'<button type="button" class="formula-variable" data-variable="{html.escape(str(key), quote=True)}" data-unit="not_available" data-current-value="not_available" data-source="{html.escape(_text((claim.get("source_ids") or ["not_available"])[0]), quote=True)}">{html.escape(str(key))}：{html.escape(_text(value))}</button>' for key, value in variables.items()) or "—"
        source_attr = ",".join(str(item) for item in claim.get("source_ids", []))
        calc_id = claim.get("calculation_id") or (claim.get("calculation_refs") or [""])[0]
        cards.append(f'''<article class="explanation-card" tabindex="0" data-claim-id="{html.escape(_text(claim.get("claim_id")), quote=True)}" data-claim-type="{html.escape(_text(claim.get("claim_type")), quote=True)}" data-calculation-id="{html.escape(_text(calc_id), quote=True)}" data-source="{html.escape(source_attr, quote=True)}" data-run-id="{html.escape(_text(run_id), quote=True)}"><div class="module-head"><h3>{html.escape(_text(claim.get("title")))}</h3>{status_badge(claim.get("confidence", "not_available"))}</div><p>{html.escape(_text(claim.get("statement")))}</p><div class="formula-card" data-formula-id="{html.escape(_text(formula.get("formula_id")), quote=True)}" data-claim-id="{html.escape(_text(claim.get("claim_id")), quote=True)}" data-calculation-id="{html.escape(_text(calc_id), quote=True)}" data-source="{html.escape(source_attr, quote=True)}" data-run-id="{html.escape(_text(run_id), quote=True)}"><span>公式：{html.escape(_text(formula.get("alt_text")))}</span>{formula_view}<details><summary>变量说明</summary><div class="formula-variables">{variable_html}</div></details><details><summary>查看 TeX 源码</summary><code>{html.escape(_text(formula.get("tex")))}</code></details></div><details><summary>证据、限制与下一检查</summary><p>证据：{html.escape(_text(claim.get("evidence_refs")))}</p><p>计算：{html.escape(_text(claim.get("calculation_refs")))}</p><p>来源：{html.escape(_text(claim.get("source_ids")))}</p><p>限制：{html.escape(_text(claim.get("caveats")))}</p><p>下一检查：{html.escape(_text(claim.get("next_check")))}</p></details></article>''')
    return '<section id="explainable" class="explainable"><h2>为什么模型得到这个结果？</h2><p class="muted">解释由已验证 artifact 生成；它描述预测关系，不自动宣称因果关系。</p><div class="modules">' + "".join(cards) + '</div></section>'


def learning_cards(data):
    payload = data.get("learning_cards", {}) if isinstance(data.get("learning_cards"), dict) else {}
    cards = payload.get("cards", []) if isinstance(payload.get("cards"), list) else []
    if not cards:
        return '<p class="muted">没有可展示的学习卡。</p>'
    run_id = data.get("run_id", data.get("experiment_id", ""))
    rendered = []
    for card in cards:
        formula = card.get("formula", {}) if isinstance(card.get("formula"), dict) else {}
        variables = "；".join(f"{key}={_text(value)}" for key, value in (card.get("variables") or {}).items()) or "—"
        lesson = card.get("lesson", {}) if isinstance(card.get("lesson"), dict) else {}
        source_attr = ",".join(str(item) for item in card.get("source_ids", []))
        calc_id = (card.get("lineage_refs") or [""])[0]
        rendered.append(f'<article class="learning-card" tabindex="0" data-learning-card-id="{html.escape(_text(card.get("card_id")), quote=True)}" data-concept="{html.escape(_text(card.get("concept")), quote=True)}" data-formula-id="{html.escape(_text(card.get("formula_id")), quote=True)}" data-calculation-id="{html.escape(_text(calc_id), quote=True)}" data-source="{html.escape(source_attr, quote=True)}" data-run-id="{html.escape(_text(run_id), quote=True)}"><div class="module-head"><h3>{html.escape(_text(card.get("concept")))}</h3>{status_badge(card.get("status", "not_available"))}</div><p>{html.escape(_text(lesson.get("observation", "not_available")))}</p><details><summary>概念、公式与推导</summary><p>{html.escape(_text(lesson.get("mechanism", "not_available")))}</p><p><b>{html.escape(_text(formula.get("alt_text", "公式不可用")))}</b></p><code>{html.escape(_text(formula.get("tex", "")))}</code><p>变量：{html.escape(variables)}</p><ol>{"".join(f"<li>{html.escape(_text(item))}</li>" for item in card.get("derivation_steps", []))}</ol></details><details><summary>例子、适用条件与失败边界</summary><p>数值例子：{html.escape(_text(card.get("numeric_example")))}</p><p>适用：{html.escape(_text(card.get("applicability")))}</p><p>失败边界：{html.escape(_text(card.get("failure_boundaries")))}</p></details><details><summary>自测问题</summary><ol>{"".join(f"<li>{html.escape(_text(item))}</li>" for item in card.get("self_test", []))}</ol></details></article>')
    return '<section class="learning-library"><div class="modules">' + "".join(rendered) + '</div></section>'
