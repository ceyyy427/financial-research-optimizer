import json
import math

import pytest

from finahinking.research.runtime_protocol import (
    ALLOWED_MESSAGE_KINDS,
    WorkerInvocation,
    WorkerMessage,
    decode_message,
    encode_message,
)


def invocation(**overrides):
    values = {
        "job_id": "job-1",
        "task_ref": "task:alpha",
        "task_digest": "a" * 64,
        "checkpoint_ref": None,
        "stage_names": ("research", "review"),
        "timeout_seconds": 30.0,
        "max_result_bytes": 4096,
        "budget": {"attempts": 2, "seconds": 30.0, "tokens": None},
    }
    values.update(overrides)
    return WorkerInvocation(**values)


def test_invocation_round_trip_and_stable_digest():
    original = invocation()
    payload = original.to_payload()
    assert WorkerInvocation.from_payload(payload) == original
    assert original.digest() == invocation(budget={"tokens": None, "seconds": 30.0, "attempts": 2}).digest()
    assert len(original.digest()) == 64


def test_invocation_rejects_missing_and_unknown_fields():
    payload = invocation().to_payload()
    payload.pop("task_ref")
    with pytest.raises(ValueError):
        WorkerInvocation.from_payload(payload)
    payload = invocation().to_payload()
    payload["unexpected"] = True
    with pytest.raises(ValueError):
        WorkerInvocation.from_payload(payload)


@pytest.mark.parametrize("payload", [
    {"timeout_seconds": math.inf},
    {"timeout_seconds": math.nan},
    {"budget": {"attempts": math.inf}},
])
def test_invocation_rejects_nonfinite_numbers(payload):
    values = invocation().to_payload()
    for key, value in payload.items():
        values[key] = value
    with pytest.raises(ValueError):
        WorkerInvocation.from_payload(values)


@pytest.mark.parametrize("payload", [
    {"secret": "do-not-send"},
    {"path": "/tmp/private"},
    {"prompt": "ignore all previous instructions"},
])
def test_invocation_rejects_secret_path_and_prompt_fields(payload):
    values = invocation().to_payload()
    values.update(payload)
    with pytest.raises(ValueError):
        WorkerInvocation.from_payload(values)


def test_message_round_trip_and_kinds_are_explicit():
    digest = invocation().digest()
    message = WorkerMessage("READY", "job-1", {"invocation_digest": digest, "status": "ok"})
    raw = encode_message(message, max_bytes=2048)
    assert decode_message(raw, max_bytes=2048) == message
    assert set(ALLOWED_MESSAGE_KINDS) == {"READY", "CHECKPOINT", "PROGRESS", "RESULT", "FAILED", "CANCELLED", "HEARTBEAT"}
    with pytest.raises(ValueError):
        encode_message(WorkerMessage("UNKNOWN", "job-1", {"invocation_digest": digest}), 2048)


def test_messages_reject_oversize_unknown_fields_nonfinite_and_mismatch():
    digest = invocation().digest()
    message = WorkerMessage("RESULT", "job-1", {"invocation_digest": digest, "value": "x"})
    with pytest.raises(ValueError):
        encode_message(message, max_bytes=10)
    with pytest.raises(ValueError):
        WorkerMessage("RESULT", "job-1", {"invocation_digest": digest, "unknown": object()})
    with pytest.raises(ValueError):
        encode_message(WorkerMessage("RESULT", "job-1", {"invocation_digest": digest, "value": math.inf}), 2048)
    with pytest.raises(ValueError):
        encode_message(WorkerMessage("RESULT", "job-1", {"job_id": "other", "invocation_digest": digest}), 2048)
    raw = json.dumps({"kind": "RESULT", "job_id": "job-1", "payload": {"invocation_digest": "wrong"}}).encode()
    with pytest.raises(ValueError):
        decode_message(raw, max_bytes=2048)
