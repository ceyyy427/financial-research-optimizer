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
_UNSAFE_FIELD = re.compile(r"(?:future|lookahead|target|label|forward_return)", re.IGNORECASE)
_MISSING_LICENSES = frozenset({"", "UNKNOWN", "MISSING", "UNVERIFIED", "PENDING", "NOT_REVIEWED"})
_KNOWN_STATUSES = frozenset({"PROPOSED", "BLOCKED", "REVIEW", "ADMITTED", "RETIRED"})


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
class FactorCatalogEntry:
    factor_id: str
    version: str
    source_ids: tuple[str, ...]
    license_status: str
    pit_semantics: str
    required_fields: tuple[str, ...]
    research_fingerprint: str
    status: str = "PROPOSED"

    def __post_init__(self) -> None:
        for name in ("factor_id", "version", "pit_semantics", "research_fingerprint", "status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
            object.__setattr__(self, name, value.strip())
        source_ids = tuple(item.strip() for item in self.source_ids if isinstance(item, str) and item.strip())
        fields = tuple(item.strip() for item in self.required_fields if isinstance(item, str) and item.strip())
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "required_fields", fields)
        object.__setattr__(self, "license_status", "" if self.license_status is None else str(self.license_status).strip())
        if self.status not in _KNOWN_STATUSES:
            raise ValueError("status is not a recognized catalog status")
        if self.research_fingerprint and not _HEX64.fullmatch(self.research_fingerprint):
            raise ValueError("research_fingerprint must be a SHA-256 hex digest")

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
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "fingerprint": self.fingerprint}


def audit_factor_catalog_entry(entry: FactorCatalogEntry) -> FactorCatalogAudit:
    """Fail closed when source, license, PIT or field metadata is incomplete."""

    if not isinstance(entry, FactorCatalogEntry):
        raise TypeError("entry must be a FactorCatalogEntry")
    if not entry.source_ids:
        raise ValueError("source metadata is required")
    license_status = entry.license_status.upper().replace("-", "_").replace(" ", "_")
    if license_status in _MISSING_LICENSES:
        raise ValueError("source license is missing or not approved")
    pit = entry.pit_semantics.casefold()
    if "unknown" in pit or "unavailable" in pit or not any(token in pit for token in ("pit", "point-in-time", "point_in_time", "t+1", "available_at")):
        raise ValueError("PIT semantics are missing or unknown")
    if not entry.required_fields:
        raise ValueError("required source fields are missing")
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
    "audit_factor_catalog_entry",
    "validate_factor_catalog_entry",
]
