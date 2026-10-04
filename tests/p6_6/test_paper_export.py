from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance
from finahinking.p6_6.diagnostics import compare_backtest_paper, feature_drift
from finahinking.p6_6.education import generate_educational_code, scan_educational_code
from finahinking.p6_6.export import ResearchPackageExporter
from finahinking.p6_6.learning import strategy_learning_bundle
from finahinking.p6_6.paper import PaperSimulator
from finahinking.quant.engines.backtest import BacktestEngine
from finahinking.quant.interfaces import BacktestConfig


class ConstantStrategy:
    strategy_id = "constant_long"
    version = "v1"

    def generate(self, dataset: Dataset) -> pd.Series:
        return pd.Series(0.5, index=dataset.frame.index)


def fixture() -> Dataset:
    dates = pd.date_range("2024-01-01", periods=8, freq="D")
    return Dataset(pd.DataFrame({"close": [100, 101, 99, 103, 104, 102, 106, 107]}, index=dates), Provenance("test", "internal://fixture"))


def config() -> BacktestConfig:
    return BacktestConfig(starting_cash=10_000.0, fee_bps=5.0, slippage_bps=5.0)


def test_paper_reuses_cost_semantics_and_is_reproducible() -> None:
    dataset = fixture()
    strategy = ConstantStrategy()
    one = PaperSimulator().run(dataset, strategy, config())
    two = PaperSimulator().run(dataset, strategy, config())
    assert one.fingerprint == two.fingerprint
    assert one.fills
    assert one.fills[0].fees > 0
    assert "broker" not in one.to_dict()
    historical = BacktestEngine().run(dataset, strategy, config())
    comparison = compare_backtest_paper(historical, one)
    assert comparison.aligned_points == len(dataset.frame)


def test_feature_drift_reports_ranked_metrics() -> None:
    baseline = pd.DataFrame({"momentum": [1.0, 1.0, 1.0], "volatility": [0.1, 0.1, 0.1]})
    current = pd.DataFrame({"momentum": [2.0, 2.1, 1.9], "volatility": [0.1, 0.2, 0.3]})
    report = feature_drift(baseline, current, threshold=0.2)
    assert report.drift_detected
    assert report.ranked_features[0] == "momentum"
    assert report.fingerprint


def test_learning_bundle_has_predict_reveal_explain_and_trace() -> None:
    bundle = strategy_learning_bundle({"strategy_id": "constant_long", "version": "v1"}, evidence_reference="run-1")
    assert bundle.cards
    assert bundle.interactions[0].events == ("PREDICT", "REVEAL", "EXPLAIN")
    assert bundle.traces[0].code_explanation


def test_educational_code_is_static_and_rejects_unsafe_source() -> None:
    from finahinking.p6_6.compiler import strategy_ir
    from finahinking.p6_6.strategy import review_strategy

    review = review_strategy("moving average trend")
    spec = review.accept().spec
    source = generate_educational_code(spec, strategy_ir(spec)).source
    assert scan_educational_code(source)["safe"]
    assert not scan_educational_code("import os\nopen('x', 'w')")["safe"]


def test_export_has_fixed_layout_and_rejects_sensitive_payload(tmp_path: Path) -> None:
    package = ResearchPackageExporter().export(tmp_path, strategy_spec={"strategy_id": "constant_long", "version": "v1"}, feature_graph={"fingerprint": "a" * 64}, config={"fee_bps": 5}, research_report={"status": "historical"}, provenance={"commit": "abc"})
    root = Path(package.root)
    assert set(package.files) >= set(ResearchPackageExporter.required_files)
    assert (root / "provenance.json").exists()
    assert package.package_fingerprint
    with pytest.raises(ValueError, match="sensitive"):
        ResearchPackageExporter().export(tmp_path, strategy_spec={"strategy_id": "x", "api_key": "secret"})
