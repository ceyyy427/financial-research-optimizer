import pandas as pd

from finahinking.p6.explanation import predict_reveal_explain
from finahinking.p6.workflows import GuidedResearchService


def _panel() -> pd.DataFrame:
    rows = []
    for date, a, b in [("2020-01-01", 100, 100), ("2020-01-02", 110, 95), ("2020-01-03", 121, 90), ("2020-01-04", 120, 92), ("2020-01-05", 130, 88)]:
        rows += [
            {"date": date, "asset": "AAA", "close": a, "available_at": date},
            {"date": date, "asset": "BBB", "close": b, "available_at": date},
        ]
    return pd.DataFrame(rows)


def test_guided_momentum_workflow_explains_limits_and_updates_learning() -> None:
    result = GuidedResearchService().run_momentum("u1", "Does momentum work in this dataset?", _panel())
    assert result.audit.state == "LEARNING_READY"
    assert result.explanation.what_was_asked
    assert result.explanation.what_was_tested
    assert result.explanation.limitations
    assert result.learning_card.evidence_reference
    assert result.audit.quant_run_ids


def test_predict_reveal_explain_is_educational_only() -> None:
    interaction = predict_reveal_explain(
        prompt="If beta is 1.5 and the market rises 1%, what is the intuitive move?",
        prediction="about 1.5%",
        result={"beta": 1.5},
        explanation="Beta scales the market return in this simplified interpretation.",
        evidence_reference="quant-1",
    )
    assert interaction.phase == "EXPLAIN"
    assert interaction.result["beta"] == 1.5
