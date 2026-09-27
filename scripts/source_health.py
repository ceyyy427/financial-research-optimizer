"""Normalize runtime provider health for routing and reporting."""
from __future__ import annotations

from datetime import datetime, timezone


HEALTH_MULTIPLIER = {"healthy": 1.0, "degraded": 0.75, "stale": 0.45, "failed": 0.0, "unknown": 0.5}


def normalize_health(source_id, health=None):
    health = dict(health or {})
    status = health.get("source_health", health.get("status", "unknown"))
    if status not in HEALTH_MULTIPLIER:
        status = "unknown"
    return {
        "source_id": source_id,
        "source_health": status,
        "last_success_at": health.get("last_success_at"),
        "last_failure_at": health.get("last_failure_at"),
        "latency_ms": health.get("latency_ms"),
        "schema_version": health.get("schema_version"),
        "provider_status": health.get("provider_status", "unknown"),
        "license_expiry": health.get("license_expiry"),
        "health_multiplier": HEALTH_MULTIPLIER[status],
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def route_health_score(profile):
    """Return a bounded multiplier; absence of telemetry never beats authority."""
    status = profile.get("source_health", profile.get("health", "unknown"))
    return HEALTH_MULTIPLIER.get(status, HEALTH_MULTIPLIER["unknown"])
