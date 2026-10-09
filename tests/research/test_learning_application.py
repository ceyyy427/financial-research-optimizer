from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import pytest

from finahinking.research.contracts import ResearchPlan, ResearchRequest, stable_digest
from finahinking.research.learning_manager import (
    AdmissionDecision,
    LearningAdmissionRecord,
    LearningApplyPreview,
    LearningManager,
    LearningProposalStore,
    VersionedResearchPolicy,
)
from finahinking.research.paper_trader import PaperLedger, PaperLedgerEntry
from finahinking.research.settlement import SettlementEvent


def settlement() -> SettlementEvent:
    return SettlementEvent(
        run_id="learning-run",
        ledger=PaperLedger(
            entries=(PaperLedgerEntry(timestamp="2026-10-01", event="paper_fill", instrument="ETF:SPY"),),
            snapshot_digest="dataset-v2",
        ),
        as_of="2026-10-02",
        realized_outcomes={
            "factor_weights": {"value": 0.7},
            "risk_rules": {"max_drawdown": 0.18},
            "registry": {"candidate": "factor:value:v2"},
        },
        costs={"fees": 0.01},
        dataset_digest="dataset-v2",
    )


def approved(manager: LearningManager, proposal):
    return manager.admit_update(
        proposal,
        LearningAdmissionRecord(
            admission_id="admission-1",
            proposal_digest=proposal.proposal_digest,
            admitted_by="research-owner",
            decision=AdmissionDecision.APPROVED,
            as_of="2026-10-03",
        ),
    )


def test_proposal_carries_settlement_asof_ledger_and_dataset_digests() -> None:
    proposal = LearningManager().propose_update(settlement())
    assert proposal.as_of == date(2026, 10, 2)
    assert proposal.ledger_digest == settlement().ledger_fingerprint
    assert proposal.dataset_digest == "dataset-v2"


def test_store_persists_proposal_admission_and_preview_idempotently(tmp_path) -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    admission = approved(manager, proposal).admission
    preview = manager.preview_apply(proposal, {"version": 1, "factor_weights": {"value": 0.5}})

    store = LearningProposalStore(tmp_path / "learning")
    saved = store.save(proposal, admission=admission, preview=preview)
    assert saved.proposal == proposal
    loaded = LearningProposalStore(tmp_path / "learning").get(proposal.proposal_digest)
    assert loaded is not None
    assert loaded.proposal == proposal
    assert loaded.admission == admission
    assert loaded.preview == preview
    assert LearningProposalStore(tmp_path / "learning").list()[0].proposal_digest == proposal.proposal_digest
    assert store.save(proposal, admission=admission, preview=preview) == saved


def test_store_retry_without_enrichment_preserves_existing_admission_and_preview(tmp_path) -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    admission = approved(manager, proposal).admission
    preview = manager.preview_apply(proposal, {"version": 1, "factor_weights": {"value": 0.5}})
    store = LearningProposalStore(tmp_path / "learning")

    store.save(proposal)
    enriched = store.save(proposal, admission=admission)
    assert store.save(proposal) == enriched
    fully_enriched = store.save(proposal, preview=preview)
    retried = store.save(proposal)

    assert retried == fully_enriched
    assert retried.admission == admission
    assert retried.preview == preview


def test_store_rejects_duplicate_digest_with_different_payload(tmp_path) -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    store = LearningProposalStore(tmp_path / "learning")
    store.save(proposal)
    # A different typed proposal cannot overwrite the original digest record.
    with pytest.raises(ValueError, match="digest"):
        store.save(proposal.__class__(
            status=proposal.status,
            settlement_digest=proposal.settlement_digest,
            as_of=proposal.as_of,
            ledger_digest=proposal.ledger_digest,
            dataset_digest=proposal.dataset_digest,
            factor_weight_updates={"value": 0.8},
            risk_rule_updates=proposal.risk_rule_updates,
            registry_updates=proposal.registry_updates,
            evidence_refs=proposal.evidence_refs,
        ))


def test_rejected_admission_cannot_preview_or_apply() -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    rejected = LearningAdmissionRecord(
        admission_id="admission-rejected",
        proposal_digest=proposal.proposal_digest,
        admitted_by="research-owner",
        decision=AdmissionDecision.REJECTED,
        as_of="2026-10-03",
    )
    with pytest.raises(ValueError, match="approved"):
        manager.admit_update(proposal, rejected)
    with pytest.raises(ValueError, match="approved"):
        manager.preview_apply(proposal, {})


def test_proposal_recomputes_and_rejects_a_forged_supplied_digest() -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())

    with pytest.raises(ValueError, match="digest"):
        replace(proposal, factor_weight_updates={"forged": 1.0}, proposal_digest=proposal.proposal_digest)


