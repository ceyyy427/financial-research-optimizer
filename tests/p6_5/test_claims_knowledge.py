import pytest

from finahinking.p6_5.claims import EvidenceBundle, TrustedEvidenceRegistry, verified_claim
from finahinking.p6_5.knowledge import (
    ConclusionLadder,
    ConclusionLevel,
    KnowledgeBridge,
    WhyItMatters,
)
from finahinking.p6_5.models import (
    Claim,
    ClaimType,
    Concept,
    ConceptRelation,
    Evidence,
    EvidenceStatus,
)


def _bundle() -> EvidenceBundle:
    evidence = Evidence("evidence-1", "OfficialDocument", "bls", "capture-1", "https://www.bls.gov/cpi/", EvidenceStatus.DIRECT_SOURCE, "CPI", ("API values have no vintage identifier.",), "a" * 64)
    claim = verified_claim(
        claim_id="claim-1",
        claim_type=ClaimType.FACT,
        text="CPI index changed.",
        evidence=(evidence,),
        evidence_status=EvidenceStatus.DIRECT_SOURCE,
        source_fingerprint="a" * 64,
    )
    return EvidenceBundle((evidence,), (claim,))


def test_evidence_bundle_and_registry_reject_forged_verified_claim() -> None:
    bundle = _bundle()
    assert bundle.show_evidence("claim-1")[0]["evidence_id"] == "evidence-1"
    registry = TrustedEvidenceRegistry(bundle)
    assert registry.verify_claim(bundle.claims[0])
    with pytest.raises(ValueError, match="verified"):
        Claim("claim-2", ClaimType.FACT, "forged", ("evidence-1",), EvidenceStatus.DIRECT_SOURCE, "b" * 64, True)
    unverified = Claim("claim-2", ClaimType.FACT, "forged", ("evidence-1",), EvidenceStatus.DIRECT_SOURCE, "b" * 64)
    with pytest.raises(ValueError, match="fingerprint"):
        registry.require_verified(unverified)


def test_why_it_matters_and_conclusion_ladder_preserve_boundaries() -> None:
    why = WhyItMatters(
        event_id="event-1",
        statement="A higher CPI reading may matter through rate expectations.",
        mechanism="Inflation -> rate expectations -> yields -> discount rates",
        relation_type="ECONOMIC_MECHANISM",
        evidence_status=EvidenceStatus.THEORY_SUPPORTED,
        evidence_ids=("evidence-1",),
        limitation="The mechanism is not a forecast of tomorrow's return.",
    )
    ladder = ConclusionLadder(
        (
            (ConclusionLevel.WHAT_WE_KNOW, "The release reported a CPI index value.", ("evidence-1",)),
            (ConclusionLevel.EVIDENCE_SUGGESTS, "The historical fixture shows an association.", ("evidence-1",)),
            (ConclusionLevel.PLAUSIBLE, "Rate expectations are a plausible mechanism.", ("evidence-1",)),
            (ConclusionLevel.UNKNOWN, "The release does not determine the next equity return.", ()),
            (ConclusionLevel.WHAT_WOULD_CHANGE_VIEW, "A revised release or a different window would change the view.", ("evidence-1",)),
        ),
        limitations=("Historical association is not causality.",),
    )
    assert why.relation_type == "ECONOMIC_MECHANISM"
    assert ladder.level(ConclusionLevel.UNKNOWN).evidence_ids == ()
    assert ladder.to_dict()["limitations"]


def test_knowledge_bridge_requires_typed_relation() -> None:
    concepts = (
        Concept("cpi", "CPI", "Average change in consumer prices.", evidence_ids=("evidence-1",)),
        Concept("rates", "Policy Rate", "A policy instrument.", evidence_ids=("evidence-1",)),
    )
    relation = ConceptRelation("rel-1", "cpi", "rates", "ECONOMIC_MECHANISM", EvidenceStatus.THEORY_SUPPORTED, ("evidence-1",))
    bridge = KnowledgeBridge("event-1", concepts, (relation,))
    assert bridge.path()[0].name == "CPI"
    with pytest.raises(ValueError, match="relation"):
        KnowledgeBridge("event-1", concepts, (ConceptRelation("rel-2", "cpi", "rates", "UNKNOWN", EvidenceStatus.THEORY_SUPPORTED),))
