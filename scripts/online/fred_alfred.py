"""FRED/ALFRED series adapter with real-time vintage parameters."""
import os

from .base_provider import BaseProvider, ProviderError


class FredAlfredProvider(BaseProvider):
    provider_name = "fred_alfred"
    provider_version = "fred-api-v1"
    license_name = "FRED terms of use"
    revision_policy = "vintage_aware"

    def __init__(self, api_key_env="FRED_API_KEY", base_url="https://api.stlouisfed.org/fred", **kwargs):
        super().__init__(**kwargs)
        self.api_key = os.environ.get(api_key_env)
        self.api_key_env = api_key_env
        self.base_url = base_url.rstrip("/")

    def fetch_series(self, series_id, observation_start=None, observation_end=None, realtime_start=None, realtime_end=None, file_type="json"):
        if not self.api_key:
            raise ProviderError("FRED/ALFRED requires an API key; pass api_key explicitly and never commit it")
        params = {"series_id": series_id, "api_key": self.api_key, "file_type": file_type}
        for key, value in (("observation_start", observation_start), ("observation_end", observation_end), ("realtime_start", realtime_start), ("realtime_end", realtime_end)):
            if value:
                params[key] = value
        response = self.request(f"{self.base_url}/series/observations", params=params, ttl_seconds=3600)
        return {"provider": self.provider_name, "series_id": series_id, "data": self.parse_json(response), "response": response}
