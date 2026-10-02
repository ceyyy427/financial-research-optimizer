from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from finahinking.data.providers import ECBProvider


class _Response(BytesIO):
    def __init__(self, payload: str, url: str) -> None:
        super().__init__(payload.encode("utf-8"))
        self._url = url

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.close()


def test_ecb_provider_loads_recorded_csv_fixture():
    path = Path("fixtures/ecb/exchange_rate_usd_eur.csv")
    dataset = ECBProvider.from_csv_fixture(path)
    assert dataset.provenance.provider == "ecb"
    assert "ECB statistics" in dataset.provenance.license
    assert list(dataset.frame.columns) == ["close"]
    assert dataset.frame.index[0] == pd.Timestamp("2024-01-02")


def test_ecb_provider_rejects_unsafe_currency_code():
    with pytest.raises(ValueError, match="three-letter"):
        ECBProvider.fetch_exchange_rate("USD/../../secret")


def test_ecb_provider_rejects_malformed_response_schema(monkeypatch):
    monkeypatch.setattr(
        "finahinking.data.providers.urlopen",
        lambda *_args, **_kwargs: _Response("wrong,value\n2024-01-01,1\n", ECBProvider.BASE_URL),
    )
    with pytest.raises(ValueError, match="schema"):
        ECBProvider.fetch_exchange_rate("USD")


def test_ecb_provider_rejects_redirect_to_unallowlisted_host(monkeypatch):
    payload = "TIME_PERIOD,OBS_VALUE\n2024-01-01,1.1\n2024-01-02,1.2\n"
    monkeypatch.setattr(
        "finahinking.data.providers.urlopen",
        lambda *_args, **_kwargs: _Response(payload, "https://example.test/redirect"),
    )
    with pytest.raises(ValueError, match="unallowlisted"):
        ECBProvider.fetch_exchange_rate("USD")


def test_ecb_provider_preserves_live_url_and_utc_retrieval_time(monkeypatch):
    payload = "TIME_PERIOD,OBS_VALUE\n2024-01-01,1.1\n2024-01-02,1.2\n"
    monkeypatch.setattr(
        "finahinking.data.providers.urlopen",
        lambda *_args, **_kwargs: _Response(payload, ECBProvider.BASE_URL),
    )
    dataset = ECBProvider.fetch_exchange_rate("USD", start="2024-01-01", end="2024-01-02")
    assert dataset.provenance.source_url.startswith(ECBProvider.BASE_URL)
    assert dataset.provenance.retrieved_at is not None
    assert dataset.provenance.retrieved_at.utcoffset() is not None
