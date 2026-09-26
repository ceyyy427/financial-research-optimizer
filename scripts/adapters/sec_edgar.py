"""SEC EDGAR official API adapter facade."""
from online.sec_edgar import SecEdgarProvider

from .base import SourceAdapter


class SecEdgarAdapter(SourceAdapter):
    def __init__(self, profile, user_agent, **kwargs):
        super().__init__(profile, authorization_status="not_required", access_method="api")
        self.provider = SecEdgarProvider(user_agent=user_agent, **kwargs)

    def submissions(self, cik):
        return self.provider.submissions(cik)

    def company_facts(self, cik):
        return self.provider.company_facts(cik)
