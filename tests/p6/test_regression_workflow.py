import importlib.util
import os
import subprocess
import sys

import pytest


def test_regression_learning_workflow_is_linked_and_grounded() -> None:
    if importlib.util.find_spec("statsmodels") is None:
        pytest.skip("statsmodels is not available in the isolated adapter environment")
    script = """
import pandas as pd
from finahinking.p6.workflows import GuidedResearchService
frame = pd.DataFrame({
    'date': pd.date_range('2020-01-01', periods=8),
    'asset_return': [0.0, 0.01, 0.02, -0.01, 0.015, 0.0, 0.01, 0.02],
    'market_return': [0.0, 0.005, 0.01, -0.005, 0.0075, 0.0, 0.005, 0.01],
})
result = GuidedResearchService().run_regression(
    'u1', 'How sensitive was this asset to the market?', frame,
    target='asset_return', features=('market_return',),
)
assert result.tool_response.quant_run_id
assert result.explanation.claims
assert result.learning_card.evidence_reference == result.tool_response.quant_run_id
assert result.tool_response.result['uncertainty']
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, ("src", env.get("PYTHONPATH", ""))))
    completed = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
