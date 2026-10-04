from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from finahinking.p6_5.bls import BLSClient
from finahinking.p6_5.models import SourceRelease
from finahinking.p6_5.product import UnderstandingEngine
from finahinking.p7.event_learning import EventLearningAdapter
from finahinking.p7.models import Principal
from finahinking.p7.repository import SQLiteP7Repository, apply_p7_migration

FIXTURE = Path(__file__).parents[2] / "fixtures" / "p6_5" / "bls_cpi_2024_2025.json"


def _journey(tmp_path: Path):
    captured = BLSClient.replay(
        FIXTURE,
        capture_id="capture-p7-real-event",
        retrieved_at="2025-01-15T13:32:00Z",
        first_observed_at="2025-01-15T13:31:00Z",
    )
    release = SourceRelease(
        "release-p7-real-event",
        "bls",
        "bls-cpi-v2",
        "MACRO_RELEASE",
        "2024-12",
        "2025-01-15T08:30:00-05:00",
        "2025-01-15T13:30:00Z",
        "https://www.bls.gov/news.release/archives/cpi_01152025.htm",
    )
    return UnderstandingEngine(artifact_root=tmp_path / "p6-5").run_cpi_journey("alice", captured, release)


def _repository() -> SQLiteP7Repository:
    connection = sqlite3.connect(":memory:")
    apply_p7_migration(connection)
    repository = SQLiteP7Repository(connection)
    repository.create_principal(Principal("alice", "Alice"))
    repository.create_principal(Principal("bob", "Bob"))
    repository.create_session("alice-session", "alice")
    repository.create_session("bob-session", "bob")
    return repository


def test_real_bls_journey_persists_claims_evidence_mastery_timeline_and_projection(tmp_path: Path) -> None:
    journey = _journey(tmp_path)
    repository = _repository()
    outcomes = {concept.concept_id: "correct" for concept in journey.knowledge_bridge.concepts}

    result = EventLearningAdapter(repository).ingest_journey(
        "alice-session",
        journey,
        mastery_outcomes=outcomes,
        projection_id="projection-cpi-real-event",
        visibility="PUBLIC",
        consent=True,
    )

    exported = repository.export_personal("alice-session")
    nodes = {item["node_id"]: item for item in exported["nodes"]}
    assert result.event_node_id in nodes
    assert len([node for node in nodes.values() if node["node_type"] == "claim"]) == len(journey.claims)
    assert len([node for node in nodes.values() if node["node_type"] == "evidence"]) == len(journey.evidence)
    assert repository.get_mastery_state("alice-session", "concept:concept-cpi").state == "EXPOSED"
    assert any(item["source_id"] == journey.event.event_id for item in exported["history"])

    projection = repository.get_public_projection("projection-cpi-real-event")
    assert projection.payload["event_type"] == "MACRO_RELEASE"
    assert "claims" not in projection.payload
    assert "source_fingerprint" not in projection.payload


def test_real_journey_cannot_be_imported_into_another_principal_graph(tmp_path: Path) -> None:
    journey = _journey(tmp_path)
    repository = _repository()
    with pytest.raises(PermissionError, match="user"):
        EventLearningAdapter(repository).ingest_journey("bob-session", journey)
    assert repository.export_personal("bob-session")["nodes"] == []
