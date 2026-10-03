import importlib
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from finahinking.quant.adapters.statsmodels_adapter import (
    OptionalDependencyError,
    RegressionResult,
    StatsmodelsAdapter,
)


def test_core_quant_imports_do_not_load_optional_packages():
    # Run this import-boundary check in a fresh interpreter.  Other quant
    # tests may legitimately exercise the optional statsmodels adapter first;
    # inspecting the parent interpreter would make the contract order
    # dependent rather than testing the core import boundary itself.
    code = """
import importlib
import sys
optional = ("statsmodels", "pypfopt", "alphalens", "pyfolio", "quantstats", "vectorbt")
assert all(name not in sys.modules for name in optional)
importlib.import_module("finahinking.quant.interfaces")
importlib.import_module("finahinking.quant.engines.backtest")
assert all(name not in sys.modules for name in optional)
"""
    env = os.environ.copy()
    source_root = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONPATH"] = source_root + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr or result.stdout


def test_statsmodels_adapter_reports_optional_dependency_without_returning_foreign_objects():
    if importlib.util.find_spec("statsmodels") is not None:
        pytest.skip("statsmodels is installed in this environment; absence behavior is not applicable")
    with pytest.raises(OptionalDependencyError, match="optional"):
        StatsmodelsAdapter().fit_ols(pd.DataFrame({"x": [1.0, 2.0], "y": [1.0, 2.0]}), "y", ["x"])


def test_regression_result_defensively_copies_parameter_and_metric_maps():
    result = RegressionResult(parameters={"x": 1.0}, metrics={"r_squared": 0.5})
    parameters = result.parameters
    metrics = result.metrics
    parameters["x"] = 99.0
    metrics["r_squared"] = 99.0
    assert result.parameters["x"] == 1.0
    assert result.metrics["r_squared"] == 0.5


def test_regression_result_rejects_non_finite_values():
    with pytest.raises(ValueError, match="finite"):
        RegressionResult(parameters={"x": float("nan")}, metrics={"r_squared": 0.5})
    with pytest.raises(ValueError, match="finite"):
        RegressionResult(parameters={"x": 1.0}, metrics={"r_squared": float("inf")})
