from __future__ import annotations

import pytest

from finahinking.research.factor_proposals import FactorTemplateRegistry


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
