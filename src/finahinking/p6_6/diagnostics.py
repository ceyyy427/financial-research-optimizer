"""Bounded paper-vs-backtest and feature-drift diagnostics."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from finahinking.experiments.models import canonical_json


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    if hasattr(value, "item"):
        try:
            return _safe(value.item())
        except (TypeError, ValueError):
            return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _series(value: Any, preferred: tuple[str, ...]) -> pd.Series:
    if isinstance(value, pd.Series):
        result = value.copy()
    elif isinstance(value, Mapping):
        for name in preferred:
            if name in value:
                return _series(value[name], preferred)
        result = pd.Series(value)
    elif any(hasattr(value, name) for name in preferred):
        for name in preferred:
            if hasattr(value, name):
                return _series(getattr(value, name), preferred)
        result = pd.Series(dtype=float)
    elif isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (list, tuple)) and len(value[0]) == 2:
            result = pd.Series({pd.Timestamp(ts): float(v) for ts, v in value})
        else:
            result = pd.Series(value)
    else:
        result = pd.Series(dtype=float)
    if len(result):
        try:
            result.index = pd.to_datetime(result.index)
        except (TypeError, ValueError):
            pass
    return pd.to_numeric(result, errors="coerce")


@dataclass(frozen=True)
class BacktestPaperComparison:
    backtest_fingerprint: str
    paper_fingerprint: str
    aligned_points: int
    backtest_final_equity: float | None
    paper_final_equity: float | None
    final_equity_delta: float | None
    mean_return_delta: float | None
    max_abs_equity_delta: float | None
    backtest_trade_count: int
    paper_fill_count: int
    interpretation: str
    limitations: tuple[str, ...] = ("comparison is descriptive, not validation of future performance",)

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema_version": 1, "backtest_fingerprint": self.backtest_fingerprint, "paper_fingerprint": self.paper_fingerprint, "aligned_points": self.aligned_points, "backtest_final_equity": self.backtest_final_equity, "paper_final_equity": self.paper_final_equity, "final_equity_delta": self.final_equity_delta, "mean_return_delta": self.mean_return_delta, "max_abs_equity_delta": self.max_abs_equity_delta, "backtest_trade_count": self.backtest_trade_count, "paper_fill_count": self.paper_fill_count, "interpretation": self.interpretation, "limitations": list(self.limitations)}
        return {**payload, "fingerprint": _digest(payload)}

    @property
    def fingerprint(self) -> str:
        return self.to_dict()["fingerprint"]


def compare_backtest_paper(backtest: Any, paper: Any) -> BacktestPaperComparison:
    """Compare aligned equity/return series without treating paper as live evidence."""
    bt_equity = _series(backtest, ("equity_curve", "equity"))
    pp_equity = _series(paper, ("portfolios", "equity_curve", "equity"))
    if "portfolios" in (paper if isinstance(paper, Mapping) else {}):
        portfolio_values = paper["portfolios"]
        pp_equity = pd.Series({pd.Timestamp(item.get("timestamp")): float(item["equity"]) for item in portfolio_values})
    elif hasattr(paper, "portfolios"):
        pp_equity = pd.Series({pd.Timestamp(item.timestamp): float(item.equity) for item in paper.portfolios})
    bt_returns = _series(backtest, ("returns",))
    pp_returns = _series(paper, ("returns",))
    if not len(pp_returns) and len(pp_equity):
        pp_returns = pp_equity.pct_change().fillna(0.0)
    aligned = pd.concat([bt_equity.rename("backtest"), pp_equity.rename("paper")], axis=1, join="inner").dropna()
    return_aligned = pd.concat([bt_returns.rename("backtest"), pp_returns.rename("paper")], axis=1, join="inner").dropna()
    final_bt = float(bt_equity.iloc[-1]) if len(bt_equity) else None
    final_pp = float(pp_equity.iloc[-1]) if len(pp_equity) else None
    delta = None if final_bt is None or final_pp is None else final_pp - final_bt
    mean_delta = float((return_aligned["paper"] - return_aligned["backtest"]).mean()) if len(return_aligned) else None
    max_delta = float((aligned["paper"] - aligned["backtest"]).abs().max()) if len(aligned) else None
    bt_fingerprint = str(getattr(backtest, "fingerprint", None) or (backtest.get("fingerprint") if isinstance(backtest, Mapping) else "unknown"))
    pp_fingerprint = str(getattr(paper, "fingerprint", None) or (paper.get("fingerprint") if isinstance(paper, Mapping) else "unknown"))
    bt_trades = getattr(backtest, "trades", None) or (backtest.get("trades", ()) if isinstance(backtest, Mapping) else ())
    pp_fills = getattr(paper, "fills", None) or (paper.get("fills", ()) if isinstance(paper, Mapping) else ())
    return BacktestPaperComparison(bt_fingerprint, pp_fingerprint, len(aligned), final_bt, final_pp, delta, mean_delta, max_delta, len(bt_trades), len(pp_fills), "Differences reflect replay timing, costs, and state alignment; inspect before drawing conclusions.")


@dataclass(frozen=True)
class FeatureDriftReport:
    baseline_reference: str
    comparison_reference: str
    features: Mapping[str, Mapping[str, float | int | None]]
    ranked_features: tuple[str, ...]
    threshold: float
    drift_detected: bool
    limitations: tuple[str, ...] = ("distributional drift is a monitoring signal, not a causal diagnosis",)

    def __post_init__(self) -> None:
        if not 0 <= float(self.threshold):
            raise ValueError("threshold must be non-negative")
        object.__setattr__(self, "threshold", float(self.threshold))
        object.__setattr__(self, "ranked_features", tuple(str(v) for v in self.ranked_features))

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema_version": 1, "baseline_reference": self.baseline_reference, "comparison_reference": self.comparison_reference, "features": _safe(self.features), "ranked_features": list(self.ranked_features), "threshold": self.threshold, "drift_detected": self.drift_detected, "limitations": list(self.limitations)}
        return {**payload, "fingerprint": _digest(payload)}

    @property
    def fingerprint(self) -> str:
        return self.to_dict()["fingerprint"]


def _feature_frame(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, Mapping):
        columns: dict[str, Any] = {}
        for name, series in value.items():
            if isinstance(series, pd.Series):
                columns[str(name)] = series
            elif isinstance(series, (list, tuple, np.ndarray)):
                columns[str(name)] = list(series)
            else:
                columns[str(name)] = [series]
        return pd.DataFrame(columns)
    raise TypeError("features must be a DataFrame or mapping")


def feature_drift(baseline: Any, comparison: Any, *, baseline_reference: str = "baseline", comparison_reference: str = "comparison", threshold: float = 0.2) -> FeatureDriftReport:
    base = _feature_frame(baseline)
    current = _feature_frame(comparison)
    names = sorted(set(map(str, base.columns)) & set(map(str, current.columns)))
    metrics: dict[str, dict[str, float | int | None]] = {}
    for name in names:
        lhs = pd.to_numeric(base[name], errors="coerce")
        rhs = pd.to_numeric(current[name], errors="coerce")
        bmean, cmean = float(lhs.mean()), float(rhs.mean())
        bstd, cstd = float(lhs.std(ddof=0)), float(rhs.std(ddof=0))
        scale = max(abs(bstd), abs(bmean), 1e-12)
        ks_proxy = abs(bmean - cmean) / scale
        variance_ratio = (cstd / max(bstd, 1e-12)) if bstd else (0.0 if cstd == 0 else math.inf)
        missing_delta = float(rhs.isna().mean() - lhs.isna().mean())
        metrics[name] = {"baseline_mean": bmean, "comparison_mean": cmean, "baseline_std": bstd, "comparison_std": cstd, "mean_shift": ks_proxy, "variance_ratio": variance_ratio if math.isfinite(variance_ratio) else None, "missing_rate_delta": missing_delta, "sample_baseline": int(lhs.notna().sum()), "sample_comparison": int(rhs.notna().sum())}
    ranked = tuple(sorted(names, key=lambda n: float(metrics[n]["mean_shift"] or 0.0), reverse=True))
    detected = any(float(metrics[name]["mean_shift"] or 0) > float(threshold) or abs(float(metrics[name]["missing_rate_delta"] or 0)) > float(threshold) for name in names)
    return FeatureDriftReport(baseline_reference, comparison_reference, metrics, ranked, threshold, detected)


compute_feature_drift = feature_drift


__all__ = ["BacktestPaperComparison", "FeatureDriftReport", "compare_backtest_paper", "compute_feature_drift", "feature_drift"]
