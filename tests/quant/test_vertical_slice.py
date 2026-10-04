from pathlib import Path

import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance
from finahinking.experiments.storage import RunStore
from finahinking.quant.interfaces import BacktestConfig
from finahinking.quant.runtime import run_quant_experiment

FIXTURE = Path("fixtures/p5/quant_vertical_slice.csv")


def test_quant_vertical_slice_replays_and_links_research_run(tmp_path):
    frame = pd.read_csv(FIXTURE, parse_dates=["date"], index_col="date")
    dataset = Dataset(frame, Provenance("fixture", "fixture://p5-vertical-slice"))
    config = BacktestConfig(starting_cash=10_000.0, fee_bps=5.0, slippage_bps=10.0)
    first = run_quant_experiment(
        dataset,
        config,
        question="Does trailing momentum support a historical allocation experiment?",
        hypothesis="A positive trailing return receives a long-only target weight.",
        conclusion="The fixture contains descriptive historical evidence only.",
        insight="The result is a reproducible experiment record, not a forecast.",
        run_id="p5-vertical-slice",
    )
    second = run_quant_experiment(
        dataset,
        config,
        question="Does trailing momentum support a historical allocation experiment?",
        hypothesis="A positive trailing return receives a long-only target weight.",
        conclusion="The fixture contains descriptive historical evidence only.",
        insight="The result is a reproducible experiment record, not a forecast.",
        run_id="p5-vertical-slice",
    )
    quant_run, research_run, report, backtest = first
    other_quant_run, other_research_run, other_report, other_backtest = second
    store = RunStore(tmp_path)
    store.save(research_run)
    assert store.load(research_run.run_id) == research_run
    assert quant_run.research_run_id == research_run.run_id
    assert quant_run.result_artifact.fingerprint == other_quant_run.result_artifact.fingerprint
    assert research_run.result_fingerprint == other_research_run.result_fingerprint
    assert report.fingerprint == other_report.fingerprint
    assert backtest.fingerprint == other_backtest.fingerprint
    assert "recommend" not in research_run.to_json().lower()

    provenance = quant_run.result_artifact.payload["provenance"]
    for field in (
        "dataset_version",
        "code_commit",
        "dependency_versions",
        "parameters",
        "engine_version",
        "cost_model",
        "slippage",
        "benchmark",
        "timestamp",
        "timestamp_kind",
        "result_fingerprint",
        "evaluation_fingerprint",
    ):
        assert field in provenance
    assert provenance["dataset_version"] == backtest.dataset_fingerprint
    assert provenance["engine_version"] == backtest.engine_version
    assert research_run.engine_version == backtest.engine_version
    assert provenance["result_fingerprint"] == backtest.fingerprint
    assert provenance["evaluation_fingerprint"] == report.fingerprint
    assert provenance["timestamp_kind"] == "dataset_as_of"
    assert provenance["slippage"] == config.slippage_bps
    assert quant_run.parameters["code_commit"] == provenance["code_commit"]
    assert quant_run.parameters["dependency_versions"] == provenance["dependency_versions"]


def test_quant_runtime_requires_strategy_factor_for_research_provenance():
    class BareStrategy:
        strategy_id = "bare-strategy"
        version = "v1"

        def generate(self, dataset):
            return pd.Series(0.0, index=dataset.frame.index)

    frame = pd.read_csv(FIXTURE, parse_dates=["date"], index_col="date")
    dataset = Dataset(frame, Provenance("fixture", "fixture://p5-vertical-slice"))
    with pytest.raises((TypeError, ValueError), match="factor"):
        run_quant_experiment(
            dataset,
            BacktestConfig(starting_cash=10_000.0, fee_bps=5.0, slippage_bps=10.0),
            question="q",
            hypothesis="h",
            conclusion="c",
            insight="i",
            strategy=BareStrategy(),
            run_id="bare-strategy-run",
        )
