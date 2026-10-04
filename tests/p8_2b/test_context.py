from __future__ import annotations

import pytest

from finahinking.p8_2b.catalog import get_knowledge_unit
from finahinking.p8_2b.context import ContextSnapshot, resolve_context


def test_context_binding_exposes_why_now_values_and_as_of_fingerprint() -> None:
    snapshot = ContextSnapshot("research_point", "rp-1", "2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", "dataset-fp", ({"name": "volatility", "value": 0.17},), ("research-1",), "realized_volatility", "research-1", "SAMPLE", ("fixture data",))
    result = resolve_context(get_knowledge_unit("volatility"), snapshot)
    assert result.status == "AVAILABLE"
    assert result.binding is not None
    assert "why" in result.binding.why_now.casefold()
    assert result.binding.current_values[0]["value"] == 0.17
    assert result.binding.dataset_fingerprint == "dataset-fp"


def test_context_rejects_future_availability_and_unknown_unit() -> None:
    with pytest.raises(ValueError, match="available_at"):
        resolve_context(get_knowledge_unit("volatility"), ContextSnapshot("research_point", "rp-1", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "fp", (), (), None, None, "SAMPLE", ()))
    with pytest.raises(KeyError):
        resolve_context(get_knowledge_unit("volatility"), ContextSnapshot("unknown", "x", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "fp", (), (), None, None, "SAMPLE", ()), unit_id="missing")
