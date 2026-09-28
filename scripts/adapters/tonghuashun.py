import asyncio
from pathlib import Path

from .base import AdapterError
from .catalog import CatalogSourceAdapter
from .protocol import SourceRequest, SourceResult, source_result_from_legacy

try:
    from ..browser.navigation import BrowserNavigation, NavigationError, tls_policy_from_env
    from ..parsers import parse
    from ..source_snapshot import create_snapshot
except ImportError:
    from browser.navigation import BrowserNavigation, NavigationError, tls_policy_from_env
    from parsers import parse
    from source_snapshot import create_snapshot


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise AdapterError("Tonghuashun browser adapter cannot run inside an active event loop; use its async facade")


class TonghuashunAdapter(CatalogSourceAdapter):
    source_id = "10jqka"

    def __init__(self, profile, browser_root="artifacts/browser", snapshot_dir="artifacts/snapshots", navigation=None, **kwargs):
        super().__init__(profile, authorization_status="not_required", access_method="browser")
        self.snapshot_dir = Path(snapshot_dir)
        self.navigation = navigation or BrowserNavigation(root=browser_root, source_id=self.source_id, **kwargs)

    @staticmethod
    def default_url(instrument_id, market_prefix="hs"):
        return f"https://d.10jqka.com.cn/v4/line/{market_prefix}_{instrument_id}/01/last.js"

    def fetch(self, url=None, params=None, instrument_id=None, market_prefix="hs", market="SZ"):
        if isinstance(url, SourceRequest):
            return self.fetch_request(url)
        params = dict(params or {})
        instrument_id = str(instrument_id or params.get("instrument_id") or params.get("code") or "")
        if not instrument_id:
            raise AdapterError("Tonghuashun requires instrument_id or params.code")
        url = url or self.default_url(instrument_id, params.get("market_prefix", market_prefix))
        try:
            result = _run(self.navigation.fetch_text(url, screenshot=False))
        except NavigationError as exc:
            raise AdapterError(f"Tonghuashun navigation failed: {exc}; failure_snapshot={exc.failure_snapshot}") from exc
        observations = parse(
            self.profile.get("parser", "tonghuashun_jsonp"),
            result.text,
            instrument_id=instrument_id,
            source_url=result.url,
            availability_time=result.retrieved_at,
            market=market,
        )
        snapshot = create_snapshot(
            self.source_id,
            result.raw_file,
            self.snapshot_dir,
            result.url,
            request_params=params,
            response_status=result.status or 200,
            content_type=result.content_type or "application/javascript",
            parser_version=self.profile.get("parser", "tonghuashun_jsonp"),
            access_method="browser",
            source_authority=self.profile.get("authority", "secondary_aggregator"),
            authorization_status="not_required",
            point_in_time_status="not_available",
            revision_status="latest_only",
            license_name=self.profile.get("name", "Tonghuashun public page"),
        )
        snapshot["tls_policy"] = tls_policy_from_env()
        return {"source_id": self.source_id, "data": result.text, "observations": observations, "snapshot": snapshot, "response": result}

    def fetch_request(self, request: SourceRequest) -> SourceResult:
        params = dict(request.params)
        params.setdefault("instrument_id", request.instrument)
        return source_result_from_legacy(self.fetch(request.requested_url, params=params, instrument_id=request.instrument, market=params.get("market", "SZ")), request)
