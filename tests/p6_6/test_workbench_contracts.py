from __future__ import annotations

import pytest

from finahinking.p6_6.workbench import (
    ALLOWED_FAULT_ACTIONS,
    ALLOWED_RISK_ACTIONS,
    ExecutionPolicy,
    FaultPolicy,
    ParameterChangeExplanation,
    PolicyProposal,
    PositionPolicySpec,
    ResearchCharter,
    RiskStatePolicy,
)


def test_position_policy_is_frozen_and_fingerprinted() -> None:
    policy = PositionPolicySpec(policy_id="equal", version="v1", mapping="equal_weight")
    assert policy.to_dict()["mapping"] == "equal_weight"
    assert len(policy.fingerprint) == 64
    with pytest.raises((AttributeError, TypeError)):
        policy.mapping = "rank_weight"  # type: ignore[misc]


def test_policies_reject_non_allowlisted_actions_and_invalid_values() -> None:
    with pytest.raises(ValueError, match="mapping"):
        PositionPolicySpec(policy_id="bad", version="v1", mapping="python")
    with pytest.raises(ValueError, match="action"):
        FaultPolicy(policy_id="faults", version="v1", actions={"DATA_STALE": "RUN_CODE"})
    with pytest.raises(ValueError, match="finite"):
        ExecutionPolicy(policy_id="exec", version="v1", fee_bps=float("nan"))
    assert "REDUCE" in ALLOWED_FAULT_ACTIONS
    assert "FREEZE" in ALLOWED_RISK_ACTIONS


def test_charter_freezes_test_boundary_and_cannot_change_hard_constraints() -> None:
    charter = ResearchCharter(
        charter_id="charter-1",
        research_question="Does a longer momentum window reduce turnover?",
        hypothesis_scope="lagged momentum only",
        dataset_reference="fixture-dataset",
        data_split={"train": "2024-01/2024-06", "validation": "2024-07/2024-09", "test": "2024-10/2024-12"},
        evaluation_metrics=("oos_return", "turnover"),
        hard_constraints={"paper_only": True, "max_experiments": 12},
        allowed_primitives=("input", "return", "rolling", "lag", "rank"),
        max_experiments=12,
    )
    assert charter.test_accessible is False
    frozen = charter.freeze_test()
    assert frozen.test_accessible is True
    assert frozen.fingerprint != charter.fingerprint
    with pytest.raises(ValueError, match="test"):
        charter.assert_test_access()


def test_policy_proposal_only_contains_structured_diff() -> None:
    proposal = PolicyProposal(
        proposal_id="proposal-1",
        provider="offline",
        model="fixture-v1",
        input_context_fingerprint="a" * 64,
        target_component="position_policy",
        allowed_parameter_diff={"mapping": "rank_weight", "max_single_weight": 0.25},
        reasoning_summary="Compare rank-weighted sizing against equal weight.",
        candidate_range={"max_single_weight": [0.1, 0.25]},
        required_experiments=("paired-baseline",),
        warnings=("Historical evidence is descriptive.",),
    )
    assert proposal.to_dict()["allowed_parameter_diff"]["mapping"] == "rank_weight"
    with pytest.raises(ValueError, match="executable"):
        PolicyProposal(
            proposal_id="proposal-2",
            provider="offline",
            model="fixture-v1",
            input_context_fingerprint="b" * 64,
            target_component="position_policy",
            allowed_parameter_diff={"code": "import os"},
            reasoning_summary="bad",
        )


def test_parameter_change_explanation_marks_confounding() -> None:
    explanation = ParameterChangeExplanation(
        explanation_id="explain-1",
        strategy_id="strategy-1",
        parameter_changes={"lookback": {"before": 20, "after": 40}, "fee_bps": {"before": 5, "after": 8}},
        intent="Test a slower signal under higher assumed costs.",
        formula_before="m20",
        formula_after="m40",
        derivation=("lag the close", "compute a rolling return"),
        code_trace=("momentum", "costs"),
        finance_interpretation="The signal horizon and friction both changed.",
        expected_effects=("lower turnover", "higher cost drag"),
        paired_metrics={"baseline": {"oos": 0.1}, "variant": {"oos": 0.08}},
        attribution={"status": "ATTRIBUTION_CONFOUNDED"},
        oos_status="NOT_EVALUATED",
        stress_status="NOT_EVALUATED",
        stability_status="UNKNOWN",
        assumptions=("Both parameters are held fixed within each replay.",),
        limitations=("The change cannot identify a single-parameter effect.",),
        next_experiment="Replay the window change with fees held constant.",
    )
    assert explanation.attribution_status == "ATTRIBUTION_CONFOUNDED"
    assert explanation.fingerprint
