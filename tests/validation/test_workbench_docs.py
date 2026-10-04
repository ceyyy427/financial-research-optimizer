from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "FACTOR_STRATEGY_WORKBENCH_GUIDE.md"
VALIDATION = ROOT / "docs" / "FACTOR_STRATEGY_WORKBENCH_VALIDATION.md"
README = ROOT / "README.md"


def test_workbench_guide_covers_the_complete_phase_chain() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    for phrase in ("Data", "Factor", "Signal", "Position and risk", "Execution", "Explanation"):
        assert phrase in text
    for phrase in ("paper-only", "ResearchCharter", "ResearchSession", "freeze", "test/OOS", "workbench/index.html"):
        assert phrase.lower() in text.lower()


def test_workbench_docs_make_the_provider_and_execution_boundary_explicit() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in (GUIDE, VALIDATION, README)).lower()
    for phrase in ("api key", "live data", "broker", "real-money", "read-only", "paper-only"):
        assert phrase in text
    assert "no api key" in text or "api keys" in text


def test_workbench_docs_expose_page_payload_and_report_entries() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in (GUIDE, VALIDATION, README))
    assert "/workbench" in text
    assert "/api/research/workbench" in text
    assert "workbench/index.html" in text
    assert "FACTOR_STRATEGY_WORKBENCH_VALIDATION.md" in README.read_text(encoding="utf-8")
