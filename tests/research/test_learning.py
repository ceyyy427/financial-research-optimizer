from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from finahinking.research.contracts import AgentReport, DecisionCard
from finahinking.research.learning import (
    LearningEntry,
    LearningStore,
    reconcile_learning,
    validate_learning_entry,
)


def entry(entry_id: str, as_of: str = "2026-09-30") -> LearningEntry:
    return LearningEntry(
        entry_id=entry_id,
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
        as_of=as_of,
        instrument_scope=("ETF:SPY",),
        lesson_type="validation",
        claim="fixture claim",
        evidence_refs=("artifact:quant-1",),
        source_run_id="run-learning",
        status="RECORDED",
    )


def test_inspect_asof_lessons_excludes_future_entries(tmp_path) -> None:
    store = LearningStore(tmp_path / "learning.jsonl", current_as_of="2026-10-01")
    store.record_evidence(entry("old", "2026-09-30"))
    store.record_evidence(entry("new", "2026-10-01"))
    assert [item.entry_id for item in store.inspect_asof_lessons("2026-09-30", ("ETF:SPY",))] == ["old"]


def test_duplicate_future_missing_evidence_and_secret_are_rejected(tmp_path) -> None:
    store = LearningStore(tmp_path / "learning.jsonl", current_as_of="2026-10-01")
    store.record_evidence(entry("one"))
    with pytest.raises(ValueError, match="duplicate"):
        store.record_evidence(entry("one"))
    with pytest.raises(ValueError, match="future"):
        store.record_evidence(entry("future", "2026-10-02"))
    with pytest.raises(ValueError, match="evidence"):
        validate_learning_entry(replace(entry("no-evidence"), evidence_refs=()))
    with pytest.raises(ValueError, match="secret"):
        validate_learning_entry(replace(entry("secret"), claim="api_key=secret"))


def test_store_is_append_only_and_digest_is_stable(tmp_path) -> None:
    path = tmp_path / "learning.jsonl"
    store = LearningStore(path, current_as_of="2026-10-01")
    store.record_evidence(entry("one"))
    first_digest = store.digest()
    second = LearningStore(path, current_as_of="2026-10-01")
    assert second.digest() == first_digest
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_reconcile_learning_only_emits_traceable_entries() -> None:
    reports = (
        AgentReport(role="technical", status="READY", claims=("supported",), evidence_refs=("artifact:t",)),
        AgentReport(role="news", status="FAILED", claims=("guess",), evidence_refs=()),
    )
    decision = DecisionCard(
        action="PAPER-ONLY",
        weights={"ETF:SPY": 1.0},
        rationale="fixture",
        evidence_refs=("artifact:t",),
        limitations=("offline",),
        eligible=True,
    )
    entries = reconcile_learning("run-learning", reports, decision, "2026-09-30")
    assert len(entries) == 1
    assert entries[0].source_run_id == "run-learning"
    assert entries[0].evidence_refs == ("artifact:t",)
