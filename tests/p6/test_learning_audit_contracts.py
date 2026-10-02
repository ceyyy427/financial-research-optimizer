from finahinking.p6.audit import GuidedSessionAudit
from finahinking.p6.learning import LearningStore, LearningThread, ReviewItem, make_learning_card


def test_learning_card_contract_and_encounter_do_not_invent_wrong_answer() -> None:
    card = make_learning_card(
        concept="Beta",
        definition="A fitted sensitivity under a specified model.",
        formula="y = alpha + beta*x + error",
        result_context={"beta": 1.2, "evidence_reference": "quant-1"},
        limitation="Association is not causality.",
        interpretation="The coefficient describes this sample and specification.",
        common_misconception="Beta is total risk.",
        follow_up_question="Would the estimate be stable in a later sample?",
    )
    payload = card.to_dict()
    assert payload["interpretation"]
    assert payload["common_misconception"] == "Beta is total risk."
    assert payload["follow_up_question"]

    progress = LearningStore().record_encounter("u1", card)
    assert progress.encounters == 1
    assert progress.correct_responses == 0
    assert progress.incorrect_responses == 0


def test_audit_records_artifacts_fingerprints_and_prediction_events() -> None:
    audit = GuidedSessionAudit.start("Does momentum work?", user_id="u1", created_at="2026-01-01T00:00:00Z")
    audit = audit.record_evidence(
        "quant-1",
        research_run_id="research-1",
        quant_run_id="quant-1",
        artifact_id="artifact-1",
        result_fingerprint="result-1",
        evidence_kind="QuantRun",
    )
    audit = audit.record_prediction("positive", evidence_reference="quant-1").record_reveal(
        "result-1", evidence_reference="quant-1"
    )
    payload = audit.to_dict()
    assert payload["artifact_ids"] == ["artifact-1"]
    assert payload["result_fingerprints"] == ["result-1"]
    assert [event["phase"] for event in payload["prediction_events"]] == ["PREDICT", "REVEAL"]


def test_review_and_learning_thread_records_are_typed() -> None:
    item = ReviewItem("u1", "beta", due_at="2026-01-02", evidence_reference="quant-1")
    thread = LearningThread("u1", ("beta", "turnover"), ("quant-1",))
    assert item.to_dict()["concept_id"] == "beta"
    assert thread.to_dict()["concept_ids"] == ["beta", "turnover"]
