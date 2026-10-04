"""Source admission and tier registry for P6.5."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import AdmissionDecision, SourceTier


@dataclass(frozen=True)
class SourceAdmissionRecord:
    source_id: str
    publisher: str
    owner: str
    tier: SourceTier
    decision: AdmissionDecision
    endpoint: str
    authentication: str
    usage_conditions: str
    historical_support: str
    revision_behavior: str
    available_at_semantics: str
    production_suitable: bool
    rationale: str
    checked_at: str | None = None

    def __post_init__(self) -> None:
        from .models import _id, _text

        object.__setattr__(self, "source_id", _id(self.source_id, "source_id"))
        for name in ("publisher", "owner", "endpoint", "authentication", "usage_conditions", "historical_support", "revision_behavior", "available_at_semantics", "rationale"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.tier, SourceTier):
            object.__setattr__(self, "tier", SourceTier(self.tier))
        if not isinstance(self.decision, AdmissionDecision):
            object.__setattr__(self, "decision", AdmissionDecision(self.decision))
        if not isinstance(self.production_suitable, bool):
            raise TypeError("production_suitable must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "publisher": self.publisher, "owner": self.owner, "tier": self.tier.value, "decision": self.decision.value, "endpoint": self.endpoint, "authentication": self.authentication, "usage_conditions": self.usage_conditions, "historical_support": self.historical_support, "revision_behavior": self.revision_behavior, "available_at_semantics": self.available_at_semantics, "production_suitable": self.production_suitable, "rationale": self.rationale, "checked_at": self.checked_at}


class SourceRegistry:
    def __init__(self) -> None:
        self._records: dict[str, SourceAdmissionRecord] = {}

    def admit(self, record: SourceAdmissionRecord) -> SourceAdmissionRecord:
        if not isinstance(record, SourceAdmissionRecord):
            raise TypeError("record must be SourceAdmissionRecord")
        previous = self._records.get(record.source_id)
        if previous is not None and previous != record:
            raise ValueError("source admission is immutable for an existing source id")
        self._records[record.source_id] = record
        return record

    def get(self, source_id: str) -> SourceAdmissionRecord:
        try:
            return self._records[source_id]
        except KeyError as exc:
            raise KeyError(f"source admission not found: {source_id}") from exc

    def authoritative_sources(self) -> tuple[SourceAdmissionRecord, ...]:
        return tuple(record for record in self._records.values() if record.decision is AdmissionDecision.ADMIT_AUTHORITATIVE)

    def all(self) -> tuple[SourceAdmissionRecord, ...]:
        return tuple(self._records.values())


def default_source_registry() -> SourceRegistry:
    """Return the reviewed P6.5 source policy without performing network I/O."""

    registry = SourceRegistry()
    registry.admit(
        SourceAdmissionRecord(
            source_id="bls",
            publisher="U.S. Bureau of Labor Statistics",
            owner="U.S. Department of Labor",
            tier=SourceTier.TIER_0,
            decision=AdmissionDecision.ADMIT_AUTHORITATIVE,
            endpoint="https://api.bls.gov/publicAPI/v2/timeseries/data/",
            authentication="none for the bounded public endpoint",
            usage_conditions="Follow current BLS API terms and preserve attribution.",
            historical_support="bounded historical series query",
            revision_behavior="vintage identifier not exposed; preserve captures and mark unresolved",
            available_at_semantics="official release bound plus first observed API time",
            production_suitable=True,
            rationale="Original official publisher with a documented CPI release and deterministic capture path.",
        )
    )
    registry.admit(
        SourceAdmissionRecord(
            source_id="a-stock-data",
            publisher="Repository contributors",
            owner="varies by discovered underlying source",
            tier=SourceTier.TIER_2,
            decision=AdmissionDecision.DISCOVERY_ONLY,
            endpoint="repository-specific discovery skill",
            authentication="varies",
            usage_conditions="Review repository license and each underlying source before use.",
            historical_support="discovery-dependent",
            revision_behavior="unknown until underlying source is admitted",
            available_at_semantics="not established",
            production_suitable=False,
            rationale="Useful for endpoint discovery; its returned values are not authoritative evidence.",
        )
    )
    registry.admit(
        SourceAdmissionRecord(
            source_id="akshare",
            publisher="AKShare contributors",
            owner="varies by endpoint and upstream source",
            tier=SourceTier.TIER_2,
            decision=AdmissionDecision.DISCOVERY_ONLY,
            endpoint="endpoint-specific adapter",
            authentication="varies",
            usage_conditions="Review endpoint terms, license, and upstream attribution.",
            historical_support="endpoint-specific",
            revision_behavior="must be established per upstream source",
            available_at_semantics="not established globally",
            production_suitable=False,
            rationale="Adapter candidate for exploration and cross-checking, not an automatic authority.",
        )
    )
    registry.admit(
        SourceAdmissionRecord(
            source_id="tushare-pro",
            publisher="Tushare Pro",
            owner="Tushare service operator and underlying providers",
            tier=SourceTier.TIER_1,
            decision=AdmissionDecision.DEFER,
            endpoint="provider account API",
            authentication="token required; never hardcode",
            usage_conditions="Account, quota, and commercial terms require review.",
            historical_support="candidate; endpoint-specific",
            revision_behavior="must establish PIT and revision behavior before admission",
            available_at_semantics="not established for this phase",
            production_suitable=False,
            rationale="Promising future provider candidate, intentionally deferred from the first CPI slice.",
        )
    )
    return registry


__all__ = ["SourceAdmissionRecord", "SourceRegistry", "default_source_registry"]
