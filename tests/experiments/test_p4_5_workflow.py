from pathlib import Path

import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance
from finahinking.experiments.engine import ExperimentEngine
from finahinking.experiments.storage import RunStore
from finahinking.factors.core import FactorDefinition
from finahinking.features.core import returns, volatility

FIXTURE = Path("fixtures/p4_5/volatility_workflow.csv")


def volatility_factor() -> FactorDefinition:
    return FactorDefinition(
        name="volatility_3d",
        definition="Rolling standard deviation of one-period returns over 3 observations.",
        explanation="Describes recent return dispersion.",
        limitations="Descriptive only; one-period lag; small sample; no costs or causal claim.",
        compute=lambda prices: volatility(returns(prices), window=3, annualization=1.0),
    )


def test_p4_5_volatility_workflow_round_trips_and_reproduces(tmp_path):
    frame = pd.read_csv(FIXTURE, parse_dates=["date"], index_col="date")
    dataset = Dataset(frame, Provenance("fixture", "fixture://volatility-workflow"))
    run = ExperimentEngine().execute(
        question="Does volatility predict future returns?",
        hypothesis="Higher recent volatility is associated with different next-period returns.",
        dataset=dataset,
        factor=volatility_factor(),
        horizon=1,
        conclusion="The fixture provides descriptive association only.",
        insight="A larger sample and out-of-sample design are required.",
        run_id="volatility-workflow",
        created_at="2026-10-02T00:00:00+00:00",
    )
    store = RunStore(tmp_path)
    store.save(run)

    loaded = store.load(run.run_id)
    reproduced = ExperimentEngine().reproduce(loaded, dataset, volatility_factor())

    assert loaded == run
    assert run.result["coverage"] == 7 / 12
    assert run.result["information_coefficient"] == pytest.approx(0.09026243397759831)
    assert run.dataset_fingerprint == "fe468014d020fbb3f59dd8b39a7b3edf8a45dab2ae414e5694ac16eab3df0a0a"
    assert run.result_fingerprint == "194a08937431f0819d95a0dc2dad83c09021009f443f0c29f5c69c542b93bea4"
    assert reproduced.result_fingerprint == run.result_fingerprint
