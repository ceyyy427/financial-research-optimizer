"""P6.6 Strategy Research & Simulation Lab contracts."""

from .compiler import CompiledStrategy, StrategyCompiler, compile_strategy
from .education import (
    CodeSafetyReport,
    EducationalCode,
    StrategyLearningTrace,
    generate_educational_code,
    learning_cards,
    scan_educational_code,
    validate_generated_code,
)
from .features import (
    FeatureRegistry,
    PointInTimeViolation,
    assert_point_in_time,
    builtin_feature_registry,
    feature_graph_for_template,
)
from .models import (
    FeatureDefinition,
    FeatureGraph,
    FeatureNode,
    FeatureVersion,
    StrategyIR,
    StrategyIRNode,
    StrategyReview,
    StrategySpec,
    StrategyVersion,
)
from .strategy import StrategyInterpreter, review_strategy

__all__ = [
    "CodeSafetyReport",
    "CompiledStrategy",
    "EducationalCode",
    "FeatureDefinition",
    "FeatureGraph",
    "FeatureNode",
    "FeatureRegistry",
    "FeatureVersion",
    "PointInTimeViolation",
    "StrategyCompiler",
    "StrategyIR",
    "StrategyIRNode",
    "StrategyInterpreter",
    "StrategyLearningTrace",
    "StrategyReview",
    "StrategySpec",
    "StrategyVersion",
    "assert_point_in_time",
    "builtin_feature_registry",
    "compile_strategy",
    "feature_graph_for_template",
    "generate_educational_code",
    "learning_cards",
    "review_strategy",
    "scan_educational_code",
    "validate_generated_code",
]
