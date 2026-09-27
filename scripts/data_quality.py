"""Reusable, data-first quality and grain checks.

The research engine treats quality as a decision, not as a single descriptive
number.  These helpers are intentionally deterministic so that the resulting
quality score can be recomputed from the same snapshot.
"""
from __future__ import annotations

from typing import Iterable


def _candidate(columns: Iterable[str], names: Iterable[str]):
    columns = set(columns)
    return next((name for name in names if name in columns), None)


def audit_grain(frame, grain_fields=None):
    """Audit the declared/inferred observation grain.

    The preferred grain is instrument × timestamp × field × vintage.  A CSV
    may not contain all four keys, so the function infers the available
    subset and reports which dimensions were absent instead of silently
    assuming that a date-only grain is safe.
    """
    columns = list(frame.columns)
    instrument = _candidate(columns, ("instrument_id", "ticker", "symbol", "asset"))
    timestamp = _candidate(columns, ("observation_time", "date", "timestamp", "observation_date"))
    field = _candidate(columns, ("field", "field_name", "series_id", "concept", "metric"))
    vintage = _candidate(columns, ("vintage_date", "vintage_time", "release_date", "availability_date"))
    inferred = [value for value in (instrument, timestamp, field, vintage) if value]
    keys = list(grain_fields or inferred)
    missing_keys = [value for value in ("instrument", "timestamp", "field", "vintage")
                    if {"instrument": instrument, "timestamp": timestamp, "field": field, "vintage": vintage}[value] is None]
    if not keys:
        duplicate_rows = 0
    else:
        duplicate_rows = int(frame.duplicated(subset=keys, keep=False).sum())
    mixed_vintages = 0
    if instrument and timestamp and vintage:
        mixed_vintages = int((frame.groupby([instrument, timestamp], dropna=False)[vintage]
                              .nunique(dropna=False) > 1).sum())
    mixed_units = 0
    unit = _candidate(columns, ("unit", "units"))
    if instrument and field and unit:
        mixed_units = int((frame.groupby([instrument, field], dropna=False)[unit]
                           .nunique(dropna=False) > 1).sum())
    return {
        "declared_grain": list(grain_fields or []),
        "inferred_grain": keys,
        "missing_grain_dimensions": missing_keys,
        "duplicate_grain_rows": duplicate_rows,
        "mixed_vintage_groups": mixed_vintages,
        "mixed_unit_groups": mixed_units,
        "grain_pass": duplicate_rows == 0 and mixed_units == 0,
    }


def quality_score(report, source_reliability_score=None):
    """Return component scores and a conservative usability decision."""
    rows = max(int(report.get("rows", 0)), 1)
    columns = max(len(report.get("columns", [])), 1)
    missing = sum(int(value) for value in report.get("missing_by_column", {}).values())
    completeness = max(0.0, 1.0 - missing / (rows * columns))
    invalid_dates = int(report.get("invalid_dates", 0))
    duplicate_dates = int(report.get("duplicate_dates", 0))
    grain = report.get("grain", {})
    freshness = 1.0 if report.get("date_end") else 0.0
    pit = 1.0 if not sum(report.get("point_in_time_invalid_dates", {}).values()) else 0.0
    if report.get("cutoff_pass") is False:
        pit = 0.0
    # Repeated timestamps across instruments are expected in panel data; the
    # grain audit, not a date-only duplicate count, decides whether they are a
    # true duplicate observation.
    date_score = 0.0 if invalid_dates else (0.8 if duplicate_dates and not grain.get("grain_pass", True) else 1.0)
    grain_score = 1.0 if grain.get("grain_pass", True) else 0.0
    # An unbound CSV has unknown source reliability; unknown is deliberately
    # scored as neutral rather than silently treated as authoritative.
    if source_reliability_score is None:
        source_reliability_score = report.get("source_reliability_score", 0.5)
    source_score = max(0.0, min(1.0, float(source_reliability_score)))
    components = {
        "quality_score": round((completeness + freshness + pit + source_score + date_score + grain_score) / 6, 6),
        "freshness_score": round(freshness, 6),
        "completeness_score": round(completeness, 6),
        "point_in_time_score": round(pit, 6),
        "source_reliability_score": round(source_score, 6),
        "date_integrity_score": round(date_score, 6),
        "grain_score": round(grain_score, 6),
    }
    hard_block = bool(int(report.get("rows", 0)) == 0 or invalid_dates or not grain.get("grain_pass", True) or pit == 0.0 or report.get("schema_drift", {}).get("schema_drift_detected", False))
    if hard_block:
        decision = "blocked"
    elif components["quality_score"] < 0.85:
        decision = "degraded"
    elif components["quality_score"] < 0.98:
        decision = "usable_with_warning"
    else:
        decision = "usable"
    components["decision"] = decision
    return components


def compare_schema(reference, current):
    """Compare two ``{field: type/unit}`` dictionaries."""
    reference = reference or {}
    current = current or {}
    new_fields = sorted(set(current) - set(reference))
    missing_fields = sorted(set(reference) - set(current))
    changed_types = sorted(field for field in set(reference) & set(current)
                           if reference[field].get("type") != current[field].get("type"))
    changed_units = sorted(field for field in set(reference) & set(current)
                           if reference[field].get("unit") != current[field].get("unit"))
    return {
        "schema_drift_detected": bool(new_fields or missing_fields or changed_types or changed_units),
        "new_fields": new_fields,
        "missing_fields": missing_fields,
        "changed_types": changed_types,
        "changed_units": changed_units,
    }
