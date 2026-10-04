"""Canonical, source-bound records for the P6.5 understanding engine.

These records deliberately do not reuse the price ``Dataset`` shape: a CPI
series is a long-form observation with a logical key, release timing, and
revision versions.  They are immutable and JSON-safe so a capture can be
replayed without importing a provider object.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
# ``source_verified`` is an output of evidence resolution, never caller
# supplied authority.  The token is process-local and intentionally omitted
# from serialization/fingerprints.
_VERIFIED_CLAIM_TOKEN = object()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def _id(value: Any, label: str) -> str:
    normalized = _text(value, label)
    if not _IDENTIFIER.fullmatch(normalized):
        raise ValueError(f"{label} must be a bounded identifier")
    return normalized


def _hash(value: Any, label: str) -> str:
    normalized = _text(value, label).lower()
    if not _HASH.fullmatch(normalized):
        raise ValueError(f"{label} must be a SHA-256 fingerprint")
    return normalized


def _tuple_text(values: Any, label: str) -> tuple[str, ...]:
    if isinstance(values, str) or values is None:
        values = () if values is None else (values,)
    try:
        return tuple(_text(value, label) for value in values)
    except TypeError as exc:
        raise TypeError(f"{label} must be a sequence") from exc


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    normalized = {str(key): value for key, value in value.items()}
    try:
        encoded = _json(normalized)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON serializable") from exc
    if len(encoded.encode("utf-8")) > 250_000:
        raise ValueError(f"{label} is too large")
    return json.loads(encoded)


class SourceTier(str, Enum):
    TIER_0 = "TIER_0"
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"


class AdmissionDecision(str, Enum):
    ADMIT_AUTHORITATIVE = "ADMIT_AUTHORITATIVE"
    ADMIT_PROVIDER = "ADMIT_PROVIDER"
    ADMIT_RESEARCH_ONLY = "ADMIT_RESEARCH_ONLY"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    DEFER = "DEFER"
    REJECT = "REJECT"


class RevisionStatus(str, Enum):
    ORIGINAL = "ORIGINAL"
    REVISED = "REVISED"
    SUPERSEDED = "SUPERSEDED"
    UNRESOLVED_REVISION = "UNRESOLVED_REVISION"


class ClaimType(str, Enum):
    FACT = "FACT"
    INTERPRETATION = "INTERPRETATION"
    HYPOTHESIS = "HYPOTHESIS"
    QUANT_FINDING = "QUANT_FINDING"
    UNKNOWN = "UNKNOWN"
    LIMITATION = "LIMITATION"


class EvidenceStatus(str, Enum):
    DIRECT_SOURCE = "DIRECT_SOURCE"
    DERIVED_FROM_SOURCE = "DERIVED_FROM_SOURCE"
    QUANT_SUPPORTED = "QUANT_SUPPORTED"
    THEORY_SUPPORTED = "THEORY_SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class Source:
    source_id: str
    name: str
    publisher: str
    tier: SourceTier
    canonical_url: str
    underlying_source: str
    owner: str
    access_method: str
    usage_conditions: str
    authentication: str
    decision: AdmissionDecision
    source_fingerprint: str | None = None
    admitted_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _id(self.source_id, "source_id"))
        for name in ("name", "publisher", "canonical_url", "underlying_source", "owner", "access_method", "usage_conditions", "authentication"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.tier, SourceTier):
            object.__setattr__(self, "tier", SourceTier(self.tier))
        if not isinstance(self.decision, AdmissionDecision):
            object.__setattr__(self, "decision", AdmissionDecision(self.decision))
        if self.source_fingerprint is not None:
            supplied = _hash(self.source_fingerprint, "source_fingerprint")
            expected = self._computed_fingerprint()
            if supplied != expected:
                raise ValueError("source_fingerprint does not match source metadata")
            object.__setattr__(self, "source_fingerprint", supplied)
        else:
            object.__setattr__(self, "source_fingerprint", self._computed_fingerprint())

    def _computed_fingerprint(self) -> str:
        return _digest({key: value for key, value in self.to_dict(include_fingerprint=False).items()})

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        payload = {
            "source_id": self.source_id,
            "name": self.name,
            "publisher": self.publisher,
            "tier": self.tier.value,
            "canonical_url": self.canonical_url,
            "underlying_source": self.underlying_source,
            "owner": self.owner,
            "access_method": self.access_method,
            "usage_conditions": self.usage_conditions,
            "authentication": self.authentication,
            "decision": self.decision.value,
            "admitted_at": self.admitted_at,
        }
        if include_fingerprint:
            payload["source_fingerprint"] = self.source_fingerprint
        return payload

    @property
    def fingerprint(self) -> str:
        return str(self.source_fingerprint)


@dataclass(frozen=True)
class SourceEndpoint:
    endpoint_id: str
    source_id: str
    url: str
    method: str
    content_type: str
    rate_limit: str
    historical_support: bool
    revision_support: str
    available_at_semantics: str
    active: bool = True

    def __post_init__(self) -> None:
        for name in ("endpoint_id", "source_id"):
            object.__setattr__(self, name, _id(getattr(self, name), name))
        for name in ("url", "method", "content_type", "rate_limit", "revision_support", "available_at_semantics"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.historical_support, bool) or not isinstance(self.active, bool):
            raise TypeError("endpoint booleans are invalid")

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"endpoint_id": self.endpoint_id, "source_id": self.source_id, "url": self.url, "method": self.method, "content_type": self.content_type, "rate_limit": self.rate_limit, "historical_support": self.historical_support, "revision_support": self.revision_support, "available_at_semantics": self.available_at_semantics, "active": self.active}


@dataclass(frozen=True)
class SourceRelease:
    release_id: str
    source_id: str
    endpoint_id: str
    event_type: str
    reference_period: str
    published_at: str
    available_at: str | None
    release_url: str
    schedule_fingerprint: str | None = None

    def __post_init__(self) -> None:
        for name in ("release_id", "source_id", "endpoint_id"):
            object.__setattr__(self, name, _id(getattr(self, name), name))
        for name in ("event_type", "reference_period", "published_at", "release_url"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.available_at is not None:
            object.__setattr__(self, "available_at", _text(self.available_at, "available_at"))
        if self.schedule_fingerprint is not None:
            object.__setattr__(self, "schedule_fingerprint", _hash(self.schedule_fingerprint, "schedule_fingerprint"))
        from .temporal import validate_temporal_order

        validate_temporal_order(
            occurred_at=None,
            effective_at=None,
            published_at=self.published_at,
            available_at=self.available_at,
            retrieved_at=None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"release_id": self.release_id, "source_id": self.source_id, "endpoint_id": self.endpoint_id, "event_type": self.event_type, "reference_period": self.reference_period, "published_at": self.published_at, "available_at": self.available_at, "release_url": self.release_url, "schedule_fingerprint": self.schedule_fingerprint}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class TransportCapture:
    capture_id: str
    source_id: str
    endpoint_id: str
    request_fingerprint: str
    retrieved_at: str
    first_observed_at: str
    status: int
    content_type: str
    relevant_headers: dict[str, str]
    raw_artifact_id: str
    payload_hash: str
    parser_version: str
    raw_payload: str | None = None

    def __post_init__(self) -> None:
        for name in ("capture_id", "source_id", "endpoint_id", "raw_artifact_id"):
            object.__setattr__(self, name, _id(getattr(self, name), name))
        for name in ("request_fingerprint", "payload_hash"):
            object.__setattr__(self, name, _hash(getattr(self, name), name))
        for name in ("retrieved_at", "first_observed_at", "content_type", "parser_version"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        from .temporal import _parse

        if _parse(self.first_observed_at, "first_observed_at") > _parse(self.retrieved_at, "retrieved_at"):
            raise ValueError("temporal order requires first_observed_at <= retrieved_at")
        if not isinstance(self.status, int) or isinstance(self.status, bool) or not 100 <= self.status <= 599:
            raise ValueError("status must be an HTTP status")
        headers = _mapping(self.relevant_headers, "relevant_headers")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in headers.items()):
            raise TypeError("headers must be text")
        object.__setattr__(self, "relevant_headers", headers)
        if self.raw_payload is not None and not isinstance(self.raw_payload, str):
            raise TypeError("raw_payload must be text")

    def to_dict(self) -> dict[str, Any]:
        return {"capture_id": self.capture_id, "source_id": self.source_id, "endpoint_id": self.endpoint_id, "request_fingerprint": self.request_fingerprint, "retrieved_at": self.retrieved_at, "first_observed_at": self.first_observed_at, "status": self.status, "content_type": self.content_type, "relevant_headers": dict(self.relevant_headers), "raw_artifact_id": self.raw_artifact_id, "payload_hash": self.payload_hash, "parser_version": self.parser_version}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Measurement:
    metric: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric", _text(self.metric, "metric"))
        object.__setattr__(self, "unit", _text(self.unit, "unit"))
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)) or not math.isfinite(float(self.value)):
            raise ValueError("measurement value must be finite")
        object.__setattr__(self, "value", float(self.value))

    def to_dict(self) -> dict[str, Any]:
        return {"metric": self.metric, "value": self.value, "unit": self.unit}


@dataclass(frozen=True)
class ObservationVersion:
    version_id: str
    value: float
    unit: str
    occurred_at: str
    effective_at: str
    published_at: str | None
    available_at: str | None
    retrieved_at: str
    capture_id: str
    revision_status: RevisionStatus = RevisionStatus.ORIGINAL
    supersedes_version_id: str | None = None
    footnotes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        from .temporal import validate_temporal_order

        object.__setattr__(self, "version_id", _id(self.version_id, "version_id"))
        object.__setattr__(self, "capture_id", _id(self.capture_id, "capture_id"))
        object.__setattr__(self, "unit", _text(self.unit, "unit"))
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)) or not math.isfinite(float(self.value)):
            raise ValueError("observation value must be finite")
        object.__setattr__(self, "value", float(self.value))
        for name in ("occurred_at", "effective_at", "retrieved_at"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("published_at", "available_at"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _text(value, name))
        validate_temporal_order(occurred_at=self.occurred_at, effective_at=self.effective_at, published_at=self.published_at, available_at=self.available_at, retrieved_at=self.retrieved_at)
        if not isinstance(self.revision_status, RevisionStatus):
            object.__setattr__(self, "revision_status", RevisionStatus(self.revision_status))
        if self.supersedes_version_id is not None:
            object.__setattr__(self, "supersedes_version_id", _id(self.supersedes_version_id, "supersedes_version_id"))
        object.__setattr__(self, "footnotes", _tuple_text(self.footnotes, "footnote"))

    def to_dict(self) -> dict[str, Any]:
        return {"version_id": self.version_id, "value": self.value, "unit": self.unit, "occurred_at": self.occurred_at, "effective_at": self.effective_at, "published_at": self.published_at, "available_at": self.available_at, "retrieved_at": self.retrieved_at, "capture_id": self.capture_id, "revision_status": self.revision_status.value, "supersedes_version_id": self.supersedes_version_id, "footnotes": list(self.footnotes)}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Observation:
    observation_id: str
    source_id: str
    series_id: str
    reference_period: str
    dimensions: dict[str, str]
    versions: tuple[ObservationVersion, ...]

    def __post_init__(self) -> None:
        for name in ("observation_id", "source_id", "series_id", "reference_period"):
            object.__setattr__(self, name, _id(getattr(self, name), name))
        dims = _mapping(self.dimensions, "dimensions")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in dims.items()):
            raise TypeError("dimensions must be text")
        object.__setattr__(self, "dimensions", dims)
        if not self.versions or any(not isinstance(version, ObservationVersion) for version in self.versions):
            raise ValueError("observation must contain versions")
        ids = [version.version_id for version in self.versions]
        if len(set(ids)) != len(ids):
            raise ValueError("observation versions must be unique")
        object.__setattr__(self, "versions", tuple(self.versions))

    @property
    def latest(self) -> ObservationVersion:
        from .temporal import _parse

        return max(self.versions, key=lambda version: _parse(version.retrieved_at, "retrieved_at"))

    def to_dict(self) -> dict[str, Any]:
        return {"observation_id": self.observation_id, "source_id": self.source_id, "series_id": self.series_id, "reference_period": self.reference_period, "dimensions": dict(self.dimensions), "versions": [version.to_dict() for version in self.versions]}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    source_id: str
    reference_period: str
    published_at: str
    available_at: str | None
    observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    occurred_at: str | None = None
    effective_at: str | None = None
    revision_status: RevisionStatus = RevisionStatus.ORIGINAL

    def __post_init__(self) -> None:
        for name in ("event_id", "source_id"):
            object.__setattr__(self, name, _id(getattr(self, name), name))
        for name in ("event_type", "reference_period", "published_at"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.available_at is not None:
            object.__setattr__(self, "available_at", _text(self.available_at, "available_at"))
        for name in ("occurred_at", "effective_at"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _text(value, name))
        object.__setattr__(self, "observation_ids", tuple(_id(value, "observation_id") for value in self.observation_ids))
        object.__setattr__(self, "evidence_ids", tuple(_id(value, "evidence_id") for value in self.evidence_ids))
        if not self.observation_ids:
            raise ValueError("event must link observations")
        if not self.evidence_ids:
            raise ValueError("event must link evidence")
        if not isinstance(self.revision_status, RevisionStatus):
            object.__setattr__(self, "revision_status", RevisionStatus(self.revision_status))
        from .temporal import validate_temporal_order

        validate_temporal_order(occurred_at=self.occurred_at or self.published_at, effective_at=self.effective_at or self.occurred_at or self.published_at, published_at=self.published_at, available_at=self.available_at, retrieved_at=self.available_at or self.published_at)

    def to_dict(self) -> dict[str, Any]:
        return {"event_id": self.event_id, "event_type": self.event_type, "source_id": self.source_id, "reference_period": self.reference_period, "occurred_at": self.occurred_at, "effective_at": self.effective_at, "published_at": self.published_at, "available_at": self.available_at, "observation_ids": list(self.observation_ids), "evidence_ids": list(self.evidence_ids), "revision_status": self.revision_status.value}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    evidence_type: str
    source_id: str
    capture_id: str | None
    reference: str
    status: EvidenceStatus
    scope: str
    limitations: tuple[str, ...] = ()
    source_fingerprint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _id(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "source_id", _id(self.source_id, "source_id"))
        if self.capture_id is not None:
            object.__setattr__(self, "capture_id", _id(self.capture_id, "capture_id"))
        for name in ("evidence_type", "reference", "scope"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.status, EvidenceStatus):
            object.__setattr__(self, "status", EvidenceStatus(self.status))
        object.__setattr__(self, "limitations", _tuple_text(self.limitations, "limitation"))
        if self.source_fingerprint is not None:
            object.__setattr__(self, "source_fingerprint", _hash(self.source_fingerprint, "source_fingerprint"))

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "evidence_type": self.evidence_type, "source_id": self.source_id, "capture_id": self.capture_id, "reference": self.reference, "status": self.status.value, "scope": self.scope, "limitations": list(self.limitations), "source_fingerprint": self.source_fingerprint}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim_type: ClaimType
    text: str
    evidence_ids: tuple[str, ...]
    evidence_status: EvidenceStatus
    source_fingerprint: str | None = None
    source_verified: bool = False
    limitations: tuple[str, ...] = ()
    _verification_token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _id(self.claim_id, "claim_id"))
        object.__setattr__(self, "text", _text(self.text, "claim text"))
        object.__setattr__(self, "evidence_ids", tuple(_id(value, "evidence_id") for value in self.evidence_ids))
        if not self.evidence_ids:
            raise ValueError("claim must link evidence")
        if not isinstance(self.claim_type, ClaimType):
            object.__setattr__(self, "claim_type", ClaimType(self.claim_type))
        if not isinstance(self.evidence_status, EvidenceStatus):
            object.__setattr__(self, "evidence_status", EvidenceStatus(self.evidence_status))
        if self.source_fingerprint is not None:
            object.__setattr__(self, "source_fingerprint", _hash(self.source_fingerprint, "source_fingerprint"))
        if not isinstance(self.source_verified, bool):
            raise TypeError("source_verified must be boolean")
        if self.source_verified and self.source_fingerprint is None:
            raise ValueError("verified claims require a source fingerprint")
        if self.source_verified and self._verification_token is not _VERIFIED_CLAIM_TOKEN:
            raise ValueError("source_verified claims require an internal evidence token")
        object.__setattr__(self, "limitations", _tuple_text(self.limitations, "limitation"))

    def to_dict(self) -> dict[str, Any]:
        return {"claim_id": self.claim_id, "claim_type": self.claim_type.value, "text": self.text, "evidence_ids": list(self.evidence_ids), "evidence_status": self.evidence_status.value, "source_fingerprint": self.source_fingerprint, "source_verified": self.source_verified, "limitations": list(self.limitations)}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class ClaimEvidenceLink:
    claim_id: str
    evidence_id: str
    support_type: EvidenceStatus
    scope: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _id(self.claim_id, "claim_id"))
        object.__setattr__(self, "evidence_id", _id(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "scope", _text(self.scope, "scope"))
        if not isinstance(self.support_type, EvidenceStatus):
            object.__setattr__(self, "support_type", EvidenceStatus(self.support_type))
        object.__setattr__(self, "limitations", _tuple_text(self.limitations, "limitation"))

    def to_dict(self) -> dict[str, Any]:
        return {"claim_id": self.claim_id, "evidence_id": self.evidence_id, "support_type": self.support_type.value, "scope": self.scope, "limitations": list(self.limitations)}


@dataclass(frozen=True)
class Concept:
    concept_id: str
    name: str
    definition: str
    formula: str = ""
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _id(self.concept_id, "concept_id"))
        object.__setattr__(self, "name", _text(self.name, "concept name"))
        object.__setattr__(self, "definition", _text(self.definition, "concept definition"))
        if not isinstance(self.formula, str):
            raise TypeError("formula must be text")
        object.__setattr__(self, "evidence_ids", tuple(_id(value, "evidence_id") for value in self.evidence_ids))

    def to_dict(self) -> dict[str, Any]:
        return {"concept_id": self.concept_id, "name": self.name, "definition": self.definition, "formula": self.formula, "evidence_ids": list(self.evidence_ids)}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class ConceptRelation:
    relation_id: str
    from_concept_id: str
    to_concept_id: str
    relation_type: str
    evidence_status: EvidenceStatus
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("relation_id", "from_concept_id", "to_concept_id"):
            object.__setattr__(self, name, _id(getattr(self, name), name))
        object.__setattr__(self, "relation_type", _text(self.relation_type, "relation_type"))
        if not isinstance(self.evidence_status, EvidenceStatus):
            object.__setattr__(self, "evidence_status", EvidenceStatus(self.evidence_status))
        object.__setattr__(self, "evidence_ids", tuple(_id(value, "evidence_id") for value in self.evidence_ids))

    def to_dict(self) -> dict[str, Any]:
        return {"relation_id": self.relation_id, "from_concept_id": self.from_concept_id, "to_concept_id": self.to_concept_id, "relation_type": self.relation_type, "evidence_status": self.evidence_status.value, "evidence_ids": list(self.evidence_ids)}


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    statement: str
    null_statement: str
    event_id: str
    factor: str
    benchmark: str
    evaluation_boundary: dict[str, Any]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "hypothesis_id", _id(self.hypothesis_id, "hypothesis_id"))
        object.__setattr__(self, "event_id", _id(self.event_id, "event_id"))
        for name in ("statement", "null_statement", "factor", "benchmark"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "evaluation_boundary", _mapping(self.evaluation_boundary, "evaluation_boundary"))
        object.__setattr__(self, "limitations", _tuple_text(self.limitations, "limitation"))

    def to_dict(self) -> dict[str, Any]:
        return {"hypothesis_id": self.hypothesis_id, "statement": self.statement, "null_statement": self.null_statement, "event_id": self.event_id, "factor": self.factor, "benchmark": self.benchmark, "evaluation_boundary": self.evaluation_boundary, "limitations": list(self.limitations)}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


__all__ = [
    "AdmissionDecision",
    "Claim",
    "ClaimEvidenceLink",
    "ClaimType",
    "Concept",
    "ConceptRelation",
    "Event",
    "Evidence",
    "EvidenceStatus",
    "Hypothesis",
    "Measurement",
    "Observation",
    "ObservationVersion",
    "RevisionStatus",
    "Source",
    "SourceEndpoint",
    "SourceRelease",
    "SourceTier",
    "TransportCapture",
]
