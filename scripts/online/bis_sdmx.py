"""BIS SDMX data API adapter."""
from .base_provider import BaseProvider


class BisSdmxProvider(BaseProvider):
    provider_name = "bis_sdmx"
    provider_version = "stats.bis.org-api-v2"
    license_name = "BIS statistics terms"
    revision_policy = "vintage_aware"

    def __init__(self, base_url="https://stats.bis.org/api/v2", **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    def fetch_data(self, flow_ref, key="", start_period=None, end_period=None, format_name="csvfile"):
        params = {"format": format_name}
        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period
        response = self.request(f"{self.base_url}/data/{flow_ref}/{key}", params=params, headers={"Accept": "text/csv" if format_name.startswith("csv") else "application/json"}, ttl_seconds=3600)
        return {"provider": self.provider_name, "flow_ref": flow_ref, "key": key, "data": response.body.decode("utf-8"), "response": response}
