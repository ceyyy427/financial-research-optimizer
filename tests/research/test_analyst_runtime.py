from __future__ import annotations

import threading
import time
from datetime import date

import pytest

from finahinking.research.analyst_runtime import (
    AnalystFailureKind,
    AnalystPool,
    ResearchManager,
)
from finahinking.research.contracts import AgentReport, FailureKind, ResearchPlan, ResearchRequest
from finahinking.research.drivers import DriverResult
from finahinking.research.workflow import AnalystSpec


def make_request(roles: tuple[str, ...] = ("fundamentals", "technical", "sentiment", "news", "learning")) -> ResearchRequest:
    return ResearchRequest(
        run_id="run-1",
        instrument="AAPL",
        as_of=date(2026, 1, 2),
        research_plan=ResearchPlan(required_datasets=("fixture",)),
        analyst_roles=roles,
        asset_class="equity",
        workflow_version="research.v1",
        config_digest="config-digest",
    )


class DelayedDriver:
    def __init__(self, delays: dict[str, float] | None = None, *, missing: set[str] | None = None) -> None:
        self.delays = delays or {}
        self.missing = missing or set()
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.lock = threading.Lock()

    def propose(self, request: ResearchRequest, context: dict[str, object]) -> DriverResult:
        role = str(context["analyst_role"])
        with self.lock:
            self.calls.append((role, context))
        time.sleep(self.delays.get(role, 0))
        if role in self.missing:
            return DriverResult()
        return DriverResult(
            reports=(
                AgentReport(
                    role=role,
                    status="READY",
                    claims=(f"observation for {role}",),
                    evidence_refs=(f"artifact:{role}",),
                ),
            ),
        )


def specs() -> tuple[AnalystSpec, ...]:
    return tuple(AnalystSpec(role=role, required=role != "learning", timeout_seconds=0.2) for role in make_request().analyst_roles)


def test_pool_runs_default_roles_in_parallel_and_sorts_by_role() -> None:
    driver = DelayedDriver({"fundamentals": 0.05, "technical": 0.01, "sentiment": 0.04, "news": 0.02, "learning": 0.0})

    outcomes = AnalystPool().run(specs(), make_request(), driver, {"dataset": "fixture"}, max_workers=5)

    assert [outcome.role for outcome in outcomes] == ["fundamentals", "technical", "sentiment", "news", "learning"]
    assert all(outcome.status == "READY" for outcome in outcomes)
    assert len(driver.calls) == 5
    assert all(context["paper_only"] is True and context["allowed_tools"] == () for _, context in driver.calls)


def test_pool_normalizes_missing_optional_and_required_roles() -> None:
    driver = DelayedDriver(missing={"fundamentals", "learning"})

    outcomes = AnalystPool().run(specs(), make_request(), driver, {}, max_workers=5)
    by_role = {outcome.role: outcome for outcome in outcomes}

    assert by_role["fundamentals"].status == "MISSING_REQUIRED"
    assert by_role["fundamentals"].failure_kind is AnalystFailureKind.MISSING_REQUIRED
    assert by_role["learning"].status == "OPTIONAL_FAILED"
    assert by_role["learning"].failure_kind is AnalystFailureKind.OPTIONAL_FAILURE


def test_pool_marks_duplicate_roles_without_proposing_twice() -> None:
    duplicate_specs = (AnalystSpec("news"), AnalystSpec("news"))
    driver = DelayedDriver()

    outcomes = AnalystPool().run(duplicate_specs, make_request(("news",)), driver, {}, max_workers=2)

    assert len(outcomes) == 2
    assert all(outcome.status == "DUPLICATE_ROLE" for outcome in outcomes)
    assert all(outcome.failure_kind is AnalystFailureKind.DUPLICATE_ROLE for outcome in outcomes)
    assert len(driver.calls) == 0


def test_pool_normalizes_roles_before_duplicate_detection() -> None:
    duplicate_specs = (AnalystSpec("News"), AnalystSpec(" news "))
    driver = DelayedDriver()

    outcomes = AnalystPool().run(duplicate_specs, make_request(("news",)), driver, {}, max_workers=2)

    assert [outcome.role for outcome in outcomes] == ["news", "news"]
    assert all(outcome.status == "DUPLICATE_ROLE" for outcome in outcomes)
    assert not driver.calls


