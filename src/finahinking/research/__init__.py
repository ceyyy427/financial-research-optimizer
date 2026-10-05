"""Governed, offline-first research-agent contracts and orchestration hooks."""

from finahinking.factors.registry import (
    FactorHealth,
    FactorHealthStatus,
    FactorMetadata,
    FactorRegistry,
)

from .contracts import (
    AgentReport,
    CheckpointIdentity,
    DecisionCard,
    FailureKind,
    ProviderSelection,
    ReportManifest,
    ResearchPlan,
    ResearchRequest,
    ResearchRunResult,
    ResearchRunState,
    ResearchState,
    RiskReview,
    RunEvent,
    stable_digest,
    to_jsonable,
    validate_transition,
)
from .drivers import CodexInteractiveDriver, CompatibleApiDriver, OfflineDriver, UserApiDriver
from .factor_loop import (
    FactorResearchRound,
    FactorResearchRun,
    FactorResearchState,
    run_factor_research,
)
from .learning import LearningEntry, LearningStore, reconcile_learning, validate_learning_entry
from .reports import (
    BundleVerification,
    ReportBundleWriter,
    render_section_html,
    verify_report_bundle,
)
from .tools import (
    ResearchToolGateway,
    ResearchToolName,
    ResearchToolRequest,
    ResearchToolResponse,
    ResearchToolStatus,
)
from .workflow import AnalystSpec, ResearchOrchestrator, WorkflowLimits

__all__ = [
    "AgentReport",
    "AnalystSpec",
    "BundleVerification",
    "CheckpointIdentity",
    "CodexInteractiveDriver",
    "CompatibleApiDriver",
    "DecisionCard",
    "FactorHealth",
    "FactorHealthStatus",
    "FactorMetadata",
    "FactorRegistry",
    "FactorResearchRound",
    "FactorResearchRun",
    "FactorResearchState",
    "FailureKind",
    "LearningEntry",
    "LearningStore",
    "OfflineDriver",
    "ProviderSelection",
    "ReportBundleWriter",
    "ReportManifest",
    "ResearchOrchestrator",
    "ResearchPlan",
    "ResearchRequest",
    "ResearchRunResult",
    "ResearchRunState",
    "ResearchState",
    "ResearchToolGateway",
    "ResearchToolName",
    "ResearchToolRequest",
    "ResearchToolResponse",
    "ResearchToolStatus",
    "RiskReview",
    "RunEvent",
    "UserApiDriver",
    "WorkflowLimits",
    "reconcile_learning",
    "render_section_html",
    "run_factor_research",
    "stable_digest",
    "to_jsonable",
    "validate_learning_entry",
    "validate_transition",
    "verify_report_bundle",
]
