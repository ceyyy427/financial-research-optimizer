from __future__ import annotations

import json
from dataclasses import replace

import pytest

from finahinking.p7_5.knowledge import (
    DEFAULT_CATALOG,
    KnowledgeCatalog,
    LearningPath,
    seed_reference_curriculum,
)

CURRICULUM = (
    "return",
    "compounding",
    "variance",
    "standard-deviation",
    "volatility",
    "covariance",
    "correlation",
    "regression",
    "beta",
    "sharpe",
    "drawdown",
    "momentum",
    "backtesting",
    "oos",
    "overfitting",
)


def test_reference_catalog_is_complete_and_typed() -> None:
    catalog = seed_reference_curriculum()
    assert tuple(item.concept_id for item in catalog.concepts) == CURRICULUM
    assert catalog.version == "p7.5-reference-1"
    assert len(catalog.fingerprint) == 64
    assert catalog.validate()
    assert {item.domain_id for item in catalog.domain_coverage} >= {
        "mathematics-linear-algebra",
        "mathematics-calculus",
        "mathematics-optimization",
        "probability",
        "statistics",
        "econometrics-regression",
        "econometrics-time-series",
        "quantitative-research",
        "portfolio-theory-risk",
        "asset-pricing",
        "markets-equities",
        "markets-bonds",
        "markets-macro",
        "markets-derivatives",
        "accounting-fundamentals",
        "behavioral-science",
        "computer-science-finance",
    }
    for concept in catalog.concepts:
        assert concept.progressive_levels == (1, 2, 3, 4, 5, 6, 7, 8)
        assert concept.equations[0].expression
        assert concept.derivations[0].why_valid
        assert concept.code_examples[0].language == "Python"
        assert concept.financial_interpretations[0].application_type == "financial"
        assert concept.quant_applications[0].application_type == "quant"
        assert concept.strategy_applications[0].application_type == "strategy"
        assert concept.misconceptions[0].correction != concept.misconceptions[0].claim
        assert concept.source_references
    assert len(catalog.get("variance").derivations) >= 3
    assert len(catalog.get("regression").derivations) >= 3
    assert "PROOF" in {item.value for item in catalog.get("regression").content_types}
    assert catalog.get("return").event_links[0].target_ids == ("sample-cpi-2026-01",)


def test_prerequisite_closure_is_deterministic_and_acyclic() -> None:
    catalog = DEFAULT_CATALOG
    assert [item.concept_id for item in catalog.prerequisite_closure("beta")] == [
        "return",
        "variance",
        "covariance",
        "standard-deviation",
        "correlation",
        "regression",
        "beta",
    ]
    assert [item.concept_id for item in catalog.prerequisite_closure("overfitting")] == [
        "return",
        "compounding",
        "momentum",
        "drawdown",
        "backtesting",
        "oos",
        "overfitting",
    ]


def test_search_and_learning_paths_are_stable() -> None:
    catalog = DEFAULT_CATALOG
    assert [item.concept_id for item in catalog.search("BETA")] == ["beta"]
    assert [item.concept_id for item in catalog.search("risk", domain="portfolio-theory")] == [
        "drawdown",
        "sharpe",
    ]
    assert catalog.path("reference-curriculum").concept_ids == CURRICULUM
    assert catalog.path("quant-research-path").path_type == "QUANT_RESEARCH"
    with pytest.raises(KeyError):
        catalog.get("not-a-concept")


def test_serialization_is_json_safe_and_does_not_duplicate_personal_state() -> None:
    payload = DEFAULT_CATALOG.to_dict()
    encoded = json.dumps(payload, sort_keys=True)
    assert "mastery" not in encoded.casefold()
    assert "owner_id" not in encoded
    assert payload["learning_paths"]
    assert payload["concepts"][0]["progressive_levels"] == list(range(1, 9))


def test_catalog_rejects_broken_prerequisite_or_path_links() -> None:
    concept = DEFAULT_CATALOG.get("return")
    with pytest.raises(ValueError, match="unknown concept"):
        KnowledgeCatalog((concept,), (LearningPath("bad", "Bad", "TEST", ("unknown", "return"), "bad"),))

    cyclic_return = replace(concept, prerequisites=("beta",))
    concepts = tuple(cyclic_return if item.concept_id == "return" else item for item in DEFAULT_CATALOG.concepts)
    with pytest.raises(ValueError, match="cycle"):
        KnowledgeCatalog(concepts, ())
