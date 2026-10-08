from __future__ import annotations

import json

import pytest

from finahinking.factors.registry import FactorRegistry
from finahinking.research.factor_catalog import FactorCatalogEntry, HumanAdmissionRecord
from finahinking.research.factor_catalog_loader import (
    BUILTIN_AUDITED_CATALOG,
    CatalogAdmissionProposal,
    admit_catalog_entry,
    load_audited_catalog,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "factor_id": "momentum_20d",
        "version": "1.0.0",
        "source_ids": ["fixture-source"],
        "license_status": "MIT",
        "pit_semantics": "T+1 point-in-time",
        "required_fields": ["close"],
        "research_fingerprint": "a" * 64,
        "evaluation_fingerprint": "b" * 64,
        "status": "PROPOSED",
    }
    row.update(overrides)
    return row


def test_loader_validates_fingerprint_and_builds_immutable_catalog(tmp_path) -> None:
    entry = FactorCatalogEntry(**_row())
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"entries": [{**_row(), "fingerprint": entry.fingerprint}]}), encoding="utf-8")
    catalog = load_audited_catalog(path)
    assert catalog.list()[0].fingerprint == entry.fingerprint
    assert catalog.list()[0].source_ids == ("fixture-source",)
    path.write_text(json.dumps({"entries": [{**_row(), "fingerprint": "0" * 64}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        load_audited_catalog(path)


def test_loader_rejects_missing_evaluation_fingerprint(tmp_path) -> None:
    row = _row()
    row.pop("evaluation_fingerprint")
    entry = FactorCatalogEntry(**row)
    row["fingerprint"] = entry.fingerprint
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"entries": [row]}), encoding="utf-8")
    with pytest.raises(ValueError, match="evaluation fingerprint"):
        load_audited_catalog(path)


@pytest.mark.parametrize("override, message", [
    ({"required_fields": ["future_return"]}, "future"),
    ({"license_status": "PROPRIETARY_UNREVIEWED"}, "license"),
    ({"version": "latest"}, "version"),
])
def test_loader_blocks_unsafe_entries(tmp_path, override, message) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"entries": [_row(**override)]}), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_audited_catalog(path)


def test_loader_blocks_duplicates_and_future_unknown_fields(tmp_path) -> None:
    path = tmp_path / "catalog.json"
    valid = FactorCatalogEntry(**_row())
    row = {**_row(), "fingerprint": valid.fingerprint}
    path.write_text(json.dumps({"entries": [row, row]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_audited_catalog(path)
    path.write_text(json.dumps({"entries": [{**_row(), "new_future_field": True}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="field"):
        load_audited_catalog(path)


def test_missing_admission_returns_proposal_without_registry_write() -> None:
    entry = BUILTIN_AUDITED_CATALOG.list()[0]
    registry = FactorRegistry()
    proposal = admit_catalog_entry(entry, None, registry=registry)
    assert isinstance(proposal, CatalogAdmissionProposal)
    assert proposal.production_write is False
    assert registry.list() == ()


def test_explicit_human_admission_is_required_before_registry_write() -> None:
    entry = BUILTIN_AUDITED_CATALOG.list()[0]
    registry = FactorRegistry()
    admission = HumanAdmissionRecord(entry.factor_id, entry.evaluation_fingerprint, entry.research_fingerprint, "reviewer-1")
    registered = admit_catalog_entry(entry, admission, registry=registry)
    assert registered.metadata.factor_id == entry.factor_id
    assert registry.get(entry.factor_id) == registered


def test_evaluation_fingerprint_mismatch_is_rejected() -> None:
    entry = BUILTIN_AUDITED_CATALOG.list()[0]
    admission = HumanAdmissionRecord(entry.factor_id, "f" * 64, entry.research_fingerprint, "reviewer-1")
    with pytest.raises(ValueError, match="evaluation"):
        admit_catalog_entry(entry, admission, registry=FactorRegistry())


def test_paper_only_admission_is_not_valid_or_selectable() -> None:
    entry = BUILTIN_AUDITED_CATALOG.list()[0]
    registry = FactorRegistry()
    admission = HumanAdmissionRecord(entry.factor_id, entry.evaluation_fingerprint, entry.research_fingerprint, "reviewer-1")
    registered = admit_catalog_entry(entry, admission, registry=registry)
    assert registered.health.status.value == "INSUFFICIENT_DATA"
    assert registry.select_eligible("2026-01-01") == ()
    assert registered.metadata.source_ids == entry.source_ids
