"""Constrained Strategy IR compiler for the P6.6 reference strategies.

Only reviewed :class:`StrategySpec` objects can reach this module.  The
compiler emits a small internal target-weight strategy for the single-series
moving-average slice.  The panel momentum strategy is represented by an IR
and is dispatched by the P5.5 panel adapter in the lab orchestrator; it is not
silently coerced into a single-asset run.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from finahinking.data.models import Dataset
from finahinking.factors.core import FactorDefinition

from .features import FeatureRegistry, builtin_feature_registry, feature_graph_for_template
from .models import StrategyIR, StrategyIRNode, StrategySpec, StrategyVersion


@dataclass(frozen=True)
class CompiledStrategy:
    """Safe P5 ``Strategy`` adapter produced from reviewed IR only."""

    strategy_id: str
    version: str
    template: str
    ir_fingerprint: str
    registry: FeatureRegistry
    moving_average_feature: str | None = None
    target_weight: float = 0.75
    factor: FactorDefinition | None = None

    def generate(self, dataset: Dataset) -> pd.Series:
        if not isinstance(dataset, Dataset):
            raise TypeError("compiled strategy requires a Dataset")
        if self.template != "moving_average_trend":
            raise ValueError("panel strategies must run through the P5.5 panel adapter")
        feature = self.registry.evaluate(self.moving_average_feature or "moving_average_20d", dataset.frame)
        close = pd.to_numeric(dataset.frame["close"], errors="coerce")
        return (close > feature).astype(float) * float(self.target_weight)


def strategy_ir(spec: StrategySpec, *, reviewed: bool = False) -> StrategyIR:
    """Build the allow-listed IR for a reviewed specification."""
    if not isinstance(spec, StrategySpec):
        raise TypeError("spec must be a StrategySpec")
    if not spec.reviewed and not reviewed:
        raise ValueError("strategy must be explicitly reviewed before compilation")
    if reviewed and not spec.reviewed:
        spec = StrategySpec(
            **{
                **spec.to_dict(),
                "feature_versions": spec.feature_versions,
                "cost_model": spec.cost_model,
                "validation_design": spec.validation_design,
                "parameters": spec.parameters,
                "reviewed": True,
            }
        )
    template = str(spec.parameters.get("template", ""))
    if template == "moving_average_trend":
        window = int(spec.parameters.get("moving_average_window", 20))
        feature_id = feature_graph_for_template(template, moving_average_window=window)[1][0].feature_id
        nodes = (
            StrategyIRNode("moving_average", "feature_ref", feature_id=feature_id, explanation="lagged moving average"),
            StrategyIRNode("trend_compare", "compare", inputs=("moving_average",), parameters={"operator": "gt", "field": "close"}, explanation="close above lagged average"),
            StrategyIRNode("target", "target_weight", inputs=("trend_compare",), parameters={"on": 0.75, "off": 0.0}, explanation="fixed long target"),
            StrategyIRNode("execution", "next_period_execution", inputs=("target",), parameters={"timing": "next_valid_bar"}, explanation="signal is lagged one execution period"),
        )
    elif template == "lagged_momentum_low_volatility":
        lookback = int(spec.parameters.get("lookback", 20))
        volatility_window = int(spec.parameters.get("volatility_window", 20))
        panel_features = feature_graph_for_template(
            template,
            lookback=lookback,
            volatility_window=volatility_window,
        )[1]
        nodes = (
            StrategyIRNode("momentum", "feature_ref", feature_id=panel_features[0].feature_id, explanation="lagged momentum"),
            StrategyIRNode("volatility", "feature_ref", feature_id=panel_features[1].feature_id, explanation="lagged realized volatility"),
            StrategyIRNode("eligible", "boolean", inputs=("volatility",), parameters={"operator": "le", "threshold": float(spec.parameters.get("volatility_threshold", 0.60))}, explanation="low-volatility eligibility"),
            StrategyIRNode("rank", "rank", inputs=("momentum",), parameters={"scope": "date"}, explanation="cross-sectional rank"),
            StrategyIRNode("selection", "selection", inputs=("eligible", "rank"), parameters={"fraction": float(spec.parameters.get("selection_fraction", 0.20))}, explanation="top eligible assets"),
            StrategyIRNode("execution", "next_period_execution", inputs=("selection",), parameters={"timing": "next_valid_period"}, explanation="next-period execution"),
        )
    else:
        raise ValueError("unsupported strategy template")
    return StrategyIR(StrategyVersion(spec), spec.feature_graph_fingerprint, nodes)


class StrategyCompiler:
    """Public compiler facade used by the P6.6 lab orchestration."""

    compiler_version = "p6.6.compiler.1"

    def compile_ir(self, spec: StrategySpec, *, reviewed: bool = False) -> StrategyIR:
        return strategy_ir(spec, reviewed=reviewed)

    def compile(self, spec: StrategySpec, *, reviewed: bool = False, registry: FeatureRegistry | None = None) -> tuple[StrategyIR, CompiledStrategy | None]:
        return compile_strategy(spec, reviewed=reviewed, registry=registry)


def compile_strategy(spec: StrategySpec, *, reviewed: bool = False, registry: FeatureRegistry | None = None) -> tuple[StrategyIR, CompiledStrategy | None]:
    ir = strategy_ir(spec, reviewed=reviewed)
    template = str(spec.parameters.get("template", ""))
    if template == "lagged_momentum_low_volatility":
        return ir, None
    resolved_registry = registry or builtin_feature_registry()
    window = int(spec.parameters.get("moving_average_window", 20))
    feature_id = feature_graph_for_template(template, moving_average_window=window)[1][0].feature_id
    if feature_id not in {item.feature_id for item in resolved_registry.definitions}:
        resolved_registry = resolved_registry.register(feature_graph_for_template(template, moving_average_window=window)[1][0])
    return ir, CompiledStrategy(
        strategy_id=spec.strategy_id,
        version=spec.version,
        template=template,
        ir_fingerprint=ir.fingerprint,
        registry=resolved_registry,
        moving_average_feature=feature_id,
        target_weight=float(spec.parameters.get("target_weight", 0.75)),
        factor=FactorDefinition(
            name=f"{template}_signal",
            definition="Reviewed P6.6 strategy signal; execution is supplied by the constrained compiler.",
            explanation="Metadata link for the existing P5 QuantRun provenance chain.",
            limitations="Historical descriptive evidence only; the factor metadata is not a forecast.",
            compute=lambda prices: pd.Series(index=prices.index, data=0.0),
        ),
    )


__all__ = ["CompiledStrategy", "StrategyCompiler", "compile_strategy", "strategy_ir"]
