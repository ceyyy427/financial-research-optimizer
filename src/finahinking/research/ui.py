"""Stable, redacted read-only view models for the local research UI."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .contracts import ReportManifest, ResearchRunState, to_jsonable

_ANALYST_ROLES = ("fundamentals", "technical", "sentiment", "news", "learning")
_SECTIONS = frozenset(("complete", "2_evidence", "3_research", "4_quant", "5_risk", "6_paper_decision"))
_SECRET = re.compile(r"(?i)(?:api[_-]?key|token|secret|password|endpoint)\s*[=:]\s*[^\s<]+")
_PATH = re.compile(r"(?:/Users/[^\s<]+|/home/[^\s<]+|[A-Za-z]:[\\/][^\s<]+)")


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return _PATH.sub("[PATH_REDACTED]", _SECRET.sub("[REDACTED]", value))
    if isinstance(value, Mapping):
        return {str(key): _scrub(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(item) for item in value]
    return value


def research_report_url(run_id: str, section: str) -> str:
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]+", run_id):
        raise ValueError("run_id is invalid")
    if section not in _SECTIONS:
        raise ValueError("report section is not allow-listed")
    return f"/research/{run_id}/report/{section}"


def research_view_model(run_state: ResearchRunState, manifest: ReportManifest | Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(run_state, ResearchRunState):
        raise TypeError("run_state must be ResearchRunState")
    manifest_payload = to_jsonable(manifest)
    reports = {report.role: report for report in run_state.analyst_reports}
    analysts = [
        {
            "role": role,
            "status": reports[role].status if role in reports else "UNAVAILABLE",
            "evidence_count": len(reports[role].evidence_refs) if role in reports else 0,
            "limitations": list(reports[role].limitations) if role in reports else ["no report returned"],
        }
        for role in sorted(reports)
    ]
    missing = sorted(set(_ANALYST_ROLES) - set(reports))
    as_of = run_state.as_of.isoformat() if run_state.as_of is not None else manifest_payload.get("source_snapshot", {}).get("as_of")
    files = manifest_payload.get("files", {}) if isinstance(manifest_payload, Mapping) else {}
    report_links = {section: research_report_url(run_state.run_id, section) for section in sorted(_SECTIONS) if (section == "complete" and "complete_report.html" in files) or section in files or f"{section}/index.html" in files}
    return _scrub(
        {
            "schema_version": 1,
            "run_id": run_state.run_id,
            "state": run_state.current_state.value,
            "state_history": [item.value for item in run_state.state_history],
            "as_of": as_of,
            "mode": "OFFLINE",
            "paper_only": True,
            "decision_eligible": run_state.decision_eligible,
            "failure_kind": run_state.failure_kind.value if run_state.failure_kind else None,
            "failure_message": run_state.failure_message,
            "analysts": analysts,
            "missing_analysts": missing,
            "report_links": report_links,
            "limitations": sorted({limitation for report in reports.values() for limitation in report.limitations}),
        }
    )

