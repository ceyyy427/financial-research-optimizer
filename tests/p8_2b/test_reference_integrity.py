from __future__ import annotations

from finahinking.p8_2b.catalog import DEFAULT_KNOWLEDGE_CATALOG


def test_flagship_references_have_curated_doi_title_author_alignment() -> None:
    """Guard against a DOI resolving to a different paper than its label."""

    expected = {
        "ols-1922": ("10.1098/rsta.1922.0009", "On the Mathematical Foundations of Theoretical Statistics", "R. A. Fisher", 1922),
        "sharpe-1966": ("10.1086/294846", "Mutual Fund Performance", "William F. Sharpe", 1966),
        "jegadeesh-titman-1993": ("10.1111/j.1540-6261.1993.tb04702.x", "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency", "Narasimhan Jegadeesh", 1993),
        "harvey-2016": ("10.1093/rfs/hhv059", "… and the Cross-Section of Expected Returns", "Campbell R. Harvey", 2015),
    }
    records = {record.reference_id: record for record in DEFAULT_KNOWLEDGE_CATALOG.references.records()}
    for reference_id, (doi, title, author, year) in expected.items():
        record = records[reference_id]
        assert record.doi == doi
        assert record.title == title
        assert author in record.authors
        assert record.year == year
        assert record.source == "CROSSREF_CURATED"


def test_every_catalog_reference_id_resolves_to_local_metadata() -> None:
    records = DEFAULT_KNOWLEDGE_CATALOG.references
    for unit in DEFAULT_KNOWLEDGE_CATALOG.units:
        for reference_id in unit.references:
            assert records.get(reference_id) is not None, (unit.unit_id, reference_id)

