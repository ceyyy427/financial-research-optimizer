"""Lazy statsmodels adapter returning only Finahinking-owned data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from ..interfaces import _digest


class OptionalDependencyError(ImportError):
    """Raised when an optional adapter is used without its approved package."""


@dataclass(frozen=True)
class RegressionResult:
    """Normalized regression evidence; never stores a statsmodels model."""

    parameters: dict[str, float]
    metrics: dict[str, float | None]

    @property
    def fingerprint(self) -> str:
        return _digest({"parameters": self.parameters, "metrics": self.metrics})


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
        return RegressionResult(parameters=parameters, metrics=metrics)
