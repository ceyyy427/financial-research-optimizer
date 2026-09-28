"""FRED and ALFRED adapter facade with explicit vintage routing."""
try:
    from ..online.fred_alfred import FredAlfredProvider
    from ..parsers import parse
    from ..online.http_cache import HttpCache
    from ..online.snapshot_store import SnapshotStore
except ImportError:
    from online.fred_alfred import FredAlfredProvider
    from parsers import parse
    from online.http_cache import HttpCache
    from online.snapshot_store import SnapshotStore

from .base import SourceAdapter
from .protocol import SourceRequest, SourceResult


class FredAlfredAdapter(SourceAdapter):
    def __init__(self, profile, **kwargs):
        super().__init__(profile, authorization_status="authorized" if kwargs.get("api_key_env") else "unknown", access_method="api")
        cache_dir = kwargs.pop("cache_dir", ".cache/financial-research-optimizer")
        snapshot_dir = kwargs.pop("snapshot_dir", "artifacts/snapshots")
        transport = kwargs.pop("transport", None)
        kwargs.setdefault("cache", HttpCache(cache_dir, transport=transport))
        kwargs.setdefault("snapshot_store", SnapshotStore(snapshot_dir))
        self.provider = FredAlfredProvider(source_id=profile["source_id"], **kwargs)

    def fetch_series(self, series_id, **kwargs):
        if self.profile["source_id"] == "alfred":
            kwargs.setdefault("realtime_start", kwargs.get("realtime_start"))
            kwargs.setdefault("realtime_end", kwargs.get("realtime_end"))
        return self.provider.fetch_series(series_id, **kwargs)

    def fetch(self, request: SourceRequest) -> SourceResult:
        params = dict(request.params)
        payload = self.fetch_series(
            request.instrument,
            observation_start=request.start,
            observation_end=request.end,
            realtime_start=params.get("realtime_start") or request.as_of,
            realtime_end=params.get("realtime_end") or request.as_of,
        )
        response = payload["response"]
        rows = parse(
            "fred_json_realtime_period" if request.source_id == "alfred" else "fred_json",
            payload["data"],
            instrument_id=request.instrument,
            source_url=response.request_url,
            availability_time=response.retrieved_at,
            vintage_time=params.get("realtime_start") if request.source_id == "alfred" else None,
        )
        limitations = [] if request.source_id == "alfred" and (params.get("realtime_start") or request.as_of) else ["FRED result uses retrieval/vintage parameters supplied at runtime"]
        return SourceResult(response.snapshot, rows, {"source_id": request.source_id, "dataset": request.dataset, "request": request.as_dict()}, "pass" if rows else "degraded", limitations)