def test_preview_and_policy_are_deeply_immutable_and_fingerprint_stable() -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    admitted = approved(manager, proposal)
    baseline = {"version": 1, "factor_weights": {"nested": {"value": 0.5}}}

    preview = manager.preview_apply(admitted, baseline)
    policy = manager.apply(admitted, baseline)
    with pytest.raises(TypeError):
        preview.factor_weights["new"] = 1.0  # type: ignore[index]
    with pytest.raises(TypeError):
        preview.factor_weights["nested"]["value"] = 0.9  # type: ignore[index]
    with pytest.raises(TypeError):
        policy.factor_weights["new"] = 1.0  # type: ignore[index]
    with pytest.raises(TypeError):
        policy.factor_weights["nested"]["value"] = 0.9  # type: ignore[index]

    assert preview.policy_fingerprint == manager.preview_apply(admitted, baseline).policy_fingerprint
    assert policy == manager.apply(admitted, baseline)


@pytest.mark.parametrize(
    ("factory", "value"),
    [
        (lambda proposal: proposal.__class__(
            status=proposal.status,
            settlement_digest=proposal.settlement_digest,
            as_of=proposal.as_of,
            factor_weight_updates={"note": "/Users/mac/private/report"},
            risk_rule_updates=proposal.risk_rule_updates,
            registry_updates=proposal.registry_updates,
            evidence_refs=proposal.evidence_refs,
        ), "path"),
        (lambda proposal: proposal.__class__(
            status=proposal.status,
            settlement_digest=proposal.settlement_digest,
            as_of=proposal.as_of,
            factor_weight_updates=proposal.factor_weight_updates,
            risk_rule_updates=proposal.risk_rule_updates,
            registry_updates=proposal.registry_updates,
            evidence_refs=("/Users/mac/private/report",),
        ), "evidence"),
    ],
)
def test_learning_proposal_rejects_unsafe_persisted_text(factory, value: str) -> None:
    proposal = LearningManager().propose_update(settlement())
    with pytest.raises(ValueError, match="sensitive|unsafe|secret|path"):
        factory(proposal)


def test_learning_admission_rationale_and_preview_limitations_reject_unsafe_text() -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    with pytest.raises(ValueError, match="sensitive|unsafe"):
        LearningAdmissionRecord(
            admission_id="admission-unsafe",
            proposal_digest=proposal.proposal_digest,
            admitted_by="research-owner",
            decision=AdmissionDecision.APPROVED,
            as_of="2026-10-03",
            rationale="see /Users/mac/private/report",
        )
    with pytest.raises(ValueError, match="sensitive|unsafe"):
        LearningApplyPreview(
            proposal_digest=proposal.proposal_digest,
            baseline_fingerprint="baseline-1",
            next_version=1,
            limitations=("https://secret.example/report",),
        )


def test_store_rejects_unknown_fields_at_every_persisted_envelope_level(tmp_path) -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    store = LearningProposalStore(tmp_path / "learning")
    path = store._path(proposal.proposal_digest)

    store.save(proposal)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["unexpected"] = "artifact:unknown"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        store.get(proposal.proposal_digest)

    path.unlink()
    store.save(proposal)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["record"]["proposal"]["unexpected"] = "artifact:unknown"
    payload["record_digest"] = stable_digest(payload["record"])
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        store.get(proposal.proposal_digest)

    admission = approved(manager, proposal).admission
    preview = manager.preview_apply(proposal, {"version": 1})
    for section in ("admission", "preview"):
        path.unlink()
        store.save(proposal, admission=admission, preview=preview)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["record"][section]["unexpected"] = "artifact:unknown"
        payload["record_digest"] = stable_digest(payload["record"])
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match="schema"):
            store.get(proposal.proposal_digest)


def test_apply_increments_version_without_mutating_production_baseline() -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    admitted = approved(manager, proposal)
    baseline = {
        "version": 4,
        "factor_weights": {"old": 1.0},
        "risk_rules": {"max_drawdown": 0.25},
        "registry": {"existing": "factor:old:v1"},
    }
    policy = manager.apply(admitted, baseline)
    assert isinstance(policy, VersionedResearchPolicy)
    assert policy.version == 5
    assert policy.factor_weights == {"old": 1.0, "value": 0.7}
    assert policy.risk_rules["max_drawdown"] == 0.18
    assert policy.registry["existing"] == "factor:old:v1"
    assert policy.paper_only is True
    assert policy.fingerprint
    assert baseline == {
        "version": 4,
        "factor_weights": {"old": 1.0},
        "risk_rules": {"max_drawdown": 0.25},
        "registry": {"existing": "factor:old:v1"},
    }


def test_next_research_request_can_reference_approved_policy_fingerprint() -> None:
    manager = LearningManager()
    proposal = manager.propose_update(settlement())
    policy = manager.apply(approved(manager, proposal), {"version": 1})
    request = ResearchRequest(
        run_id="next-run",
        instrument="ETF:SPY",
        as_of="2026-10-04",
        research_plan=ResearchPlan(required_datasets=("fixture-prices",)),
        analyst_roles=("technical",),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg-next",
        previous_policy_fingerprint=policy.fingerprint,
    )
    assert request.previous_policy_fingerprint == policy.fingerprint
