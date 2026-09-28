"""Shared request/result contracts for source adapters.

The contract intentionally carries an authorization reference, never a token
or cookie.  Raw responses remain on disk in the snapshot manifest; they are
not embedded in ``SourceResult`` or reader-facing artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


class AdapterContractError(ValueError):
    """Raised when a source request violates the adapter contract."""


@dataclass(frozen=True)
class SourceRequest:
    source_id: str
    dataset: str
    instrument: str | None = None
    start: str | None = None
    end: str | None = None
    as_of: str | None = None
    adjustment: str | None = None
    authorization_ref: str | None = None
    access_method: str | None = None
    params: Mapping[str, Any] = field(default_factory=dict)
    requested_url: str | None = None

    def __post_init__(self):
        if not self.source_id or not self.dataset:
            raise AdapterContractError("source_id and dataset are required")
        if self.requested_url and not self.requested_url.startswith(("https://", "http://")):
            raise AdapterContractError("requested_url must be an absolute HTTP(S) URL")
        object.__setattr__(self, "params", dict(self.params or {}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "dataset": self.dataset,
            "instrument": self.instrument,
            "start": self.start,
            "end": self.end,
            "as_of": self.as_of,
            "adjustment": self.adjustment,
            "authorization_ref": self.authorization_ref,
            "access_method": self.access_method,
            "params": dict(self.params),
            "requested_url": self.requested_url,
        }


@dataclass
class SourceResult:
    raw_snapshot: dict[str, Any] | None
    observations: list[dict[str, Any]]
    provenance: dict[str, Any]
    quality_status: str
    limitations: list[str] = field(default_factory=list)
    source_capability: dict[str, Any] = field(default_factory=dict)
    freshness: dict[str, Any] = field(default_factory=dict)

    VALID_STATUSES = frozenset({"pass", "usable_with_warning", "degraded", "blocked"})

    def __post_init__(self):
        if self.quality_status not in self.VALID_STATUSES:
            raise AdapterContractError(f"invalid quality_status: {self.quality_status}")
        if not isinstance(self.observations, list):
            raise AdapterContractError("observations must be a list")
        if not isinstance(self.provenance, dict):
            raise AdapterContractError("provenance must be an object")

    def as_dict(self) -> dict[str, Any]:
        return {
            "raw_snapshot": self.raw_snapshot,
            "observations": self.observations,
            "provenance": self.provenance,
            "quality_status": self.quality_status,
            "limitations": list(self.limitations),
            "source_capability": dict(self.source_capability),
            "freshness": dict(self.freshness),
        }


class SourceAdapterProtocol(Protocol):
    source_id: str

    def fetch(self, request: SourceRequest) -> SourceResult:
        """Fetch one declared dataset slice and return auditable output."""


def source_result_from_legacy(payload: Mapping[str, Any], request: SourceRequest) -> SourceResult:
    """Convert an existing adapter payload without losing provenance."""
    snapshot = dict(payload.get("snapshot") or {})
    provenance = {
        "source_id": request.source_id,
        "dataset": request.dataset,
        "request": request.as_dict(),
        "snapshot_hash": snapshot.get("snapshot_hash"),
        "raw_file": snapshot.get("raw_file"),
        "access_method": snapshot.get("access_method"),
        "authorization_status": snapshot.get("authorization_status"),
        "point_in_time_status": snapshot.get("point_in_time_status"),
        "revision_status": snapshot.get("revision_status"),
    }
    limitations = []
    if provenance["point_in_time_status"] in {None, "not_available"}:
        limitations.append("historical availability timestamp is not verified")
    return SourceResult(snapshot, list(payload.get("observations") or []), provenance, "pass" if payload.get("observations") else "degraded", limitations)
