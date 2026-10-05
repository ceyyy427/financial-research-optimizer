from __future__ import annotations

import pytest

from finahinking.research.contracts import ProviderSelection
from finahinking.research.providers import (
    ModelEnvelope,
    ModelResponse,
    ProviderCapabilities,
    ProviderRegistry,
)


class FakeAdapter:
    def __init__(self, capabilities: ProviderCapabilities) -> None:
        self._capabilities = capabilities

    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def invoke(self, envelope: ModelEnvelope) -> ModelResponse:
        return ModelResponse(provider="fake", model="fixture", content={"ok": True})


def selection() -> ProviderSelection:
    return ProviderSelection(
        provider="fixture",
        model="fixture-v1",
        role_models={"technical": "fixture-v1"},
        capabilities=("structured_output",),
    )


def test_registry_rejects_unregistered_provider_and_missing_capability() -> None:
    registry = ProviderRegistry()
    with pytest.raises(LookupError, match="not registered"):
        registry.resolve(selection())

    registry.register(
        "fixture",
        FakeAdapter(
            ProviderCapabilities(
                structured_output=True,
                tool_calling=False,
                parallel_roles=False,
                max_context=4096,
                offline=True,
            )
        ),
    )
    assert registry.resolve(selection()) is not None
    with pytest.raises(ValueError, match="tool_calling"):
        registry.check(selection(), ("tool_calling",))


def test_registry_rejects_unconfigured_model_and_redacts_selection() -> None:
    registry = ProviderRegistry()
    registry.register(
        "fixture",
        FakeAdapter(ProviderCapabilities(True, False, False, 4096, True)),
    )
    with pytest.raises(ValueError, match="model"):
        registry.check(
            ProviderSelection(provider="fixture", model=" "),
            (),
        )

    secret_selection = ProviderSelection(
        provider="fixture",
        model="fixture-v1",
        metadata={"api_key": "secret", "endpoint": "https://example.invalid"},
    )
    redacted = registry.redacted_selection(secret_selection)
    assert "secret" not in str(redacted)
    assert "endpoint" not in str(redacted)

