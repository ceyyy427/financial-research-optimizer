"""The first product-quality P6.5 event-to-learning journey."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from finahinking.p6.explanation import PredictionRevealExplain, predict_reveal_explain
from finahinking.p6.gateway import P6QuantGateway
from finahinking.p6.learning import LearningCard, LearningStore, make_learning_card

from .admission import SourceRegistry, default_source_registry
from .bls import BLSCPIAdapter, CapturedBLSResponse
from .claims import EvidenceBundle, verified_claim
from .knowledge import ConclusionLadder, ConclusionLevel, KnowledgeBridge, WhyItMatters
from .models import (
    AdmissionDecision,
    Claim,
    ClaimEvidenceLink,
    ClaimType,
    Concept,
    ConceptRelation,
    Event,
    Evidence,
    EvidenceStatus,
    Source,
    SourceEndpoint,
    SourceRelease,
    SourceTier,
)
from .quant_bridge import EventQuantBridge

_SAFE_ARTIFACT_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


@dataclass(frozen=True)
class ProductJourney:
    user_id: str
    event: Event
    claims: tuple[Claim, ...]
    evidence: tuple[Evidence, ...]
    show_evidence: tuple[dict[str, Any], ...]
    what_happened: str
    what_changed: str
    why_it_may_matter: WhyItMatters
    what_we_know: str
    evidence_suggests: str
    plausible: str
    unknown: str
    what_would_change_view: str
    what_to_watch_next: str
    knowledge_bridge: KnowledgeBridge
    test_idea: dict[str, Any]
    quant_evidence: dict[str, Any]
    conclusion_ladder: ConclusionLadder
    predict_reveal_explain: PredictionRevealExplain
    learning_card: LearningCard
    learning_state: Any
    progressive_levels: tuple[str, ...] = ("EVENT", "MECHANISM", "EVIDENCE", "QUANT", "DEEP_KNOWLEDGE")

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "event": self.event.to_dict(),
            "claims": [claim.to_dict() for claim in self.claims],
            "evidence": [item.to_dict() for item in self.evidence],
            "show_evidence": [dict(item) for item in self.show_evidence],
            "what_happened": self.what_happened,
            "what_changed": self.what_changed,
            "why_it_may_matter": self.why_it_may_matter.to_dict(),
            "what_we_know": self.what_we_know,
            "evidence_suggests": self.evidence_suggests,
            "plausible": self.plausible,
            "unknown": self.unknown,
            "what_would_change_view": self.what_would_change_view,
            "what_to_watch_next": self.what_to_watch_next,
            "knowledge_bridge": self.knowledge_bridge.to_dict(),
            "test_idea": dict(self.test_idea),
            "quant_evidence": dict(self.quant_evidence),
            "conclusion_ladder": self.conclusion_ladder.to_dict(),
            "predict_reveal_explain": self.predict_reveal_explain.to_dict(),
            "learning_card": self.learning_card.to_dict(),
            "learning_state": self.learning_state.to_dict() if hasattr(self.learning_state, "to_dict") else self.learning_state,
            "progressive_levels": list(self.progressive_levels),
        }


class UnderstandingEngine:
    """Compose source, evidence, typed quant, and learning contracts."""

    def __init__(self, *, gateway: P6QuantGateway | None = None, learning_store: LearningStore | None = None, artifact_root: str | Path | None = None, repository: Any | None = None, source_registry: SourceRegistry | None = None) -> None:
        self.gateway = gateway or P6QuantGateway()
        self.quant_bridge = EventQuantBridge(self.gateway)
        self.learning_store = learning_store or LearningStore()
        self.artifact_root = Path(artifact_root or Path.cwd() / "research_workspace" / "p6_5_artifacts")
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.repository = repository
        self.source_registry = source_registry or default_source_registry()

    def _persist_capture(self, captured: CapturedBLSResponse) -> Path:
        if not isinstance(captured.raw_bytes, bytes) or not captured.raw_bytes:
            raise ValueError("raw capture bytes are required")
        if captured.capture.raw_payload is None:
            raise ValueError("capture text payload is required")
        if captured.capture.raw_payload.encode("utf-8") != captured.raw_bytes:
            raise ValueError("capture text and raw bytes differ")
        if hashlib.sha256(captured.raw_bytes).hexdigest() != captured.capture.payload_hash:
            raise ValueError("capture payload hash does not match raw bytes")
        artifact_id = captured.capture.raw_artifact_id
        if not _SAFE_ARTIFACT_ID.fullmatch(artifact_id):
            raise ValueError("raw artifact id is unsafe")
        path = self.artifact_root / f"{artifact_id}.bin"
        if path.parent != self.artifact_root:
            raise ValueError("raw artifact path escapes root")
        if path.exists():
            raise ValueError("raw artifact path already exists")
        fd, temporary = tempfile.mkstemp(prefix=f".{artifact_id}.", suffix=".tmp", dir=self.artifact_root)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(captured.raw_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return path

    @staticmethod
    def _quant_fixture() -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        values = {
            "2020-01-01": (100.0, 100.0),
            "2020-01-02": (110.0, 95.0),
            "2020-01-03": (121.0, 90.0),
            "2020-01-04": (120.0, 92.0),
            "2020-01-05": (130.0, 88.0),
        }
        for date, (aaa, bbb) in values.items():
            rows.extend(
                [
                    {"date": date, "asset": "AAA", "close": aaa, "available_at": date},
                    {"date": date, "asset": "BBB", "close": bbb, "available_at": date},
                ]
            )
        return pd.DataFrame(rows)

    def _run_quant(self, event: Event, user_id: str) -> Any:
        return self.quant_bridge.run(event, user_id, frame=self._quant_fixture())

    def _persist_vertical_slice(self, *, source: Source, release: SourceRelease, capture: CapturedBLSResponse, observations: tuple[Any, ...], event: Event, evidence: tuple[Evidence, ...], claims: tuple[Claim, ...], concepts: tuple[Concept, ...], quant_evidence_id: str, card: LearningCard, user_id: str) -> None:
        """Persist the completed chain through the parameterized repository.

        The repository is optional so the deterministic product fixture can be
        used without a database, but when supplied every link is written in a
        dependency-safe order (source → capture/observations/evidence → event
        → claims → learning reference).
        """

        if self.repository is None:
            return
        endpoint = SourceEndpoint(
            endpoint_id="bls-cpi-v2",
            source_id=source.source_id,
            url="https://api.bls.gov/publicAPI/v2/timeseries/data/",
            method="POST",
            content_type="application/json",
            rate_limit="public quota",
            historical_support=True,
            revision_support="unknown_vintage",
            available_at_semantics="release_bound_plus_first_observed",
        )
        self.repository.save_source(source)
        self.repository.save_endpoint(endpoint)
        self.repository.save_release(release)
        self.repository.save_capture(capture.capture)
        for observation in observations:
            self.repository.save_observation(observation)
        for item in evidence:
            self.repository.save_evidence(item)
        self.repository.save_event(event)
        for concept in concepts:
            self.repository.save_concept(concept)
        for claim in claims:
            self.repository.save_claim(claim)
            for evidence_id in claim.evidence_ids:
                self.repository.link_claim_evidence(
                    ClaimEvidenceLink(
                        claim_id=claim.claim_id,
                        evidence_id=evidence_id,
                        support_type=claim.evidence_status,
                        scope="Product journey claim support",
                        limitations=claim.limitations,
                    )
                )
        self.repository.save_learning_ref(
            learning_ref_id=f"learning-{event.event_id}-{user_id}",
            event_id=event.event_id,
            evidence_id=quant_evidence_id,
            concept_id="concept-cpi",
            card_fingerprint=card.fingerprint,
            user_id=user_id,
        )

    def run_cpi_journey(self, user_id: str, captured: CapturedBLSResponse, release: SourceRelease) -> ProductJourney:
        if not isinstance(captured, CapturedBLSResponse) or not isinstance(release, SourceRelease):
            raise TypeError("captured response and release are required")
        admission = self.source_registry.get(captured.capture.source_id)
        if admission.decision is not AdmissionDecision.ADMIT_AUTHORITATIVE:
            raise ValueError("source is not admitted as authoritative")
        if release.source_id != admission.source_id or release.endpoint_id != "bls-cpi-v2":
            raise ValueError("release is outside the admitted BLS boundary")
        if not release.release_url.startswith("https://www.bls.gov/news.release/"):
            raise ValueError("release is outside the admitted BLS boundary")
        self._persist_capture(captured)
        source = Source(
            source_id="bls",
            name="Bureau of Labor Statistics CPI",
            publisher="U.S. Bureau of Labor Statistics",
            tier=SourceTier.TIER_0,
            canonical_url="https://www.bls.gov/cpi/",
            underlying_source="BLS Public Data API v2",
            owner="U.S. Department of Labor",
            access_method="official_api_post",
            usage_conditions="Public API; preserve attribution and current terms.",
            authentication="none_for_admitted_fixture_mode",
            decision=AdmissionDecision.ADMIT_AUTHORITATIVE,
        )
        parsed = BLSCPIAdapter.parse_capture(captured.capture, release_by_period={release.reference_period: release})
        capture_evidence = Evidence(
            evidence_id=f"evidence-{captured.capture.capture_id}",
            evidence_type="TransportCapture",
            source_id=source.source_id,
            capture_id=captured.capture.capture_id,
            reference=captured.capture.raw_artifact_id,
            status=EvidenceStatus.DIRECT_SOURCE,
            scope="Raw BLS API response preserved before canonicalization.",
            limitations=("Transport capture proves what was received, not an independent vintage identifier.",),
            source_fingerprint=source.fingerprint,
        )
        release_evidence = Evidence(
            evidence_id=f"evidence-{release.release_id}",
            evidence_type="OfficialDocument",
            source_id=source.source_id,
            capture_id=captured.capture.capture_id,
            reference=release.release_url,
            status=EvidenceStatus.DIRECT_SOURCE,
            scope=f"Official CPI release timing for {release.reference_period}.",
            limitations=("Release timing is a publication bound; API first observation remains separately recorded.",),
            source_fingerprint=source.fingerprint,
        )
        event = BLSCPIAdapter.to_event(
            release.reference_period,
            parsed.observations,
            release,
            evidence_ids=(capture_evidence.evidence_id, release_evidence.evidence_id),
        )
        claims: list[Claim] = []
        for observation in parsed.observations:
            if observation.reference_period != release.reference_period:
                continue
            latest = observation.latest
            claims.append(
                verified_claim(
                    claim_id=f"claim-{observation.observation_id}",
                    claim_type=ClaimType.FACT,
                    text=f"BLS {observation.series_id} was {latest.value:.3f} for {observation.reference_period}.",
                    evidence=(release_evidence, capture_evidence),
                    evidence_status=EvidenceStatus.DIRECT_SOURCE,
                    source_fingerprint=source.fingerprint,
                    limitations=("The API response does not expose a vintage identifier.",),
                )
            )
        if not claims:
            raise ValueError("BLS release has no canonical observations")
        why = WhyItMatters(
            event_id=event.event_id,
            statement="A CPI release may matter through inflation expectations and the policy-rate mechanism.",
            mechanism="Inflation -> rate expectations -> bond yields -> discount rates -> asset valuation",
            relation_type="ECONOMIC_MECHANISM",
            evidence_status=EvidenceStatus.THEORY_SUPPORTED,
            evidence_ids=(release_evidence.evidence_id,),
            limitation="This mechanism is a structured interpretation, not a causal or price forecast.",
        )
        concepts = (
            Concept("concept-cpi", "CPI", "An index of average consumer prices paid by urban consumers.", evidence_ids=(release_evidence.evidence_id,)),
            Concept("concept-inflation", "Inflation", "The rate at which a general price index changes over time.", "(CPI_t / CPI_{t-1}) - 1", (release_evidence.evidence_id,)),
            Concept("concept-rate", "Policy Rate", "A central-bank policy instrument that can influence financing conditions.", evidence_ids=(release_evidence.evidence_id,)),
            Concept("concept-yield", "Bond Yield", "The return demanded by holders of a bond.", evidence_ids=(release_evidence.evidence_id,)),
            Concept("concept-discount", "Discount Rate", "A rate used to translate future cash flows into present value.", evidence_ids=(release_evidence.evidence_id,)),
            Concept("concept-valuation", "Equity Valuation", "A present-value view of expected future cash flows.", evidence_ids=(release_evidence.evidence_id,)),
        )
        relations = (
            ConceptRelation("relation-cpi-inflation", "concept-cpi", "concept-inflation", "SUPPORTED_RELATIONSHIP", EvidenceStatus.DERIVED_FROM_SOURCE, (release_evidence.evidence_id,)),
            ConceptRelation("relation-inflation-rate", "concept-inflation", "concept-rate", "ECONOMIC_MECHANISM", EvidenceStatus.THEORY_SUPPORTED, (release_evidence.evidence_id,)),
            ConceptRelation("relation-rate-yield", "concept-rate", "concept-yield", "ECONOMIC_MECHANISM", EvidenceStatus.THEORY_SUPPORTED, (release_evidence.evidence_id,)),
            ConceptRelation("relation-yield-discount", "concept-yield", "concept-discount", "ECONOMIC_MECHANISM", EvidenceStatus.THEORY_SUPPORTED, (release_evidence.evidence_id,)),
            ConceptRelation("relation-discount-valuation", "concept-discount", "concept-valuation", "ECONOMIC_MECHANISM", EvidenceStatus.THEORY_SUPPORTED, (release_evidence.evidence_id,)),
        )
        bridge = KnowledgeBridge(event.event_id, concepts, relations)
        response = self._run_quant(event, user_id)
        if response.status != "SUCCEEDED" or not response.quant_run_id or not response.result_fingerprint:
            raise RuntimeError(response.message or "typed quant bridge did not complete")
        quant_evidence_id = f"evidence-{response.quant_run_id}"
        quant_evidence = Evidence(
            evidence_id=quant_evidence_id,
            evidence_type="QuantRun",
            source_id=source.source_id,
            capture_id=captured.capture.capture_id,
            reference=response.quant_run_id,
            status=EvidenceStatus.QUANT_SUPPORTED,
            scope="Normalized P6 typed-gateway historical experiment.",
            limitations=tuple(response.limitations),
            source_fingerprint=response.result_fingerprint,
        )
        quant_claim = verified_claim(
            claim_id=f"claim-{response.quant_run_id}",
            claim_type=ClaimType.QUANT_FINDING,
            text="The fixed historical experiment reports a normalized result for its supplied fixture.",
            evidence=(quant_evidence,),
            evidence_status=EvidenceStatus.QUANT_SUPPORTED,
            source_fingerprint=response.result_fingerprint,
            limitations=tuple(response.limitations),
        )
        all_evidence = (capture_evidence, release_evidence, quant_evidence)
        interpretation_claim = verified_claim(
            claim_id=f"claim-interpretation-{event.reference_period}",
            claim_type=ClaimType.INTERPRETATION,
            text="The CPI release may matter through inflation expectations and the policy-rate mechanism.",
            evidence=(release_evidence,),
            evidence_status=EvidenceStatus.THEORY_SUPPORTED,
            source_fingerprint=source.fingerprint,
            limitations=("This mechanism is not a causal or price forecast.",),
        )
        hypothesis_claim = verified_claim(
            claim_id=f"claim-hypothesis-{event.reference_period}",
            claim_type=ClaimType.HYPOTHESIS,
            text="A fixed historical momentum test can provide bounded context around the event.",
            evidence=(quant_evidence,),
            evidence_status=EvidenceStatus.QUANT_SUPPORTED,
            source_fingerprint=response.result_fingerprint,
            limitations=("The sample cannot establish that the mechanism caused the result.",),
        )
        unknown_claim = verified_claim(
            claim_id=f"claim-unknown-{event.reference_period}",
            claim_type=ClaimType.UNKNOWN,
            text="The release alone does not determine the next asset return or a causal effect.",
            evidence=(release_evidence,),
            evidence_status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
            source_fingerprint=source.fingerprint,
            limitations=("A later pre-specified test and additional evidence would be needed.",),
        )
        limitation_claim = verified_claim(
            claim_id=f"claim-limitation-{event.reference_period}",
            claim_type=ClaimType.LIMITATION,
            text="The BLS API response does not expose a vintage identifier for this capture.",
            evidence=(capture_evidence,),
            evidence_status=EvidenceStatus.PARTIALLY_SUPPORTED,
            source_fingerprint=source.fingerprint,
            limitations=("Revision history therefore remains bounded rather than fully reconstructed.",),
        )
        all_claims = (*claims, interpretation_claim, hypothesis_claim, unknown_claim, limitation_claim, quant_claim)
        bundle = EvidenceBundle(all_evidence, all_claims)
        evaluation = response.result.get("evaluation", {}) if isinstance(response.result, dict) else {}
        metrics = evaluation.get("metrics", {}) if isinstance(evaluation, dict) else {}
        ladder = ConclusionLadder(
            (
                (ConclusionLevel.WHAT_WE_KNOW, "The official BLS release and captured API response provide a CPI observation.", (release_evidence.evidence_id, capture_evidence.evidence_id)),
                (ConclusionLevel.EVIDENCE_SUGGESTS, f"The fixed historical experiment produced normalized metrics: {metrics}.", (quant_evidence_id,)),
                (ConclusionLevel.PLAUSIBLE, why.statement, (release_evidence.evidence_id,)),
                (ConclusionLevel.UNKNOWN, "The release alone does not determine causality or the next asset return.", ()),
                (ConclusionLevel.WHAT_WOULD_CHANGE_VIEW, "A documented revision, a different event window, or a pre-specified later test period could change the view.", (quant_evidence_id, release_evidence.evidence_id)),
            ),
            limitations=("Historical association is not causality or a forecast.", *response.limitations),
        )
        prediction = predict_reveal_explain(
            prompt="Before seeing the result, what should a fixed historical test be able to establish?",
            prediction="It can describe the supplied historical sample, but it cannot guarantee the next outcome.",
            result=evaluation,
            explanation="The normalized result is evidence about this pre-specified sample; warnings and limitations bound the interpretation.",
            evidence_reference=response.quant_run_id,
            require_grounding=True,
        )
        card = make_learning_card(
            concept="CPI Evidence and Historical Association",
            definition="A CPI release is a source-bound observation; a historical quantitative result describes a specified sample and does not prove causality.",
            formula="inflation_t = CPI_t / CPI_{t-1} - 1",
            result_context={"evidence_reference": quant_evidence_id, "metrics": metrics, "limitations": list(response.limitations), "interpretation": "Read the mechanism as a hypothesis to test, not a prediction."},
            limitation="The event and quant result remain bounded by source timing, revision uncertainty, sample design, and no-causality limits.",
            interpretation="The result is descriptive evidence for the fixed historical experiment.",
            common_misconception="A hot CPI release means stocks must fall.",
            follow_up_question="Which later evidence would distinguish the proposed mechanism from other explanations?",
        )
        learning_state = self.learning_store.record_encounter(user_id, card, confidence=0.0)
        show = tuple(item for claim in all_claims for item in bundle.show_evidence(claim.claim_id))
        self._persist_vertical_slice(
            source=source,
            release=release,
            capture=captured,
            observations=parsed.observations,
            event=event,
            evidence=all_evidence,
            claims=all_claims,
            concepts=concepts,
            quant_evidence_id=quant_evidence_id,
            card=card,
            user_id=user_id,
        )
        nsa = next((item for item in parsed.observations if item.series_id == "CUUR0000SA0" and item.reference_period == release.reference_period), None)
        change = "The captured release includes a separately identified reference period and publication bound."
        if nsa:
            change = f"The unadjusted CPI-U index is {nsa.latest.value:.3f}; its publication bound is {nsa.latest.published_at}."
        return ProductJourney(
            user_id=user_id,
            event=event,
            claims=all_claims,
            evidence=all_evidence,
            show_evidence=show,
            what_happened=f"BLS published a CPI release for {event.reference_period}.",
            what_changed=change,
            why_it_may_matter=why,
            what_we_know=" ".join(claim.text for claim in claims),
            evidence_suggests=ladder.level(ConclusionLevel.EVIDENCE_SUGGESTS).text,
            plausible=ladder.level(ConclusionLevel.PLAUSIBLE).text,
            unknown=ladder.level(ConclusionLevel.UNKNOWN).text,
            what_would_change_view=ladder.level(ConclusionLevel.WHAT_WOULD_CHANGE_VIEW).text,
            what_to_watch_next="Watch the next official CPI release, any documented revision, and the pre-specified later test window.",
            knowledge_bridge=bridge,
            test_idea={"hypothesis": "A fixed historical momentum experiment can provide bounded context.", "event_id": event.event_id, "request_id": response.request_id},
            quant_evidence=response.to_dict(),
            conclusion_ladder=ladder,
            predict_reveal_explain=prediction,
            learning_card=card,
            learning_state=learning_state,
        )


__all__ = ["ProductJourney", "UnderstandingEngine"]
