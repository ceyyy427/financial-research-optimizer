import pytest

from finahinking.quant.portfolio import optimize_equal_weight_allocation, validate_target_weights


def test_target_weights_are_explicit_and_within_long_only_limits():
    weights = validate_target_weights({"asset": 0.75}, max_weight=1.0, long_only=True)
    assert weights == {"asset": 0.75}


def test_target_weights_reject_negative_or_overallocated_values():
    with pytest.raises(ValueError, match="negative"):
        validate_target_weights({"asset": -0.1}, max_weight=1.0, long_only=True)
    with pytest.raises(ValueError, match="sum"):
        validate_target_weights({"a": 0.75, "b": 0.5}, max_weight=1.0, long_only=True)


def test_equal_weight_optimizer_is_deterministic_and_constraint_aware():
    assert optimize_equal_weight_allocation(["b", "a", "a"]) == {"a": 0.5, "b": 0.5}
    assert optimize_equal_weight_allocation(["a", "b", "c"], max_weight=0.25) == {
        "a": 0.25,
        "b": 0.25,
        "c": 0.25,
    }


def test_equal_weight_optimizer_rejects_empty_universe():
    with pytest.raises(ValueError, match="asset universe"):
        optimize_equal_weight_allocation([])


def test_equal_weight_optimizer_validates_universe_and_caps():
    with pytest.raises(ValueError, match="asset identifiers"):
        optimize_equal_weight_allocation(["a", 2])
    with pytest.raises(ValueError, match="max weight"):
        optimize_equal_weight_allocation(["a"], max_weight=0.0)
    with pytest.raises(ValueError, match="max weight"):
        optimize_equal_weight_allocation(["a"], max_weight=float("nan"))
