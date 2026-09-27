"""Small offline SDMX CSV/JSON normalizer used by ECB and BIS adapters."""
import csv
import io


def _rows(payload):
    if isinstance(payload, str):
        return [dict(row) for row in csv.DictReader(io.StringIO(payload))]
    if isinstance(payload, dict):
        for key in ("data", "observations", "records", "values"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        data = payload.get("data", {})
        if isinstance(data, dict) and isinstance(data.get("dataSets"), list):
            rows = []
            for dataset in data["dataSets"]:
                for series in (dataset.get("series", {}) or {}).values():
                    for index, observation in (series.get("observations", {}) or {}).items():
                        rows.append({"TIME_PERIOD": index, "OBS_VALUE": observation[0] if isinstance(observation, list) else observation})
            return rows
    return []


def parse_sdmx(payload, instrument_id=None, source_url=None):
    output = []
    for item in _rows(payload):
        if not isinstance(item, dict):
            continue
        observation = item.get("TIME_PERIOD") or item.get("time_period") or item.get("date") or item.get("observation_date")
        value = item.get("OBS_VALUE") if item.get("OBS_VALUE") is not None else item.get("value")
        if observation in (None, "") or value in (None, ""):
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        declared_availability = item.get("AVAILABILITY_DATE") or item.get("availability_date") or item.get("RELEASE_DATE") or item.get("release_date")
        availability = declared_availability or observation
        output.append({
            "instrument_id": str(instrument_id or item.get("series_id") or item.get("SERIES_KEY") or "unknown"),
            "field": "value", "value": value,
            "unit": str(item.get("UNIT_MEASURE") or item.get("unit") or "unknown"),
            "frequency": item.get("FREQ") or item.get("frequency"),
            "observation_time": str(observation), "release_time": item.get("RELEASE_DATE") or item.get("release_date"),
            "availability_time": str(availability), "effective_time": str(observation),
            "vintage_time": item.get("VINTAGE_DATE") or item.get("vintage_date"),
            "source_url": source_url, "adjustment": str(item.get("ADJUSTMENT") or item.get("adjustment") or "not_stated"),
            "point_in_time_status": "pass" if declared_availability else "not_available",
        })
    return output
