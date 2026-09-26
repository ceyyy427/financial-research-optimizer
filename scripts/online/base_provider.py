"""Common provider contract: request, raw cache, snapshot, and provenance."""
import json
from dataclasses import dataclass
from pathlib import Path

from .http_cache import HttpCache
from .snapshot_store import SnapshotStore


class ProviderError(RuntimeError):
    pass


@dataclass
class ProviderResponse:
    status: int
    headers: dict
    body: bytes
    request_url: str
    request_params: dict
    retrieved_at: str
    cache_expiry: str
    response_hash: str
    raw_file: str
    from_cache: bool
    stale: bool
    snapshot: dict | None = None

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class BaseProvider:
    provider_name = "generic"
    provider_version = "1"
    license_name = "unknown"
    revision_policy = "point_in_time"

    def __init__(self, cache=None, snapshot_store=None, user_agent="financial-research-optimizer/online"):
        self.cache = cache or HttpCache(Path(".cache") / "financial-research-optimizer")
        self.snapshot_store = snapshot_store
        self.user_agent = user_agent

    def request(self, url, params=None, headers=None, ttl_seconds=86400, snapshot=True):
        merged_headers = {"User-Agent": self.user_agent, "Accept": "application/json", **(headers or {})}
        try:
            response = self.cache.request("GET", url, params=params, headers=merged_headers, ttl_seconds=ttl_seconds)
        except Exception as exc:
            raise ProviderError(f"{self.provider_name} request failed: {exc}") from exc
        result = ProviderResponse(**response.__dict__)
        if snapshot and self.snapshot_store:
            result.snapshot = self.snapshot_store.save(
                self.provider_name, response, self.provider_version, self.license_name,
                self.revision_policy, request_params=response.request_params,
            )
        return result

    def parse_json(self, response):
        try:
            return response.json()
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"{self.provider_name} returned non-JSON content") from exc
