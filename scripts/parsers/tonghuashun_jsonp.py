"""Parser for Tonghuashun daily line JSONP responses."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone


JSONP_RE = re.compile(r"^\s*([A-Za-z_$][\w$]*)\((.*)\)\s*$", re.DOTALL)


def _availability(value):
    if value:
        return str(value).replace("Z", "+00:00")
    return datetime.now(timezone.utc).isoformat()


def parse_tonghuashun_jsonp(payload, instrument_id=None, source_url=None, availability_time=None, market="SZ"):
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    if not isinstance(payload, str):
        raise ValueError("Tonghuashun JSONP payload must be text")
    match = JSONP_RE.match(payload)
    if not match:
        raise ValueError("invalid Tonghuashun JSONP envelope")
    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid Tonghuashun JSONP body") from exc
    if not isinstance(data, dict) or not isinstance(data.get("data"), str):
        raise ValueError("Tonghuashun JSONP missing data string")
    instrument_id = str(instrument_id or data.get("code") or "unknown")
    available = _availability(availability_time)
    records = []
    for raw in data["data"].split(";"):
        fields = raw.split(",")
        if len(fields) < 7 or not fields[0].strip():
            continue
        date, opening, high, low, close, volume, amount = fields[:7]
        try:
            close_value = float(close)
            volume_value = float(volume)
        except ValueError as exc:
            raise ValueError(f"invalid Tonghuashun numeric row: {raw}") from exc
        observation_time = f"{date}T15:00:00+08:00"
        records.append({
            "instrument_id": instrument_id,
            "field": "close",
            "value": close_value,
            "open": float(opening),
            "high": float(high),
            "low": float(low),
            "volume": volume_value,
            "amount": float(amount or 0),
            "unit": "CNY",
            "currency": "CNY",
            "observation_time": observation_time,
            "release_time": None,
            "availability_time": available,
            "effective_time": observation_time,
            "vintage_time": None,
            "adjustment": "unadjusted",
            "source_url": source_url,
            "access_method": "browser",
            "point_in_time_status": "not_available",
            "revision_status": "latest_only",
            "market": market,
            "parser_version": "tonghuashun_jsonp_v1",
        })
    if not records:
        raise ValueError("Tonghuashun JSONP contained no observations")
    return records
