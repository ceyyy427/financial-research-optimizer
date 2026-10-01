import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import pandas as pd

from .models import Dataset, Provenance
from .validation import validate_price_dataset


class ECBProvider:
    BASE_URL = "https://data-api.ecb.europa.eu/service/data/EXR"
    ALLOWED_HOST = "data-api.ecb.europa.eu"

    @classmethod
    def from_csv_fixture(cls, path: str | Path) -> Dataset:
        frame = pd.read_csv(path, parse_dates=["date"], index_col="date")
        validate_price_dataset(frame)
        return Dataset(frame=frame, provenance=Provenance(provider="ecb", source_url=str(path)))

    @classmethod
    def fetch_exchange_rate(cls, currency: str = "USD", start: str | None = None, end: str | None = None) -> Dataset:
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("currency must be a three-letter uppercase code")
        params = {"format": "csvdata", "startPeriod": start, "endPeriod": end}
        query = urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{cls.BASE_URL}/D.{currency}.EUR.SP00.A?{query}"
        request = Request(url, headers={"Accept": "text/csv", "User-Agent": "finahinking/0.1"})
        with urlopen(request, timeout=15) as response:
            if urlparse(response.geturl()).hostname != cls.ALLOWED_HOST:
                raise ValueError("ECB response redirected to an unallowlisted host")
            frame = pd.read_csv(response)
        date_col = "TIME_PERIOD"
        value_col = "OBS_VALUE"
        if date_col not in frame or value_col not in frame:
            raise ValueError("ECB response schema missing TIME_PERIOD or OBS_VALUE")
        normalized = frame[[date_col, value_col]].rename(columns={date_col: "date", value_col: "close"})
        normalized = normalized.set_index("date")
        normalized.index = pd.to_datetime(normalized.index)
        normalized["close"] = pd.to_numeric(normalized["close"], errors="coerce")
        validate_price_dataset(normalized)
        return Dataset(normalized, Provenance(provider="ecb", source_url=url, retrieved_at=datetime.now(UTC)))
