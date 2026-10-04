"""Typed P6.6 research configuration and adapters to frozen P5/P5.5 runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from finahinking.data.models import Dataset
from finahinking.quant.interfaces import BacktestConfig
from finahinking.quant.multi_asset import (
    CrossSectionalMomentumConfig,
    MultiAssetDataset,
    run_cross_sectional_momentum_experiment,
)
from finahinking.quant.runtime import run_quant_experiment

from .compiler import CompiledStrategy, compile_strategy
from .models import StrategySpec


@dataclass(frozen=True)
class BacktestConfiguration:
    starting_cash: float = 100_000.0
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    frequency: str = "daily"
    benchmark: str = "buy_and_hold"
    max_abs_weight: float = 1.0
    allow_negative_cash: bool = False
    universe: str = "approved-dataset"
    as_of: str | None = None

    def to_p5(self) -> BacktestConfig:
        return BacktestConfig(
            starting_cash=self.starting_cash,
            fee_bps=self.fee_bps,
            slippage_bps=self.slippage_bps,
            frequency=self.frequency,
            benchmark=self.benchmark,
            max_abs_weight=self.max_abs_weight,
            allow_negative_cash=self.allow_negative_cash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "starting_cash": self.starting_cash,
            "fee_bps": self.fee_bps,
            "slippage_bps": self.slippage_bps,
            "frequency": self.frequency,
            "benchmark": self.benchmark,
            "max_abs_weight": self.max_abs_weight,
            "allow_negative_cash": self.allow_negative_cash,
            "universe": self.universe,
            "as_of": self.as_of,
        }


@dataclass(frozen=True)
class ResearchPreview:
    strategy_id: str
    template: str
    accepted: bool
    execution_authority: str
    mapped_configuration: Mapping[str, Any]
    rejections: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "template": self.template,
            "accepted": self.accepted,
            "execution_authority": self.execution_authority,
            "mapped_configuration": dict(self.mapped_configuration),
            "rejections": list(self.rejections),
            "warnings": list(self.warnings),
        }


def _panel_configuration(
    spec: StrategySpec,
    config: BacktestConfiguration | CrossSectionalMomentumConfig | None,
) -> CrossSectionalMomentumConfig:
    """Resolve panel execution settings from the reviewed spec and explicit config."""

    if isinstance(config, CrossSectionalMomentumConfig):
        return config
    parameters = spec.parameters
    if config is None:
        cost_model = spec.cost_model
        starting_cash = 100_000.0
        fee_bps = float(cost_model.get("fee_bps", 5.0))
        slippage_bps = float(cost_model.get("slippage_bps", 5.0))
    else:
        starting_cash = config.starting_cash
        fee_bps = config.fee_bps
        slippage_bps = config.slippage_bps
    max_abs_weight = config.max_abs_weight if isinstance(config, BacktestConfiguration) else 1.0
    return CrossSectionalMomentumConfig(
        lookback=int(parameters.get("lookback", 20)),
        top_fraction=float(parameters.get("selection_fraction", 0.20)),
        starting_cash=starting_cash,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        max_abs_weight=max_abs_weight,
    )


def preview_backtest(spec: StrategySpec, config: BacktestConfiguration | None = None) -> ResearchPreview:
    if not isinstance(spec, StrategySpec):
        raise TypeError("spec must be a StrategySpec")
    resolved = config or BacktestConfiguration()
    template = str(spec.parameters.get("template", ""))
    rejections: list[str] = []
    warnings = ["Historical descriptive evidence only; OOS and validity review remain required."]
    if resolved.max_abs_weight <= 0 or resolved.max_abs_weight > 1:
        rejections.append("max_abs_weight must be in (0, 1]")
    if template == "moving_average_trend":
        authority = "p5.BacktestEngine"
        try:
            mapped = resolved.to_p5().to_dict()
        except (TypeError, ValueError) as exc:
            rejections.append(str(exc))
            mapped = resolved.to_dict()
    elif template == "lagged_momentum_low_volatility":
        authority = "p5.5.multi_asset_ledger"
        mapped = _panel_configuration(spec, config).to_dict()
        mapped.update({"volatility_window": int(spec.parameters.get("volatility_window", 20)), "volatility_threshold": float(spec.parameters.get("volatility_threshold", 0.60))})
    else:
        authority = "none"
        mapped = resolved.to_dict()
        rejections.append("unsupported strategy template")
    return ResearchPreview(spec.strategy_id, template, not rejections, authority, mapped, tuple(rejections), tuple(warnings))


def run_historical_backtest(
    spec: StrategySpec,
    dataset: Dataset,
    config: BacktestConfiguration | None = None,
    *,
    question: str | None = None,
    hypothesis: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run one reviewed strategy through an existing authoritative ledger."""
    if not isinstance(spec, StrategySpec) or not spec.reviewed:
        raise ValueError("a reviewed StrategySpec is required")
    if not isinstance(dataset, Dataset):
        raise TypeError("dataset must be a Dataset")
    resolved = config or BacktestConfiguration()
    preview = preview_backtest(spec, resolved)
    if not preview.accepted:
        raise ValueError("; ".join(preview.rejections))
    ir, compiled = compile_strategy(spec)
    template = str(spec.parameters.get("template", ""))
    if template == "moving_average_trend":
        assert isinstance(compiled, CompiledStrategy)
        quant_run, research_run, evaluation, backtest = run_quant_experiment(
            dataset,
            resolved.to_p5(),
            question=question or spec.research_question,
            hypothesis=hypothesis or spec.hypothesis,
            conclusion="The result is descriptive historical evidence and not a forecast.",
            insight="The constrained moving-average signal was executed with explicit next-bar costs.",
            strategy=compiled,
            run_id=run_id or f"p6-6-{spec.strategy_id}-{spec.version}",
        )
        return {"kind": "single_asset", "preview": preview, "ir": ir, "quant_run": quant_run, "research_run": research_run, "evaluation": evaluation, "backtest": backtest}
    raise ValueError("panel execution requires a MultiAssetDataset; use run_panel_backtest")


def run_panel_backtest(
    spec: StrategySpec,
    dataset: MultiAssetDataset,
    config: BacktestConfiguration | CrossSectionalMomentumConfig | None = None,
    *,
    question: str | None = None,
    hypothesis: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(spec, StrategySpec) or not spec.reviewed:
        raise ValueError("a reviewed StrategySpec is required")
    if str(spec.parameters.get("template", "")) != "lagged_momentum_low_volatility":
        raise ValueError("run_panel_backtest accepts only the reference panel template")
    ir, _ = compile_strategy(spec)
    resolved = _panel_configuration(spec, config)
    experiment = run_cross_sectional_momentum_experiment(
        dataset,
        resolved,
        question=question or spec.research_question,
        hypothesis=hypothesis or spec.hypothesis,
        run_id=run_id or f"p6-6-{spec.strategy_id}-{spec.version}",
        strategy_id=spec.strategy_id,
        strategy_version=spec.version,
        volatility_window=int(spec.parameters.get("volatility_window", 20)),
        volatility_threshold=float(spec.parameters.get("volatility_threshold", 0.60)),
    )
    return {"kind": "multi_asset", "ir": ir, "experiment": experiment, "preview": preview_backtest(spec)}


__all__ = ["BacktestConfiguration", "ResearchPreview", "preview_backtest", "run_historical_backtest", "run_panel_backtest"]
