from __future__ import annotations

import math
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
    gateway = object()
    risk = policy.context_for("risk_manager", {"risk_gateway": gateway, "network": object(), "dataset": "fixture"}, capabilities=("risk_gateway",))
    analyst = policy.context_for("technical", {"risk_gateway": gateway, "dataset": "fixture"})

    assert risk["risk_gateway"] is gateway
    assert "risk_gateway" not in analyst
    assert risk["paper_only"] is True


def test_runtime_blocks_live_statuses_and_direct_non_paper_outcomes() -> None:
    live = AgentRuntime().run(
        (task("paper_trader", "p1", capabilities=("paper_gateway",)),),
        lambda _task, _context: {"status": "ORDER_SENT"},
        {},
    )[0]
    assert live.failure_kind is FailureKind.PAPER_ONLY_VIOLATION
    with pytest.raises(ValueError, match="paper-only"):
        from finahinking.research.contracts import AgentOutcome

        AgentOutcome(role="paper_trader", task_id="p2", input_digest="d", paper_only=False)


def test_contracts_reject_secrets_and_arbitrary_task_inputs() -> None:
    with pytest.raises((TypeError, ValueError)):
        AgentTask(role="news", task_id="n1", input_digest="d", inputs={"api_key": "secret"})
    with pytest.raises((TypeError, ValueError)):
        AgentTask(role="news", task_id="n2", input_digest="d", inputs={"value": object()})


def test_optional_task_failures_are_not_marked_required() -> None:
    outcome = AgentRuntime().run(
        (task("news", "n1", required=False),),
        lambda _task, _context: (_ for _ in ()).throw(RuntimeError("failure")),
        {},
    )[0]
    assert outcome.status == "OPTIONAL_FAILED"
    assert outcome.failure_kind is FailureKind.INTERNAL_ERROR


def test_runtime_requires_real_booleans_for_mapping_paper_flags() -> None:
    for key, value in (("paper_only", 0), ("live", 1)):
        outcome = AgentRuntime().run(
            (task("paper_trader", "p1", capabilities=("paper_gateway",)),),
            lambda _task, _context, key=key, value=value: {key: value},
            {},
        )[0]
        assert outcome.failure_kind is FailureKind.PAPER_ONLY_VIOLATION


def test_allowed_tools_are_the_declared_role_capability_intersection() -> None:
    policy = RoleCapabilityPolicy.default()
    context = policy.context_for(
        "risk_manager",
        {"risk_gateway": object(), "dataset": "fixture"},
        capabilities=("risk_gateway", "deterministic_risk_gateway"),
    )
    assert context["allowed_tools"] == ("deterministic_risk_gateway", "risk_gateway")


def test_optional_none_invalid_and_typed_failures_are_optional_failed() -> None:
    from finahinking.research.contracts import AgentOutcome

    results = (
        lambda _task, _context: None,
        lambda _task, _context: object(),
        lambda task_value, _context: AgentOutcome(
            role=task_value.role,
            task_id=task_value.task_id,
            input_digest=task_value.input_digest,
            status="FAILED",
            failure_kind=FailureKind.INTERNAL_ERROR,
        ),
    )
    for driver in results:
        outcome = AgentRuntime().run((task("news", "n1", required=False),), driver, {})[0]
        assert outcome.status == "OPTIONAL_FAILED"

    mismatch = AgentRuntime().run(
        (task("news", "n1", required=False),),
        lambda task_value, _context: AgentOutcome(role=task_value.role, task_id="other", input_digest=task_value.input_digest),
        {},
    )[0]
    assert mismatch.failure_kind is FailureKind.VALIDATION_FAILED
    assert mismatch.status == "REJECTED"


def test_task_inputs_reject_nonfinite_numbers_and_nested_paths() -> None:
    for value in (math.nan, math.inf, "src/foo.py", "./relative.txt", "https://private.test/data"):
        with pytest.raises((TypeError, ValueError)):
            AgentTask(role="news", task_id="n1", input_digest="d", inputs={"nested": {"value": value}})


def test_outcome_failure_and_evidence_fields_are_strict_and_secret_free() -> None:
    from finahinking.research.contracts import AgentOutcome

    with pytest.raises((TypeError, ValueError)):
        AgentOutcome(role="news", task_id="n1", input_digest="d", failure_kind=object())
    with pytest.raises((TypeError, ValueError)):
        AgentOutcome(role="news", task_id="n1", input_digest="d", evidence_refs=("src/private/report.json",))


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
