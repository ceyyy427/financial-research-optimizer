"""Local-only data connection settings and credential boundaries."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
from collections.abc import Mapping
from pathlib import Path
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

    def _run(self, args: list[str], *, input_data: str | None = None) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [self._executable, *args],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
                timeout=self._timeout,
                input=input_data,
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
            "-U",
            "-w",
        ], input_data=value)
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


class PersistentDataConnectionStore(DataConnectionSettingsStore):
    """A local connection registry that persists only non-secret settings.

    The JSON file contains the connection contract and an opaque credential
    reference. Credential values are always delegated to ``credential_store``
    and never enter the file, repr, logs, or serialized status payloads.
    Loading this store is side-effect free: it does not resolve credentials or
    contact a remote endpoint.
    """

    def __init__(self, path: str | os.PathLike[str], *, credential_store: DataCredentialStore | None = None) -> None:
        super().__init__(credential_store=credential_store)
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    @staticmethod
    def _serialize(config: DataConnectionConfig) -> dict[str, object]:
        ref = config.credential_ref.to_dict() if config.credential_ref is not None else None
        # The endpoint is part of the user-owned connection contract, but the
        # redacted view used by reports/UI intentionally omits it.
        return {
            "connection_id": config.connection_id,
            "display_name": config.display_name,
            "base_url": config.base_url,
            "credential_ref": ref,
            "auth_mode": config.auth_mode,
            "field_mapping": dict(config.field_mapping),
            "records_path": config.records_path,
            "auth_header": config.auth_header,
            "source_declaration": config.source_declaration,
            "allow_local": config.allow_local,
        }

    @staticmethod
    def _deserialize(payload: Mapping[str, object]) -> DataConnectionConfig:
        raw_ref = payload.get("credential_ref")
        ref: DataSourceCredentialRef | None = None
        if raw_ref is not None:
            if not isinstance(raw_ref, Mapping):
                raise ValueError("persisted credential reference is invalid")
            ref = DataSourceCredentialRef(
                env_var=raw_ref.get("env_var") if isinstance(raw_ref.get("env_var"), str) else None,
                keychain_label=raw_ref.get("keychain_label") if isinstance(raw_ref.get("keychain_label"), str) else None,
            )
        mapping = payload.get("field_mapping", {})
        if not isinstance(mapping, Mapping):
            raise TypeError("persisted field mapping is invalid")
        return DataConnectionConfig(
            connection_id=str(payload.get("connection_id", "")),
            display_name=str(payload.get("display_name", "")),
            base_url=str(payload.get("base_url", "")),
            credential_ref=ref,
            auth_mode=str(payload.get("auth_mode", "no_auth")),
            field_mapping={str(key): str(value) for key, value in mapping.items()},
            records_path=payload.get("records_path") if isinstance(payload.get("records_path"), str) else None,
            auth_header=payload.get("auth_header") if isinstance(payload.get("auth_header"), str) else None,
            source_declaration=str(payload.get("source_declaration", "User-declared data source; Finathink has not independently verified it.")),
            allow_local=bool(payload.get("allow_local", False)),
        )

    def _load(self) -> None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return
        if not raw.strip():
            return
        try:
            payload = json.loads(raw)
            rows = payload.get("connections", []) if isinstance(payload, Mapping) else []
            if not isinstance(rows, list):
                raise TypeError("persisted connections are invalid")
            for row in rows:
                if isinstance(row, Mapping):
                    config = self._deserialize(row)
                    self._configs[config.connection_id] = config
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("persisted data connections are invalid") from exc

    def _flush(self) -> None:
        payload = {
            "schema_version": 1,
            "connections": [self._serialize(config) for config in sorted(self._configs.values(), key=lambda item: item.connection_id)],
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        temporary = self.path.with_name(f".{self.path.name}.{secrets.token_hex(8)}.tmp")
        try:
            temporary.write_text(encoded, encoding="utf-8")
            os.replace(temporary, self.path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def save(self, config: DataConnectionConfig, *, credential_value: str | None = None) -> None:
        super().save(config, credential_value=credential_value)
        self._flush()

    def remove(self, connection_id: str) -> None:
        super().remove(connection_id)
        self._flush()


def new_local_credential_ref(connection_id: str) -> DataSourceCredentialRef:
    """Create an opaque keychain reference without embedding user identifiers."""

    del connection_id
    return DataSourceCredentialRef(keychain_label=f"finathink-data-{secrets.token_hex(24)}")


__all__ = [
    "DataConnectionSettingsStore",
    "DataCredentialStore",
    "EnvironmentDataCredentialStore",
    "InMemoryDataCredentialStore",
    "KeychainBackend",
    "KeychainDataCredentialStore",
    "KeychainError",
    "MacOSKeychainBackend",
    "PersistentDataConnectionStore",
    "new_local_credential_ref",
]
