from __future__ import annotations

import pytest

from finahinking.research.learning_manager import (
    AdmissionDecision,
    LearningAdmissionRecord,
    LearningManager,
    LearningUpdateStatus,
)
from finahinking.research.paper_trader import PaperLedger, PaperLedgerEntry
from finahinking.research.run_store import ResearchRunStore
from finahinking.research.settlement import SettlementEvent


def event(**overrides: object) -> SettlementEvent:
    values: dict[str, object] = {
        "run_id": "run-settlement",
        "ledger": PaperLedger(
            entries=(PaperLedgerEntry(timestamp="2026-10-01", event="paper_fill", instrument="ETF:SPY"),),
            snapshot_digest="dataset-v1",
        ),
        "as_of": "2026-10-02",
        "realized_outcomes": {
            "factor_weights": {"value": 0.6, "quality": 0.4},
            "risk_rules": {"max_drawdown": 0.2},
            "registry": {"candidate": "factor:value:v2"},
        },
        "costs": {"fees": 0.01},
        "dataset_digest": "dataset-v1",
    }
    values.update(overrides)
    return SettlementEvent(**values)


def test_no_settlement_returns_no_learning_update() -> None:
    result = LearningManager().propose_update(None, ())
    assert result.status is LearningUpdateStatus.NO_LEARNING_UPDATE
    assert result.proposal_digest


def test_settlement_produces_proposal_without_mutating_manager_state() -> None:
    manager = LearningManager()
    result = manager.propose_update(event(), ())
    assert result.status is LearningUpdateStatus.PROPOSAL_READY
    assert result.factor_weight_updates == {"quality": 0.4, "value": 0.6}
    assert result.risk_rule_updates == {"max_drawdown": 0.2}
    assert result.registry_updates == {"candidate": "factor:value:v2"}
    assert result.admitted is False
    assert manager.admitted_updates == ()


def test_repeat_settlement_is_idempotent_and_digest_stable() -> None:
    manager = LearningManager()
    first = manager.propose_update(event(), ())
    second = manager.propose_update(event(), ())
    assert second == first
    assert second.proposal_digest == first.proposal_digest


def test_admission_requires_explicit_typed_record_and_matching_proposal() -> None:
    manager = LearningManager()
    proposal = manager.propose_update(event(), ())
    record = LearningAdmissionRecord(
        admission_id="admission-1",
        proposal_digest=proposal.proposal_digest,
        admitted_by="research-owner",
        decision=AdmissionDecision.APPROVED,
        as_of="2026-10-03",
    )
    admitted = manager.admit_update(proposal, record)
    assert admitted.proposal == proposal
    assert admitted.admission == record
    assert manager.admitted_updates == (admitted,)
    with pytest.raises((TypeError, ValueError), match="admission"):
        manager.admit_update(proposal, {"decision": "APPROVED"})


def test_admission_rejects_mismatch_and_no_update_is_written_for_rejected_proposal() -> None:
    manager = LearningManager()
    proposal = manager.propose_update(event(), ())
    record = LearningAdmissionRecord(
        admission_id="admission-2",
        proposal_digest="proposal-other",
        admitted_by="research-owner",
        decision=AdmissionDecision.APPROVED,
        as_of="2026-10-03",
    )
    with pytest.raises(ValueError, match="digest"):
        manager.admit_update(proposal, record)
    rejected = LearningAdmissionRecord(
        admission_id="admission-3",
        proposal_digest=proposal.proposal_digest,
        admitted_by="research-owner",
        decision=AdmissionDecision.REJECTED,
        as_of="2026-10-03",
    )
    with pytest.raises(ValueError, match="approved"):
        manager.admit_update(proposal, rejected)


def test_future_or_duplicate_history_fails_closed() -> None:
    manager = LearningManager()
    first = event()
    future = event(as_of="2026-10-04")
    with pytest.raises(ValueError, match="future"):
        manager.propose_update(first, (future,))
    with pytest.raises(ValueError, match="duplicate"):
        manager.propose_update(first, (first, first))


def test_learning_proposal_can_be_checkpointed_without_sensitive_payload(tmp_path) -> None:
    manager = LearningManager()
    proposal = manager.propose_update(event(), ())
    store = ResearchRunStore(tmp_path)
    path = store.save_learning_proposal("run-settlement", proposal)
    assert path.name == "run-settlement.learning.json"
    assert store.load_learning_proposal("run-settlement") == proposal
    assert store.learning_reference("run-settlement") == "learning:run-settlement"
