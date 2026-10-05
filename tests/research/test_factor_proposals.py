from __future__ import annotations

import pytest

from finahinking.research.factor_proposals import (
    FactorHypothesis,
    FactorProposalCatalog,
    validate_factor_proposal,
)


@pytest.mark.parametrize("family", ["mean_reversion", "momentum", "volatility", "liquidity"])
def test_catalog_generates_bounded_stable_dsl_proposals(family: str) -> None:
    hypothesis = FactorHypothesis(
        hypothesis_id="h-1",
        text="  Price   signal may persist  ",
        family=family,
        inputs=("close", "volume", "return_1d"),
        horizon=20,
        direction="positive",
    )
    catalog = FactorProposalCatalog()

    first = catalog.propose(hypothesis)
    second = catalog.propose(hypothesis)

    assert 1 <= len(first) <= 5
    assert first == second
    assert [item.proposal_id for item in first] == sorted(item.proposal_id for item in first)
    assert all(item.paper_only is True for item in first)
    assert all("eval" not in item.expression for item in first)
    for proposal in first:
        validate_factor_proposal(proposal)


def test_text_whitespace_and_case_do_not_change_proposal_digest() -> None:
    catalog = FactorProposalCatalog()
    base = FactorHypothesis("h-1", "Momentum  signal", "MOMENTUM", ("return_1d",), 20, "Positive")
    variant = FactorHypothesis("h-1", " momentum signal ", "momentum", ("return_1d",), 20, "positive")
    assert catalog.propose(base) == catalog.propose(variant)


@pytest.mark.parametrize("family", ["unknown", "", "future_momentum"])
def test_unknown_family_is_rejected(family: str) -> None:
    with pytest.raises(ValueError):
        hypothesis = FactorHypothesis("h", "text", family, ("close",), 5, "positive")
        FactorProposalCatalog().propose(hypothesis)


def test_limits_and_unsafe_fields_are_rejected() -> None:
    hypothesis = FactorHypothesis("h", "text", "momentum", ("close",), 5, "positive")
    with pytest.raises(ValueError):
        FactorProposalCatalog().propose(hypothesis, limit=33)
    with pytest.raises(ValueError):
        unsafe = FactorHypothesis("h", "eval(close)", "momentum", ("close", "future_return", "path"), 5, "positive")
        FactorProposalCatalog().propose(unsafe)


@pytest.mark.parametrize("expression", ["eval(close)", "__import__('os')", "close('/tmp/a')", "rolling_mean(future_return,5)"])
def test_validate_rejects_executable_future_or_unbounded_proposal(expression: str) -> None:
    from finahinking.research.factor_proposals import FactorProposal

    proposal = FactorProposal("p", expression, "h", ("close",), {"paper_only": True})
    with pytest.raises(ValueError):
        validate_factor_proposal(proposal)
