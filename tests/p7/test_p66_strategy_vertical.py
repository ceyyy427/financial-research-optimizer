from __future__ import annotations

import sqlite3

import pandas as pd

from finahinking.data.models import Dataset, Provenance
from finahinking.p6_6 import StrategyResearchLab
from finahinking.p7 import (
    CommunityComment,
    CommunityPost,
    CommunityRoom,
    Principal,
    SQLiteP7Repository,
    StrategyJourneyInput,
    StrategyPersonalCommunityWorkflow,
    apply_p7_migration,
)


def make_repository() -> SQLiteP7Repository:
    connection = sqlite3.connect(":memory:")
    apply_p7_migration(connection)
    repository = SQLiteP7Repository(connection)
    repository.create_principal(Principal("alice", "Alice"))
    repository.create_principal(Principal("bob", "Bob"))
    repository.create_session("alice-session", "alice")
    repository.create_session("bob-session", "bob")
    return repository


def strategy_dataset() -> Dataset:
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    return Dataset(
        pd.DataFrame({"close": range(100, 140)}, index=dates),
        Provenance("p7-p66-fixture", "internal://p7-p66-fixture"),
    )


def test_real_p66_lab_run_flows_through_private_learning_projection_and_question() -> None:
    repository = make_repository()
    repository.create_room("alice-session", CommunityRoom("research-room", "Research", "Evidence-linked"))
    repository.join_room("bob-session", "research-room")

    lab = StrategyResearchLab()
    review = lab.interpreter.accept(lab.review("moving average trend"))
    lab_run = lab.run(review, strategy_dataset(), paper=True, run_id="p66-vertical")
    journey = StrategyJourneyInput.from_lab_run(
        "alice-session",
        lab_run,
        concept_ids=("oos-validation",),
        create_missing_concepts=True,
        occurred_at="2024-02-09T00:00:00Z",
        oos_fingerprint="b" * 64,
        misconception_id="mis-oos-vertical",
        misconception_observed="A successful backtest guarantees future performance.",
        misconception_correction="Untouched out-of-sample evidence is still required.",
        misconception_evidence_reference="p66-oos-review",
        detected_at="2024-02-09T00:00:00Z",
        projection_id="projection-p66-vertical",
        projection_visibility="SHARED_ROOM",
        projection_fields=("summary", "limitations", "provenance"),
        room_id="research-room",
        publish=True,
        consent=True,
        post=CommunityPost(
            "post-p66-vertical",
            "research-room",
            "alice",
            "QUANT_FINDING",
            "Moving average replay",
            "This is historical evidence, not a forecast.",
        ),
    )
    result = StrategyPersonalCommunityWorkflow(repository).run(journey)

    assert result.strategy_node.payload["strategy_fingerprint"] == lab_run.spec.fingerprint
    assert result.projection is not None
    assert result.projection.payload["summary"] == "Historical P6.6 strategy evidence; not a forecast."
    assert result.projection.payload["limitations"]
    assert result.guidance.evidence_ids == ("p66-oos-review",)
    assert result.guidance.truth_preserved is True
    assert result.misconception is not None and result.misconception.status == "OPEN"
    assert result.learning_thread_id == "thread-" + lab_run.spec.strategy_id
    history = repository.list_strategy_versions("alice-session", strategy_id=lab_run.spec.strategy_id)
    assert len(history) == 1
    assert history[0]["strategy_fingerprint"] == lab_run.spec.fingerprint
    assert history[0]["feature_fingerprint"] == lab_run.ir.feature_graph_fingerprint
    assert history[0]["backtest_fingerprint"] == lab_run.historical["backtest"].fingerprint
    assert history[0]["oos_fingerprint"] == "b" * 64
    assert history[0]["paper_fingerprint"] == lab_run.paper.fingerprint
    assert history[0]["code_commit"] == lab_run.historical["quant_run"].parameters["code_commit"]

    repository.add_comment(
        "bob-session",
        CommunityComment("comment-p66-counter", result.post_id or "", "bob", "Counter-evidence should use a frozen OOS period."),
    )
    question = StrategyPersonalCommunityWorkflow(repository).save_discussion_as_question(
        "alice-session", result.post_id or "", "question-p66-counter", "Which OOS evidence would change this view?"
    )
    assert question.node_type == "question"
    assert repository.get_public_projection(result.projection.projection_id, "bob-session").payload == result.projection.payload
