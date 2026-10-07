from __future__ import annotations

import pytest

from finahinking.research.factor_catalog import (
    FactorCatalogEntry,
    audit_factor_catalog_entry,
)


def _entry(**overrides: object) -> FactorCatalogEntry:
    values: dict[str, object] = {
        "factor_id": "momentum.v1",
        "version": "1.0.0",
        "source_ids": ("fixture-source",),
        "license_status": "MIT",
        "pit_semantics": "T+1 point-in-time",
        "required_fields": ("close",),
        "research_fingerprint": "a" * 64,
        "status": "PROPOSED",
    }
    values.update(overrides)
    return FactorCatalogEntry(**values)


def test_catalog_entry_exposes_auditable_metadata_and_stable_fingerprint() -> None:
    first = _entry()
    second = _entry()

    assert first.to_dict()["factor_id"] == "momentum.v1"
    assert first.fingerprint == second.fingerprint
    assert audit_factor_catalog_entry(first).eligible is True
    assert audit_factor_catalog_entry(first).limitations == ()


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"license_status": ""}, "license"),
        ({"license_status": "UNKNOWN"}, "license"),
        ({"source_ids": ()}, "source"),
        ({"pit_semantics": "unknown"}, "PIT"),
        ({"version": ""}, "version"),
        ({"required_fields": ("future_return",)}, "future"),
    ],
)
def test_catalog_audit_blocks_missing_license_pit_or_future_fields(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        audit_factor_catalog_entry(_entry(**overrides))


def test_catalog_entry_does_not_claim_production_admission() -> None:
    entry = _entry(status="PROPOSED")
    assert entry.status == "PROPOSED"
    assert entry.production_admitted is False
