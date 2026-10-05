from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_execution_report_declares_scope_and_plan() -> None:
    report = (ROOT / "docs/FINATHINK_AUTONOMOUS_EXECUTION_REPORT.md").read_text(encoding="utf-8").lower()
    plan = (ROOT / "docs/superpowers/plans/2026-10-05-finathink-autonomous-delivery-plan.md").read_text(encoding="utf-8").lower()
    for phrase in ("paper-only", "api key", "factor", "github", "停止标准"):
        assert phrase in report
    assert "finathink_autonomous_execution_report.md" in plan


def test_execution_report_keeps_live_provider_and_broker_deferred() -> None:
    report = (ROOT / "docs/FINATHINK_AUTONOMOUS_EXECUTION_REPORT.md").read_text(encoding="utf-8").lower()
    assert "不连接券商" in report
    assert "实时数据" in report
    assert "模型任意执行" in report

