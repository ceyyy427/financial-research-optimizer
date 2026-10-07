"""Provider-neutral, paper-only runtime for governed research roles.

The runtime owns scheduling and failure normalization.  It does not execute
model supplied code, expose arbitrary tools, or turn role output into a live
decision.  Deterministic gateways are passed only to the roles that explicitly
declare them in :class:`RoleCapabilityPolicy`.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import (
    AgentOutcome,
    AgentReport,
    AgentRole,
    AgentTask,
    FailureKind,
    stable_digest,
)
from .drivers import DriverResult


class AgentStatus(str, Enum):
    READY = "READY"
    OFFLINE = "OFFLINE"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    REJECTED = "REJECTED"
    DUPLICATE_ROLE = "DUPLICATE_ROLE"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    OPTIONAL_FAILED = "OPTIONAL_FAILED"


@dataclass(frozen=True, slots=True)
class _RoleRule:
    input_names: frozenset[str]
    capabilities: frozenset[str]


_PAPER_DENY = re.compile(r"(?:broker|order|cancel|account|live|credential|secret|network)", re.IGNORECASE)
_SENSITIVE = re.compile(r"(?:api[-_]?key|secret|token|password|authorization|endpoint|absolute[-_]?path|file[-_]?path)", re.IGNORECASE)


class RoleCapabilityPolicy:
    """Allowlist of role inputs and deterministic gateways.

    A policy is intentionally small and immutable.  Callers can construct a
    custom policy for a test fixture, while ``default`` provides the governed
    production boundary used by the runtime.
    """

    def __init__(self, rules: Mapping[str, _RoleRule] | None = None) -> None:
        self._rules = dict(rules or self._default_rules())

    @classmethod
    def _default_rules(cls) -> dict[str, _RoleRule]:
        analyst_inputs = frozenset({"dataset", "snapshot", "evidence", "request", "research_plan", "as_of"})
        return {
            role.value: _RoleRule(analyst_inputs, frozenset({"paper_only"}))
            for role in (
                AgentRole.FUNDAMENTALS,
                AgentRole.TECHNICAL,
                AgentRole.SENTIMENT,
                AgentRole.NEWS,
                AgentRole.LEARNING,
            )
        } | {
            AgentRole.RESEARCH_MANAGER.value: _RoleRule(
                frozenset({"analyst_reports", "evidence_refs", "request", "research_plan", "as_of"}), frozenset({"paper_only"})
            ),
            AgentRole.RISK_MANAGER.value: _RoleRule(
                frozenset({"risk_gateway", "deterministic_gateway", "snapshot", "factor_result", "constraints", "dataset", "as_of"}),
                frozenset({"risk_gateway", "deterministic_risk_gateway", "deterministic_gateway", "paper_only"}),
            ),
            AgentRole.PORTFOLIO_MANAGER.value: _RoleRule(
                frozenset({"portfolio_gateway", "deterministic_gateway", "risk_result", "candidates", "constraints", "snapshot", "as_of"}),
                frozenset({"portfolio_gateway", "deterministic_portfolio_gateway", "deterministic_gateway", "paper_only"}),
            ),
            AgentRole.PAPER_TRADER.value: _RoleRule(
                frozenset({"paper_gateway", "deterministic_gateway", "proposal", "snapshot", "execution_policy", "constraints", "as_of"}),
                frozenset({"paper_gateway", "deterministic_paper_gateway", "deterministic_gateway", "paper_only"}),
            ),
            AgentRole.LEARNING_MANAGER.value: _RoleRule(
                frozenset({"settlement", "history", "ledger", "as_of", "research_plan"}), frozenset({"paper_only"})
            ),
        }

    @classmethod
    def default(cls) -> RoleCapabilityPolicy:
        return cls()

    def rule_for(self, role: AgentRole | str) -> _RoleRule:
        name = role.value if isinstance(role, AgentRole) else str(role).strip().casefold()
        try:
            return self._rules[name]
        except KeyError as exc:
            raise ValueError(f"unknown agent role: {name}") from exc

    def validate(self, task: AgentTask) -> None:
        rule = self.rule_for(task.role)
        requested = {str(item).strip().casefold() for item in task.capabilities}
        if any(_PAPER_DENY.search(item) for item in requested):
            raise ValueError("capability denied: paper-only runtime denies live, broker, account, order, and network capabilities")
        denied = requested - rule.capabilities
        if denied:
            raise ValueError(f"capability denied for {task.role}: {', '.join(sorted(denied))}")

    def context_for(self, role: AgentRole | str, context: Mapping[str, Any]) -> dict[str, Any]:
        rule = self.rule_for(role)
        drop = object()

        def scrub(key: str, value: Any) -> Any:
            if _SENSITIVE.search(key) or _PAPER_DENY.search(key):
                return drop
            if callable(value):
                return drop
            if value is None or isinstance(value, (bool, int, float, str)):
                return value
            if isinstance(value, Mapping):
                return {
                    str(child_key): child_value
                    for child_key, child in value.items()
                    if isinstance(child_key, str)
                    and not _SENSITIVE.search(child_key)
                    and not _PAPER_DENY.search(child_key)
                    and (child_value := scrub(child_key, child)) is not drop
                }
            if isinstance(value, (list, tuple)):
                items = [item for item in (scrub(key, child) for child in value) if item is not drop]
                return tuple(items) if isinstance(value, tuple) else items
            # Deterministic gateways are opaque objects; their names are
            # allowlisted and they never enter a digest or serialized contract.
            return value if key in rule.input_names else drop

        safe: dict[str, Any] = {}
        for key, value in context.items():
            if not isinstance(key, str) or key not in rule.input_names:
                continue
            cleaned = scrub(key, value)
            if cleaned is not drop:
                safe[key] = cleaned
        safe.update(
            {
                "agent_role": str(role),
                "paper_only": True,
                "allowed_tools": tuple(sorted(item for item in rule.capabilities if item != "paper_only")),
            }
        )
        return safe


def _failure_digest(role: str, task_id: str, status: str, failure_kind: Any) -> str:
    return stable_digest(
        {
            "role": role,
            "task_id": task_id,
            "status": status,
            "failure_kind": failure_kind.value if isinstance(failure_kind, Enum) else str(failure_kind),
        }
    )


def _failure_outcome(task: AgentTask, status: str, kind: FailureKind, *, evidence_refs: Sequence[str] = ()) -> AgentOutcome:
    return AgentOutcome(
        role=task.role,
        task_id=task.task_id,
        input_digest=task.input_digest,
        capabilities=task.capabilities,
        status=status,
        failure_kind=kind,
        message_digest=_failure_digest(task.role, task.task_id, status, kind),
        evidence_refs=tuple(evidence_refs),
        paper_only=True,
    )


class AgentRuntime:
    """Run bounded role tasks concurrently and return stable, typed outcomes."""

    def __init__(self, *, policy: RoleCapabilityPolicy | None = None, max_workers: int = 8) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self.policy = policy or RoleCapabilityPolicy.default()
        self.max_workers = max_workers

    def run(
        self,
        tasks: Sequence[AgentTask],
        driver: Any,
        context: Mapping[str, Any] | None = None,
        *,
        required_roles: Sequence[str] = (),
    ) -> tuple[AgentOutcome, ...]:
        supplied = tuple(tasks)
        context = dict(context or {})
        counts = Counter(task.role for task in supplied)
        duplicate_roles = {role for role, count in counts.items() if count > 1}
        outcomes: list[AgentOutcome] = []
        valid: list[AgentTask] = []
        for task in supplied:
            if task.role in duplicate_roles:
                outcomes.append(_failure_outcome(task, AgentStatus.DUPLICATE_ROLE.value, FailureKind.DUPLICATE_ROLE))
                continue
            try:
                self.policy.validate(task)
            except ValueError:
                outcomes.append(_failure_outcome(task, AgentStatus.REJECTED.value, FailureKind.CAPABILITY_DENIED))
                continue
            valid.append(task)

        present = {task.role for task in supplied}
        for role in required_roles:
            normalized = str(role).strip().casefold()
            if normalized not in present:
                missing = AgentTask(
                    role=normalized,
                    task_id=f"missing:{normalized}",
                    input_digest=stable_digest({"role": normalized, "missing": True}),
                    required=True,
                )
                outcomes.append(_failure_outcome(missing, AgentStatus.MISSING_REQUIRED.value, FailureKind.ANALYST_REQUIRED_MISSING))

        if valid:
            executor = ThreadPoolExecutor(max_workers=min(self.max_workers, len(valid)), thread_name_prefix="finathink-agent")
            submitted: dict[Future[Any], tuple[AgentTask, float]] = {}
            try:
                for task in valid:
                    submitted[executor.submit(self._invoke, task, driver, context)] = (task, time.monotonic())
                pending = set(submitted)
                while pending:
                    done, _ = wait(pending, timeout=0.01)
                    for future in done:
                        pending.discard(future)
                        task, _started = submitted[future]
                        try:
                            outcomes.append(future.result())
                        except Exception:  # noqa: BLE001 - normalize driver boundary failures
                            outcomes.append(_failure_outcome(task, AgentStatus.FAILED.value, FailureKind.INTERNAL_ERROR))
                    now = time.monotonic()
                    for future in tuple(pending):
                        task, started = submitted[future]
                        if now - started >= task.timeout_seconds:
                            pending.remove(future)
                            future.cancel()
                            outcomes.append(_failure_outcome(task, AgentStatus.TIMEOUT.value, FailureKind.ANALYST_TIMEOUT))
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

        return tuple(sorted(outcomes, key=lambda item: (item.role, item.task_id)))

    def _invoke(self, task: AgentTask, driver: Any, context: Mapping[str, Any]) -> AgentOutcome:
        merged = dict(context)
        merged.update(task.inputs)
        safe_context = self.policy.context_for(task.role, merged)
        result = self._call_driver(driver, task, safe_context)
        return self._normalize_result(task, result)

    @staticmethod
    def _call_driver(driver: Any, task: AgentTask, context: Mapping[str, Any]) -> Any:
        if isinstance(driver, Mapping):
            selected = driver.get(task.role)
            if selected is None:
                raise TypeError("driver mapping has no implementation for role")
            return selected(task, context) if callable(selected) else selected
        if callable(driver):
            return driver(task, context)
        for name in ("run", "execute", "propose"):
            method = getattr(driver, name, None)
            if method is None:
                continue
            if name == "propose" and context.get("request") is not None:
                return method(context["request"], context)
            try:
                return method(task, context)
            except TypeError:
                request = context.get("request")
                if request is not None:
                    return method(request, context)
                raise
        raise TypeError("driver must be callable or expose run/execute/propose")

    def _normalize_result(self, task: AgentTask, result: Any) -> AgentOutcome:
        if isinstance(result, AgentOutcome):
            if result.role != task.role or result.input_digest != task.input_digest:
                return _failure_outcome(task, AgentStatus.REJECTED.value, FailureKind.VALIDATION_FAILED)
            if not result.paper_only:
                return _failure_outcome(task, AgentStatus.REJECTED.value, FailureKind.PAPER_ONLY_VIOLATION)
            if not set(result.capabilities).issubset(task.capabilities):
                return _failure_outcome(task, AgentStatus.REJECTED.value, FailureKind.CAPABILITY_DENIED)
            return result

        report: AgentReport | None = None
        if isinstance(result, DriverResult):
            if result.failure_kind is not None or result.requires_external_turn:
                kind = result.failure_kind or FailureKind.PROVIDER_NOT_CONFIGURED
                if not isinstance(kind, FailureKind):
                    kind = FailureKind.INTERNAL_ERROR
                return _failure_outcome(task, AgentStatus.FAILED.value, kind)
            reports = tuple(item for item in result.reports if item.role.casefold() == task.role)
            if len(reports) != 1:
                return _failure_outcome(task, AgentStatus.FAILED.value, FailureKind.VALIDATION_FAILED)
            report = reports[0]
        elif isinstance(result, AgentReport):
            report = result

        if report is not None:
            status = report.status.upper()
            if status == "FAILED":
                return _failure_outcome(task, AgentStatus.FAILED.value, FailureKind.INTERNAL_ERROR, evidence_refs=report.evidence_refs)
            return AgentOutcome(
                role=task.role,
                task_id=task.task_id,
                input_digest=task.input_digest,
                capabilities=task.capabilities,
                status=status,
                evidence_refs=report.evidence_refs,
                output_digest=stable_digest({"status": status, "evidence_refs": report.evidence_refs}),
            )

        if isinstance(result, Mapping):
            if result.get("paper_only") is False or result.get("live") is True:
                return _failure_outcome(task, AgentStatus.REJECTED.value, FailureKind.PAPER_ONLY_VIOLATION)
            status = str(result.get("status", AgentStatus.READY.value)).upper()
            kind = result.get("failure_kind")
            if kind is not None:
                try:
                    kind = FailureKind(kind)
                except ValueError:
                    kind = FailureKind.INTERNAL_ERROR
            refs = tuple(str(item) for item in result.get("evidence_refs", ()))
            return AgentOutcome(
                role=task.role,
                task_id=task.task_id,
                input_digest=task.input_digest,
                capabilities=task.capabilities,
                status=status,
                failure_kind=kind,
                evidence_refs=refs,
                output_digest=stable_digest({"status": status, "evidence_refs": refs}),
            )
        return _failure_outcome(task, AgentStatus.FAILED.value, FailureKind.VALIDATION_FAILED)


__all__ = [
    "AgentOutcome",
    "AgentRole",
    "AgentRuntime",
    "AgentStatus",
    "AgentTask",
    "RoleCapabilityPolicy",
]
