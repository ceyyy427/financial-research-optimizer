"""Guided, human-controlled quant research and learning contracts."""

from .audit import GuidedSessionAudit
from .classifier import Classification, TaskClassifier, classify_question
from .explanation import (
    ExplanationRecord,
    PredictionRevealExplain,
    explain_result,
    predict_reveal_explain,
)
from .gateway import P6QuantGateway, RegressionEvidence
from .grounding import GroundedClaim, claims_from_result, ground_numeric_claim
from .hypothesis import HypothesisBuilder, build_hypothesis, validate_hypothesis
from .learning import (
    LearningCard,
    LearningStore,
    generate_quiz,
    make_learning_card,
    record_misconception,
)
from .models import (
    AssumptionReview,
    Benchmark,
    ClaimType,
    EvaluationBoundary,
    ExperimentSpecification,
    Factor,
    Hypothesis,
    KnownAssumptions,
    NullHypothesis,
    P6State,
    Period,
    ResearchQuestion,
    TaskCategory,
    TypedToolRequest,
    TypedToolResponse,
    Universe,
)
from .planner import ExperimentPlanner, plan_experiment
from .security import validate_agent_text, validate_payload, validate_untrusted_text
from .state_machine import GuidedStateMachine, P6StateMachine
from .workflows import GuidedResearchError, GuidedResearchResult, GuidedResearchService

__all__ = [
    "AssumptionReview",
    "Benchmark",
    "ClaimType",
    "Classification",
    "EvaluationBoundary",
    "ExperimentPlanner",
    "ExperimentSpecification",
    "ExplanationRecord",
    "Factor",
    "GroundedClaim",
    "GuidedResearchError",
    "GuidedResearchResult",
    "GuidedResearchService",
    "GuidedSessionAudit",
    "GuidedStateMachine",
    "Hypothesis",
    "HypothesisBuilder",
    "KnownAssumptions",
    "LearningCard",
    "LearningStore",
    "NullHypothesis",
    "P6QuantGateway",
    "P6State",
    "P6StateMachine",
    "Period",
    "PredictionRevealExplain",
    "RegressionEvidence",
    "ResearchQuestion",
    "TaskCategory",
    "TaskClassifier",
    "TypedToolRequest",
    "TypedToolResponse",
    "Universe",
    "build_hypothesis",
    "claims_from_result",
    "classify_question",
    "explain_result",
    "generate_quiz",
    "ground_numeric_claim",
    "make_learning_card",
    "plan_experiment",
    "predict_reveal_explain",
    "record_misconception",
    "validate_agent_text",
    "validate_hypothesis",
    "validate_payload",
    "validate_untrusted_text",
]
