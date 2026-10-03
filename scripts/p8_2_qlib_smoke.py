#!/usr/bin/env python3
"""Run a tiny, isolated Qlib/LightGBM compatibility smoke.

This script is deliberately not part of the core runtime.  It exercises the
Qlib model seam with an in-memory DatasetH-shaped fixture, then emits scalar
metrics only.  No Qlib model/data objects cross into Finathink contracts.
"""

from __future__ import annotations

import json


def main() -> int:
    # These imports intentionally live inside the smoke so the core process
    # never imports optional Qlib dependencies.
    import lightgbm
    import numpy as np
    import pandas as pd
    import qlib
    from qlib.contrib.model.gbdt import LGBModel

    # Import/init compatibility is the first gate.  Qlib's data provider is
    # intentionally not initialized: this smoke never reaches external data.
    qlib_version = getattr(qlib, "__version__", "unknown")
    rows = {
        "train": (0.0, 1.0, 2.0, 3.0),
        "valid": (4.0, 5.0),
        "test": (6.0, 7.0),
    }

    class TinyDataset:
        def __init__(self) -> None:
            self.segments = {
                "train": ("train", "train"),
                "valid": ("valid", "valid"),
                "test": ("test", "test"),
            }

        def prepare(self, segment, col_set=None, data_key=None):
            values = rows[segment]
            features = np.asarray(values, dtype=float).reshape(-1, 1)
            labels = features[:, 0] * 0.5 + 1.0
            if col_set == ["feature", "label"]:
                columns = pd.MultiIndex.from_tuples([("feature", "x"), ("label", "y")])
                return pd.DataFrame(np.column_stack([features[:, 0], labels]), columns=columns)
            return pd.DataFrame(features, columns=["x"])

    dataset = TinyDataset()
    model = LGBModel(
        num_boost_round=5,
        early_stopping_rounds=2,
        learning_rate=0.1,
        num_leaves=7,
        min_data_in_leaf=1,
    )
    # Qlib's workflow logger expects an active recorder.  The model training
    # itself is what this isolated smoke checks, so keep the logger inert.
    import qlib.workflow

    qlib.workflow.R.log_metrics = lambda **kwargs: None
    model.fit(dataset, verbose_eval=-1)
    prediction = model.predict(dataset, "test")
    values = [float(value) for value in prediction.tolist()]
    mae = sum(abs((row * 0.5 + 1.0) - predicted) for row, predicted in zip(rows["test"], values)) / len(values)
    result = {
        "status": "PASS",
        "qlib_version": qlib_version,
        "lightgbm_version": lightgbm.__version__,
        "train_rows": len(rows["train"]),
        "test_rows": len(rows["test"]),
        "oos_mae": mae,
        "raw_objects_returned": False,
        "provider_initialized": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