def test_pool_recursively_removes_nested_tool_values_and_callables() -> None:
    driver = DelayedDriver()
    nested = {
        "safe": {"label": "fixture", "tool_gateway": object(), "deep": {"executor": object(), "keep": 1}},
        "callable": lambda: None,
        "items": [{"tool": object(), "keep": "ok"}],
    }

    AnalystPool().run((AnalystSpec("news"),), make_request(("news",)), driver, nested, max_workers=1)

    passed = driver.calls[0][1]
    assert passed["safe"] == {"label": "fixture", "deep": {"keep": 1}}
    assert passed["items"] == [{"keep": "ok"}]
    assert "callable" not in passed


def test_pool_marks_timeouts_and_driver_exceptions_as_typed_failures() -> None:
    timeout_spec = AnalystSpec("news", timeout_seconds=0.01)

    outcomes = AnalystPool().run((timeout_spec,), make_request(("news",)), DelayedDriver({"news": 0.1}), {}, max_workers=1)
    assert outcomes[0].status == "TIMEOUT"
    assert outcomes[0].failure_kind is AnalystFailureKind.TIMEOUT

    class ExplodingDriver(DelayedDriver):
        def propose(self, request: ResearchRequest, context: dict[str, object]) -> DriverResult:
            raise RuntimeError("boom")

    outcomes = AnalystPool().run((AnalystSpec("news"),), make_request(("news",)), ExplodingDriver(), {}, max_workers=1)
    assert outcomes[0].status == "FAILED"
    assert outcomes[0].failure_kind is FailureKind.INTERNAL_ERROR


def test_pool_message_digest_is_stable_for_same_input() -> None:
    first = AnalystPool().run((AnalystSpec("news"),), make_request(("news",)), DelayedDriver(), {"dataset": "fixture"})
    second = AnalystPool().run((AnalystSpec("news"),), make_request(("news",)), DelayedDriver(), {"dataset": "fixture"})

    assert first[0].message_digest == second[0].message_digest


def test_pool_does_not_retain_driver_exception_or_failure_message() -> None:
    class ExplodingDriver(DelayedDriver):
        def propose(self, request, context):
            raise RuntimeError("api_key=super-secret https://evil.test /Users/private prompt=hidden")

    class FailedDriver(DelayedDriver):
        def propose(self, request, context):
            return DriverResult(
                failure_kind=FailureKind.INTERNAL_ERROR,
                failure_message="raw provider response token=super-secret",
            )

    exploded = AnalystPool().run((AnalystSpec("news"),), make_request(("news",)), ExplodingDriver(), {})[0]
    failed = AnalystPool().run((AnalystSpec("news"),), make_request(("news",)), FailedDriver(), {})[0]
    for outcome in (exploded, failed):
        assert outcome.failure_kind is FailureKind.INTERNAL_ERROR
        assert all(value not in repr(outcome) for value in ("super-secret", "evil.test", "/Users/private", "prompt=hidden", "raw provider response"))


def test_manager_synthesizes_evidence_refs_without_copying_claims() -> None:
    reports = (
        AgentReport(role="news", status="READY", claims=("unsupported fact",), evidence_refs=("artifact:news",)),
        AgentReport(role="fundamentals", status="READY", claims=("another fact",), evidence_refs=("artifact:fundamentals",)),
    )

    plan = ResearchManager().synthesize(reports, make_request(("fundamentals", "news")))

    assert plan.hypotheses == ()
    assert plan.validation_spec["evidence_refs"] == ("artifact:fundamentals", "artifact:news")
    assert "unsupported fact" not in repr(plan)


def test_manager_requires_evidence_refs() -> None:
    with pytest.raises(ValueError, match="evidence"):
        ResearchManager().synthesize((AgentReport(role="news", status="READY"),), make_request(("news",)))


def test_manager_blocks_when_any_usable_report_lacks_evidence_refs() -> None:
    reports = (
        AgentReport(role="news", status="READY", claims=("fact",), evidence_refs=("artifact:news",)),
        AgentReport(role="fundamentals", status="READY", claims=("fact without evidence",)),
    )

    with pytest.raises(ValueError, match="evidence.*fundamentals"):
        ResearchManager().synthesize(reports, make_request(("fundamentals", "news")))
