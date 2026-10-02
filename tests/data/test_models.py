from datetime import UTC, datetime

import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance


def test_provenance_requires_nonempty_provider_and_source_url():
    with pytest.raises(ValueError, match="provider"):
        Provenance(provider="", source_url="https://example.test")
    with pytest.raises(ValueError, match="source_url"):
        Provenance(provider="ecb", source_url="")


def test_provenance_rejects_naive_retrieval_time():
    with pytest.raises(ValueError, match="timezone"):
        Provenance(
            provider="ecb",
            source_url="https://example.test",
            retrieved_at=datetime(2024, 1, 1),  # noqa: DTZ001 - intentionally naive
        )


def test_provenance_accepts_timezone_aware_retrieval_time():
    provenance = Provenance(
        provider="ecb",
        source_url="https://example.test",
        retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    assert provenance.retrieved_at is not None


def test_dataset_requires_provenance_and_normalizes_index():
    frame = pd.DataFrame({"value": [2.0, 1.0]}, index=pd.to_datetime(["2024-01-02", "2024-01-01"]))
    dataset = Dataset(frame=frame, provenance=Provenance(provider="ecb", source_url="https://data-api.ecb.europa.eu"))
    assert dataset.frame.index.is_monotonic_increasing
    assert dataset.frame.index.name == "date"


def test_dataset_rejects_duplicate_dates():
    frame = pd.DataFrame({"value": [1.0, 2.0]}, index=pd.to_datetime(["2024-01-01", "2024-01-01"]))
    with pytest.raises(ValueError, match="duplicate"):
        Dataset(frame=frame, provenance=Provenance(provider="ecb", source_url="https://data-api.ecb.europa.eu"))


def test_dataset_rejects_nonpositive_close_prices():
    frame = pd.DataFrame({"close": [100.0, 0.0]}, index=pd.date_range("2024-01-01", periods=2))
    with pytest.raises(ValueError, match="strictly positive"):
        Dataset(frame=frame, provenance=Provenance(provider="ecb", source_url="https://data-api.ecb.europa.eu"))
