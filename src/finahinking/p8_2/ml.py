"""Finathink-native deterministic ML research fallback helpers."""

from __future__ import annotations

from typing import Any

from .contracts import DatasetSnapshot, MLResearchResult, MLResearchSpecification, ModelMetric


def _scope_label(scope: Any) -> str:
    if isinstance(scope, dict):
        start = scope.get("start", "")
        end = scope.get("end", "")
        return f"{start}|{end}"
    return str(scope or "unspecified")


def run_deterministic_baseline(spec: MLResearchSpecification, dataset: DatasetSnapshot) -> MLResearchResult:
    """Run a transparent mean/last-value baseline without optional packages."""

    if dataset.fingerprint != spec.dataset_fingerprint:
        raise ValueError("ML dataset fingerprint does not match specification")
    observations = dataset.observations
    if not observations:
        raise ValueError("ML dataset cannot be empty")
    mean_close = sum(item.close for item in observations) / len(observations)
    predictions = tuple(
        {
            "instrument": item.instrument,
            "timestamp": item.timestamp.isoformat(),
            "split": "test",
            "target": item.close,
            "prediction": mean_close,
        }
        for item in observations
    )
    mae = sum(abs(item["target"] - item["prediction"]) for item in predictions) / len(predictions)
    rmse = (sum((item["target"] - item["prediction"]) ** 2 for item in predictions) / len(predictions)) ** 0.5
    metrics = (
        ModelMetric("mae", mae, "test", "Average absolute error against the declared target."),
        ModelMetric("rmse", rmse, "test", "Root mean squared error; scale-dependent."),
    )
    return MLResearchResult(
        specification_fingerprint=spec.fingerprint,
        dataset_fingerprint=dataset.fingerprint,
        status="FALLBACK",
        engine="finathink-deterministic-baseline",
        metrics=metrics,
        predictions=predictions,
        feature_importance={feature: 0.0 for feature in spec.features},
        limitations=(
            "This is a deterministic baseline, not evidence that a model predicts future returns.",
            f"Declared train/validation/test scopes: {_scope_label(spec.train_scope)} / {_scope_label(spec.validation_scope)} / {_scope_label(spec.test_scope)}.",
            "The fixture target is close price; leakage and target construction must be reviewed for production research.",
        ),
        fallback_used=True,
        model_artifact={"kind": "baseline", "mean_target": mean_close},
    )


__all__ = ["run_deterministic_baseline"]
