"""Provider capability contracts without provider SDKs or secret handling."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .contracts import ProviderSelection, stable_digest, to_jsonable


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    structured_output: bool
    tool_calling: bool
    parallel_roles: bool
    max_context: int
    offline: bool

    def __post_init__(self) -> None:
        if self.max_context <= 0:
            raise ValueError("max_context must be positive")


@dataclass(frozen=True, slots=True)
class ModelEnvelope:
    """A secret-free request envelope.

    The envelope contains digests and allowlisted names, never a raw prompt,
    endpoint, path, credential, or executable instruction.
    """

    request_id: str
    role: str
    input_digest: str
    context_digest: str
    tool_names: tuple[str, ...] = ()
    instructions: str = "Return a structured research observation for review."

    def __post_init__(self) -> None:
        for name, value in (("request_id", self.request_id), ("role", self.role), ("input_digest", self.input_digest), ("context_digest", self.context_digest)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        object.__setattr__(self, "tool_names", tuple(sorted(set(self.tool_names))))
        object.__setattr__(self, "instructions", self.instructions.strip())


@dataclass(frozen=True, slots=True)
class ModelResponse:
    provider: str
    model: str
    content: Mapping[str, Any]
    finish_reason: str = "stop"

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model.strip():
            raise ValueError("provider and model must be non-empty")
        object.__setattr__(self, "content", dict(self.content))


class ProviderAdapter(Protocol):
    def capabilities(self) -> ProviderCapabilities: ...

    def invoke(self, envelope: ModelEnvelope) -> ModelResponse: ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, name: str, adapter: ProviderAdapter) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("provider name must be non-empty")
        if not hasattr(adapter, "capabilities") or not hasattr(adapter, "invoke"):
            raise TypeError("provider adapter must expose capabilities and invoke")
        self._adapters[normalized] = adapter

    def resolve(self, selection: ProviderSelection) -> ProviderAdapter:
        try:
            return self._adapters[selection.provider]
        except KeyError as exc:
            raise LookupError(f"provider {selection.provider!r} is not registered") from exc

    def check(self, selection: ProviderSelection, required_capabilities: tuple[str, ...]) -> ProviderCapabilities:
        if not selection.model.strip():
            raise ValueError("model must be configured")
        adapter = self.resolve(selection)
        capabilities = adapter.capabilities()
        for capability_name in required_capabilities:
            if not hasattr(capabilities, capability_name):
                raise ValueError(f"unknown provider capability: {capability_name}")
            if not getattr(capabilities, capability_name):
                raise ValueError(f"provider lacks capability: {capability_name}")
        return capabilities

    def redacted_selection(self, selection: ProviderSelection) -> dict[str, Any]:
        return to_jsonable(selection.redacted())


def envelope_digest(envelope: ModelEnvelope) -> str:
    return stable_digest(envelope)
