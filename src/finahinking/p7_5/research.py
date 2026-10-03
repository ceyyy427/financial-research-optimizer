"""Local, bounded P7.5 research runtime.

The local application is deliberately a thin client of this module.  The
runtime owns the deterministic authored fixture, calls the P5/P6.6 engines,
and writes the resulting provenance envelope into the authenticated P7
repository.  No payload can provide code, callables, paths, or an execution
command.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from finahinking.data.models import Dataset, Provenance
from finahinking.features.core import returns, volatility
from finahinking.p6_6 import StrategyResearchLab
from finahinking.p6_6.backtest import BacktestConfiguration
from finahinking.p6_6.diagnostics import compare_backtest_paper
from finahinking.p6_6.models import canonical_json
from finahinking.p6_6.validation import evaluate_frozen_oos, make_oos_plan
from finahinking.p7.models import LearningThread, PersonalNode
from finahinking.p7.workflows import StrategyJourneyInput, StrategyPersonalCommunityWorkflow
from finahinking.quant.regression import RegressionDependencyUnavailable, run_regression_experiment
from finahinking.quant.runtime import _code_commit
from finahinking.quant.splits import Period

_LIMITATIONS = (
    "The authored fixture is deterministic historical evidence, not a forecast.",
    "Survivorship, liquidity, taxes, and market impact are not modeled.",
    "Out-of-sample and paper results remain replay diagnostics, not investment advice.",
)
_STRATEGY_KEYS = frozenset({"mode", "idea", "options"})
_OPTION_KEYS = frozenset({"moving_average_window", "fee_bps", "slippage_bps", "starting_cash"})
_QUANT_KEYS = frozenset({"question", "hypothesis"})


def _safe(value: Any) -> Any:
    """Convert engine objects and numeric scalars into strict JSON values."""

    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return _safe(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(_safe(value)).encode("utf-8")).hexdigest()


def _text(payload: Mapping[str, Any], key: str, default: str) -> str:
    value = payload.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _reject_unknown(payload: Mapping[str, Any], allowed: frozenset[str], label: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"unsupported option: {', '.join(unknown)}")


def _authored_frame() -> pd.DataFrame:
    """Return the project-authored 96-observation deterministic price fixture."""

    n = 96
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    index = np.arange(n, dtype=float)
    market_returns = 0.00035 + 0.0018 * np.sin(index / 6.0) + 0.00055 * np.cos(index / 11.0)
    asset_returns = 0.00020 + 0.82 * market_returns + 0.00045 * np.sin(index / 3.7)
    # Keep every generated price strictly positive while making the fixture
    # sufficiently non-flat for both volatility and OLS uncertainty.
    market_close = 100.0 * np.cumprod(1.0 + market_returns)
    close = 100.0 * np.cumprod(1.0 + asset_returns)
    return pd.DataFrame({"close": close, "market_close": market_close}, index=dates)


def _ols(y: pd.Series, x: pd.Series) -> tuple[float, float, tuple[float, float]]:
    observations = pd.concat((y.rename("y"), x.rename("x")), axis=1).dropna()
    if len(observations) < 40:
        raise ValueError("authored regression sample must contain at least 40 observations")
    design = np.column_stack((np.ones(len(observations)), observations["x"].to_numpy(float)))
    target = observations["y"].to_numpy(float)
    coefficients, _, _, _ = np.linalg.lstsq(design, target, rcond=None)
    residuals = target - design @ coefficients
    degrees_of_freedom = len(target) - design.shape[1]
    if degrees_of_freedom <= 0:
        raise ValueError("regression has no residual degrees of freedom")
    covariance = (residuals @ residuals / degrees_of_freedom) * np.linalg.inv(design.T @ design)
    standard_error = float(np.sqrt(max(float(covariance[1, 1]), 0.0)))
    beta = float(coefficients[1])
    return beta, standard_error, (beta - 1.96 * standard_error, beta + 1.96 * standard_error)


class LocalResearchService:
    """Run bounded quant and strategy research for one authenticated session."""

    def __init__(self, repository: Any, session_id: str, artifact_root: str | Path) -> None:
        if repository is None or not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("repository and session_id are required")
        self.repository = repository
        self.session_id = session_id.strip()
        self.artifact_root = Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        # Fail early on an invalid/expired session instead of doing work that
        # cannot be linked to the user's private timeline.
        self.repository._principal(self.session_id)

    def _write_artifact(self, node_id: str, result: dict[str, Any]) -> str:
        path = self.artifact_root / f"{node_id}.json"
        path.write_text(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False), encoding="utf-8")
        return str(path)

    def get_artifact(self, node_id: str) -> dict[str, Any]:
        """Read a private artifact through the authenticated P7 repository."""

        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id is required")
        node = self.repository.get_node(self.session_id, node_id.strip())
        return {"node_id": node.node_id, "node_type": node.node_type, "title": node.title, **node.payload}

    def run_quant(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {} if payload is None else payload
        if not isinstance(request, dict):
            raise TypeError("quant payload must be a JSON object")
        _reject_unknown(request, _QUANT_KEYS, "quant option")
        frame = _authored_frame()
        asset_returns = returns(frame["close"]).rename("asset_return")
        market_returns = returns(frame["market_close"]).rename("market_return")
        rolling_volatility = volatility(asset_returns, window=20, annualization=252.0).rename("volatility")
        beta, beta_se, beta_ci = _ols(asset_returns, market_returns)
        observations = pd.concat((asset_returns, market_returns), axis=1).dropna()
        split_index = 72
        if len(observations) <= split_index or len(observations) - split_index < 10:
            raise ValueError("authored dataset split is too small")
        dataset_fingerprint = _digest(
            {
                "provider": "finahinking-authored-fixture",
                "source_url": "internal://p7.5-authored-research-v1",
                "records": frame.reset_index(names="date").to_dict(orient="records"),
            }
        )
        sample = []
        for timestamp in frame.index[20:25]:
            sample.append(
                {
                    "date": pd.Timestamp(timestamp).isoformat(),
                    "return": float(asset_returns.loc[timestamp]),
                    "volatility": float(rolling_volatility.loc[timestamp]),
                }
            )
        numeric_results: dict[str, Any] = {
            "sample_count": len(observations),
            "return_mean": float(observations["asset_return"].mean()),
            "return_volatility": float(observations["asset_return"].std(ddof=1) * np.sqrt(252.0)),
            "beta": beta,
            "beta_standard_error": beta_se,
            "beta_ci95": list(beta_ci),
        }
        regression_status = "numpy_ols"
        # Use the governed regression adapter when its optional dependency is
        # present.  The local runtime still has a genuine OLS implementation
        # when the isolated adapter environment omits statsmodels.
        try:
            regression = run_regression_experiment(
                observations.reset_index(names="date"),
                target="asset_return",
                features=("market_return",),
                question=_text(request, "question", "How does the market relate to asset returns?"),
                hypothesis=_text(request, "hypothesis", "Market returns have a measurable historical beta to asset returns."),
            )
            adapter_params = regression.regression.parameters
            adapter_uncertainty = regression.regression.uncertainty or {}
            numeric_results["beta"] = float(adapter_params.get("market_return", beta))
            numeric_results["uncertainty"] = _safe(adapter_uncertainty)
            regression_status = "governed_ols_adapter"
        except RegressionDependencyUnavailable:
            numeric_results["uncertainty"] = {"method": "residual_standard_error", "confidence": 0.95}
        numeric_results["regression_status"] = regression_status
        split_dates = observations.index
        dataset_payload = {
            "provider": "finahinking-authored-fixture",
            "source_url": "internal://p7.5-authored-research-v1",
            "observation_count": len(frame),
            "split": {"train_count": split_index, "test_count": int(len(observations) - split_index)},
            "fingerprint": dataset_fingerprint,
            "sample": sample,
        }
        code_commit = _code_commit()
        node_id = f"quant-{dataset_fingerprint[:16]}"
        result: dict[str, Any] = {
            "node_id": node_id,
            "node_type": "quant_run",
            "dataset": dataset_payload,
            "numeric_results": _safe(numeric_results),
            "code_commit": code_commit,
            "limitations": list(_LIMITATIONS),
            "provenance": {
                "service": "finahinking.p7_5.LocalResearchService",
                "dataset_fingerprint": dataset_fingerprint,
                "code_commit": code_commit,
                "split": {"train_end": pd.Timestamp(split_dates[split_index - 1]).isoformat(), "test_start": pd.Timestamp(split_dates[split_index]).isoformat()},
            },
        }
        result["artifact_fingerprint"] = _digest(result)
        node_payload = {**result, "artifact_fingerprint": result["artifact_fingerprint"]}
        try:
            self.repository.get_node(self.session_id, node_id)
        except KeyError:
            self.repository.save_node(self.session_id, PersonalNode(node_id, "quant_run", "Quant research run", node_payload))
            self.repository.save_history_entry(
                self.session_id,
                history_id=f"history-{node_id}",
                source_kind="quant",
                source_id=node_id,
                source_fingerprint=result["artifact_fingerprint"],
                event_type="completed",
                title="Quant returns and volatility research",
                occurred_at=pd.Timestamp(frame.index[-1]).isoformat(),
                limitations=_LIMITATIONS,
            )
        else:
            self.repository.update_node(self.session_id, node_id, node_payload)
        self.repository.link_artifact(self.session_id, "quant", node_id, result["artifact_fingerprint"], tuple(result), code_commit=code_commit)
        thread_id = f"thread-{node_id}"
        existing_threads = self.repository.connection.execute("SELECT 1 FROM p7_learning_threads WHERE thread_id = ?", (thread_id,)).fetchone()
        if existing_threads is None:
            self.repository.create_learning_thread(self.session_id, LearningThread(thread_id, "Quant research learning", (node_id,)))
        result["learning_thread_id"] = thread_id
        result["artifact_path"] = str(self.artifact_root / f"{node_id}.json")
        self._write_artifact(node_id, result)
        return _safe(result)

    def run_strategy(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {} if payload is None else payload
        if not isinstance(request, dict):
            raise TypeError("strategy payload must be a JSON object")
        _reject_unknown(request, _STRATEGY_KEYS, "strategy option")
        mode = request.get("mode", "guided")
        if mode not in {"guided", "advanced"}:
            raise ValueError("mode must be guided or advanced")
        options = request.get("options", {})
        if not isinstance(options, dict):
            raise TypeError("options must be a JSON object")
        _reject_unknown(options, _OPTION_KEYS, "strategy option")
        idea = _text(request, "idea", "moving average trend")
        moving_average_window = int(options.get("moving_average_window", 20))
        if moving_average_window < 1 or moving_average_window > 120:
            raise ValueError("moving_average_window must be between 1 and 120")
        fee_bps = float(options.get("fee_bps", 5.0))
        slippage_bps = float(options.get("slippage_bps", 5.0))
        starting_cash = float(options.get("starting_cash", 100_000.0))
        for value, label in ((fee_bps, "fee_bps"), (slippage_bps, "slippage_bps"), (starting_cash, "starting_cash")):
            if not math.isfinite(value) or value < 0 or (label == "starting_cash" and value <= 0):
                raise ValueError(f"{label} is invalid")
        if "momentum" in idea.lower() or "low volatility" in idea.lower():
            raise ValueError("the local strategy runtime currently supports the single-series moving-average template")
        lab = StrategyResearchLab()
        review = lab.interpreter.accept(
            lab.review(
                idea,
                strategy_id=str(request.get("strategy_id", "p75-moving-average")),
                moving_average_window=moving_average_window,
                dataset_reference="internal://p7.5-authored-research-v1",
            )
        )
        data = Dataset(_authored_frame()[["close"]], Provenance("finahinking-authored-fixture", "internal://p7.5-authored-research-v1"))
        config = BacktestConfiguration(starting_cash=starting_cash, fee_bps=fee_bps, slippage_bps=slippage_bps)
        lab_run = lab.run(review, data, config=config, paper=True, run_id=f"p75-{review.spec.strategy_id}-{review.spec.version}")
        historical = lab_run.historical or {}
        backtest = historical["backtest"]
        evaluation = historical["evaluation"]
        train_end = data.frame.index[59] + pd.Timedelta(days=1)
        validation_end = data.frame.index[71] + pd.Timedelta(days=1)
        test_end = data.frame.index[-1] + pd.Timedelta(days=1)
        plan = make_oos_plan(
            Period(data.frame.index[0], train_end),
            Period(validation_end, test_end),
            validation=Period(train_end, validation_end),
            hypothesis=review.spec.hypothesis,
            frozen_configuration={"strategy_fingerprint": review.spec.fingerprint, "feature_graph_fingerprint": lab_run.ir.feature_graph_fingerprint, "cost_model": config.to_dict()},
        )
        observations = {timestamp: value for timestamp, value in backtest.returns if plan.test_period.contains(timestamp)}
        oos = evaluate_frozen_oos(plan, observations)
        paper = lab_run.paper
        comparison = lab_run.comparison or compare_backtest_paper(backtest, paper)
        learning = lab_run.learning
        educational = lab_run.educational_code
        code_commit = str(historical["quant_run"].parameters.get("code_commit", _code_commit()))
        limitations = tuple(dict.fromkeys((*_LIMITATIONS, *review.spec.limitations, *evaluation.limitations, *(paper.limitations if paper else ()), *comparison.limitations)))
        result: dict[str, Any] = {
            "node_id": review.spec.strategy_id,
            "mode": mode,
            "strategy": _safe(lab_run.spec.to_dict()),
            "strategy_fingerprint": lab_run.spec.fingerprint,
            "feature": {"fingerprint": lab_run.ir.feature_graph_fingerprint, "graph": _safe(lab_run.ir.to_dict())},
            "feature_fingerprint": lab_run.ir.feature_graph_fingerprint,
            "backtest": _safe(backtest.to_dict()),
            "backtest_fingerprint": backtest.fingerprint,
            "oos": _safe(oos.to_dict()),
            "oos_fingerprint": oos.fingerprint,
            "paper": _safe(paper.to_dict() if paper else None),
            "paper_fingerprint": paper.fingerprint if paper else None,
            "compare": _safe(comparison.to_dict()),
            "compare_fingerprint": comparison.fingerprint,
            "learning": _safe(learning.to_dict() if learning else None),
            "learning_fingerprint": learning.fingerprint if learning else None,
            "code": _safe(educational.to_dict() if educational else None),
            "numeric_results": _safe(evaluation.metrics),
            "code_commit": code_commit,
            "limitations": list(limitations),
            "provenance": {"dataset_fingerprint": backtest.dataset_fingerprint, "quant_run_id": historical["quant_run"].quant_run_id, "research_run_id": historical["research_run"].run_id, "code_commit": code_commit},
        }
        result["artifact_fingerprint"] = _digest(result)
        # P7 personal nodes have a deliberately small JSON payload limit.  The
        # complete run remains in the local artifact file and the node keeps
        # the provenance, fingerprints, and numeric evidence needed to resume
        # the learning thread.
        node_result = dict(result)
        node_result["backtest"] = {"fingerprint": result["backtest_fingerprint"], "metrics": result["numeric_results"]}
        node_result["paper"] = {"fingerprint": result["paper_fingerprint"]}
        node_result["compare"] = {"fingerprint": result["compare_fingerprint"]}
        node_result["learning"] = {"fingerprint": result["learning_fingerprint"]}
        node_result["code"] = {"fingerprint": _digest(result.get("code")) if result.get("code") is not None else None}
        journey = StrategyJourneyInput.from_lab_run(
            self.session_id,
            lab_run,
            payload=node_result,
            oos_fingerprint=oos.fingerprint,
            concept_ids=(),
            code_commit=code_commit,
            strategy_limitations=limitations,
        )
        try:
            self.repository.get_node(self.session_id, result["node_id"])
        except KeyError:
            StrategyPersonalCommunityWorkflow(self.repository).run(journey)
        else:
            # Guided and advanced views intentionally share one StrategySpec
            # and therefore one private strategy node.  A second view updates
            # that node in place while retaining the original history entry
            # and learning thread.
            self.repository.update_node(
                self.session_id,
                result["node_id"],
                {
                    **node_result,
                    "source_kind": "strategy",
                    "source_id": result["node_id"],
                    "source_fingerprint": result["strategy_fingerprint"],
                    "strategy_fingerprint": result["strategy_fingerprint"],
                    "limitations": list(limitations),
                },
            )
        result["artifact_path"] = str(self.artifact_root / f"{result['node_id']}.json")
        self._write_artifact(result["node_id"], result)
        return _safe(result)


__all__ = ["LocalResearchService"]
