import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_p5_final_report_covers_every_acceptance_gate():
    report = _read("docs/reviews/P5_FINAL_VALIDATION_REPORT.md")
    for marker in (
        "PASS",
        "Backtest Engine",
        "ResearchRun",
        "Artifact",
        "QuantRun",
        "Provenance",
        "no data leakage",
        "cost model",
        "Benchmark",
        "License",
        "Audit Agent",
        "P6",
        "Finathink P5 Quant Engine Foundation: COMPLETE",
    ):
        assert marker in report


def test_p5_state_is_gated_and_core_has_no_direct_optional_imports():
    state = _read("docs/PROJECT_STATE.md")
    for marker in ("Current phase: P5 Quant Engine Foundation", "P5 gate: PASS", "P5 status: PASS", "P6 implementation scope: out of scope"):
        assert marker in state
    forbidden = re.compile(r"^\s*(?:from|import)\s+(?:statsmodels|pypfopt|alphalens|pyfolio|quantstats|vectorbt)\b", re.MULTILINE)
    for path in (ROOT / "src" / "finahinking" / "quant").rglob("*.py"):
        if "adapters" not in path.parts:
            assert forbidden.search(path.read_text(encoding="utf-8")) is None
