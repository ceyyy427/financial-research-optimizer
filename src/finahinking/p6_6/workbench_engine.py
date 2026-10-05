"""Deterministic long-only policy replay; model text never enters execution.

Signals observed at t create targets for t+delay. Portfolio returns are charged
to delayed holdings. This weight-space teaching simulator complements (does
not replace) P5/P5.5's share/cash ledgers; impact and financing are not modeled.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import pstdev
from typing import Any

from .workbench import (
    ExecutionPolicy,
    FaultPolicy,
    PositionPolicySpec,
    RiskStatePolicy,
    _digest,
    _finite,
    _freeze,
    _id,
    _safe,
)


@dataclass(frozen=True, slots=True)
class WorkbenchPoint:
    point_id: str
    time: str
    available_at: str
    instrument: str
    score: float
    signal: bool
    raw_weight: float
    risk_scale: float
    final_weight: float
    held_weight: float
    exposure: float
    cash: float
    risk_state: str
    risk_reasons: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    trade_weight: float
    fees: float
    slippage: float
    gross_return: float
    net_return: float
    equity: float
    drawdown: float
    fault_events: tuple[Mapping[str, Any], ...]
    dataset_fingerprint: str
    strategy_fingerprint: str
    policy_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return _safe({name: getattr(self, name) for name in self.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class WorkbenchRun:
    run_id: str
    points: tuple[WorkbenchPoint, ...]
    policies: Mapping[str, Any]
    metrics: Mapping[str, Any]
    dataset_fingerprint: str
    strategy_fingerprint: str
    limitations: tuple[str, ...] = (
        "Historical weight-space paper replay, not an order or future return guarantee.",
        "No market-impact, covariance optimization, margin, financing, or share-lot model is claimed.",
        "Risk-budget sizing uses diagonal-volatility approximation; cross-asset correlations are unmodeled.",
        "Weight drift between periods is not simulated; liquidity limits require supplied weight-space capacity.",
    )

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return _safe({"run_id": self.run_id, "points": [point.to_dict() for point in self.points], "policies": self.policies, "metrics": self.metrics, "dataset_fingerprint": self.dataset_fingerprint, "strategy_fingerprint": self.strategy_fingerprint, "limitations": self.limitations, "paper_only": True})


def transition_risk(state: str, age: int, metrics: Mapping[str, float], policy: RiskStatePolicy) -> tuple[str, int, tuple[str, ...]]:
    """Escalation is immediate; de-escalation requires duration and hysteresis."""
    vol = metrics.get("volatility", 0.0)
    drawdown = abs(metrics.get("drawdown", 0.0))
    threshold = policy.thresholds
    reasons: list[str] = []
    desired = "NORMAL"
    if drawdown >= threshold.get("freeze_drawdown", 0.20):
        desired = "FREEZE"
        reasons.append("drawdown budget exhausted")
    elif vol >= threshold.get("defensive_volatility", 0.26):
        desired = "DEFENSIVE"
        reasons.append("portfolio volatility above defensive threshold")
    elif vol >= threshold.get("caution_volatility", 0.18):
        desired = "CAUTION"
        reasons.append("portfolio volatility above caution threshold")
    severity = {"NORMAL": 0, "RECOVERY": 1, "CAUTION": 2, "DEFENSIVE": 3, "FREEZE": 4, "FLATTEN": 5}
    if severity[desired] > severity[state]:
        return desired, 1, tuple(reasons)
    if desired == state:
        return state, age + 1, tuple(reasons)
    if age < policy.minimum_duration:
        return state, age + 1, ("minimum state duration not reached",)
    if state in {"FREEZE", "FLATTEN"}:
        ready = drawdown <= threshold.get("recovery_drawdown", 0.05)
    elif state == "DEFENSIVE":
        ready = vol < threshold.get("defensive_volatility", 0.26) - policy.hysteresis
    else:
        ready = vol < threshold.get("caution_volatility", 0.18) - policy.hysteresis
    if not ready:
        return state, age + 1, ("hysteresis recovery boundary not crossed",)
    return ("NORMAL" if state == "RECOVERY" else "RECOVERY"), 1, ("recovery criteria satisfied",)


def _timestamp(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except (ValueError, TypeError) as exc:
        raise ValueError("observation time must be ISO formatted") from exc


def _mapping(rows: Sequence[Mapping[str, Any]], policy: PositionPolicySpec) -> dict[str, float]:
    selected = sorted((row for row in rows if row["signal"]), key=lambda row: (-row["score"], row["instrument"]))
    coefficients: dict[str, float] = {}
    for index, row in enumerate(selected):
        if policy.mapping == "rank_weight":
            coefficient = len(selected) - index
        elif policy.mapping in {"inverse_volatility", "risk_budget"}:
            volatility = row["volatility"]
            if volatility <= 0:
                continue  # unknown/zero vol never grants infinite capital
            coefficient = 1 / volatility
            if policy.mapping == "risk_budget":
                coefficient *= math.sqrt(row.get("risk_budget", 1.0))
        else:
            coefficient = 1.0
        coefficients[row["instrument"]] = coefficient
    total = sum(coefficients.values())
    exposure = min(policy.max_exposure, 1 - policy.cash_buffer)
    return {row["instrument"]: min(policy.max_single_weight, exposure * coefficients.get(row["instrument"], 0) / total) if total else 0.0 for row in rows}


def _project(target: Mapping[str, float], held: Mapping[str, float], policy: PositionPolicySpec) -> dict[str, float]:
    projected = {asset: min(policy.max_single_weight, max(0.0, weight)) for asset, weight in target.items()}
    cap = min(policy.max_exposure, 1 - policy.cash_buffer)
    exposure = sum(projected.values())
    if exposure > cap and exposure:
        projected = {asset: weight * cap / exposure for asset, weight in projected.items()}
    changes = {asset: max(-policy.max_trade_weight, min(policy.max_trade_weight, weight - held.get(asset, 0))) for asset, weight in projected.items()}
    turnover = sum(abs(change) for change in changes.values())
    scale = min(1.0, policy.max_turnover / turnover) if turnover else 1.0
    return {asset: held.get(asset, 0) + change * scale for asset, change in changes.items()}


def run_workbench(
    run_id: str,
    observations: Sequence[Mapping[str, Any]],
    position: PositionPolicySpec,
    risk: RiskStatePolicy,
    execution: ExecutionPolicy,
    faults: FaultPolicy,
    *,
    dataset_fingerprint: str | None = None,
    strategy_fingerprint: str | None = None,
) -> WorkbenchRun:
    run_id = _id(run_id, "run_id")
    if not observations or len(observations) > 10000:
        raise ValueError("observations must contain 1..10000 rows")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for item in observations:
        row = _safe(item)
        row["instrument"] = _id(row.get("instrument"), "instrument")
        row["score"] = _finite(row.get("score"), "score")
        _timestamp(row.get("time"))
        row["available_at"] = row.get("available_at", row["time"])
        if _timestamp(row["available_at"]) > _timestamp(row["time"]):
            raise ValueError("available_at cannot exceed signal time")
        identity = (row["time"], row["instrument"])
        if identity in seen:
            raise ValueError("duplicate observation time/instrument")
        seen.add(identity)
        row["volatility"] = _finite(row.get("volatility", 0), "volatility")
        if row["volatility"] < 0:
            raise ValueError("volatility must be non-negative")
        row["return"] = _finite(row.get("return", 0), "return")
        if row["return"] <= -1:
            raise ValueError("return must exceed -1")
        if not isinstance(row.get("signal", False), bool):
            raise TypeError("signal must be boolean")
        row["signal"] = row.get("signal", False)
        grouped[row["time"]].append(row)
    dataset = dataset_fingerprint or _digest(observations)
    strategy = strategy_fingerprint or _digest({"kind": "provided-factor-signals", "observations": observations})
    policies = {"position": position.to_dict(), "risk": risk.to_dict(), "execution": execution.to_dict(), "fault": faults.to_dict()}
    policy_fp = _digest(policies)
    pending: list[dict[str, float]] = []
    held: dict[str, float] = {}
    points: list[WorkbenchPoint] = []
    returns: list[float] = []
    state, age, equity, peak = "NORMAL", 1, 1.0, 1.0
    total_fees = total_slippage = total_turnover = 0.0
    min_drawdown = 0.0
    for period_index, time in enumerate(sorted(grouped, key=_timestamp)):
        rows = sorted(grouped[time], key=lambda row: row["instrument"])
        current_assets = {row["instrument"] for row in rows}
        # Missing prices for a held asset must not silently erase the holding.
        for asset in sorted(set(held) - current_assets):
            rows.append({"id": f"missing-{asset}-{period_index}", "instrument": asset, "time": time, "available_at": time, "score": 0.0, "signal": False, "return": 0.0, "volatility": 0.0, "stale": True})
        raw = _mapping(rows, position)
        realized_vol = pstdev(returns[-20:]) * math.sqrt(252) if len(returns) >= 2 else math.sqrt(sum((raw[row["instrument"]] * row["volatility"]) ** 2 for row in rows))
        observed_drawdown = max([1 - equity / peak] + [abs(float(row.get("drawdown", 0))) for row in rows])
        state, age, reasons = transition_risk(state, age, {"volatility": realized_vol, "drawdown": observed_drawdown}, risk)
        risk_scale = min(1.0, position.target_volatility / realized_vol) if position.target_volatility and realized_vol else 1.0
        risk_scale *= {"NORMAL": 1.0, "CAUTION": 0.75, "DEFENSIVE": 0.35, "RECOVERY": 0.5, "FREEZE": 0.0, "FLATTEN": 0.0}[state]
        target = _project({asset: value * risk_scale for asset, value in raw.items()}, held, position)
        delayed = pending[period_index - execution.delay_periods] if period_index >= execution.delay_periods else dict(held)
        if state == "FREEZE":
            delayed = target = dict(held)
        elif state == "FLATTEN":
            delayed = target = {asset: 0.0 for asset in raw}
        desired = _project({asset: delayed.get(asset, 0.0) for asset in raw}, held, position)
        entries: list[dict[str, Any]] = []
        for row in rows:
            asset = row["instrument"]
            before = held.get(asset, 0.0)
            change = desired[asset] - before
            events: list[dict[str, Any]] = []
            kind = "DATA_STALE" if row.get("stale") or row.get("missing") else "FACTOR_FAILURE" if row.get("factor_failed") else "COMPUTE_TIMEOUT" if row.get("timeout") else None
            slippage_bps = float(row.get("slippage_bps", execution.slippage_bps))
            if slippage_bps > execution.stress_slippage_bps:
                kind = kind or "SLIPPAGE_EXCEEDED"
            if kind:
                action = faults.actions.get(kind, "BLOCK")
                events.append({"kind": kind, "action": action, "time": time, "instrument": asset, "policy_fingerprint": faults.fingerprint})
                if action in {"SKIP", "FREEZE", "BLOCK"}:
                    change = 0.0
                    target[asset] = before
                elif action == "REDUCE":
                    change *= 0.5
                    target[asset] = min(target[asset], before + max(0, change))
                elif action == "FLATTEN":
                    change = -before
                    target[asset] = 0.0
                else:  # FALLBACK is a recorded hold, never an invented signal
                    change = 0.0
                    target[asset] = before
            capacity = float(row.get("liquidity_weight", 1e12)) * min(position.liquidity_participation, execution.liquidity_participation)
            change = max(-capacity, min(capacity, change))
            if abs(change) < max(execution.rebalance_band, execution.minimum_trade_weight):
                change = 0.0
            held[asset] = before + change
            fees = abs(change) * execution.fee_bps / 10000
            slippage = abs(change) * slippage_bps / 10000
            gross = held[asset] * row["return"]
            entries.append({"row": row, "weight": held[asset], "change": change, "fees": fees, "slippage": slippage, "gross": gross, "net": gross - fees - slippage, "events": events})
        pending.append(dict(target))
        net = sum(entry["net"] for entry in entries)
        equity *= 1 + net
        peak = max(peak, equity)
        dd = equity / peak - 1
        min_drawdown = min(min_drawdown, dd)
        returns.append(net)
        for entry in entries:
            row = entry["row"]
            asset = row["instrument"]
            total_fees += entry["fees"]
            total_slippage += entry["slippage"]
            total_turnover += abs(entry["change"])
            points.append(WorkbenchPoint(str(row.get("id", f"{asset}-{period_index}")), time, row["available_at"], asset, row["score"], row["signal"], raw[asset], risk_scale, target.get(asset, held[asset]), held[asset], sum(target.values()), max(0.0, 1 - sum(target.values())), state, reasons, tuple(risk.actions.get(state, ("FREEZE",))), entry["change"], entry["fees"], entry["slippage"], entry["gross"], entry["net"], equity, dd, tuple(_freeze(event, "fault_event") for event in entry["events"]), dataset, strategy, policy_fp))
    metrics = {"total_return": equity - 1, "max_drawdown": min_drawdown, "turnover": total_turnover, "fees": total_fees, "slippage": total_slippage, "volatility": pstdev(returns) * math.sqrt(252), "periods": len(returns), "fault_count": sum(len(point.fault_events) for point in points)}
    return WorkbenchRun(run_id, tuple(points), _freeze(policies, "policies"), _freeze(metrics, "metrics"), dataset, strategy)
