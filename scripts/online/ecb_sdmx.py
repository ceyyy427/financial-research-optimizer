"""ECB SDMX data API adapter."""
from .base_provider import BaseProvider


class EcbSdmxProvider(BaseProvider):
    provider_name = "ecb_sdmx"
    provider_version = "data-api.ecb.europa.eu-v1"
    license_name = "ECB data terms"
    revision_policy = "vintage_aware"

    def __init__(self, base_url="https://data-api.ecb.europa.eu/service", **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    def fetch_data(self, flow_ref, key="", start_period=None, end_period=None, format_name="csvdata"):
        params = {"format": format_name}
        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period
        response = self.request(f"{self.base_url}/data/{flow_ref}/{key}", params=params, headers={"Accept": "text/csv" if format_name == "csvdata" else "application/json"}, ttl_seconds=3600)
        return {"provider": self.provider_name, "flow_ref": flow_ref, "key": key, "data": response.body.decode("utf-8"), "response": response}
