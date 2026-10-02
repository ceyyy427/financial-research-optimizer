import pytest

from finahinking.p6_5.admission import (
    SourceAdmissionRecord,
    SourceRegistry,
    default_source_registry,
)
from finahinking.p6_5.models import AdmissionDecision, ObservationVersion, SourceTier
from finahinking.p6_5.temporal import record_conflict, record_revision, validate_temporal_order


def test_source_registry_keeps_tier_and_decision_separate() -> None:
    registry = SourceRegistry()
    record = SourceAdmissionRecord(
        source_id="akshare-cpi",
        publisher="AKShare contributors",
        owner="upstream sources vary",
        tier=SourceTier.TIER_2,
        decision=AdmissionDecision.DISCOVERY_ONLY,
        endpoint="https://example.invalid/akshare",
        authentication="none",
        usage_conditions="Review endpoint terms before use",
        historical_support="unknown",
        revision_behavior="unknown",
        available_at_semantics="not established",
        production_suitable=False,
        rationale="Discovery only; underlying source identity must be admitted separately.",
    )
    registry.admit(record)
    assert registry.get("akshare-cpi").decision is AdmissionDecision.DISCOVERY_ONLY
    assert registry.authoritative_sources() == ()


def test_default_registry_makes_discovery_sources_non_authoritative() -> None:
    registry = default_source_registry()
    assert [item.source_id for item in registry.authoritative_sources()] == ["bls"]
    assert registry.get("a-stock-data").decision is AdmissionDecision.DISCOVERY_ONLY
    assert registry.get("akshare").decision is AdmissionDecision.DISCOVERY_ONLY
    assert registry.get("tushare-pro").decision is AdmissionDecision.DEFER


def test_revision_preserves_versions_and_conflict_is_visible() -> None:
    first = ObservationVersion(
        version_id="obs-v1",
        value=100.0,
        unit="index",
        occurred_at="2024-01-01T00:00:00Z",
        effective_at="2024-01-01T00:00:00Z",
        published_at="2024-02-01T00:00:00Z",
        available_at="2024-02-01T00:01:00Z",
        retrieved_at="2024-02-01T00:01:00Z",
        capture_id="capture-1",
    )
    second = ObservationVersion(
        version_id="obs-v2",
        value=101.0,
        unit="index",
        occurred_at="2024-01-01T00:00:00Z",
        effective_at="2024-01-01T00:00:00Z",
        published_at="2024-03-01T00:00:00Z",
        available_at="2024-03-01T00:01:00Z",
        retrieved_at="2024-03-01T00:01:00Z",
        capture_id="capture-2",
    )
    revised = record_revision(first, second)
    assert revised.supersedes_version_id == first.version_id
    conflict = record_conflict("obs-1", first, second, reason="same logical key, different value")
    assert conflict.observation_id == "obs-1"
    assert conflict.value_a != conflict.value_b


def test_latest_version_compares_instants_not_timestamp_strings() -> None:
    earlier_text = ObservationVersion(
        version_id="obs-offset-a", value=100.0, unit="index",
        occurred_at="2024-01-01T00:00:00Z", effective_at="2024-01-01T00:00:00Z",
        published_at="2024-02-01T00:00:00Z", available_at="2024-02-01T00:01:00Z",
        retrieved_at="2024-02-01T02:00:00+01:00", capture_id="capture-a",
    )
    later_instant = ObservationVersion(
        version_id="obs-offset-b", value=101.0, unit="index",
        occurred_at="2024-01-01T00:00:00Z", effective_at="2024-01-01T00:00:00Z",
        published_at="2024-02-01T00:00:00Z", available_at="2024-02-01T00:01:00Z",
        retrieved_at="2024-02-01T01:30:00Z", capture_id="capture-b",
    )
    from finahinking.p6_5.models import Observation

    observation = Observation("obs-offset", "bls", "CUUR0000SA0", "2024-01", {}, (earlier_text, later_instant))
    assert observation.latest.version_id == "obs-offset-b"


def test_available_time_requires_a_publication_bound() -> None:
    assert validate_temporal_order(
        occurred_at="2024-01-01T00:00:00Z",
        effective_at="2024-01-01T00:00:00Z",
        published_at="2024-02-01T00:00:00Z",
        available_at="2024-02-01T00:01:00Z",
        retrieved_at="2024-02-01T00:02:00Z",
    ) is True
    with pytest.raises(ValueError, match="available_at"):
        validate_temporal_order(
            occurred_at="2024-01-01T00:00:00Z",
            effective_at="2024-01-01T00:00:00Z",
            published_at="2024-02-01T00:00:00Z",
            available_at="2024-01-31T23:59:00Z",
            retrieved_at="2024-02-01T00:02:00Z",
        )
