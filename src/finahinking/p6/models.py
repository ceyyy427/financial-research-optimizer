"""Typed, serializable records used by the guided P6 workflow.

The P6 layer is deliberately data oriented.  These records describe a
question and a proposed experiment; they do not execute code or hold foreign
library objects.  Constructors perform the small amount of validation needed
to keep a session auditable and deterministic.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


def _safe(value: Any, *, reject_locations: bool = True) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        forbidden = {
            "__import__", "__code__", "__class__", "__globals__", "callable", "eval", "exec", "import", "imports", "module",
            "path", "file_path", "source", "source_code", "generated_python",
            "generated_shell", "shell_command", "subprocess", "delete", "delete_artifact",
            "rewrite_provenance", "package_install", "command", "adapter", "adapter_name",
        }
        for key, item in value.items():
            key_text = str(key)
            if not isinstance(key, str):
                raise TypeError("payload keys must be text")
            if key_text.casefold() in forbidden:
                raise ValueError("payload contains an executable or mutation directive")
            normalized[key_text] = _safe(item, reject_locations=reject_locations)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_safe(v, reject_locations=reject_locations) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        lowered = value.casefold()
        forbidden_tokens = ("eval(", "exec(", "pip install", "shell command", "rewrite provenance", "delete artifact", "os.system", "subprocess", "generated python", "generated shell")
        if any(token in lowered for token in forbidden_tokens) or (reject_locations and any(token in lowered for token in ("https://", "http://", "file://"))):
            raise ValueError("payload contains an executable or mutation directive")
        return value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("payload contains a non-finite number")
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported value type: {type(value).__name__}")


def _json(value: Any) -> str:
    return json.dumps(_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _optional_identifier(value: Any, name: str) -> str | None:
    normalized = _optional_text(value, name)
    if normalized is not None and not _IDENTIFIER.fullmatch(normalized):
        raise ValueError(f"{name} must be a bounded identifier")
    return normalized


def _as_tuple(values: Any, name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    try:
        return tuple(_required_text(value, name) for value in values)
    except TypeError as exc:
        raise TypeError(f"{name} must be a sequence of text") from exc


def _nested(value: Any) -> Any:
    """Serialize one of the small P6 records without exposing foreign objects."""

    if hasattr(value, "to_dict"):
        return value.to_dict()
    return _safe(value)


def _result_safe(value: Any) -> Any:
    """Validate normalized evidence without treating provenance URLs as code.

    Tool results may legitimately contain an offline ``source_url`` or other
    textual provenance, but they must never carry callables, foreign objects,
    sets, or non-finite numbers across the typed response boundary.
    """

    forbidden_keys = {
        "__import__", "__code__", "__class__", "__globals__", "callable", "eval", "exec", "import", "imports", "module",
        "source_code", "generated_python", "generated_shell", "shell_command", "subprocess", "delete_artifact",
        "rewrite_provenance", "package_install", "command",
    }
    forbidden_tokens = (
        "eval(", "exec(", "pip install", "shell command", "rewrite provenance", "delete artifact",
        "os.system", "subprocess", "generated python", "generated shell",
    )
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("result mapping keys must be text")
            if key.casefold() in forbidden_keys:
                raise ValueError("result contains an executable or mutation directive")
            normalized[key] = _result_safe(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_result_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("result contains a non-finite number")
        return value
    if isinstance(value, str):
        if any(token in value.casefold() for token in forbidden_tokens):
            raise ValueError("result contains an executable or mutation directive")
        return value
    if isinstance(value, (int, bool)) or value is None:
        return value
    if callable(value):
        raise TypeError("result cannot contain callables")
    raise TypeError(f"unsupported result value type: {type(value).__name__}")


class TaskCategory(str, Enum):
    ANSWER = "ANSWER"
    GUIDE = "GUIDE"
    QUESTION = "QUESTION"
    EVIDENCE = "EVIDENCE"
    QUANT = "QUANT"
    HISTORY = "HISTORY"
    LEARN = "LEARN"
    STAND_BACK = "STAND_BACK"


class P6State(str, Enum):
    QUESTION_RECEIVED = "QUESTION_RECEIVED"
    CLASSIFIED = "CLASSIFIED"
    HYPOTHESIS_PROPOSED = "HYPOTHESIS_PROPOSED"
    EXPERIMENT_PROPOSED = "EXPERIMENT_PROPOSED"
    ASSUMPTIONS_ACCEPTED = "ASSUMPTIONS_ACCEPTED"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    EVIDENCE_READY = "EVIDENCE_READY"
    EXPLANATION_READY = "EXPLANATION_READY"
    LEARNING_READY = "LEARNING_READY"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ClaimType(str, Enum):
    USER_CLAIM = "USER CLAIM"
    SYSTEM_HYPOTHESIS = "SYSTEM HYPOTHESIS"
    EMPIRICAL_RESULT = "EMPIRICAL RESULT"
    INTERPRETATION = "INTERPRETATION"


@dataclass(frozen=True)
class ResearchQuestion:
    question: str
    user_id: str | None = None
    question_id: str | None = None
    category: TaskCategory | None = None
    normalized_intent: str | None = None
    created_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "question", _required_text(self.question, "question"))
        from .security import validate_untrusted_text

        validate_untrusted_text(self.question)
        if self.user_id is not None:
            object.__setattr__(self, "user_id", _optional_identifier(self.user_id, "user_id"))
        if self.question_id is not None:
            object.__setattr__(self, "question_id", _optional_identifier(self.question_id, "question_id"))
        if self.category is not None and not isinstance(self.category, TaskCategory):
            object.__setattr__(self, "category", TaskCategory(self.category))
        if self.normalized_intent is not None:
            object.__setattr__(self, "normalized_intent", _required_text(self.normalized_intent, "normalized_intent"))
            validate_untrusted_text(self.normalized_intent)
        if self.created_at is not None:
            object.__setattr__(self, "created_at", _required_text(self.created_at, "created_at"))
            validate_untrusted_text(self.created_at)

    @property
    def text(self) -> str:
        return self.question

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "question": self.question, "user_id": self.user_id,
                "question_id": self.question_id, "category": self.category.value if self.category else None,
                "normalized_intent": self.normalized_intent, "created_at": self.created_at}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Universe:
    name: str
    assets: tuple[str, ...] = ()
    inclusion_rule: str = ""
    point_in_time: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "universe"))
        assets = tuple(_required_text(item, "asset") for item in self.assets)
        if len(set(assets)) != len(assets):
            raise ValueError("universe assets must be unique")
        object.__setattr__(self, "assets", assets)
        if not isinstance(self.inclusion_rule, str):
            raise TypeError("inclusion_rule must be text")
        from .security import validate_untrusted_text

        if self.inclusion_rule:
            validate_untrusted_text(self.inclusion_rule)
        if not isinstance(self.point_in_time, bool):
            raise TypeError("point_in_time must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "assets": list(self.assets), "inclusion_rule": self.inclusion_rule,
                "point_in_time": self.point_in_time}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Period:
    start: str
    end: str

    def __post_init__(self) -> None:
        start = _required_text(self.start, "period start")
        end = _required_text(self.end, "period end")
        from .security import validate_untrusted_text

        validate_untrusted_text(start)
        validate_untrusted_text(end)
        # ISO dates sort lexicographically.  For richer timestamps, compare
        # parsed values when possible and leave domain-specific formats intact.
        try:
            if datetime.fromisoformat(start) >= datetime.fromisoformat(end):
                raise ValueError("period start must precede period end")
        except ValueError as exc:
            if "period start" in str(exc):
                raise
            if start >= end:
                raise ValueError("period start must precede period end") from exc
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    def to_dict(self) -> dict[str, str]:
        return {"start": self.start, "end": self.end}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Factor:
    name: str
    definition: str = ""
    formula: str = ""
    lookback: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "factor"))
        for name in ("definition", "formula"):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be text")
        from .security import validate_untrusted_text

        if self.definition:
            validate_untrusted_text(self.definition)
        if self.formula:
            validate_untrusted_text(self.formula)
        if self.lookback is not None and (isinstance(self.lookback, bool) or self.lookback < 1):
            raise ValueError("lookback must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "definition": self.definition, "formula": self.formula, "lookback": self.lookback}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Benchmark:
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "benchmark"))
        from .security import validate_untrusted_text

        validate_untrusted_text(self.name)

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class KnownAssumptions:
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "assumptions", tuple(_required_text(v, "assumption") for v in self.assumptions))
        object.__setattr__(self, "limitations", tuple(_required_text(v, "limitation") for v in self.limitations))
        from .security import validate_untrusted_text

        for value in (*self.assumptions, *self.limitations):
            validate_untrusted_text(value)

    def to_dict(self) -> dict[str, list[str]]:
        return {"assumptions": list(self.assumptions), "limitations": list(self.limitations)}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


def _period_value(value: Any, name: str) -> Period | None:
    if value is None:
        return None
    if isinstance(value, Period):
        return value
    if isinstance(value, Mapping):
        return Period(str(value["start"]), str(value["end"]))
    if isinstance(value, str) and "/" in value:
        start, end = value.split("/", 1)
        return Period(start, end)
    raise TypeError(f"{name} must be a Period or start/end mapping")


@dataclass(frozen=True)
class EvaluationBoundary:
    """Small P6 view of the P5.5 train/select/evaluate boundary.

    The boundary is metadata at planning time.  A concrete P5.5 ``OOSPlan``
    remains authoritative when a quant service executes the experiment.
    """

    test_period: Period
    training_period: Period | None = None
    validation_period: Period | None = None
    configuration_fingerprint: str | None = None
    method: str = "later_test_window"

    def __post_init__(self) -> None:
        test = _period_value(self.test_period, "test_period")
        training = _period_value(self.training_period, "training_period")
        validation = _period_value(self.validation_period, "validation_period")
        if test is None:
            raise ValueError("test_period is required")
        if training and training.end > test.start:
            raise ValueError("training and test periods must not overlap")
        if validation and validation.end > test.start:
            raise ValueError("validation and test periods must not overlap")
        if training and validation and training.end > validation.start:
            raise ValueError("training and validation periods must be chronological")
        object.__setattr__(self, "test_period", test)
        object.__setattr__(self, "training_period", training)
        object.__setattr__(self, "validation_period", validation)
        object.__setattr__(self, "configuration_fingerprint", _optional_text(self.configuration_fingerprint, "configuration_fingerprint"))
        object.__setattr__(self, "method", _required_text(self.method, "method"))
        from .security import validate_untrusted_text

        validate_untrusted_text(self.method)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "training_period": self.training_period.to_dict() if self.training_period else None,
            "validation_period": self.validation_period.to_dict() if self.validation_period else None,
            "test_period": self.test_period.to_dict(),
            "configuration_fingerprint": self.configuration_fingerprint,
        }

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class AssumptionReview:
    """Auditable human decision attached to a material experiment plan."""

    accepted: bool
    assumptions: tuple[str, ...] = ()
    material_changes: tuple[str, ...] = ()
    reviewer: str | None = None
    decision_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise TypeError("accepted must be boolean")
        object.__setattr__(self, "assumptions", _as_tuple(self.assumptions, "assumption"))
        object.__setattr__(self, "material_changes", _as_tuple(self.material_changes, "material change"))
        object.__setattr__(self, "reviewer", _optional_text(self.reviewer, "reviewer"))
        object.__setattr__(self, "decision_id", _optional_text(self.decision_id, "decision_id"))
        from .security import validate_untrusted_text

        for value in (*self.assumptions, *self.material_changes, self.reviewer, self.decision_id):
            if value is not None:
                validate_untrusted_text(value)

    def to_dict(self) -> dict[str, Any]:
        return {"accepted": self.accepted, "assumptions": list(self.assumptions),
                "material_changes": list(self.material_changes), "reviewer": self.reviewer,
                "decision_id": self.decision_id}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class NullHypothesis:
    statement: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "statement", _required_text(self.statement, "null_hypothesis"))

    def __str__(self) -> str:
        return self.statement

    def to_dict(self) -> dict[str, str]:
        return {"statement": self.statement}


@dataclass(frozen=True)
class Hypothesis:
    question: ResearchQuestion | str
    statement: str
    null_hypothesis: str | NullHypothesis
    universe: Universe | str
    period: Period | str
    factor: Factor | str
    benchmark: Benchmark | str
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    statement_type: str = ClaimType.SYSTEM_HYPOTHESIS.value
    claim_type: ClaimType = ClaimType.SYSTEM_HYPOTHESIS
    evaluation_boundary: EvaluationBoundary | Mapping[str, Any] | None = None
    known_assumptions: KnownAssumptions | None = None
    hypothesis_id: str | None = None
    version: int = 1
    created_at: str | None = None
    user_claim: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "statement", _required_text(self.statement, "statement"))
        object.__setattr__(self, "null_hypothesis", str(self.null_hypothesis) if isinstance(self.null_hypothesis, NullHypothesis) else _required_text(self.null_hypothesis, "null_hypothesis"))
        from .security import validate_untrusted_text

        validate_untrusted_text(self.statement)
        validate_untrusted_text(self.null_hypothesis)
        if self.user_claim is not None:
            object.__setattr__(self, "user_claim", _required_text(self.user_claim, "user_claim"))
            validate_untrusted_text(self.user_claim)
        if not isinstance(self.question, ResearchQuestion):
            object.__setattr__(self, "question", ResearchQuestion(str(self.question)))
        for value in (self.universe, self.period, self.factor, self.benchmark):
            if isinstance(value, str):
                validate_untrusted_text(value)
        object.__setattr__(self, "assumptions", _as_tuple(self.assumptions, "assumption"))
        object.__setattr__(self, "limitations", _as_tuple(self.limitations, "limitation"))
        for value in (*self.assumptions, *self.limitations):
            validate_untrusted_text(value)
        statement_type = self.statement_type or ClaimType.SYSTEM_HYPOTHESIS.value
        if statement_type not in {claim.value for claim in ClaimType}:
            raise ValueError("statement_type is not a recognized claim type")
        object.__setattr__(self, "statement_type", statement_type)
        if not isinstance(self.claim_type, ClaimType):
            object.__setattr__(self, "claim_type", ClaimType(self.claim_type))
        if self.known_assumptions is None:
            object.__setattr__(self, "known_assumptions", KnownAssumptions(self.assumptions, self.limitations))
        elif not isinstance(self.known_assumptions, KnownAssumptions):
            raise TypeError("known_assumptions must be a KnownAssumptions record")
        if self.evaluation_boundary is not None and not isinstance(self.evaluation_boundary, EvaluationBoundary):
            if isinstance(self.evaluation_boundary, Mapping):
                boundary = dict(self.evaluation_boundary)
                object.__setattr__(self, "evaluation_boundary", EvaluationBoundary(**boundary))
            else:
                raise TypeError("evaluation_boundary must be an EvaluationBoundary record")
        object.__setattr__(self, "hypothesis_id", _optional_identifier(self.hypothesis_id, "hypothesis_id"))
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("hypothesis version must be a positive integer")
        if self.created_at is not None:
            object.__setattr__(self, "created_at", _required_text(self.created_at, "created_at"))
        object.__setattr__(self, "user_claim", _optional_text(self.user_claim, "user_claim") or self.question.question)

    @property
    def material_assumptions(self) -> tuple[str, ...]:
        return self.assumptions

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "question": self.question.to_dict(), "statement": self.statement,
                "null_hypothesis": self.null_hypothesis, "universe": _nested(self.universe),
                "period": _nested(self.period), "factor": _nested(self.factor),
                "benchmark": _nested(self.benchmark), "assumptions": list(self.assumptions),
                "limitations": list(self.limitations), "known_assumptions": self.known_assumptions.to_dict(),
                "evaluation_boundary": self.evaluation_boundary.to_dict() if self.evaluation_boundary else None,
                "statement_type": self.statement_type, "claim_type": self.claim_type.value,
                "hypothesis_id": self.hypothesis_id, "version": self.version, "created_at": self.created_at,
                "user_claim": self.user_claim}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class ExperimentSpecification:
    question: ResearchQuestion
    hypothesis: Hypothesis
    dataset_id: str
    category: TaskCategory = TaskCategory.QUANT
    benchmark: str = "equal_weight"
    execution_timing: str = "next_period"
    material_assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    tool_name: str = "quant.run_backtest"
    universe: Any | None = None
    factor: Any | None = None
    period: Any | None = None
    evaluation_boundary: EvaluationBoundary | Mapping[str, Any] | None = None
    cost_model: Any | None = None
    slippage_model: Any | None = None
    requested_metrics: tuple[str, ...] = ()
    validity_profile: Mapping[str, Any] = field(default_factory=dict)
    oos_design: Mapping[str, Any] = field(default_factory=dict)
    assumption_review: AssumptionReview | None = None
    specification_id: str | None = None
    version: int = 1
    confirmation_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.question, ResearchQuestion) or not isinstance(self.hypothesis, Hypothesis):
            raise TypeError("question and hypothesis must be typed records")
        dataset_id = _required_text(self.dataset_id, "dataset_id")
        if not _IDENTIFIER.fullmatch(dataset_id):
            raise ValueError("dataset_id must be a bounded identifier")
        object.__setattr__(self, "dataset_id", dataset_id)
        if not isinstance(self.category, TaskCategory):
            object.__setattr__(self, "category", TaskCategory(self.category))
        object.__setattr__(self, "benchmark", _required_text(self.benchmark, "benchmark"))
        object.__setattr__(self, "execution_timing", _required_text(self.execution_timing, "execution_timing"))
        from .security import validate_untrusted_text

        validate_untrusted_text(self.benchmark)
        validate_untrusted_text(self.execution_timing)
        object.__setattr__(self, "material_assumptions", _as_tuple(self.material_assumptions or self.hypothesis.assumptions, "assumption"))
        object.__setattr__(self, "limitations", _as_tuple(self.limitations or self.hypothesis.limitations, "limitation"))
        for value in (*self.material_assumptions, *self.limitations):
            validate_untrusted_text(value)
        object.__setattr__(self, "parameters", copy.deepcopy(_safe(self.parameters)))
        if not isinstance(self.requires_confirmation, bool):
            raise TypeError("requires_confirmation must be boolean")
        if self.evaluation_boundary is not None and not isinstance(self.evaluation_boundary, EvaluationBoundary):
            if isinstance(self.evaluation_boundary, Mapping):
                object.__setattr__(self, "evaluation_boundary", EvaluationBoundary(**dict(self.evaluation_boundary)))
            else:
                raise TypeError("evaluation_boundary must be an EvaluationBoundary record")
        object.__setattr__(self, "requested_metrics", _as_tuple(self.requested_metrics, "metric"))
        object.__setattr__(self, "validity_profile", copy.deepcopy(_safe(dict(self.validity_profile))))
        object.__setattr__(self, "oos_design", copy.deepcopy(_safe(dict(self.oos_design))))
        if self.assumption_review is not None and not isinstance(self.assumption_review, AssumptionReview):
            raise TypeError("assumption_review must be an AssumptionReview record")
        if self.requires_confirmation and self.assumption_review is None:
            raise ValueError("a confirmation-required plan must include an assumption review")
        if self.requires_confirmation and self.assumption_review is not None and self.assumption_review.accepted:
            raise ValueError("a confirmation-required plan cannot already be accepted")
        object.__setattr__(self, "specification_id", _optional_identifier(self.specification_id, "specification_id"))
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("specification version must be a positive integer")
        if self.confirmation_reason is not None:
            object.__setattr__(self, "confirmation_reason", _required_text(self.confirmation_reason, "confirmation_reason"))
        if self.tool_name not in {
            "quant.run_backtest", "quant.run_regression", "quant.evaluate_performance",
            "quant.analyze_risk", "quant.compare_benchmark", "quant.inspect_run",
        }:
            raise ValueError("tool_name is not allow-listed")

    @classmethod
    def from_hypothesis(cls, hypothesis: Hypothesis, *, dataset_id: str) -> ExperimentSpecification:
        from finahinking.quant.validity import ResearchValidity

        question = hypothesis.question if isinstance(hypothesis.question, ResearchQuestion) else ResearchQuestion(str(hypothesis.question))
        return cls(question=question, hypothesis=hypothesis, dataset_id=dataset_id,
                   benchmark=str(hypothesis.benchmark), material_assumptions=hypothesis.assumptions,
                   limitations=hypothesis.limitations, universe=hypothesis.universe,
                   factor=hypothesis.factor, period=hypothesis.period,
                   evaluation_boundary=hypothesis.evaluation_boundary,
                   validity_profile=ResearchValidity.default_p5_5().to_dict(),
                   oos_design={"method": "later_test_window", "status": "planned"})

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema_version": 1, "question": self.question.to_dict(), "hypothesis": self.hypothesis.to_dict(),
                   "dataset_id": self.dataset_id, "category": self.category.value,
                   "benchmark": self.benchmark, "execution_timing": self.execution_timing,
                   "material_assumptions": list(self.material_assumptions), "limitations": list(self.limitations),
                   "parameters": copy.deepcopy(self.parameters), "requires_confirmation": self.requires_confirmation,
                   "tool_name": self.tool_name, "universe": _nested(self.universe) if self.universe is not None else None,
                   "factor": _nested(self.factor) if self.factor is not None else None,
                   "period": _nested(self.period) if self.period is not None else None,
                   "evaluation_boundary": self.evaluation_boundary.to_dict() if self.evaluation_boundary else None,
                   "cost_model": _nested(self.cost_model) if self.cost_model is not None else None,
                   "slippage_model": _nested(self.slippage_model) if self.slippage_model is not None else None,
                   "requested_metrics": list(self.requested_metrics), "validity_profile": copy.deepcopy(self.validity_profile),
                   "oos_design": copy.deepcopy(self.oos_design),
                   "assumption_review": self.assumption_review.to_dict() if self.assumption_review else None,
                   "specification_id": self.specification_id, "version": self.version,
                   "confirmation_reason": self.confirmation_reason}
        return {**payload, "fingerprint": _digest(payload)}

    @property
    def fingerprint(self) -> str:
        payload = self.to_dict()
        return payload["fingerprint"]

    @property
    def frozen_configuration_fingerprint(self) -> str | None:
        return self.evaluation_boundary.configuration_fingerprint if self.evaluation_boundary else None


@dataclass(frozen=True)
class TypedToolRequest:
    tool_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    research_run_id: str | None = None
    quant_run_id: str | None = None
    request_id: str | None = None
    experiment_fingerprint: str | None = None
    assumptions_accepted: bool = False
    provenance_context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", _required_text(self.tool_name, "tool_name"))
        if not isinstance(self.parameters, Mapping):
            raise TypeError("parameters must be a mapping")
        object.__setattr__(self, "parameters", copy.deepcopy(_safe(self.parameters)))
        object.__setattr__(self, "research_run_id", _optional_text(self.research_run_id, "research_run_id"))
        object.__setattr__(self, "quant_run_id", _optional_text(self.quant_run_id, "quant_run_id"))
        object.__setattr__(self, "request_id", _optional_identifier(self.request_id, "request_id"))
        object.__setattr__(self, "experiment_fingerprint", _optional_text(self.experiment_fingerprint, "experiment_fingerprint"))
        if self.experiment_fingerprint is not None:
            try:
                int(self.experiment_fingerprint, 16)
            except ValueError as exc:
                raise ValueError("experiment_fingerprint is invalid") from exc
            if len(self.experiment_fingerprint) != 64:
                raise ValueError("experiment_fingerprint is invalid")
        if not isinstance(self.assumptions_accepted, bool):
            raise TypeError("assumptions_accepted must be boolean")
        if not isinstance(self.provenance_context, Mapping):
            raise TypeError("provenance_context must be a mapping")
        object.__setattr__(self, "provenance_context", copy.deepcopy(_safe(dict(self.provenance_context))))

    @property
    def resolved_request_id(self) -> str:
        if self.request_id:
            return self.request_id
        seed = {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "research_run_id": self.research_run_id,
            "quant_run_id": self.quant_run_id,
            "experiment_fingerprint": self.experiment_fingerprint,
            "assumptions_accepted": self.assumptions_accepted,
            "provenance_context": dict(self.provenance_context),
        }
        return f"p6-request-{_digest(seed)[:16]}"

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": 1,
            "tool_name": self.tool_name,
            "parameters": copy.deepcopy(self.parameters),
            "research_run_id": self.research_run_id,
            "quant_run_id": self.quant_run_id,
            "request_id": self.resolved_request_id,
            "experiment_fingerprint": self.experiment_fingerprint,
            "assumptions_accepted": self.assumptions_accepted,
            "provenance_context": copy.deepcopy(dict(self.provenance_context)),
        }
        return {**payload, "fingerprint": self.fingerprint} if include_fingerprint else payload


@dataclass(frozen=True)
class TypedToolResponse:
    tool_name: str
    status: str
    result: Mapping[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    research_run_id: str | None = None
    quant_run_id: str | None = None
    evidence_reference: str | None = None
    request_id: str | None = None
    artifact_fingerprint: str | None = None
    result_fingerprint: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    failure_code: str | None = None
    message: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", _required_text(self.tool_name, "tool_name"))
        status = self.status.value if isinstance(self.status, Enum) else _required_text(self.status, "status")
        allowed = {"SUCCEEDED", "REJECTED", "FAILED", "UNAVAILABLE"}
        if status not in allowed:
            raise ValueError("status is not a recognized tool status")
        object.__setattr__(self, "status", status)
        if self.result is not None:
            if not isinstance(self.result, Mapping):
                raise TypeError("result must be a mapping")
            object.__setattr__(self, "result", _result_safe(self.result))
        from .security import validate_untrusted_text

        normalized_warnings = tuple(str(value) for value in self.warnings)
        normalized_limitations = tuple(str(value) for value in self.limitations)
        for value in (*normalized_warnings, *normalized_limitations):
            validate_untrusted_text(value)
        object.__setattr__(self, "warnings", normalized_warnings)
        object.__setattr__(self, "limitations", normalized_limitations)
        if not isinstance(self.provenance, Mapping):
            raise TypeError("provenance must be a mapping")
        object.__setattr__(self, "provenance", _result_safe(self.provenance))
        if self.failure_code is not None:
            failure = self.failure_code.value if isinstance(self.failure_code, Enum) else _required_text(self.failure_code, "failure_code")
            if failure not in {
                "UNKNOWN_TOOL", "UNSAFE_REQUEST", "INVALID_REQUEST", "NOT_IMPLEMENTED",
                "EXECUTION_ERROR", "ADAPTER_UNAVAILABLE",
            }:
                raise ValueError("failure_code is not recognized")
            object.__setattr__(self, "failure_code", failure)
        if status in {"REJECTED", "FAILED", "UNAVAILABLE"} and not self.failure_code:
            raise ValueError("failed responses require failure_code")
        if status == "SUCCEEDED" and self.failure_code is not None:
            raise ValueError("successful responses cannot carry failure_code")
        if self.request_id is not None:
            object.__setattr__(self, "request_id", _optional_identifier(self.request_id, "request_id"))
        for name in ("research_run_id", "quant_run_id", "evidence_reference", "artifact_fingerprint", "result_fingerprint"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _optional_identifier(value, name))
        if not isinstance(self.message, str):
            raise TypeError("message must be text")
        validate_untrusted_text(self.message) if self.message else None

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "tool_name": self.tool_name, "status": self.status, "result": copy.deepcopy(self.result),
                "warnings": list(self.warnings), "limitations": list(self.limitations),
                "research_run_id": self.research_run_id, "quant_run_id": self.quant_run_id,
                "evidence_reference": self.evidence_reference, "request_id": self.request_id,
                "artifact_fingerprint": self.artifact_fingerprint, "result_fingerprint": self.result_fingerprint,
                "provenance": copy.deepcopy(dict(self.provenance)), "failure_code": self.failure_code,
                "message": self.message}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


__all__ = ["AssumptionReview", "Benchmark", "ClaimType", "EvaluationBoundary",
           "ExperimentSpecification", "Factor", "Hypothesis", "KnownAssumptions",
           "NullHypothesis", "P6State", "Period", "ResearchQuestion", "TaskCategory",
           "TypedToolRequest", "TypedToolResponse", "Universe"]
