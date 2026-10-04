"""Trusted claim/evidence projection for source and quant records."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .models import _VERIFIED_CLAIM_TOKEN, Claim, ClaimType, Evidence, EvidenceStatus


def verified_claim(
    *,
    claim_id: str,
    claim_type: ClaimType,
    text: str,
    evidence: Iterable[Evidence],
    evidence_status: EvidenceStatus,
    source_fingerprint: str,
    limitations: Iterable[str] = (),
) -> Claim:
    """Issue a verified claim only after matching it to supplied evidence.

    Callers may construct unverified candidate ``Claim`` records, but a
    product-facing verified claim needs this resolver.  The private token is
    deliberately not serializable or user-settable through the public model.
    """

    evidence_tuple = tuple(evidence)
    if not evidence_tuple:
        raise ValueError("verified claims require evidence")
    if not any(item.source_fingerprint == source_fingerprint for item in evidence_tuple):
        raise ValueError("verified claim fingerprint does not match evidence")
    return Claim(
        claim_id=claim_id,
        claim_type=claim_type,
        text=text,
        evidence_ids=tuple(item.evidence_id for item in evidence_tuple),
        evidence_status=evidence_status,
        source_fingerprint=source_fingerprint,
        source_verified=True,
        limitations=tuple(limitations),
        _verification_token=_VERIFIED_CLAIM_TOKEN,
    )


@dataclass(frozen=True)
class EvidenceBundle:
    evidence: tuple[Evidence, ...]
    claims: tuple[Claim, ...]

    def __post_init__(self) -> None:
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        if len(evidence_by_id) != len(self.evidence):
            raise ValueError("evidence ids must be unique")
        claim_ids = {claim.claim_id for claim in self.claims}
        if len(claim_ids) != len(self.claims):
            raise ValueError("claim ids must be unique")
        for claim in self.claims:
            linked = [evidence_by_id.get(evidence_id) for evidence_id in claim.evidence_ids]
            if any(item is None for item in linked):
                raise ValueError("claim references unknown evidence")
            if claim.source_verified:
                source_fingerprints = {item.source_fingerprint for item in linked if item.source_fingerprint}
                if not claim.source_fingerprint or claim.source_fingerprint not in source_fingerprints:
                    raise ValueError("verified claim fingerprint does not match evidence")
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "claims", tuple(self.claims))

    @property
    def evidence_by_id(self) -> dict[str, Evidence]:
        return {item.evidence_id: item for item in self.evidence}

    def show_evidence(self, claim_id: str) -> list[dict[str, Any]]:
        claim = next((item for item in self.claims if item.claim_id == claim_id), None)
        if claim is None:
            return []
        evidence = self.evidence_by_id
        return [
            {
                "claim_id": claim.claim_id,
                "claim_type": claim.claim_type.value,
                "claim_text": claim.text,
                "evidence_id": evidence_id,
                "evidence_type": evidence[evidence_id].evidence_type,
                "publisher_source_id": evidence[evidence_id].source_id,
                "reference": evidence[evidence_id].reference,
                "status": evidence[evidence_id].status.value,
                "scope": evidence[evidence_id].scope,
                "limitations": list(evidence[evidence_id].limitations),
                "source_fingerprint": evidence[evidence_id].source_fingerprint,
            }
            for evidence_id in claim.evidence_ids
        ]


class TrustedEvidenceRegistry:
    """A small allowlist used before claims cross a product boundary."""

    def __init__(self, bundle: EvidenceBundle) -> None:
        if not isinstance(bundle, EvidenceBundle):
            raise TypeError("bundle must be an EvidenceBundle")
        self.bundle = bundle

    def verify_claim(self, claim: Claim) -> bool:
        if not isinstance(claim, Claim):
            return False
        if not claim.source_verified:
            return False
        try:
            EvidenceBundle(self.bundle.evidence, (claim,))
        except ValueError:
            return False
        return True

    def require_verified(self, claim: Claim) -> Claim:
        if not self.verify_claim(claim):
            raise ValueError("claim fingerprint is not grounded in trusted evidence")
        return claim


__all__ = ["EvidenceBundle", "TrustedEvidenceRegistry", "verified_claim"]
