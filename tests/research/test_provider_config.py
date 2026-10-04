from __future__ import annotations

import json

import pytest

from finahinking.research.providers import (
    ProviderCapabilities,
    ProviderRegistry,
    load_provider_config,
    load_provider_config_from_mapping,
    resolve_provider_selection,
)


def test_provider_precedence_and_secret_reference_redaction() -> None:
    selection = resolve_provider_selection(
        defaults={"provider": "offline", "model": "fixture", "role_models": {"technical": "fixture"}},
        local_config={"provider": "local", "model": "local-v1"},
        environment={"FINAHINKING_PROVIDER": "env", "FINAHINKING_MODEL": "env-v1", "FINAHINKING_API_KEY_REF": "keychain://finathink"},
        cli_ui={"model": "cli-v1"},
        run_override={"role_models": {"technical": "run-v1"}},
    )
    assert selection.provider == "env"
    assert selection.model == "cli-v1"
    assert selection.role_models["technical"] == "run-v1"
    assert "keychain://finathink" not in json.dumps(selection.redacted())


def test_example_provider_config_is_local_and_schema_checked() -> None:
    payload = load_provider_config("docs/research-providers.example.json")
    assert payload["defaults"]["provider"] == "offline"
    assert all("api_key" not in json.dumps(item) for item in payload["providers"])
    with pytest.raises((TypeError, ValueError), match="providers"):
        load_provider_config_from_mapping({"defaults": {}})


def test_provider_registry_does_not_autofallback_after_capability_error() -> None:
    registry = ProviderRegistry()
    registry.register("offline", type("Adapter", (), {"capabilities": lambda self: ProviderCapabilities(True, False, False, 100, True), "invoke": lambda self, envelope: None})())
    selection = resolve_provider_selection(defaults={"provider": "offline", "model": "fixture"})
    with pytest.raises(ValueError, match="tool_calling"):
        registry.check(selection, ("tool_calling",))
