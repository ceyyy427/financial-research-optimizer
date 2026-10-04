"""TDD coverage for the P8.2 Finathink-owned research contracts."""

from __future__ import annotations

import json

import pytest

from finahinking.p8_2.contracts import (
    DatasetSnapshot,
    FeatureObservation,
    MarketObservation,
    MLResearchSpecification,
    ParameterSweepSpecification,
    ResearchPoint,
)


def _observation(**overrides: object) -> MarketObservation:
    values = {
        "instrument": "DEMO",
        "timestamp": "2026-01-02T00:00:00+00:00",
        "open": 100.0,
        "high": 103.0,
        "low": 99.0,
        "close": 102.0,
        "volume": 1_000.0,
        "source": "fixture",
        "provider": "finathink.fixture",
        "available_at": "2026-01-02T00:00:00+00:00",
    }
    values.update(overrides)
    return MarketObservation(**values)


def test_market_observation_and_snapshot_round_trip_with_pit() -> None:
    observation = _observation()
    snapshot = DatasetSnapshot(
        dataset_id="fixture-demo",
        observations=(observation,),
        mode="SAMPLE",
        as_of="2026-01-03T00:00:00+00:00",
        provenance={"provider": "finathink.fixture", "source": "deterministic"},
    )

    assert snapshot.pit_available("2026-01-03T00:00:00+00:00") is True
    assert snapshot.pit_available("2026-01-01T00:00:00+00:00") is False
    encoded = snapshot.to_json()
    restored = DatasetSnapshot.from_json(encoded)
    assert restored.to_dict() == snapshot.to_dict()
    assert json.loads(encoded)["fingerprint"] == snapshot.fingerprint


def test_snapshot_accepts_explicit_synthetic_mode() -> None:
    snapshot = DatasetSnapshot(
        dataset_id="synthetic-demo",
        observations=(_observation(),),
        mode="SYNTHETIC",
        provenance={"provider": "test", "source": "synthetic"},
    )
    assert snapshot.mode == "SYNTHETIC"


def test_contract_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _observation(timestamp="2026-01-02T00:00:00")
    with pytest.raises(ValueError, match="timezone-aware"):
        _observation(available_at="2026-01-02T00:00:00")


def test_contracts_reject_non_finite_values_and_executable_payload_keys() -> None:
    with pytest.raises(ValueError, match="finite"):
        _observation(close=float("nan"))

    with pytest.raises(ValueError, match="executable"):
        FeatureObservation(
            feature_name="momentum",
            instrument="DEMO",
            timestamp="2026-01-02T00:00:00Z",
            value=0.1,
            dataset_fingerprint="a" * 64,
            metadata={"__code__": "import os"},
        )


def test_research_point_bounds_and_fingerprint_changes() -> None:
    point = ResearchPoint(
        point_id="point-1",
        instrument="DEMO",
        timestamp="2026-01-02T00:00:00Z",
        value=0.1,
        dataset_fingerprint="a" * 64,
    )
    changed = ResearchPoint(
        point_id="point-1",
        instrument="DEMO",
        timestamp="2026-01-02T00:00:00Z",
        value=0.2,
        dataset_fingerprint="a" * 64,
    )
    assert point.fingerprint != changed.fingerprint
    with pytest.raises(ValueError, match="finite"):
        ResearchPoint(
            point_id="point-1",
            instrument="DEMO",
            timestamp="2026-01-02T00:00:00Z",
            value=float("inf"),
            dataset_fingerprint="a" * 64,
        )


def test_sweep_and_ml_specifications_are_bounded_and_json_safe() -> None:
    sweep = ParameterSweepSpecification(
        strategy_version="demo-v1",
        parameters={"direction": "long"},
        parameter_ranges={"window": (5, 10), "threshold": (0.1, 0.2)},
        train_scope={"start": "2020-01-01", "end": "2022-01-01"},
        validation_scope={"start": "2022-01-01", "end": "2023-01-01"},
        oos_scope={"start": "2023-01-01", "end": "2024-01-01"},
    )
    assert sweep.experiment_count == 4
    assert len(sweep.enumerate_parameters()) == 4
    assert sweep.from_json(sweep.to_json()).fingerprint == sweep.fingerprint
    with pytest.raises(ValueError, match="experiment"):
        ParameterSweepSpecification(
            strategy_version="demo-v1",
            parameter_ranges={"window": list(range(10_001))},
        )

    ml = MLResearchSpecification(
        research_id="ml-demo",
        dataset_fingerprint="a" * 64,
        target="next_return",
        features=("momentum", "volatility"),
        train_scope={"start": "2020-01-01", "end": "2022-01-01"},
        validation_scope={"start": "2022-01-01", "end": "2023-01-01"},
        test_scope={"start": "2023-01-01", "end": "2024-01-01"},
    )
    assert ml.from_dict(ml.to_dict()).fingerprint == ml.fingerprint
