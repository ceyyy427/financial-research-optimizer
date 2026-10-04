import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance
from finahinking.experiments.engine import ExperimentEngine, ReproducibilityError
from finahinking.factors.core import momentum_factor


def dataset() -> Dataset:
    prices = pd.Series(
        [100, 101, 103, 106, 110, 115, 121],
        index=pd.date_range("2024-01-01", periods=7),
        name="close",
    )
    return Dataset(prices.to_frame(), Provenance("ecb", "fixture://prices"))


def test_engine_executes_complete_research_run():
    run = ExperimentEngine().execute(
        question="Does momentum relate to future returns?",
        hypothesis="Positive momentum is associated with positive future returns.",
        dataset=dataset(),
        factor=momentum_factor(2),
        horizon=1,
        conclusion="The sample supports a positive association.",
        insight="This is descriptive evidence only.",
    )
    assert run.method == "information_coefficient"
    assert run.factor_name == "momentum_2d"
    assert run.result["coverage"] > 0
    assert run.dataset_fingerprint


def test_engine_reproduction_detects_dataset_drift():
    engine = ExperimentEngine()
    original = dataset()
    run = engine.execute("q", "h", original, momentum_factor(2), 1, "c", "i")
    changed = Dataset(original.frame.assign(close=lambda frame: frame["close"] + 1), original.provenance)
    with pytest.raises(ReproducibilityError, match="dataset"):
        engine.reproduce(run, changed, momentum_factor(2))


def test_engine_rejects_nonpositive_horizon():
    with pytest.raises(ValueError, match="horizon"):
        ExperimentEngine().execute("q", "h", dataset(), momentum_factor(2), 0, "c", "i")
