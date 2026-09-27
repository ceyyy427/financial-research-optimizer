from .catalog import CatalogSourceAdapter
try:
    from ..online.base_provider import BaseProvider
    from ..online.http_cache import HttpCache
    from ..online.snapshot_store import SnapshotStore
    from ..parsers import parse
except ImportError:
    from online.base_provider import BaseProvider
    from online.http_cache import HttpCache
    from online.snapshot_store import SnapshotStore
    from parsers import parse


class StatsGovCnAdapter(CatalogSourceAdapter):
    source_id = "stats_gov_cn"

    def __init__(self, profile, cache_dir=".cache/financial-research-optimizer", snapshot_dir="artifacts/snapshots", transport=None, **kwargs):
        super().__init__(profile, authorization_status="not_required", access_method="api")
        self.provider = BaseProvider(
            cache=HttpCache(cache_dir, transport=transport),
            snapshot_store=SnapshotStore(snapshot_dir),
            user_agent="financial-research-optimizer/stats-gov-cn",
        )
        self.provider.provider_name = profile["source_id"]
        self.provider.provider_version = "stats-gov-cn-v1"
        self.provider.license_name = "National Data terms"
        self.provider.revision_policy = "vintage_aware"

    def fetch(self, url, params=None, instrument_id=None):
        response = self.provider.request(url, params=params, ttl_seconds=3600, snapshot=True)
        payload = self.provider.parse_json(response)
        rows = parse(self.profile["parser"], payload, instrument_id=instrument_id, source_url=url)
        snapshot = dict(response.snapshot or {})
        snapshot.update({
            "source_id": self.profile["source_id"],
            "access_method": "api",
            "source_authority": self.profile["authority"],
            "authorization_status": "not_required",
            "point_in_time_status": "pass" if rows and all(row.get("point_in_time_status") == "pass" for row in rows) else "not_available",
            "revision_status": "vintage_aware",
            "parser_version": self.profile["parser"],
            "response_status": response.status,
            "content_type": response.headers.get("content-type", ""),
            "snapshot_hash": f"sha256:{snapshot.get('snapshot_hash', response.response_hash)}" if not str(snapshot.get("snapshot_hash", "")).startswith("sha256:") else snapshot.get("snapshot_hash"),
            "fallback_used": response.from_cache,
        })
        return {"source_id": self.profile["source_id"], "data": payload, "observations": rows, "snapshot": snapshot, "response": response}
