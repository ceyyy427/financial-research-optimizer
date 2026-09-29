"""Explicit source adapter factory.

Unknown sources and undeclared datasets fail closed.  A browser adapter is
never selected merely because a URL was supplied by a caller.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .base import AdapterError, SourceAdapter
from .cninfo import CninfoAdapter
from .eastmoney import EastmoneyAdapter
from .fred_alfred import FredAlfredAdapter
from .licensed_provider import LicensedProviderAdapter
from .nasdaq_data_link import NasdaqDataLinkAdapter
from .pbc import PbcAdapter
from .protocol import SourceRequest, SourceResult, source_result_from_legacy
from .sec_edgar import SecEdgarAdapter
from .sse import SseAdapter
from .stats_gov_cn import StatsGovCnAdapter
from .szse import SzseAdapter
from .tonghuashun import TonghuashunAdapter
from .yahoo_finance import YahooFinanceAdapter


class AdapterNotReady(AdapterError):
    """The requested source/dataset is declared but not executable."""


class AdapterAuthorizationRequired(AdapterError):
    """The requested source requires an external authorization reference."""


DATASETS = {
    "stats_gov_cn": "macro_series",
    "pbc": "macro_series",
    "cninfo": "announcements_pdf",
    "sse": "market_file",
    "szse": "market_file",
    "eastmoney": "market_daily",
    "10jqka": "daily_line",
    "wind": "authorized_snapshot",
    "csmar": "authorized_snapshot",
    "sec_edgar": "company_facts",
    "fred": "series_observations",
    "alfred": "vintage_series",
    "nasdaq_data_link": "dataset_slice",
    "yahoo_finance": "chart_history",
    "investing_com": "market_history",
    "tradingview": "chart_history",
    "akshare": "library_daily",
    "tushare": "daily",
    "joinquant": "authorized_snapshot",
    "ecb_sdmx": "sdmx_series",
    "bis_sdmx": "sdmx_series",
}

# Dataset contracts are deliberately explicit.  A source-level adapter cannot
# silently claim every endpoint exposed by the website or vendor.
DATASET_CONTRACTS = {source_id: {dataset_id} for source_id, dataset_id in DATASETS.items()}
DATASET_CONTRACTS["sec_edgar"].add("submissions")

# These are the only source IDs with a tested end-to-end SourceRequest fetch.
# Other IDs still have explicit factory entries so they fail with a precise
# blocked/not-ready result rather than falling through to generic HTTP.
IMPLEMENTED_ADAPTERS = frozenset({"stats_gov_cn", "10jqka", "sec_edgar", "fred", "alfred", "ecb_sdmx", "bis_sdmx"})


def is_fetch_implemented(source_id: str, dataset_id: str | None = None, access_method: str | None = None) -> bool:
    """Single source of truth for formal fetch capability."""
    if source_id not in IMPLEMENTED_ADAPTERS:
        return False
    return dataset_id is None or dataset_id in DATASET_CONTRACTS.get(source_id, set())


_CONTRACT_ONLY = {
    "pbc": PbcAdapter,
    "cninfo": CninfoAdapter,
    "sse": SseAdapter,
    "szse": SzseAdapter,
    "eastmoney": EastmoneyAdapter,
    "wind": LicensedProviderAdapter,
    "csmar": LicensedProviderAdapter,
    "nasdaq_data_link": NasdaqDataLinkAdapter,
    "yahoo_finance": YahooFinanceAdapter,
    "investing_com": YahooFinanceAdapter,
    "tradingview": YahooFinanceAdapter,
    "akshare": LicensedProviderAdapter,
    "tushare": LicensedProviderAdapter,
    "joinquant": LicensedProviderAdapter,
}


def default_dataset(source_id: str) -> str:
    try:
        return DATASETS[source_id]
    except KeyError as exc:
        raise AdapterNotReady(f"no dataset contract registered for source_id={source_id}") from exc


def _host_allowed(url: str, base_urls: list[str] | None) -> bool:
    if not base_urls:
        return False
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    for base in base_urls:
        base_host = (urlparse(base).hostname or "").lower()
        if base_host and (host == base_host or host.endswith("." + base_host)):
            return True
    return False


def validate_requested_url(profile: dict, requested_url: str | None) -> None:
    if requested_url and not _host_allowed(requested_url, profile.get("base_urls")):
        raise AdapterError(f"requested URL is outside the source allowlist: {requested_url}")


class _LegacyBridge:
    def __init__(self, implementation, request: SourceRequest):
        self.implementation = implementation
        self.request = request
        self.source_id = request.source_id

    def fetch(self, request: SourceRequest) -> SourceResult:
        if hasattr(self.implementation, "fetch_request"):
            return self.implementation.fetch_request(request)
        raise AdapterNotReady(f"adapter {request.source_id} does not implement SourceRequest.fetch")


class ContractOnlyAdapter(SourceAdapter):
    def __init__(self, profile, authorization_status="unknown"):
        super().__init__(profile, authorization_status=authorization_status, access_method=profile.get("primary_method"))

    def fetch(self, request: SourceRequest) -> SourceResult:
        if self.profile.get("access_policy") in {"authorized_only", "licensed_only"} and not request.authorization_ref:
            raise AdapterAuthorizationRequired(f"{request.source_id}:{request.dataset} requires authorization_ref")
        raise AdapterNotReady(
            f"{request.source_id}:{request.dataset} is declared {self.profile.get('implementation_status')}/"
            f"{self.profile.get('parser_status')} and has no executable slice"
        )


def build_adapter(source_id: str, profile: dict, output_dir="artifacts/online", transport=None, navigation=None, user_agent=None, authorization_status="unknown"):
    expected = profile.get("source_id")
    if expected != source_id:
        raise AdapterError(f"source/profile mismatch: {source_id} != {expected}")
    common = {
        "cache_dir": Path(output_dir) / "cache",
        "snapshot_dir": Path(output_dir) / "snapshots",
        "transport": transport,
    }
    if source_id == "stats_gov_cn":
        return StatsGovCnAdapter(profile, **common)
    if source_id == "10jqka":
        return TonghuashunAdapter(profile, browser_root=Path(output_dir) / "browser", snapshot_dir=Path(output_dir) / "snapshots", navigation=navigation)
    if source_id == "sec_edgar":
        return SecEdgarAdapter(profile, user_agent=user_agent or "financial-research-optimizer/contact@example.invalid", cache_dir=Path(output_dir) / "cache", snapshot_dir=Path(output_dir) / "snapshots", transport=transport)
    if source_id in {"fred", "alfred"}:
        return FredAlfredAdapter(profile, cache_dir=Path(output_dir) / "cache", snapshot_dir=Path(output_dir) / "snapshots", transport=transport)
    if source_id in {"ecb_sdmx", "bis_sdmx"}:
        from .sdmx import SdmxAdapter
        return SdmxAdapter(profile, cache_dir=Path(output_dir) / "cache", snapshot_dir=Path(output_dir) / "snapshots", transport=transport)
    if source_id not in _CONTRACT_ONLY:
        raise AdapterNotReady(f"no explicit adapter factory entry for source_id={source_id}")
    return ContractOnlyAdapter(profile, authorization_status=authorization_status)


def build_request(source_id: str, params: dict | None = None, requested_url: str | None = None) -> SourceRequest:
    if source_id not in DATASET_CONTRACTS:
        raise AdapterNotReady(f"no dataset contract registered for source_id={source_id}")
    params = dict(params or {})
    dataset = str(params.pop("dataset", DATASETS.get(source_id, "default")))
    if dataset not in DATASET_CONTRACTS[source_id]:
        allowed = ", ".join(sorted(DATASET_CONTRACTS[source_id]))
        raise AdapterNotReady(f"undeclared dataset for {source_id}: {dataset}; allowed={allowed}")
    return SourceRequest(
        source_id=source_id,
        dataset=dataset,
        instrument=params.pop("instrument", None) or params.get("instrument_id") or params.get("series_id") or params.get("cik"),
        start=params.pop("start", None) or params.get("observation_start"),
        end=params.pop("end", None) or params.get("observation_end"),
        as_of=params.pop("as_of", None),
        adjustment=params.pop("adjustment", None),
        authorization_ref=params.pop("authorization_ref", None),
        access_method=params.pop("access_method", None),
        params=params,
        requested_url=requested_url,
    )


def fetch_with_adapter(adapter, request: SourceRequest) -> SourceResult:
    """Invoke only the formal request method; no generic HTTP fallback exists."""
    validate_requested_url(adapter.profile, request.requested_url)
    method = getattr(adapter, "fetch", None)
    if method is None:
        raise AdapterNotReady(f"adapter {request.source_id} has no fetch implementation")
    result = method(request)
    if not isinstance(result, SourceResult):
        raise AdapterError(f"adapter {request.source_id} returned a non-SourceResult payload")
    return result
