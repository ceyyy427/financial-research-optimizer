"""Escaped, content-addressed HTML report bundles for research runs."""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import ReportManifest, ResearchRunResult, RunEvent, stable_digest, to_jsonable

_SECRET_TEXT = re.compile(r"(?i)(?:api[_-]?key|token|secret|password|endpoint)\s*[=:]\s*[^\s<]+")
_ABSOLUTE_PATH = re.compile(r"(?:/Users/[^\s<]+|/home/[^\s<]+|[A-Za-z]:[\\/][^\s<]+)")
_HTML_HANDLER = re.compile(r"(?i)\bon[a-z]+\s*=")
_REQUIRED_ANALYSTS = ("fundamentals", "technical", "sentiment", "news", "learning")
_REQUIRED_SECTIONS = ("2_evidence", "3_research", "4_quant", "5_risk", "6_paper_decision")


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        value = _SECRET_TEXT.sub("[REDACTED]", value)
        value = _ABSOLUTE_PATH.sub("[PATH_REDACTED]", value)
        return _HTML_HANDLER.sub("[ATTR_REDACTED]=", value)
    if is_dataclass(value):
        return _scrub(to_jsonable(value))
    if isinstance(value, Mapping):
        return {str(key): _scrub(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_scrub(item) for item in value]
    return value


def render_section_html(
    title: str,
    payload: Mapping[str, Any] | Any,
    evidence_refs: Sequence[str] = (),
    limitations: Sequence[str] = (),
) -> str:
    safe_title = html.escape(_scrub(str(title)), quote=True)
    safe_payload = html.escape(
        json.dumps(_scrub(payload), ensure_ascii=False, sort_keys=True, indent=2, default=str),
        quote=False,
    )
    evidence_html = "".join(f"<li>{html.escape(_scrub(str(ref)), quote=True)}</li>" for ref in evidence_refs)
    limitations_html = "".join(f"<li>{html.escape(_scrub(str(item)), quote=True)}</li>" for item in limitations)
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{safe_title}</title></head><body><main>"
        f"<h1>{safe_title}</h1><h2>Findings</h2><pre>{safe_payload}</pre>"
        f"<h2>Evidence</h2><ul>{evidence_html or '<li>None recorded</li>'}</ul>"
        f"<h2>Limitations</h2><ul>{limitations_html or '<li>None recorded</li>'}</ul>"
        "</main></body></html>"
    )


@dataclass(frozen=True, slots=True)
class BundleVerification:
    ok: bool
    errors: tuple[str, ...] = ()


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(manifest: ReportManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(to_jsonable(manifest), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def append_event(event: RunEvent, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(to_jsonable(event), ensure_ascii=False, sort_keys=True) + "\n")


class ReportBundleWriter:
    def write(self, result: ResearchRunResult, output_root: str | Path) -> ReportManifest:
        bundle = Path(output_root) / result.state.run_id
        bundle.mkdir(parents=True, exist_ok=True)
        analyst_by_role = {report.role: report for report in result.state.analyst_reports}

        complete_sections: list[str] = []
        for role in _REQUIRED_ANALYSTS:
            report = analyst_by_role.get(role)
            if report is None:
                html_text = render_section_html(
                    role,
                    {"status": "UNAVAILABLE", "role": role},
                    limitations=("optional or unconfigured analyst did not return a report",),
                )
            else:
                html_text = render_section_html(
                    role,
                    {"status": report.status, "claims": report.claims, "model_ref": report.model_ref},
                    report.evidence_refs,
                    report.limitations,
                )
            path = bundle / "1_analysts" / f"{role}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html_text, encoding="utf-8")
            complete_sections.append(html_text)

        section_payload = {
            "state": result.state.current_state.value,
            "state_history": result.state.state_history,
            "decision_eligible": result.state.decision_eligible,
            "decision": result.decision,
        }
        for section in _REQUIRED_SECTIONS:
            path = bundle / section / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                render_section_html(section, section_payload, result.decision.evidence_refs if result.decision else (), result.decision.limitations if result.decision else ()),
                encoding="utf-8",
            )

        complete_path = bundle / "complete_report.html"
        complete_path.write_text(
            render_section_html(
                "Finathink research report",
                {"run_id": result.state.run_id, "state": result.state.current_state, "decision": result.decision, "reports": result.state.analyst_reports},
                result.decision.evidence_refs if result.decision else (),
                result.decision.limitations if result.decision else (),
            ),
            encoding="utf-8",
        )
        activity_path = bundle / "activity.jsonl"
        if activity_path.exists():
            activity_path.unlink()
        for event in result.events:
            append_event(event, activity_path)

        files: dict[str, str] = {}
        for path in sorted(bundle.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                files[str(path.relative_to(bundle))] = _digest_file(path)
        manifest = ReportManifest(
            run_id=result.state.run_id,
            schema_version="research-report.v1",
            files=files,
            source_snapshot={"as_of": result.state.as_of, "state_digest": stable_digest(result.state), "decision_digest": stable_digest(result.decision) if result.decision else None},
            created_at=datetime.now(UTC),
        )
        write_manifest(manifest, bundle / "manifest.json")
        return manifest


def verify_report_bundle(manifest_path: str | Path) -> BundleVerification:
    manifest_path = Path(manifest_path)
    errors: list[str] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "research-report.v1":
            errors.append("manifest schema_version is invalid")
        bundle = manifest_path.parent
        files = payload.get("files", {})
        required = {"complete_report.html", "activity.jsonl"}
        required.update(f"1_analysts/{role}.html" for role in _REQUIRED_ANALYSTS)
        required.update(f"{section}/index.html" for section in _REQUIRED_SECTIONS)
        for relative in sorted(required):
            if relative not in files:
                errors.append(f"manifest missing required file: {relative}")
        for relative, expected in files.items():
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                errors.append(f"unsafe manifest path: {relative}")
                continue
            path = bundle / relative_path
            if not path.exists():
                errors.append(f"missing file: {relative}")
            elif _digest_file(path) != expected:
                errors.append(f"digest mismatch: {relative}")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        errors.append(f"manifest unreadable: {exc}")
    return BundleVerification(ok=not errors, errors=tuple(errors))
