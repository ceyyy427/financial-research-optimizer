from pathlib import Path

import pandas as pd
import pytest

from finahinking.data.providers import ECBProvider


def test_ecb_provider_loads_recorded_csv_fixture():
    path = Path("fixtures/ecb/exchange_rate_usd_eur.csv")
    dataset = ECBProvider.from_csv_fixture(path)
    assert dataset.provenance.provider == "ecb"
    assert list(dataset.frame.columns) == ["close"]
    assert dataset.frame.index[0] == pd.Timestamp("2024-01-02")


def test_ecb_provider_rejects_unsafe_currency_code():
    with pytest.raises(ValueError, match="three-letter"):
        ECBProvider.fetch_exchange_rate("USD/../../secret")
