from __future__ import annotations

import pytest

from finahinking.p8_2b.references import LocalReferenceCache, ReferenceRecord, normalize_doi


def test_doi_normalization_cache_and_bibtex_are_deterministic() -> None:
    assert normalize_doi("https://doi.org/10.2307/232") == "10.2307/232"
    record = ReferenceRecord(
        reference_id="ols-1936",
        title="Statistical laws in research",
        authors=("Harold Hotelling",),
        year=1936,
        reference_type="PAPER",
        role="FOUNDATIONAL_REFERENCE",
        doi="10.2307/232",
        url="https://doi.org/10.2307/232",
        publisher="Journal Publisher",
        source="CURATED",
        notes="Foundational reading.",
    )
    cache = LocalReferenceCache((record,))
    assert cache.get("10.2307/232") == record
    assert "@article{ols-1936" in record.bibtex()
    assert record.to_csl_json()["DOI"] == "10.2307/232"


def test_reference_rejects_invalid_doi_and_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="DOI"):
        ReferenceRecord("bad", "Title", ("Author",), 2020, "PAPER", "FURTHER_READING", "10", "https://example.test", "Pub", "CURATED", "Notes")
    record = ReferenceRecord("dup", "Title", ("Author",), 2020, "BOOK", "FURTHER_READING", None, "https://example.test", "Pub", "CURATED", "Notes")
    with pytest.raises(ValueError, match="duplicate"):
        LocalReferenceCache((record, record))
