import hashlib
import sqlite3

import pytest

from finahinking.p6_5.claims import verified_claim
from finahinking.p6_5.models import (
    AdmissionDecision,
    ClaimEvidenceLink,
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
from finahinking.p6_5.repository import SQLiteUnderstandingRepository, apply_migration


def _repo(tmp_path):
    connection = sqlite3.connect(":memory:")
    apply_migration(connection, dialect="sqlite")
    return SQLiteUnderstandingRepository(connection, artifact_root=tmp_path)


def _records():
    source = Source("bls", "BLS CPI", "BLS", SourceTier.TIER_0, "https://www.bls.gov/cpi/", "BLS API", "U.S. DOL", "official_api", "public", "none", AdmissionDecision.ADMIT_AUTHORITATIVE)
    endpoint = SourceEndpoint("bls-cpi-v2", "bls", "https://api.bls.gov/publicAPI/v2/timeseries/data/", "POST", "application/json", "public quota", True, "unknown_vintage", "release_plus_first_observed")
    release = SourceRelease("release-2024-12", "bls", "bls-cpi-v2", "MACRO_RELEASE", "2024-12", "2025-01-15T08:30:00-05:00", "2025-01-15T13:30:00Z", "https://www.bls.gov/news.release/archives/cpi_01152025.htm")
    raw_payload = '{"status":"REQUEST_SUCCEEDED"}'
    capture = TransportCapture("capture-1", "bls", "bls-cpi-v2", "a" * 64, "2025-01-15T13:32:00Z", "2025-01-15T13:31:00Z", 200, "application/json", {}, "artifact-capture-1", hashlib.sha256(raw_payload.encode()).hexdigest(), "bls-v1", raw_payload)
    version = ObservationVersion("obs-v1", 315.605, "index", "2024-12-01T00:00:00Z", "2024-12-01T00:00:00Z", "2025-01-15T08:30:00-05:00", "2025-01-15T13:31:00Z", "2025-01-15T13:32:00Z", "capture-1")
    observation = Observation("obs-1", "bls", "CUUR0000SA0", "2024-12", {"item": "All items"}, (version,))
    evidence = Evidence("evidence-1", "OfficialDocument", "bls", "capture-1", "https://www.bls.gov/news.release/archives/cpi_01152025.htm", EvidenceStatus.DIRECT_SOURCE, "December 2024 CPI", ("API row lacks release timestamp.",), source.fingerprint)
    claim = verified_claim(
        claim_id="claim-1",
        claim_type=ClaimType.FACT,
        text="CPI was 315.605.",
        evidence=(evidence,),
        evidence_status=EvidenceStatus.DIRECT_SOURCE,
        source_fingerprint=source.fingerprint,
    )
    return source, endpoint, release, capture, observation, evidence, claim


def test_migration_enforces_foreign_keys_and_show_evidence(tmp_path) -> None:
    repo = _repo(tmp_path)
    source, endpoint, release, capture, observation, evidence, claim = _records()
    repo.save_source(source)
    repo.save_endpoint(endpoint)
    repo.save_release(release)
    repo.save_capture(capture)
    repo.save_observation(observation)
    repo.save_evidence(evidence)
    repo.save_claim(claim)
    repo.link_claim_evidence(ClaimEvidenceLink("claim-1", "evidence-1", EvidenceStatus.DIRECT_SOURCE, "the release directly reports the index"))
    shown = repo.show_evidence("claim-1")
    assert shown[0]["claim_id"] == "claim-1"
    assert shown[0]["publisher"] == "BLS"
    assert shown[0]["capture_id"] == "capture-1"
    assert (tmp_path / "artifact-capture-1.bin").read_text() == '{"status":"REQUEST_SUCCEEDED"}'


def test_parameterized_lookup_does_not_execute_sql(tmp_path) -> None:
    repo = _repo(tmp_path)
    assert repo.show_evidence("claim-1' OR 1=1; DROP TABLE p6_5_sources; --") == []
    repo.connection.execute("SELECT 1 FROM p6_5_sources")


def test_duplicate_logical_observation_and_orphan_claim_are_rejected(tmp_path) -> None:
    repo = _repo(tmp_path)
    source, endpoint, release, capture, observation, _evidence, claim = _records()
    repo.save_source(source)
    repo.save_endpoint(endpoint)
    repo.save_release(release)
    repo.save_capture(capture)
    repo.save_observation(observation)
    with pytest.raises(ValueError, match="observation"):
        repo.save_observation(observation)
    with pytest.raises(ValueError, match="foreign key"):
        repo.save_claim(claim)


def test_event_evidence_foreign_key_and_observation_save_are_atomic(tmp_path) -> None:
    repo = _repo(tmp_path)
    source, endpoint, release, capture, _observation, evidence, _claim = _records()
    repo.save_source(source)
    repo.save_endpoint(endpoint)
    repo.save_release(release)
    repo.save_capture(capture)
    repo.save_evidence(evidence)
    bad_event = Event(
        "event-1", "MACRO_RELEASE", "bls", "2024-12", release.published_at, release.available_at,
        ("missing-observation",), (evidence.evidence_id,),
    )
    with pytest.raises(ValueError, match="event link"):
        repo.save_event(bad_event)
    assert repo.connection.execute("SELECT 1 FROM p6_5_events WHERE event_id = 'event-1'").fetchone() is None


def test_capture_failure_rolls_back_artifact_row_and_file(tmp_path) -> None:
    repo = _repo(tmp_path)
    source, endpoint, release, capture, _observation, _evidence, _claim = _records()
    repo.save_source(source)
    repo.save_endpoint(endpoint)
    repo.save_release(release)
    repo.save_capture(capture)
    duplicate_request = TransportCapture(
        "capture-duplicate",
        "bls",
        "bls-cpi-v2",
        capture.request_fingerprint,
        capture.retrieved_at,
        capture.first_observed_at,
        capture.status,
        capture.content_type,
        capture.relevant_headers,
        "artifact-capture-2",
        capture.payload_hash,
        capture.parser_version,
        capture.raw_payload,
    )
    with pytest.raises(ValueError, match="capture"):
        repo.save_capture(duplicate_request)
    assert repo.connection.execute("SELECT 1 FROM p6_5_artifacts WHERE artifact_id = 'artifact-capture-2'").fetchone() is None
    assert not (tmp_path / "artifact-capture-2.bin").exists()
