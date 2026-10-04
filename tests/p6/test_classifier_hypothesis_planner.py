from finahinking.p6.classifier import classify_question
from finahinking.p6.hypothesis import build_hypothesis
from finahinking.p6.models import TaskCategory
from finahinking.p6.planner import plan_experiment


def test_classifier_routes_only_quantitative_question_to_quant() -> None:
    assert classify_question("Does momentum work in this dataset?").category is TaskCategory.QUANT
    assert classify_question("What is a Sharpe ratio?").category is TaskCategory.LEARN
    assert classify_question("Please show the source evidence for this claim").category is TaskCategory.EVIDENCE
    assert classify_question("Should I buy this stock?").category is TaskCategory.STAND_BACK


def test_hypothesis_and_planner_preserve_material_assumptions() -> None:
    question = build_hypothesis("Does momentum work in this dataset?")
    assert question.statement_type == "SYSTEM HYPOTHESIS"
    spec = plan_experiment(question, dataset_id="fixture_panel")
    assert spec.benchmark == "equal_weight"
    assert spec.execution_timing == "next_period"
    assert spec.requires_confirmation is False
    changed = plan_experiment(question, dataset_id="fixture_panel", benchmark="custom")
    assert changed.requires_confirmation is True
