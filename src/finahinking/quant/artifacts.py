"""Data-only, content-addressed P5 artifacts and QuantRun records."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from finahinking.experiments.models import canonical_json

from .interfaces import _digest, validate_identifier

_MAX_ARTIFACT_BYTES = 1_000_000
_FORBIDDEN_KEYS = {
    "__class__",
    "__code__",
    "__globals__",
    "__import__",
    "callable",
    "eval",
    "exec",
    "module",
    "pickle",
    "source_code",
}


def _reject_executable_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("artifact payload keys must be strings")
            if key.casefold() in _FORBIDDEN_KEYS:
                raise ValueError("artifact payload contains executable key")
            _reject_executable_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_executable_keys(item)
    elif callable(value):
        raise TypeError("artifact payload contains executable value")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("artifact payload contains non-finite value")
    elif hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
        try:
            scalar = value.item()
        except (AttributeError, TypeError, ValueError) as exc:
            raise TypeError("artifact payload contains unsupported value") from exc
        if scalar is not value:
            _reject_executable_keys(scalar)
        else:
            raise TypeError("artifact payload contains unsupported value")
    elif value is not None and not isinstance(value, (str, int, bool, datetime)):
        raise TypeError("artifact payload contains unsupported value")


def _validated_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    _reject_executable_keys(value)
    try:
        encoded = canonical_json(value).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON serializable") from exc
    if len(encoded) > _MAX_ARTIFACT_BYTES:
        raise ValueError(f"{label} exceeds size limit")
    normalized = json.loads(encoded)
    if not isinstance(normalized, dict):
        raise TypeError(f"{label} must be a mapping")
    return normalized


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    artifact_type: str
    schema_version: int
    _payload: dict[str, Any]
    created_at: str

    @property
    def payload(self) -> dict[str, Any]:
        """Return a defensive copy so records remain content-addressed."""

        return copy.deepcopy(self._payload)

    @classmethod
    def create(
        cls,
        artifact_id: str,
        artifact_type: str,
        payload: dict[str, Any],
        created_at: datetime | str | None = None,
    ) -> Artifact:
        validate_identifier(artifact_id, "artifact identifier")
        validate_identifier(artifact_type, "artifact type")
        stored_payload = _validated_mapping(payload, "artifact payload")
        if created_at is None:
            timestamp = datetime.now(UTC).isoformat()
        elif isinstance(created_at, datetime):
            timestamp = created_at.isoformat()
        elif isinstance(created_at, str) and created_at.strip():
            timestamp = created_at
        else:
            raise ValueError("created timestamp is invalid")
        return cls(artifact_id, artifact_type, 1, stored_payload, timestamp)

    @property
    def fingerprint(self) -> str:
        return _digest(
            {
                "artifact_id": self.artifact_id,
                "artifact_type": self.artifact_type,
                "schema_version": self.schema_version,
                "payload": self._payload,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "payload": copy.deepcopy(self._payload),
            "created_at": self.created_at,
            "fingerprint": self.fingerprint,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Artifact:
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("artifact schema is invalid")
        required = {"artifact_id", "artifact_type", "payload", "created_at", "fingerprint"}
        if not required.issubset(payload):
            raise ValueError("artifact schema is invalid")
        stored_payload = _validated_mapping(payload["payload"], "artifact payload")
        artifact = cls(
            artifact_id=payload["artifact_id"],
            artifact_type=payload["artifact_type"],
            schema_version=payload["schema_version"],
            _payload=stored_payload,
            created_at=payload["created_at"],
        )
        validate_identifier(artifact.artifact_id, "artifact identifier")
        validate_identifier(artifact.artifact_type, "artifact type")
        if payload.get("fingerprint") != artifact.fingerprint:
            raise ValueError("artifact fingerprint is invalid")
        return artifact

    @classmethod
    def from_json(cls, encoded: str) -> Artifact:
        try:
            return cls.from_dict(json.loads(encoded))
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise ValueError("artifact schema is invalid") from exc


@dataclass(frozen=True)
class QuantRun:
    quant_run_id: str
    research_run_id: str
    dataset_version: str
    strategy_version: str
    engine_version: str
    _parameters: dict[str, Any]
    result_artifact: Artifact
    timestamp: str

    @property
    def parameters(self) -> dict[str, Any]:
        """Return a defensive copy so run provenance cannot be mutated."""

        return copy.deepcopy(self._parameters)

    @classmethod
    def create(
        cls,
        *,
        quant_run_id: str,
        research_run_id: str,
        dataset_version: str,
        strategy_version: str,
        engine_version: str,
        parameters: dict[str, Any],
        result_artifact: Artifact,
        timestamp: datetime | str | None = None,
    ) -> QuantRun:
        for value, field in (
            (quant_run_id, "quant run identifier"),
            (research_run_id, "research run identifier"),
            (dataset_version, "dataset version"),
            (strategy_version, "strategy version"),
            (engine_version, "engine version"),
        ):
            validate_identifier(value, field)
        stored_parameters = _validated_mapping(parameters, "parameters")
        if not isinstance(result_artifact, Artifact):
            raise TypeError("result artifact is invalid")
        if timestamp is None:
            timestamp_text = datetime.now(UTC).isoformat()
        elif isinstance(timestamp, datetime):
            timestamp_text = timestamp.isoformat()
        elif isinstance(timestamp, str) and timestamp.strip():
            timestamp_text = timestamp
        else:
            raise ValueError("timestamp is invalid")
        return cls(
            quant_run_id,
            research_run_id,
            dataset_version,
            strategy_version,
            engine_version,
            stored_parameters,
            result_artifact,
            timestamp_text,
        )

    @property
    def fingerprint(self) -> str:
        return _digest(
            {
                "quant_run_id": self.quant_run_id,
                "research_run_id": self.research_run_id,
                "dataset_version": self.dataset_version,
                "strategy_version": self.strategy_version,
                "engine_version": self.engine_version,
                "parameters": self._parameters,
                "result_artifact": self.result_artifact.to_dict(),
                "timestamp": self.timestamp,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": self.quant_run_id,
            "research_run_id": self.research_run_id,
            "dataset_version": self.dataset_version,
            "strategy_version": self.strategy_version,
            "engine_version": self.engine_version,
            "parameters": copy.deepcopy(self._parameters),
            "result_artifact": self.result_artifact.to_dict(),
            "fingerprint": self.fingerprint,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> QuantRun:
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("quant run schema is invalid")
        required = {
            "id",
            "research_run_id",
            "dataset_version",
            "strategy_version",
            "engine_version",
            "parameters",
            "result_artifact",
            "fingerprint",
            "timestamp",
        }
        if not required.issubset(payload):
            raise ValueError("quant run schema is invalid")
        stored_parameters = _validated_mapping(payload["parameters"], "parameters")
        run = cls(
            quant_run_id=payload["id"],
            research_run_id=payload["research_run_id"],
            dataset_version=payload["dataset_version"],
            strategy_version=payload["strategy_version"],
            engine_version=payload["engine_version"],
            _parameters=stored_parameters,
            result_artifact=Artifact.from_dict(payload["result_artifact"]),
            timestamp=payload["timestamp"],
        )
        for value, field in (
            (run.quant_run_id, "quant run identifier"),
            (run.research_run_id, "research run identifier"),
            (run.dataset_version, "dataset version"),
            (run.strategy_version, "strategy version"),
            (run.engine_version, "engine version"),
        ):
            validate_identifier(value, field)
        if payload.get("fingerprint") != run.fingerprint:
            raise ValueError("quant run fingerprint is invalid")
        return run

    @classmethod
    def from_json(cls, encoded: str) -> QuantRun:
        try:
            return cls.from_dict(json.loads(encoded))
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise ValueError("quant run schema is invalid") from exc
