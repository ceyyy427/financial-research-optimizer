from __future__ import annotations

import pandas as pd
import pytest

from finahinking.research.factor_pipeline import (
    FactorResearchPipeline,
    HumanAdmissionRecord,
    rank_factor_proposals,
)
from finahinking.research.factor_proposals import FactorHypothesis


def _hypothesis() -> FactorHypothesis:
    return FactorHypothesis(
        "momentum-runtime",
        "price momentum should persist",
        "momentum",
        ("close",),
        1,
        "positive",
    )


def _dataset() -> dict[str, object]:
    index = pd.date_range("2024-01-01", periods=48, freq="D", tz="UTC")
    close = pd.Series([100 + i + (i % 3) for i in range(len(index))], index=index, dtype=float)
    return {"frame": pd.DataFrame({"close": close}, index=index), "forward_return": close.pct_change().shift(-1)}


def _config(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "source_ids": ("fixture-source",),
        "license_status": "VERIFIED",
        "pit_semantics": "T+1 point-in-time",
        "version": "1.0.0",
        "max_proposals": 2,
        "max_rounds": 2,
        "min_samples": 8,
        "shift_periods": 1,
        "min_abs_ic": 0.0,
        "min_icir": -1_000_000.0,
        "max_turnover": 10.0,
    }
    values.update(overrides)
    return values


def test_pipeline_turns_natural_language_into_hidden_oos_rank_and_human_proposals() -> None:
    result = FactorResearchPipeline().run(_hypothesis(), _dataset(), _config())

    assert result.proposals
    assert result.research_run.test_evaluation is None
    assert all(item.evaluation.oos_status == "HIDDEN" for item in result.research_run.rounds)
    assert result.ranks == rank_factor_proposals(result)
    assert result.admission_proposals
    assert all(item.requires_human_admission for item in result.admission_proposals)
    assert all(item.status == "PENDING_HUMAN_ADMISSION" for item in result.admission_proposals)
    assert result.catalog_entries[0].status == "PROPOSED"


def test_pipeline_freeze_then_evaluates_test_once() -> None:
    pipeline = FactorResearchPipeline()
    result = pipeline.run(_hypothesis(), _dataset(), _config(max_proposals=2, max_rounds=2))
    candidate_id = next(item.candidate.candidate_id for item in result.research_run.rounds if item.admission.status == "ADMITTED")

    with pytest.raises(ValueError, match="frozen"):
        result.evaluate_test(_dataset())
    frozen = result.freeze(candidate_id)
    tested = frozen.evaluate_test(_dataset())

    assert tested.research_run.test_evaluation is not None
    with pytest.raises(ValueError, match="once-only"):
        tested.evaluate_test(_dataset())


def test_pipeline_repeated_run_and_rank_are_deterministic() -> None:
    pipeline = FactorResearchPipeline()
    first = pipeline.run(_hypothesis(), _dataset(), _config())
    second = pipeline.run(_hypothesis(), _dataset(), _config())

    assert first.fingerprint == second.fingerprint
    assert [item.proposal_id for item in first.ranks] == [item.proposal_id for item in second.ranks]


def test_pipeline_blocks_missing_license_and_future_or_lookahead_inputs() -> None:
    with pytest.raises(ValueError, match="license"):
        FactorResearchPipeline().run(_hypothesis(), _dataset(), _config(license_status="UNKNOWN"))

    for alias in ("future_return", "forward_return_5d", "forward", "next_return", "tomorrow_return", "target", "label"):
        future = _dataset()
        frame = future["frame"]
        assert isinstance(frame, pd.DataFrame)
        future["frame"] = frame.assign(**{alias: frame["close"].pct_change().shift(-1)})
        with pytest.raises(ValueError, match="future"):
            FactorResearchPipeline().run(_hypothesis(), future, _config())

    with pytest.raises(ValueError, match="version"):
        FactorResearchPipeline().run(_hypothesis(), _dataset(), _config(version=""))

    with pytest.raises(ValueError, match="license"):
        FactorResearchPipeline().run(_hypothesis(), _dataset(), {"source_ids": ("fixture-source",), "pit_semantics": "T+1 point-in-time"})

    with pytest.raises(ValueError, match="license"):
        FactorResearchPipeline().run(_hypothesis(), _dataset(), _config(license_status="PROPRIETARY_UNREVIEWED"))

    with pytest.raises(ValueError, match="PIT"):
        FactorResearchPipeline().run(_hypothesis(), _dataset(), _config(pit_semantics="available_at <= as_of"))


def test_pipeline_does_not_mutate_registry_or_accept_unreviewed_admission() -> None:
    result = FactorResearchPipeline().run(_hypothesis(), _dataset(), _config(max_proposals=1, max_rounds=1))
    proposal = result.admission_proposals[0]

    assert proposal.production_write is False
    with pytest.raises(TypeError, match="HumanAdmissionRecord"):
        result.admit(proposal.proposal_id, {"approved": True})


def test_catalog_lineage_fingerprint_binds_dataset_config_run_and_admission() -> None:
    pipeline = FactorResearchPipeline()
    result = pipeline.run(_hypothesis(), _dataset(), _config(max_proposals=1, max_rounds=1))
    entry = result.catalog_entries[0]
    evaluation = result.research_run.rounds[0].evaluation
    admission = result.admission_proposals[0]
    assert entry.research_fingerprint != evaluation.fingerprint
    changed = pipeline.run(_hypothesis(), _dataset(), _config(max_proposals=1, max_rounds=1, cost_per_turnover=0.01))
    assert changed.catalog_entries[0].research_fingerprint != entry.research_fingerprint

    with pytest.raises(ValueError, match="bind"):
        result.admit(admission.proposal_id, HumanAdmissionRecord(admission.proposal_id, evaluation.fingerprint, "0" * 64, "reviewer-1"))
    approved = result.admit(
        admission.proposal_id,
        HumanAdmissionRecord(admission.proposal_id, evaluation.fingerprint, entry.research_fingerprint, "reviewer-1"),
    )
    assert approved.status == "HUMAN_ADMITTED"
    assert approved.production_write is False
