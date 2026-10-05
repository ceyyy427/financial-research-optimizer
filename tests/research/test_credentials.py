from __future__ import annotations

import json
import pickle
from collections.abc import Iterator, Mapping

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

    with pytest.raises((TypeError, RuntimeError)) as error:
        pickle.dumps(store)
    assert SECRET not in str(error.value)


def test_environment_store_does_not_copy_or_iterate_the_environment() -> None:
    from finahinking.research.credentials import EnvironmentCredentialStore

    class ExplicitEnvironment(Mapping[str, str]):
        def __getitem__(self, key: str) -> str:
            if key == "FINAHINK_USER_API_KEY":
                return SECRET
            raise KeyError(key)

        def __iter__(self) -> Iterator[str]:
            raise AssertionError("the store must not enumerate environment values")

        def __len__(self) -> int:
            return 1

    ref = ProviderCredentialRef("user-compatible", env_var="FINAHINK_USER_API_KEY")
    store = EnvironmentCredentialStore(ExplicitEnvironment())
    assert store.has(ref) is True


def test_capabilities_reject_non_strings_without_stringifying_secrets() -> None:
    from finahinking.research.credentials import (
        EnvironmentCredentialStore,
        build_provider_runtime,
    )

    class SecretCapability:
        def __str__(self) -> str:
            return SECRET

    config = runtime_mapping()
    config["capabilities"] = [SecretCapability()]
    with pytest.raises(TypeError, match="capabilities") as error:
        build_provider_runtime(config, EnvironmentCredentialStore({"FINAHINK_USER_API_KEY": SECRET}))
    assert SECRET not in str(error.value)


def test_credential_store_failures_are_normalized_without_secret_or_path() -> None:
    from finahinking.research.credentials import build_provider_runtime

    class FailingStore:
        def has(self, ref: ProviderCredentialRef) -> bool:
            raise RuntimeError(f"backend failed: {SECRET} /Users/private/provider-key")

        def resolve(self, ref: ProviderCredentialRef) -> str:
            raise AssertionError("resolve must not be called")

    with pytest.raises(ValueError, match="credential|provider") as error:
        build_provider_runtime(runtime_mapping(), FailingStore())
    assert SECRET not in str(error.value)
    assert "/Users/private/provider-key" not in str(error.value)


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (TimeoutError(f"timed out with {SECRET} at /Users/private/provider"), "timeout"),
        (TypeError(f"malformed response contains {SECRET} at /Users/private/provider"), "malformed"),
    ],
)
def test_provider_error_normalization_is_secret_free(failure: BaseException, expected: str) -> None:
    from finahinking.research.credentials import normalize_provider_error

    message = normalize_provider_error(failure)
    assert expected in message
    assert SECRET not in message
    assert "/Users/private/provider" not in message


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
