"""Optional capability detection with explicit, non-crashing fallbacks."""

from __future__ import annotations

import importlib.metadata
import importlib.util
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(frozen=True)
class Capability:
    name: str
    status: str
    version: str | None = None
    environment: str = "core"
    detail: str = ""
    provider: str = "Finathink"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "version": self.version,
            "environment": self.environment,
            "detail": self.detail,
            "provider": self.provider,
        }


@dataclass(frozen=True)
class CapabilityRegistry:
    """A snapshot of optional/runtime capabilities.

    Detection never imports an optional package.  ``find_spec`` and metadata
    lookup are both guarded because a partially-installed distribution should
    be represented as unavailable rather than crash application startup.
    """

    capabilities: dict[str, Capability] = field(default_factory=dict)

    _PROBES: ClassVar[dict[str, tuple[str, str, str]]] = {
        "qlib": ("qlib", "isolated", "Qlib ML research sandbox"),
        "vectorbt": ("vectorbt", "isolated", "vectorbt parameter research sandbox"),
        "lightgbm": ("lightgbm", "isolated", "LightGBM baseline provider"),
        "statsmodels": ("statsmodels", "core", "statsmodels adapter"),
        "numpy": ("numpy", "core", "internal numerical runtime"),
        "pandas": ("pandas", "core", "internal tabular runtime"),
    }

    @classmethod
    def detect(cls) -> CapabilityRegistry:
        found: dict[str, Capability] = {}
        for name, (module_name, environment, detail) in cls._PROBES.items():
            try:
                present = importlib.util.find_spec(module_name) is not None
            except (ImportError, ModuleNotFoundError, ValueError):
                present = False
            version = None
            if present:
                try:
                    version = importlib.metadata.version(module_name)
                except importlib.metadata.PackageNotFoundError:
                    version = None
                except (OSError, RuntimeError, TypeError):  # pragma: no cover - hostile metadata
                    version = None
            found[name] = Capability(
                name=name,
                status="AVAILABLE" if present else "NOT INSTALLED",
                version=version,
                environment=environment,
                detail=detail,
                provider=name,
            )
        # QMT is a connection boundary, not a Python dependency.  It starts
        # disconnected and is promoted by the bridge only after a read-only
        # connection is established.
        found["qmt"] = Capability(
            name="qmt",
            status="NOT CONNECTED",
            environment="bridge",
            detail="read-only market-data bridge; authenticate in the official QMT client",
            provider="QMT bridge",
        )
        found["chart_renderer"] = Capability(
            name="chart_renderer",
            status="AVAILABLE",
            environment="core",
            detail="server-normalized chart payload and local renderer",
            provider="Finathink",
        )
        found["internal_quant"] = Capability(
            name="internal_quant",
            status="AVAILABLE",
            environment="core",
            detail="Finathink-owned quant research engine",
            provider="Finathink",
        )
        return cls(found)

    def get(self, name: str, default: Capability | None = None) -> Capability | None:
        aliases = {
            "qlib ml": "qlib",
            "qlib_ml": "qlib",
            "vectorbt sweep": "vectorbt",
            "vectorbt_sweep": "vectorbt",
            "qmt data": "qmt",
            "qmt bridge": "qmt",
        }
        key = aliases.get(name.casefold(), name)
        return self.capabilities.get(key, default)

    def status(self, name: str) -> str:
        capability = self.get(name)
        return capability.status if capability is not None else "NOT INSTALLED"

    def __getitem__(self, name: str) -> Capability:
        return self.capabilities[name]

    def __iter__(self):
        return iter(self.capabilities)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {name: capability.to_dict() for name, capability in sorted(self.capabilities.items())}


__all__ = ["Capability", "CapabilityRegistry"]
