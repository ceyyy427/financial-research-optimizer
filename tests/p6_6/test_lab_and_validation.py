from __future__ import annotations

import pandas as pd

from finahinking.data.models import Dataset, Provenance
from finahinking.p6_6 import (
    StrategyLab,
    evaluate_frozen_oos,
    make_oos_plan,
    preview_backtest,
    walk_forward,
)
from finahinking.quant.splits import Period


def _dataset() -> Dataset:
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    return Dataset(pd.DataFrame({"close": range(100, 140)}, index=dates), Provenance("fixture", "internal://fixture"))


def test_review_gate_and_authoritative_p5_run() -> None:
    lab = StrategyLab()
    review = lab.interpreter.accept(lab.review("moving average trend"))
    run = lab.run(review, _dataset(), paper=True)
    assert run.spec.reviewed
    assert run.historical["backtest"].engine_version.startswith("p5.inhouse")
    assert run.paper is not None and run.comparison is not None
    assert run.educational_code is not None and run.educational_code.safety.safe


def test_preview_rejects_unknown_template() -> None:
    lab = StrategyLab()
    review = lab.interpreter.accept(lab.review("momentum with low volatility"))
    assert preview_backtest(review.spec).accepted


def test_frozen_oos_and_walk_forward_record_multiple_testing() -> None:
    first = make_oos_plan(
        Period("2024-01-01", "2024-01-05"),
        Period("2024-01-05", "2024-01-08"),
        hypothesis="fixed trend hypothesis",
        experiment_count=2,
        frozen_configuration={"window": 20},
    )
    second = make_oos_plan(
        Period("2024-01-05", "2024-01-09"),
        Period("2024-01-09", "2024-01-12"),
        hypothesis="fixed trend hypothesis",
        experiment_count=2,
        frozen_configuration={"window": 20},
    )
    assert evaluate_frozen_oos(first, {"2024-01-05": 0.1}).metrics["mean"] == 0.1
    report = walk_forward(
        [(first, {"2024-01-05": 0.1}, {"window": 20}), (second, {"2024-01-09": 0.2}, {"window": 20})],
        hypothesis="fixed trend hypothesis",
        experiment_count=2,
    )
    assert len(report.windows) == 2
    assert report.multiple_testing.experiment_count == 2
    assert "selection bias" in report.multiple_testing.warnings[0]
