"""Server-side research view models for the P8.2 local workspace.

The browser receives a small, already-normalized payload.  It may render and
select values, but it never derives returns, features, signals, or scores.
This module is intentionally independent from optional Qlib/vectorbt/QMT SDKs;
those systems can only enter through the Finathink-owned contracts and source
adapters.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Any

from finahinking.p8_2.contracts import DatasetSnapshot, MarketObservation


def _number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _observation_dict(item: MarketObservation) -> dict[str, Any]:
    return item.to_dict()


def _fixture_snapshot() -> DatasetSnapshot:
    """Load the deterministic fixture through the P8.2 source boundary."""

    from finahinking.p8_2.data_sources import FixtureMarketDataSource

    return FixtureMarketDataSource().snapshot()


def _sweep_payload(dataset: DatasetSnapshot) -> dict[str, Any]:
    """Return a bounded, transparent parameter sweep for the sample chart."""

    from finahinking.p8_2.contracts import ParameterSweepSpecification
    from finahinking.p8_2.sweeps import run_parameter_sweep

    spec = ParameterSweepSpecification(
        strategy_version="fixture-momentum-v1",
        parameter_ranges={"window": (3, 5, 8), "threshold": (0.0, 0.01)},
        train_scope={"start": "2026-01-01", "end": "2026-01-04"},
        validation_scope={"start": "2026-01-04", "end": "2026-01-06"},
        oos_scope={"start": "2026-01-06", "end": "2026-01-10"},
        parameters={"dataset_fingerprint": dataset.fingerprint},
    )

    def evaluate(parameters: dict[str, object]) -> dict[str, object]:
        window = _number(parameters["window"], "window")
        threshold = _number(parameters["threshold"], "threshold")
        train_score = round((window / 100.0) + threshold, 6)
        # This is a deterministic fixture metric, not a claim about a best
        # strategy.  The OOS value is deliberately retained beside train.
        return {
            "train": {"score": train_score},
            "validation": {"score": round(train_score - 0.003, 6)},
            "oos": {"score": round(train_score - 0.01, 6)},
        }

    result = run_parameter_sweep(spec, evaluate)
    payload = result.to_dict()
    payload["dataset_fingerprint"] = dataset.fingerprint
    payload["selection_policy"] = spec.selection_policy
    return payload


def build_research_payload(snapshot: DatasetSnapshot | None = None) -> dict[str, Any]:
    """Build the canonical JSON payload consumed by the research workspace."""

    dataset = snapshot or _fixture_snapshot()
    observations = tuple(dataset.observations)
    previous_close: float | None = None
    points: list[dict[str, Any]] = []
    for index, item in enumerate(observations):
        close = _number(item.close, "close")
        one_period_return = 0.0 if previous_close is None else round((close / previous_close) - 1.0, 8)
        range_pct = round((item.high - item.low) / item.close, 8)
        points.append(
            {
                "id": f"{item.instrument}-{item.timestamp.strftime('%Y%m%dT%H%M%SZ')}",
                "instrument": item.instrument,
                "time": item.timestamp.isoformat(),
                "open": _number(item.open, "open"),
                "high": _number(item.high, "high"),
                "low": _number(item.low, "low"),
                "close": close,
                "volume": _number(item.volume, "volume"),
                "features": {
                    "return_1d": one_period_return,
                    "range_pct": range_pct,
                    "close_rank": round((index + 1) / len(observations), 8),
                },
                "events": ["fixture-start"] if index == 0 else [],
                "signal": "observation",
                "source": item.source,
                "provider": item.provider,
                "available_at": item.available_at.isoformat(),
            }
        )
        previous_close = close

    feature_meta = [
        {
            "id": "return_1d",
            "label": "One-period return",
            "definition": "Close_t / Close_(t-1) − 1; first observation is explicitly 0 in the fixture.",
            "source": "server-normalized fixture",
            "lookahead": "not used",
        },
        {
            "id": "range_pct",
            "label": "Intraday range",
            "definition": "(High − Low) / Close",
            "source": "server-normalized fixture",
            "lookahead": "not used",
        },
        {
            "id": "close_rank",
            "label": "Chronological close rank",
            "definition": "Position in the ordered sample, not a predictive score.",
            "source": "server-normalized fixture",
            "lookahead": "descriptive only",
        },
    ]
    events = [
        {
            "id": "fixture-start",
            "label": "Fixture start",
            "kind": "DATASET",
            "description": "First available observation in the deterministic sample.",
            "source": dataset.provenance.get("source", "finathink.fixture"),
        }
    ]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "view": "research-series",
        "dataset": {
            "id": dataset.dataset_id,
            "fingerprint": dataset.fingerprint,
            "mode": dataset.mode,
            "as_of": dataset.as_of.isoformat(),
            "provider": dataset.provenance.get("provider", "finahinking.fixture"),
            "source": dataset.provenance.get("source", "deterministic fixture"),
            "pit_available": dataset.pit_available(dataset.as_of),
            "limitations": list(dataset.limitations),
        },
        "points": points,
        "features": feature_meta,
        "events": events,
        "sweep": _sweep_payload(dataset),
        "limitations": list(dataset.limitations)
        + [
            "Sample data only; no live market feed is connected.",
            "Feature values are descriptive fixture outputs, not forecasts or trading instructions.",
            "Parameter results retain train, validation, OOS, and multiple-testing warnings.",
        ],
    }
    payload["payload_fingerprint"] = _digest(payload)
    return payload


def capability_payload() -> dict[str, Any]:
    """Return capability status without importing optional SDK modules."""

    from finahinking.p8_2.capabilities import CapabilityRegistry

    return CapabilityRegistry.detect().to_dict()


def qmt_payload() -> dict[str, Any]:
    """Return the read-only QMT bridge status and its explicit boundary."""

    from finahinking.p8_2.qmt import QMTBridgeClient

    status = QMTBridgeClient().status()
    return {
        **status.to_dict(),
        "permissions": ["market_data_read", "snapshot_read"],
        "denied": ["order_stock", "cancel_order", "account_read", "passwords"],
    }


def ml_payload(dataset: DatasetSnapshot | None = None) -> dict[str, Any]:
    """Describe the ML lab with a typed optional-adapter result."""

    snapshot = dataset or _fixture_snapshot()
    from finahinking.p8_2.adapters import QlibResearchAdapter
    from finahinking.p8_2.contracts import MLResearchSpecification

    spec = MLResearchSpecification(
        research_id="fixture-ml-v1",
        dataset_fingerprint=snapshot.fingerprint,
        target="close",
        features=("close", "volume"),
        train_scope={"start": "2026-01-01", "end": "2026-01-04"},
        validation_scope={"start": "2026-01-04", "end": "2026-01-06"},
        test_scope={"start": "2026-01-06", "end": "2026-01-10"},
    )
    result = QlibResearchAdapter(force_unavailable=True).run(spec, snapshot)
    return {
        "specification": spec.to_dict(),
        "result": result.to_dict(),
        "boundary": "Qlib is an optional sandbox; raw Qlib objects never cross this response boundary.",
    }


def parameter_payload(dataset: DatasetSnapshot | None = None) -> dict[str, Any]:
    payload = build_research_payload(dataset)
    sweep = payload["sweep"]
    return {
        "dataset": payload["dataset"],
        "sweep": sweep,
        "interpretation": {
            "oos_first": True,
            "multiple_testing_visible": True,
            "selection_policy": sweep.get("selection_policy", "pre_specified"),
            "warning": "This view compares declared experiments; it does not name a best strategy.",
        },
    }


def utc_now_label() -> str:
    """Stable-format helper used only for UI copy, never for data timestamps."""

    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
