import pytest

from finahinking.p6.models import (
    ExperimentSpecification,
    Hypothesis,
    P6State,
    ResearchQuestion,
    TaskCategory,
)
from finahinking.p6.state_machine import GuidedStateMachine


def test_typed_question_hypothesis_spec_and_ordered_state_machine() -> None:
    question = ResearchQuestion("Does momentum work in this dataset?", user_id="u1")
    hypothesis = Hypothesis(
        question=question,
        statement="A fixed lagged momentum rank has positive excess return.",
        null_hypothesis="There is no excess return after costs.",
        universe="fixture_panel",
        period="2020-01-01/2020-01-05",
        factor="cross_sectional_momentum",
        benchmark="equal_weight",
        assumptions=("fixed lookback", "next-period execution"),
        limitations=("liquidity not modeled",),
    )
    spec = ExperimentSpecification.from_hypothesis(hypothesis, dataset_id="fixture_panel")
    assert spec.category is TaskCategory.QUANT
    assert spec.material_assumptions
    machine = GuidedStateMachine()
    for state in (
        P6State.CLASSIFIED,
        P6State.HYPOTHESIS_PROPOSED,
        P6State.EXPERIMENT_PROPOSED,
        P6State.ASSUMPTIONS_ACCEPTED,
        P6State.TOOL_EXECUTED,
        P6State.EVIDENCE_READY,
        P6State.EXPLANATION_READY,
        P6State.LEARNING_READY,
    ):
        machine.transition(state)
    assert machine.state is P6State.LEARNING_READY


def test_state_machine_rejects_skipping_assumption_review() -> None:
    machine = GuidedStateMachine()
    with pytest.raises(ValueError, match="transition"):
        machine.transition(P6State.TOOL_EXECUTED)
