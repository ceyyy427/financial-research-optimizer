"""Immutable research-validity records for P5.5 experiments.

The validity layer deliberately contains no statistical or third-party
implementation.  It records what an experiment did and did not establish so
that downstream result and explanation layers cannot silently imply realism.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    LIMITED = "LIMITED"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ValidityDimension(str, Enum):
    POINT_IN_TIME = "point_in_time_correctness"
    POINT_IN_TIME_CORRECTNESS = "point_in_time_correctness"  # noqa: PIE796
    AVAILABLE_AT_SEMANTICS = "available_at_semantics"
    LOOK_AHEAD_BIAS = "look_ahead_bias"
    SIGNAL_TIMING = "signal_timing"
    EXECUTION_TIMING = "execution_timing"
    REBALANCE_TIMING = "rebalance_timing"
    TRANSACTION_COSTS = "transaction_costs"
    SLIPPAGE = "slippage"
    TURNOVER = "turnover"
    BENCHMARK_ALIGNMENT = "benchmark_alignment"
    MISSING_DATA = "missing_data"
    SAMPLE_SIZE = "sample_size"
    IS_OOS_SEPARATION = "is_oos_separation"
    PARAMETER_SEARCH_SCOPE = "parameter_search_scope"
    MULTIPLE_TESTING = "multiple_testing"
    DATA_SNOOPING = "data_snooping"
    SURVIVORSHIP_BIAS = "survivorship_bias"
    DELISTING = "delisting"
    CORPORATE_ACTIONS = "corporate_actions"
    LIQUIDITY = "liquidity"
    CAPACITY = "capacity"
    LEVERAGE = "leverage"
    SHORTING = "shorting"
    MARKET_IMPACT = "market_impact"


# Keep this registry stable: it is part of the experiment evidence schema.
VALIDITY_DIMENSIONS: tuple[str, ...] = (
    "point_in_time_correctness",
    "available_at_semantics",
    "look_ahead_bias",
    "signal_timing",
    "execution_timing",
    "rebalance_timing",
    "transaction_costs",
    "slippage",
    "turnover",
    "benchmark_alignment",
    "missing_data",
    "sample_size",
    "is_oos_separation",
    "parameter_search_scope",
    "multiple_testing",
    "data_snooping",
    "survivorship_bias",
    "delisting",
    "corporate_actions",
    "liquidity",
    "capacity",
    "leverage",
    "shorting",
    "market_impact",
)
REQUIRED_VALIDITY_DIMENSIONS = VALIDITY_DIMENSIONS


SURVIVORSHIP_BIAS_NOT_MODELED = "SURVIVORSHIP_BIAS_NOT_MODELED"
DELISTING_NOT_MODELED = "DELISTING_NOT_MODELED"
CORPORATE_ACTIONS_PARTIAL = "CORPORATE_ACTIONS_PARTIAL"
LIQUIDITY_NOT_MODELED = "LIQUIDITY_NOT_MODELED"
CAPACITY_UNKNOWN = "CAPACITY_UNKNOWN"
MARKET_IMPACT_NOT_MODELED = "MARKET_IMPACT_NOT_MODELED"
AVAILABLE_AT_UNVERIFIED = "AVAILABLE_AT_UNVERIFIED"
OOS_BOUNDARY_MISSING = "OOS_BOUNDARY_MISSING"
MULTIPLE_TESTING_UNRECORDED = "MULTIPLE_TESTING_UNRECORDED"
DATA_SNOOPING_RISK = "DATA_SNOOPING_RISK"

WARNING_CODES: tuple[str, ...] = (
    SURVIVORSHIP_BIAS_NOT_MODELED,
    DELISTING_NOT_MODELED,
    CORPORATE_ACTIONS_PARTIAL,
    LIQUIDITY_NOT_MODELED,
    CAPACITY_UNKNOWN,
    MARKET_IMPACT_NOT_MODELED,
    AVAILABLE_AT_UNVERIFIED,
    OOS_BOUNDARY_MISSING,
    MULTIPLE_TESTING_UNRECORDED,
    DATA_SNOOPING_RISK,
)
VALIDITY_WARNING_CODES = WARNING_CODES


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        # json.dumps below is responsible for rejecting NaN and infinity.
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"value of type {type(value).__name__} is not JSON-safe")


def _canonical(value: Any) -> str:
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _status(value: ValidityStatus | str) -> ValidityStatus:
    try:
        return value if isinstance(value, ValidityStatus) else ValidityStatus(str(value).upper())
    except ValueError as exc:
        raise ValueError(f"invalid validity status: {value!r}") from exc


@dataclass(frozen=True)
class ValidityAssessment:
    """One explicit classification for a registered validity dimension."""

    dimension: str
    status: ValidityStatus
    note: str = ""

    def __post_init__(self) -> None:
        dimension = self.dimension.value if isinstance(self.dimension, ValidityDimension) else self.dimension
        if dimension not in VALIDITY_DIMENSIONS:
            raise ValueError(f"unknown validity dimension: {self.dimension}")
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "status", _status(self.status))
        if not isinstance(self.note, str):
            raise TypeError("validity note must be text")

    def to_dict(self) -> dict[str, str]:
        result = {"dimension": self.dimension, "status": self.status.value}
        if self.note:
            result["note"] = self.note
        return result


@dataclass(frozen=True, init=False)
class MultipleTestingMetadata:
    """Bounded search/selection metadata required for reproducible evidence."""

    hypothesis: str
    search_space: Any
    experiment_count: int
    selection_method: str
    validation_method: str
    oos_boundary: Any

    def __init__(
        self,
        hypothesis: str,
        search_space: Any,
        experiment_count: int,
        selection_method: str,
        validation_method: str,
        oos_boundary: Any = None,
    ) -> None:
        if not isinstance(hypothesis, str) or not hypothesis.strip():
            raise ValueError("hypothesis is required")
        if isinstance(experiment_count, bool) or not isinstance(experiment_count, int) or experiment_count < 1:
            raise ValueError("experiment_count must be a positive integer")
        for name, value in (("selection_method", selection_method), ("validation_method", validation_method)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        # The common multiple-testing failure is explicitly disallowed.  A
        # caller must use a pre-specified selection rule and validation/OOS
        # evidence rather than selecting the highest in-sample Sharpe.
        selection = selection_method.casefold().replace("-", "_").replace(" ", "_")
        if selection in {"best_sharpe", "best_sharpe_only", "max_sharpe", "highest_sharpe"}:
            raise ValueError("best-Sharpe-only selection is not permitted")
        if experiment_count > 1 and not oos_boundary:
            raise ValueError("multiple experiments require an explicit OOS boundary")
        try:
            normalized_space = _json_safe(search_space)
            normalized_boundary = _json_safe(oos_boundary) if oos_boundary is not None else None
            _canonical(normalized_space)
            _canonical(normalized_boundary)
        except (TypeError, ValueError) as exc:
            raise ValueError("search metadata must be JSON-safe") from exc
        object.__setattr__(self, "hypothesis", hypothesis)
        object.__setattr__(self, "search_space", normalized_space)
        object.__setattr__(self, "experiment_count", experiment_count)
        object.__setattr__(self, "selection_method", selection_method)
        object.__setattr__(self, "validation_method", validation_method)
        object.__setattr__(self, "oos_boundary", normalized_boundary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis": copy.deepcopy(self.hypothesis),
            "search_space": copy.deepcopy(self.search_space),
            "experiment_count": self.experiment_count,
            "selection_method": self.selection_method,
            "validation_method": self.validation_method,
            "oos_boundary": copy.deepcopy(self.oos_boundary),
        }


@dataclass(frozen=True, init=False)
class ResearchValidity:
    """A serializable, immutable validity profile attached to an experiment."""

    assessments: tuple[ValidityAssessment, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    multiple_testing: MultipleTestingMetadata | None

    def __init__(
        self,
        assessments: Mapping[str, ValidityStatus | str | ValidityAssessment] | tuple[ValidityAssessment, ...] | list[ValidityAssessment],
        warnings: tuple[str, ...] | list[str] = (),
        limitations: tuple[str, ...] | list[str] = (),
        multiple_testing: MultipleTestingMetadata | None = None,
    ) -> None:
        if isinstance(assessments, Mapping):
            normalized_items = []
            for dimension, value in assessments.items():
                dimension_text = dimension.value if isinstance(dimension, ValidityDimension) else str(dimension)
                if isinstance(value, ValidityAssessment):
                    normalized_items.append(value)
                elif isinstance(value, Mapping):
                    normalized_items.append(ValidityAssessment(dimension_text, value["status"], value.get("note", "")))
                else:
                    normalized_items.append(ValidityAssessment(dimension_text, value))
            normalized = tuple(normalized_items)
        else:
            normalized = tuple(assessments)
            if not all(isinstance(item, ValidityAssessment) for item in normalized):
                raise TypeError("assessments must be a mapping or ValidityAssessment sequence")
        missing = set(VALIDITY_DIMENSIONS) - {item.dimension for item in normalized}
        unknown = {item.dimension for item in normalized} - set(VALIDITY_DIMENSIONS)
        if missing or unknown:
            raise ValueError(
                "validity dimensions must be complete; "
                f"missing={sorted(missing)}, unknown={sorted(unknown)}"
            )
        if len({item.dimension for item in normalized}) != len(normalized):
            raise ValueError("validity dimensions must be unique")
        normalized = tuple(sorted(normalized, key=lambda item: item.dimension))
        warning_values = tuple(str(item) for item in warnings)
        unknown_warnings = set(warning_values) - set(WARNING_CODES)
        if unknown_warnings:
            raise ValueError(f"unknown warning code(s): {sorted(unknown_warnings)}")
        limitation_values = tuple(str(item) for item in limitations)
        if multiple_testing is not None and not isinstance(multiple_testing, MultipleTestingMetadata):
            raise TypeError("multiple_testing must be MultipleTestingMetadata or None")
        object.__setattr__(self, "assessments", normalized)
        object.__setattr__(self, "warnings", tuple(sorted(set(warning_values))))
        object.__setattr__(self, "limitations", limitation_values)
        object.__setattr__(self, "multiple_testing", multiple_testing)

    @classmethod
    def complete(
        cls,
        statuses: Mapping[str, ValidityStatus | str],
        *,
        warnings: tuple[str, ...] | list[str] = (),
        limitations: tuple[str, ...] | list[str] = (),
        multiple_testing: MultipleTestingMetadata | None = None,
    ) -> ResearchValidity:
        missing = set(VALIDITY_DIMENSIONS) - set(statuses)
        unknown = set(statuses) - set(VALIDITY_DIMENSIONS)
        if missing or unknown:
            raise ValueError(f"validity dimensions must be complete; missing={sorted(missing)}, unknown={sorted(unknown)}")
        return cls(statuses, warnings, limitations, multiple_testing)

    @classmethod
    def default_p5_5(cls) -> ResearchValidity:
        """Return the conservative profile used by the fixed P5.5 slice."""

        supported = {
            "point_in_time_correctness": ValidityStatus.SUPPORTED,
            "available_at_semantics": ValidityStatus.SUPPORTED,
            "look_ahead_bias": ValidityStatus.SUPPORTED,
            "signal_timing": ValidityStatus.SUPPORTED,
            "execution_timing": ValidityStatus.SUPPORTED,
            "rebalance_timing": ValidityStatus.SUPPORTED,
            "transaction_costs": ValidityStatus.SUPPORTED,
            "slippage": ValidityStatus.SUPPORTED,
            "turnover": ValidityStatus.SUPPORTED,
            "benchmark_alignment": ValidityStatus.LIMITED,
            "missing_data": ValidityStatus.LIMITED,
            "sample_size": ValidityStatus.LIMITED,
            "is_oos_separation": ValidityStatus.LIMITED,
            "parameter_search_scope": ValidityStatus.SUPPORTED,
            "multiple_testing": ValidityStatus.SUPPORTED,
            "data_snooping": ValidityStatus.LIMITED,
            "survivorship_bias": ValidityStatus.UNSUPPORTED,
            "delisting": ValidityStatus.UNSUPPORTED,
            "corporate_actions": ValidityStatus.LIMITED,
            "liquidity": ValidityStatus.UNSUPPORTED,
            "capacity": ValidityStatus.UNSUPPORTED,
            "leverage": ValidityStatus.SUPPORTED,
            "shorting": ValidityStatus.NOT_APPLICABLE,
            "market_impact": ValidityStatus.UNSUPPORTED,
        }
        return cls.complete(
            supported,
            warnings=WARNING_CODES,
            limitations=(
                "The fixed slice is descriptive and uses pre-registered parameters.",
                "Unsupported market realism is not implied.",
            ),
            multiple_testing=MultipleTestingMetadata(
                hypothesis="fixed cross-sectional lagged momentum experiment",
                search_space={"lookback": "fixed", "top_fraction": "fixed"},
                experiment_count=1,
                selection_method="pre_registered_fixed_config",
                validation_method="explicit_oos_boundary_required_for_oos_claims",
            ),
        )

    def status_for(self, dimension: str) -> ValidityStatus:
        for assessment in self.assessments:
            if assessment.dimension == dimension:
                return assessment.status
        raise KeyError(dimension)

    @property
    def dimensions(self) -> tuple[str, ...]:
        return tuple(item.dimension for item in self.assessments)

    def assessment(self, dimension: str | ValidityDimension) -> ValidityAssessment:
        key = dimension.value if isinstance(dimension, ValidityDimension) else dimension
        for item in self.assessments:
            if item.dimension == key:
                return item
        raise KeyError(key)

    @property
    def is_complete(self) -> bool:
        return {item.dimension for item in self.assessments} == set(VALIDITY_DIMENSIONS)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": 1,
            "assessments": [item.to_dict() for item in self.assessments],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
            "multiple_testing": self.multiple_testing.to_dict() if self.multiple_testing else None,
        }
        result["fingerprint"] = _fingerprint(result)
        return result

    @property
    def fingerprint(self) -> str:
        return _fingerprint(
            {
                "schema_version": 1,
                "assessments": [item.to_dict() for item in self.assessments],
                "warnings": list(self.warnings),
                "limitations": list(self.limitations),
                "multiple_testing": self.multiple_testing.to_dict() if self.multiple_testing else None,
            }
        )

    def to_json(self) -> str:
        return _canonical(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ResearchValidity:
        if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
            raise ValueError("research validity schema is invalid")
        assessments = tuple(
            ValidityAssessment(item["dimension"], item["status"], item.get("note", ""))
            for item in payload.get("assessments", ())
        )
        multiple = payload.get("multiple_testing")
        metadata = None
        if multiple is not None:
            metadata = MultipleTestingMetadata(**multiple)
        result = cls(assessments, tuple(payload.get("warnings", ())), tuple(payload.get("limitations", ())), metadata)
        if payload.get("fingerprint") != result.fingerprint:
            raise ValueError("research validity fingerprint is invalid")
        return result

    @classmethod
    def from_json(cls, encoded: str) -> ResearchValidity:
        try:
            return cls.from_dict(json.loads(encoded))
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise ValueError("research validity schema is invalid") from exc


def reject_best_sharpe_selection(selection_method: str) -> None:
    """Raise when a caller tries to call best in-sample Sharpe discovery."""

    MultipleTestingMetadata("hypothesis", {}, 1, selection_method, "pre_specified")


def validate_multiple_testing(metadata: MultipleTestingMetadata) -> MultipleTestingMetadata:
    if not isinstance(metadata, MultipleTestingMetadata):
        raise TypeError("multiple-testing metadata is required")
    return metadata
