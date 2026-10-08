from dataclasses import dataclass

from finahinking.research.codex_bridge import CodexBridge
from finahinking.research.job_queue import JobQueue


@dataclass(frozen=True)
class Task:
    task_id: str = "dispatch-1"
    role: str = "technical"
    input_digest: str = "input-1"
    context_digest: str = "context-1"
    prompt_digest: str = "prompt-1"
    capabilities: tuple[str, ...] = ("structured_output", "paper_only")


def test_dispatch_is_digest_only_and_external_until_callback(tmp_path):
    queue = JobQueue(tmp_path / "jobs.sqlite")
    bridge = CodexBridge(queue=queue)
    envelope = bridge.create_handoff(Task())
    record = bridge.enqueue(envelope)
    assert record.status == "EXTERNAL_HANDOFF_REQUIRED"
    claimed = queue.claim("worker")
    assert claimed is not None and claimed.task_type == "external"
    assert bridge.record_external_result(envelope, None).status == "EXTERNAL_HANDOFF_REQUIRED"


def test_dispatch_rejects_input_fingerprint_and_duplicate_callback_is_idempotent():
    bridge = CodexBridge()
    envelope = bridge.create_handoff(Task())
    bridge.enqueue(envelope)
    bad = bridge.record_external_result(envelope, {"schema_version": envelope.schema_version, "input_digest": "wrong", "status": "READY"})
    assert bad.failure_kind == "INPUT_DIGEST_MISMATCH"
    valid = {"schema_version": envelope.schema_version, "input_digest": envelope.input_digest, "status": "READY", "paper_only": True}
    first = bridge.record_external_result(envelope, valid)
    second = bridge.record_external_result(envelope, valid)
    assert first.status == second.status == "READY"
    assert first == second
