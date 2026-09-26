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
    "fred_alfred": ProviderRoute("fred_alfred", "api", ("browser_download", "cached_snapshot"), True, True, True),
    "sec_edgar": ProviderRoute("sec_edgar", "api", ("browser_download", "cached_snapshot"), False, True, True),
    "ecb_sdmx": ProviderRoute("ecb_sdmx", "api", ("browser_download", "cached_snapshot"), False, True, True),
    "bis_sdmx": ProviderRoute("bis_sdmx", "api", ("browser_download", "cached_snapshot"), False, True, True),
    "official_web": ProviderRoute("official_web", "browser", ("cached_snapshot",), False, True, False),
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
