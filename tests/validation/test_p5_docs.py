from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_p5_admission_matrix_records_every_candidate_and_classification() -> None:
    matrix = _read("docs/p5/COMPONENT_ADMISSION_MATRIX.md")
    for candidate in (
        "statsmodels",
        "PyPortfolioOpt",
        "Alphalens Reloaded",
        "Pyfolio Reloaded",
        "QuantStats",
        "bt",
        "vectorbt",
        "Riskfolio-Lib",
        "TA-Lib",
        "Backtrader",
    ):
        assert candidate in matrix
    for label in ("A — CORE CANDIDATE", "B — OPTIONAL ADAPTER", "C — REFERENCE ONLY", "D — REJECTED"):
        assert label in matrix
    assert "License" in matrix
    assert "macOS arm64" in matrix
    assert "Security" in matrix


def test_p5_dependency_plan_forbids_blind_installation() -> None:
    plan = _read("docs/p5/DEPENDENCY_PLAN.md")
    assert "pip install everything" in plan
    assert "No candidate is installed" in plan
    assert "pip check" in plan
    assert "dependency tree" in plan


def test_p5_optional_sandbox_records_controlled_statsmodels_install() -> None:
    sandbox = _read("docs/p5/OPTIONAL_SANDBOX.md")
    for marker in ("statsmodels==0.15.0", "BSD-3-Clause", "macOS arm64", "`pip check`: PASS"):
        assert marker in sandbox


def test_p5_admission_evidence_and_portfolio_scope_are_recorded() -> None:
    evidence = _read("docs/p5/ADMISSION_EVIDENCE.md")
    portfolio = _read("docs/p5/PORTFOLIO_LAYER.md")
    for marker in (
        "statsmodels",
        "B; isolated `0.15.0` adapter sandbox",
        "Riskfolio-Lib",
        "TA-Lib",
        "Backtrader",
        "BSD-3-Clause",
        "BSD-2-Clause",
        "Security",
        "not installed",
        "no benchmark was run",
    ):
        assert marker in evidence
    for marker in (
        "optimize_equal_weight_allocation",
        "validate_target_weights",
        "residual",
        "not an investment recommendation",
    ):
        assert marker in portfolio


def test_p5_gate_review_contains_acceptance_and_forbidden_scope() -> None:
    gate = _read("docs/phases/P5_GATE_REVIEW.md")
    for marker in (
        "P5 Gate Review",
        "Backtest Engine",
        "ResearchRun",
        "Provenance",
        "no data leakage",
        "cost model",
        "Benchmark",
        "License",
        "Audit Agent",
        "P6",
        "PASS",
    ):
        assert marker in gate


def test_project_state_records_p5_without_erasing_p4_5() -> None:
    state = _read("docs/PROJECT_STATE.md")
    assert "Current phase: P5 Quant Engine Foundation" in state
    for marker in ("P0 gate: PASS", "P1 gate: PASS", "P2 gate: PASS", "P3 gate: PASS", "P4 gate: PASS", "P4.5 | PASS"):
        assert marker in state
    assert "P6" in state
    assert "out of scope" in state
