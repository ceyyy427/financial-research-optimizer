from __future__ import annotations

import time

import pytest

from finahinking.research.agent_roles import (
    AgentRole,
    AgentRuntime,
    AgentStatus,
    RoleCapabilityPolicy,
)
from finahinking.research.contracts import AgentTask, FailureKind


def task(role: str, task_id: str, *, capabilities: tuple[str, ...] = (), required: bool = True) -> AgentTask:
    return AgentTask(
        role=role,
        task_id=task_id,
        input_digest="input-digest",
        capabilities=capabilities,
        required=required,
        timeout_seconds=0.2,
    )


class Driver:
    def __init__(self, delay: float = 0.0, *, fail: bool = False) -> None:
        self.delay = delay
        self.fail = fail

    def run(self, agent_task: AgentTask, context: dict[str, object]) -> dict[str, object]:
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("api_key=secret endpoint=https://private.test")
        return {"status": "READY", "evidence_refs": (f"artifact:{agent_task.role}",)}


def test_runtime_runs_all_roles_and_sorts_stably() -> None:
    tasks = (
        task("risk_manager", "risk-2"),
        task("fundamentals", "fund-1"),
        task("paper_trader", "paper-1", capabilities=("deterministic_paper_gateway",)),
    )

    outcomes = AgentRuntime().run(tasks, Driver(), {"dataset": "fixture"})

    assert [(item.role, item.task_id) for item in outcomes] == [
        ("fundamentals", "fund-1"),
        ("paper_trader", "paper-1"),
        ("risk_manager", "risk-2"),
    ]
    assert all(item.status == AgentStatus.READY for item in outcomes)
    assert all(item.paper_only for item in outcomes)


def test_runtime_normalizes_exception_and_timeout_without_raw_message() -> None:
    failed = AgentRuntime().run((task("news", "news-1"),), Driver(fail=True), {})[0]
    timed_out = AgentRuntime().run((task("news", "news-2"),), Driver(delay=0.5), {})[0]

    assert failed.failure_kind is FailureKind.INTERNAL_ERROR
    assert timed_out.failure_kind is FailureKind.ANALYST_TIMEOUT
    for outcome in (failed, timed_out):
        assert "secret" not in repr(outcome)
        assert "private.test" not in repr(outcome)


def test_runtime_rejects_duplicate_and_missing_required_roles() -> None:
    duplicates = AgentRuntime().run((task("news", "n1"), task("news", "n2")), Driver(), {})
    missing = AgentRuntime().run(
        (task("fundamentals", "f1"),), Driver(), {}, required_roles=("fundamentals", "technical")
    )

    assert all(item.failure_kind is FailureKind.DUPLICATE_ROLE for item in duplicates)
    assert any(item.role == "technical" and item.failure_kind is FailureKind.ANALYST_REQUIRED_MISSING for item in missing)


def test_policy_rejects_capability_escalation_and_live_execution() -> None:
    policy = RoleCapabilityPolicy.default()
    with pytest.raises(ValueError, match="capability"):
        policy.validate(task("risk_manager", "r1", capabilities=("network",)))
    with pytest.raises(ValueError, match="paper"):
        policy.validate(task("paper_trader", "p1", capabilities=("order_gateway",)))

    outcome = AgentRuntime(policy=policy).run(
        (task("paper_trader", "p1", capabilities=("order_gateway",)),), Driver(), {}
    )[0]
    assert outcome.failure_kind is FailureKind.CAPABILITY_DENIED


def test_policy_exposes_deterministic_gateway_only_to_risk_and_paper_roles() -> None:
    policy = RoleCapabilityPolicy.default()
    risk = policy.context_for("risk_manager", {"risk_gateway": object(), "network": object(), "dataset": "fixture"})
    analyst = policy.context_for("technical", {"risk_gateway": object(), "dataset": "fixture"})

    assert "risk_gateway" in risk
    assert "risk_gateway" not in analyst
    assert risk["paper_only"] is True


def test_agent_role_enum_covers_runtime_roles() -> None:
    assert {role.value for role in AgentRole} >= {
        "fundamentals",
        "technical",
        "sentiment",
        "news",
        "learning",
        "research_manager",
        "risk_manager",
        "portfolio_manager",
        "paper_trader",
        "learning_manager",
    }
