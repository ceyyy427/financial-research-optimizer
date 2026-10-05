from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS = ROOT / "docs" / "diagrams"
EXPECTED = (
    "finathink-overview.svg",
    "event-evidence.svg",
    "knowledge-path.svg",
    "quant-research.svg",
    "factor-workbench.svg",
    "strategy-risk.svg",
    "research-agents.svg",
    "report-learning.svg",
)
MODULE_TOKENS = (
    "--module-event",
    "--module-evidence",
    "--module-knowledge",
    "--module-data",
    "--module-quant",
    "--module-factor",
    "--module-risk",
    "--module-report",
)


def test_flow_diagram_set_has_accessible_svg_assets() -> None:
    for name in EXPECTED:
        path = DIAGRAMS / name
        assert path.is_file() and path.read_text(encoding="utf-8").strip(), name
        text = path.read_text(encoding="utf-8")
        assert "<svg" in text and "viewBox=" in text
        assert 'role="img"' in text and "<title" in text


def test_diagram_system_declares_module_colors_and_icon_rules() -> None:
    system = (ROOT / "docs" / "FINATHINK_DIAGRAM_SYSTEM.md").read_text(encoding="utf-8")
    for token in MODULE_TOKENS:
        assert token in system
    for phrase in ("图标", "箭头", "alt", "SVG"):
        assert phrase in system


def test_product_docs_expose_the_overview_and_module_diagrams() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    workbench = (ROOT / "docs" / "FACTOR_STRATEGY_WORKBENCH_GUIDE.md").read_text(encoding="utf-8")
    agents = (ROOT / "docs" / "RESEARCH_AGENT_GUIDE.md").read_text(encoding="utf-8")
    strategy = (ROOT / "docs" / "STRATEGY_RESEARCH_GUIDE.md").read_text(encoding="utf-8")

    assert "docs/diagrams/finathink-overview.svg" in readme
    assert "diagrams/factor-workbench.svg" in workbench
    assert "diagrams/research-agents.svg" in agents
    assert "diagrams/strategy-risk.svg" in strategy
