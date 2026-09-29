"""Tolerant parser for official National Data JSON/record payloads."""

import re


def _observation_date(value):
    text = str(value)
    match = re.fullmatch(r"(\d{4})(\d{2})MM", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-01"
    match = re.fullmatch(r"(\d{4})YY", text)
    if match:
        return f"{match.group(1)}-01-01"
    return text


def parse_stats_gov_json(payload, instrument_id=None, source_url=None):
    rows = payload.get("data", payload.get("records", payload.get("observations", []))) if isinstance(payload, dict) else payload
    if isinstance(rows, dict) and isinstance(rows.get("data"), list):
        rows = rows["data"]
    # NBS v2 stream/esData returns period objects containing indicator values.
    if rows and isinstance(rows[0], dict) and isinstance(rows[0].get("values"), list):
        expanded = []
        for period in rows:
            for value in period.get("values", []):
                expanded.append({"date": period.get("code") or period.get("name"), **value})
        rows = expanded
    if isinstance(rows, dict):
        rows = rows.get("data", [])
    output = []
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        observation = item.get("observation_date") or item.get("date") or item.get("time") or item.get("period")
        observation = _observation_date(observation) if observation is not None else observation
        value = item.get("value") if item.get("value") is not None else item.get("data")
        if observation is None or value is None:
            continue
        output.append({
            "instrument_id": str(item.get("series_id") or item.get("indicator") or instrument_id or "unknown"),
            "field": str(item.get("field") or item.get("indicator") or "value"),
            "value": value,
            "unit": str(item.get("unit") or item.get("du_name") or "unknown"),
            "observation_time": str(observation),
            "release_time": item.get("release_date") or item.get("release_time"),
            "availability_time": item.get("availability_date") or item.get("availability_time") or item.get("release_date") or item.get("release_time") or observation,
            "effective_time": item.get("effective_time") or observation,
            "vintage_time": item.get("vintage_date") or item.get("vintage_time"),
            "source_url": source_url,
            "adjustment": str(item.get("adjustment") or "not_stated"),
            "point_in_time_status": "pass" if item.get("release_date") or item.get("availability_date") else "not_available",
        })
    return output
