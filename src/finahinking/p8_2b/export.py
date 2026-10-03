"""Stable learner/researcher exports for a validated knowledge unit."""

from __future__ import annotations

from .catalog import KnowledgeCatalog
from .contracts import KnowledgeUnit
from .math import render_latex


def _refs(unit: KnowledgeUnit, catalog: KnowledgeCatalog):
    return [record for record in catalog.references.records() if record.reference_id in unit.references]


def export_markdown(unit: KnowledgeUnit, catalog: KnowledgeCatalog) -> str:
    equations = "\n".join(f"- `{equation.equation_id}`: `{render_latex(equation.expression)}` — {equation.meaning}" for equation in unit.equations)
    return f"# {unit.title}\n\n## Why now\n{unit.why_now}\n\n## Background\n{unit.background}\n\n## Intuition\n{unit.intuition}\n\n## Equations\n{equations}\n\n## Assumptions\n" + "\n".join(f"- {item}" for item in unit.assumptions) + "\n\n## Limitations\n" + "\n".join(f"- {item}" for item in unit.limitations) + "\n\n## References\n" + "\n".join(f"- {record.title} ({record.year}) — {record.doi or record.url}" for record in _refs(unit, catalog)) + "\n"


def export_latex(unit: KnowledgeUnit, catalog: KnowledgeCatalog) -> str:
    equations = "\n".join(f"\\begin{{equation}}\\label{{eq:{equation.equation_id}}}{render_latex(equation.expression)}\\end{{equation}}" for equation in unit.equations)
    return f"\\section{{{unit.title}}}\n\\paragraph{{Why now.}} {unit.why_now}\n\\paragraph{{Background.}} {unit.background}\n{equations}\n"


def export_bibtex(unit: KnowledgeUnit, catalog: KnowledgeCatalog) -> str:
    return "\n\n".join(record.bibtex() for record in _refs(unit, catalog))


def export_csl_json(unit: KnowledgeUnit, catalog: KnowledgeCatalog) -> list[dict[str, object]]:
    return [record.to_csl_json() for record in _refs(unit, catalog)]
