"""Deterministic long-only portfolio construction for paper research."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .contracts import stable_digest
from .risk_runtime import RiskReviewResult

_FORBIDDEN = {"broker", "order", "cancel", "account", "live", "endpoint", "credential", "secret"}


def _safe(value: Any, path: str = "value") -> Any:
    if callable(value):
        raise TypeError(f"{path} contains a forbidden executable value")
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for key, child in value.items():
            name = str(key)
            if any(token in name.casefold() for token in _FORBIDDEN):
                raise ValueError(f"{path} contains a forbidden paper-only field")
            output[name] = _safe(child, f"{path}.{name}")
        return output
    if isinstance(value, (tuple, list)):
        return [_safe(item, f"{path}[]") for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        return value
    return value


def _number(value: Any, label: str, *, default: float | None = None) -> float:
    if value is None and default is not None:
        return default
    if isinstance(value, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return _safe(value, label)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if isinstance(result, Mapping):
            return _safe(result, label)
    # Small typed test doubles may expose only the public result attributes.
    # Read this closed allow-list rather than serializing arbitrary objects.
    if not isinstance(value, (str, bytes, int, float, bool)):
        known = {name: getattr(value, name) for name in ("passed", "status", "blocking_reasons", "fingerprint", "risk_digest") if hasattr(value, name)}
        if known:
            return _safe(known, label)
    raise TypeError(f"{label} must be a structured result")


@dataclass(frozen=True, slots=True)
class PaperPortfolioProposal:
    status: str = "BLOCKED"
    passed: bool = False
    weights: Mapping[str, float] = field(default_factory=dict)
    cash_weight: float = 1.0
    candidates: tuple[str, ...] = ()
    risk_digest: str = ""
    constraints: Mapping[str, Any] = field(default_factory=dict)
    rationale: str = ""
    paper_only: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool):
            raise TypeError("passed must be boolean")
        status = str(self.status).strip().upper()
        object.__setattr__(self, "status", "PASSED" if self.passed else ("BLOCKED" if status == "PASSED" else status))
        normalized: dict[str, float] = {}
        for instrument, weight in dict(self.weights).items():
            name = str(instrument).strip()
            if not name or any(token in name.casefold() for token in _FORBIDDEN):
                raise ValueError("instrument is invalid for paper-only portfolio")
            value = _number(weight, f"weights.{name}")
            if value < -1e-12:
                raise ValueError("portfolio weights must be long-only")
            normalized[name] = max(0.0, value)
        object.__setattr__(self, "weights", {key: normalized[key] for key in sorted(normalized)})
        object.__setattr__(self, "cash_weight", _number(self.cash_weight, "cash_weight"))
        if self.cash_weight < -1e-12:
            raise ValueError("cash weight must be non-negative")
        object.__setattr__(self, "candidates", tuple(str(item) for item in self.candidates))
        object.__setattr__(self, "constraints", dict(self.constraints))
        object.__setattr__(self, "rationale", str(self.rationale))
        if self.paper_only is not True:
            raise ValueError("portfolio proposal must be paper-only")
        if sum(self.weights.values()) + self.cash_weight > 1.0 + 1e-9:
            raise ValueError("portfolio exposure exceeds one")

    @property
    def fingerprint(self) -> str:
        return stable_digest(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "weights": dict(self.weights),
            "cash_weight": self.cash_weight,
            "candidates": list(self.candidates),
            "risk_digest": self.risk_digest,
            "constraints": dict(self.constraints),
            "rationale": self.rationale,
            "paper_only": self.paper_only,
            "fingerprint": self.fingerprint,
        }


class PortfolioManager:
    """Construct a transparent equal-weight paper portfolio after risk gates."""

    def construct(self, risk_result: RiskReviewResult | Mapping[str, Any], candidates: Sequence[Any] | Mapping[str, Any], constraints: Mapping[str, Any] | Any) -> PaperPortfolioProposal:
        if not isinstance(risk_result, RiskReviewResult):
            raise TypeError("risk_result must be a RiskReviewResult")
        risk = risk_result.to_dict()
        policy = _mapping(constraints, "constraints")
        if policy.get("long_only", True) is not True:
            raise ValueError("portfolio runtime is long-only")
        if risk_result.blocking_reasons:
            return PaperPortfolioProposal(
                status="BLOCKED",
                passed=False,
                risk_digest=risk_result.fingerprint,
                constraints=policy,
                rationale="risk gate blocked portfolio: " + "; ".join(risk_result.blocking_reasons),
            )
        if risk.get("passed") is not True and str(risk.get("status", "")).upper() != "PASSED":
            reasons = tuple(str(item) for item in risk.get("blocking_reasons", ()))
            return PaperPortfolioProposal(status="BLOCKED", passed=False, candidates=(), risk_digest=str(risk.get("fingerprint", "")), constraints=policy, rationale="risk gate blocked portfolio: " + "; ".join(reasons))

        extracted: list[tuple[str, float | None]] = []
        if isinstance(candidates, Mapping):
            source = tuple(candidates.items())
            for instrument, weight in source:
                value = _number(weight, f"candidate.{instrument}")
                if not 0 <= value <= 1:
                    raise ValueError("candidate weight is outside long-only bounds")
                extracted.append((str(instrument), value))
        elif isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
            raise TypeError("candidates must be a sequence or mapping")
        else:
            for item in candidates:
                if isinstance(item, str):
                    extracted.append((item, None))
                elif isinstance(item, Mapping):
                    instrument = item.get("instrument", item.get("symbol", item.get("id")))
                    if instrument is None:
                        raise ValueError("candidate instrument is required")
                    score = item.get("score", item.get("rank_score"))
                    extracted.append((str(instrument), None if score is None else _number(score, "candidate.score")))
                else:
                    instrument = getattr(item, "instrument", getattr(item, "symbol", None))
                    if instrument is None:
                        raise TypeError("candidates must be normalized records")
                    score = getattr(item, "score", None)
                    extracted.append((str(instrument), None if score is None else _number(score, "candidate.score")))
        names = sorted({name.strip() for name, _ in extracted if name.strip()})
        if not names:
            return PaperPortfolioProposal(status="BLOCKED", passed=False, risk_digest=str(risk.get("fingerprint", "")), constraints=policy, rationale="no candidates")
        if any(any(token in name.casefold() for token in _FORBIDDEN) for name in names):
            raise ValueError("candidate contains forbidden paper-only execution field")
        max_single = _number(policy.get("max_single_weight", policy.get("max_weight", 1.0)), "max_single_weight")
        max_exposure = _number(policy.get("max_exposure", 1.0), "max_exposure")
        cash_buffer = _number(policy.get("cash_buffer", 0.0), "cash_buffer")
        risk_max_concentration = risk_result.limits.get("max_concentration", risk_result.limits.get("concentration_limit"))
        if risk_max_concentration is None:
            risk_max_concentration = risk_result.metrics.get("max_concentration_limit")
        if risk_max_concentration is not None:
            risk_limit = _number(risk_max_concentration, "risk.max_concentration")
            observed = risk_result.metrics.get("concentration")
            if isinstance(observed, (int, float)) and float(observed) > risk_limit + 1e-12:
                return PaperPortfolioProposal(
                    status="BLOCKED",
                    passed=False,
                    risk_digest=risk_result.fingerprint,
                    constraints=policy,
                    rationale="risk concentration gate failed",
                )
            max_single = min(max_single, risk_limit)
        if not 0 <= max_single <= 1 or not 0 <= max_exposure <= 1 or not 0 <= cash_buffer <= 1:
            raise ValueError("portfolio constraints must be between zero and one")
        max_exposure = min(max_exposure, 1.0 - cash_buffer)
        target_exposure = min(max_exposure, 1.0 - cash_buffer)
        share = min(max_single, target_exposure / len(names))
        weights = {name: share for name in names}
        used = share * len(names)
        return PaperPortfolioProposal(
            status="PASSED",
            passed=True,
            weights=weights,
            cash_weight=max(0.0, 1.0 - used),
            candidates=tuple(names),
            risk_digest=str(risk.get("fingerprint", risk.get("risk_digest", ""))),
            constraints=policy,
            rationale="deterministic long-only paper allocation; no investment recommendation",
        )


__all__ = ["PaperPortfolioProposal", "PortfolioManager"]
