"""Natural-language strategy review for the two P6.6 reference templates."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from .features import feature_graph_for_template
from .models import StrategyReview, StrategySpec


class StrategyInterpreter:
    """Map a bounded natural-language idea to an explicit, reviewable spec.

    This is intentionally a small allow-list, not a general language-to-code
    runtime.  Unknown ideas are rejected so that assumptions cannot be hidden
    in an unreviewed parser interpretation.
    """

    def review(
        self,
        idea: str,
        *,
        strategy_id: str | None = None,
        version: str = "v1",
        dataset_reference: str = "dataset-under-review",
        universe: str | None = None,
    ) -> StrategyReview:
        if not isinstance(idea, str) or not idea.strip():
            raise ValueError("strategy idea is required")
        text = idea.strip()
        normalized = re.sub(r"\s+", " ", text.lower())
        if any(token in normalized for token in ("moving average", "moving-average", "trend", "均线", "趋势")):
            template = "moving_average_trend"
            default_id = "moving_average_trend"
        elif any(token in normalized for token in ("momentum", "low volatility", "low-volatility", "动量", "低波动")):
            template = "lagged_momentum_low_volatility"
            default_id = "lagged_momentum_low_volatility"
        else:
            raise ValueError("idea is outside the supported P6.6 templates")
        graph, feature_versions = feature_graph_for_template(template)
        resolved_id = strategy_id or default_id
        if template == "lagged_momentum_low_volatility":
            spec = StrategySpec(
                strategy_id=resolved_id,
                version=version,
                name="Lagged momentum with low-volatility filter",
                original_idea=text,
                research_question="Does lagged momentum among lower-volatility assets improve risk-adjusted returns after costs?",
                hypothesis="Assets with stronger lagged momentum and volatility below the threshold may have better subsequent returns, but the effect may not persist out of sample.",
                universe=universe or "approved multi-asset price universe",
                dataset_reference=dataset_reference,
                feature_versions=feature_versions,
                feature_graph_fingerprint=graph.fingerprint,
                signal_rule="Use the lagged 20-day momentum feature.",
                filter_rule="Exclude observations whose lagged 20-day annualized volatility exceeds 0.60.",
                ranking_rule="Rank surviving assets by lagged momentum within each date.",
                selection_rule="Select the top eligible assets; use equal weights.",
                entry_rule="Enter at the next valid period after the signal.",
                exit_rule="Exit when the asset is no longer eligible or selected.",
                position_sizing="Equal-weight selected assets, capped at 1.0 absolute portfolio weight.",
                portfolio_construction="Long-only; target weights sum to at most 1.0.",
                rebalance_frequency="daily",
                execution_timing="next_period_open_or_first_valid_bar",
                risk_constraints=("long_only", "max_abs_weight=1.0", "no_lookahead", "explicit_costs"),
                cost_model={"fee_bps": 5.0, "slippage_bps": 5.0},
                validation_design={"method": "walk_forward", "oos_required": True, "multiple_testing": "report_only"},
                parameters={"template": template, "volatility_threshold": 0.60, "selection_fraction": 0.20},
                limitations=("No causal claim is made.", "Survivorship and universe construction can dominate results.", "The volatility threshold is a research parameter, not a guarantee."),
            )
            assumptions = (
                "Momentum and volatility are lagged before any signal is formed.",
                "The selected universe and asset history are supplied by an approved dataset.",
                "Equal weights and explicit fee/slippage assumptions are used.",
                "Execution occurs on the next valid period, never at the signal close.",
            )
        else:
            spec = StrategySpec(
                strategy_id=resolved_id,
                version=version,
                name="Lagged moving-average trend",
                original_idea=text,
                research_question="Does a lagged moving-average trend rule produce useful historical evidence after costs?",
                hypothesis="A close above its lagged 20-day moving average may support a long target weight, though regime changes and costs can erase the effect.",
                universe=universe or "one approved price series",
                dataset_reference=dataset_reference,
                feature_versions=feature_versions,
                feature_graph_fingerprint=graph.fingerprint,
                signal_rule="Go long when the latest close is above the lagged 20-day moving average.",
                filter_rule="No additional filter.",
                ranking_rule="Not applicable to a single series.",
                selection_rule="Use the single approved asset.",
                entry_rule="Enter at the next valid period after the signal.",
                exit_rule="Set target weight to zero when close is at or below the moving average.",
                position_sizing="Use a fixed 0.75 long target weight.",
                portfolio_construction="Long-only single-asset target weighting.",
                rebalance_frequency="daily",
                execution_timing="next_period_open_or_first_valid_bar",
                risk_constraints=("long_only", "max_abs_weight=1.0", "no_lookahead", "explicit_costs"),
                cost_model={"fee_bps": 5.0, "slippage_bps": 5.0},
                validation_design={"method": "walk_forward", "oos_required": True, "multiple_testing": "report_only"},
                parameters={"template": template, "moving_average_window": 20, "target_weight": 0.75},
                limitations=("Single-series evidence is not a portfolio recommendation.", "Moving averages can lag regime changes.", "Historical evidence does not forecast future returns."),
            )
            assumptions = (
                "The moving average is lagged before signal formation.",
                "The strategy is long-only with a fixed target weight.",
                "Execution occurs on the next valid period, never at the signal close.",
            )
        warnings = (
            "Review the dataset reference, universe membership, and cost model before accepting.",
            "OOS and multiple-testing diagnostics are required before interpreting performance.",
        )
        return StrategyReview(spec=spec, assumptions=assumptions, warnings=warnings, reviewed=False)

    def accept(self, review: StrategyReview) -> StrategyReview:
        if not isinstance(review, StrategyReview):
            raise TypeError("review must be a StrategyReview")
        return review.accept()

    def build_spec(self, review: StrategyReview, *, reviewed: bool = False) -> StrategySpec:
        if not isinstance(review, StrategyReview):
            raise TypeError("review must be a StrategyReview")
        if not reviewed and not review.reviewed:
            raise ValueError("explicit reviewed=True acknowledgement is required")
        return replace(review.spec, reviewed=True)


def review_strategy(idea: str, **kwargs: Any) -> StrategyReview:
    return StrategyInterpreter().review(idea, **kwargs)


__all__ = ["StrategyInterpreter", "review_strategy"]
