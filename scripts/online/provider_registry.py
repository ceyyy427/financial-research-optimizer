"""Route a source to API-first, browser-second, cache-last access modes."""
from dataclasses import dataclass


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
