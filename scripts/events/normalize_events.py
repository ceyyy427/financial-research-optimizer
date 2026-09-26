"""Normalize event timestamps before event features can enter a model."""
import hashlib
import json
from datetime import datetime, timezone


def _dt(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def normalize_event(raw, source_id, forecast_origin=None, reliability=0.5, impact_hours=24):
    occurred = _dt(raw.get("occurred_at") or raw.get("event_time"))
    published = _dt(raw.get("published_at") or raw.get("release_date"))
    retrieved = _dt(raw.get("retrieved_at")) or datetime.now(timezone.utc)
    first_visible = _dt(raw.get("first_visible_at")) or published or retrieved
    if not occurred or not published:
        raise ValueError("event requires occurred_at and published_at")
    start = _dt(raw.get("impact_start")) or first_visible
    end = _dt(raw.get("impact_end"))
    if end is None:
        from datetime import timedelta
        end = start + timedelta(hours=impact_hours)
    signature = json.dumps({"source_id": source_id, "event_type": raw.get("event_type"), "headline": raw.get("headline"), "published_at": published.isoformat()}, sort_keys=True)
    event_id = raw.get("event_id") or hashlib.sha256(signature.encode()).hexdigest()[:20]
    origin = _dt(forecast_origin) if forecast_origin else None
    safe = published <= first_visible <= retrieved and (origin is None or first_visible <= origin)
    return {
        "event_id": event_id,
        "event_type": raw.get("event_type", "unknown"),
        "headline": raw.get("headline", ""),
        "occurred_at": occurred.isoformat(),
        "published_at": published.isoformat(),
        "retrieved_at": retrieved.isoformat(),
        "first_visible_at": first_visible.isoformat(),
        "impact_window": {"start": start.isoformat(), "end": end.isoformat()},
        "source_id": source_id,
        "source_reliability": float(reliability),
        "revision_of": raw.get("revision_of"),
        "duplicate_group": hashlib.sha256(signature.encode()).hexdigest()[:16],
        "point_in_time_safe": safe,
    }


def audit_event_timestamps(events):
    seen = {}
    errors = []
    for event in events:
        if not event.get("point_in_time_safe"):
            errors.append(f"event {event.get('event_id')} is not point-in-time safe")
        group = event.get("duplicate_group")
        if group:
            seen.setdefault(group, []).append(event.get("event_id"))
    duplicates = {group: ids for group, ids in seen.items() if len(ids) > 1}
    return {"safe": not errors, "errors": errors, "duplicate_groups": duplicates, "event_count": len(events)}
