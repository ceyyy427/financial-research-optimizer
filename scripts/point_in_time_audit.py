#!/usr/bin/env python3
"""Point-in-time leakage checks for tabular financial data."""
import pandas as pd


def audit_point_in_time(frame, forecast_origin):
    origin = pd.Timestamp(forecast_origin, tz="UTC")
    result = {"future_release_rows": 0, "future_availability_rows": 0, "future_vintage_rows": 0, "invalid_effective_rows": 0, "point_in_time_safe": True}
    mapping = {
        "release_date": "future_release_rows",
        "availability_date": "future_availability_rows",
        "vintage_date": "future_vintage_rows",
        "effective_timestamp": "invalid_effective_rows",
    }
    for column, key in mapping.items():
        if column not in frame.columns:
            continue
        parsed = pd.to_datetime(frame[column], errors="coerce", utc=True)
        count = int((parsed > origin).sum())
        result[key] = count
    result["point_in_time_safe"] = not any(result[key] for key in ("future_release_rows", "future_availability_rows", "future_vintage_rows", "invalid_effective_rows"))
    return result
