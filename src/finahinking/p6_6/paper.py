"""Deterministic paper-trading simulation for the P6.6 research lab.

This module deliberately models a *replay* of approved historical data.  It
has no broker, account, credentials, network, or order-submission boundary.
The fill and cost rules mirror :mod:`finahinking.quant.engines.backtest` so a
paper run can be compared with the P5 historical result without introducing a
second execution authority.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from finahinking.data.models import Dataset, Provenance
from finahinking.experiments.models import canonical_json, dataset_payload
from finahinking.quant.interfaces import BacktestConfig


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _finite(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return _safe(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    return value


def _as_dataset(value: Dataset | pd.DataFrame) -> Dataset:
    if isinstance(value, Dataset):
        return value
    if not isinstance(value, pd.DataFrame):
        raise TypeError("dataset must be a Dataset or pandas DataFrame")
    if value.empty:
        raise ValueError("dataset cannot be empty")
    frame = value.copy()
    if "close" not in frame.columns:
        raise ValueError("dataset must contain a close column")
    frame.index = pd.to_datetime(frame.index)
    frame.index.name = "date"
    return Dataset(frame, Provenance(provider="p6_6_fixture", source_url="internal://approved-fixture"))


def _strategy_identity(strategy: Any, strategy_version: Any | None) -> tuple[str, str]:
    source = strategy_version if strategy_version is not None else strategy
    if isinstance(source, Mapping):
        strategy_id = source.get("strategy_id") or source.get("strategy_name") or source.get("name")
        version = source.get("version") or source.get("strategy_version")
    else:
        strategy_id = getattr(source, "strategy_id", None) or getattr(source, "strategy_name", None) or getattr(source, "name", None)
        version = getattr(source, "version", None) or getattr(source, "strategy_version", None)
    strategy_id = str(strategy_id or getattr(strategy, "strategy_id", "p6_6_strategy"))
    version = str(version or getattr(strategy, "version", "v1"))
    for label, value in (("strategy_id", strategy_id), ("strategy_version", version)):
        if not value or "/" in value or "\\" in value or value in {".", ".."}:
            raise ValueError(f"{label} is invalid")
    return strategy_id, version


def _target_series(strategy: Any, as_of: Dataset) -> pd.Series:
    if hasattr(strategy, "generate"):
        values = strategy.generate(as_of)
    elif callable(strategy):
        values = strategy(as_of)
    else:
        raise TypeError("strategy must implement generate(dataset) or be callable")
    if not isinstance(values, pd.Series):
        if isinstance(values, Mapping):
            values = pd.Series(values)
        else:
            raise TypeError("strategy must return a pandas Series")
    if len(values) == 1 and len(as_of.frame) > 1:
        values = pd.Series(float(values.iloc[0]), index=as_of.frame.index)
    try:
        values = values.copy()
        values.index = pd.to_datetime(values.index)
    except (TypeError, ValueError) as exc:
        raise ValueError("strategy index is invalid") from exc
    if not values.index.equals(as_of.frame.index):
        raise ValueError("strategy index must match dataset index")
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.replace([float("inf"), float("-inf")], pd.NA).notna().sum() != len(numeric.dropna()):
        raise ValueError("strategy weights must be finite")
    return numeric.astype(float).fillna(0.0)


@dataclass(frozen=True)
class PaperSignal:
    timestamp: str
    target_weight: float
    reason: str
    strategy_version: str
    feature_versions: tuple[str, ...] = ()
    observation_time: str | None = None
    signal_time: str | None = None
    decision_values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        weight = _finite(self.target_weight, "target_weight")
        if not -1.0 <= weight <= 1.0:
            raise ValueError("target_weight must be between -1 and 1")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason is required")
        object.__setattr__(self, "target_weight", weight)
        object.__setattr__(self, "timestamp", pd.Timestamp(self.timestamp).isoformat())
        object.__setattr__(self, "feature_versions", tuple(str(value) for value in self.feature_versions))
        object.__setattr__(self, "observation_time", pd.Timestamp(self.observation_time or self.timestamp).isoformat())
        object.__setattr__(self, "signal_time", pd.Timestamp(self.signal_time or self.timestamp).isoformat())
        object.__setattr__(self, "decision_values", dict(self.decision_values))

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp, "target_weight": self.target_weight, "reason": self.reason, "strategy_version": self.strategy_version, "feature_versions": list(self.feature_versions), "observation_time": self.observation_time, "signal_time": self.signal_time, "decision_values": _safe(self.decision_values)}


@dataclass(frozen=True)
class VirtualOrder:
    timestamp: str
    side: str
    quantity: float
    target_weight: float
    signal_timestamp: str
    reason: str
    instrument: str = "asset"
    eligible_fill_time: str | None = None
    fill_price_rule: str = "next_valid_price"
    status: str = "filled"

    def __post_init__(self) -> None:
        if self.side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        quantity = _finite(self.quantity, "quantity")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "target_weight", _finite(self.target_weight, "target_weight"))
        object.__setattr__(self, "timestamp", pd.Timestamp(self.timestamp).isoformat())
        object.__setattr__(self, "signal_timestamp", pd.Timestamp(self.signal_timestamp).isoformat())
        object.__setattr__(self, "eligible_fill_time", pd.Timestamp(self.eligible_fill_time or self.timestamp).isoformat())
        if not isinstance(self.instrument, str) or not self.instrument.strip():
            raise ValueError("instrument is required")
        if self.status not in {"created", "filled", "cancelled"}:
            raise ValueError("order status is invalid")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason is required")

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp, "side": self.side, "quantity": self.quantity, "target_weight": self.target_weight, "signal_timestamp": self.signal_timestamp, "reason": self.reason, "instrument": self.instrument, "eligible_fill_time": self.eligible_fill_time, "fill_price_rule": self.fill_price_rule, "status": self.status}

    @property
    def created_at(self) -> str:
        return self.timestamp


@dataclass(frozen=True)
class VirtualFill:
    timestamp: str
    side: str
    quantity: float
    reference_price: float
    execution_price: float
    notional: float
    fees: float
    slippage: float
    order_timestamp: str
    instrument: str = "asset"

    def __post_init__(self) -> None:
        if self.side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        for name in ("quantity", "reference_price", "execution_price", "notional", "fees", "slippage"):
            number = _finite(getattr(self, name), name)
            if name in {"quantity", "reference_price", "execution_price"} and number <= 0:
                raise ValueError(f"{name} must be positive")
            if name in {"fees", "slippage"} and number < 0:
                raise ValueError(f"{name} must be non-negative")
            object.__setattr__(self, name, number)
        if abs(self.notional - self.quantity * self.execution_price) > max(1e-8, abs(self.notional) * 1e-8):
            raise ValueError("notional does not match quantity and execution_price")
        object.__setattr__(self, "timestamp", pd.Timestamp(self.timestamp).isoformat())
        object.__setattr__(self, "order_timestamp", pd.Timestamp(self.order_timestamp).isoformat())
        object.__setattr__(self, "instrument", str(self.instrument))

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp, "side": self.side, "quantity": self.quantity, "reference_price": self.reference_price, "execution_price": self.execution_price, "notional": self.notional, "fees": self.fees, "slippage": self.slippage, "order_timestamp": self.order_timestamp, "instrument": self.instrument}

    @property
    def cost(self) -> float:
        return self.fees


@dataclass(frozen=True)
class VirtualPortfolio:
    timestamp: str
    cash: float
    position: float
    equity: float
    target_weight: float
    turnover: float
    realized_pnl: float
    unrealized_pnl: float
    exposure: float
    benchmark_equity: float

    def __post_init__(self) -> None:
        for name in ("cash", "position", "equity", "target_weight", "turnover", "realized_pnl", "unrealized_pnl", "exposure", "benchmark_equity"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        object.__setattr__(self, "timestamp", pd.Timestamp(self.timestamp).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {name: _safe(getattr(self, name)) for name in ("timestamp", "cash", "position", "equity", "target_weight", "turnover", "realized_pnl", "unrealized_pnl", "exposure", "benchmark_equity")}


@dataclass(frozen=True)
class PaperRun:
    dataset_fingerprint: str
    strategy_id: str
    strategy_version: str
    engine_version: str
    config: dict[str, Any]
    signals: tuple[PaperSignal, ...]
    orders: tuple[VirtualOrder, ...]
    fills: tuple[VirtualFill, ...]
    portfolios: tuple[VirtualPortfolio, ...]
    approved_data_reference: str
    limitations: tuple[str, ...] = ("historical replay only", "not broker-connected", "not a forecast or guarantee")
    paper_run_id: str = "paper-run"
    data_source: str = "approved_replay"
    started_at: str = ""
    simulation_clock: str = "virtual_clock"
    initial_capital: float | None = None
    status: str = "completed"
    benchmark: str = "buy_and_hold"
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dataset_fingerprint or not self.approved_data_reference:
            raise ValueError("approved dataset reference is required")
        if any(not isinstance(item, PaperSignal) for item in self.signals):
            raise TypeError("signals must be PaperSignal records")
        if any(not isinstance(item, VirtualOrder) for item in self.orders):
            raise TypeError("orders must be VirtualOrder records")
        if any(not isinstance(item, VirtualFill) for item in self.fills):
            raise TypeError("fills must be VirtualFill records")
        if any(not isinstance(item, VirtualPortfolio) for item in self.portfolios):
            raise TypeError("portfolios must be VirtualPortfolio records")
        if any(name.casefold() in {"broker", "account", "credential", "secret", "endpoint"} for name in self.__dict__):
            raise ValueError("paper run contains a forbidden broker field")
        object.__setattr__(self, "limitations", tuple(str(item) for item in self.limitations))
        if not isinstance(self.paper_run_id, str) or not self.paper_run_id.strip():
            raise ValueError("paper_run_id is required")
        if self.status not in {"created", "running", "completed", "failed"}:
            raise ValueError("paper run status is invalid")
        if self.initial_capital is None:
            object.__setattr__(self, "initial_capital", float(self.config.get("starting_cash", 0.0)))
        else:
            object.__setattr__(self, "initial_capital", _finite(self.initial_capital, "initial_capital"))
        object.__setattr__(self, "provenance", dict(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema_version": 1, "paper_run_id": self.paper_run_id, "dataset_fingerprint": self.dataset_fingerprint, "strategy_id": self.strategy_id, "strategy_version": self.strategy_version, "engine_version": self.engine_version, "data_source": self.data_source, "approved_data_reference": self.approved_data_reference, "started_at": self.started_at, "simulation_clock": self.simulation_clock, "initial_capital": self.initial_capital, "status": self.status, "benchmark": self.benchmark, "config": _safe(self.config), "signals": [item.to_dict() for item in self.signals], "orders": [item.to_dict() for item in self.orders], "fills": [item.to_dict() for item in self.fills], "portfolios": [item.to_dict() for item in self.portfolios], "limitations": list(self.limitations), "provenance": _safe(self.provenance)}
        return {**payload, "fingerprint": _digest(payload)}

    @property
    def fingerprint(self) -> str:
        return str(self.to_dict()["fingerprint"])

    @property
    def dataset_reference(self) -> str:
        return self.approved_data_reference

    @property
    def configuration(self) -> dict[str, Any]:
        return dict(self.config)

    @property
    def current_value(self) -> float | None:
        return None if not self.portfolios else float(self.portfolios[-1].equity)

    @property
    def cash(self) -> float | None:
        return None if not self.portfolios else float(self.portfolios[-1].cash)

    @property
    def positions(self) -> float | None:
        return None if not self.portfolios else float(self.portfolios[-1].position)

    @property
    def transaction_costs(self) -> float:
        return float(sum(fill.fees for fill in self.fills))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PaperRun:
        if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
            raise ValueError("paper run schema is invalid")
        required = {"dataset_fingerprint", "strategy_id", "strategy_version", "engine_version", "config", "signals", "orders", "fills", "portfolios", "approved_data_reference", "limitations", "fingerprint"}
        if not required.issubset(payload):
            raise ValueError("paper run schema is invalid")
        run = cls(
            dataset_fingerprint=str(payload["dataset_fingerprint"]),
            strategy_id=str(payload["strategy_id"]),
            strategy_version=str(payload["strategy_version"]),
            engine_version=str(payload["engine_version"]),
            config=dict(payload["config"]),
            signals=tuple(PaperSignal(**item) for item in payload["signals"]),
            orders=tuple(VirtualOrder(**item) for item in payload["orders"]),
            fills=tuple(VirtualFill(**item) for item in payload["fills"]),
            portfolios=tuple(VirtualPortfolio(**item) for item in payload["portfolios"]),
            approved_data_reference=str(payload["approved_data_reference"]),
            limitations=tuple(str(item) for item in payload["limitations"]),
            paper_run_id=str(payload.get("paper_run_id", "paper-run")),
            data_source=str(payload.get("data_source", "approved_replay")),
            started_at=str(payload.get("started_at", "")),
            simulation_clock=str(payload.get("simulation_clock", "virtual_clock")),
            initial_capital=payload.get("initial_capital"),
            status=str(payload.get("status", "completed")),
            benchmark=str(payload.get("benchmark", "buy_and_hold")),
            provenance=dict(payload.get("provenance", {})),
        )
        if payload["fingerprint"] != run.fingerprint:
            raise ValueError("paper run fingerprint is invalid")
        return run


class PaperSimulator:
    """Run a frozen strategy through a virtual clock and deterministic fills."""

    engine_version = "p6_6.paper-replay.1"

    def run(self, dataset: Dataset | pd.DataFrame, strategy: Any, config: BacktestConfig | Mapping[str, Any], *, strategy_version: Any | None = None, approved_data_reference: str | None = None) -> PaperRun:
        approved = _as_dataset(dataset)
        resolved_config = config if isinstance(config, BacktestConfig) else BacktestConfig.from_dict(dict(config))
        strategy_id, version = _strategy_identity(strategy, strategy_version)
        frozen = strategy_version if strategy_version is not None else strategy
        raw_features = (frozen.get("feature_versions", ()) if isinstance(frozen, Mapping) else getattr(frozen, "feature_versions", ()))
        feature_versions = tuple(str(getattr(item, "fingerprint", getattr(item, "version", item))) for item in raw_features)
        frame = approved.frame
        signals: list[PaperSignal] = []
        for end in range(1, len(frame) + 1):
            as_of = Dataset(frame.iloc[:end].copy(), approved.provenance)
            series = _target_series(strategy, as_of)
            signal = float(series.iloc[-1])
            if abs(signal) > resolved_config.max_abs_weight + 1e-12:
                raise ValueError("strategy weight exceeds configured limit")
            timestamp = pd.Timestamp(frame.index[end - 1]).isoformat()
            signals.append(PaperSignal(timestamp, signal, f"{strategy_id} target-weight signal", version, feature_versions=feature_versions, decision_values={"target_weight": signal}))
        prices = frame["close"].astype(float)
        cash = float(resolved_config.starting_cash)
        position = 0.0
        benchmark_units = float(resolved_config.starting_cash / prices.iloc[0])
        realized = 0.0
        turnover = 0.0
        orders: list[VirtualOrder] = []
        fills: list[VirtualFill] = []
        portfolios: list[VirtualPortfolio] = []
        previous_price = float(prices.iloc[0])
        for index, (timestamp, price_value) in enumerate(prices.items()):
            timestamp_text = pd.Timestamp(timestamp).isoformat()
            price = _finite(price_value, "price")
            equity_before = cash + position * price
            target = 0.0 if index == 0 else signals[index - 1].target_weight
            target_position = target * equity_before / price
            delta = target_position - position
            fill: VirtualFill | None = None
            if abs(delta) > 1e-12:
                side = "buy" if delta > 0 else "sell"
                quantity = abs(delta)
                direction = 1.0 if side == "buy" else -1.0
                execution_price = price * (1.0 + direction * resolved_config.slippage_bps / 10_000.0)
                notional = quantity * execution_price
                fees = notional * resolved_config.fee_bps / 10_000.0
                slippage = quantity * abs(execution_price - price)
                candidate_cash = cash - notional - fees if side == "buy" else cash + notional - fees
                if not resolved_config.allow_negative_cash and candidate_cash < -1e-9:
                    raise ValueError("negative cash is not allowed")
                order = VirtualOrder(timestamp_text, side, quantity, target, signals[index - 1].timestamp if index else timestamp_text, signals[index - 1].reason if index else f"{strategy_id} initial target")
                fill = VirtualFill(timestamp_text, side, quantity, price, execution_price, notional, fees, slippage, order.timestamp)
                orders.append(order)
                fills.append(fill)
                if side == "sell":
                    realized += quantity * (execution_price - previous_price)
                cash = candidate_cash
                position += delta
                turnover += notional
            equity = cash + position * price
            benchmark_equity = benchmark_units * price
            portfolios.append(VirtualPortfolio(timestamp_text, cash, position, equity, target, turnover, realized, position * (price - previous_price), position * price, benchmark_equity))
            previous_price = price
        dataset_reference = approved_data_reference or _digest(dataset_payload(approved))
        return PaperRun(dataset_fingerprint=_digest(dataset_payload(approved)), strategy_id=strategy_id, strategy_version=version, engine_version=self.engine_version, config=resolved_config.to_dict(), signals=tuple(signals), orders=tuple(orders), fills=tuple(fills), portfolios=tuple(portfolios), approved_data_reference=dataset_reference, paper_run_id=f"paper-{strategy_id}-{version}", data_source=str(approved.provenance.provider), started_at=str(frame.index[0]), provenance={"dataset_fingerprint": _digest(dataset_payload(approved)), "dataset_reference": dataset_reference, "strategy_version": version, "engine_version": self.engine_version})


def run_paper(*args: Any, **kwargs: Any) -> PaperRun:
    return PaperSimulator().run(*args, **kwargs)


__all__ = ["PaperRun", "PaperSignal", "PaperSimulator", "VirtualFill", "VirtualOrder", "VirtualPortfolio", "run_paper"]
