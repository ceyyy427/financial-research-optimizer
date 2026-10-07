"""Settlement-aware, proposal-only learning manager.

The manager can suggest bounded changes after paper settlement.  It has no
registry, risk-policy, or production writer: only an explicit typed admission
record turns a proposal into an ``AdmittedUpdate`` value object.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from .contracts import stable_digest
from .settlement import SettlementEvent

_PUBLIC_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_VALUE = re.compile(
    r"(?:api[-_]?key|secret|token|password|credential|authorization)\s*[=:]|\bprompt\b|[A-Za-z][A-Za-z0-9+.-]*://",
    re.IGNORECASE,
)


class LearningUpdateStatus(str, Enum):
    NO_LEARNING_UPDATE = "NO_LEARNING_UPDATE"
    PROPOSAL_READY = "PROPOSAL_READY"


class AdmissionDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def _as_date(value: date | str, name: str) -> date:
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO date") from exc
    if not isinstance(value, date):
        raise TypeError(f"{name} must be a date")
    return value


def _public_id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _PUBLIC_ID.fullmatch(value.strip()):
        raise ValueError(f"{name} must be a stable public identifier")
    return value.strip()


def _clean_mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or any(token in key.casefold() for token in ("prompt", "secret", "token", "provider", "credential", "endpoint", "path")):
            raise ValueError(f"{name} contains sensitive key")
        if isinstance(item, Mapping):
            result[key.strip()] = _clean_mapping(item, f"{name}.{key}")
        elif isinstance(item, str):
            if _SENSITIVE_VALUE.search(item):
                raise ValueError(f"{name} contains sensitive value")
            result[key.strip()] = item
        elif isinstance(item, (int, float, bool)) or item is None:
            result[key.strip()] = item
        else:
            raise TypeError(f"{name} contains unsupported value")
    return result


@dataclass(frozen=True, slots=True)
class LearningAdmissionRecord:
    admission_id: str
    proposal_digest: str
    admitted_by: str
    decision: AdmissionDecision | str
    as_of: date | str
    rationale: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "admission_id", _public_id(self.admission_id, "admission_id"))
        object.__setattr__(self, "proposal_digest", _public_id(self.proposal_digest, "proposal_digest"))
        object.__setattr__(self, "admitted_by", _public_id(self.admitted_by, "admitted_by"))
        if not isinstance(self.decision, AdmissionDecision):
            object.__setattr__(self, "decision", AdmissionDecision(self.decision))
        object.__setattr__(self, "as_of", _as_date(self.as_of, "admission as_of"))
        if not isinstance(self.rationale, str):
            raise TypeError("rationale must be text")
        if any(token in self.rationale.casefold() for token in ("api_key", "secret", "token=", "prompt", "http://", "https://")):
            raise ValueError("admission rationale contains sensitive material")


@dataclass(frozen=True, slots=True)
class LearningUpdateProposal:
    status: LearningUpdateStatus | str
    settlement_digest: str | None
    as_of: date | None
    factor_weight_updates: Mapping[str, Any] = field(default_factory=dict)
    risk_rule_updates: Mapping[str, Any] = field(default_factory=dict)
    registry_updates: Mapping[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    proposal_digest: str = ""
    admitted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.status, LearningUpdateStatus):
            object.__setattr__(self, "status", LearningUpdateStatus(self.status))
        if self.settlement_digest is not None:
            object.__setattr__(self, "settlement_digest", _public_id(self.settlement_digest, "settlement_digest"))
        if self.as_of is not None and not isinstance(self.as_of, date):
            object.__setattr__(self, "as_of", _as_date(self.as_of, "proposal as_of"))
        object.__setattr__(self, "factor_weight_updates", _clean_mapping(self.factor_weight_updates, "factor_weight_updates"))
        object.__setattr__(self, "risk_rule_updates", _clean_mapping(self.risk_rule_updates, "risk_rule_updates"))
        object.__setattr__(self, "registry_updates", _clean_mapping(self.registry_updates, "registry_updates"))
        refs = tuple(str(ref).strip() for ref in self.evidence_refs if str(ref).strip())
        if any(_SENSITIVE_VALUE.search(ref) for ref in refs):
            raise ValueError("evidence refs contain sensitive material")
        object.__setattr__(self, "evidence_refs", refs)
        if self.admitted is not False:
            raise ValueError("proposals cannot be marked admitted")
        if self.proposal_digest:
            object.__setattr__(self, "proposal_digest", _public_id(self.proposal_digest, "proposal_digest"))
        else:
            object.__setattr__(self, "proposal_digest", self._compute_digest())

    @property
    def factor_weights(self) -> Mapping[str, Any]:
        return self.factor_weight_updates

    @property
    def risk_rules(self) -> Mapping[str, Any]:
        return self.risk_rule_updates

    @property
    def registry(self) -> Mapping[str, Any]:
        return self.registry_updates

    def _compute_digest(self) -> str:
        return stable_digest({
            "status": self.status,
            "settlement_digest": self.settlement_digest,
            "as_of": self.as_of,
            "factor_weight_updates": self.factor_weight_updates,
            "risk_rule_updates": self.risk_rule_updates,
            "registry_updates": self.registry_updates,
            "evidence_refs": self.evidence_refs,
        })


@dataclass(frozen=True, slots=True)
class AdmittedUpdate:
    proposal: LearningUpdateProposal
    admission: LearningAdmissionRecord

    def __post_init__(self) -> None:
        if not isinstance(self.proposal, LearningUpdateProposal) or not isinstance(self.admission, LearningAdmissionRecord):
            raise TypeError("admitted update requires typed proposal and admission")
        if self.proposal.status is not LearningUpdateStatus.PROPOSAL_READY:
            raise ValueError("only a ready proposal can be admitted")
        if self.admission.decision is not AdmissionDecision.APPROVED:
            raise ValueError("admission must be approved")
        if self.admission.proposal_digest != self.proposal.proposal_digest:
            raise ValueError("admission proposal digest does not match")
        if self.proposal.as_of is not None and self.admission.as_of < self.proposal.as_of:
            raise ValueError("admission as_of cannot precede proposal as_of")


class LearningManager:
    def __init__(self) -> None:
        self._proposals: dict[str, LearningUpdateProposal] = {}
        self._admitted: dict[str, AdmittedUpdate] = {}

    @property
    def admitted_updates(self) -> tuple[AdmittedUpdate, ...]:
        return tuple(self._admitted[key] for key in sorted(self._admitted))

    def propose_update(
        self,
        settlement: SettlementEvent | None,
        history: Sequence[SettlementEvent] = (),
    ) -> LearningUpdateProposal:
        if settlement is None:
            return LearningUpdateProposal(LearningUpdateStatus.NO_LEARNING_UPDATE, None, None)
        if not isinstance(settlement, SettlementEvent):
            raise TypeError("settlement must be a SettlementEvent")
        seen: set[str] = set()
        for previous in history:
            if not isinstance(previous, SettlementEvent):
                raise TypeError("learning history must contain SettlementEvent values")
            if previous.as_of > settlement.as_of:
                raise ValueError("learning history contains a future settlement")
            if previous.fingerprint in seen:
                raise ValueError("duplicate settlement in learning history")
            seen.add(previous.fingerprint)
        digest = settlement.fingerprint
        if digest in seen:
            raise ValueError("duplicate settlement in learning history")
        if digest in self._proposals:
            return self._proposals[digest]
        outcomes = settlement.realized_outcomes
        factor = outcomes.get("factor_weight_updates", outcomes.get("factor_weights", outcomes.get("factor_scores", {}))) if isinstance(outcomes, Mapping) else {}
        risk = outcomes.get("risk_rule_updates", outcomes.get("risk_rules", {})) if isinstance(outcomes, Mapping) else {}
        registry = outcomes.get("registry_updates", outcomes.get("registry", {})) if isinstance(outcomes, Mapping) else {}
        proposal = LearningUpdateProposal(
            LearningUpdateStatus.PROPOSAL_READY,
            digest,
            settlement.as_of,
            factor_weight_updates=_clean_mapping(factor, "factor_weight_updates"),
            risk_rule_updates=_clean_mapping(risk, "risk_rule_updates"),
            registry_updates=_clean_mapping(registry, "registry_updates"),
            evidence_refs=(f"settlement:{settlement.run_id}", f"ledger:{settlement.ledger_fingerprint}"),
        )
        self._proposals[digest] = proposal
        return proposal

    def admit_update(self, proposal: LearningUpdateProposal, admission_record: LearningAdmissionRecord) -> AdmittedUpdate:
        if not isinstance(proposal, LearningUpdateProposal) or not isinstance(admission_record, LearningAdmissionRecord):
            raise TypeError("explicit typed admission record is required")
        if admission_record.proposal_digest != proposal.proposal_digest:
            raise ValueError("admission proposal digest does not match")
        if proposal.proposal_digest in self._admitted:
            previous = self._admitted[proposal.proposal_digest]
            if previous.admission == admission_record:
                return previous
            raise ValueError("proposal already has an admission")
        admitted = AdmittedUpdate(proposal, admission_record)
        self._admitted[proposal.proposal_digest] = admitted
        return admitted


__all__ = [
    "AdmissionDecision",
    "AdmittedUpdate",
    "LearningAdmissionRecord",
    "LearningManager",
    "LearningUpdateProposal",
    "LearningUpdateStatus",
]
