"""Deterministic P6 guided research workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .audit import GuidedSessionAudit
from .classifier import classify_question
from .explanation import ExplanationRecord, explain_result
from .gateway import P6QuantGateway
from .hypothesis import build_hypothesis
from .learning import LearningCard, LearningStore, make_learning_card
from .models import P6State, ResearchQuestion, TaskCategory, TypedToolRequest
from .planner import plan_experiment
from .security import validate_untrusted_text
from .state_machine import GuidedStateMachine


@dataclass(frozen=True)
class GuidedResearchResult:
    audit: GuidedSessionAudit
    question: ResearchQuestion
    hypothesis: Any
    experiment: Any
    tool_response: Any
    explanation: ExplanationRecord
    learning_card: LearningCard
    learning_state: Any | None = None


class GuidedResearchError(RuntimeError):
    """A bounded workflow failure carrying its terminal audit record."""

    def __init__(self, message: str, *, audit: GuidedSessionAudit) -> None:
        super().__init__(message)
        self.audit = audit


class GuidedResearchService:
    """Orchestrate one bounded question-to-learning session."""

    def __init__(self, gateway: P6QuantGateway | None = None, learning_store: LearningStore | None = None) -> None:
        self.gateway = gateway or P6QuantGateway()
        self.learning_store = learning_store or LearningStore()
        self.last_audit: GuidedSessionAudit | None = None

    @staticmethod
    def _terminal_failure(audit: GuidedSessionAudit, *, state: str, reason: str) -> GuidedResearchError:
        terminal = audit.record_terminal(state, reason=reason)
        return GuidedResearchError(reason, audit=terminal)

    @staticmethod
    def _rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a DataFrame")
        rows = json.loads(frame.to_json(orient="records", date_format="iso"))
        if not isinstance(rows, list):
            raise TypeError("frame did not serialize to records")
        return rows

    def run_momentum(self, user_id: str, question_text: str, frame: pd.DataFrame) -> GuidedResearchResult:
        validate_untrusted_text(question_text)
        question = ResearchQuestion(question_text, user_id=user_id)
        classification = classify_question(question)
        if classification.category is not TaskCategory.QUANT:
            raise ValueError("the guided momentum workflow requires a QUANT question")
        machine = GuidedStateMachine()
        audit = GuidedSessionAudit.start(question.question, user_id=user_id)
        self.last_audit = audit
        machine.transition(P6State.CLASSIFIED)
        audit = audit.record_classification(classification.category)
        hypothesis = build_hypothesis(question)
        machine.transition(P6State.HYPOTHESIS_PROPOSED)
        audit = audit.record_hypothesis(hypothesis)
        experiment = plan_experiment(hypothesis, dataset_id="p6-panel")
        self.gateway.register_plan(experiment)
        machine.transition(P6State.EXPERIMENT_PROPOSED)
        audit = audit.record_experiment(experiment)
        # The default fixed experiment has no material changes, so the existing
        # product policy permits an automatic assumption acceptance.
        if experiment.requires_confirmation:
            failure = self._terminal_failure(
                audit,
                state=P6State.REJECTED.value,
                reason="material assumptions require human confirmation",
            )
            self.last_audit = failure.audit
            raise failure
        machine.transition(P6State.ASSUMPTIONS_ACCEPTED)
        audit = audit.record_assumptions(experiment.material_assumptions)
        request = TypedToolRequest(
            "quant.run_backtest",
            {
                "rows": self._rows(frame),
                "question": question.question,
                "hypothesis": hypothesis.statement,
            },
            request_id=f"p6-momentum-{user_id}",
            experiment_fingerprint=experiment.fingerprint,
            assumptions_accepted=True,
            provenance_context={"workflow": "guided-momentum-v1"},
        )
        response = self.gateway.execute(request)
        if response.status != "SUCCEEDED":
            failure = self._terminal_failure(
                audit,
                state=P6State.FAILED.value,
                reason=response.message or "quant tool did not complete",
            )
            self.last_audit = failure.audit
            raise failure
        machine.transition(P6State.TOOL_EXECUTED)
        audit = audit.record_tool_call(
            "quant.run_backtest",
            request_id=response.request_id,
            request_fingerprint=request.fingerprint,
            experiment_fingerprint=experiment.fingerprint,
            status=response.status,
        )
        machine.transition(P6State.EVIDENCE_READY)
        evidence_reference = response.quant_run_id or response.result_fingerprint or "quant-evidence"
        audit = audit.record_evidence(
            evidence_reference,
            research_run_id=response.research_run_id,
            quant_run_id=response.quant_run_id,
            artifact_id=(response.result.get("artifact", {}).get("artifact_id")
                         if isinstance(response.result, dict) else None),
            result_fingerprint=response.result_fingerprint,
            evidence_kind="QuantRun",
            warnings=tuple(response.warnings),
            limitations=tuple(response.limitations),
        )
        evaluation = response.result["evaluation"]
        explanation = explain_result(
            question=question.question,
            tested="A fixed cross-sectional lagged-momentum portfolio with next-period execution and explicit costs.",
            data_used="A point-in-time long-form panel with date, asset, close, and available_at.",
            normalized_result=evaluation,
            evidence_reference=evidence_reference,
            evidence_kind="QuantRun",
            supports="The result describes whether the fixed historical experiment showed separation after the stated costs.",
            does_not_support="It does not support a forecast, causality, institutional execution claim, or a trading recommendation.",
            limitations=tuple(response.limitations),
            concepts=("Momentum", "Turnover", "Out-of-sample testing"),
            warnings=tuple(response.warnings),
        )
        machine.transition(P6State.EXPLANATION_READY)
        audit = audit.record_explanation(explanation.version)
        total_return = evaluation.get("metrics", {}).get("total_return")
        card = make_learning_card(
            concept="Momentum",
            definition="A ranking of trailing returns measured before the next-period execution.",
            formula="p_t / p_{t-k} - 1",
            result_context={"total_return": total_return, "evidence_reference": evidence_reference,
                            "warnings": list(response.warnings), "limitations": list(response.limitations)},
            limitation="Historical evidence is not a forecast; realism warnings remain material: " + "; ".join(response.warnings),
            interpretation="The observed return belongs to this fixed historical experiment only.",
            common_misconception="A profitable backtest guarantees future performance.",
            follow_up_question="What would you want to verify in a later out-of-sample period?",
        )
        learning_state = self.learning_store.record_encounter(user_id, card, confidence=0.0)
        machine.transition(P6State.LEARNING_READY)
        audit = audit.record_learning(concept_id=card.concept, card_fingerprint=card.fingerprint)
        self.last_audit = audit
        return GuidedResearchResult(audit, question, hypothesis, experiment, response, explanation, card, learning_state)

    def run_regression(
        self,
        user_id: str,
        question_text: str,
        frame: pd.DataFrame,
        *,
        target: str,
        features: tuple[str, ...] | list[str],
    ) -> GuidedResearchResult:
        validate_untrusted_text(question_text)
        question = ResearchQuestion(question_text, user_id=user_id)
        classification = classify_question(question)
        if classification.category is not TaskCategory.QUANT:
            raise ValueError("the guided regression workflow requires a QUANT question")
        machine = GuidedStateMachine()
        audit = GuidedSessionAudit.start(question.question, user_id=user_id).record_classification(classification.category)
        self.last_audit = audit
        machine.transition(P6State.CLASSIFIED)
        hypothesis = build_hypothesis(question)
        machine.transition(P6State.HYPOTHESIS_PROPOSED)
        audit = audit.record_hypothesis(hypothesis)
        experiment = plan_experiment(
            hypothesis,
            dataset_id="p6-regression",
            benchmark="equal_weight",
            tool_name="quant.run_regression",
        )
        self.gateway.register_plan(experiment)
        machine.transition(P6State.EXPERIMENT_PROPOSED)
        audit = audit.record_experiment(experiment)
        machine.transition(P6State.ASSUMPTIONS_ACCEPTED)
        audit = audit.record_assumptions(experiment.material_assumptions)
        request = TypedToolRequest(
            "quant.run_regression",
            {
                "rows": self._rows(frame),
                "target": target,
                "features": list(features),
                "question": question.question,
                "hypothesis": hypothesis.statement,
            },
            experiment_fingerprint=experiment.fingerprint,
            assumptions_accepted=True,
            provenance_context={"workflow": "guided-regression-v1"},
        )
        response = self.gateway.execute(request)
        if response.status != "SUCCEEDED":
            failure = self._terminal_failure(
                audit,
                state=P6State.FAILED.value,
                reason=response.message or "regression adapter is unavailable",
            )
            self.last_audit = failure.audit
            raise failure
        machine.transition(P6State.TOOL_EXECUTED)
        audit = audit.record_tool_call(
            "quant.run_regression",
            request_id=response.request_id,
            request_fingerprint=request.fingerprint,
            experiment_fingerprint=experiment.fingerprint,
            status=response.status,
        )
        machine.transition(P6State.EVIDENCE_READY)
        evidence_reference = response.quant_run_id or "regression-evidence"
        audit = audit.record_evidence(
            evidence_reference,
            research_run_id=response.research_run_id,
            quant_run_id=response.quant_run_id,
            artifact_id=(response.result.get("artifact_id")
                         if isinstance(response.result, dict) and response.result.get("artifact_id")
                         else (f"artifact-{response.quant_run_id}" if response.quant_run_id else None)),
            result_fingerprint=response.result_fingerprint,
            evidence_kind="RegressionResult",
            warnings=tuple(response.warnings),
            limitations=tuple(response.limitations),
        )
        explanation = explain_result(
            question=question.question,
            tested="An approved ordinary-least-squares sensitivity specification.",
            data_used="The supplied aligned target and feature observations.",
            normalized_result=response.result,
            evidence_reference=evidence_reference,
            evidence_kind="RegressionResult",
            supports="The normalized coefficient describes historical linear association in the supplied sample.",
            does_not_support="It does not establish causality, stability, or future returns.",
            limitations=tuple(response.limitations),
            concepts=("Regression coefficient", "Beta", "Uncertainty"),
            warnings=tuple(response.warnings),
        )
        machine.transition(P6State.EXPLANATION_READY)
        audit = audit.record_explanation(explanation.version)
        beta = response.result.get("parameters", {}).get(features[0]) if response.result else None
        card = make_learning_card(
            concept="Regression Coefficient",
            definition="The fitted change in the target associated with one unit of a feature, conditional on the specification.",
            formula="y = intercept + beta * x + error",
            result_context={"beta": beta, "uncertainty": response.result.get("uncertainty", {}) if response.result else {},
                            "evidence_reference": evidence_reference, "warnings": list(response.warnings),
                            "limitations": list(response.limitations)},
            limitation="A coefficient is an association under a model, not proof of causality. " + "; ".join(response.warnings),
            interpretation="The coefficient describes fitted historical association under this specification.",
            common_misconception="A low p-value proves causality.",
            follow_up_question="How might the coefficient change in a later sample?",
        )
        learning_state = self.learning_store.record_encounter(user_id, card, confidence=0.0)
        machine.transition(P6State.LEARNING_READY)
        audit = audit.record_learning(concept_id=card.concept, card_fingerprint=card.fingerprint)
        self.last_audit = audit
        return GuidedResearchResult(audit, question, hypothesis, experiment, response, explanation, card, learning_state)


__all__ = ["GuidedResearchError", "GuidedResearchResult", "GuidedResearchService"]
