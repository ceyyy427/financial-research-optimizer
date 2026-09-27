"""Source-specific adapter layer over registry, browser, API, and snapshots."""

from .catalog import CatalogSourceAdapter
from .fred_alfred import FredAlfredAdapter
from .licensed_provider import LicensedProviderAdapter
from .sec_edgar import SecEdgarAdapter
from .tonghuashun import TonghuashunAdapter

__all__ = ["CatalogSourceAdapter", "FredAlfredAdapter", "LicensedProviderAdapter", "SecEdgarAdapter", "TonghuashunAdapter"]
