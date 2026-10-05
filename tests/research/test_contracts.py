from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from finahinking.research.contracts import (
    CheckpointIdentity,
    DecisionCard,
    ProviderSelection,
    ResearchPlan,
    ResearchRequest,
    ResearchState,
    stable_digest,
    to_jsonable,
    validate_transition,
)


def make_request() -> ResearchRequest:
    return ResearchRequest(
        run_id="run-001",
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(
            hypotheses=("mean reversion",),
            required_datasets=("daily_prices",),
            factor_ids=("momentum.v1",),
            validation_spec={"oos": True},
            risk_policy_version="risk.v1",
        ),
        analyst_roles=("technical", "fundamentals"),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg-001",
    )


def test_contracts_round_trip_to_json_and_digest_is_order_independent() -> None:
    request = make_request()
    encoded = to_jsonable(request)
    decoded = json.loads(json.dumps(encoded, sort_keys=True))

    assert decoded["run_id"] == "run-001"
    assert decoded["as_of"] == "2026-10-01"
    assert stable_digest({"b": 2, "a": 1}) == stable_digest({"a": 1, "b": 2})
    assert stable_digest(request) == stable_digest(decoded)


def test_request_rejects_empty_instrument_and_duplicate_roles() -> None:
    request = make_request()
    with pytest.raises(ValueError, match="instrument"):
        ResearchRequest(
            run_id=request.run_id,
            instrument=" ",
            as_of=request.as_of,
            research_plan=request.research_plan,
            analyst_roles=request.analyst_roles,
            asset_class=request.asset_class,
            workflow_version=request.workflow_version,
            config_digest=request.config_digest,
        )

    with pytest.raises(ValueError, match="analyst_roles"):
        ResearchRequest(
            run_id=request.run_id,
            instrument=request.instrument,
            as_of=request.as_of,
            research_plan=request.research_plan,
            analyst_roles=("technical", "technical"),
            asset_class=request.asset_class,
            workflow_version=request.workflow_version,
            config_digest=request.config_digest,
        )


def test_state_transition_rejects_illegal_transition_and_allows_terminal_failure() -> None:
    validate_transition(ResearchState.RECEIVED, ResearchState.IDENTIFIED)
    validate_transition(ResearchState.DATA_CHECKED, ResearchState.NO_DATA_AVAILABLE)

    with pytest.raises(ValueError, match="transition"):
        validate_transition(ResearchState.RECEIVED, ResearchState.PAPER_DECISION_READY)

    with pytest.raises(ValueError, match="terminal"):
        validate_transition(ResearchState.FAILED, ResearchState.RECEIVED)


def test_to_jsonable_rejects_secrets_paths_and_callables() -> None:
    with pytest.raises(ValueError, match="secret"):
        to_jsonable({"api_key": "do-not-store"})
    with pytest.raises(TypeError, match="Path"):
        to_jsonable(Path("/tmp/private"))
    with pytest.raises(TypeError, match="callable"):
        to_jsonable(lambda: None)

    selection = ProviderSelection(
        provider="offline",
        model="fixture-v1",
        role_models={"technical": "fixture-v1"},
        capabilities=("structured_output",),
        metadata={"api_key": "secret", "endpoint": "https://example.invalid"},
    )
    redacted = selection.redacted()
    assert "api_key" not in json.dumps(redacted)
    assert "endpoint" not in json.dumps(redacted)


def test_checkpoint_rejects_reverse_as_of_and_has_stable_identity_digest() -> None:
    request = make_request()
    checkpoint = CheckpointIdentity(
        instrument=request.instrument,
        as_of=request.as_of,
        dataset_snapshot={"id": "prices-001", "as_of": "2026-09-30"},
        analyst_set=request.analyst_roles,
        role_model_map={"technical": "offline/fixture-v1"},
        skill_versions={"workflow": "v1"},
        workflow_version=request.workflow_version,
        depth=2,
        rounds=3,
        config_digest=request.config_digest,
        research_plan_digest=stable_digest(request.research_plan),
    )
    assert checkpoint.digest() == checkpoint.digest()

    with pytest.raises(ValueError, match="as_of"):
        CheckpointIdentity(
            instrument=request.instrument,
            as_of=request.as_of,
            dataset_snapshot={"id": "future", "as_of": "2026-10-02"},
            analyst_set=request.analyst_roles,
            role_model_map={},
            skill_versions={},
            workflow_version=request.workflow_version,
            depth=1,
            rounds=1,
            config_digest=request.config_digest,
            research_plan_digest=stable_digest(request.research_plan),
        )


def test_decision_card_is_explicitly_paper_only() -> None:
    card = DecisionCard(
        action="paper rebalance",
        weights={"ETF:SPY": 1.0},
        rationale="fixture evidence",
        evidence_refs=("artifact:quant-1",),
        limitations=("offline fixture",),
        approval_required=True,
        eligible=True,
    )
    assert card.paper_only is True
    assert to_jsonable(card)["paper_only"] is True
