from __future__ import annotations

from finahinking.p8_2b.catalog import DEFAULT_KNOWLEDGE_CATALOG, get_knowledge_unit
from finahinking.p8_2b.export import export_bibtex, export_csl_json, export_latex, export_markdown


def test_exports_are_structured_and_keep_equation_and_reference_provenance() -> None:
    unit = get_knowledge_unit("sharpe")
    assert "Why now" in export_markdown(unit, DEFAULT_KNOWLEDGE_CATALOG)
    assert "\\begin{equation}" in export_latex(unit, DEFAULT_KNOWLEDGE_CATALOG)
    assert "@article{sharpe-1966" in export_bibtex(unit, DEFAULT_KNOWLEDGE_CATALOG)
    assert export_csl_json(unit, DEFAULT_KNOWLEDGE_CATALOG)[0]["id"] == "sharpe-1966"
