"""Paths to runtime data shipped inside the Finahinking distribution.

The source checkout keeps migrations and fixtures at repository root for
reviewability.  Wheels cannot rely on that checkout layout, so release builds
copy the same files into ``finahinking._package_data`` and callers resolve
them through these small, read-only helpers.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DATA_ROOT = Path(__file__).resolve().parent / "_package_data"


def _resource_path(kind: str, relative: str) -> Path:
    """Return a packaged file while preventing traversal outside its bundle."""

    candidate = (PACKAGE_DATA_ROOT / kind / relative).resolve()
    root = (PACKAGE_DATA_ROOT / kind).resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise FileNotFoundError(f"packaged {kind} resource not found: {relative}")
    return candidate


def migration_path(filename: str) -> Path:
    """Resolve one SQL migration bundled with the installed package."""

    return _resource_path("migrations", filename)


def fixture_path(relative: str) -> Path:
    """Resolve one deterministic sample fixture bundled with the package."""

    return _resource_path("fixtures", relative)


__all__ = ["PACKAGE_DATA_ROOT", "fixture_path", "migration_path"]
