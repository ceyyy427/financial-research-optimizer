import sqlite3
from pathlib import Path

import pytest

from finahinking.p6_5.bls import BLSClient
from finahinking.p6_5.models import SourceRelease
from finahinking.p6_5.product import UnderstandingEngine
from finahinking.p6_5.repository import SQLiteUnderstandingRepository, apply_migration

FIXTURE = Path(__file__).parents[2] / "fixtures" / "p6_5" / "bls_cpi_2024_2025.json"


def test_cpi_journey_exposes_progressive_disclosure_and_learning(tmp_path) -> None:
    captured = BLSClient.replay(FIXTURE, capture_id="capture-journey", retrieved_at="2025-01-15T13:32:00Z", first_observed_at="2025-01-15T13:31:00Z")
    release = SourceRelease("release-journey", "bls", "bls-cpi-v2", "MACRO_RELEASE", "2024-12", "2025-01-15T08:30:00-05:00", "2025-01-15T13:30:00Z", "https://www.bls.gov/news.release/archives/cpi_01152025.htm")
    journey = UnderstandingEngine(artifact_root=tmp_path).run_cpi_journey("user-1", captured, release)
    assert journey.progressive_levels == ("EVENT", "MECHANISM", "EVIDENCE", "QUANT", "DEEP_KNOWLEDGE")
    assert journey.what_happened and journey.what_changed and journey.why_it_may_matter
    assert journey.what_we_know and journey.evidence_suggests and journey.plausible
    assert journey.unknown and journey.what_would_change_view and journey.what_to_watch_next
    assert journey.show_evidence and journey.knowledge_bridge and journey.quant_evidence
    assert journey.conclusion_ladder and journey.predict_reveal_explain
    assert journey.learning_card and journey.learning_state
    assert journey.quant_evidence["status"] == "SUCCEEDED"


def test_cpi_journey_can_persist_the_full_evidence_chain(tmp_path) -> None:
    captured = BLSClient.replay(FIXTURE, capture_id="capture-persist", retrieved_at="2025-01-15T13:32:00Z", first_observed_at="2025-01-15T13:31:00Z")
    release = SourceRelease("release-persist", "bls", "bls-cpi-v2", "MACRO_RELEASE", "2024-12", "2025-01-15T08:30:00-05:00", "2025-01-15T13:30:00Z", "https://www.bls.gov/news.release/archives/cpi_01152025.htm")
    connection = sqlite3.connect(":memory:")
    apply_migration(connection)
    repository = SQLiteUnderstandingRepository(connection, artifact_root=tmp_path / "db-artifacts")
    journey = UnderstandingEngine(artifact_root=tmp_path / "journey-artifacts", repository=repository).run_cpi_journey("user-1", captured, release)
    assert repository.show_evidence(journey.claims[0].claim_id)
    assert connection.execute("SELECT count(*) FROM p6_5_events").fetchone()[0] == 1
    assert connection.execute("SELECT count(*) FROM p6_5_learning_refs").fetchone()[0] == 1


def test_cpi_journey_rejects_a_release_outside_the_admitted_bls_boundary(tmp_path) -> None:
    captured = BLSClient.replay(FIXTURE, capture_id="capture-reject", retrieved_at="2025-01-15T13:32:00Z", first_observed_at="2025-01-15T13:31:00Z")
    release = SourceRelease("release-reject", "bls", "bls-cpi-v2", "MACRO_RELEASE", "2024-12", "2025-01-15T08:30:00-05:00", "2025-01-15T13:30:00Z", "https://untrusted.example/release")
    with pytest.raises(ValueError, match="admitted"):
        UnderstandingEngine(artifact_root=tmp_path).run_cpi_journey("user-1", captured, release)
