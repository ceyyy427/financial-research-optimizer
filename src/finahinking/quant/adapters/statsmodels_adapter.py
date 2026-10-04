"""Lazy statsmodels adapter returning only Finahinking-owned data."""

from __future__ import annotations

import copy
import math
from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from ..interfaces import _digest


class OptionalDependencyError(ImportError):
    """Raised when an optional adapter is used without its approved package."""


@dataclass(frozen=True, init=False)
class RegressionResult:
    """Normalized regression evidence; never stores a statsmodels model."""

    _parameters: dict[str, float]
    _metrics: dict[str, float | None]
    _uncertainty: dict[str, dict[str, float | None]]

    def __init__(
        self,
        parameters: dict[str, float],
        metrics: dict[str, float | None],
        uncertainty: dict[str, dict[str, float | None]] | None = None,
    ) -> None:
        if not isinstance(parameters, dict) or not isinstance(metrics, dict):
            raise TypeError("regression maps must be dictionaries")
        normalized_parameters = {str(key): float(value) for key, value in parameters.items()}
        normalized_metrics = {
            str(key): None if value is None else float(value) for key, value in metrics.items()
        }
        if any(not math.isfinite(value) for value in normalized_parameters.values()):
            raise ValueError("regression parameters must be finite")
        if any(value is not None and not math.isfinite(value) for value in normalized_metrics.values()):
            raise ValueError("regression metrics must be finite or None")
        object.__setattr__(self, "_parameters", copy.deepcopy(normalized_parameters))
        object.__setattr__(self, "_metrics", copy.deepcopy(normalized_metrics))
        normalized_uncertainty: dict[str, dict[str, float | None]] = {}
        for parameter, values in (uncertainty or {}).items():
            if not isinstance(values, dict):
                raise TypeError("regression uncertainty must be a mapping")
            normalized_values: dict[str, float | None] = {}
            for name, value in values.items():
                numeric = None if value is None else float(value)
                if numeric is not None and not math.isfinite(numeric):
                    raise ValueError("regression uncertainty must be finite or None")
                normalized_values[str(name)] = numeric
            normalized_uncertainty[str(parameter)] = normalized_values
        object.__setattr__(self, "_uncertainty", copy.deepcopy(normalized_uncertainty))

    @property
    def parameters(self) -> dict[str, float]:
        return copy.deepcopy(self._parameters)

    @property
    def metrics(self) -> dict[str, float | None]:
        return copy.deepcopy(self._metrics)

    @property
    def uncertainty(self) -> dict[str, dict[str, float | None]]:
        return copy.deepcopy(self._uncertainty)

    @property
    def fingerprint(self) -> str:
        return _digest({"parameters": self._parameters, "metrics": self._metrics, "uncertainty": self._uncertainty})


class StatsmodelsAdapter:
    """Expose a small OLS seam without making statsmodels a core dependency."""

    package_name = "statsmodels"

    def fit_ols(
        self,
        frame: pd.DataFrame,
        target: str,
        features: Sequence[str],
    ) -> RegressionResult:
        try:
            import statsmodels.api as sm
        except ImportError as exc:
            raise OptionalDependencyError(
                "statsmodels is an optional adapter dependency; install it only in an approved isolated environment"
            ) from exc
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame")
        if not isinstance(target, str) or not target or target not in frame.columns:
            raise ValueError("target column is invalid")
        if not features or any(feature not in frame.columns for feature in features):
            raise ValueError("feature columns are invalid")
        observations = frame[[target, *features]].astype(float).dropna()
        if observations.empty:
            raise ValueError("regression observations are empty")
        design = sm.add_constant(observations[list(features)], has_constant="add")
        fitted = sm.OLS(observations[target], design).fit()
        parameters = {str(key): float(value) for key, value in fitted.params.items()}
        metrics: dict[str, float | None] = {
            "r_squared": float(fitted.rsquared) if pd.notna(fitted.rsquared) else None,
            "aic": float(fitted.aic) if pd.notna(fitted.aic) else None,
            "bic": float(fitted.bic) if pd.notna(fitted.bic) else None,
        }
        uncertainty: dict[str, dict[str, float | None]] = {}
        confidence = fitted.conf_int()
        for name in parameters:
            standard_error = fitted.bse.get(name)
            p_value = fitted.pvalues.get(name)
            interval = confidence.loc[name] if name in confidence.index else None
            uncertainty[name] = {
                "std_error": float(standard_error) if pd.notna(standard_error) else None,
                "p_value": float(p_value) if pd.notna(p_value) else None,
                "ci_low": float(interval.iloc[0]) if interval is not None and pd.notna(interval.iloc[0]) else None,
                "ci_high": float(interval.iloc[1]) if interval is not None and pd.notna(interval.iloc[1]) else None,
            }
        return RegressionResult(parameters=parameters, metrics=metrics, uncertainty=uncertainty)
