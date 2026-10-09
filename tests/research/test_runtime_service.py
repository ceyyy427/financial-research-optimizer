from __future__ import annotations

from datetime import date

from finahinking.research.contracts import AgentTask, ResearchPlan, ResearchRequest
from finahinking.research.job_queue import JobQueue, JobStatus, StaleLeaseError
from finahinking.research.runtime_service import ResearchRuntimeService, RuntimeLimits
from finahinking.research.worker import WorkerStatus


def request(run_id: str = "runtime-test") -> ResearchRequest:
    return ResearchRequest(
        run_id=run_id,
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(required_datasets=("fixture",), factor_ids=("momentum.v1",)),
        analyst_roles=("technical",),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="config-fixture",
    )


def stage_runner(name: str):
    def run(received: ResearchRequest, previous: dict[str, str]):
        return {"status": "completed", "result_ref": f"artifact:{name}-{received.run_id}"}

    return run


def test_submit_is_idempotent_and_publishes_durable_stage_references(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    stages = {name: stage_runner(name) for name in ("workflow", "factor", "risk", "portfolio", "report")}
    service = ResearchRuntimeService(path, stage_runners=stages, max_attempts=8)

    first = service.submit(request())
    duplicate = service.submit(request())
    assert duplicate == first

    result = service.run_until_terminal(first.job_id, RuntimeLimits(max_attempts=8))
    assert result.status is WorkerStatus.COMPLETED
    loaded = service.queue.get(first.job_id)
    assert loaded.status is JobStatus.COMPLETED
    assert loaded.checkpoint_ref is not None
    assert len(service.queue.stage_checkpoints(first.job_id)) == 5
    assert {item["stage_name"] for item in service.queue.stage_checkpoints(first.job_id)} == set(stages)


def test_resume_uses_explicit_request_resolver_after_service_restart(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    stages = {name: stage_runner(name) for name in ("workflow", "factor", "risk")}
    original = request("restartable")
    first = ResearchRuntimeService(path, stage_runners=stages, max_attempts=8)
    job = first.submit(original)
    assert first.run_until_terminal(job.job_id, RuntimeLimits(max_attempts=8)).status is WorkerStatus.COMPLETED

    reopened = ResearchRuntimeService(path, stage_runners=stages, request_resolver=lambda task_ref: original, max_attempts=8)
    resumed = reopened.resume(job.job_id)
    assert resumed.status is WorkerStatus.COMPLETED
    assert reopened.queue.get(job.job_id).status is JobStatus.COMPLETED


def test_cancelled_submission_reaches_terminal_without_running_stages(tmp_path) -> None:
    calls: list[str] = []

    def runner(received: ResearchRequest, previous: dict[str, str]):
        calls.append(received.run_id)
        return {"status": "completed", "result_ref": "artifact:unexpected"}

    service = ResearchRuntimeService(tmp_path / "jobs.sqlite", stage_runners={"workflow": runner})
    job = service.submit(request("cancelled"))
    service.cancel(job.job_id)
    result = service.run_until_terminal(job.job_id, RuntimeLimits(max_attempts=2))
    assert result.status is WorkerStatus.CANCELLED
    assert calls == []


def test_required_stage_failure_is_terminal_and_has_no_decision_reference(tmp_path) -> None:
    def failed(received: ResearchRequest, previous: dict[str, str]):
        raise ValueError("stage failed")

    service = ResearchRuntimeService(tmp_path / "jobs.sqlite", stage_runners={"workflow": failed}, max_attempts=3)
    job = service.submit(request("failed"))
    result = service.run_until_terminal(job.job_id, RuntimeLimits(max_attempts=3))
    assert result.status is WorkerStatus.FAILED
    record = service.queue.get(job.job_id)
    assert record.status is JobStatus.FAILED
    assert record.result_ref is None


def test_stage_journal_survives_queue_reopen(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    service = ResearchRuntimeService(path, stage_runners={"workflow": stage_runner("workflow")})
    job = service.submit(request("journal"))
    assert service.run_until_terminal(job.job_id, RuntimeLimits(max_attempts=2)).status is WorkerStatus.COMPLETED
    reopened = JobQueue(path)
    rows = reopened.stage_checkpoints(job.job_id)
    assert rows and rows[0]["stage_ref"].startswith("stage:")


def test_stage_checkpoint_rejects_a_lost_worker_lease(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite", lease_seconds=1, backoff_base_seconds=0)
    task = AgentTask(role="research_runtime", task_id="fenced-task", input_digest="fenced-input")
    record = queue.enqueue(task, "fenced-key")
    first = queue.claim("worker-a")
    assert first is not None
    # A second claim after lease expiry owns the durable job now.
    recovered = JobQueue(queue.path, clock=lambda: float(first.lease_until) + 1, lease_seconds=1, backoff_base_seconds=0)
    second = recovered.claim("worker-b")
    assert second is not None
    import pytest

    with pytest.raises(StaleLeaseError, match="lease"):
        recovered.record_stage_checkpoint(
            record.job_id,
            "workflow",
            "stage:stale",
            result_ref="artifact:stale",
            worker_id=first.worker_id,
            attempt=first.attempts,
            lease_until=first.lease_until,
            lease_token=first.lease_token,
        )
