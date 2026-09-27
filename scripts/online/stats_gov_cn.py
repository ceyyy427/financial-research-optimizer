"""National Data provider with the same snapshot contract as other providers."""
from .base_provider import BaseProvider


class StatsGovCnProvider(BaseProvider):
    provider_name = "stats_gov_cn"
    provider_version = "stats-gov-cn-v1"
    license_name = "National Data terms"
    revision_policy = "vintage_aware"

    def __init__(self, **kwargs):
        super().__init__(user_agent="financial-research-optimizer/stats-gov-cn", **kwargs)

    def fetch(self, url, params=None):
        response = self.request(url, params=params or {}, ttl_seconds=3600, snapshot=True)
        return {"provider": self.provider_name, "data": self.parse_json(response), "response": response}
