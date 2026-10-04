from __future__ import annotations

from datetime import date

from finahinking.research.contracts import (
    FailureKind,
    ResearchPlan,
    ResearchRequest,
    stable_digest,
)
from finahinking.research.drivers import (
    CodexInteractiveDriver,
    CompatibleApiDriver,
    OfflineDriver,
    UserApiDriver,
)
from finahinking.research.providers import (
    ModelEnvelope,
    ModelResponse,
    ProviderCapabilities,
)


def request() -> ResearchRequest:
    return ResearchRequest(
        run_id="run-driver",
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(hypotheses=("trend",)),
        analyst_roles=("technical", "learning"),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg",
    )


def test_offline_driver_is_deterministic_and_marked_offline() -> None:
    driver = OfflineDriver()
    first = driver.propose(request(), {"fixture": "v1"})
    second = driver.propose(request(), {"fixture": "v1"})

    assert stable_digest(first) == stable_digest(second)
    assert first.reports[0].model_ref == "offline/fixture-v1"
    assert first.reports[0].status == "OFFLINE"


def test_codex_driver_only_returns_reviewable_handoff_envelope() -> None:
    result = CodexInteractiveDriver().propose(request(), {"tool_names": ["quant.run_backtest"]})

    assert result.requires_external_turn is True
    assert result.envelope is not None
    assert result.envelope.tool_names == ()
    assert result.envelope.prompt_digest
    assert "api_key" not in str(result.envelope)
    assert "execute" not in result.envelope.instructions.lower()


def test_user_api_driver_requires_explicit_adapter_and_never_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "must-not-be-read")
    result = UserApiDriver(selection=None, adapter=None).propose(request(), {})
    assert result.failure_kind is FailureKind.PROVIDER_NOT_CONFIGURED


class ExplicitAdapter:
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(True, False, False, 4096, False)

    def invoke(self, envelope: ModelEnvelope) -> ModelResponse:
        return ModelResponse(
            provider="explicit",
            model="model-v1",
            content={"status": "READY", "claims": ["explicit result"]},
        )


def test_user_api_driver_uses_only_explicit_adapter() -> None:
    result = UserApiDriver(
        selection={"provider": "explicit", "model": "model-v1"},
        adapter=ExplicitAdapter(),
    ).propose(request(), {})
    assert result.failure_kind is None
    assert result.reports[0].claims == ("explicit result",)


def test_compatible_driver_is_explicitly_unavailable_without_sdk() -> None:
    result = CompatibleApiDriver().propose(request(), {})
    assert result.failure_kind is FailureKind.PROVIDER_NOT_CONFIGURED

