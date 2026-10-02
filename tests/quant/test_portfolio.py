import pytest

from finahinking.quant.portfolio import validate_target_weights


def test_target_weights_are_explicit_and_within_long_only_limits():
    weights = validate_target_weights({"asset": 0.75}, max_weight=1.0, long_only=True)
    assert weights == {"asset": 0.75}


def test_target_weights_reject_negative_or_overallocated_values():
    with pytest.raises(ValueError, match="negative"):
        validate_target_weights({"asset": -0.1}, max_weight=1.0, long_only=True)
    with pytest.raises(ValueError, match="sum"):
        validate_target_weights({"a": 0.75, "b": 0.5}, max_weight=1.0, long_only=True)
