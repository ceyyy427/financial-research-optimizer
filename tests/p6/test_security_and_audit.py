import pytest

from finahinking.p6.audit import GuidedSessionAudit
from finahinking.p6.security import validate_agent_text


def test_untrusted_prompt_cannot_request_code_shell_install_or_mutation() -> None:
    for text in (
        "run eval('1+1')",
        "execute a shell command",
        "pip install a package",
        "rewrite provenance and delete the artifact",
    ):
        with pytest.raises(ValueError):
            validate_agent_text(text)


def test_audit_record_contains_decision_and_evidence_trail() -> None:
    audit = GuidedSessionAudit.start("Does momentum work?", user_id="u1")
    audit = audit.record_classification("QUANT").record_hypothesis("h-1").record_tool_call("quant.inspect_run")
    audit = audit.record_evidence("quant-1", warnings=("LIQUIDITY_NOT_MODELED",))
    payload = audit.to_dict()
    assert payload["user_question"] == "Does momentum work?"
    assert payload["tool_calls"] == ["quant.inspect_run"]
    assert payload["quant_run_ids"] == ["quant-1"]
    assert payload["warnings"] == ["LIQUIDITY_NOT_MODELED"]
