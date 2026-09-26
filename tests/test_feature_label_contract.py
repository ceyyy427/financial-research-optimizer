import pandas as pd

from feature_label_audit import audit_availability, audit_label_split


def test_future_feature_availability_is_blocked():
    frame = pd.DataFrame({"availability_time": ["2026-01-08T10:00:00Z", "2026-01-10T10:00:00Z"]})
    result = audit_availability(frame, "availability_time", "2026-01-09T00:00:00Z")
    assert result["future_rows"] == 1
    assert result["point_in_time_safe"] is False


def test_label_overlap_requires_purge_and_embargo():
    train = pd.DataFrame({"label_start": ["2026-01-01"], "label_end": ["2026-01-20"]})
    evaluation = pd.DataFrame({"label_start": ["2026-01-22"], "label_end": ["2026-02-10"]})
    assert audit_label_split(train, evaluation, purge_period=0, embargo_period=0)["safe"] is True
    assert audit_label_split(train, evaluation, purge_period=3, embargo_period=0)["safe"] is False
