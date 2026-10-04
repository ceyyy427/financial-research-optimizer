from __future__ import annotations

from datetime import date

from finahinking.factors.core import momentum_factor
from finahinking.quant.services import QuantServiceGateway
from finahinking.research import (
    FactorHealth,
    FactorHealthStatus,
    FactorMetadata,
    FactorRegistry,
    LearningStore,
    OfflineDriver,
    ReportBundleWriter,
    ResearchOrchestrator,
    ResearchPlan,
    ResearchRequest,
    ResearchToolGateway,
    stable_digest,
)
from finahinking.research.learning import reconcile_learning
from finahinking.research.reports import verify_report_bundle


def run_slice(root):
    quant = QuantServiceGateway()
    quant.register("quant.run_backtest", lambda params: {"annual_return": 0.1, "oos": True})
    quant.register("quant.analyze_risk", lambda params: {"passed": True, "max_drawdown": 0.08})
    tools = ResearchToolGateway(quant_gateway=quant)
    request = ResearchRequest(
        run_id="vertical-slice",
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(
            hypotheses=("trend",),
            required_datasets=("fixture-prices",),
            factor_ids=("momentum.v1",),
        ),
        analyst_roles=("fundamentals", "technical", "learning"),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg-fixture",
    )
    registry = FactorRegistry()
    registry.register(
        momentum_factor(20),
        FactorMetadata(
            factor_id="momentum.v1",
            version="1.0.0",
            definition="trailing return",
            formula="close / close.shift(20) - 1",
            input_fields=("close",),
            source="fixture",
            pit=True,
            direction="positive",
            limits={},
            validation_spec={"shift_periods": 1, "oos": True},
        ),
        FactorHealth(FactorHealthStatus.VALID, "2026-10-01", 0.05, 0.4, 0.1, 0.1, 0.1, 100, "fixture"),
    )
    result = ResearchOrchestrator().run(request, OfflineDriver(), tools)
    manifest = ReportBundleWriter().write(result, root / "reports")
    store = LearningStore(root / "learning.jsonl", current_as_of="2026-10-01")
    for entry in reconcile_learning(request.run_id, result.state.analyst_reports, result.decision, request.as_of):
        store.record_evidence(entry)
    assert verify_report_bundle(root / "reports" / request.run_id / "manifest.json").ok
    return result, manifest, store


def test_offline_vertical_slice_is_reproducible_and_reportable(tmp_path) -> None:
    first, first_manifest, first_store = run_slice(tmp_path / "first")
    second, second_manifest, second_store = run_slice(tmp_path / "second")

    assert first.state.current_state.value == "LEARNING_RECORDED"
    assert stable_digest(first.state) == stable_digest(second.state)
    assert stable_digest(first.decision) == stable_digest(second.decision)
    assert {key: value for key, value in first_manifest.files.items() if key != "activity.jsonl"} == {
        key: value for key, value in second_manifest.files.items() if key != "activity.jsonl"
    }
    assert first_store.digest() == second_store.digest()
