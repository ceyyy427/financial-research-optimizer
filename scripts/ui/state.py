"""Serializable, non-computational state for the offline dashboard."""
from __future__ import annotations

import json


DEFAULT_UI_STATE = {
    "run_id": None,
    "active_tab": "overview",
    "selected_model": "all",
    "selected_source": "all",
    "time_range": "all",
    "horizon": None,
    "scenario_id": None,
    "pending_action": None,
    "theme": "system",
}


def normalize_state(value=None, *, run_id=None):
    """Return a bounded UI state; this function never changes financial data."""
    state = dict(DEFAULT_UI_STATE)
    if isinstance(value, dict):
        state.update({key: value[key] for key in state if key in value})
    if run_id is not None:
        state["run_id"] = str(run_id)
    if state["active_tab"] not in {"overview", "why", "forecast", "risk", "portfolio", "provenance", "learning"}:
        state["active_tab"] = "overview"
    if state["theme"] not in {"system", "light", "dark"}:
        state["theme"] = "system"
    return state


def state_json(value=None, *, run_id=None):
    return json.dumps(normalize_state(value, run_id=run_id), ensure_ascii=False, separators=(",", ":"))
