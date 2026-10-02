import json

import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance
from finahinking.experiments.models import ResearchRun
from finahinking.factors.core import momentum_factor


def dataset() -> Dataset:
    frame = pd.DataFrame(
        {"close": [100.0, 101.0, 103.0]},
        index=pd.date_range("2024-01-01", periods=3),
    )
    return Dataset(frame, Provenance("ecb", "fixture://prices"))


def test_research_run_round_trips_as_canonical_json():
    run = ResearchRun.create(
        question="Does momentum relate to forward returns?",
        hypothesis="Positive momentum has positive future returns.",
        dataset=dataset(),
        factor=momentum_factor(2),
        method="information_coefficient",
        parameters={"horizon": 1},
        result={"coverage": 0.5, "information_coefficient": None},
        conclusion="Insufficient observations.",
        insight="The fixture is too short.",
        limitations=["Small sample"],
        run_id="run-test-1",
        created_at="2026-10-02T00:00:00+00:00",
    )
    encoded = run.to_json()
    assert json.loads(encoded)["run_id"] == "run-test-1"
    assert ResearchRun.from_json(encoded) == run
    assert run.result_fingerprint == ResearchRun.from_json(encoded).result_fingerprint


def test_research_run_rejects_invalid_required_fields():
    with pytest.raises(ValueError, match="question"):
        ResearchRun.create(
            question="",
            hypothesis="h",
            dataset=dataset(),
            factor=momentum_factor(2),
            method="information_coefficient",
            parameters={"horizon": 1},
            result={},
            conclusion="c",
            insight="i",
            limitations=[],
        )


def test_research_run_rejects_tampered_dataset_fingerprint():
    run = ResearchRun.create(
        question="q", hypothesis="h", dataset=dataset(), factor=momentum_factor(2),
        method="information_coefficient", parameters={"horizon": 1}, result={},
        conclusion="c", insight="i", limitations=[], run_id="tamper-test",
    )
    payload = run.to_dict()
    payload["dataset"]["records"][0]["close"] = 999.0
    with pytest.raises(ValueError, match="dataset fingerprint"):
        ResearchRun.from_dict(payload)
