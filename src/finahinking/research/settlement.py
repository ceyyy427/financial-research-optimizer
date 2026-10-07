"""Typed, paper-only settlement evidence for the learning boundary.

Settlement is deliberately a value object.  It contains the immutable paper
ledger fingerprint and realized, normalized outcomes; it never accepts a
broker response, model object, prompt, or executable callback.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from .contracts import stable_digest, to_jsonable
from .paper_trader import PaperLedger

_PUBLIC_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE = re.compile(
    r"(?:api[-_]?key|secret|token|password|credential|authorization|prompt|"
    r"raw(?:[-_ ]?provider)?[-_ ]?response|endpoint|private[-_ ]?key|"
    r"file[-_ ]?path|absolute[-_ ]?path)",
    re.IGNORECASE,
)
_SENSITIVE_VALUE = re.compile(
    r"(?:api[-_]?key|secret|token|password|credential|authorization)\s*[=:]|\bprompt\b",
    re.IGNORECASE,
)
_URI = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://")
_PATH = re.compile(r"(?:^|[\s:=])(?:~[\\/]|[\\/]|\.\.?[\\/]|[A-Za-z]:[\\/])")


def _as_date(value: date | str, name: str = "as_of") -> date:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO date") from exc
    if not isinstance(value, date):
        raise TypeError(f"{name} must be a date")
    return value


def _safe(value: Any, path: str = "value") -> Any:
    """Normalize JSON-like values and reject secrets/provider objects."""

    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        return value
    if isinstance(value, str):
        if _URI.search(value) or _PATH.search(value) or _SENSITIVE_VALUE.search(value):
            raise ValueError(f"{path} contains endpoint or path material")
        return value
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, child in value.items():
            if not isinstance(key, str) or not key.strip() or _SENSITIVE.search(key):
                raise ValueError(f"{path} contains sensitive field")
            clean[key.strip()] = _safe(child, f"{path}.{key}")
        return clean
    if isinstance(value, (tuple, list)):
        return tuple(_safe(item, f"{path}[]") for item in value)
    # Dataclasses/raw provider SDK instances are intentionally not coerced.
    raise TypeError(f"{path} must contain normalized JSON data")


def _ledger_date(value: str) -> date | None:
    text = str(value).strip()
    if not text or text.casefold() in {"paper-time", "unknown"}:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class SettlementEvent:
    """A single realized paper outcome at a declared point in time."""

    run_id: str
    ledger: PaperLedger
    as_of: date | str
    realized_outcomes: Mapping[str, Any] = field(default_factory=dict)
    costs: Mapping[str, float] = field(default_factory=dict)
    dataset_digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not _PUBLIC_ID.fullmatch(self.run_id.strip()):
            raise ValueError("run_id must be a stable public identifier")
        object.__setattr__(self, "run_id", self.run_id.strip())
        if not isinstance(self.ledger, PaperLedger) or self.ledger.paper_only is not True:
            raise TypeError("settlement requires a paper-only PaperLedger")
        event_as_of = _as_date(self.as_of)
        object.__setattr__(self, "as_of", event_as_of)
        if not isinstance(self.dataset_digest, str) or not _PUBLIC_ID.fullmatch(self.dataset_digest.strip()):
            raise ValueError("dataset_digest must be a stable public identifier")
        object.__setattr__(self, "dataset_digest", self.dataset_digest.strip())
        if not self.ledger.snapshot_digest:
            raise ValueError("paper ledger snapshot digest is required")
        if self.ledger.snapshot_digest != self.dataset_digest:
            raise ValueError("dataset digest does not match paper ledger snapshot")
        for item in self.ledger.entries:
            entry_date = _ledger_date(item.timestamp)
            if entry_date is not None and entry_date > event_as_of:
                raise ValueError("settlement as_of cannot precede ledger timestamp")
        outcomes = _safe(self.realized_outcomes, "realized_outcomes")
        if not isinstance(outcomes, Mapping):
            raise TypeError("realized_outcomes must be a mapping")
        object.__setattr__(self, "realized_outcomes", dict(outcomes))
        costs = _safe(self.costs, "costs")
        if not isinstance(costs, Mapping):
            raise TypeError("costs must be a mapping")
        normalized_costs: dict[str, float] = {}
        for key, value in costs.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError("settlement costs must be finite numbers")
            if float(value) < 0:
                raise ValueError("settlement costs cannot be negative")
            normalized_costs[str(key)] = float(value)
        object.__setattr__(self, "costs", normalized_costs)

    @property
    def ledger_fingerprint(self) -> str:
        return self.ledger.fingerprint

    @property
    def fingerprint(self) -> str:
        return stable_digest(
            {
                "run_id": self.run_id,
                "ledger_fingerprint": self.ledger_fingerprint,
                "as_of": self.as_of,
                "realized_outcomes": self.realized_outcomes,
                "costs": self.costs,
                "dataset_digest": self.dataset_digest,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "ledger": self.ledger.to_dict(),
            "as_of": self.as_of,
            "realized_outcomes": to_jsonable(self.realized_outcomes),
            "costs": dict(self.costs),
            "dataset_digest": self.dataset_digest,
            "ledger_fingerprint": self.ledger_fingerprint,
            "fingerprint": self.fingerprint,
        }


__all__ = ["SettlementEvent"]
