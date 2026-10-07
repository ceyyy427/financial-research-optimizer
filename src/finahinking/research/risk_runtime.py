"""Deterministic risk gate for the paper-only research runtime.

The gate accepts only a Finathink-normalized snapshot and deterministic factor
metrics.  It deliberately has no provider, network, broker, or execution
dependency; a missing or ambiguous gate is a blocking result.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, is_dataclass
from typing import Any

from .contracts import stable_digest

_FORBIDDEN = {"broker", "order", "orders", "cancel", "account", "live", "endpoint", "credential", "secret"}
_PIT_PASS = {"AVAILABLE", "VALID", "VERIFIED", "KNOWN", "READY", "TRUE", "OK"}
_PIT_FAIL = {"UNKNOWN", "UNAVAILABLE", "INVALID", "FALSE", "STALE", "MISSING", "UNVERIFIED"}


def _safe(value: Any, path: str = "value") -> Any:
    if callable(value):
        raise TypeError(f"{path} contains forbidden executable or live input")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            name = str(key)
            lowered = name.casefold()
            if any(token in lowered for token in _FORBIDDEN):
                raise ValueError(f"{path} contains forbidden paper-only field")
            result[name] = _safe(child, f"{path}.{name}")
        return result
    if isinstance(value, (list, tuple)):
        return [_safe(item, f"{path}[]") for item in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        return value
    item = getattr(value, "item", None)
    if callable(item):
        return _safe(item(), path)
    raise TypeError(f"{path} must be normalized JSON data")


def _payload(value: Any, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return _safe(value, label)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        if not isinstance(data, Mapping):
            raise TypeError(f"{label} must normalize to a mapping")
        return _safe(data, label)
    if is_dataclass(value):
        # Dataclasses from Finathink contracts expose only data fields.  Avoid
        # accepting arbitrary objects with executable attributes.
        from dataclasses import asdict

        return _safe(asdict(value), label)
    raise TypeError(f"{label} must be a normalized mapping")


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _known_number(value: Any, label: str) -> float | None:
    if value is None or (isinstance(value, str) and value.strip().upper() in {"UNKNOWN", "UNAVAILABLE", "MISSING", "N/A", "NONE"}):
        return None
    return _number(value, label)


def _nested(data: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in data:
            return data[name]
    return None


def _pit_status(snapshot: Mapping[str, Any]) -> str:
    raw = _nested(snapshot, "pit_status", "pit", "pit_state", "availability_status")
    if raw is None:
        semantics = _nested(snapshot, "pit_semantics", "point_in_time")
        if isinstance(semantics, bool):
            return "AVAILABLE" if semantics else "UNKNOWN"
        raw = semantics
    if isinstance(raw, str):
        value = raw.strip().upper().replace("-", "_")
        if value in _PIT_PASS or value in _PIT_FAIL:
            return value
        if "UNKNOWN" in value or "UNAVAILABLE" in value:
            return "UNKNOWN"
        if "AVAILABLE" in value or "VERIFIED" in value:
            return "AVAILABLE"
    observations = snapshot.get("observations", snapshot.get("records", ()))
    as_of = snapshot.get("as_of")
    if isinstance(observations, Sequence) and not isinstance(observations, (str, bytes)) and as_of is not None:
        available = []
        for item in observations:
            if isinstance(item, Mapping):
                value = item.get("available_at", item.get("timestamp"))
                if value is not None:
                    available.append(str(value) <= str(as_of))
        if available and all(available):
            return "AVAILABLE"
    return "UNKNOWN"


def _observations(snapshot: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = _nested(snapshot, "observations", "records", "data")
    if raw is None:
        return ()
    if isinstance(raw, Mapping):
        raw = tuple(raw.values())
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise TypeError("snapshot observations must be a sequence")
    normalized: list[Mapping[str, Any]] = []
    for item in raw:
        if isinstance(item, Mapping):
            normalized.append(item)
        else:
            to_dict = getattr(item, "to_dict", None)
            if not callable(to_dict) or not isinstance(to_dict(), Mapping):
                raise TypeError("snapshot observations must be normalized records")
            normalized.append(to_dict())
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class RiskReviewResult:
    """Immutable, typed result of all deterministic risk gates."""

    status: str = "BLOCKED"
    passed: bool = False
    gates: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    metrics: Mapping[str, float | str] = field(default_factory=dict)
    snapshot_digest: str = ""
    factor_digest: str = ""
    policy_version: str = "risk.v1"
    limits: Mapping[str, Any] = field(default_factory=dict)
    paper_only: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool):
            raise TypeError("passed must be boolean")
        status = str(self.status).strip().upper()
        if status not in {"PASSED", "BLOCKED", "FAILED"}:
            raise ValueError("risk status is invalid")
        if self.passed and status != "PASSED":
            object.__setattr__(self, "status", "PASSED")
        elif not self.passed and status == "PASSED":
            object.__setattr__(self, "status", "BLOCKED")
        else:
            object.__setattr__(self, "status", status)
        object.__setattr__(self, "gates", tuple(str(item) for item in self.gates))
        object.__setattr__(self, "blocking_reasons", tuple(str(item) for item in self.blocking_reasons))
        object.__setattr__(self, "metrics", dict(self.metrics))
        object.__setattr__(self, "limits", dict(self.limits))
        if self.paper_only is not True:
            raise ValueError("risk review must be paper-only")

    @property
    def blocking(self) -> bool:
        return not self.passed

    @property
    def fingerprint(self) -> str:
        return stable_digest(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "gates": list(self.gates),
            "blocking_reasons": list(self.blocking_reasons),
            "metrics": dict(self.metrics),
            "snapshot_digest": self.snapshot_digest,
            "factor_digest": self.factor_digest,
            "policy_version": self.policy_version,
            "limits": dict(self.limits),
            "paper_only": self.paper_only,
            "fingerprint": self.fingerprint,
        }


class RiskManager:
    """Apply deterministic exposure, liquidity, drawdown and stress gates."""

    def review(self, snapshot: Any, factor_result: Any, constraints: Mapping[str, Any] | Any) -> RiskReviewResult:
        snap = _payload(snapshot, "snapshot")
        factor = _payload(factor_result, "factor_result")
        policy = _payload(constraints, "constraints") if not isinstance(constraints, Mapping) else _safe(constraints, "constraints")
        if not isinstance(policy, Mapping):
            raise TypeError("constraints must be a mapping")
        reasons: list[str] = []
        gates: list[str] = []
        pit = _pit_status(snap)
        gates.append("pit")
        if pit not in _PIT_PASS:
            reasons.append("PIT status is unknown or unavailable")

        factor_status = str(_nested(factor, "status", "admission_status", "evaluation_status") or "").upper()
        if not factor_status:
            reasons.append("factor status is unavailable")
        elif factor_status not in {"ADMITTED", "VALID", "PASSED", "READY", "HUMAN_ADMITTED"}:
            reasons.append("factor result is not eligible")
        if factor.get("passed") is False:
            reasons.append("factor result failed")
        if factor.get("production_write") is True:
            reasons.append("factor result requests production write")
        gates.append("factor")

        observations = _observations(snap)
        metrics = factor.get("metrics") if isinstance(factor.get("metrics"), Mapping) else {}
        snapshot_metrics = snap.get("metrics") if isinstance(snap.get("metrics"), Mapping) else {}

        liquidity = _nested(metrics, "liquidity", "min_liquidity", "average_volume")
        if liquidity is None:
            liquidity = _nested(snap, "liquidity", "min_liquidity")
        if liquidity is None and observations:
            values = [float(item.get("volume", item.get("amount", 0.0)) or 0.0) for item in observations]
            liquidity = min(values) if values else None
        minimum_liquidity = _nested(policy, "min_liquidity", "minimum_liquidity")
        if minimum_liquidity is not None:
            try:
                liquidity_value = _known_number(liquidity, "liquidity")
            except (TypeError, ValueError):
                liquidity_value = None
            if liquidity_value is None:
                reasons.append("liquidity metric is unavailable")
            elif liquidity_value < _number(minimum_liquidity, "min_liquidity"):
                reasons.append("liquidity limit failed")
        gates.append("liquidity")

        concentration = _nested(metrics, "concentration", "max_concentration")
        if concentration is None:
            concentration = _nested(snap, "concentration", "max_concentration")
        if concentration is None and observations:
            notionals = []
            for item in observations:
                try:
                    notionals.append(max(0.0, _number(item.get("close", 0.0), "close")) * max(0.0, _number(item.get("volume", 0.0), "volume")))
                except (TypeError, ValueError):
                    continue
            total = sum(notionals)
            concentration = max(notionals) / total if notionals and total else None
        max_concentration = _nested(policy, "max_concentration", "concentration_limit")
        if max_concentration is not None:
            try:
                concentration_value = _known_number(concentration, "concentration")
            except (TypeError, ValueError):
                concentration_value = None
            if concentration_value is None:
                reasons.append("concentration metric is unavailable")
            elif concentration_value > _number(max_concentration, "max_concentration") + 1e-12:
                reasons.append("concentration limit failed")
        gates.append("concentration")

        drawdown = _nested(metrics, "drawdown", "max_drawdown")
        if drawdown is None:
            drawdown = _nested(snapshot_metrics, "drawdown", "max_drawdown")
        if drawdown is None:
            drawdown = _nested(snap, "drawdown", "max_drawdown")
        drawdown_unknown = isinstance(drawdown, str) and drawdown.strip().upper() in {"UNKNOWN", "UNAVAILABLE", "MISSING", "N/A", "NONE"}
        if drawdown_unknown or drawdown is None:
            reasons.append("drawdown metric is unavailable")
            drawdown = 0.0
        else:
            drawdown = abs(_number(drawdown, "drawdown"))
        max_drawdown = _nested(policy, "max_drawdown", "drawdown_limit")
        if max_drawdown is not None and drawdown > _number(max_drawdown, "max_drawdown") + 1e-12:
            reasons.append("drawdown limit failed")
        gates.append("drawdown")

        stress = _nested(snap, "stress_results") or _nested(metrics, "stress_results")
        scenarios = _nested(policy, "stress_scenarios", "stress_tests")
        if scenarios is None:
            reasons.append("stress scenarios are unavailable")
        elif scenarios is not None:
            if not isinstance(scenarios, Mapping) or not scenarios:
                reasons.append("stress scenarios are invalid")
            else:
                for name, scenario in scenarios.items():
                    outcome = stress.get(name) if isinstance(stress, Mapping) else None
                    if not isinstance(outcome, Mapping):
                        reasons.append(f"stress scenario result unavailable: {name}")
                    elif outcome.get("passed") is False:
                        reasons.append(f"stress scenario failed: {name}")
                    elif outcome.get("passed") is not True:
                        reasons.append(f"stress scenario result unknown: {name}")
                    elif (
                        isinstance(scenario, Mapping)
                        and "drawdown" in scenario
                        and max_drawdown is not None
                        and abs(_number(scenario["drawdown"], f"stress.{name}.drawdown")) > _number(max_drawdown, "max_drawdown") + 1e-12
                    ):
                        reasons.append(f"stress scenario failed: {name}")
        gates.append("stress")

        try:
            clean_liquidity = _known_number(liquidity, "liquidity")
        except (TypeError, ValueError):
            clean_liquidity = None
        try:
            clean_concentration = _known_number(concentration, "concentration")
        except (TypeError, ValueError):
            clean_concentration = None
        clean_metrics: dict[str, float | str] = {
            "pit_status": pit,
            "liquidity": clean_liquidity if clean_liquidity is not None else "UNKNOWN",
            "concentration": clean_concentration if clean_concentration is not None else "UNKNOWN",
            "drawdown": float(drawdown),
        }
        return RiskReviewResult(
            status="PASSED" if not reasons else "BLOCKED",
            passed=not reasons,
            gates=tuple(gates),
            blocking_reasons=tuple(dict.fromkeys(reasons)),
            metrics=clean_metrics,
            snapshot_digest=stable_digest(snap),
            factor_digest=stable_digest(factor),
            policy_version=str(policy.get("policy_version", policy.get("version", "risk.v1"))),
            limits=policy,
        )


__all__ = ["RiskManager", "RiskReviewResult"]
