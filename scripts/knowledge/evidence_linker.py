"""Bind explanatory language to saved artifacts and result-lineage fields."""
from __future__ import annotations

from typing import Any


def _metrics(data: dict[str, Any]) -> list[dict[str, Any]]:
    lineage = data.get("result_lineage") if isinstance(data.get("result_lineage"), dict) else {}
    values = lineage.get("metrics", [])
    return [item for item in values if isinstance(item, dict)]


def source_ids(data: dict[str, Any]) -> list[str]:
    found = []
    for item in data.get("sources", []) if isinstance(data.get("sources"), list) else []:
        if isinstance(item, dict) and item.get("id") is not None:
            found.append(str(item["id"]))
    for item in data.get("online_status", {}).get("source_ids", []) if isinstance(data.get("online_status"), dict) else []:
        found.append(str(item))
    return sorted(set(found))


def link(data: dict[str, Any], *, artifact: str, pointer: str | None = None, metric_ids: list[str] | None = None) -> dict[str, Any]:
    metrics = _metrics(data)
    wanted = set(metric_ids or [])
    matched = [item for item in metrics if not wanted or item.get("metric_id") in wanted]
    if not matched and metric_ids:
        matched = [item for item in metrics if item.get("metric_id") in wanted]
    calculation_ids = [str(item["calculation_id"]) for item in matched if item.get("calculation_id")]
    input_hash = next((item.get("input_hash") for item in matched if item.get("input_hash")), None)
    refs = [artifact + (pointer or "")]
    return {"evidence_refs": refs, "calculation_refs": calculation_ids, "calculation_id": calculation_ids[0] if calculation_ids else None, "source_ids": source_ids(data), "input_hash": input_hash, "matched_metrics": matched}


def claim_context(data: dict[str, Any], refs: list[str], artifact: str) -> dict[str, Any]:
    return link(data, artifact=artifact, pointer="", metric_ids=refs)
