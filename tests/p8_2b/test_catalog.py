from __future__ import annotations

import pytest

from finahinking.p8_2b.catalog import DEFAULT_KNOWLEDGE_CATALOG, get_knowledge_unit, search_catalog
from finahinking.p8_2b.validation import validate_catalog


def test_flagship_catalog_contains_four_complete_lessons_and_valid_prerequisite_dag() -> None:
    validate_catalog(DEFAULT_KNOWLEDGE_CATALOG)
    ids = {unit.unit_id for unit in DEFAULT_KNOWLEDGE_CATALOG.units}
    assert {"ols", "sharpe", "momentum", "oos-overfitting"} <= ids
    assert all(unit.why_now and unit.assumptions and unit.limitations for unit in DEFAULT_KNOWLEDGE_CATALOG.units)
    assert get_knowledge_unit("ols").proofs[0].status == "REFERENCE_DERIVED"


def test_catalog_search_matches_equations_symbols_and_code() -> None:
    assert {unit.unit_id for unit in search_catalog("beta")} >= {"ols"}
    assert {unit.unit_id for unit in search_catalog("rolling")} >= {"volatility", "momentum"}
    assert search_catalog("not a concept") == ()


def test_validator_rejects_prerequisite_cycle() -> None:
    from dataclasses import replace

    cycle = replace(DEFAULT_KNOWLEDGE_CATALOG.units[0], prerequisites=(DEFAULT_KNOWLEDGE_CATALOG.units[0].unit_id,))
    broken = replace(DEFAULT_KNOWLEDGE_CATALOG, units=(cycle, *DEFAULT_KNOWLEDGE_CATALOG.units[1:]))
    with pytest.raises(ValueError, match="cycle"):
        validate_catalog(broken)
