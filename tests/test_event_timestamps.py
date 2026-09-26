from events.normalize_events import audit_event_timestamps, normalize_event


def test_event_first_visible_time_is_point_in_time_safe():
    event = normalize_event({"event_type": "macro_release", "headline": "CPI", "occurred_at": "2026-09-25T08:00:00Z", "published_at": "2026-09-25T09:00:00Z", "retrieved_at": "2026-09-25T09:01:00Z"}, "fred", forecast_origin="2026-09-25T09:30:00Z")
    assert event["point_in_time_safe"] is True
    assert audit_event_timestamps([event])["safe"] is True


def test_event_published_after_forecast_origin_is_blocked():
    event = normalize_event({"event_type": "filing", "occurred_at": "2026-09-25T08:00:00Z", "published_at": "2026-09-25T10:00:00Z", "retrieved_at": "2026-09-25T10:01:00Z"}, "sec", forecast_origin="2026-09-25T09:30:00Z")
    assert event["point_in_time_safe"] is False
    assert audit_event_timestamps([event])["safe"] is False
