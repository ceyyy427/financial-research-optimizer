"""FRED and ALFRED adapter facade with explicit vintage routing."""
try:
    from ..online.fred_alfred import FredAlfredProvider
except ImportError:
    from online.fred_alfred import FredAlfredProvider

from .base import SourceAdapter


class FredAlfredAdapter(SourceAdapter):
    def __init__(self, profile, **kwargs):
        super().__init__(profile, authorization_status="authorized" if kwargs.get("api_key_env") else "unknown", access_method="api")
        self.provider = FredAlfredProvider(source_id=profile["source_id"], **kwargs)

    def fetch_series(self, series_id, **kwargs):
        if self.profile["source_id"] == "alfred":
            kwargs.setdefault("realtime_start", kwargs.get("realtime_start"))
            kwargs.setdefault("realtime_end", kwargs.get("realtime_end"))
        return self.provider.fetch_series(series_id, **kwargs)
