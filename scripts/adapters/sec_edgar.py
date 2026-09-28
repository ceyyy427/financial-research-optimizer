"""SEC EDGAR official API adapter facade."""
try:
    from ..online.sec_edgar import SecEdgarProvider
except ImportError:
    from online.sec_edgar import SecEdgarProvider

from .base import SourceAdapter
from .protocol import SourceRequest, SourceResult
try:
    from ..parsers import parse
except ImportError:
    from parsers import parse


class SecEdgarAdapter(SourceAdapter):
    def __init__(self, profile, user_agent, **kwargs):
        super().__init__(profile, authorization_status="not_required", access_method="api")
        self.provider = SecEdgarProvider(user_agent=user_agent, **kwargs)

    def submissions(self, cik):
        return self.provider.submissions(cik)

    def company_facts(self, cik):
        return self.provider.company_facts(cik)

    def fetch(self, request: SourceRequest) -> SourceResult:
        endpoint = request.params.get("endpoint", "companyfacts")
        if endpoint == "companyfacts":
            payload = self.company_facts(request.instrument)
            response = payload["response"]
            rows = parse("sec_xbrl_filing", payload["data"], instrument_id=request.instrument, source_url=response.request_url)
        elif endpoint == "submissions":
            payload = self.submissions(request.instrument)
            response = payload["response"]
            rows = []
        else:
            raise ValueError(f"unsupported SEC dataset endpoint: {endpoint}")
        return SourceResult(response.snapshot, rows, {"source_id": request.source_id, "dataset": request.dataset, "endpoint": endpoint, "request": request.as_dict()}, "pass" if rows or endpoint == "submissions" else "degraded", [] if rows else ["submissions metadata has no canonical fact rows"])
