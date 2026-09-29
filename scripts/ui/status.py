"""Accessible status vocabulary for the dashboard."""
import html


def normalize_status(value, default="not_available"):
    value = str(value or default).strip().lower().replace(" ", "_")
    return value if value else default


def status_badge(value, label=None):
    state = normalize_status(value)
    caption = label or state.replace("_", " ").upper()
    return f'<span class="state-badge" data-state="{html.escape(state, quote=True)}" role="status"><span aria-hidden="true">●</span>{html.escape(caption)}</span>'
