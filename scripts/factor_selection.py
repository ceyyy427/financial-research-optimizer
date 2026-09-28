#!/usr/bin/env python3
"""Train-window-only high-dimensional factor screening utilities."""
from __future__ import annotations

import numpy as np


def fisher_screen(features, labels, feature_names=None, max_features=None, epsilon=1e-12):
    """Rank features by between-class / within-class variance.

    This is a challenger selector for p >> n settings.  It is not a complete
    Fisher discriminant classifier: selection must be repeated inside each
    rolling training window, followed by purge/embargo-safe out-of-sample
    evaluation.
    """
    x = np.asarray(features, dtype=float)
    y = np.asarray(labels).reshape(-1)
    if x.ndim != 2 or x.shape[0] < 2 or not np.all(np.isfinite(x)):
        raise ValueError("features must be a finite two-dimensional matrix")
    if y.size != x.shape[0] or np.unique(y).size < 2:
        raise ValueError("labels must have one finite value per row and at least two classes")
    names = list(feature_names or [f"feature_{i}" for i in range(x.shape[1])])
    if len(names) != x.shape[1]:
        raise ValueError("feature_names length must match feature columns")
    overall = x.mean(axis=0)
    between = np.zeros(x.shape[1])
    within = np.zeros(x.shape[1])
    class_counts = {}
    for cls in np.unique(y):
        mask = y == cls
        count = int(mask.sum())
        class_counts[str(cls)] = count
        class_mean = x[mask].mean(axis=0)
        between += count * (class_mean - overall) ** 2
        within += np.square(x[mask] - class_mean).sum(axis=0)
    scores = between / (within + float(epsilon))
    order = np.argsort(-scores, kind="stable")
    limit = x.shape[1] if max_features is None else max(1, min(int(max_features), x.shape[1]))
    selected = [names[index] for index in order[:limit]]
    return {
        "method": "fisher_between_within_score",
        "selected_features": selected,
        "scores": {names[index]: float(scores[index]) for index in order},
        "class_counts": class_counts,
        "sample_size": int(x.shape[0]),
        "feature_count": int(x.shape[1]),
        "status": "ok",
        "selection_scope": "training_window_only",
        "failure_boundary": "p >> n, class imbalance, regime drift, and post-selection leakage",
    }
