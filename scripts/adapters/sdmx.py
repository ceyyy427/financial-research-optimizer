"""Explicit ECB/BIS SDMX adapter returning the common source result."""

try:
    from ..online.bis_sdmx import BisSdmxProvider
    from ..online.ecb_sdmx import EcbSdmxProvider
    from ..parsers import parse
except ImportError:
    from online.bis_sdmx import BisSdmxProvider
    from online.ecb_sdmx import EcbSdmxProvider
    from parsers import parse

from .base import SourceAdapter
from .protocol import SourceRequest, SourceResult


class SdmxAdapter(SourceAdapter):
    def __init__(self, profile, cache_dir, snapshot_dir, transport=None, **kwargs):
        super().__init__(profile, authorization_status="not_required", access_method="api")
        provider_cls = EcbSdmxProvider if profile["source_id"] == "ecb_sdmx" else BisSdmxProvider
        try:
            from ..online.http_cache import HttpCache
            from ..online.snapshot_store import SnapshotStore
        except ImportError:
            from online.http_cache import HttpCache
            from online.snapshot_store import SnapshotStore
        self.provider = provider_cls(cache=HttpCache(cache_dir, transport=transport), snapshot_store=SnapshotStore(snapshot_dir))

    def fetch(self, request: SourceRequest) -> SourceResult:
        flow_ref = request.params.get("flow_ref") or request.instrument
        if not flow_ref:
            raise ValueError(f"{request.source_id}: flow_ref or instrument is required")
        payload = self.provider.fetch_data(flow_ref, request.params.get("key", ""), request.start, request.end)
        response = payload["response"]
        rows = parse("ecb_sdmx_json" if request.source_id == "ecb_sdmx" else "bis_sdmx_json", payload["data"], instrument_id=request.instrument or flow_ref, source_url=response.request_url)
        return SourceResult(response.snapshot, rows, {"source_id": request.source_id, "dataset": request.dataset, "request": request.as_dict()}, "pass" if rows else "degraded", [] if rows else ["empty SDMX response"])
