"""Flatten SEC Company Facts units into filing-time observations."""


def parse_sec_xbrl(payload, instrument_id=None, source_url=None):
    facts = payload.get("facts", {}) if isinstance(payload, dict) else {}
    output = []
    for taxonomy, concepts in facts.items():
        for concept, definition in (concepts or {}).items():
            for unit, values in (definition.get("units", {}) or {}).items():
                for item in values or []:
                    if not isinstance(item, dict) or item.get("val") is None or not item.get("filed"):
                        continue
                    filed = item["filed"]
                    output.append({
                        "instrument_id": str(instrument_id or payload.get("cik") or "unknown"),
                        "field": f"{taxonomy}:{concept}",
                        "value": item["val"],
                        "unit": unit,
                        "observation_time": item.get("end") or item.get("start") or filed,
                        "release_time": filed,
                        "availability_time": item.get("accepted_datetime") or filed,
                        "effective_time": item.get("end") or filed,
                        "vintage_time": filed,
                        "source_url": source_url,
                        "adjustment": "filing_reported",
                        "point_in_time_status": "pass",
                        "revision_status": "filing_date_aware",
                    })
    return output
