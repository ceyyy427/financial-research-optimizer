"""Provider-neutral JSON adapters with a secret-free result boundary.

The adapters deliberately know nothing about a vendor SDK.  A caller supplies
an explicit endpoint, bounded transport, and credential reference.  The
endpoint and resolved credential are request-local values and never appear in
the returned :class:`ModelResponse` or normalized failures.
"""

from __future__ import annotations

import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from .credentials import CredentialStore
from .provider_status import ProviderCredentialRef
from .providers import ModelEnvelope, ModelResponse, ProviderCapabilities


class ProviderFailureKind(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    TIMEOUT = "TIMEOUT"
    TRANSPORT = "TRANSPORT"
    HTTP_ERROR = "HTTP_ERROR"
    NON_JSON = "NON_JSON"
    SCHEMA_ERROR = "SCHEMA_ERROR"
    CAPABILITY_REJECTED = "CAPABILITY_REJECTED"


class ProviderAdapterError(RuntimeError):
    """Stable, non-sensitive provider boundary error."""

    def __init__(self, message: str, *, kind: ProviderFailureKind) -> None:
        self.kind = kind
        super().__init__(message)


class ProviderTimeoutError(ProviderAdapterError, TimeoutError):
    def __init__(self) -> None:
        super().__init__("provider timeout", kind=ProviderFailureKind.TIMEOUT)


class ProviderSchemaError(ProviderAdapterError, ValueError):
    def __init__(self, message: str = "provider response schema invalid") -> None:
        super().__init__(message, kind=ProviderFailureKind.SCHEMA_ERROR)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 1
    backoff_seconds: float = 0.0

    def __post_init__(self) -> None:
        if type(self.max_attempts) is not int or self.max_attempts < 1 or self.max_attempts > 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if not isinstance(self.backoff_seconds, (int, float)) or self.backoff_seconds < 0 or self.backoff_seconds > 30:
            raise ValueError("backoff_seconds must be between 0 and 30")


class JsonTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json: object,
        timeout: float,
    ) -> object: ...


def _response_parts(response: object) -> tuple[int, object]:
    """Extract status and JSON body from tiny injected transport responses."""

    if isinstance(response, Mapping):
        status = response.get("status_code", response.get("status", 200))
        try:
            status_code = int(status)
        except (TypeError, ValueError) as exc:
            raise ProviderSchemaError() from exc
        if "json" in response:
            return status_code, response["json"]
        if "body" in response:
            return status_code, response["body"]
        if "text" in response:
            return status_code, response["text"]
        return status_code, response

    status = getattr(response, "status_code", 200)
    try:
        status_code = int(status)
    except (TypeError, ValueError) as exc:
        raise ProviderSchemaError() from exc
    json_method = getattr(response, "json", None)
    if callable(json_method):
        try:
            return status_code, json_method()
        except Exception:  # noqa: BLE001 - normalize parser internals
            raise ProviderAdapterError("provider response is not JSON", kind=ProviderFailureKind.NON_JSON) from None
    body = getattr(response, "body", None)
    if body is not None:
        return status_code, body
    return status_code, response


_CONTENT_KEYS = frozenset({"status", "claims", "evidence_refs", "limitations"})
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "endpoint",
        "file_path",
        "path",
        "password",
        "prompt",
        "raw_provider_response",
        "secret",
        "token",
    }
)
_FORBIDDEN_TEXT = re.compile(
    r"(?:api[-_]?key|authorization|password|secret|token|https?://|/Users/|/private/|prompt)",
    re.IGNORECASE,
)


