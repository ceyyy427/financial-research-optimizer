"""Local-only data connection settings and credential boundaries."""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from typing import Protocol

from .user_api_contracts import DataConnectionConfig, DataSourceCredentialRef


class DataCredentialStore(Protocol):
    def has(self, ref: DataSourceCredentialRef) -> bool: ...
    def resolve(self, ref: DataSourceCredentialRef) -> str: ...


class InMemoryDataCredentialStore:
    """Process-local test/UI store; values cannot be serialized by design."""

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[object, str] | None = None) -> None:
        self._values: dict[object, str] = {}
        for key, value in (values or {}).items():
            if not isinstance(value, str) or not value:
                raise ValueError("data credential values must be non-empty strings")
            self._values[key] = value

    def __repr__(self) -> str:
        return "InMemoryDataCredentialStore(<values redacted>)"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("data credentials cannot be serialized")

    def put(self, ref: DataSourceCredentialRef, value: str) -> None:
        if not isinstance(ref, DataSourceCredentialRef) or not isinstance(value, str) or not value:
            raise ValueError("invalid data credential")
        self._values[ref] = value

    def has(self, ref: DataSourceCredentialRef) -> bool:
        return isinstance(ref, DataSourceCredentialRef) and ref in self._values

    def resolve(self, ref: DataSourceCredentialRef) -> str:
        if not self.has(ref):
            raise ValueError("data credential is not configured")
        return self._values[ref]


class EnvironmentDataCredentialStore:
    """Read only the explicit data environment variable named by a reference."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = os.environ if environment is None else environment

    def has(self, ref: DataSourceCredentialRef) -> bool:
        if ref.env_var is None:
            return False
        return bool(self._environment.get(ref.env_var, ""))

    def resolve(self, ref: DataSourceCredentialRef) -> str:
        if not self.has(ref):
            raise ValueError("data credential is not configured")
        assert ref.env_var is not None
        return str(self._environment[ref.env_var])


class DataConnectionSettingsStore:
    """Keep redacted connection config in process memory; secrets stay separate."""

    def __init__(self, credential_store: InMemoryDataCredentialStore | None = None) -> None:
        self.credentials = credential_store or InMemoryDataCredentialStore()
        self._configs: dict[str, DataConnectionConfig] = {}

    def save(self, config: DataConnectionConfig, *, credential_value: str | None = None) -> None:
        if credential_value is not None:
            if config.credential_ref is None:
                raise ValueError("credential value supplied for an unauthenticated connection")
            self.credentials.put(config.credential_ref, credential_value)
        self._configs[config.connection_id] = config

    def get(self, connection_id: str) -> DataConnectionConfig:
        try:
            return self._configs[connection_id]
        except KeyError as exc:
            raise KeyError("data connection not found") from exc

    def list(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {**config.redacted(), "credential_configured": bool(config.credential_ref and self.credentials.has(config.credential_ref))}
            for config in sorted(self._configs.values(), key=lambda item: item.connection_id)
        )

    def remove(self, connection_id: str) -> None:
        self._configs.pop(connection_id, None)


def new_local_credential_ref(connection_id: str) -> DataSourceCredentialRef:
    """Create an opaque process-local key reference without storing its value."""

    safe = "".join(char if char.isalnum() else "-" for char in connection_id).strip("-")[:48] or "connection"
    return DataSourceCredentialRef(keychain_label=f"finathink-data-{safe}-{secrets.token_hex(8)}")


__all__ = [
    "DataConnectionSettingsStore", "DataCredentialStore", "EnvironmentDataCredentialStore",
    "InMemoryDataCredentialStore", "new_local_credential_ref",
]
