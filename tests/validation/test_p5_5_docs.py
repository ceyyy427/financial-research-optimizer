from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_p5_5_contracts_cover_required_dimensions_tools_and_scope() -> None:
    validity = _read("docs/p5_5/QUANT_RESEARCH_VALIDITY_CONTRACT.md")
    api = _read("docs/p5_5/P5_5_TOOL_API_SPEC.md")
    for marker in (
        "SUPPORTED",
        "LIMITED",
        "UNSUPPORTED",
        "NOT_APPLICABLE",
        "point-in-time",
        "available_at",
        "look-ahead",
        "IS/OOS",
        "multiple testing",
        "survivorship",
        "delisting",
        "corporate actions",
        "liquidity",
        "capacity",
        "market impact",
        "OOS",
        "QuantRun",
        "ResearchRun",
        "fingerprint",
    ):
        assert marker.casefold() in validity.casefold()
    for tool in (
        "quant.run_backtest",
        "quant.run_regression",
        "quant.evaluate_performance",
        "quant.analyze_risk",
        "quant.compare_benchmark",
        "quant.inspect_run",
    ):
        assert tool in api
    for marker in ("typed request", "typed response", "provenance", "warnings", "limitations", "arbitrary Python", "REJECTED"):
        assert marker.casefold() in api.casefold()


def test_p5_5_capability_matrix_records_no_install_decision() -> None:
    matrix = _read("docs/p5_5/P5_5_SKILL_CAPABILITY_MATRIX.md")
    assert "NO CAPABILITY GAP" in matrix or "No skill" in matrix
    assert "MCP" in matrix
    assert "statsmodels" in matrix
    assert "DEFERRED" in matrix
