from __future__ import annotations

import pytest

from finahinking.p8_2b.catalog import DEFAULT_KNOWLEDGE_CATALOG
from finahinking.p8_2b.validation import validate_catalog, validate_code


def test_code_validator_rejects_imports_and_dynamic_execution() -> None:
    with pytest.raises(ValueError, match="unsafe"):
        validate_code("import os\nopen('secret.txt').read()")
    with pytest.raises(ValueError, match="unsafe"):
        validate_code("eval('1 + 1')")


def test_catalog_validation_returns_stable_unit_ids() -> None:
    assert validate_catalog(DEFAULT_KNOWLEDGE_CATALOG) == tuple(sorted(unit.unit_id for unit in DEFAULT_KNOWLEDGE_CATALOG.units))
