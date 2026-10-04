"""Public project identity and side-effect-free optional capability discovery."""

from __future__ import annotations

import importlib.util
import json
from importlib.metadata import PackageNotFoundError, version


def project_identity() -> dict[str, str]:
    """Return the public name and compatibility names for this release line."""

    return {
        "project_id": "finathink",
        "distribution_name": "finathink",
        "legacy_distribution_name": "finahinking",
        "python_import": "finahinking",
        "cli": "finathink",
    }


def _installed(name: str) -> tuple[str, str]:
    try:
        return "AVAILABLE", version(name)
    except PackageNotFoundError:
        return "ABSENT", ""


def capability_inventory() -> list[dict[str, str]]:
    """Discover optional packages without importing their runtime modules."""

    capabilities: list[dict[str, str]] = []
    for identifier, package, module, reason in (
        ("math_renderer", "katex", None, "frontend bundle decides the renderer"),
        ("sympy", "sympy", "sympy", "optional symbolic verification adapter"),
        ("codemirror", "@codemirror/view", None, "only needed if read-only viewer has a gap"),
        ("crossref", "httpx", "httpx", "resolver transport is optional and offline-safe"),
    ):
        status, package_version = _installed(package) if module is not None else ("UNKNOWN", "")
        if module is not None and status == "ABSENT":
            status = "ABSENT"
        elif module is not None and importlib.util.find_spec(module) is None:
            status = "ABSENT"
            package_version = ""
        capabilities.append({"id": identifier, "status": status, "version": package_version, "reason": reason})
    json.dumps(capabilities, sort_keys=True)
    return capabilities
