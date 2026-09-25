import pandas as pd

from point_in_time_audit import audit_point_in_time


def test_point_in_time_safe_fixture(FIXTURE):
    frame = pd.read_csv(FIXTURE)
    result = audit_point_in_time(frame, "2026-01-09")
    assert result["point_in_time_safe"] is True


def test_future_release_is_detected():
    frame = pd.DataFrame({"release_date": ["2026-01-09"], "availability_date": ["2026-01-09"], "vintage_date": ["2026-01-09"], "effective_timestamp": ["2026-01-09T00:00:00Z"]})
    result = audit_point_in_time(frame, "2026-01-08")
    assert result["point_in_time_safe"] is False
    assert result["future_release_rows"] == 1
