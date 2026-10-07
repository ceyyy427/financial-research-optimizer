"""Secret-free provider readiness contracts.

Provider credentials belong to the user's environment or keychain. This
module reports whether a reference is configured, never the referenced value.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_KEYCHAIN_LABEL = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SECRET_LIKE_LABEL = re.compile(r"(?:api[-_]?key|secret|token|password|credential)", re.IGNORECASE)
_SAFE_CAPABILITY = re.compile(r"^[a-z][a-z0-9_:-]{0,63}$")


@dataclass(frozen=True, slots=True)
class ProviderCredentialRef:
    """A pointer to a credential, not a credential itself."""

    provider: str
    env_var: str | None = None
    keychain_label: str | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must be non-empty")
        if self.env_var is None and self.keychain_label is None:
            raise ValueError("credential reference requires environment or keychain reference")
        if self.env_var is not None and not _ENV_NAME.fullmatch(self.env_var):
            raise ValueError("credential environment variable name is invalid")
        if self.keychain_label is not None and (
            not _KEYCHAIN_LABEL.fullmatch(self.keychain_label)
            or _SECRET_LIKE_LABEL.search(self.keychain_label) is not None
        ):
            raise ValueError("credential keychain label is invalid")

    @classmethod
    def from_mapping(cls, provider: str, value: Mapping[str, Any]) -> ProviderCredentialRef:
        if not isinstance(value, Mapping):
            raise TypeError("credential_ref must be a mapping")
        if set(value) - {"env_var", "keychain_label"}:
            raise ValueError("credential reference contains unsupported or secret fields")
        return cls(
            provider=provider,
            env_var=str(value["env_var"]) if value.get("env_var") is not None else None,
            keychain_label=(
                str(value["keychain_label"])
                if value.get("keychain_label") is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, str]:
        result: dict[str, str] = {}
        if self.env_var is not None:
            result["env_var"] = self.env_var
        if self.keychain_label is not None:
            result["keychain_label"] = self.keychain_label
        return result


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    provider: str
    model: str
    enabled: bool
    configured: bool
    offline: bool
    capabilities: tuple[str, ...] = ()
    credential_ref: ProviderCredentialRef | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "provider": self.provider,
            "model": self.model,
            "enabled": self.enabled,
            "configured": self.configured,
            "offline": self.offline,
            "capabilities": list(self.capabilities),
            "reason": self.reason,
        }
        if self.credential_ref is not None:
            result["credential_ref"] = self.credential_ref.to_dict()
        return result


def _safe_capabilities(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        raise TypeError("provider capabilities must be a sequence of strings")
    try:
        values = tuple(value)
    except TypeError as exc:
        raise TypeError("provider capabilities must be a sequence of strings") from exc
    if any(type(item) is not str for item in values):
        raise TypeError("provider capabilities must contain only strings")
    normalized = tuple(item.strip() for item in values)
    if any(not item or not _SAFE_CAPABILITY.fullmatch(item) or _SECRET_LIKE_LABEL.search(item) for item in normalized):
        raise ValueError("provider capabilities contain an unsafe name")
    if len(set(normalized)) != len(normalized):
        raise ValueError("provider capabilities must not contain duplicates")
    return tuple(sorted(normalized))


def provider_status_payload(
    config: Mapping[str, Any], environment: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return UI-safe provider readiness without copying secret values."""

    if not isinstance(config, Mapping) or not isinstance(config.get("defaults"), Mapping):
        raise TypeError("provider config requires a defaults mapping")
    providers = config.get("providers")
    if not isinstance(providers, list):
        raise TypeError("provider config requires a providers list")
    defaults = config["defaults"]
    default_provider = str(defaults.get("provider", "offline"))
    default_model = str(defaults.get("model", "fixture-v1"))
    role_models = {
        str(key): str(value)
        for key, value in dict(defaults.get("role_models", {})).items()
    }
    env = environment or {}
    statuses: list[ProviderStatus] = []
    for item in providers:
        if not isinstance(item, Mapping) or not str(item.get("name", "")).strip():
            raise ValueError("each provider requires a name")
        name = str(item["name"]).strip()
        model = str(item.get("model", default_model)).strip()
        if not model:
            raise ValueError("provider model must be non-empty")
        credential_ref = None
        if item.get("credential_ref") is not None:
            credential_ref = ProviderCredentialRef.from_mapping(name, item["credential_ref"])
        offline = bool(item.get("offline", False))
        enabled = bool(item.get("enabled", True))
        if offline:
            configured = True
            reason = "offline fixture"
        elif credential_ref is None:
            configured = False
            reason = "credential reference is not configured"
        elif credential_ref.env_var is not None and str(env.get(credential_ref.env_var, "")):
            configured = True
            reason = "configured"
        elif credential_ref.keychain_label is not None:
            configured = False
            reason = "keychain credential must be configured"
        else:
            configured = False
            reason = "credential is not configured"
        capabilities = _safe_capabilities(item.get("capabilities", ()))
        statuses.append(
            ProviderStatus(
                provider=name,
                model=model,
                enabled=enabled,
                configured=configured,
                offline=offline,
                capabilities=capabilities,
                credential_ref=credential_ref,
                reason=reason,
            )
        )
    statuses.sort(key=lambda status: status.provider)
    return {
        "defaults": {"provider": default_provider, "model": default_model},
        "role_models": role_models,
        "providers": [status.to_dict() for status in statuses],
        "secret_policy": "Only credential references are returned; secret values stay in the user environment or keychain.",
    }
