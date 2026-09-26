"""SEC EDGAR submissions and Company Facts adapter."""
from .base_provider import BaseProvider, ProviderError


class SecEdgarProvider(BaseProvider):
    provider_name = "sec_edgar"
    provider_version = "data.sec.gov-v1"
    license_name = "SEC public data terms"
    revision_policy = "filing_date_aware"

    def __init__(self, user_agent, base_url="https://data.sec.gov", **kwargs):
        if not user_agent or "@" not in user_agent:
            raise ProviderError("SEC EDGAR requires a descriptive User-Agent with a contact address")
        super().__init__(user_agent=user_agent, **kwargs)
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _cik(cik):
        value = str(cik).upper().replace("CIK", "").lstrip("0") or "0"
        return value.zfill(10)

    def submissions(self, cik):
        response = self.request(f"{self.base_url}/submissions/CIK{self._cik(cik)}.json", ttl_seconds=3600)
        return {"provider": self.provider_name, "endpoint": "submissions", "data": self.parse_json(response), "response": response}

    def company_facts(self, cik):
        response = self.request(f"{self.base_url}/api/xbrl/companyfacts/CIK{self._cik(cik)}.json", ttl_seconds=86400)
        return {"provider": self.provider_name, "endpoint": "companyfacts", "data": self.parse_json(response), "response": response}
