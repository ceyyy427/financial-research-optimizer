"""Stable, redacted read-only view models for the local research UI."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from .contracts import ReportManifest, ResearchRunState
from .reports import redact_public_payload

_ANALYST_ROLES = ("fundamentals", "technical", "sentiment", "news", "learning")
_SECTIONS = frozenset(("complete", "2_evidence", "3_research", "4_quant", "5_risk", "6_paper_decision"))


def _scrub(value: Any) -> Any:
    return redact_public_payload(value)


def research_report_url(run_id: str, section: str) -> str:
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]+", run_id):
        raise ValueError("run_id is invalid")
    if section not in _SECTIONS:
        raise ValueError("report section is not allow-listed")
    return f"/research/{run_id}/report/{section}"


def research_view_model(run_state: ResearchRunState, manifest: ReportManifest | Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(run_state, ResearchRunState):
        raise TypeError("run_state must be ResearchRunState")
    manifest_payload = _manifest_payload(manifest)
    if manifest_payload.get("run_id") != run_state.run_id:
        raise ValueError("manifest run_id does not match run state")
    if manifest_payload.get("schema_version") != "research-report.v1":
        raise ValueError("manifest schema is incompatible")
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
    snapshot = manifest_payload.get("source_snapshot", {}) if isinstance(manifest_payload, Mapping) else {}
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    role_status = snapshot.get("role_status")
    if not isinstance(role_status, Mapping):
        role_status = {role: (reports[role].status if role in reports else "UNAVAILABLE") for role in _ANALYST_ROLES}
    stage_status = snapshot.get("stage_status")
    if not isinstance(stage_status, Mapping):
        stage_status = _stage_status(run_state)
    missing_evidence = snapshot.get("missing_evidence")
    if not isinstance(missing_evidence, (list, tuple)):
        missing_evidence = [f"{role}:evidence" for role, report in sorted(reports.items()) if not report.evidence_refs]
    checkpoint_status = snapshot.get("checkpoint_status", {"state": "NOT_ATTACHED"})
    if not isinstance(checkpoint_status, Mapping):
        checkpoint_status = {"state": str(checkpoint_status)}
    factor_proposals = snapshot.get("factor_proposals", [])
    if not isinstance(factor_proposals, (list, tuple)):
        factor_proposals = []
    provider_readiness = snapshot.get("provider_readiness", {"status": "UNKNOWN"})
    if not isinstance(provider_readiness, Mapping):
        provider_readiness = {"status": str(provider_readiness)}
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
            "role_status": dict(sorted((str(key), str(value)) for key, value in role_status.items())),
            "stage_status": dict(sorted((str(key), str(value)) for key, value in stage_status.items())),
            "missing_evidence": sorted(str(item) for item in missing_evidence),
            "checkpoint_status": dict(checkpoint_status),
            "factor_proposals": list(factor_proposals),
            "provider_readiness": dict(provider_readiness),
            "report_tree": {
                "analysts": {role: f"1_analysts/{role}.html" for role in _ANALYST_ROLES},
                "stages": {section: f"{section}/index.html" for section in ("2_evidence", "3_research", "4_quant", "5_risk", "6_paper_decision")},
                "complete": "complete_report.html",
            },
            "report_links": report_links,
            "limitations": sorted({limitation for report in reports.values() for limitation in report.limitations}),
        }
    )


def _manifest_payload(value: ReportManifest | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, ReportManifest):
        return {
            "run_id": value.run_id,
            "schema_version": value.schema_version,
            "files": dict(value.files),
            "source_snapshot": _coerce_public(value.source_snapshot),
            "created_at": _coerce_public(value.created_at),
        }
    if not isinstance(value, Mapping):
        raise TypeError("manifest must be ReportManifest or mapping")
    return _coerce_public(dict(value))


def _coerce_public(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _coerce_public(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _coerce_public(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce_public(item) for item in value]
    return str(value)


def _stage_status(run_state: ResearchRunState) -> dict[str, str]:
    stages = (
        ("analysts", "ANALYSTS_READY"),
        ("evidence", "EVIDENCE_REVIEW"),
        ("research", "RESEARCH_PLAN_READY"),
        ("quant", "QUANT_VALIDATION"),
        ("risk", "RISK_REVIEW"),
        ("paper_decision", "PAPER_DECISION_READY"),
        ("publication", "REPORT_PUBLISHED"),
        ("learning", "LEARNING_RECORDED"),
    )
    history = {item.value for item in run_state.state_history}
    terminal = run_state.current_state.value
    return {
        name: (
            "COMPLETE" if state_name in history else
            "CURRENT" if state_name == terminal else
            "CANCELLED" if terminal == "CANCELLED" else
            "BLOCKED" if terminal in {"FAILED", "VALIDATION_FAILED", "PROVIDER_NOT_CONFIGURED"} else
            "PENDING"
        )
        for name, state_name in stages
    }


def render_status_wall_html(model: Mapping[str, Any], *, title: str = "Finathink research status") -> str:
    """Render a read-only, no-JS status wall from a server-owned view model."""

    safe = _scrub(dict(model))
    esc = lambda value: html.escape(str(value if value is not None else "—"), quote=True)
    role_status = safe.get("role_status", {}) if isinstance(safe, Mapping) else {}
    stage_status = safe.get("stage_status", {}) if isinstance(safe, Mapping) else {}
    missing = safe.get("missing_evidence", []) if isinstance(safe, Mapping) else []
    role_cards = "".join(
        f'<li data-role="{esc(role)}"><strong>{esc(role)}</strong><span>{esc(status)}</span></li>'
        for role, status in sorted(role_status.items())
    ) or "<li>No analyst status recorded.</li>"
    stage_rows = "".join(
        f'<tr><th scope="row">{esc(stage)}</th><td>{esc(status)}</td></tr>'
        for stage, status in sorted(stage_status.items())
    ) or '<tr><td colspan="2">No stage status recorded.</td></tr>'
    limitation_rows = "".join(f"<li>{esc(item)}</li>" for item in missing) or "<li>None recorded.</li>"
    safe_title = _scrub(title)
    run_id = esc(safe.get("run_id"))
    state = esc(safe.get("state"))
    payload_json = html.escape(json.dumps(safe, ensure_ascii=False, sort_keys=True), quote=True)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Read-only multi-agent research status wall"><title>{esc(safe_title)} · {run_id}</title><style>body{{font:16px/1.5 system-ui,sans-serif;max-width:980px;margin:0 auto;padding:2rem;color:#173137}}h1{{margin-bottom:.25rem}}.meta{{color:#617174}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.7rem;padding:0;list-style:none}}.grid li{{border:1px solid #c9c2b5;padding:.8rem;display:flex;justify-content:space-between;gap:.5rem}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}th,td{{text-align:left;border-bottom:1px solid #c9c2b5;padding:.6rem}}code,pre{{overflow:auto}}.note{{border-left:3px solid #c36e48;padding-left:1rem}}</style></head><body><main><h1>{esc(safe_title)}</h1><p class="meta">Run {run_id} · State {state} · PAPER-ONLY · READ-ONLY</p><section aria-labelledby="roles"><h2 id="roles">Analyst roles</h2><ul class="grid">{role_cards}</ul></section><section aria-labelledby="stages"><h2 id="stages">Stage wall</h2><table><thead><tr><th>Stage</th><th>Status</th></tr></thead><tbody>{stage_rows}</tbody></table></section><section class="note" aria-labelledby="evidence"><h2 id="evidence">Missing evidence</h2><ul>{limitation_rows}</ul></section><noscript><p>This report is fully readable without JavaScript. Values are server-provided; no financial indicators are calculated in the browser.</p></noscript><details><summary>Server payload (redacted)</summary><pre>{payload_json}</pre></details></main></body></html>'''
