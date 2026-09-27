#!/usr/bin/env python3
"""Backward-compatible alias for :mod:`build_refresh_plan`."""

try:
    from .build_refresh_plan import build_refresh_plan, main
except ImportError:
    from build_refresh_plan import build_refresh_plan, main
