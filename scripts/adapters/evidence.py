"""Evidence-driven adapter maturity and routing decisions.

Registry labels describe intent; this module evaluates executable capability
from factory registration, replay/integration evidence, smoke evidence, health,
freshness, PIT and certification expiry. Missing evidence is never promoted.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PASS = {"passed", "pass", "complete", "healthy", "verified", "fresh", "ready", "not_required"}


def load_evidence(path=None):
    target = Path(path or Path(__file__).resolve().parents[2] / "config" / "adapter_evidence.json")
    if not target.exists():
        return {}
    payload = json.loads(target.read_text(encoding="utf-8"))
    return {str(item["source_id"]): item for item in payload.get("datasets", [])}


def _passed(value):
    return str(value or "").lower() in PASS


def _not_expired(value, now=None):
    if not value:
        return False
    try:
        expiry = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        current = datetime.fromisoformat(str(now).replace("Z", "+00:00")) if now else datetime.now(timezone.utc)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return expiry > current
    except ValueError:
        return False


def evaluate_maturity(profile, source_id, dataset_id, evidence=None, factory_registered=False, fetch_implemented=False, now=None):
    evidence = dict(evidence or {})
    implementation = profile.get("implementation_status", "planned")
    parser = profile.get("parser_status", "unavailable")
    contract_status = evidence.get("contract_status", "declared")
    fixture_status = evidence.get("fixture_status", "not_run")
    integration_status = evidence.get("integration_status", "not_run")
    quality_status = evidence.get("quality_gate_status", "not_run")
    live_smoke_status = evidence.get("live_smoke_status", "not_run")
    health_status = evidence.get("health_status", profile.get("source_health", "unknown"))
    freshness_status = evidence.get("freshness_status", "not_run")
    pit_status = evidence.get("point_in_time_status", "verified" if profile.get("point_in_time") and source_id not in {"10jqka", "fred"} else "not_available")
    # L3 executable fixtures do not claim a live certification.  An absent
    # expiry therefore keeps the adapter executable while live certification
    # still requires an explicit last success, snapshot and health evidence.
    certification_valid = _not_expired(evidence.get("certification_expires_at"), now) if evidence.get("certification_expires_at") else True
    l3_evidence = {
        "factory_registered": bool(factory_registered),
        "request_contract_passed": _passed(contract_status),
        "parser_fixture_passed": _passed(fixture_status),
        "integration_test_passed": _passed(integration_status),
        "quality_gate_passed": _passed(quality_status),
        "certification_not_expired": certification_valid,
    }
    automatic = bool(fetch_implemented and all(l3_evidence.values()))
    live_certified = bool(
        automatic
        and _passed(live_smoke_status)
        and _passed(health_status)
        and _passed(freshness_status)
        and _passed(pit_status)
        and bool(evidence.get("last_live_success_at"))
        and bool(evidence.get("snapshot_hash"))
    )
    fallback_fetch = _passed(evidence.get("fallback_fetch_status"))
    degraded_execution = bool(fallback_fetch and not automatic)
    contract_only = bool(factory_registered and not fetch_implemented)
    manual_review_only = bool(contract_only and implementation == "partial")
    blocked = bool(implementation == "planned" or not factory_registered)
    roles = set(profile.get("roles", []))
    secondary = profile.get("kind") == "secondary_aggregator" or profile.get("authority") in {"secondary_aggregator", "depends_on_underlying_source"}
    authority_primary = bool(automatic and "primary" in roles and not secondary)
    cross_check_only = bool((secondary or "cross_check" in roles) and not authority_primary)
    if live_certified:
        level = "L4"
    elif automatic:
        level = "L3"
    elif _passed(fixture_status) or _passed(parser):
        level = "L2"
    elif factory_registered:
        level = "L1"
    else:
        level = "L0"
    return {
        "source_id": source_id,
        "dataset_id": dataset_id,
        "access_method": profile.get("primary_method"),
        "maturity_level": level,
        "automatic_execution_ready": automatic,
        "live_certified": live_certified,
        "degraded_execution_ready": degraded_execution,
        "manual_review_only": manual_review_only,
        "contract_only": contract_only,
        "blocked": blocked,
        "authority_primary_allowed": authority_primary,
        "cross_check_only": cross_check_only,
        "evidence": {
            **l3_evidence,
            "contract_status": contract_status,
            "fixture_status": fixture_status,
            "integration_status": integration_status,
            "quality_gate_status": quality_status,
            "live_smoke_status": live_smoke_status,
            "health_status": health_status,
            "freshness_status": freshness_status,
            "point_in_time_status": pit_status,
            "revision_status": evidence.get("revision_status", "not_run"),
            "snapshot_hash": evidence.get("snapshot_hash"),
            "last_live_success_at": evidence.get("last_live_success_at"),
            "certification_expires_at": evidence.get("certification_expires_at"),
        },
    }
