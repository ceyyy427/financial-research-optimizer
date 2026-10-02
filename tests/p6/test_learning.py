from finahinking.p6.learning import (
    LearningStore,
    generate_quiz,
    make_learning_card,
    record_misconception,
)


def test_learning_card_quiz_and_auditable_progress_are_grounded() -> None:
    card = make_learning_card(
        concept="Momentum",
        definition="A ranking of trailing returns measured before execution.",
        formula="r_t / r_{t-k} - 1",
        result_context={"metric": "excess_return", "value": 0.02, "evidence_reference": "quant-1"},
        limitation="Historical evidence is not a forecast.",
    )
    assert card.evidence_reference == "quant-1"
    quiz = generate_quiz(card)
    assert quiz.correct_answer in quiz.options
    store = LearningStore()
    progress = store.record_answer("u1", card, correct=False, confidence=0.2)
    assert progress.incorrect_responses == 1
    misconception = record_misconception(
        "u1", card, observed_statement="A profitable backtest guarantees future performance."
    )
    assert misconception.evidence_reference == "quant-1"
    assert "psychological" not in misconception.to_dict()
