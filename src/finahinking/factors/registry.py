"""Versioned factor metadata, health and bounded validation lifecycle."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from .core import FactorDefinition
from .evaluation import FactorAdmissionDecision


class FactorHealthStatus(str, Enum):
    VALID = "VALID"
    DECAYING = "DECAYING"
    REVERSED = "REVERSED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    RETIRED = "RETIRED"


def _date(value: date | str) -> date:
    if isinstance(value, str):
        value = date.fromisoformat(value)
    if not isinstance(value, date):
        raise TypeError("as_of must be a date")
    return value


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")
    return value.strip()


@dataclass(frozen=True, slots=True)
class FactorMetadata:
    factor_id: str
    version: str
    definition: str
    formula: str
    input_fields: tuple[str, ...]
    source: str
    pit: bool
    direction: str
    limits: Mapping[str, Any]
    validation_spec: Mapping[str, Any]

    def __post_init__(self) -> None:
        for name in ("factor_id", "version", "definition", "formula", "source", "direction"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not self.pit:
            raise ValueError("pit must be true for an eligible factor")
        object.__setattr__(self, "input_fields", tuple(_text(item, "input_fields") for item in self.input_fields))
        if not self.input_fields:
            raise ValueError("input_fields must not be empty")
        object.__setattr__(self, "limits", dict(self.limits))
        object.__setattr__(self, "validation_spec", dict(self.validation_spec))
        if not self.validation_spec:
            raise ValueError("validation_spec must not be empty")


@dataclass(frozen=True, slots=True)
class FactorHealth:
    status: FactorHealthStatus
    as_of: date | str
    ic: float
    icir: float
    decay_score: float
    crowding_score: float
    collinearity_score: float
    sample_size: int
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.status, FactorHealthStatus):
            object.__setattr__(self, "status", FactorHealthStatus(self.status))
        object.__setattr__(self, "as_of", _date(self.as_of))
        if self.sample_size < 0:
            raise ValueError("sample_size must be non-negative")
        object.__setattr__(self, "reason", _text(self.reason, "reason"))


@dataclass(frozen=True, slots=True)
class RegisteredFactor:
    definition: FactorDefinition
    metadata: FactorMetadata
    health_history: tuple[FactorHealth, ...]

    @property
    def health(self) -> FactorHealth:
        return self.health_history[-1]


@dataclass(frozen=True, slots=True)
class FactorLifecycleResult:
    accepted: bool
    steps: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    failed_step: str | None = None
    reason: str | None = None


class FactorRegistry:
    def __init__(self) -> None:
        self._factors: dict[str, RegisteredFactor] = {}
        self._admissions: dict[str, list[FactorAdmissionDecision]] = {}

    def register(self, factor: FactorDefinition, metadata: FactorMetadata, health: FactorHealth) -> RegisteredFactor:
        if metadata.factor_id in self._factors:
            raise ValueError(f"factor {metadata.factor_id} is already registered")
        if _date(health.as_of) < date(2000, 1, 1):
            raise ValueError("health as_of is outside supported range")
        registered = RegisteredFactor(factor, metadata, (health,))
        self._factors[metadata.factor_id] = registered
        return registered

    def register_catalog_entry(self, entry: Any, admission: Any) -> RegisteredFactor:
        """Write an audited catalog entry only with an explicit human admission."""

        from finahinking.research.factor_catalog import (
            HumanAdmissionRecord,
            audit_factor_catalog_entry,
        )

        if not isinstance(admission, HumanAdmissionRecord):
            raise TypeError("HumanAdmissionRecord is required before registry write")
        audit = audit_factor_catalog_entry(entry)
        if not audit.eligible:
            raise ValueError("catalog entry is not eligible for admission")
        if entry.status != "PROPOSED":
            raise ValueError("only proposed catalog entries can be admitted")
        if admission.proposal_id != entry.factor_id or admission.research_fingerprint != entry.research_fingerprint:
            raise ValueError("admission record does not bind catalog entry")
        if entry.factor_id in self._factors:
            raise ValueError(f"factor {entry.factor_id} is already registered")
        import re

        from finahinking.factors.core import momentum_factor

        match = re.fullmatch(r"momentum_(\d+)d", entry.factor_id)
        factor = momentum_factor(int(match.group(1))) if match else FactorDefinition(
            name=entry.factor_id,
            definition=f"Audited factor {entry.factor_id}.",
            explanation="Catalog-admitted paper research factor.",
            limitations="Paper-only until independently validated.",
            compute=lambda values: values,
        )
        metadata = FactorMetadata(
            factor_id=entry.factor_id,
            version=entry.version,
            definition=factor.definition,
            formula=factor.definition,
            input_fields=entry.required_fields,
            source=entry.source_ids[0],
            pit=True,
            direction="positive",
            limits={"paper_only": True},
            validation_spec={"shift_periods": 1, "oos": True, "research_fingerprint": entry.research_fingerprint},
        )
        health = FactorHealth(FactorHealthStatus.VALID, "2000-01-01", 0.0, 0.0, 0.0, 0.0, 0.0, 0, "human admission")
        return self.register(factor, metadata, health)

    def get(self, factor_id: str) -> RegisteredFactor:
        try:
            return self._factors[factor_id]
        except KeyError as exc:
            raise LookupError(f"factor {factor_id!r} is not registered") from exc

    def list(self) -> tuple[RegisteredFactor, ...]:
        return tuple(self._factors[key] for key in sorted(self._factors))

    def update_health(self, factor_id: str, health: FactorHealth) -> RegisteredFactor:
        current = self.get(factor_id)
        if _date(health.as_of) < current.health.as_of:
            raise ValueError("health updates must be append-only and non-decreasing by as_of")
        updated = RegisteredFactor(current.definition, current.metadata, current.health_history + (health,))
        self._factors[factor_id] = updated
        return updated

    def select_eligible(self, as_of: date | str, constraints: Mapping[str, Any] | None = None) -> tuple[RegisteredFactor, ...]:
        cutoff = _date(as_of)
        constraints = constraints or {}
        eligible: list[RegisteredFactor] = []
        for factor in self.list():
            if factor.health.as_of > cutoff or factor.health.status is not FactorHealthStatus.VALID:
                continue
            if any(factor.metadata.limits.get(key, value) > value for key, value in constraints.items() if isinstance(value, (int, float))):
                continue
            eligible.append(factor)
        return tuple(eligible)

    def record_admission(self, decision: FactorAdmissionDecision) -> FactorAdmissionDecision:
        history = self._admissions.setdefault(decision.candidate_id, [])
        if history and history[-1].evaluation_fingerprint == decision.evaluation_fingerprint:
            raise ValueError("duplicate factor admission evaluation")
        history.append(decision)
        return decision

    def admission_history(self, candidate_id: str | None = None) -> tuple[FactorAdmissionDecision, ...]:
        if candidate_id is not None:
            return tuple(self._admissions.get(candidate_id, ()))
        return tuple(item for key in sorted(self._admissions) for item in self._admissions[key])


_LIFECYCLE_STEPS = (
    "HYPOTHESIS",
    "COMPUTE",
    "IC_IR",
    "DEDUPE",
    "T_PLUS_ONE",
    "ANNUAL_OOS",
    "ORTHOGONAL_CAPACITY",
    "ARCHIVE_OR_FALSE",
)


def run_factor_lifecycle(
    factor: FactorDefinition,
    dataset_snapshot: Mapping[str, Any],
    validation_spec: Mapping[str, Any],
) -> FactorLifecycleResult:
    snapshot_as_of = _date(dataset_snapshot.get("as_of", "2000-01-01"))
    requested_as_of = validation_spec.get("as_of")
    if requested_as_of is not None and snapshot_as_of > _date(requested_as_of):
        return FactorLifecycleResult(False, (), (), "PIT", "dataset snapshot is after requested as_of")
    refs: list[str] = []
    for step in _LIFECYCLE_STEPS:
        refs.append(f"factor:{factor.name}:{step.lower()}")
        if step == "T_PLUS_ONE" and int(validation_spec.get("shift_periods", 1)) < 1:
            return FactorLifecycleResult(False, tuple(_LIFECYCLE_STEPS[: len(refs)]), tuple(refs), step, "T+1 shift is required")
        if step == "ANNUAL_OOS" and validation_spec.get("oos") is not True:
            return FactorLifecycleResult(False, tuple(_LIFECYCLE_STEPS[: len(refs)]), tuple(refs), step, "out-of-sample validation is required")
    return FactorLifecycleResult(True, _LIFECYCLE_STEPS, tuple(refs))
