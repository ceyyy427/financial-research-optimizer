import pytest

from finahinking.quant.validity import (
    AVAILABLE_AT_UNVERIFIED,
    DATA_SNOOPING_RISK,
    MULTIPLE_TESTING_UNRECORDED,
    OOS_BOUNDARY_MISSING,
    REQUIRED_VALIDITY_DIMENSIONS,
    WARNING_CODES,
    ResearchValidity,
    ValidityAssessment,
    ValidityDimension,
    ValidityStatus,
)


def test_validity_profile_covers_every_required_dimension_and_round_trips() -> None:
    profile = ResearchValidity.default_p5_5()
    assert set(profile.dimensions) == set(REQUIRED_VALIDITY_DIMENSIONS)
    assert profile.assessment(ValidityDimension.POINT_IN_TIME).status in set(ValidityStatus)
    assert set(WARNING_CODES).issuperset(
        {
            "SURVIVORSHIP_BIAS_NOT_MODELED",
            "DELISTING_NOT_MODELED",
            "CORPORATE_ACTIONS_PARTIAL",
            "LIQUIDITY_NOT_MODELED",
            "CAPACITY_UNKNOWN",
        }
    )
    restored = ResearchValidity.from_dict(profile.to_dict())
    assert restored.fingerprint == profile.fingerprint
    assert restored.warnings


def test_validity_assessment_rejects_unknown_status() -> None:
    try:
        ValidityAssessment("not-a-status", "bad")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid validity status must be rejected")


def test_validity_profile_requires_all_registered_dimensions() -> None:
    with pytest.raises(ValueError, match="complete"):
        ResearchValidity({"point_in_time_correctness": ValidityStatus.SUPPORTED})


def test_multiple_testing_requires_oos_boundary() -> None:
    from finahinking.quant.validity import MultipleTestingMetadata

    with pytest.raises(ValueError, match="OOS boundary"):
        MultipleTestingMetadata("h", {"lookback": [2, 3]}, 2, "pre_registered", "fixed_validation")
    metadata = MultipleTestingMetadata(
        "h", {"lookback": [2, 3]}, 2, "pre_registered", "fixed_validation", {"test": "2020-01-01/2020-02-01"}
    )
    assert metadata.experiment_count == 2
    assert {AVAILABLE_AT_UNVERIFIED, OOS_BOUNDARY_MISSING, MULTIPLE_TESTING_UNRECORDED, DATA_SNOOPING_RISK}.issubset(WARNING_CODES)
