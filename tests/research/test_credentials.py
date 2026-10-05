from __future__ import annotations

import json

import pytest

from finahinking.research.contracts import ProviderSelection, to_jsonable
from finahinking.research.provider_status import ProviderCredentialRef

SECRET = "user-api-key-do-not-render"


def runtime_mapping() -> dict[str, object]:
    return {
        "provider": "user-compatible",
        "model": "user-model",
        "credential_ref": {"env_var": "FINAHINK_USER_API_KEY"},
        "capabilities": ["structured_output"],
    }


def test_environment_credential_is_only_reported_as_configured() -> None:
    from finahinking.research.credentials import (
        EnvironmentCredentialStore,
        build_provider_runtime,
    )

    ref = ProviderCredentialRef("user-compatible", env_var="FINAHINK_USER_API_KEY")
    store = EnvironmentCredentialStore({"FINAHINK_USER_API_KEY": SECRET})

    assert store.has(ref) is True
    runtime = build_provider_runtime(runtime_mapping(), store)
    encoded = json.dumps(to_jsonable(runtime), ensure_ascii=False, sort_keys=True)

    assert runtime.redacted() == {
        "provider": "user-compatible",
        "model": "user-model",
        "credential_ref": {"env_var": "FINAHINK_USER_API_KEY"},
        "capabilities": ["structured_output"],
        "configured": True,
    }
    assert SECRET not in str(runtime)
    assert SECRET not in repr(runtime)
    assert SECRET not in encoded
    assert not hasattr(runtime, "resolve")


def test_provider_selection_remains_secret_free_and_does_not_resolve_credentials() -> None:
    from finahinking.research.credentials import EnvironmentCredentialStore

    selection = ProviderSelection(
        provider="user-compatible",
        model="user-model",
    )
    store = EnvironmentCredentialStore({"FINAHINK_USER_API_KEY": SECRET})

    assert "credential_ref" not in selection.redacted()
    assert SECRET not in json.dumps(to_jsonable(selection), ensure_ascii=False)
    assert store.has(ProviderCredentialRef("user-compatible", env_var="FINAHINK_USER_API_KEY"))


def test_runtime_requires_a_credential_reference() -> None:
    from finahinking.research.credentials import (
        EnvironmentCredentialStore,
        build_provider_runtime,
    )

    config = runtime_mapping()
    config.pop("credential_ref")
    with pytest.raises(ValueError, match="credential reference"):
        build_provider_runtime(config, EnvironmentCredentialStore({}))


@pytest.mark.parametrize("env_var", ["not-safe", "$(print SECRET)", "/tmp/key", "A.B"])
def test_runtime_rejects_non_explicit_environment_names(env_var: str) -> None:
    from finahinking.research.credentials import (
        EnvironmentCredentialStore,
        build_provider_runtime,
    )

    config = runtime_mapping()
    config["credential_ref"] = {"env_var": env_var}
    with pytest.raises(ValueError, match="environment"):
        build_provider_runtime(config, EnvironmentCredentialStore({env_var: SECRET}))


@pytest.mark.parametrize("field", ["api_key", "secret", "token", "endpoint", "path"])
def test_runtime_rejects_secret_like_configuration_fields(field: str) -> None:
    from finahinking.research.credentials import (
        EnvironmentCredentialStore,
        build_provider_runtime,
    )

    config = runtime_mapping()
    config[field] = SECRET
    with pytest.raises(ValueError, match="unsupported|secret"):
        build_provider_runtime(config, EnvironmentCredentialStore({}))


def test_runtime_rejects_missing_secret_without_resolving_or_echoing_it() -> None:
    from finahinking.research.credentials import (
        EnvironmentCredentialStore,
        build_provider_runtime,
    )

    store = EnvironmentCredentialStore({})
    with pytest.raises(ValueError, match="configured") as error:
        build_provider_runtime(runtime_mapping(), store)
    assert SECRET not in str(error.value)


def test_in_memory_store_is_test_only_and_never_serializable() -> None:
    from finahinking.research.credentials import InMemoryCredentialStore

    ref = ProviderCredentialRef("user-compatible", env_var="FINAHINK_USER_API_KEY")
    store = InMemoryCredentialStore({ref: SECRET})

    assert store.has(ref)
    assert store.resolve(ref) == SECRET
    assert SECRET not in repr(store)
    with pytest.raises(TypeError, match="unsupported|serializ"):
        to_jsonable(store)


def test_runtime_configuration_does_not_call_network_or_normalize_provider_payloads() -> None:
    from finahinking.research.credentials import (
        EnvironmentCredentialStore,
        build_provider_runtime,
    )

    class Store(EnvironmentCredentialStore):
        def resolve(self, ref: ProviderCredentialRef) -> str:
            raise AssertionError("runtime construction must not resolve or call a provider")

    runtime = build_provider_runtime(runtime_mapping(), Store({"FINAHINK_USER_API_KEY": SECRET}))
    assert runtime.provider == "user-compatible"
    assert runtime.capabilities == ("structured_output",)
