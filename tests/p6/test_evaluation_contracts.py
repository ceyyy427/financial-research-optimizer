import pandas as pd
import pytest

from finahinking.p6.classifier import classify_question
from finahinking.p6.explanation import ExplanationRecord
from finahinking.p6.gateway import P6QuantGateway
from finahinking.p6.grounding import claims_from_result, ground_numeric_claim
from finahinking.p6.hypothesis import build_hypothesis
from finahinking.p6.models import TaskCategory, TypedToolRequest, TypedToolResponse
from finahinking.p6.planner import plan_experiment
from finahinking.p6.workflows import GuidedResearchError, GuidedResearchService
from finahinking.quant.interfaces import _digest


@pytest.mark.parametrize(
    ("text", "category"),
    (
        ("Is the sky blue?", TaskCategory.ANSWER),
        ("How do I inspect a stored run?", TaskCategory.GUIDE),
        ("Which dataset should we use?", TaskCategory.QUESTION),
        ("Please cite the source evidence", TaskCategory.EVIDENCE),
        ("Does momentum work in this dataset?", TaskCategory.QUANT),
        ("What is the history of factor investing?", TaskCategory.HISTORY),
        ("What is a Sharpe ratio?", TaskCategory.LEARN),
        ("Should I buy this stock?", TaskCategory.STAND_BACK),
    ),
)
def test_classifier_covers_all_categories_and_ambiguity(text: str, category: TaskCategory) -> None:
    assert classify_question(text).category is category


def test_ambiguous_question_requires_clarification() -> None:
    result = classify_question("Can you help with this?")
    assert result.category is TaskCategory.QUESTION
    assert result.required_clarifications


def test_plan_fingerprint_is_reproducible_and_material_changes_pause() -> None:
    hypothesis = build_hypothesis("Does momentum work in this dataset?")
    first = plan_experiment(hypothesis, dataset_id="fixture_panel")
    second = plan_experiment(hypothesis, dataset_id="fixture_panel")
    assert first.fingerprint == second.fingerprint
    changed = plan_experiment(hypothesis, dataset_id="fixture_panel", benchmark="custom")
    assert changed.requires_confirmation
    assert changed.assumption_review is not None
    assert not changed.assumption_review.accepted


def test_direct_gateway_requires_an_accepted_registered_plan() -> None:
    hypothesis = build_hypothesis("Does momentum work in this dataset?")
    specification = plan_experiment(hypothesis, dataset_id="fixture_panel")
    gateway = P6QuantGateway()
    response = gateway.run_momentum(
        pd.DataFrame(
            [
                {"date": "2020-01-01", "asset": "AAA", "close": 100, "available_at": "2020-01-01"},
                {"date": "2020-01-01", "asset": "BBB", "close": 100, "available_at": "2020-01-01"},
            ]
        ),
        question=hypothesis.question.question,
        hypothesis=hypothesis.statement,
    )
    assert response.status.value == "REJECTED"
    assert not gateway._records  # type: ignore[attr-defined]
    gateway.register_plan(specification)
    assert specification.assumption_review is not None and specification.assumption_review.accepted


def test_grounding_rejects_self_consistent_hash_without_run_identity() -> None:
    payload = {"metrics": {"sharpe": 99.0}}
    payload["fingerprint"] = _digest(payload)
    with pytest.raises(ValueError, match="linked"):
        claims_from_result(payload, "quant-approved", "QuantRun")


def test_unverified_low_level_claim_cannot_enter_an_explanation() -> None:
    claim = ground_numeric_claim(
        "A value was 1.",
        value=1.0,
        evidence_reference="quant-approved",
        evidence_kind="QuantRun",
        source_fingerprint="0" * 64,
    )
    with pytest.raises(ValueError, match="verified"):
        ExplanationRecord(
            what_was_asked="What was measured?",
            what_was_tested="A fixed record",
            data_used="A fixture",
            result=claim.text,
            supports="The field was present.",
            does_not_support="It is not a forecast.",
            limitations=("Historical only.",),
            concepts=("Evidence",),
            claims=(claim,),
            evidence_reference="quant-approved",
        )


def test_typed_failure_code_is_allow_listed() -> None:
    with pytest.raises(ValueError, match="failure_code"):
        TypedToolResponse("quant.run_backtest", "FAILED", failure_code="invented")


def test_typed_execute_preserves_request_provenance_and_plan_binding() -> None:
    hypothesis = build_hypothesis("Does momentum work in this dataset?")
    specification = plan_experiment(hypothesis, dataset_id="fixture_panel")
    gateway = P6QuantGateway()
    gateway.register_plan(specification)
    rows = []
    for date, a, b in (
        ("2020-01-01", 100, 100),
        ("2020-01-02", 110, 95),
        ("2020-01-03", 121, 90),
        ("2020-01-04", 120, 92),
        ("2020-01-05", 130, 88),
    ):
        rows.extend(
            [
                {"date": date, "asset": "AAA", "close": a, "available_at": date},
                {"date": date, "asset": "BBB", "close": b, "available_at": date},
            ]
        )
    request = TypedToolRequest(
        "quant.run_backtest",
        {
            "rows": rows,
            "question": hypothesis.question.question,
            "hypothesis": hypothesis.statement,
        },
        experiment_fingerprint=specification.fingerprint,
        assumptions_accepted=True,
        provenance_context={"surface": "p6-test"},
    )
    response = gateway.execute(request)
    assert response.status == "SUCCEEDED"
    assert response.provenance["request_fingerprint"] == request.fingerprint
    assert response.provenance["request_context"] == {"surface": "p6-test"}


def test_post_construction_request_mutation_is_revalidated() -> None:
    request = TypedToolRequest("quant.inspect_run", {"run_id": "quant-1"})
    request.parameters["source_code"] = "print('unsafe')"
    response = P6QuantGateway().execute(request)
    assert response.status == "REJECTED"
    assert response.failure_code == "UNSAFE_REQUEST"


def test_failed_typed_call_returns_a_terminal_audit_without_evidence() -> None:
    class RejectingGateway(P6QuantGateway):
        def execute(self, request: TypedToolRequest) -> TypedToolResponse:
            return TypedToolResponse(
                request.tool_name,
                "FAILED",
                request_id=request.resolved_request_id,
                failure_code="EXECUTION_ERROR",
                message="bounded fixture failure",
            )

    with pytest.raises(GuidedResearchError) as error:
        GuidedResearchService(gateway=RejectingGateway()).run_momentum(
            "u1", "Does momentum work in this dataset?", pd.DataFrame(
                [
                    {"date": "2020-01-01", "asset": "AAA", "close": 100, "available_at": "2020-01-01"},
                    {"date": "2020-01-01", "asset": "BBB", "close": 100, "available_at": "2020-01-01"},
                ]
            ),
        )
    assert error.value.audit.state == "FAILED"
    assert not error.value.audit.quant_run_ids
