#!/usr/bin/env python3
"""Capability-aware source routing for the upper research agent."""
import argparse
import json
from dataclasses import dataclass
from pathlib import Path


class SourceRoutingError(RuntimeError):
    """Raised when no source satisfies the declared research contract."""


def load_registry(path):
    path = Path(path)
    try:
        import yaml
    except ImportError as exc:
        raise SourceRoutingError("source_registry.yaml requires PyYAML; install with python3 -m pip install -r requirements.txt") from exc
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = payload.get("sources", payload) if isinstance(payload, dict) else payload
    if not isinstance(sources, list):
        raise SourceRoutingError("source registry must contain a sources list")
    profiles = {}
    for profile in sources:
        if not isinstance(profile, dict) or not profile.get("source_id"):
            raise SourceRoutingError("every source profile needs source_id")
        source_id = profile["source_id"]
        if source_id in profiles:
            raise SourceRoutingError(f"duplicate source_id: {source_id}")
        profiles[source_id] = profile
    return profiles


@dataclass(frozen=True)
class SourceCandidate:
    profile: dict
    score: float
    reasons: tuple
    authorization_status: str = "unknown"

    def as_dict(self, role="primary", required_fields=None):
        profile = self.profile
        return {
            "source_id": profile["source_id"],
            "role": role,
            "reason": "; ".join(self.reasons),
            "authority": profile.get("authority"),
            "source_authority": profile.get("authority"),
            "access_method": profile.get("primary_method"),
            "required_fields": required_fields or profile.get("required_fields", []),
            "point_in_time": profile.get("point_in_time", False),
            "revision_aware": profile.get("revision_aware", False),
            "authorization_required": profile.get("authentication", {}).get("required", False),
            "authorization_status": self.authorization_status,
            "access_policy": profile.get("access_policy"),
            "priority_score": round(self.score, 4),
        }


