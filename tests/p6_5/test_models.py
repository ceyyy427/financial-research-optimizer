
import pytest

from finahinking.p6_5.claims import verified_claim
from finahinking.p6_5.models import (
    AdmissionDecision,
    ClaimType,
    Event,
    Evidence,
    EvidenceStatus,
    Observation,
    ObservationVersion,
    Source,
    SourceEndpoint,
    SourceRelease,
    SourceTier,
    TransportCapture,
)


def _source() -> Source:
    return Source(
        source_id="bls",
        name="Bureau of Labor Statistics CPI",
        publisher="U.S. Bureau of Labor Statistics",
        tier=SourceTier.TIER_0,
        canonical_url="https://www.bls.gov/cpi/",
        underlying_source="BLS Public Data API v2",
        owner="U.S. Department of Labor",
        access_method="official_api",
        usage_conditions="Public API; preserve attribution and current terms.",
        authentication="none_for_fixture",
        decision=AdmissionDecision.ADMIT_AUTHORITATIVE,
    )


def test_source_endpoint_release_and_capture_have_deterministic_identity() -> None:
    source = _source()
    endpoint = SourceEndpoint(
        endpoint_id="bls-cpi-v2",
        source_id=source.source_id,
        url="https://api.bls.gov/publicAPI/v2/timeseries/data/",
        method="POST",
        content_type="application/json",
        rate_limit="50 series per request; public quota applies",
        historical_support=True,
        revision_support="unknown_vintage",
        available_at_semantics="release_bound_plus_first_observed",
    )
    release = SourceRelease(
        release_id="bls-cpi-2024-12",
        source_id=source.source_id,
        endpoint_id=endpoint.endpoint_id,
        event_type="MACRO_RELEASE",
        reference_period="2024-12",
        published_at="2025-01-15T08:30:00-05:00",
        available_at="2025-01-15T08:30:00-05:00",
        release_url="https://www.bls.gov/news.release/archives/cpi_01152025.htm",
    )
    capture = TransportCapture(
        capture_id="capture-bls-2024-12",
        source_id=source.source_id,
        endpoint_id=endpoint.endpoint_id,
        request_fingerprint="a" * 64,
        retrieved_at="2025-01-15T08:31:00Z",
        first_observed_at="2025-01-15T08:31:00Z",
        status=200,
        content_type="application/json",
        relevant_headers={"content-type": "application/json"},
        raw_artifact_id="artifact-bls-2024-12",
        payload_hash="b" * 64,
        parser_version="bls-cpi-v1",
    )
    assert source.fingerprint == source.fingerprint
    assert endpoint.source_id == source.source_id
    assert release.endpoint_id == endpoint.endpoint_id
    assert capture.raw_artifact_id == "artifact-bls-2024-12"
    assert all(len(value) == 64 for value in (capture.request_fingerprint, capture.payload_hash))
    assert source.to_dict()["tier"] == "TIER_0"


def test_observation_revision_and_event_keep_temporal_fields_explicit() -> None:
    observation = Observation(
        observation_id="obs-bls-cuur-2024-12",
        source_id="bls",
        series_id="CUUR0000SA0",
        reference_period="2024-12",
        dimensions={"area": "U.S. city average", "item": "All items", "adjustment": "NSA"},
        versions=(
            ObservationVersion(
                version_id="obs-bls-cuur-2024-12-v1",
                value=315.605,
                unit="index",
                occurred_at="2024-12-01T00:00:00Z",
                effective_at="2024-12-01T00:00:00Z",
                published_at="2025-01-15T08:30:00-05:00",
                available_at="2025-01-15T13:31:00Z",
                retrieved_at="2025-01-15T13:32:00Z",
                capture_id="capture-bls-2024-12",
            ),
        ),
    )
    event = Event(
        event_id="event-bls-cpi-2024-12",
        event_type="MACRO_RELEASE",
        source_id="bls",
        reference_period="2024-12",
        published_at="2025-01-15T08:30:00-05:00",
        available_at="2025-01-15T13:31:00Z",
        observation_ids=(observation.observation_id,),
        evidence_ids=("capture-bls-2024-12",),
    )
    assert observation.latest.value == 315.605
    assert observation.latest.available_at != observation.latest.retrieved_at
    assert event.observation_ids == (observation.observation_id,)
    assert event.to_dict()["published_at"] == "2025-01-15T08:30:00-05:00"


def test_claim_evidence_requires_explicit_type_and_status() -> None:
    evidence = Evidence(
        evidence_id="evidence-bls-capture",
        evidence_type="OfficialDocument",
        source_id="bls",
        capture_id="capture-bls-2024-12",
        reference="https://www.bls.gov/news.release/archives/cpi_01152025.htm",
        status=EvidenceStatus.DIRECT_SOURCE,
        scope="December 2024 CPI release",
        limitations=("The API row does not itself carry a public-release timestamp.",),
    )
    claim = verified_claim(
        claim_id="claim-cpi-index",
        claim_type=ClaimType.FACT,
        text="The CPI-U all-items index was 315.605 for December 2024.",
        evidence=(Evidence(
            evidence_id=evidence.evidence_id,
            evidence_type=evidence.evidence_type,
            source_id=evidence.source_id,
            capture_id=evidence.capture_id,
            reference=evidence.reference,
            status=evidence.status,
            scope=evidence.scope,
            limitations=evidence.limitations,
            source_fingerprint="c" * 64,
        ),),
        evidence_status=EvidenceStatus.DIRECT_SOURCE,
        source_fingerprint="c" * 64,
    )
    assert claim.claim_type is ClaimType.FACT
    assert claim.evidence_ids == (evidence.evidence_id,)
    assert evidence.to_dict()["status"] == "DIRECT_SOURCE"


def test_invalid_fingerprint_and_temporal_order_are_rejected() -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        Source(
            source_id="bad",
            name="Bad",
            publisher="Bad",
            tier=SourceTier.TIER_0,
            canonical_url="https://example.com",
            underlying_source="bad",
            owner="bad",
            access_method="api",
            usage_conditions="bad",
            authentication="none",
            decision=AdmissionDecision.ADMIT_AUTHORITATIVE,
            source_fingerprint="not-a-hash",
        )
    with pytest.raises(ValueError, match="temporal"):
        ObservationVersion(
            version_id="obs-v1",
            value=1.0,
            unit="index",
            occurred_at="2025-01-01T00:00:00Z",
            effective_at="2025-01-01T00:00:00Z",
            published_at="2024-12-31T00:00:00Z",
            available_at="2025-01-02T00:00:00Z",
            retrieved_at="2025-01-01T00:00:00Z",
            capture_id="capture",
        )

    with pytest.raises(ValueError, match="temporal"):
        SourceRelease(
            release_id="release-bad",
            source_id="bls",
            endpoint_id="bls-cpi-v2",
            event_type="MACRO_RELEASE",
            reference_period="2024-12",
            published_at="2025-01-15T13:30:00Z",
            available_at="2025-01-15T13:29:00Z",
            release_url="https://www.bls.gov/cpi/",
        )
