"""Deterministic, point-in-time-safe cross-sectional momentum research.

This module is deliberately additive to the single-asset P5 engine.  It owns a
small long-form panel contract and a fixed research experiment; it is not a
portfolio optimizer or an execution connector.
"""

from __future__ import annotations

import copy
import hashlib
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from finahinking.data.models import Dataset, Provenance
from finahinking.experiments.models import ResearchRun, canonical_json
from finahinking.factors.core import momentum_factor

from .artifacts import Artifact, QuantRun
from .interfaces import _digest
from .risk.metrics import conditional_value_at_risk, maximum_drawdown, value_at_risk
from .runtime import _code_commit, _dependency_versions

P5_5_WARNING_CODES: tuple[str, ...] = (
    "SURVIVORSHIP_BIAS_NOT_MODELED",
    "DELISTING_NOT_MODELED",
    "CORPORATE_ACTIONS_PARTIAL",
    "LIQUIDITY_NOT_MODELED",
    "CAPACITY_UNKNOWN",
    "MARKET_IMPACT_NOT_MODELED",
)


def _finite(value: Any, field: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _as_timestamp(value: Any, field: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValueError(f"{field} is invalid")
    return timestamp


@dataclass(frozen=True)
class MultiAssetDataset:
    """Long-form prices with an explicit availability timestamp."""

    frame: pd.DataFrame
    provider: str
    source_url: str
    license: str = "offline fixture; verify provider terms before redistribution"

    def __post_init__(self) -> None:
        if not isinstance(self.frame, pd.DataFrame) or self.frame.empty:
            raise ValueError("multi-asset frame cannot be empty")
        required = {"date", "asset", "close", "available_at"}
        if not required.issubset(self.frame.columns):
            raise ValueError(f"multi-asset frame requires {sorted(required)}")
        frame = self.frame.loc[:, ["date", "asset", "close", "available_at"]].copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="raise")
        frame["available_at"] = pd.to_datetime(frame["available_at"], errors="raise")
        if frame["date"].isna().any() or frame["available_at"].isna().any():
            raise ValueError("date and available_at must be valid")
        date_zone = getattr(frame["date"].dt, "tz", None)
        available_zone = getattr(frame["available_at"].dt, "tz", None)
        if date_zone != available_zone:
            raise ValueError("date and available_at must use compatible timezone semantics")
        frame["asset"] = frame["asset"].astype(str)
        if (frame["asset"].str.strip() == "").any():
            raise ValueError("asset identifiers are required")
        frame["close"] = pd.to_numeric(frame["close"], errors="raise")
        if not np.isfinite(frame["close"].to_numpy(dtype=float)).all() or (frame["close"] <= 0).any():
            raise ValueError("close values must be positive and finite")
        if frame.duplicated(["date", "asset"]).any():
            raise ValueError("duplicate date/asset observations")
        frame = frame.sort_values(["date", "asset"]).reset_index(drop=True)
        frame.index.name = "observation"
        object.__setattr__(self, "frame", frame)
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("provider is required")
        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise ValueError("source_url is required")

    @property
    def dates(self) -> tuple[pd.Timestamp, ...]:
        return tuple(pd.Timestamp(value) for value in sorted(self.frame["date"].unique()))

    @property
    def assets(self) -> tuple[str, ...]:
        return tuple(sorted(self.frame["asset"].unique().tolist()))

    @property
    def fingerprint(self) -> str:
        records = [
            {
                "date": pd.Timestamp(row.date).isoformat(),
                "asset": str(row.asset),
                "close": float(row.close),
                "available_at": pd.Timestamp(row.available_at).isoformat(),
            }
            for row in self.frame.itertuples(index=False)
        ]
        return hashlib.sha256(
            canonical_json(
                {
                    "records": records,
                    "provider": self.provider,
                    "source_url": self.source_url,
                    "license": self.license,
                }
            ).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "fingerprint": self.fingerprint,
            "provider": self.provider,
            "source_url": self.source_url,
            "license": self.license,
            "records": [
                {
                    "date": pd.Timestamp(row.date).isoformat(),
                    "asset": str(row.asset),
                    "close": float(row.close),
                    "available_at": pd.Timestamp(row.available_at).isoformat(),
                }
                for row in self.frame.itertuples(index=False)
            ],
        }


@dataclass(frozen=True)
class CrossSectionalMomentumConfig:
    lookback: int = 2
    top_fraction: float = 0.5
    starting_cash: float = 100_000.0
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    benchmark: str = "equal_weight"
    annualization: int = 252
    max_abs_weight: float = 1.0
    allow_short: bool = False
    leverage: float = 1.0

    def __post_init__(self) -> None:
        if isinstance(self.lookback, bool) or self.lookback < 1:
            raise ValueError("lookback must be a positive integer")
        for value, name in (
            (self.top_fraction, "top_fraction"),
            (self.starting_cash, "starting_cash"),
            (self.fee_bps, "fee_bps"),
            (self.slippage_bps, "slippage_bps"),
            (self.max_abs_weight, "max_abs_weight"),
            (self.leverage, "leverage"),
        ):
            _finite(value, name)
        if not 0 < self.top_fraction <= 1:
            raise ValueError("top_fraction must be in (0, 1]")
        if self.starting_cash <= 0 or self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("cash and costs are invalid")
        if not 0 < self.max_abs_weight <= 1 or self.leverage != 1.0:
            raise ValueError("only unlevered max-weight portfolios are supported")
        if self.allow_short:
            raise ValueError("shorting is not supported by this slice")
        if self.benchmark != "equal_weight":
            raise ValueError("benchmark must be equal_weight")
        if isinstance(self.annualization, bool) or self.annualization < 1:
            raise ValueError("annualization must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "lookback": self.lookback,
            "top_fraction": self.top_fraction,
            "starting_cash": self.starting_cash,
            "fee_bps": self.fee_bps,
            "slippage_bps": self.slippage_bps,
            "benchmark": self.benchmark,
            "annualization": self.annualization,
            "max_abs_weight": self.max_abs_weight,
            "allow_short": self.allow_short,
            "leverage": self.leverage,
        }


@dataclass(frozen=True)
class MultiAssetBacktestResult:
    dataset_fingerprint: str
    strategy_id: str
    strategy_version: str
    config: CrossSectionalMomentumConfig
    equity_curve: tuple[tuple[str, float], ...]
    returns: tuple[tuple[str, float], ...]
    invested_weights: tuple[tuple[str, float], ...]
    turnover: tuple[tuple[str, float], ...]
    benchmark_returns: tuple[tuple[str, float], ...]
    selected_assets: tuple[tuple[str, tuple[str, ...]], ...]
    fees: tuple[tuple[str, float], ...]
    slippage: tuple[tuple[str, float], ...]
    trade_count: int

    @property
    def fingerprint(self) -> str:
        payload = {
            "schema_version": 1,
            "dataset_fingerprint": self.dataset_fingerprint,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "config": self.config.to_dict(),
            "equity_curve": self.equity_curve,
            "returns": self.returns,
            "invested_weights": self.invested_weights,
            "turnover": self.turnover,
            "benchmark_returns": self.benchmark_returns,
            "selected_assets": self.selected_assets,
            "fees": self.fees,
            "slippage": self.slippage,
            "trade_count": self.trade_count,
        }
        return _digest(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "dataset_fingerprint": self.dataset_fingerprint,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "config": self.config.to_dict(),
            "equity_curve": [[timestamp, value] for timestamp, value in self.equity_curve],
            "returns": [[timestamp, value] for timestamp, value in self.returns],
            "invested_weights": [[timestamp, value] for timestamp, value in self.invested_weights],
            "turnover": [[timestamp, value] for timestamp, value in self.turnover],
            "benchmark_returns": [[timestamp, value] for timestamp, value in self.benchmark_returns],
            "selected_assets": [[timestamp, list(assets)] for timestamp, assets in self.selected_assets],
            "fees": [[timestamp, value] for timestamp, value in self.fees],
            "slippage": [[timestamp, value] for timestamp, value in self.slippage],
            "trade_count": self.trade_count,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class MultiAssetEvaluation:
    result_fingerprint: str
    metrics: dict[str, float | None]
    benchmark: str
    limitations: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        return _digest(
            {
                "result_fingerprint": self.result_fingerprint,
                "metrics": self.metrics,
                "benchmark": self.benchmark,
                "limitations": self.limitations,
                "warnings": self.warnings,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "result_fingerprint": self.result_fingerprint,
            "metrics": copy.deepcopy(self.metrics),
            "benchmark": self.benchmark,
            "limitations": list(self.limitations),
            "warnings": list(self.warnings),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class MultiAssetExperimentResult:
    quant_run: QuantRun
    research_run: ResearchRun
    artifact: Artifact
    backtest: MultiAssetBacktestResult
    evaluation: MultiAssetEvaluation
    validity: Any
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]


def _asof_price(frame: pd.DataFrame, asset: str, timestamp: pd.Timestamp) -> float | None:
    eligible = frame[
        (frame["asset"] == asset)
        & (frame["date"] <= timestamp)
        & (frame["available_at"] <= timestamp)
    ]
    if eligible.empty:
        return None
    row = eligible.sort_values(["date", "available_at"]).iloc[-1]
    return float(row["close"])


def _signal_weights(dataset: MultiAssetDataset, timestamp: pd.Timestamp, config: CrossSectionalMomentumConfig) -> tuple[dict[str, float], tuple[str, ...]]:
    values: dict[str, float] = {}
    for asset in dataset.assets:
        eligible = dataset.frame[
            (dataset.frame["asset"] == asset)
            & (dataset.frame["date"] <= timestamp)
            & (dataset.frame["available_at"] <= timestamp)
        ].sort_values("date")
        prices = eligible["close"].astype(float).tolist()
        if len(prices) > config.lookback:
            values[asset] = prices[-1] / prices[-1 - config.lookback] - 1.0
    if not values:
        return {}, ()
    count = max(1, math.ceil(len(values) * config.top_fraction))
    ranked = sorted(values, key=lambda asset: (-values[asset], asset))[:count]
    weight = min(config.max_abs_weight / len(ranked), 1.0 / len(ranked))
    return {asset: weight for asset in ranked}, tuple(ranked)


def _evaluate(backtest: MultiAssetBacktestResult) -> MultiAssetEvaluation:
    returns = pd.Series([value for _, value in backtest.returns], dtype=float)
    equity = pd.Series([value for _, value in backtest.equity_curve], dtype=float)
    benchmark = pd.Series([value for _, value in backtest.benchmark_returns], dtype=float)
    volatility = None if len(returns) < 2 else float(returns.std(ddof=1) * math.sqrt(backtest.config.annualization))
    mean = None if returns.empty else float(returns.mean())
    sharpe = None if volatility in (None, 0.0) or mean is None else float(mean * math.sqrt(backtest.config.annualization) / returns.std(ddof=1))
    total = None if len(equity) < 2 else float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    benchmark_total = float((1 + benchmark).prod() - 1.0) if not benchmark.empty else None
    metrics: dict[str, float | None] = {
        "total_return": total,
        "volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": maximum_drawdown(equity),
        "value_at_risk_95": value_at_risk(returns),
        "conditional_value_at_risk_95": conditional_value_at_risk(returns),
        "turnover": float(sum(value for _, value in backtest.turnover)),
        "total_fees": float(sum(value for _, value in backtest.fees)),
        "total_slippage": float(sum(value for _, value in backtest.slippage)),
        "benchmark_return": benchmark_total,
        "excess_return": None if total is None or benchmark_total is None else total - benchmark_total,
        "trade_count": float(backtest.trade_count),
    }
    limitations = (
        "descriptive historical evidence only; not investment advice.",
        "The fixed slice does not model survivorship, delistings, liquidity, capacity, or market impact.",
        "Corporate actions are only partially represented by supplied prices.",
    )
    return MultiAssetEvaluation(
        result_fingerprint=backtest.fingerprint,
        metrics=metrics,
        benchmark=backtest.config.benchmark,
        limitations=limitations,
        warnings=P5_5_WARNING_CODES,
    )


def run_cross_sectional_momentum_experiment(
    dataset: MultiAssetDataset,
    config: CrossSectionalMomentumConfig | None = None,
    *,
    question: str,
    hypothesis: str,
    run_id: str | None = None,
    validity: Any | None = None,
) -> MultiAssetExperimentResult:
    """Run one fixed, lagged, long-only panel experiment and preserve evidence."""

    if not isinstance(question, str) or not question.strip() or not isinstance(hypothesis, str) or not hypothesis.strip():
        raise ValueError("question and hypothesis are required")
    config = config or CrossSectionalMomentumConfig()
    dates = list(dataset.dates)
    if len(dates) < 2:
        raise ValueError("at least two dates are required")
    equity = float(config.starting_cash)
    executed_weights: dict[str, float] = {}
    equity_curve: list[tuple[str, float]] = [(dates[0].isoformat(), equity)]
    returns: list[tuple[str, float]] = [(dates[0].isoformat(), 0.0)]
    invested: list[tuple[str, float]] = [(dates[0].isoformat(), 0.0)]
    turnovers: list[tuple[str, float]] = [(dates[0].isoformat(), 0.0)]
    fees: list[tuple[str, float]] = [(dates[0].isoformat(), 0.0)]
    slippages: list[tuple[str, float]] = [(dates[0].isoformat(), 0.0)]
    benchmark_returns: list[tuple[str, float]] = [(dates[0].isoformat(), 0.0)]
    selected_assets: list[tuple[str, tuple[str, ...]]] = [(dates[0].isoformat(), ())]
    pending: dict[str, float] = {}
    trade_count = 0
    for index in range(1, len(dates)):
        timestamp = dates[index]
        previous_timestamp = dates[index - 1]
        current_assets = dataset.assets
        gross_components: list[float] = []
        bench_components: list[float] = []
        for asset in current_assets:
            current = _asof_price(dataset.frame, asset, timestamp)
            previous = _asof_price(dataset.frame, asset, previous_timestamp)
            if current is None or previous is None or previous <= 0:
                continue
            asset_return = current / previous - 1.0
            gross_components.append(pending.get(asset, 0.0) * asset_return)
            bench_components.append(asset_return)
        turnover = float(sum(abs(pending.get(asset, 0.0) - executed_weights.get(asset, 0.0)) for asset in current_assets) / 2.0)
        fee_value = equity * turnover * config.fee_bps / 10000.0
        slippage_value = equity * turnover * config.slippage_bps / 10000.0
        friction = (fee_value + slippage_value) / equity if equity else 0.0
        period_return = float(sum(gross_components) - friction)
        equity *= 1.0 + period_return
        returns.append((timestamp.isoformat(), period_return))
        equity_curve.append((timestamp.isoformat(), equity))
        invested.append((timestamp.isoformat(), float(sum(pending.values()))))
        turnovers.append((timestamp.isoformat(), turnover))
        fees.append((timestamp.isoformat(), fee_value))
        slippages.append((timestamp.isoformat(), slippage_value))
        benchmark_returns.append((timestamp.isoformat(), float(np.mean(bench_components)) if bench_components else 0.0))
        trade_count += sum(
            1
            for asset in current_assets
            if abs(pending.get(asset, 0.0) - executed_weights.get(asset, 0.0)) > 0
        )
        executed_weights = dict(pending)
        # Signals use only information available at the close and execute next period.
        pending, selected = _signal_weights(dataset, timestamp, config)
        selected_assets.append((timestamp.isoformat(), selected))
    backtest = MultiAssetBacktestResult(
        dataset_fingerprint=dataset.fingerprint,
        strategy_id="cross-sectional-lagged-momentum",
        strategy_version="v1",
        config=config,
        equity_curve=tuple(equity_curve),
        returns=tuple(returns),
        invested_weights=tuple(invested),
        turnover=tuple(turnovers),
        benchmark_returns=tuple(benchmark_returns),
        selected_assets=tuple(selected_assets),
        fees=tuple(fees),
        slippage=tuple(slippages),
        trade_count=trade_count,
    )
    evaluation = _evaluate(backtest)
    if validity is None:
        from .validity import ResearchValidity

        validity = ResearchValidity.default_p5_5()
    if not getattr(validity, "is_complete", False):
        raise ValueError("validity profile must classify every required dimension")
    timestamp = dates[-1].isoformat()
    identifier = run_id or f"momentum-{backtest.fingerprint[:16]}"
    # ResearchRun retains its existing single-series schema; the full panel
    # fingerprint and records remain in the artifact/provenance envelope.
    benchmark_index = [1.0]
    for value in benchmark_returns[1:]:
        benchmark_index.append(benchmark_index[-1] * (1.0 + value[1]))
    series = pd.DataFrame({"close": benchmark_index}, index=pd.to_datetime(dates))
    research_dataset = Dataset(
        frame=series,
        provenance=Provenance(provider=dataset.provider, source_url=dataset.source_url),
    )
    factor = momentum_factor(config.lookback)
    provenance = {
        "dataset_version": dataset.fingerprint,
        "panel_schema": "date,asset,close,available_at",
        "strategy_version": backtest.strategy_version,
        "engine_version": "p5.5-multi-asset-v1",
        "parameters": config.to_dict(),
        "timestamp": timestamp,
        "timestamp_kind": "dataset_as_of",
        "result_fingerprint": backtest.fingerprint,
        "evaluation_fingerprint": evaluation.fingerprint,
        "validity": validity.to_dict(),
        "warnings": list(evaluation.warnings),
        "limitations": list(evaluation.limitations),
        "oos": {"is_oos": False, "selection": "fixed_pre_registered_parameters"},
        "code_commit": _code_commit(),
        "dependency_versions": _dependency_versions(),
        "lookback_semantics": "last available observations, not a calendar interpolation",
    }
    artifact = Artifact.create(
        artifact_id=f"artifact-{identifier}",
        artifact_type="cross_sectional_momentum_evaluation",
        payload={"backtest_result": backtest.to_dict(), "evaluation_report": evaluation.to_dict(), "provenance": provenance},
        created_at=timestamp,
    )
    research_run = ResearchRun.create(
        run_id=f"research-{identifier}",
        created_at=timestamp,
        question=question,
        hypothesis=hypothesis,
        dataset=research_dataset,
        factor=factor,
        method="cross_sectional_lagged_momentum",
        parameters={**config.to_dict(), **provenance, "artifact_fingerprint": artifact.fingerprint},
        result={
            "quant_run_id": identifier,
            "backtest_fingerprint": backtest.fingerprint,
            "evaluation_fingerprint": evaluation.fingerprint,
            "artifact_fingerprint": artifact.fingerprint,
            "metrics": evaluation.metrics,
            "warnings": list(evaluation.warnings),
        },
        conclusion="The fixed experiment reports descriptive separation evidence; it does not establish future performance or causality.",
        insight="Momentum ranking and next-period execution were evaluated with explicit costs and a deterministic benchmark.",
        limitations=list(evaluation.limitations),
        engine_version="p5.5-multi-asset-v1",
    )
    quant_run = QuantRun.create(
        quant_run_id=identifier,
        research_run_id=research_run.run_id,
        dataset_version=dataset.fingerprint,
        strategy_version=backtest.strategy_version,
        engine_version="p5.5-multi-asset-v1",
        parameters={**config.to_dict(), "validity": validity.to_dict(), "warnings": list(evaluation.warnings), "result_fingerprint": backtest.fingerprint},
        result_artifact=artifact,
        timestamp=timestamp,
    )
    return MultiAssetExperimentResult(
        quant_run=quant_run,
        research_run=research_run,
        artifact=artifact,
        backtest=backtest,
        evaluation=evaluation,
        validity=validity,
        warnings=evaluation.warnings,
        limitations=evaluation.limitations,
    )
