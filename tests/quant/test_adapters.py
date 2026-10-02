import importlib
import sys

import pandas as pd
import pytest

from finahinking.quant.adapters.statsmodels_adapter import (
    OptionalDependencyError,
    StatsmodelsAdapter,
)


def test_core_quant_imports_do_not_load_optional_packages():
    for module_name in ("statsmodels", "pypfopt", "alphalens", "pyfolio", "quantstats", "vectorbt"):
        assert module_name not in sys.modules
    importlib.import_module("finahinking.quant.interfaces")
    importlib.import_module("finahinking.quant.engines.backtest")
    for module_name in ("statsmodels", "pypfopt", "alphalens", "pyfolio", "quantstats", "vectorbt"):
        assert module_name not in sys.modules


def test_statsmodels_adapter_reports_optional_dependency_without_returning_foreign_objects():
    if importlib.util.find_spec("statsmodels") is not None:
        pytest.skip("statsmodels is installed in this environment; absence behavior is not applicable")
    with pytest.raises(OptionalDependencyError, match="optional"):
        StatsmodelsAdapter().fit_ols(pd.DataFrame({"x": [1.0, 2.0], "y": [1.0, 2.0]}), "y", ["x"])
