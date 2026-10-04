from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from finahinking.factors.core import momentum_factor
from finahinking.factors.registry import (
    FactorHealth,
    FactorHealthStatus,
    FactorMetadata,
    FactorRegistry,
    run_factor_lifecycle,
)
from finahinking.research.contracts import stable_digest


def metadata(**overrides) -> FactorMetadata:
    values = {
        "factor_id": "momentum.v1",
        "version": "1.0.0",
        "definition": "trailing return",
        "formula": "close / close.shift(20) - 1",
        "input_fields": ("close",),
        "source": "fixture-source",
        "pit": True,
        "direction": "positive",
        "limits": {"max_turnover": 0.5},
        "validation_spec": {"shift_periods": 1, "oos": True},
    }
    values.update(overrides)
    return FactorMetadata(**values)


def health(status: FactorHealthStatus, as_of: str = "2026-10-01") -> FactorHealth:
    return FactorHealth(
        status=status,
        as_of=as_of,
        ic=0.05,
        icir=0.4,
        decay_score=0.1,
        crowding_score=0.1,
        collinearity_score=0.1,
        sample_size=100,
        reason=status.value,
    )


def test_existing_momentum_factor_api_remains_compatible() -> None:
    factor = momentum_factor(20)
    assert factor.name == "momentum_20d"
    assert callable(factor.compute)


def test_metadata_requires_pit_source_direction_and_validation_version() -> None:
    with pytest.raises(ValueError, match="source"):
        replace(metadata(), source=" ")
    with pytest.raises(ValueError, match="pit"):
        replace(metadata(), pit=False)
    with pytest.raises(ValueError, match="version"):
        replace(metadata(), version=" ")
    with pytest.raises(ValueError, match="validation_spec"):
        replace(metadata(), validation_spec={})


def test_registry_is_append_only_and_filters_unhealthy_factors() -> None:
    registry = FactorRegistry()
    factor = momentum_factor(20)
    registry.register(factor, metadata(), health(FactorHealthStatus.VALID))
    registry.update_health("momentum.v1", health(FactorHealthStatus.DECAYING))
    assert registry.get("momentum.v1").health_history == (
        health(FactorHealthStatus.VALID),
        health(FactorHealthStatus.DECAYING),
    )
    assert registry.select_eligible(date(2026, 10, 1)) == ()

    registry.update_health("momentum.v1", health(FactorHealthStatus.VALID, "2026-10-02"))
    assert [item.metadata.factor_id for item in registry.select_eligible(date(2026, 10, 2))] == ["momentum.v1"]


def test_lifecycle_rejects_t_plus_one_and_oos_violations_and_future_snapshot() -> None:
    factor = momentum_factor(20)
    invalid_shift = run_factor_lifecycle(factor, {"as_of": "2026-10-01"}, {"shift_periods": 0, "oos": True})
    invalid_oos = run_factor_lifecycle(factor, {"as_of": "2026-10-01"}, {"shift_periods": 1, "oos": False})
    future_snapshot = run_factor_lifecycle(factor, {"as_of": "2026-10-02"}, {"shift_periods": 1, "oos": True, "as_of": "2026-10-01"})

    assert invalid_shift.accepted is False and invalid_shift.failed_step == "T_PLUS_ONE"
    assert invalid_oos.accepted is False and invalid_oos.failed_step == "ANNUAL_OOS"
    assert future_snapshot.accepted is False and future_snapshot.failed_step == "PIT"


def test_lifecycle_result_is_deterministic() -> None:
    factor = momentum_factor(20)
    first = run_factor_lifecycle(factor, {"as_of": "2026-10-01", "dataset_id": "fixture"}, {"shift_periods": 1, "oos": True})
    second = run_factor_lifecycle(factor, {"dataset_id": "fixture", "as_of": "2026-10-01"}, {"oos": True, "shift_periods": 1})
    assert first.accepted is True
    assert stable_digest(first) == stable_digest(second)
    assert len(first.evidence_refs) == 8
