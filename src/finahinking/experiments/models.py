"""Serializable research-run records and deterministic fingerprints."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from finahinking.data.models import Dataset
from finahinking.factors.core import FactorDefinition


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return _safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _fingerprint_safe(value: Any) -> Any:
    """Normalize numeric noise before hashing cross-platform experiment results."""

    safe = _safe(value)
    if isinstance(safe, dict):
        return {str(key): _fingerprint_safe(item) for key, item in safe.items()}
    if isinstance(safe, (list, tuple)):
        return [_fingerprint_safe(item) for item in safe]
    if isinstance(safe, float):
        return float(format(safe, ".15g"))
    return safe


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_fingerprint_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def dataset_payload(dataset: Dataset) -> dict[str, Any]:
    frame = dataset.frame.copy()
    records = []
    for index, row in frame.iterrows():
        record = {"date": pd.Timestamp(index).isoformat()}
        record.update({str(key): _safe(value) for key, value in row.to_dict().items()})
        records.append(record)
    provenance = {
        "provider": dataset.provenance.provider,
        "source_url": dataset.provenance.source_url,
        "retrieved_at": dataset.provenance.retrieved_at,
        "license": dataset.provenance.license,
    }
    return {"columns": [str(column) for column in frame.columns], "records": records, "provenance": provenance}


@dataclass(frozen=True)
class ResearchRun:
    run_id: str
    question: str
    hypothesis: str
    dataset: dict[str, Any]
    factor_name: str
    factor_definition: str
    factor_explanation: str
    factor_limitations: str
    method: str
    parameters: dict[str, Any]
    result: dict[str, Any]
    conclusion: str
    insight: str
    limitations: tuple[str, ...]
    created_at: str
    engine_version: str = "0.1.0"

    @classmethod
    def create(
        cls,
        *,
        question: str,
        hypothesis: str,
        dataset: Dataset,
        factor: FactorDefinition,
        method: str,
        parameters: dict[str, Any],
        result: dict[str, Any],
        conclusion: str,
        insight: str,
        limitations: list[str] | tuple[str, ...],
        run_id: str | None = None,
        created_at: str | None = None,
        engine_version: str | None = None,
    ) -> ResearchRun:
        for name, value in (("question", question), ("hypothesis", hypothesis), ("method", method), ("conclusion", conclusion), ("insight", insight)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        identifier = run_id or __import__("uuid").uuid4().hex
        if not identifier or "/" in identifier or "\\" in identifier:
            raise ValueError("run id is invalid")
        resolved_engine_version = "0.1.0" if engine_version is None else engine_version
        if not isinstance(resolved_engine_version, str) or not resolved_engine_version.strip():
            raise ValueError("engine version is required")
        payload = dataset_payload(dataset)
        return cls(
            run_id=identifier,
            question=question,
            hypothesis=hypothesis,
            dataset={**payload, "fingerprint": _digest(payload)},
            factor_name=factor.name,
            factor_definition=factor.definition,
            factor_explanation=factor.explanation,
            factor_limitations=factor.limitations,
            method=method,
            parameters=_safe(parameters),
            result=_safe(result),
            conclusion=conclusion,
            insight=insight,
            limitations=tuple(str(item) for item in limitations),
            created_at=created_at or datetime.now(UTC).isoformat(),
            engine_version=resolved_engine_version,
        )

    @property
    def dataset_fingerprint(self) -> str:
        return str(self.dataset["fingerprint"])

    @property
    def result_fingerprint(self) -> str:
        return _stable_digest({"dataset": self.dataset_fingerprint, "factor": self.factor_name, "factor_definition": self.factor_definition, "method": self.method, "parameters": self.parameters, "result": self.result})

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, **{key: _safe(value) for key, value in self.__dict__.items()}, "result_fingerprint": self.result_fingerprint}

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ResearchRun:
        required = {"schema_version", "run_id", "question", "hypothesis", "dataset", "factor_name", "factor_definition", "factor_explanation", "factor_limitations", "method", "parameters", "result", "conclusion", "insight", "limitations", "created_at", "engine_version", "result_fingerprint"}
        if not isinstance(payload, dict) or not required.issubset(payload) or payload.get("schema_version") != 1:
            raise ValueError("research run schema is invalid")
        values = {key: payload[key] for key in required - {"schema_version", "result_fingerprint"}}
        dataset = values["dataset"]
        if not isinstance(dataset, dict) or "fingerprint" not in dataset:
            raise ValueError("research run schema is invalid")
        dataset_without_fingerprint = {key: value for key, value in dataset.items() if key != "fingerprint"}
        if dataset["fingerprint"] != _digest(dataset_without_fingerprint):
            raise ValueError("research run dataset fingerprint is invalid")
        values["limitations"] = tuple(values["limitations"])
        run = cls(**values)
        if run.result_fingerprint != payload["result_fingerprint"]:
            raise ValueError("research run result fingerprint is invalid")
        return run

    @classmethod
    def from_json(cls, encoded: str) -> ResearchRun:
        try:
            return cls.from_dict(json.loads(encoded))
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise ValueError("research run schema is invalid") from exc
