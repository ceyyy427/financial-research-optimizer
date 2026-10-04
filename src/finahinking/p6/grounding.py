"""Evidence-grounding primitives for P6 explanations."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from finahinking.quant.interfaces import _digest

APPROVED_EVIDENCE_KINDS = frozenset({"QuantRun", "EvaluationReport", "RegressionResult", "RiskReport", "OOSResult"})
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
# A boolean supplied by an untrusted caller is not proof of provenance.  The
# only code allowed to construct a verified claim is the verifier below,
# which has access to this process-local capability token.
_VERIFIED_TOKEN = object()


def _verify_source(payload: dict[str, Any], evidence_reference: str) -> str:
    """Verify that the supplied normalized record's fingerprint is intact.

    This is an integrity check, not a source of truth by itself: callers still
    need an approved run/evidence reference.  It prevents fabricated claims
    from being accepted merely because a field named ``fingerprint`` exists.
    """

    claimed = payload.get("fingerprint")
    if not isinstance(claimed, str) or not _FINGERPRINT.fullmatch(claimed):
        raise ValueError("quantitative claims require a valid fingerprinted normalized result")
    if not isinstance(evidence_reference, str) or not evidence_reference.strip():
        raise ValueError("quantitative claims require an evidence reference")
    # A self-consistent hash is an integrity check, not an identity check.  A
    # claim is only grounded when the normalized record carries an approved
    # run/evidence identifier that matches the reference shown to the user.
    linked_ids = tuple(
        str(payload[key])
        for key in ("quant_run_id", "research_run_id", "id", "evidence_reference")
        if isinstance(payload.get(key), str) and payload[key].strip()
    )
    if evidence_reference not in linked_ids:
        raise ValueError("normalized result is not linked to the approved evidence reference")
    candidates = [
        {key: value for key, value in payload.items() if key != "fingerprint"},
        {key: value for key, value in payload.items() if key not in {"fingerprint", "schema_version"}},
    ]
    # MultiAssetEvaluation intentionally fingerprints this stable subset.
    if {"result_fingerprint", "metrics", "benchmark", "limitations", "warnings"}.issubset(payload):
        candidates.append({key: payload[key] for key in ("result_fingerprint", "metrics", "benchmark", "limitations", "warnings")})
    if {"id", "research_run_id", "dataset_version", "strategy_version", "engine_version", "parameters", "result_artifact", "timestamp"}.issubset(payload):
        candidates.append({
            "quant_run_id": payload["id"],
            "research_run_id": payload["research_run_id"],
            "dataset_version": payload["dataset_version"],
            "strategy_version": payload["strategy_version"],
            "engine_version": payload["engine_version"],
            "parameters": payload["parameters"],
            "result_artifact": payload["result_artifact"],
            "timestamp": payload["timestamp"],
        })
    if not any(_digest(candidate) == claimed for candidate in candidates):
        raise ValueError("fingerprinted normalized result is invalid")
    return claimed


@dataclass(frozen=True)
class GroundedClaim:
    text: str
    value: float | int | str | None
    evidence_reference: str
    evidence_kind: str
    source_field: str = ""
    source_fingerprint: str = ""
    unit: str | None = None
    claim_kind: str = "EMPIRICAL RESULT"
    interpretation: bool = False
    source_verified: bool = False
    _verification_token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("claim text is required")
        if not isinstance(self.evidence_reference, str) or not self.evidence_reference.strip():
            raise ValueError("evidence reference is required")
        if self.evidence_kind not in APPROVED_EVIDENCE_KINDS:
            raise ValueError("evidence kind is not approved")
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("claim value must be finite")
        if not isinstance(self.source_fingerprint, str) or not _FINGERPRINT.fullmatch(self.source_fingerprint):
            raise ValueError("numeric claims require a valid source fingerprint")
        if self.claim_kind not in {"EMPIRICAL RESULT", "INTERPRETATION"}:
            raise ValueError("claim kind is invalid")
        if not isinstance(self.source_verified, bool):
            raise TypeError("source_verified must be boolean")
        if self.source_verified and self._verification_token is not _VERIFIED_TOKEN:
            raise ValueError("source_verified claims require an internal verified evidence token")

    @property
    def claim_id(self) -> str:
        return f"claim-{self.fingerprint[:16]}"

    def _payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "value": self.value,
            "evidence_reference": self.evidence_reference,
            "evidence_kind": self.evidence_kind,
            "source_field": self.source_field,
            "source_fingerprint": self.source_fingerprint,
            "unit": self.unit,
            "claim_kind": self.claim_kind,
            "interpretation": self.interpretation,
            "source_verified": self.source_verified,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"claim_id": self.claim_id, **self._payload()}

    @property
    def fingerprint(self) -> str:
        return _digest(self._payload())


def ground_numeric_claim(
    text: str,
    *,
    value: float | str | None,
    evidence_reference: str,
    evidence_kind: str,
    source_field: str = "",
    source_fingerprint: str = "",
    unit: str | None = None,
    claim_kind: str = "EMPIRICAL RESULT",
    interpretation: bool = False,
    source_payload: dict[str, Any] | None = None,
) -> GroundedClaim:
    verified = False
    if source_payload is not None:
        verified_fingerprint = _verify_source(source_payload, evidence_reference)
        if verified_fingerprint != source_fingerprint:
            raise ValueError("source fingerprint does not match the normalized result")
        verified = True
    return GroundedClaim(
        text=text,
        value=value,
        evidence_reference=evidence_reference,
        evidence_kind=evidence_kind,
        source_field=source_field,
        source_fingerprint=source_fingerprint,
        unit=unit,
        claim_kind=claim_kind,
        interpretation=interpretation,
        source_verified=verified,
        _verification_token=_VERIFIED_TOKEN if verified else None,
    )


def require_grounded_claim(claim: GroundedClaim) -> GroundedClaim:
    if not isinstance(claim, GroundedClaim):
        raise TypeError("explanation claims must be GroundedClaim records")
    return claim


def claims_from_result(result: Any, evidence_reference: str, evidence_kind: str) -> tuple[GroundedClaim, ...]:
    """Create claims only from numeric fields already present in a normalized result."""

    if evidence_kind not in APPROVED_EVIDENCE_KINDS:
        raise ValueError("evidence kind is not approved")
    payload = result.to_dict() if hasattr(result, "to_dict") else result
    if not isinstance(payload, dict):
        raise TypeError("normalized result must serialize to a mapping")
    source_fingerprint = _verify_source(payload, evidence_reference)
    linked_run = payload.get("quant_run_id")
    if linked_run is not None and linked_run != evidence_reference:
        raise ValueError("evidence reference does not match the normalized result")
    metrics = payload.get("metrics", payload.get("result", {}).get("metrics", {}))
    if not isinstance(metrics, dict):
        return ()
    fields: dict[str, Any] = {f"metrics.{key}": value for key, value in metrics.items()}
    parameters = payload.get("parameters", {})
    if isinstance(parameters, dict):
        fields.update({f"parameters.{key}": value for key, value in parameters.items()})
    uncertainty = payload.get("uncertainty", {})
    if isinstance(uncertainty, dict):
        for parameter, values in uncertainty.items():
            if isinstance(values, dict):
                fields.update({f"uncertainty.{parameter}.{key}": value for key, value in values.items()})
    claims: list[GroundedClaim] = []
    for key, value in sorted(fields.items()):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            claims.append(
                GroundedClaim(
                    text=f"{key} is {value}.",
                    value=value,
                    evidence_reference=evidence_reference,
                    evidence_kind=evidence_kind,
                    source_field=key,
                    source_fingerprint=source_fingerprint,
                    source_verified=True,
                    _verification_token=_VERIFIED_TOKEN,
                )
            )
    return tuple(claims)


__all__ = ["APPROVED_EVIDENCE_KINDS", "GroundedClaim", "claims_from_result", "ground_numeric_claim", "require_grounded_claim"]
