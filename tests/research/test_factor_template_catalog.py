from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from finahinking.research.factor_pipeline import FactorResearchPipeline
from finahinking.research.factor_proposals import (
    FactorProposalCatalog,
    FactorTemplate,
    FactorTemplateRegistry,
)


def test_template_versions_cannot_be_forged() -> None:
    registry = FactorTemplateRegistry()
    hypothesis = registry.resolve("momentum", {})
    with pytest.raises(ValueError, match="version"):
        FactorProposalCatalog(registry).propose(replace(hypothesis, template_version="99.0.0"))
    with pytest.raises(ValueError, match="version"):
        registry.resolve("momentum", {"template_version": "99.0.0"})


def test_custom_registry_reaches_catalog_and_pipeline() -> None:
    registry = FactorTemplateRegistry()
    registry.register("custom", "momentum", "rank(rolling_mean(close,{window}))", ("close",), "2.0.0")
    hypothesis = registry.resolve("custom", {"horizon": 2})
    assert FactorProposalCatalog(registry).propose(hypothesis)
    close = pd.Series([100 + i + i % 3 for i in range(60)], index=pd.date_range("2024-01-01", periods=60), dtype=float)
    dataset = {"frame": pd.DataFrame({"close": close}), "forward_return": close.pct_change().shift(-1)}
    config = {"horizon": 2, "source_ids": ("fixture",), "license_status": "VERIFIED", "pit_semantics": "T+1 point-in-time"}
    result = FactorResearchPipeline(registry).run("custom", dataset, config)
    assert result.hypothesis.template_name == "custom"
    assert result.hypothesis.template_version == "2.0.0"
    with pytest.raises(ValueError, match="version"):
        FactorResearchPipeline(registry).run(replace(hypothesis, template_version="99.0.0"), dataset, config)
    with pytest.raises(ValueError, match="version"):
        FactorResearchPipeline(registry).run({"text": "custom", "family": "momentum", "inputs": ("close",), "template_name": "custom", "template_version": "99.0.0"}, dataset, config)


def test_canonical_names_and_unknown_language() -> None:
    registry = FactorTemplateRegistry()
    for name in ("short_term_reversal", "short term reversal", "short-term-reversal"):
        hypothesis = registry.resolve(name, {})
        assert hypothesis.template_name == "short_term_reversal"
        assert FactorProposalCatalog(registry).propose(hypothesis)[0].required_fields == ("return_1d",)
    for text in ("evolution", "momentum volatility", "unknown momentum words"):
        with pytest.raises(ValueError):
            registry.resolve(text, {})


@pytest.mark.parametrize("expression", ["open(close)", "rank(tomorrow)", "rank({bad})", "rank({field!r})", "rank({field", "rank(rolling_mean(close,0))", "rank(close,close)"])
def test_registration_validates_dsl_immediately(expression: str) -> None:
    with pytest.raises(ValueError):
        FactorTemplateRegistry().register("bad", "momentum", expression, ("close",), "1.0.0")


def test_mapping_constructor() -> None:
    template = FactorTemplate("custom", "momentum", "rank(close)", ("close",), "2.0.0")
    assert FactorTemplateRegistry({"custom": template}).get("custom") == template


def test_legacy_hypotheses_keep_close_and_return_defaults() -> None:
    from finahinking.research.factor_proposals import FactorHypothesis

    registry = FactorTemplateRegistry()
    for family in ("momentum", "mean_reversion", "volatility"):
        for field in ("close", "return_1d"):
            hypothesis = FactorHypothesis("legacy", "legacy hypothesis", family, (field,), 5, "positive")
            bound = registry.bind(hypothesis)
            assert bound.template_version == "1.0.0"
            assert all(item.required_fields == (field,) for item in FactorProposalCatalog(registry).propose(bound))


def test_template_definition_changes_bind_config_and_lineage() -> None:
    close = pd.Series([100 + i + i % 3 for i in range(60)], index=pd.date_range("2024-01-01", periods=60), dtype=float)
    dataset = {"frame": pd.DataFrame({"close": close}), "forward_return": close.pct_change().shift(-1)}
    config = {"horizon": 2, "source_ids": ("fixture",), "license_status": "VERIFIED", "pit_semantics": "T+1 point-in-time"}
    results = []
    for expression in ("rank(close)", "negate(rank(close))"):
        registry = FactorTemplateRegistry({})
        registry.register("custom", "momentum", expression, ("close",), "2.0.0")
        results.append(FactorResearchPipeline(registry).run("custom", dataset, config))
    assert results[0].config_digest != results[1].config_digest
    assert results[0].catalog_entries[0].research_fingerprint != results[1].catalog_entries[0].research_fingerprint


@pytest.mark.parametrize("text,fields", [("mean reversion", ("close",)), ("momentum", ("return_1d",)), ("volatility", ("return_1d",)), ("liquidity", ("volume",)), ("short term reversal", ("return_1d",)), ("volume trend", ("volume",))])
def test_default_templates_resolve_to_versioned_hypotheses(text: str, fields: tuple[str, ...]) -> None:
    hypothesis = FactorTemplateRegistry().resolve(text, {"inputs": fields, "horizon": 20})
    assert hypothesis.template_name
    assert hypothesis.template_version == "1.0.0"
    assert hypothesis.inputs == fields


@pytest.mark.parametrize("text,config", [("unknown language", {}), ("future return", {}), ("momentum", {"horizon": 0}), ("momentum", {"horizon": 253}), ("momentum", {"inputs": ("future_return",)})])
def test_resolution_rejects_unknown_future_and_unbounded_requests(text: str, config: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        FactorTemplateRegistry().resolve(text, config)


def test_registration_is_allow_list_only() -> None:
    registry = FactorTemplateRegistry()
    with pytest.raises(ValueError):
        registry.register("unsafe", "momentum", "__import__('os')", ("close",), "1.0.0")
    template = registry.register("custom", "momentum", "rank(rolling_mean({field},{window}))", ("close",), "2.0.0")
    assert template.version == "2.0.0"
    with pytest.raises(ValueError):
        registry.register("custom", "momentum", "rank(close)", ("close",), "2.0.0")
