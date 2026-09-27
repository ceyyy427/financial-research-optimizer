"""MCP resource URI parsing and safe artifact reads."""

from __future__ import annotations

import json
import re
from typing import Any

from financial_research.run_store import RunStore, RunStoreError


RESOURCE_RE = re.compile(r"^research://runs/(?P<run_id>run_[A-Za-z0-9][A-Za-z0-9_.-]{2,127})/(?P<artifact>[A-Za-z0-9_.-]+)$")


def parse_resource_uri(uri: str) -> tuple[str, str]:
    match = RESOURCE_RE.fullmatch(uri)
    if not match:
        raise RunStoreError("resource URI must be research://runs/{run_id}/{artifact}")
    return match.group("run_id"), match.group("artifact")


def read_research_artifact(store: RunStore, run_id: str, artifact: str) -> dict[str, Any]:
    return store.artifact(run_id, artifact, include_content=True)


def read_resource_uri(store: RunStore, uri: str) -> str:
    run_id, artifact = parse_resource_uri(uri)
    return json.dumps(read_research_artifact(store, run_id, artifact), ensure_ascii=False, indent=2)
