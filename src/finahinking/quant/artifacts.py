"""Data-only, content-addressed P5 artifacts and QuantRun records."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from finahinking.experiments.models import canonical_json

from .interfaces import _digest, validate_identifier

_MAX_ARTIFACT_BYTES = 1_000_000
_FORBIDDEN_KEYS = {"__class__", "__code__", "__globals__", "pickle", "source_code"}


def _reject_executable_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in _FORBIDDEN_KEYS:
                raise ValueError("artifact payload contains executable key")
            _reject_executable_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_executable_keys(item)


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    artifact_type: str
    schema_version: int
    payload: dict[str, Any]
    created_at: str

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
        if not isinstance(payload, dict):
            raise ValueError("artifact payload must be a mapping")
        _reject_executable_keys(payload)
        encoded = canonical_json(payload).encode("utf-8")
        if len(encoded) > _MAX_ARTIFACT_BYTES:
            raise ValueError("artifact payload exceeds size limit")
        timestamp = (created_at or datetime.now(UTC)).isoformat()
        return cls(artifact_id, artifact_type, 1, payload, timestamp)

    @property
    def fingerprint(self) -> str:
        return _digest(
            {
                "artifact_id": self.artifact_id,
                "artifact_type": self.artifact_type,
                "schema_version": self.schema_version,
                "payload": self.payload,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "created_at": self.created_at,
            "fingerprint": self.fingerprint,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Artifact:
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("artifact schema is invalid")
        artifact = cls(
            artifact_id=payload["artifact_id"],
            artifact_type=payload["artifact_type"],
            schema_version=payload["schema_version"],
            payload=payload["payload"],
            created_at=payload["created_at"],
        )
        validate_identifier(artifact.artifact_id, "artifact identifier")
        validate_identifier(artifact.artifact_type, "artifact type")
        _reject_executable_keys(artifact.payload)
        if payload.get("fingerprint") != artifact.fingerprint:
            raise ValueError("artifact fingerprint is invalid")
        return artifact

    @classmethod
    def from_json(cls, encoded: str) -> Artifact:
        import json

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
    parameters: dict[str, Any]
    result_artifact: Artifact
    timestamp: str

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
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be a mapping")
        if not isinstance(result_artifact, Artifact):
            raise ValueError("result artifact is invalid")
        return cls(
            quant_run_id,
            research_run_id,
            dataset_version,
            strategy_version,
            engine_version,
            parameters,
            result_artifact,
            (timestamp or datetime.now(UTC)).isoformat(),
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
                "parameters": self.parameters,
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
            "parameters": self.parameters,
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
        run = cls(
            quant_run_id=payload["id"],
            research_run_id=payload["research_run_id"],
            dataset_version=payload["dataset_version"],
            strategy_version=payload["strategy_version"],
            engine_version=payload["engine_version"],
            parameters=dict(payload["parameters"]),
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
        import json

        try:
            return cls.from_dict(json.loads(encoded))
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise ValueError("quant run schema is invalid") from exc
