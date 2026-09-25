#!/usr/bin/env python3
"""Leakage-safe expanding/rolling window construction from one config."""


def build_windows(n_rows, config):
    evaluation = config["evaluation"]
    train = evaluation["train_period"]
    validation = evaluation["validation_period"]
    test = evaluation["test_period"]
    step = evaluation.get("step_size", test)
    gap = evaluation.get("purge_gap", 0) + evaluation.get("embargo_period", 0)
    windows = []
    origin = train + validation + gap
    while origin + test <= n_rows:
        windows.append({
            "train": (0, origin - validation - gap) if evaluation["method"] == "expanding_window" else (max(0, origin - validation - gap - train), origin - validation - gap),
            "validation": (origin - validation - gap, origin - gap),
            "test": (origin, origin + test),
        })
        origin += step
    return windows
