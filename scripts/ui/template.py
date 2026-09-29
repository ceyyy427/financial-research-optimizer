"""Dashboard shell around the existing artifact renderer."""
from .layout import anchor_sections, dashboard_chrome
from .components import source_matrix
try:
    from ..knowledge.explanation_engine import build_explanations
except ImportError:
    from knowledge.explanation_engine import build_explanations
from .theme import theme_css
from .state import state_json
from .interaction import interaction_js


def render_dashboard(data, config, manifest, legacy_renderer):
    """Enhance legacy HTML without calculating or mutating financial results."""
    if not data.get("knowledge_explanations"):
        data = dict(data)
        data["knowledge_explanations"] = build_explanations(data)
    if isinstance(data.get("formula_manifest"), dict):
        data = dict(data)
        assets = {item.get("formula_id"): item for item in data["formula_manifest"].get("formulas", []) if isinstance(item, dict)}
        data["knowledge_explanations"] = [dict(claim, formula_asset=assets.get(claim.get("formula_id"), {})) for claim in data.get("knowledge_explanations", [])]
    document = legacy_renderer(data, config=config, manifest=manifest)
    chrome = dashboard_chrome(data)
    document = document.replace("<body><main>", "<body><main>" + chrome, 1)
    document = document.replace("<h2>来源与复现</h2>", source_matrix(data) + "<h2>来源与复现</h2>", 1)
    document = anchor_sections(document)
    document = document.replace("</style>", theme_css() + "</style>", 1)
    document = document.replace("</body>", f'<script>window.__FRO_UI_STATE__={state_json(data.get("ui_state"), run_id=data.get("run_id", data.get("experiment_id")))};</script><script>{interaction_js()}</script></body>', 1)
    return document
