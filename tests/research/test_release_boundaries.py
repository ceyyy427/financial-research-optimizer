"""Regression gates from the independent spawn runtime release review."""
import time
from dataclasses import replace

import pytest

from finahinking.research.contracts import AgentTask, stable_digest
from finahinking.research.job_queue import JobQueue, JobStatus
from finahinking.research.runtime_protocol import ProtocolError
from finahinking.research.runtime_service import ResearchRuntimeService, RuntimeLimits
from finahinking.research.stage_registry import StageRegistryError
from finahinking.research.supervisor import (
    ResearchSupervisor,
    _control_receive,
    _message_from_payload,
)
from finahinking.research.worker import WorkerStatus

from .test_runtime_service import request
from .test_supervisor import _registry, stage_checkpoint_then_wait, stage_measured, stage_ok


def test_missing_persisted_stage_never_falls_back(tmp_path):
    queue = JobQueue(tmp_path / 'jobs.sqlite')
    job = queue.enqueue(AgentTask(role='technical', task_id='missing', input_digest='input', capabilities=('missing',)), 'missing')
    supervisor = ResearchSupervisor(queue, registry=_registry('workflow', stage_ok), worker_id='owner', max_concurrency=1, _embedded=True)
    with pytest.raises(StageRegistryError):
        supervisor._make_handle(job)


def test_snapshot_identity_and_atomic_rollback(tmp_path):
    queue = JobQueue(tmp_path / 'jobs.sqlite')
    original = request()
    task = AgentTask(role='technical', task_id='bound', input_digest=stable_digest(original))
    queue.enqueue(task, 'bound', request_snapshot=original)
    with pytest.raises(ValueError):
        queue.save_request_snapshot('bound', request('different'))
    assert queue.load_request_snapshot('bound') == original


@pytest.mark.parametrize('value', ['api_key=SECRET', '/tmp/private', 'https://private.example', 'prompt=hidden'])
def test_unsafe_snapshot_rejected_before_queue_visibility(tmp_path, value):
    queue = JobQueue(tmp_path / 'jobs.sqlite')
    original = replace(request(), instrument=value)
    task = AgentTask(role='technical', task_id='unsafe', input_digest=stable_digest(original))
    with pytest.raises(ValueError):
        queue.enqueue(task, 'unsafe', request_snapshot=original)
    assert queue.claim('observer') is None


def test_control_receive_requests_allocation_bound():
    class Connection:
        def recv_bytes(self, maxlength):
            assert maxlength == 65536
            return b'[]'
    with pytest.raises(ProtocolError):
        _control_receive(Connection())
    with pytest.raises(ProtocolError):
        _message_from_payload({'kind': 'RESULT', 'job_id': 'job', 'payload': {}, 'extra': 1})


def test_submit_limits_reach_worker_before_claim(tmp_path):
    service = ResearchRuntimeService(tmp_path / 'jobs.sqlite', stage_runners={'workflow': stage_measured})
    limits = RuntimeLimits(max_experiments=1, max_attempts=1)
    try:
        job = service.submit(request('budgeted'), limits=limits)
        service.run_until_terminal(job.job_id, limits)
        assert service.queue.get(job.job_id).status is JobStatus.FAILED
        metrics = service._supervisor.metrics_for(job.job_id)
        assert metrics is not None and metrics.resource_failures >= 1
    finally:
        service.stop_supervisor()


def test_stop_releases_active_lease(tmp_path):
    queue = JobQueue(tmp_path / 'jobs.sqlite', backoff_base_seconds=0)
    job = queue.enqueue(AgentTask(role='technical', task_id='stop-job', input_digest='input'), 'stop')
    supervisor = ResearchSupervisor(queue, registry=_registry('workflow', stage_checkpoint_then_wait), worker_id='owner', max_concurrency=1)
    supervisor.start()
    try:
        deadline = time.monotonic() + 5
        while queue.get(job.job_id).checkpoint_ref is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert queue.get(job.job_id).checkpoint_ref is not None
    finally:
        supervisor.stop()
    assert queue.get(job.job_id).status is not JobStatus.RUNNING
    assert queue.get(job.job_id).lease_token is None


def test_observer_wall_deadline_persists_cancellation(tmp_path):
    service = ResearchRuntimeService(tmp_path / 'jobs.sqlite', stage_runners={'workflow': stage_checkpoint_then_wait})
    try:
        job = service.submit(request('wall-deadline'))
        result = service.run_until_terminal(job.job_id, RuntimeLimits(max_wall_seconds=0.05, max_attempts=1))
        record = service.queue.get(job.job_id)
        assert result.status is WorkerStatus.CANCELLED
        assert record.status is JobStatus.CANCELLED
        assert record.lease_token is None
    finally:
        service.stop_supervisor()
