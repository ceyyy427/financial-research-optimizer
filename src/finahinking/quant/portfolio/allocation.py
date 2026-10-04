"""Validated target-weight allocation helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping


def validate_target_weights(
    weights: Mapping[str, float],
    *,
    max_weight: float = 1.0,
    long_only: bool = True,
) -> dict[str, float]:
    if not isinstance(weights, Mapping):
        raise TypeError("weights must be a mapping")
    if not math.isfinite(float(max_weight)) or max_weight <= 0 or max_weight > 1:
        raise ValueError("max weight must be in (0, 1]")
    normalized: dict[str, float] = {}
    for asset, value in weights.items():
        if not isinstance(asset, str) or not asset.strip():
            raise ValueError("asset identifier is required")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("weights must be finite")
        if long_only and number < 0:
            raise ValueError("negative weights are not allowed for long-only allocation")
        if abs(number) > max_weight + 1e-12:
            raise ValueError("weight exceeds max weight")
        normalized[asset] = number
    exposure = sum(normalized.values()) if long_only else sum(abs(value) for value in normalized.values())
    if exposure > 1.0 + 1e-12:
        raise ValueError("weight sum exceeds one")
    return {asset: normalized[asset] for asset in sorted(normalized)}


def optimize_equal_weight_allocation(
    assets: Iterable[str],
    *,
    max_weight: float = 1.0,
) -> dict[str, float]:
    """Return a deterministic constrained baseline allocation.

    This is a transparent allocation primitive for research fixtures, not a
    recommendation or an expected-return optimizer. Any uncapped residual is
    represented as cash when ``max_weight`` is below the equal-weight share.
    """

    if isinstance(assets, (str, bytes)) or not isinstance(assets, Iterable):
        raise TypeError("asset universe must be iterable")
    collected = list(assets)
    if any(not isinstance(asset, str) or not asset.strip() for asset in collected):
        raise ValueError("asset identifiers are required")
    names = sorted(set(collected))
    if not names:
        raise ValueError("asset universe must not be empty")
    share = min(1.0 / len(names), float(max_weight))
    return validate_target_weights({asset: share for asset in names}, max_weight=max_weight, long_only=True)
