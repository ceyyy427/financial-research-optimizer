"""Interactive chart controls that filter existing SVG marks only."""
import html


def chart_controls(data):
    models = []
    sources = []
    for item in data.get("model_cards", []) if isinstance(data.get("model_cards"), list) else []:
        if isinstance(item, dict) and item.get("model_id"):
            models.append(str(item["model_id"]))
    for item in data.get("sources", []) if isinstance(data.get("sources"), list) else []:
        if isinstance(item, dict) and item.get("id"):
            sources.append(str(item["id"]))
    model_options = "".join(f'<option value="{html.escape(value, quote=True)}">{html.escape(value)}</option>' for value in sorted(set(models)))
    source_options = "".join(f'<option value="{html.escape(value, quote=True)}">{html.escape(value)}</option>' for value in sorted(set(sources)))
    return f'''<section class="dashboard-controls" aria-label="本地展示筛选"><label>时间范围<select data-ui-control="time_range"><option value="all">全部</option><option value="30d">30d</option><option value="60d">60d</option><option value="120d">120d</option></select></label><label>模型<select data-ui-control="model"><option value="all">全部模型</option>{model_options}</select></label><label>来源<select data-ui-control="source"><option value="all">全部来源</option>{source_options}</select></label><button type="button" data-action="theme" aria-pressed="false">切换主题</button><span class="muted" data-ui-message aria-live="polite">仅改变展示，不重新计算结果。</span></section>'''
