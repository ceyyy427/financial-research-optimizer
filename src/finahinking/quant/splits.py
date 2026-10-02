"""Deterministic in-sample/out-of-sample boundary contracts for P5.5."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise
from typing import Any

import pandas as pd

from .validity import MultipleTestingMetadata


def _timestamp(value: pd.Timestamp | datetime | str) -> pd.Timestamp:
    result = pd.Timestamp(value)
    if pd.isna(result):
        raise ValueError("period boundary is invalid")
    return result


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    raise TypeError(f"configuration value of type {type(value).__name__} is not JSON-safe")


def _canonical(value: Any) -> str:
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Period:
    """A half-open chronological interval ``[start, end)``."""

    start: pd.Timestamp | datetime | str
    end: pd.Timestamp | datetime | str

    def __post_init__(self) -> None:
        start = _timestamp(self.start)
        end = _timestamp(self.end)
        try:
            ordered = start < end
        except TypeError as exc:
            raise ValueError("period boundaries must use compatible timezone semantics") from exc
        if not ordered:
            raise ValueError("period start must be before period end")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    def to_dict(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}

    def contains(self, value: pd.Timestamp | datetime | str) -> bool:
        timestamp = _timestamp(value)
        return self.start <= timestamp < self.end


@dataclass(frozen=True)
class TrainingPeriod(Period):
    pass


@dataclass(frozen=True)
class ValidationPeriod(Period):
    pass


@dataclass(frozen=True)
class TestPeriod(Period):
    # Prevent pytest from treating this domain type as a test class when it is
    # imported into a test module.
    __test__ = False

def _ordered(*periods: Period | None) -> None:
    present = [period for period in periods if period is not None]
    for previous, current in pairwise(present):
        try:
            overlaps = previous.end > current.start
        except TypeError as exc:
            raise ValueError("period boundaries must use compatible timezone semantics") from exc
        if overlaps:
            raise ValueError("OOS periods must be chronological and non-overlapping")


@dataclass(frozen=True, init=False)
class FrozenConfiguration:
    """A defensive, content-addressed configuration snapshot."""

    payload: dict[str, Any]
    fingerprint: str

    def __init__(self, configuration: Mapping[str, Any] | Any) -> None:
        if not isinstance(configuration, Mapping):
            raise TypeError("frozen configuration must be a mapping")
        normalized = _json_safe(configuration)
        if not isinstance(normalized, dict):
            raise TypeError("frozen configuration must be a mapping")
        object.__setattr__(self, "payload", copy.deepcopy(normalized))
        object.__setattr__(self, "fingerprint", _fingerprint(normalized))

    def to_dict(self) -> dict[str, Any]:
        return {"payload": copy.deepcopy(self.payload), "fingerprint": self.fingerprint}


@dataclass(frozen=True, init=False)
class ParameterSelectionBoundary:
    """The only interval allowed to select or freeze parameters."""

    training_period: TrainingPeriod
    validation_period: ValidationPeriod | None
    frozen_configuration: FrozenConfiguration | None

    def __init__(
        self,
        training_period: TrainingPeriod | Period | None = None,
        validation_period: ValidationPeriod | Period | None = None,
        frozen_configuration: FrozenConfiguration | Mapping[str, Any] | None = None,
        *,
        training: TrainingPeriod | Period | None = None,
        validation: ValidationPeriod | Period | None = None,
    ) -> None:
        resolved_training = training_period if training_period is not None else training
        resolved_validation = validation_period if validation_period is not None else validation
        if resolved_training is None:
            raise ValueError("training period is required")
        if not isinstance(resolved_training, TrainingPeriod):
            resolved_training = TrainingPeriod(resolved_training.start, resolved_training.end)
        if resolved_validation is not None and not isinstance(resolved_validation, ValidationPeriod):
            resolved_validation = ValidationPeriod(resolved_validation.start, resolved_validation.end)
        _ordered(resolved_training, resolved_validation)
        if isinstance(frozen_configuration, Mapping):
            resolved_configuration = FrozenConfiguration(frozen_configuration)
        elif frozen_configuration is None or isinstance(frozen_configuration, FrozenConfiguration):
            resolved_configuration = frozen_configuration
        else:
            raise TypeError("frozen configuration is invalid")
        object.__setattr__(self, "training_period", resolved_training)
        object.__setattr__(self, "validation_period", resolved_validation)
        object.__setattr__(self, "frozen_configuration", resolved_configuration)

    @property
    def configuration_fingerprint(self) -> str | None:
        return self.frozen_configuration.fingerprint if self.frozen_configuration else None

    @property
    def frozen_configuration_fingerprint(self) -> str | None:
        return self.configuration_fingerprint

    @property
    def start(self) -> pd.Timestamp:
        return self.training_period.start

    @property
    def end(self) -> pd.Timestamp:
        return (self.validation_period or self.training_period).end

    def freeze(self, configuration: Mapping[str, Any]) -> ParameterSelectionBoundary:
        if self.frozen_configuration is not None:
            raise ValueError("configuration is already frozen")
        return ParameterSelectionBoundary(self.training_period, self.validation_period, FrozenConfiguration(configuration))

    freeze_configuration = freeze
    freeze_config = freeze

    def to_dict(self) -> dict[str, Any]:
        return {
            "training_period": self.training_period.to_dict(),
            "validation_period": self.validation_period.to_dict() if self.validation_period else None,
            "frozen_configuration": self.frozen_configuration.to_dict() if self.frozen_configuration else None,
        }


@dataclass(frozen=True, init=False)
class EvaluationBoundary:
    """The later interval on which a frozen configuration may be evaluated."""

    test_period: TestPeriod
    parameter_selection_boundary: ParameterSelectionBoundary

    def __init__(
        self,
        test_period: TestPeriod | Period,
        parameter_selection_boundary: ParameterSelectionBoundary | None = None,
        *,
        parameter_selection: ParameterSelectionBoundary | None = None,
    ) -> None:
        if not isinstance(test_period, TestPeriod):
            test_period = TestPeriod(test_period.start, test_period.end)
        selection = parameter_selection_boundary or parameter_selection
        if selection is None:
            raise ValueError("parameter selection boundary is required")
        _ordered(selection.training_period, selection.validation_period, test_period)
        if selection.frozen_configuration is None:
            raise ValueError("configuration must be frozen before evaluation")
        object.__setattr__(self, "test_period", test_period)
        object.__setattr__(self, "parameter_selection_boundary", selection)

    @property
    def frozen_configuration_fingerprint(self) -> str:
        return self.parameter_selection_boundary.frozen_configuration_fingerprint  # type: ignore[return-value]

    @property
    def start(self) -> pd.Timestamp:
        return self.test_period.start

    @property
    def end(self) -> pd.Timestamp:
        return self.test_period.end

    def to_dict(self) -> dict[str, Any]:
        return {"test_period": self.test_period.to_dict(), "parameter_selection_boundary": self.parameter_selection_boundary.to_dict()}


@dataclass(frozen=True, init=False)
class OOSPlan:
    """Complete deterministic train/select/freeze/evaluate metadata."""

    training_period: TrainingPeriod
    validation_period: ValidationPeriod | None
    test_period: TestPeriod
    hypothesis: str
    search_space: Any
    experiment_count: int
    selection_method: str
    validation_method: str
    parameter_selection_boundary: ParameterSelectionBoundary
    evaluation_boundary: EvaluationBoundary | None

    def __init__(
        self,
        training_period: TrainingPeriod | Period | None = None,
        test_period: TestPeriod | Period | None = None,
        *,
        validation_period: ValidationPeriod | Period | None = None,
        hypothesis: str = "",
        search_space: Any = None,
        experiment_count: int = 1,
        selection_method: str = "pre_specified",
        validation_method: str = "out_of_sample",
        frozen_configuration: Mapping[str, Any] | FrozenConfiguration | None = None,
        training: TrainingPeriod | Period | None = None,
        validation: ValidationPeriod | Period | None = None,
        test: TestPeriod | Period | None = None,
        selection: ParameterSelectionBoundary | None = None,
        evaluation: EvaluationBoundary | None = None,
    ) -> None:
        resolved_training = training_period if training_period is not None else training
        resolved_validation = validation_period if validation_period is not None else validation
        resolved_test = test_period if test_period is not None else test
        if resolved_training is None or resolved_test is None:
            raise ValueError("training and test periods are required")
        train = resolved_training if isinstance(resolved_training, TrainingPeriod) else TrainingPeriod(resolved_training.start, resolved_training.end)
        valid = None if resolved_validation is None else (resolved_validation if isinstance(resolved_validation, ValidationPeriod) else ValidationPeriod(resolved_validation.start, resolved_validation.end))
        test_window = resolved_test if isinstance(resolved_test, TestPeriod) else TestPeriod(resolved_test.start, resolved_test.end)
        _ordered(train, valid, test_window)
        if not isinstance(hypothesis, str) or not hypothesis.strip():
            raise ValueError("hypothesis is required")
        boundary_metadata = {
            "training": train.to_dict(),
            "validation": valid.to_dict() if valid else None,
            "test": test_window.to_dict(),
        }
        metadata = MultipleTestingMetadata(
            hypothesis,
            {} if search_space is None else search_space,
            experiment_count,
            selection_method,
            validation_method,
            boundary_metadata if experiment_count > 1 else None,
        )
        boundary = selection or ParameterSelectionBoundary(train, valid, frozen_configuration)
        if boundary.training_period != train or boundary.validation_period != valid:
            raise ValueError("selection boundary does not match plan periods")
        resolved_evaluation = evaluation
        if resolved_evaluation is not None:
            if resolved_evaluation.test_period != test_window:
                raise ValueError("evaluation boundary does not match test period")
        elif boundary.frozen_configuration is not None:
            resolved_evaluation = EvaluationBoundary(test_window, boundary)
        object.__setattr__(self, "training_period", train)
        object.__setattr__(self, "validation_period", valid)
        object.__setattr__(self, "test_period", test_window)
        object.__setattr__(self, "hypothesis", hypothesis)
        object.__setattr__(self, "search_space", copy.deepcopy(metadata.search_space))
        object.__setattr__(self, "experiment_count", metadata.experiment_count)
        object.__setattr__(self, "selection_method", metadata.selection_method)
        object.__setattr__(self, "validation_method", metadata.validation_method)
        object.__setattr__(self, "parameter_selection_boundary", boundary)
        object.__setattr__(self, "evaluation_boundary", resolved_evaluation)

    @property
    def frozen_configuration_fingerprint(self) -> str:
        value = self.parameter_selection_boundary.frozen_configuration_fingerprint
        if value is None:
            raise ValueError("configuration has not been frozen")
        return value

    @property
    def configuration_fingerprint(self) -> str:
        return self.frozen_configuration_fingerprint

    @property
    def selection_boundary(self) -> ParameterSelectionBoundary:
        return self.parameter_selection_boundary

    @property
    def evaluation(self) -> EvaluationBoundary | None:
        return self.evaluation_boundary

    def freeze_configuration(self, configuration: Mapping[str, Any]) -> OOSPlan:
        if self.parameter_selection_boundary.frozen_configuration is not None:
            raise ValueError("configuration is already frozen")
        frozen = self.parameter_selection_boundary.freeze(configuration)
        return OOSPlan(
            training_period=self.training_period,
            validation_period=self.validation_period,
            test_period=self.test_period,
            hypothesis=self.hypothesis,
            search_space=self.search_space,
            experiment_count=self.experiment_count,
            selection_method=self.selection_method,
            validation_method=self.validation_method,
            selection=frozen,
        )

    freeze = freeze_configuration

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": 1,
            "training_period": self.training_period.to_dict(),
            "validation_period": self.validation_period.to_dict() if self.validation_period else None,
            "test_period": self.test_period.to_dict(),
            "test": self.test_period.to_dict(),
            "hypothesis": self.hypothesis,
            "search_space": copy.deepcopy(self.search_space),
            "experiment_count": self.experiment_count,
            "selection_method": self.selection_method,
            "validation_method": self.validation_method,
            "parameter_selection_boundary": self.parameter_selection_boundary.to_dict(),
            "evaluation_boundary": self.evaluation_boundary.to_dict() if self.evaluation_boundary else None,
            "frozen_configuration_fingerprint": self.parameter_selection_boundary.frozen_configuration_fingerprint,
        }
        result["fingerprint"] = _fingerprint(result)
        return result

    @property
    def fingerprint(self) -> str:
        return _fingerprint(
            {
                "schema_version": 1,
                "training_period": self.training_period.to_dict(),
                "validation_period": self.validation_period.to_dict() if self.validation_period else None,
                "test_period": self.test_period.to_dict(),
                "hypothesis": self.hypothesis,
                "search_space": copy.deepcopy(self.search_space),
                "experiment_count": self.experiment_count,
                "selection_method": self.selection_method,
                "validation_method": self.validation_method,
                "parameter_selection_boundary": self.parameter_selection_boundary.to_dict(),
                "evaluation_boundary": self.evaluation_boundary.to_dict() if self.evaluation_boundary else None,
                "frozen_configuration_fingerprint": self.parameter_selection_boundary.frozen_configuration_fingerprint,
            }
        )


@dataclass(frozen=True)
class OOSResult:
    """Normalized, deterministic evidence computed only on a frozen test window."""

    plan_fingerprint: str
    configuration_fingerprint: str
    observations: tuple[tuple[str, float], ...]
    metrics: dict[str, float | int | None]

    @property
    def fingerprint(self) -> str:
        return _fingerprint(
            {
                "schema_version": 1,
                "plan_fingerprint": self.plan_fingerprint,
                "configuration_fingerprint": self.configuration_fingerprint,
                "observations": self.observations,
                "metrics": self.metrics,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "plan_fingerprint": self.plan_fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "observations": [[timestamp, value] for timestamp, value in self.observations],
            "metrics": copy.deepcopy(self.metrics),
            "fingerprint": self.fingerprint,
        }


def evaluate_oos(plan: OOSPlan, observations: Mapping[Any, float]) -> OOSResult:
    """Evaluate finite observations strictly inside the later frozen test period.

    This intentionally exposes descriptive aggregation only.  It cannot select
    parameters and rejects any observation that falls in the training or
    validation windows.
    """

    if not isinstance(plan, OOSPlan) or plan.evaluation_boundary is None:
        raise ValueError("an OOS plan must be frozen before evaluation")
    if not isinstance(observations, Mapping) or not observations:
        raise ValueError("test observations are required")
    normalized: list[tuple[str, float]] = []
    for timestamp, value in observations.items():
        parsed = _timestamp(timestamp)
        if not plan.test_period.contains(parsed):
            raise ValueError("observation is outside the frozen evaluation boundary")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("test observations must be finite numbers")
        normalized.append((parsed.isoformat(), number))
    normalized.sort(key=lambda item: item[0])
    values = [value for _, value in normalized]
    metrics: dict[str, float | int | None] = {
        "observation_count": len(values),
        "mean": float(sum(values) / len(values)),
        "cumulative": float(pd.Series(values, dtype=float).sum()),
    }
    result = OOSResult(plan.fingerprint, plan.frozen_configuration_fingerprint, tuple(normalized), metrics)
    return result
