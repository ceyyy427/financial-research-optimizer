from __future__ import annotations

import pytest

from finahinking.research.provider_adapters import (
    DeepSeekCompatibleAdapter,
    OpenAICompatibleAdapter,
    ProviderContractResult,
    ProviderFailureKind,
    RetryPolicy,
)
from finahinking.research.providers import ModelEnvelope


class SequenceTransport:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, *, headers: dict[str, str], json: object, timeout: float) -> object:
        self.calls.append({"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout})
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def env() -> ModelEnvelope:
    return ModelEnvelope("run", "research", "input", "context")


def adapter(transport: SequenceTransport, *, provider: str = "openai"):
    cls = DeepSeekCompatibleAdapter if provider == "deepseek" else OpenAICompatibleAdapter
    return cls(model="test-model", endpoint="https://provider.invalid/v1/chat/completions", transport=transport,
               retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0))


def test_contract_success_is_structured_and_payload_is_compatible() -> None:
    transport = SequenceTransport({"status_code": 200, "json": {"schema_version": "research-model.v1", "content": {"status": "READY", "evidence_refs": ["artifact:one"]}}})
    result = adapter(transport).invoke_contract(env())
    assert isinstance(result, ProviderContractResult)
    assert result.status == "READY"
    assert result.provider == "openai-compatible"
    assert result.model == "test-model"
    assert "artifact:one" in result.evidence_refs
    payload = transport.calls[0]["json"]
    assert isinstance(payload, dict)
    assert payload["model"] == "test-model"
    assert payload["messages"]


@pytest.mark.parametrize(
    ("status", "expected"),
    [(401, "UNAUTHORIZED"), (403, "FORBIDDEN"), (429, "RATE_LIMITED"), (503, "RETRY_EXHAUSTED")],
)
def test_http_failures_are_normalized_without_raw_response(status: int, expected: str) -> None:
    response = {"status_code": status, "json": {"error": "secret"}}
    result = adapter(SequenceTransport(response, response, response)).invoke_contract(env())
    assert result.status == expected
    assert result.provider == "openai-compatible"
    assert all("secret" not in value for value in result.limitations)


def test_retryable_5xx_and_timeout_retry_then_succeed() -> None:
    response = {"status_code": 200, "json": {"schema_version": "research-model.v1", "content": {"status": "READY"}}}
    transport = SequenceTransport({"status_code": 503, "json": {}}, TimeoutError("private"), response)
    result = adapter(transport).invoke_contract(env())
    assert result.status == "READY"
    assert len(transport.calls) == 3


@pytest.mark.parametrize(
    "response",
    [{"status_code": 200, "text": "not-json"}, {"status_code": 200, "json": {"schema_version": "wrong", "content": {}}}],
)
def test_non_json_and_schema_mismatch_are_normalized(response: object) -> None:
    result = adapter(SequenceTransport(response)).invoke_contract(env())
    assert result.status in {"NON_JSON", "SCHEMA_ERROR"}


def test_retry_exhaustion_is_explicit() -> None:
    transport = SequenceTransport({"status_code": 503, "json": {}}, {"status_code": 503, "json": {}}, {"status_code": 503, "json": {}})
    result = adapter(transport).invoke_contract(env())
    assert result.status == "RETRY_EXHAUSTED"
    assert len(transport.calls) == 3
