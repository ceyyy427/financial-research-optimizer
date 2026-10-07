from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from finahinking.research.codex_bridge import CodexBridge, CodexTaskEnvelope


@dataclass(frozen=True)
class Task:
    task_id: str = "task-1"
    role: str = "technical"
    input_digest: str = "input-digest"
    context_digest: str = "context-digest"
    prompt_digest: str = "prompt-digest"
    capabilities: tuple[str, ...] = ("structured_output", "paper_only")
    workflow_version: str = "research.v1"


def test_create_handoff_contains_only_digests_capabilities_and_paper_boundary() -> None:
    bridge = CodexBridge()
    envelope = bridge.create_handoff(Task())

    assert isinstance(envelope, CodexTaskEnvelope)
    payload = envelope.to_dict()
    assert payload["task_id"] == "task-1"
    assert payload["input_digest"] == "input-digest"
    assert payload["context_digest"] == "context-digest"
    assert payload["prompt_digest"] == "prompt-digest"
    assert payload["paper_only"] is True
    assert payload["tool_names"] == []
    assert "full prompt" not in json.dumps(payload).casefold()


def test_accept_result_requires_external_handoff_when_result_is_missing() -> None:
    bridge = CodexBridge()
    envelope = bridge.create_handoff(Task())
    outcome = bridge.accept_result(envelope, None)

    assert outcome.status == "EXTERNAL_HANDOFF_REQUIRED"
    assert outcome.failure_kind == "EXTERNAL_HANDOFF_REQUIRED"
    assert outcome.input_digest == envelope.input_digest
    assert outcome.message_digest


def test_accept_result_rejects_digest_mismatch_without_echoing_values() -> None:
    bridge = CodexBridge()
    envelope = bridge.create_handoff(Task())
    outcome = bridge.accept_result(
        envelope,
        {"schema_version": envelope.schema_version, "input_digest": "wrong-digest", "status": "READY"},
    )
    assert outcome.status == "REJECTED"
    assert outcome.failure_kind == "INPUT_DIGEST_MISMATCH"
    assert "wrong-digest" not in json.dumps(outcome, default=str)


def test_accept_result_rejects_capability_overreach_and_artifact_boundary() -> None:
    bridge = CodexBridge()
    envelope = bridge.create_handoff(Task())
    outcome = bridge.accept_result(
        envelope,
        {
            "schema_version": envelope.schema_version,
            "input_digest": envelope.input_digest,
            "capabilities": ["execute_order"],
            "endpoint": "https://secret.example",
            "status": "READY",
        },
    )
    assert outcome.status == "REJECTED"
    assert outcome.failure_kind in {"CAPABILITY_DENIED", "ARTIFACT_BOUNDARY_VIOLATION"}
    assert "https://secret.example" not in json.dumps(outcome, default=str)


def test_accept_result_rejects_sensitive_text_inside_evidence_refs() -> None:
    bridge = CodexBridge()
    envelope = bridge.create_handoff(Task())
    outcome = bridge.accept_result(
        envelope,
        {
            "schema_version": envelope.schema_version,
            "input_digest": envelope.input_digest,
            "evidence_refs": ["/Users/private/report.json"],
            "status": "READY",
        },
    )
    assert outcome.failure_kind == "ARTIFACT_BOUNDARY_VIOLATION"


def test_accept_result_rejects_schema_error_and_duplicate_result() -> None:
    bridge = CodexBridge()
    envelope = bridge.create_handoff(Task())
    valid = {"schema_version": envelope.schema_version, "input_digest": envelope.input_digest, "status": "READY", "evidence_refs": ["artifact:1"]}
    first = bridge.accept_result(envelope, valid)
    second = bridge.accept_result(envelope, valid)

    assert first.status == "READY"
    assert first.failure_kind is None
    assert second.status == "REJECTED"
    assert second.failure_kind == "DUPLICATE_RESULT"

    malformed = bridge.accept_result(
        CodexBridge().create_handoff(Task(task_id="task-2")),
        {"schema_version": "wrong", "input_digest": Task().input_digest, "status": "READY"},
    )
    assert malformed.failure_kind == "SCHEMA_ERROR"


@pytest.mark.parametrize("capability", ["execute_order", "broker", "filesystem", "network", "live"])
def test_create_handoff_rejects_non_research_capabilities(capability: str) -> None:
    with pytest.raises(ValueError, match="capability"):
        CodexBridge().create_handoff(Task(capabilities=(capability,)))
