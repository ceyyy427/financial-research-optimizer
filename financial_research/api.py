"""Stable client API; implementation modules remain private to the runtime."""
from __future__ import annotations

from typing import Any

from .capabilities import get_capabilities
from .runtime import get_run_status as _get_run_status
from .runtime import read_research_artifact as _read_research_artifact
from .runtime import run_research as _run_research


async def run_research(*args, **kwargs) -> dict[str, Any]:
    return await _run_research(*args, **kwargs)


def get_run_status(store, run_id: str) -> dict[str, Any]:
    return _get_run_status(store, run_id)


def read_artifact(store, run_id: str, artifact: str) -> dict[str, Any]:
    return _read_research_artifact(store, run_id, artifact)


__all__ = ["run_research", "get_run_status", "read_artifact", "get_capabilities"]
