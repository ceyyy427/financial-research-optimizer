"""Audit metadata for research factor proposals.

The catalog is deliberately separate from :mod:`finahinking.factors.registry`.
Research automation may create entries with ``PROPOSED`` status, but an entry
is never written to the production registry by this module.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SEMVER = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
_UNSAFE_FIELD = re.compile(r"(?:future|lookahead|target|label|forward|next|tomorrow)", re.IGNORECASE)
_LICENSE_ALLOWLIST = frozenset({
    "APPROVED", "VERIFIED", "PUBLIC_DOMAIN", "INTERNAL", "FIXTURE", "MIT",
    "APACHE_2_0", "BSD_2_CLAUSE", "BSD_3_CLAUSE", "CC_BY_4_0", "CC0_1_0",
})
_PIT_ALLOWLIST = frozenset({"PIT", "POINT_IN_TIME", "T+1", "T+1_POINT_IN_TIME", "T_PLUS_1", "T_PLUS_1_POINT_IN_TIME"})
_KNOWN_STATUSES = frozenset({"PROPOSED", "BLOCKED", "REVIEW", "RETIRED"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class FactorCatalogAudit:
    """The deterministic result of auditing catalog metadata."""

    eligible: bool
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"eligible": self.eligible, "limitations": list(self.limitations)}


@dataclass(frozen=True, slots=True)
class HumanAdmissionRecord:
    """Immutable, independently recorded approval evidence."""

    proposal_id: str
    evaluation_fingerprint: str
    research_fingerprint: str
    reviewer_id: str
    decision: str = "APPROVE"

    def __post_init__(self) -> None:
        for name in ("proposal_id", "evaluation_fingerprint", "research_fingerprint", "reviewer_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
            object.__setattr__(self, name, value.strip())
        if not _HEX64.fullmatch(self.evaluation_fingerprint) or not _HEX64.fullmatch(self.research_fingerprint):
            raise ValueError("admission fingerprints must be SHA-256 hex digests")
        if self.decision != "APPROVE":
            raise ValueError("only explicit APPROVE admission records are accepted")

    @property
    def fingerprint(self) -> str:
        return _digest({"proposal_id": self.proposal_id, "evaluation_fingerprint": self.evaluation_fingerprint, "research_fingerprint": self.research_fingerprint, "reviewer_id": self.reviewer_id, "decision": self.decision})

    def to_dict(self) -> dict[str, str]:
        return {"proposal_id": self.proposal_id, "evaluation_fingerprint": self.evaluation_fingerprint, "research_fingerprint": self.research_fingerprint, "reviewer_id": self.reviewer_id, "decision": self.decision, "fingerprint": self.fingerprint}


@dataclass(frozen=True, slots=True)
class FactorCatalogEntry:
    factor_id: str
    version: str
    source_ids: tuple[str, ...]
    license_status: str
    pit_semantics: str
    required_fields: tuple[str, ...]
    research_fingerprint: str
    status: str = "PROPOSED"
    evaluation_fingerprint: str | None = None

    def __post_init__(self) -> None:
        for name in ("factor_id", "version", "research_fingerprint", "status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.pit_semantics, str) or not self.pit_semantics.strip():
            raise ValueError("PIT semantics must be non-empty")
        object.__setattr__(self, "pit_semantics", self.pit_semantics.strip())
        source_ids = tuple(item.strip() for item in self.source_ids if isinstance(item, str) and item.strip())
        fields = tuple(item.strip() for item in self.required_fields if isinstance(item, str) and item.strip())
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "required_fields", fields)
        object.__setattr__(self, "license_status", "" if self.license_status is None else str(self.license_status).strip())
        if self.status not in _KNOWN_STATUSES:
            raise ValueError("status is not a recognized catalog status")
        if not _SEMVER.fullmatch(self.version):
            raise ValueError("version must be semantic version x.y.z")
        if self.research_fingerprint and not _HEX64.fullmatch(self.research_fingerprint):
            raise ValueError("research_fingerprint must be a SHA-256 hex digest")
        if self.evaluation_fingerprint is not None and not _HEX64.fullmatch(self.evaluation_fingerprint):
            raise ValueError("evaluation_fingerprint must be a SHA-256 hex digest")

    @property
    def production_admitted(self) -> bool:
        return self.status == "ADMITTED"

    @property
    def fingerprint(self) -> str:
        return _digest(self._payload())

    def _payload(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "version": self.version,
            "source_ids": list(self.source_ids),
            "license_status": self.license_status,
            "pit_semantics": self.pit_semantics,
            "required_fields": list(self.required_fields),
            "research_fingerprint": self.research_fingerprint,
            "status": self.status,
            "evaluation_fingerprint": self.evaluation_fingerprint,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "fingerprint": self.fingerprint}


def audit_factor_catalog_entry(entry: FactorCatalogEntry, *, require_evaluation: bool = False) -> FactorCatalogAudit:
    """Fail closed when source, license, PIT or field metadata is incomplete."""

    if not isinstance(entry, FactorCatalogEntry):
        raise TypeError("entry must be a FactorCatalogEntry")
    if not entry.source_ids:
        raise ValueError("source metadata is required")
    license_status = re.sub(r"[^A-Z0-9]+", "_", entry.license_status.upper()).strip("_")
    if license_status not in _LICENSE_ALLOWLIST:
        raise ValueError("source license is missing or not approved")
    pit = re.sub(r"[\s-]+", "_", entry.pit_semantics.strip().upper())
    if pit not in _PIT_ALLOWLIST:
        raise ValueError("PIT semantics are missing or unknown")
    if not entry.required_fields:
        raise ValueError("required source fields are missing")
    if require_evaluation and not entry.evaluation_fingerprint:
        raise ValueError("evaluation fingerprint is required")
    if len(set(entry.source_ids)) != len(entry.source_ids):
        raise ValueError("duplicate source metadata")
    if len(set(entry.required_fields)) != len(entry.required_fields):
        raise ValueError("duplicate required fields")
    unsafe = next((field for field in entry.required_fields if _UNSAFE_FIELD.search(field)), None)
    if unsafe is not None:
        raise ValueError(f"future-looking field is not allowed: {unsafe}")
    if entry.status == "BLOCKED":
        return FactorCatalogAudit(False, ("catalog entry is blocked",))
    return FactorCatalogAudit(True, ())


def validate_factor_catalog_entry(entry: FactorCatalogEntry) -> None:
    """Validate an entry without mutating a production registry."""

    audit_factor_catalog_entry(entry)


@dataclass(frozen=True, slots=True)
class FactorCatalog:
    """An immutable proposal catalog; it has no production registry writer."""

    entries: tuple[FactorCatalogEntry, ...] = ()

    def propose(self, entry: FactorCatalogEntry) -> FactorCatalog:
        audit_factor_catalog_entry(entry)
        if any(item.factor_id == entry.factor_id and item.version == entry.version for item in self.entries):
            raise ValueError("duplicate factor catalog entry")
        return FactorCatalog(tuple(sorted((*self.entries, entry), key=lambda item: (item.factor_id, item.version))))

    def list(self) -> tuple[FactorCatalogEntry, ...]:
        return self.entries


__all__ = [
    "FactorCatalog",
    "FactorCatalogAudit",
    "FactorCatalogEntry",
    "HumanAdmissionRecord",
    "audit_factor_catalog_entry",
    "validate_factor_catalog_entry",
]
