from __future__ import annotations

import json

import pytest

from finahinking.research.credentials import InMemoryCredentialStore
from finahinking.research.provider_adapters import (
    OpenAICompatibleAdapter,
    ProviderAdapterError,
    ProviderFailureKind,
)
from finahinking.research.provider_status import ProviderCredentialRef
from finahinking.research.providers import ModelEnvelope

SECRET = "provider-secret-value"
ENDPOINT = "https://model.example.test/v1/chat"


class Transport:
    def __init__(self, response: object | None = None, *, error: BaseException | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, *, headers: dict[str, str], json: object, timeout: float) -> object:
        self.calls.append({"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout})
        if self.error is not None:
            raise self.error
        return self.response


def envelope(*, tools: tuple[str, ...] = ()) -> ModelEnvelope:
    return ModelEnvelope(
        request_id="run-1",
        role="technical",
        input_digest="input-digest",
        context_digest="context-digest",
        tool_names=tools,
    )


def adapter(transport: Transport, *, endpoint: str | None = ENDPOINT) -> OpenAICompatibleAdapter:
    ref = ProviderCredentialRef("openai-compatible", env_var="FINAHINK_TEST_KEY")
    return OpenAICompatibleAdapter(
        model="model-v1",
        endpoint=endpoint,
        transport=transport,
        credential_ref=ref,
        credential_store=InMemoryCredentialStore({ref: SECRET}),
        schema_version="research-model.v1",
    )


def test_adapter_sends_bounded_json_contract_and_returns_typed_response() -> None:
    transport = Transport(
        {"status_code": 200, "json": {"schema_version": "research-model.v1", "content": {"status": "READY", "claims": ["observation"]}}}
    )
    response = adapter(transport).invoke(envelope())

    assert response.provider == "openai-compatible"
    assert response.model == "model-v1"
    assert response.content == {"status": "READY", "claims": ["observation"]}
    call = transport.calls[0]
    assert call["url"] == ENDPOINT
    assert call["headers"] == {"Authorization": f"Bearer {SECRET}", "Content-Type": "application/json", "Accept": "application/json"}
    assert call["json"] == {
        "schema_version": "research-model.v1",
        "model": "model-v1",
        "role": "technical",
        "input_digest": "input-digest",
        "context_digest": "context-digest",
        "tool_names": [],
    }


def test_adapter_rejects_model_requested_tools_without_transport_call() -> None:
    transport = Transport()
    with pytest.raises(ProviderAdapterError, match="capability") as error:
        adapter(transport).invoke(envelope(tools=("filesystem",)))
    assert error.value.kind is ProviderFailureKind.CAPABILITY_REJECTED
    assert transport.calls == []


def test_adapter_requires_explicit_endpoint_and_never_fakes_offline_success() -> None:
    transport = Transport()
    with pytest.raises(ProviderAdapterError, match="configured") as error:
        adapter(transport, endpoint=None).invoke(envelope())
    assert error.value.kind is ProviderFailureKind.NOT_CONFIGURED
    assert transport.calls == []


@pytest.mark.parametrize(
    ("response", "kind"),
    [
        ({"status_code": 200, "text": "not-json"}, ProviderFailureKind.NON_JSON),
        ({"status_code": 502, "json": {"error": SECRET}}, ProviderFailureKind.HTTP_ERROR),
        ({"status_code": 200, "json": {"schema_version": "wrong", "content": {}}}, ProviderFailureKind.SCHEMA_ERROR),
    ],
)
def test_adapter_normalizes_non_json_http_and_schema_failures_without_secrets(response: object, kind: ProviderFailureKind) -> None:
    transport = Transport(response)
    with pytest.raises(ProviderAdapterError) as error:
        adapter(transport).invoke(envelope())
    assert error.value.kind is kind
    message = str(error.value)
    assert SECRET not in message
    assert ENDPOINT not in message
    assert "prompt" not in message.casefold()


def test_adapter_normalizes_timeout_without_secret_or_endpoint() -> None:
    transport = Transport(error=TimeoutError(f"timed out {SECRET} {ENDPOINT}"))
    with pytest.raises(ProviderAdapterError) as error:
        adapter(transport).invoke(envelope())
    assert error.value.kind is ProviderFailureKind.TIMEOUT
    assert SECRET not in str(error.value)
    assert ENDPOINT not in str(error.value)


def test_adapter_retries_bounded_transport_failure() -> None:
    class EventuallyReady(Transport):
        def __init__(self) -> None:
            super().__init__()
            self.remaining = 1

        def request(self, *args: object, **kwargs: object) -> object:
            self.calls.append({"args": args, "kwargs": kwargs})
            if self.remaining:
                self.remaining -= 1
                raise ConnectionError(f"failed {SECRET}")
            return {"status_code": 200, "json": {"schema_version": "research-model.v1", "content": {"status": "READY"}}}

    transport = EventuallyReady()
    result = OpenAICompatibleAdapter(
        model="model-v1",
        endpoint=ENDPOINT,
        transport=transport,
        retry_policy={"max_attempts": 2, "backoff_seconds": 0},
        schema_version="research-model.v1",
    ).invoke(envelope())
    assert result.content == {"status": "READY"}
    assert len(transport.calls) == 2


def test_adapter_result_does_not_include_secret_endpoint_prompt_or_raw_response() -> None:
    transport = Transport(
        {"status_code": 200, "json": {"schema_version": "research-model.v1", "content": {"status": "READY", "claims": ["safe"]}, "raw_provider_response": SECRET}}
    )
    result = adapter(transport).invoke(envelope())
    encoded = json.dumps(result.content)
    assert SECRET not in encoded
    assert ENDPOINT not in encoded
    assert "raw_provider_response" not in encoded


def test_adapter_rejects_sensitive_text_inside_model_content() -> None:
    transport = Transport(
        {"status_code": 200, "json": {"schema_version": "research-model.v1", "content": {"claims": [f"secret={SECRET}"]}}}
    )
    with pytest.raises(ProviderAdapterError) as error:
        adapter(transport).invoke(envelope())
    assert error.value.kind is ProviderFailureKind.SCHEMA_ERROR
    assert SECRET not in str(error.value)
