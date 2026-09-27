"""Parser for normalized exchange CSV/JSON rows."""


def parse_exchange_file(payload, source_url=None):
    rows = payload.get("data", payload.get("records", [])) if isinstance(payload, dict) else payload
    output = []
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        observation = item.get("observation_time") or item.get("date") or item.get("trade_date")
        if not observation:
            continue
        for field in ("close", "volume"):
            if item.get(field) is None:
                continue
            output.append({
                "instrument_id": str(item.get("instrument_id") or item.get("code") or "unknown"),
                "field": field,
                "value": item[field],
                "unit": item.get("currency", "shares" if field == "volume" else "unknown"),
                "observation_time": observation,
                "release_time": item.get("release_time"),
                "availability_time": item.get("availability_time") or item.get("release_time") or observation,
                "effective_time": item.get("effective_time") or observation,
                "vintage_time": item.get("vintage_time"),
                "source_url": source_url,
                "adjustment": item.get("adjustment", "unadjusted"),
                "point_in_time_status": "pass" if item.get("availability_time") or item.get("release_time") else "not_available",
            })
    return output