class SourceRouter:
    """Select sources by declared capabilities, not by whether a page opens."""

    AUTHORITY_SCORES = {
        "exchange": 40,
        "securities_regulator": 40,
        "central_bank": 38,
        "national_statistics": 38,
        "regulator_disclosure": 38,
        "federal_reserve": 36,
        "licensed_provider": 32,
        "licensed_market_data": 28,
        "depends_on_underlying_source": 12,
        "secondary_aggregator": 5,
    }

    def __init__(self, profiles, registry_path=None):
        self.profiles = profiles
        self.registry_path = str(registry_path) if registry_path else None

    @classmethod
    def from_file(cls, path):
        return cls(load_registry(path), registry_path=path)

    @staticmethod
    def _capability_ok(profile, capability):
        capability = str(capability).lower()
        if capability in {"point_in_time", "point-in-time", "pit"}:
            return bool(profile.get("point_in_time"))
        if capability in {"vintage_data", "vintage"}:
            return bool(profile.get("revision_aware")) and ("vintages" in profile.get("data_types", []) or profile.get("source_id") == "alfred")
        if capability == "revision_aware":
            return bool(profile.get("revision_aware"))
        if capability in {"release_aware", "release_time"}:
            checks = set(profile.get("quality_checks", []))
            return "release_date" in checks or "accepted_datetime" in checks or "announcement_time" in checks
        if capability == "api":
            return "api" in profile.get("access_methods", [])
        if capability in {"authorized", "licensed"}:
            return profile.get("access_policy") in {"authorized_only", "licensed_only"}
        if capability.startswith("field:"):
            return capability.split(":", 1)[1] in profile.get("required_fields", [])
        if capability.startswith("data_type:"):
            return capability.split(":", 1)[1] in profile.get("data_types", [])
        return capability in profile.get("access_methods", []) or capability in profile.get("data_types", [])

    def _candidate(self, profile, required_capabilities, required_fields, authorization_status, topic, freshness_minutes):
        missing = [cap for cap in required_capabilities if not self._capability_ok(profile, cap)]
        fields = set(profile.get("required_fields", []))
        missing_fields = [field for field in required_fields if field not in fields]
        auth = profile.get("authentication", {})
        needs_auth = bool(auth.get("required") or profile.get("access_policy") in {"authorized_only", "licensed_only"})
        licensed_only = profile.get("access_policy") in {"authorized_only", "licensed_only"}
        if licensed_only and authorization_status not in {"authorized", "not_required"}:
            return None, [f"authorization status {authorization_status} is insufficient"]
        if missing or missing_fields:
            reasons = []
            if missing:
                reasons.append(f"missing capabilities: {','.join(missing)}")
            if missing_fields:
                reasons.append(f"missing fields: {','.join(missing_fields)}")
            return None, reasons
        score = float(profile.get("priority", 0)) + self.AUTHORITY_SCORES.get(profile.get("authority"), 0)
        reasons = [f"authority={profile.get('authority')}", "declared capabilities satisfy the contract"]
        if profile.get("point_in_time"):
            score += 25
            reasons.append("point-in-time capable")
        if profile.get("revision_aware"):
            score += 15
            reasons.append("revision aware")
        if needs_auth and authorization_status not in {"authorized", "not_required"}:
            score -= 20
            reasons.append("authorization checkpoint required before fetch")
        if "api" in profile.get("access_methods", []):
            score += 6
            reasons.append("API available")
        if freshness_minutes is not None and "cached_snapshot" in profile.get("fallback_methods", []):
            score += 2
            reasons.append(f"cache fallback for {freshness_minutes} minute freshness budget")
        if profile.get("kind") == "secondary_aggregator":
            score -= 25
            reasons.append("secondary source; cross-check only")
        if topic and any(str(token).lower() in str(topic).lower() for token in profile.get("data_types", [])):
            score += 2
        return SourceCandidate(profile, score, tuple(reasons), authorization_status), []

    def resolve(self, topic, universe=None, required_capabilities=None, required_fields=None, authorization_status="unknown", freshness_minutes=None, allow_secondary=False):
        required_capabilities = list(required_capabilities or [])
        required_fields = list(required_fields or [])
        candidates, rejected = [], {}
        for profile in self.profiles.values():
            if profile.get("kind") == "secondary_aggregator" and not allow_secondary and required_capabilities:
                # Secondary sources remain eligible only when no higher-grade source can satisfy the contract.
                pass
            candidate, reasons = self._candidate(profile, required_capabilities, required_fields, authorization_status, topic, freshness_minutes)
            if candidate:
                candidates.append(candidate)
            else:
                rejected[profile["source_id"]] = reasons
        if not candidates:
            raise SourceRoutingError(json.dumps({"reason": "no source satisfies contract", "rejected": rejected}, ensure_ascii=False))
        candidates.sort(key=lambda item: (-item.score, item.profile["source_id"]))
        primary = candidates[0]
        secondary = [item for item in candidates[1:] if item.profile.get("source_id") != primary.profile.get("source_id")]
        if not allow_secondary:
            secondary = [item for item in secondary if item.profile.get("kind") != "secondary_aggregator"]
        source_plan = [primary.as_dict("primary", required_fields)]
        source_plan.extend(item.as_dict("cross_check", required_fields) for item in secondary[:3])
        fallback_plan = list(primary.profile.get("fallback_methods", []))
        blocking_rules = ["material_price_conflict", "missing_effective_timestamp", "unknown_adjustment_convention"]
        if primary.profile.get("access_policy") in {"licensed_only", "authorized_only"}:
            blocking_rules.append("authorization_expired_or_missing")
        return {
            "topic": topic,
            "universe": list(universe or []),
            "source_plan": source_plan,
            "fallback_plan": fallback_plan,
            "blocking_rules": blocking_rules,
            "rejected_sources": rejected,
            "selection_rule": "authority → point_in_time → field completeness → freshness → authorization → stability → cost",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/source_registry.yaml"))
    parser.add_argument("--topic", required=True)
    parser.add_argument("--universe", nargs="*", default=[])
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--field", action="append", default=[])
    parser.add_argument("--authorization-status", default="unknown")
    parser.add_argument("--freshness-minutes", type=int, default=None)
    parser.add_argument("--allow-secondary", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    router = SourceRouter.from_file(args.registry)
    payload = router.resolve(args.topic, args.universe, args.capability, args.field, args.authorization_status, args.freshness_minutes, args.allow_secondary)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(rendered)


if __name__ == "__main__":
    main()
