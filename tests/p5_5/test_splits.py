import pytest

from finahinking.quant.splits import (
    OOSPlan,
    TestPeriod,
    TrainingPeriod,
    ValidationPeriod,
    evaluate_oos,
)


def test_oos_plan_freezes_configuration_before_later_test() -> None:
    plan = OOSPlan(
        training=TrainingPeriod("2020-01-01", "2020-01-05"),
        validation=ValidationPeriod("2020-01-06", "2020-01-07"),
        test=TestPeriod("2020-01-08", "2020-01-10"),
        hypothesis="momentum has separation",
        search_space={"lookback": [3]},
        experiment_count=1,
        selection_method="pre_registered",
        validation_method="fixed_validation",
    )
    frozen = plan.freeze_configuration({"lookback": 3, "top_fraction": 0.5})
    assert frozen.configuration_fingerprint
    assert frozen.evaluation_boundary.start > frozen.selection_boundary.end
    assert plan.to_dict()["test"]["start"] == "2020-01-08T00:00:00"
    evidence = evaluate_oos(frozen, {"2020-01-08": 0.1, "2020-01-09": -0.02})
    assert evidence.metrics["observation_count"] == 2
    with pytest.raises(ValueError, match="outside"):
        evaluate_oos(frozen, {"2020-01-07": 0.2})


def test_oos_plan_rejects_overlapping_selection_and_evaluation() -> None:
    with pytest.raises(ValueError, match="overlap|after|best-Sharpe"):
        OOSPlan(
            training=TrainingPeriod("2020-01-01", "2020-01-05"),
            validation=ValidationPeriod("2020-01-06", "2020-01-08"),
            test=TestPeriod("2020-01-08", "2020-01-10"),
            hypothesis="bad",
            search_space={"lookback": [1, 2]},
            experiment_count=2,
            selection_method="best_sharpe",
            validation_method="none",
        )


def test_multiple_experiment_plan_carries_an_explicit_oos_boundary() -> None:
    plan = OOSPlan(
        training=TrainingPeriod("2020-01-01", "2020-01-05"),
        validation=ValidationPeriod("2020-01-06", "2020-01-07"),
        test=TestPeriod("2020-01-08", "2020-01-10"),
        hypothesis="pre-registered comparison",
        search_space={"lookback": [2, 3]},
        experiment_count=2,
        selection_method="pre_registered",
        validation_method="fixed_oos",
    ).freeze_configuration({"lookback": 2})
    assert plan.experiment_count == 2
