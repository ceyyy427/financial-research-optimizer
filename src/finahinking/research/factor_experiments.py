"""Bounded, paper-only factor parameter experiments.

This module is deliberately a thin orchestration layer over the existing
``evaluate_factor_candidate`` evaluator.  It expands a finite parameter grid,
evaluates each point on the validation/PIT phase, and keeps the OOS boundary
explicit.  No experiment result is an execution or trading recommendation.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from finahinking.factors.evaluation import FactorEvaluation, evaluate_factor_candidate
from finahinking.factors.mining import FactorCandidate

from .factor_pipeline import _dataset_digest


def _jsonable(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _digest(value: Any) -> str:
    encoded = json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class FactorExperimentSpec:
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]]
    max_experiments: int = 20
    split: Mapping[str, float] | None = None
    decay_horizons: tuple[int, ...] = (1, 5, 20)

    def __post_init__(self) -> None:
        if isinstance(self.max_experiments, bool) or not isinstance(self.max_experiments, int) or not 1 <= self.max_experiments <= 256:
            raise ValueError("max_experiments must be between 1 and 256")
        split = dict(self.split or {"train": 0.6, "validation": 0.2, "test": 0.2})
        if set(split) != {"train", "validation", "test"} or any(float(value) <= 0 for value in split.values()) or abs(sum(float(value) for value in split.values()) - 1.0) > 1e-9:
            raise ValueError("split must contain positive train, validation and test ratios summing to one")
        horizons = tuple(self.decay_horizons)
        if not horizons or any(isinstance(item, bool) or int(item) != item or int(item) < 1 for item in horizons):
            raise ValueError("decay_horizons must contain positive integers")
        object.__setattr__(self, "split", {key: float(split[key]) for key in ("train", "validation", "test")})
        object.__setattr__(self, "decay_horizons", tuple(int(item) for item in horizons))

    def to_dict(self) -> dict[str, Any]:
        return {"parameters": _jsonable(self.parameters), "max_experiments": self.max_experiments, "split": dict(self.split or {}), "decay_horizons": list(self.decay_horizons)}


@dataclass(frozen=True, slots=True)
class FactorExperimentRecord:
    experiment_id: str
    parameters: Mapping[str, Any]
    evaluation: FactorEvaluation
    digest: str
    dataset_fingerprint: str
    config_digest: str
    research_fingerprint: str
    split: Mapping[str, float]
    limitations: tuple[str, ...]

    @property
    def ic(self) -> float | None:
        return self.evaluation.information_coefficient

    @property
    def ir(self) -> float | None:
        return self.evaluation.information_ratio

    @property
    def turnover(self) -> float | None:
        return self.evaluation.turnover

    @property
    def decay(self) -> Mapping[str, float | None]:
        return {str(horizon): value for horizon, value in zip(self.evaluation.decay.horizons, self.evaluation.decay.information_coefficients)}

    def to_dict(self) -> dict[str, Any]:
        return {"experiment_id": self.experiment_id, "parameters": _jsonable(self.parameters), "evaluation": self.evaluation.to_dict(), "digest": self.digest, "dataset_fingerprint": self.dataset_fingerprint, "config_digest": self.config_digest, "research_fingerprint": self.research_fingerprint, "split": dict(self.split), "ic": self.ic, "ir": self.ir, "turnover": self.turnover, "decay": dict(self.decay), "limitations": list(self.limitations), "paper_only": True}


@dataclass(frozen=True, slots=True)
class FactorExperimentResult:
    experiments: tuple[FactorExperimentRecord, ...]
    ranking: tuple[str, ...]
    experiment_digest: str
    dataset_fingerprint: str
    config_digest: str
    research_fingerprint: str
    split: Mapping[str, float]
    limitations: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        return self.experiment_digest

    def to_dict(self) -> dict[str, Any]:
        return {"experiments": [item.to_dict() for item in self.experiments], "ranking": list(self.ranking), "experiment_digest": self.experiment_digest, "dataset_fingerprint": self.dataset_fingerprint, "config_digest": self.config_digest, "research_fingerprint": self.research_fingerprint, "split": dict(self.split), "limitations": list(self.limitations), "paper_only": True}

    def comparison_payload(self) -> dict[str, Any]:
        return {"schema_version": 1, "paper_only": True, "runs": [{"run_id": item.experiment_id, "inputs": {"parameters": _jsonable(item.parameters), "dataset_fingerprint": item.dataset_fingerprint, "config_digest": item.config_digest, "research_fingerprint": item.research_fingerprint}, "metrics": {"ic": item.ic, "ir": item.ir, "turnover": item.turnover, "decay": dict(item.decay)}, "limitations": list(item.limitations)} for item in self.experiments]}

    @property
    def comparison(self) -> dict[str, Any]:
        """Server-owned descriptive payload suitable for ``compare_experiments``."""

        return self.comparison_payload()


def _grid(parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    if isinstance(parameters, Mapping):
        names = tuple(sorted(str(name) for name in parameters))
        axes = []
        for name in names:
            value = parameters[name]
            axes.append(tuple(value) if isinstance(value, (list, tuple, set, frozenset)) else (value,))
        return tuple(dict(zip(names, values)) for values in itertools.product(*axes))
    if isinstance(parameters, Sequence) and not isinstance(parameters, (str, bytes)):
        if not all(isinstance(item, Mapping) for item in parameters):
            raise TypeError("parameter sequence must contain mappings")
        return tuple(dict(item) for item in parameters)
    raise TypeError("parameters must be a mapping or sequence of mappings")


def _candidate_for(parameters: Mapping[str, Any], dataset: Mapping[str, Any], index: int) -> FactorCandidate:
    raw = parameters.get("expression", parameters.get("factor"))
    if raw is None:
        candidates = dataset.get("candidates", ())
        if candidates and isinstance(candidates, Sequence):
            candidate = candidates[index % len(candidates)]
            if isinstance(candidate, FactorCandidate):
                return candidate
            if isinstance(candidate, Mapping):
                raw = candidate.get("expression")
        raw = raw or "rank(close)"
    expression = str(raw).format(**dict(parameters))
    return FactorCandidate(f"experiment-{index:04d}", expression, "bounded parameter experiment", "factor-experiment", dict(parameters))


def run_factor_experiments(spec: FactorExperimentSpec, dataset: Mapping[str, Any], config: Mapping[str, Any] | None = None) -> FactorExperimentResult:
    if not isinstance(spec, FactorExperimentSpec):
        raise TypeError("spec must be FactorExperimentSpec")
    if not isinstance(dataset, Mapping):
        raise TypeError("dataset must be a mapping")
    frame, forward = dataset.get("frame"), dataset.get("forward_return")
    if not isinstance(frame, pd.DataFrame) or not isinstance(forward, pd.Series):
        raise TypeError("dataset requires frame and forward_return")
    if not frame.index.equals(forward.index):
        raise ValueError("forward_return must use the same index as frame")
    dataset_fingerprint = _dataset_digest(dataset)
    config_payload = dict(config or dataset.get("config", {}))
    config_digest = _digest(config_payload)
    research_fingerprint = _digest({"dataset_fingerprint": dataset_fingerprint, "config_digest": config_digest, "spec": spec.to_dict()})
    grid = _grid(spec.parameters)
    if len(grid) > spec.max_experiments:
        grid = grid[: spec.max_experiments]
    if not grid:
        raise ValueError("parameter grid must contain at least one experiment")
    records: list[FactorExperimentRecord] = []
    for index, parameters in enumerate(grid, start=1):
        candidate = _candidate_for(parameters, dataset, index)
        evaluation_spec = {**config_payload, "phase": "validation", "oos": False, "train_ratio": spec.split["train"], "validation_ratio": spec.split["validation"], "decay_horizons": spec.decay_horizons, "shift_periods": int(config_payload.get("shift_periods", 1)), "evaluation_start": frame.index[int(len(frame) * spec.split["train"])], "evaluation_end": frame.index[max(int(len(frame) * (spec.split["train"] + spec.split["validation"])) - 2, 0)], "min_samples": int(config_payload.get("min_samples", 8))}
        evaluation = evaluate_factor_candidate(candidate, frame, forward, evaluation_spec)
        digest = _digest({"parameters": parameters, "evaluation": evaluation.to_dict(), "dataset_fingerprint": dataset_fingerprint, "config_digest": config_digest, "research_fingerprint": research_fingerprint})
        limitations = tuple(dict.fromkeys((*evaluation.warnings, "OOS/test evidence remains hidden until an explicit frozen test evaluation", "paper-only descriptive factor diagnostics; no trade advice")))
        records.append(FactorExperimentRecord(f"experiment-{index:04d}", parameters, evaluation, digest, dataset_fingerprint, config_digest, research_fingerprint, spec.split, limitations))
    def score(item: FactorExperimentRecord) -> tuple[float, str]:
        value = (abs(item.ic or 0.0) + 0.1 * (item.ir or 0.0) + 0.1 * sum(v for v in item.decay.values() if v is not None) - 0.1 * (item.turnover or 0.0))
        return (-value, item.digest)
    ranking = tuple(item.experiment_id for item in sorted(records, key=score))
    result_digest = _digest({"experiments": [item.digest for item in records], "ranking": ranking, "dataset_fingerprint": dataset_fingerprint, "config_digest": config_digest, "research_fingerprint": research_fingerprint})
    return FactorExperimentResult(tuple(records), ranking, result_digest, dataset_fingerprint, config_digest, research_fingerprint, spec.split, ("bounded parameter grid", "PIT T+1 timing", "OOS/test remains gated", "paper-only; no trade advice"))


__all__ = ["FactorExperimentRecord", "FactorExperimentResult", "FactorExperimentSpec", "run_factor_experiments"]
