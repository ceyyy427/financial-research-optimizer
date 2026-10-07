"""Local-only data connection settings and credential boundaries."""

from __future__ import annotations

import os
import secrets
import subprocess
from collections.abc import Mapping
from typing import Protocol

from .user_api_contracts import DataConnectionConfig, DataSourceCredentialRef


class DataCredentialStore(Protocol):
    def has(self, ref: DataSourceCredentialRef) -> bool: ...
    def resolve(self, ref: DataSourceCredentialRef) -> str: ...
    def put(self, ref: DataSourceCredentialRef, value: str) -> None: ...


class KeychainBackend(Protocol):
    """Minimal backend used by the credential store and its tests."""

    def get(self, label: str) -> str | None: ...
    def put(self, label: str, value: str) -> None: ...


class KeychainError(RuntimeError):
    """A generic, secret-free keychain operation failure."""


class MacOSKeychainBackend:
    """Use the macOS keychain through the argument-array ``security`` CLI.

    The command never uses a shell and command output is intentionally not
    included in exceptions.  Tests inject a ``KeychainBackend`` instead of
    touching a user's keychain.
    """

    __slots__ = ("_account", "_executable", "_timeout")

    def __init__(self, *, executable: str = "/usr/bin/security", account: str = "finathink-data", timeout: float = 5.0) -> None:
        self._executable = executable
        self._account = account
        self._timeout = timeout

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [self._executable, *args],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
                timeout=self._timeout,
            )
        except (OSError, subprocess.SubprocessError):
            raise KeychainError("system credential storage is unavailable") from None

    def get(self, label: str) -> str | None:
        result = self._run(["find-generic-password", "-a", self._account, "-s", label, "-w"])
        if result.returncode != 0:
            return None
        value = result.stdout.strip()
        return value or None

    def put(self, label: str, value: str) -> None:
        result = self._run([
            "add-generic-password",
            "-a",
            self._account,
            "-s",
            label,
            "-w",
            value,
            "-U",
        ])
        if result.returncode != 0:
            raise KeychainError("system credential storage rejected the value")


class KeychainDataCredentialStore:
    """Data credential store backed by the OS keychain.

    Only credential references cross the settings boundary.  ``backend`` is
    injectable so tests can prove the boundary without writing a real key.
    """

    __slots__ = ("_backend",)

    def __init__(self, backend: KeychainBackend | None = None) -> None:
        self._backend = backend or MacOSKeychainBackend()

    def has(self, ref: DataSourceCredentialRef) -> bool:
        if not isinstance(ref, DataSourceCredentialRef) or ref.keychain_label is None:
            return False
        try:
            return self._backend.get(ref.keychain_label) is not None
        except KeychainError:
            return False

    def resolve(self, ref: DataSourceCredentialRef) -> str:
        if not isinstance(ref, DataSourceCredentialRef) or ref.keychain_label is None:
            raise ValueError("data credential is not configured")
        try:
            value = self._backend.get(ref.keychain_label)
        except KeychainError:
            raise ValueError("data credential is not configured") from None
        if not value:
            raise ValueError("data credential is not configured")
        return value

    def put(self, ref: DataSourceCredentialRef, value: str) -> None:
        if not isinstance(ref, DataSourceCredentialRef) or ref.keychain_label is None:
            raise ValueError("keychain credential reference is required")
        if not isinstance(value, str) or not value:
            raise ValueError("data credential must be non-empty")
        try:
            self._backend.put(ref.keychain_label, value)
        except KeychainError:
            raise ValueError("system credential storage is unavailable") from None


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
        if not isinstance(ref, DataSourceCredentialRef):
            return False
        aliases = [ref]
        if ref.env_var is not None:
            aliases.append(ref.env_var)
        if ref.keychain_label is not None:
            aliases.append(ref.keychain_label)
        return any(alias in self._values for alias in aliases)

    def resolve(self, ref: DataSourceCredentialRef) -> str:
        if not self.has(ref):
            raise ValueError("data credential is not configured")
        if ref in self._values:
            return self._values[ref]
        alias = ref.env_var or ref.keychain_label
        if alias is not None and alias in self._values:
            return self._values[alias]
        raise ValueError("data credential is not configured")


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

    def put(self, ref: DataSourceCredentialRef, value: str) -> None:
        del ref, value
        raise ValueError("environment credentials are read-only")


class DataConnectionSettingsStore:
    """Keep redacted connection config in process memory; secrets use keychain."""

    def __init__(self, credential_store: DataCredentialStore | None = None) -> None:
        self.credentials = credential_store or KeychainDataCredentialStore()
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
    "InMemoryDataCredentialStore", "KeychainBackend", "KeychainDataCredentialStore",
    "KeychainError", "MacOSKeychainBackend", "new_local_credential_ref",
]
