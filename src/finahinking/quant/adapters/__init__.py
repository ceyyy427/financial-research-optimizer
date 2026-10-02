"""Optional third-party adapters; importing this package installs nothing."""

from .statsmodels_adapter import OptionalDependencyError, RegressionResult, StatsmodelsAdapter

__all__ = ["OptionalDependencyError", "RegressionResult", "StatsmodelsAdapter"]