def _safe_content(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderSchemaError()
    keys = {str(key) for key in value}
    if keys - _CONTENT_KEYS:
        raise ProviderSchemaError()
    result: dict[str, Any] = {}
    for key in _CONTENT_KEYS:
        if key not in value:
            continue
        item = value[key]
        if key == "status":
            if not isinstance(item, str) or not item.strip():
                raise ProviderSchemaError()
            if _FORBIDDEN_TEXT.search(item):
                raise ProviderSchemaError()
            result[key] = item.strip()
        else:
            if not isinstance(item, (list, tuple)) or any(not isinstance(entry, str) for entry in item):
                raise ProviderSchemaError()
            if any(_FORBIDDEN_TEXT.search(entry) for entry in item):
                raise ProviderSchemaError()
            result[key] = list(item)
    return result


class _CompatibleAdapter:
    provider_name = "compatible"

    def __init__(
        self,
        *,
        model: str,
        endpoint: str | None = None,
        transport: JsonTransport | None = None,
        timeout: float = 15.0,
        retry_policy: RetryPolicy | Mapping[str, Any] | None = None,
        credential_ref: ProviderCredentialRef | None = None,
        credential_store: CredentialStore | None = None,
        schema_version: str = "research-model.v1",
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be non-empty")
        if endpoint is not None and (not isinstance(endpoint, str) or not endpoint.strip()):
            raise ValueError("endpoint must be explicit when configured")
        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
            raise ValueError("timeout must be between 0 and 300 seconds")
        if not isinstance(schema_version, str) or not schema_version.strip():
            raise ValueError("schema_version must be non-empty")
        if retry_policy is None:
            policy = RetryPolicy()
        elif isinstance(retry_policy, RetryPolicy):
            policy = retry_policy
        elif isinstance(retry_policy, Mapping):
            policy = RetryPolicy(**dict(retry_policy))
        else:
            raise TypeError("retry_policy must be RetryPolicy or a mapping")
        if credential_ref is not None and not isinstance(credential_ref, ProviderCredentialRef):
            raise TypeError("credential_ref must be a ProviderCredentialRef")
        if credential_ref is not None and credential_store is None:
            raise ValueError("credential store is required for a credential reference")
        if transport is not None and not callable(getattr(transport, "request", None)) and not callable(transport):
            raise TypeError("transport must expose request or be callable")
        self.model = model.strip()
        self.endpoint = endpoint.strip() if endpoint is not None else None
        self.transport = transport
        self.timeout = float(timeout)
        self.retry_policy = policy
        self.credential_ref = credential_ref
        self.credential_store = credential_store
        self.schema_version = schema_version.strip()

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=True,
            tool_calling=False,
            parallel_roles=False,
            max_context=32768,
            offline=self.endpoint is None,
        )

    def invoke(self, envelope: ModelEnvelope) -> ModelResponse:
        if not isinstance(envelope, ModelEnvelope):
            raise TypeError("envelope must be a ModelEnvelope")
        if envelope.tool_names:
            raise ProviderAdapterError("provider capability rejected", kind=ProviderFailureKind.CAPABILITY_REJECTED)
        if self.endpoint is None or self.transport is None:
            raise ProviderAdapterError("provider is not configured", kind=ProviderFailureKind.NOT_CONFIGURED)

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.credential_ref is not None:
            assert self.credential_store is not None
            try:
                credential = self.credential_store.resolve(self.credential_ref)
            except Exception:  # noqa: BLE001 - never expose credential backend details
                raise ProviderAdapterError("credential is not configured", kind=ProviderFailureKind.NOT_CONFIGURED) from None
            if not isinstance(credential, str) or not credential:
                raise ProviderAdapterError("credential is not configured", kind=ProviderFailureKind.NOT_CONFIGURED)
            headers["Authorization"] = f"Bearer {credential}"

        payload = {
            "schema_version": self.schema_version,
            "model": self.model,
            "role": envelope.role,
            "input_digest": envelope.input_digest,
            "context_digest": envelope.context_digest,
            "tool_names": [],
        }
        last_transport: BaseException | None = None
        for attempt in range(self.retry_policy.max_attempts):
            try:
                response = self._request(headers, payload)
                status_code, body = _response_parts(response)
                if status_code < 200 or status_code >= 300:
                    raise ProviderAdapterError("provider returned an error status", kind=ProviderFailureKind.HTTP_ERROR)
                if isinstance(body, (str, bytes, bytearray)):
                    raise ProviderAdapterError("provider response is not JSON", kind=ProviderFailureKind.NON_JSON)
                if not isinstance(body, Mapping):
                    raise ProviderSchemaError()
                if body.get("schema_version") != self.schema_version:
                    raise ProviderSchemaError()
                content = _safe_content(body.get("content"))
                return ModelResponse(provider=self.provider_name, model=self.model, content=content, finish_reason=str(body.get("finish_reason", "stop")))
            except ProviderAdapterError:
                raise
            except TimeoutError:
                last_transport = ProviderTimeoutError()
            except Exception:  # noqa: BLE001 - normalize every transport detail
                last_transport = ProviderAdapterError("provider request failed", kind=ProviderFailureKind.TRANSPORT)
            if attempt + 1 < self.retry_policy.max_attempts and self.retry_policy.backoff_seconds:
                time.sleep(self.retry_policy.backoff_seconds * (attempt + 1))
        if isinstance(last_transport, ProviderTimeoutError):
            raise last_transport
        raise last_transport or ProviderAdapterError("provider request failed", kind=ProviderFailureKind.TRANSPORT)

    def _request(self, headers: Mapping[str, str], payload: Mapping[str, Any]) -> object:
        assert self.transport is not None
        if callable(getattr(self.transport, "request", None)):
            return self.transport.request("POST", self.endpoint, headers=dict(headers), json=dict(payload), timeout=self.timeout)  # type: ignore[union-attr]
        return self.transport("POST", self.endpoint, headers=dict(headers), json=dict(payload), timeout=self.timeout)  # type: ignore[operator]


class OpenAICompatibleAdapter(_CompatibleAdapter):
    provider_name = "openai-compatible"


class DeepSeekCompatibleAdapter(_CompatibleAdapter):
    provider_name = "deepseek-compatible"


__all__ = [
    "DeepSeekCompatibleAdapter",
    "JsonTransport",
    "OpenAICompatibleAdapter",
    "ProviderAdapterError",
    "ProviderFailureKind",
    "ProviderSchemaError",
    "ProviderTimeoutError",
    "RetryPolicy",
]
