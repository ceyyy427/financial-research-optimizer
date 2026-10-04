"""Bounded factor graph and append-only research-session history."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from .workbench import ResearchCharter, _digest, _finite, _id, _safe

ALLOWED_PRIMITIVES = frozenset({"input", "return", "rolling", "lag", "normalize", "rank", "winsorize", "combine", "filter"})
ATTEMPT_STATUSES = frozenset({"PENDING", "KEEP", "REJECTED", "SUPERSEDED"})


def _time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _freeze_node(value: Mapping[str, Any]) -> Mapping[str, Any]:
    def immutable(item: Any) -> Any:
        if isinstance(item, dict):
            return MappingProxyType({key: immutable(child) for key, child in item.items()})
        if isinstance(item, list):
            return tuple(immutable(child) for child in item)
        return item

    return immutable(_safe(value, "factor_node"))


@dataclass(frozen=True, slots=True)
class FactorGraphSpec:
    factor_id: str
    version: str
    nodes: tuple[Mapping[str, Any], ...]
    outputs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "factor_id", _id(self.factor_id, "factor_id"))
        object.__setattr__(self, "version", _id(self.version, "version"))
        nodes = tuple(_freeze_node(node) for node in self.nodes)
        if not nodes:
            raise ValueError("factor graph requires at least one node")
        node_map = {str(node.get("id")): node for node in nodes}
        if len(node_map) != len(nodes) or any(not node_id or node_id == "None" for node_id in node_map):
            raise ValueError("factor graph node ids must be unique")
        for node in nodes:
            primitive = node.get("primitive")
            if primitive not in ALLOWED_PRIMITIVES:
                raise ValueError(f"primitive {primitive!r} is not allow-listed")
            inputs = tuple(node.get("inputs", ()))
            if any(input_id not in node_map for input_id in inputs):
                raise ValueError("factor graph input is missing")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("factor graph contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for input_id in tuple(node_map[node_id].get("inputs", ())):
                visit(input_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_map:
            visit(node_id)
        outputs = tuple(str(output) for output in self.outputs)
        if not outputs or any(output not in node_map for output in outputs):
            raise ValueError("factor graph outputs must reference nodes")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "outputs", outputs)

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return _safe({"factor_id": self.factor_id, "version": self.version, "nodes": self.nodes, "outputs": self.outputs, "fingerprint": _digest({"factor_id": self.factor_id, "version": self.version, "nodes": self.nodes, "outputs": self.outputs})})


def _topological(graph: FactorGraphSpec) -> tuple[Mapping[str, Any], ...]:
    node_map = {str(node["id"]): node for node in graph.nodes}
    ordered: list[Mapping[str, Any]] = []
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        for dependency in tuple(node_map[node_id].get("inputs", ())):
            visit(dependency)
        visited.add(node_id)
        ordered.append(node_map[node_id])

    for node_id in node_map:
        visit(node_id)
    return tuple(ordered)


def evaluate_factor_graph(graph: FactorGraphSpec, observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not observations:
        return []
    rows = [dict(_safe(row, "observation")) for row in observations]
    for row in rows:
        if _time(row["available_at"]) > _time(row["time"]):
            raise ValueError("available_at cannot be later than signal time")
        row["instrument"] = _id(row["instrument"], "instrument")
    rows.sort(key=lambda row: (_time(row["time"]), row["instrument"]))
    by_asset: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_asset[row["instrument"]].append((index, row))
    values: dict[str, dict[int, float | None]] = defaultdict(dict)
    availability: dict[str, dict[int, str | None]] = defaultdict(dict)
    for node in _topological(graph):
        node_id = str(node["id"])
        primitive = str(node["primitive"])
        inputs = tuple(node.get("inputs", ()))
        if primitive == "input":
            field = str(node.get("field", ""))
            if not field:
                raise ValueError("input primitive requires field")
            for index, row in enumerate(rows):
                raw = row.get(field)
                values[node_id][index] = None if raw is None else _finite(raw, f"{node_id}.{field}")
                availability[node_id][index] = str(row["available_at"])
        elif primitive == "return":
            window = int(node.get("window", 1))
            if window < 1:
                raise ValueError("return window must be positive")
            for asset_rows in by_asset.values():
                for position, (index, _row) in enumerate(asset_rows):
                    if position < window:
                        values[node_id][index] = None
                        availability[node_id][index] = None
                        continue
                    current = values[inputs[0]].get(index)
                    previous_index = asset_rows[position - window][0]
                    previous = values[inputs[0]].get(previous_index)
                    values[node_id][index] = None if current is None or previous in (None, 0) else current / previous - 1
                    availability[node_id][index] = availability[inputs[0]].get(index)
        elif primitive == "lag":
            periods = int(node.get("periods", 1))
            if periods < 1:
                raise ValueError("lag periods must be positive")
            for asset_rows in by_asset.values():
                for position, (index, _row) in enumerate(asset_rows):
                    source = asset_rows[position - periods][0] if position >= periods else None
                    values[node_id][index] = values[inputs[0]].get(source) if source is not None else None
                    availability[node_id][index] = availability[inputs[0]].get(source) if source is not None else None
        elif primitive == "rolling":
            window = int(node.get("window", 5))
            for asset_rows in by_asset.values():
                for position, (index, _row) in enumerate(asset_rows):
                    sample = [values[inputs[0]].get(asset_rows[offset][0]) for offset in range(max(0, position - window + 1), position + 1)]
                    valid = [item for item in sample if item is not None]
                    values[node_id][index] = sum(valid) / len(valid) if valid else None
                    availability[node_id][index] = availability[inputs[0]].get(asset_rows[max(0, position - window + 1)][0]) if valid else None
        elif primitive == "combine":
            weights = tuple(node.get("weights", (1.0 for _ in inputs)))
            for index in range(len(rows)):
                sample = [values[input_id].get(index) for input_id in inputs]
                values[node_id][index] = None if any(item is None for item in sample) else sum(float(weight) * float(item) for weight, item in zip(weights, sample, strict=False))
                availability[node_id][index] = min((availability[input_id].get(index) for input_id in inputs if availability[input_id].get(index)), default=None)
        elif primitive == "normalize" or primitive in {"rank", "winsorize", "filter"}:
            for index in range(len(rows)):
                value = values[inputs[0]].get(index)
                values[node_id][index] = value
                availability[node_id][index] = availability[inputs[0]].get(index)
        else:
            raise ValueError(f"unsupported primitive {primitive}")
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        factors = {output: values[output].get(index) for output in graph.outputs}
        available = [availability[output].get(index) for output in graph.outputs if availability[output].get(index)]
        factors["available_at"] = min(available) if available else None
        result.append({**row, "factors": factors, "factor_graph_fingerprint": graph.fingerprint})
    return result


@dataclass(frozen=True, slots=True)
class ResearchAttempt:
    candidate_id: str
    status: str
    metrics: Mapping[str, Any]
    attempt_index: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _id(self.candidate_id, "candidate_id"))
        if self.status not in ATTEMPT_STATUSES:
            raise ValueError("attempt status is not allow-listed")
        object.__setattr__(self, "metrics", MappingProxyType(_safe(self.metrics, "attempt.metrics")))

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "status": self.status, "metrics": dict(self.metrics), "attempt_index": self.attempt_index}


@dataclass(frozen=True, slots=True)
class ResearchSession:
    session_id: str
    charter: ResearchCharter
    state: str
    attempts: tuple[ResearchAttempt, ...] = ()
    selected_candidate: str | None = None
    test_metrics: Mapping[str, Any] | None = None

    @classmethod
    def start(cls, session_id: str, charter: ResearchCharter) -> ResearchSession:
        return cls(_id(session_id, "session_id"), charter, "CHARTER_FROZEN")

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return _safe({"session_id": self.session_id, "charter": self.charter.to_dict(), "state": self.state, "attempts": [attempt.to_dict() for attempt in self.attempts], "selected_candidate": self.selected_candidate, "test_metrics": self.test_metrics})

    def record_attempt(self, candidate_id: str, status: str, metrics: Mapping[str, Any]) -> ResearchSession:
        if status == "BEST" or status not in ATTEMPT_STATUSES:
            raise ValueError("attempt status must be PENDING, KEEP, REJECTED, or SUPERSEDED; no best label")
        if len(self.attempts) >= self.charter.max_experiments:
            raise ValueError("research experiment budget is exhausted")
        if any("test" in str(key).lower() or str(key).lower().startswith("oos") for key in metrics):
            raise ValueError("test/OOS metrics are hidden until the strategy is frozen")
        attempt = ResearchAttempt(candidate_id, status, metrics, len(self.attempts) + 1)
        return replace(self, attempts=self.attempts + (attempt,), state="CANDIDATE_POOL" if status == "KEEP" else self.state)

    def freeze(self, candidate_id: str) -> ResearchSession:
        if not any(attempt.candidate_id == candidate_id and attempt.status == "KEEP" for attempt in self.attempts):
            raise ValueError("only a kept candidate can be frozen")
        return replace(self, state="STRATEGY_FROZEN", selected_candidate=_id(candidate_id, "candidate_id"), charter=self.charter.freeze_test())

    def evaluate_test(self, metrics: Mapping[str, Any]) -> ResearchSession:
        if self.test_metrics is not None:
            raise ValueError("test evaluation is once-only for a frozen version")
        if self.state != "STRATEGY_FROZEN":
            self.charter.assert_test_access()
            raise ValueError("test evaluation requires a frozen strategy")
        return replace(self, state="TEST_EVALUATED", test_metrics=MappingProxyType(_safe(metrics, "test_metrics")))


class WorkbenchStore:
    """Small append-only local store; persistence adapters can wrap this later."""

    def __init__(self) -> None:
        self._versions: dict[str, ResearchSession] = {}
        self._history: dict[str, list[str]] = defaultdict(list)

    def save(self, session: ResearchSession) -> str:
        if not isinstance(session, ResearchSession):
            raise TypeError("session must be a ResearchSession")
        version = f"{session.session_id}:{session.fingerprint[:16]}"
        self._versions[version] = session
        if version not in self._history[session.session_id]:
            self._history[session.session_id].append(version)
        return version

    def open(self, version: str) -> ResearchSession:
        try:
            return self._versions[version]
        except KeyError as exc:
            raise KeyError("research version not found") from exc

    def rollback(self, version: str) -> ResearchSession:
        session = self.open(version)
        history = self._history[session.session_id]
        index = history.index(version)
        return self.open(history[max(0, index - 1)])

    def history(self, session_id: str) -> tuple[str, ...]:
        return tuple(self._history.get(session_id, ()))


__all__ = ["FactorGraphSpec", "ResearchAttempt", "ResearchSession", "WorkbenchStore", "evaluate_factor_graph"]
