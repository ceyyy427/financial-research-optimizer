"""Named JSON backend for callers that prefer an explicit backend type."""

from .run_store import RunStore

JsonRunStore = RunStore

__all__ = ["JsonRunStore"]
