"""Contract checks for the P6.6 documentation and stop boundary."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCS = (
    "P6_6_EXECUTION_PLAN.md",
    "P6_6_ARCHITECTURE.md",
    "P6_6_CAPABILITY_MATRIX.md",
    "STRATEGY_RESEARCH_CONSTITUTION.md",
    "P6_6_CARRY_FORWARD_RISKS.md",
    "P6_6_FEATURE_CONTRACT.md",
    "P6_6_FEATURE_GRAPH.md",
    "P6_6_STRATEGY_SPEC.md",
    "P6_6_STRATEGY_IR.md",
    "P6_6_CODE_GENERATION_CONTRACT.md",
    "P6_6_CODE_MATH_FINANCE_LEARNING.md",
    "P6_6_BACKTEST_CONFIGURATION.md",
    "P6_6_PAPER_SIMULATION.md",
    "P6_6_EXPORT_CONTRACT.md",
    "P6_6_SECURITY_REVIEW.md",
    "P6_6_RESEARCH_VALIDITY_REVIEW.md",
    "P6_6_REPRODUCIBILITY_REVIEW.md",
    "P6_6_INDEPENDENT_AUDITS.md",
    "P6_6_FINAL_VALIDATION_REPORT.md",
    "P6_6_GATE_REVIEW.md",
    "P7_READINESS_REPORT.md",
)


def _read(name: str) -> str:
    path = ROOT / "docs" / "p6_6" / name
    assert path.is_file(), f"missing P6.6 document: {path}"
    value = path.read_text(encoding="utf-8")
    assert value.strip(), f"empty P6.6 document: {path}"
    return value


def test_p6_6_document_set_is_complete() -> None:
    docs = {name: _read(name) for name in REQUIRED_DOCS}
    assert "P6.6" in docs["P6_6_EXECUTION_PLAN.md"]
    assert "point-in-time" in docs["P6_6_FEATURE_CONTRACT.md"].casefold()
    assert "strategy" in docs["P6_6_STRATEGY_IR.md"].casefold()
    assert "paper" in docs["P6_6_PAPER_SIMULATION.md"].casefold()
    assert "security" in docs["P6_6_SECURITY_REVIEW.md"].casefold()
    assert "reproduc" in docs["P6_6_REPRODUCIBILITY_REVIEW.md"].casefold()


def test_p7_readiness_has_exact_three_way_decision() -> None:
    report = _read("P7_READINESS_REPORT.md")
    assert re.search(r"(?:^|\n)\s*(?:A|B|C)\s*[—-]\s*(?:READY|P6\.6 REWORK REQUIRED)", report, re.IGNORECASE)
