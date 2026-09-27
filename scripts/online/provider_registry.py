"""Route low-level providers or use the full capability-aware source registry."""
from dataclasses import dataclass
from pathlib import Path

try:
    from ..source_router import SourceRouter
except ImportError:
    from source_router import SourceRouter


@dataclass(frozen=True)
class ProviderRoute:
    source_id: str
    access_mode: str
    fallback: tuple
    requires_auth: bool
    point_in_time_support: bool
    revision_support: bool


ROUTES = {
    "fred": ProviderRoute("fred", "api", ("cached_snapshot",), True, False, True),
    "alfred": ProviderRoute("alfred", "api", ("cached_snapshot",), True, True, True),
    "sec_edgar": ProviderRoute("sec_edgar", "api", ("browser_download", "cached_snapshot"), False, True, True),
    "ecb_sdmx": ProviderRoute("ecb_sdmx", "api", ("browser_download", "cached_snapshot"), False, True, True),
    "bis_sdmx": ProviderRoute("bis_sdmx", "api", ("browser_download", "cached_snapshot"), False, True, True),
    "official_web": ProviderRoute("official_web", "browser", ("cached_snapshot",), False, True, False),
}


def build_provider(source_id, cache, snapshot_store, transport=None, user_agent=None, **kwargs):
    """Construct the source-specific provider; never silently fall back to BaseProvider."""
    from .bis_sdmx import BisSdmxProvider
    from .ecb_sdmx import EcbSdmxProvider
    from .fred_alfred import FredAlfredProvider
    from .sec_edgar import SecEdgarProvider
    from .stats_gov_cn import StatsGovCnProvider

    common = {"cache": cache, "snapshot_store": snapshot_store}
    if transport is not None:
        # HttpCache owns the injectable transport.  Keeping this explicit makes
        # provider construction auditable and keeps tests offline.
        cache.transport = transport
    factories = {
        "stats_gov_cn": lambda: StatsGovCnProvider(**common),
        "fred": lambda: FredAlfredProvider(source_id="fred", **common),
        "alfred": lambda: FredAlfredProvider(source_id="alfred", **common),
        "sec_edgar": lambda: SecEdgarProvider(user_agent=user_agent or "financial-research-optimizer/SEC contact@example.invalid", **common),
        "ecb_sdmx": lambda: EcbSdmxProvider(**common),
        "bis_sdmx": lambda: BisSdmxProvider(**common),
    }
    factory = factories.get(source_id)
    if factory is None:
        raise KeyError(f"no executable provider registered for {source_id}")
    return factory()


PROVIDER_IDS = frozenset({"stats_gov_cn", "fred", "alfred", "sec_edgar", "ecb_sdmx", "bis_sdmx"})


def provider_alignment(source_id, profile):
    provider_id = profile.get("provider_id", source_id)
    adapter_id = profile.get("adapter_id", source_id)
    return {
        "source_id": source_id,
        "provider_id": provider_id,
        "adapter_id": adapter_id,
        "aligned": provider_id == source_id and adapter_id == source_id,
        "provider_registered": source_id in PROVIDER_IDS,
    }


def route_provider(source_id, prefer_browser=False):
    route = ROUTES.get(source_id)
    if not route:
        raise KeyError(f"no provider route registered for {source_id}")
    if prefer_browser and route.access_mode == "api":
        return ProviderRoute(route.source_id, "browser", route.fallback, route.requires_auth, route.point_in_time_support, route.revision_support)
    return route


def resolve_source(topic, universe=None, required_capabilities=None, required_fields=None, registry_path=None, **kwargs):
    """Resolve a website/profile through the executable source registry."""
    router = SourceRouter.from_file(registry_path or Path(__file__).resolve().parents[2] / "config" / "source_registry.yaml")
    return router.resolve(topic, universe, required_capabilities, required_fields, **kwargs)
