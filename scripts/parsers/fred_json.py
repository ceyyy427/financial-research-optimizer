"""Parser for FRED/ALFRED observations."""


def parse_fred_json(payload, instrument_id=None, source_url=None, availability_time=None, vintage_time=None):
    observations = payload.get("observations", []) if isinstance(payload, dict) else []
    output = []
    for item in observations:
        if not isinstance(item, dict) or item.get("value") in {None, "."}:
            continue
        observation = item.get("date") or item.get("observation_date")
        output.append({
            "instrument_id": str(instrument_id or payload.get("series_id") or "unknown"),
            "field": "value",
            "value": float(item["value"]),
            "unit": str(item.get("unit") or "unknown"),
            "observation_time": observation,
            "release_time": item.get("release_date"),
            "availability_time": availability_time or item.get("availability_date") or item.get("realtime_start") or observation,
            "effective_time": observation,
            "vintage_time": vintage_time or item.get("vintage_date") or item.get("realtime_start"),
            "source_url": source_url,
            "adjustment": str(item.get("seasonal_adjustment") or "not_stated"),
            "point_in_time_status": "pass" if availability_time or item.get("realtime_start") else "not_available",
        })
    return output
