"""Research-only quant contracts, stabilized P5.5 services, and runtime boundaries."""

from .artifacts import Artifact, QuantRun
from .interfaces import (
    BacktestConfig,
    BacktestResult,
    EvaluationReport,
    Strategy,
    StrategyIntent,
    Trade,
)
from .multi_asset import (
    CrossSectionalMomentumConfig,
    MultiAssetDataset,
    MultiAssetExperimentResult,
    run_cross_sectional_momentum_experiment,
)
from .regression import (
    RegressionDependencyUnavailable,
    RegressionExperimentResult,
    run_regression_experiment,
)
from .services import (
    ALLOWED_TOOLS,
    QuantServiceGateway,
    ToolFailureCode,
    ToolRequest,
    ToolResponse,
    ToolStatus,
)
from .splits import (
    EvaluationBoundary,
    OOSPlan,
    OOSResult,
    ParameterSelectionBoundary,
    TestPeriod,
    TrainingPeriod,
    ValidationPeriod,
    evaluate_oos,
)
from .validity import ResearchValidity, ValidityAssessment, ValidityDimension, ValidityStatus

__all__ = [
    "ALLOWED_TOOLS",
    "Artifact",
    "BacktestConfig",
    "BacktestResult",
    "CrossSectionalMomentumConfig",
    "EvaluationBoundary",
    "EvaluationReport",
    "MultiAssetDataset",
    "MultiAssetExperimentResult",
    "OOSPlan",
    "OOSResult",
    "ParameterSelectionBoundary",
    "QuantRun",
    "QuantServiceGateway",
    "RegressionDependencyUnavailable",
    "RegressionExperimentResult",
    "ResearchValidity",
    "Strategy",
    "StrategyIntent",
    "TestPeriod",
    "ToolFailureCode",
    "ToolRequest",
    "ToolResponse",
    "ToolStatus",
    "Trade",
    "TrainingPeriod",
    "ValidationPeriod",
    "ValidityAssessment",
    "ValidityDimension",
    "ValidityStatus",
    "evaluate_oos",
    "run_cross_sectional_momentum_experiment",
    "run_regression_experiment",
]
