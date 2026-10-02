"""P6 gateway: the only route from guided orchestration to quant services."""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from finahinking.experiments.models import canonical_json
from finahinking.quant.multi_asset import (
    CrossSectionalMomentumConfig,
    MultiAssetDataset,
    run_cross_sectional_momentum_experiment,
)
from finahinking.quant.regression import (
    RegressionDependencyUnavailable,
    run_regression_experiment,
)
from finahinking.quant.runtime import _code_commit, _dependency_versions
from finahinking.quant.services import ToolFailureCode, ToolResponse, ToolStatus
from finahinking.quant.validity import ResearchValidity

from .models import ExperimentSpecification, TypedToolRequest, TypedToolResponse
from .security import validate_untrusted_text


@dataclass(frozen=True)
class RegressionEvidence:
    parameters: dict[str, float]
    metrics: dict[str, float | None]
    dataset_fingerprint: str
    research_run_id: str
    quant_run_id: str
    uncertainty: dict[str, dict[str, float | None]] | None = None
    artifact_fingerprint: str | None = None
    artifact_id: str | None = None
    validity: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = (
        "Regression is descriptive historical evidence, not causality or investment advice.",
    )

    @property
    def fingerprint(self) -> str:
        payload = self.to_dict(include_fingerprint=False)
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": 1,
            "result_kind": "RegressionResult",
            "parameters": copy.deepcopy(self.parameters),
            "metrics": copy.deepcopy(self.metrics),
            "uncertainty": copy.deepcopy(self.uncertainty or {}),
            "dataset_fingerprint": self.dataset_fingerprint,
            "research_run_id": self.research_run_id,
            "quant_run_id": self.quant_run_id,
            "artifact_id": self.artifact_id,
            "artifact_fingerprint": self.artifact_fingerprint,
            "validity": copy.deepcopy(self.validity or ResearchValidity.default_p5_5().to_dict()),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
        return {**payload, "fingerprint": self.fingerprint} if include_fingerprint else payload


def _safe_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return validate_untrusted_text(value.strip())


_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _normalize_request_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if _REQUEST_ID.fullmatch(normalized) else None


def _response_from_experiment(experiment: Any, request_id: str) -> ToolResponse:
    result = {
        "backtest": experiment.backtest.to_dict(),
        "evaluation": experiment.evaluation.to_dict(),
        "validity": experiment.validity.to_dict(),
        "quant_run": experiment.quant_run.to_dict(),
        "research_run": experiment.research_run.to_dict(),
        "artifact": experiment.artifact.to_dict(),
    }
    # Bind the normalized evaluation to the run identity before it crosses
    # the explanation boundary.  The evaluation's own fingerprint remains
    # verifiable because the grounding verifier recognizes its stable subset.
    result["evaluation"]["quant_run_id"] = experiment.quant_run.quant_run_id
    result["evaluation"]["research_run_id"] = experiment.research_run.run_id
    return ToolResponse(
        request_id=request_id,
        tool_name="quant.run_backtest",
        status=ToolStatus.SUCCEEDED,
        result=result,
        research_run_id=experiment.research_run.run_id,
        quant_run_id=experiment.quant_run.quant_run_id,
        artifact_fingerprint=experiment.artifact.fingerprint,
        result_fingerprint=experiment.backtest.fingerprint,
        provenance={
            "gateway": "finahinking-p6-v1",
            "code_commit": experiment.quant_run.parameters.get("code_commit", _code_commit()),
            "dependency_versions": _dependency_versions(),
            "request_fingerprint": hashlib.sha256(request_id.encode("utf-8")).hexdigest(),
        },
        warnings=experiment.warnings,
        limitations=experiment.limitations,
    )


class P6QuantGateway:
    """Typed façade over the frozen P5.5 services."""

    approved_tools = (
        "quant.run_backtest",
        "quant.run_regression",
        "quant.evaluate_performance",
        "quant.analyze_risk",
        "quant.compare_benchmark",
        "quant.inspect_run",
    )

    def __init__(self) -> None:
        self._records: dict[str, Any] = {}
        self._plans: dict[str, ExperimentSpecification] = {}

    def register_plan(self, specification: ExperimentSpecification) -> str:
        if not isinstance(specification, ExperimentSpecification):
            raise TypeError("experiment specification must be an ExperimentSpecification")
        fingerprint = specification.fingerprint
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValueError("experiment specification must have a valid fingerprint")
        if specification.to_dict().get("fingerprint") != fingerprint:
            raise ValueError("experiment specification fingerprint is not reproducible")
        self._plans[fingerprint] = specification
        return fingerprint

    def _plan_matches(self, fingerprint: str | None, tool_name: str) -> bool:
        if not fingerprint:
            return False
        specification = self._plans.get(fingerprint)
        return bool(
            specification is not None
            and specification.fingerprint == fingerprint
            and specification.tool_name == tool_name
            and specification.assumption_review is not None
            and specification.assumption_review.accepted
        )

    def run_momentum(
        self,
        frame: pd.DataFrame,
        *,
        question: str,
        hypothesis: str,
        config: CrossSectionalMomentumConfig | None = None,
        request_id: str = "p6-momentum",
        experiment_fingerprint: str | None = None,
    ) -> ToolResponse:
        normalized_request_id = _normalize_request_id(request_id)
        if normalized_request_id is None:
            return ToolResponse(
                request_id="p6-invalid-request",
                tool_name="quant.run_backtest",
                status=ToolStatus.REJECTED,
                failure_code=ToolFailureCode.INVALID_REQUEST,
                message="invalid quant request",
            )
        request_id = normalized_request_id
        try:
            if not self._plan_matches(experiment_fingerprint, "quant.run_backtest"):
                raise ValueError("experiment fingerprint is not registered")
            dataset = MultiAssetDataset(frame, provider="fixture", source_url="offline://p6-guided")
            experiment = run_cross_sectional_momentum_experiment(
                dataset,
                config,
                question=_safe_text(question, "question"),
                hypothesis=_safe_text(hypothesis, "hypothesis"),
            )
            self._records[experiment.quant_run.quant_run_id] = experiment.quant_run
            self._records[experiment.research_run.run_id] = experiment.research_run
            self._records[experiment.artifact.artifact_id] = experiment.artifact
            return _response_from_experiment(experiment, request_id)
        except (TypeError, ValueError):
            return ToolResponse(
                request_id=request_id,
                tool_name="quant.run_backtest",
                status=ToolStatus.REJECTED,
                failure_code=ToolFailureCode.INVALID_REQUEST,
                message="invalid quant request",
            )
        except Exception:  # noqa: BLE001 - agent boundary must sanitize domain failures
            return ToolResponse(
                request_id=request_id,
                tool_name="quant.run_backtest",
                status=ToolStatus.FAILED,
                failure_code=ToolFailureCode.EXECUTION_ERROR,
                message="quant service failed",
            )

    def run_regression(
        self,
        frame: pd.DataFrame,
        *,
        target: str,
        features: Sequence[str],
        question: str,
        hypothesis: str,
        request_id: str = "p6-regression",
        experiment_fingerprint: str | None = None,
    ) -> ToolResponse:
        normalized_request_id = _normalize_request_id(request_id)
        if normalized_request_id is None:
            return ToolResponse(
                request_id="p6-invalid-request",
                tool_name="quant.run_regression",
                status=ToolStatus.REJECTED,
                failure_code=ToolFailureCode.INVALID_REQUEST,
                message="invalid regression request",
            )
        request_id = normalized_request_id
        try:
            if not self._plan_matches(experiment_fingerprint, "quant.run_regression"):
                raise ValueError("experiment fingerprint is not registered")
            experiment = run_regression_experiment(
                frame,
                target=target,
                features=features,
                question=_safe_text(question, "question"),
                hypothesis=_safe_text(hypothesis, "hypothesis"),
            )
        except RegressionDependencyUnavailable:
            return ToolResponse(
                request_id=request_id,
                tool_name="quant.run_regression",
                status=ToolStatus.UNAVAILABLE,
                failure_code=ToolFailureCode.ADAPTER_UNAVAILABLE,
                message="approved regression adapter is unavailable in this environment",
            )
        except (TypeError, ValueError):
            return ToolResponse(
                request_id=request_id,
                tool_name="quant.run_regression",
                status=ToolStatus.REJECTED,
                failure_code=ToolFailureCode.INVALID_REQUEST,
                message="invalid regression request",
            )
        except Exception:  # noqa: BLE001 - agent boundary must sanitize domain failures
            return ToolResponse(
                request_id=request_id,
                tool_name="quant.run_regression",
                status=ToolStatus.FAILED,
                failure_code=ToolFailureCode.EXECUTION_ERROR,
                message="regression service failed",
            )
        quant_id = experiment.quant_run.quant_run_id
        research_id = experiment.research_run.run_id
        evidence = RegressionEvidence(
            parameters=experiment.regression.parameters,
            metrics=experiment.regression.metrics,
            uncertainty=experiment.regression.uncertainty,
            dataset_fingerprint=experiment.dataset_fingerprint,
            research_run_id=research_id,
            quant_run_id=quant_id,
            artifact_fingerprint=experiment.artifact.fingerprint,
            artifact_id=experiment.artifact.artifact_id,
            validity=ResearchValidity.default_p5_5().to_dict(),
            warnings=experiment.warnings,
            limitations=experiment.limitations,
        )
        self._records[quant_id] = experiment.quant_run
        self._records[research_id] = experiment.research_run
        self._records[experiment.artifact.artifact_id] = experiment.artifact
        return ToolResponse(
            request_id=request_id,
            tool_name="quant.run_regression",
            status=ToolStatus.SUCCEEDED,
            result=evidence.to_dict(),
            research_run_id=research_id,
            quant_run_id=quant_id,
            artifact_fingerprint=experiment.artifact.fingerprint,
            result_fingerprint=evidence.fingerprint,
            provenance={
                **experiment.provenance,
                "gateway": "finahinking-p6-v1",
                "request_fingerprint": hashlib.sha256(request_id.encode("utf-8")).hexdigest(),
            },
            warnings=experiment.warnings,
            limitations=experiment.limitations,
        )

    def inspect_run(self, run_id: str) -> ToolResponse:
        if _normalize_request_id(run_id) is None:
            return ToolResponse(
                request_id="inspect-invalid-request",
                tool_name="quant.inspect_run",
                status=ToolStatus.REJECTED,
                failure_code=ToolFailureCode.INVALID_REQUEST,
                message="invalid run identifier",
            )
        record = self._records.get(run_id)
        if record is None:
            return ToolResponse(
                request_id=f"inspect-{run_id}",
                tool_name="quant.inspect_run",
                status=ToolStatus.FAILED,
                failure_code=ToolFailureCode.EXECUTION_ERROR,
                message="run was not found",
            )
        payload = record.to_dict() if hasattr(record, "to_dict") else copy.deepcopy(record)
        return ToolResponse(
            request_id=f"inspect-{run_id}",
            tool_name="quant.inspect_run",
            status=ToolStatus.SUCCEEDED,
            result=payload,
            result_fingerprint=getattr(record, "fingerprint", None),
            provenance={"gateway": "finahinking-p6-v1"},
        )

    @staticmethod
    def _frame_from_request(parameters: dict[str, Any]) -> pd.DataFrame:
        rows = parameters.get("rows")
        if not isinstance(rows, list) or not rows or len(rows) > 100_000:
            raise ValueError("rows must be a bounded non-empty list")
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError("rows must contain JSON objects")
        return pd.DataFrame(copy.deepcopy(rows))

    @staticmethod
    def _typed_response(
        response: ToolResponse,
        request_id: str,
        *,
        tool_name: str | None = None,
        request_fingerprint: str | None = None,
        provenance_context: dict[str, Any] | None = None,
    ) -> TypedToolResponse:
        provenance = copy.deepcopy(response.provenance)
        if request_fingerprint:
            provenance["request_fingerprint"] = request_fingerprint
        if provenance_context:
            provenance["request_context"] = copy.deepcopy(provenance_context)
        return TypedToolResponse(
            tool_name or response.tool_name,
            response.status.value,
            result=response.result if isinstance(response.result, dict) else None,
            warnings=response.warnings,
            limitations=response.limitations,
            research_run_id=response.research_run_id,
            quant_run_id=response.quant_run_id,
            evidence_reference=response.quant_run_id or response.research_run_id,
            request_id=request_id,
            artifact_fingerprint=response.artifact_fingerprint,
            result_fingerprint=response.result_fingerprint,
            provenance=provenance,
            failure_code=response.failure_code.value if response.failure_code else None,
            message=response.message,
        )

    def execute(self, request: TypedToolRequest) -> TypedToolResponse:
        if not isinstance(request, TypedToolRequest):
            return TypedToolResponse(
                "unknown",
                "REJECTED",
                failure_code=ToolFailureCode.INVALID_REQUEST.value,
                message="request must be a typed P6 tool request",
            )
        # Frozen dataclasses can still contain mutable dictionaries. Rebuild
        # the envelope at the trust boundary so post-construction mutation
        # cannot bypass payload validation or alter the authorized fingerprint.
        try:
            request = TypedToolRequest(
                request.tool_name,
                dict(request.parameters),
                research_run_id=request.research_run_id,
                quant_run_id=request.quant_run_id,
                request_id=request.request_id,
                experiment_fingerprint=request.experiment_fingerprint,
                assumptions_accepted=request.assumptions_accepted,
                provenance_context=dict(request.provenance_context),
            )
        except (TypeError, ValueError):
            return TypedToolResponse(
                "unknown",
                "REJECTED",
                request_id="p6-invalid-request",
                failure_code=ToolFailureCode.UNSAFE_REQUEST.value,
                message="request failed boundary validation",
            )
        request_id = request.resolved_request_id
        if request.tool_name not in self.approved_tools:
            return TypedToolResponse(
                request.tool_name,
                "REJECTED",
                request_id=request_id,
                failure_code=ToolFailureCode.UNKNOWN_TOOL.value,
                limitations=("tool is not approved",),
            )
        if request.tool_name != "quant.inspect_run" and not request.assumptions_accepted:
            return TypedToolResponse(
                request.tool_name,
                "REJECTED",
                request_id=request_id,
                failure_code=ToolFailureCode.INVALID_REQUEST.value,
                limitations=("assumptions must be accepted before execution",),
            )
        if request.tool_name in {"quant.run_backtest", "quant.run_regression"} and not self._plan_matches(
            request.experiment_fingerprint, request.tool_name
        ):
            return TypedToolResponse(
                request.tool_name,
                "REJECTED",
                request_id=request_id,
                failure_code=ToolFailureCode.INVALID_REQUEST.value,
                limitations=("a registered experiment fingerprint is required",),
            )
        if request.tool_name == "quant.inspect_run":
            run_id = request.parameters.get("run_id")
            if not isinstance(run_id, str) or not run_id.strip():
                return TypedToolResponse(
                    request.tool_name,
                    "REJECTED",
                    request_id=request_id,
                    failure_code=ToolFailureCode.INVALID_REQUEST.value,
                    message="run_id is required for inspection",
                )
            response = self.inspect_run(run_id)
            return self._typed_response(
                response,
                request_id,
                request_fingerprint=request.fingerprint,
                provenance_context=dict(request.provenance_context),
            )
        if request.tool_name not in {"quant.run_backtest", "quant.run_regression"}:
            return TypedToolResponse(
                request.tool_name,
                "REJECTED",
                request_id=request_id,
                failure_code=ToolFailureCode.NOT_IMPLEMENTED.value,
                limitations=("the approved service is not exposed by this P6 fixture gateway",),
            )
        try:
            frame = self._frame_from_request(request.parameters)
            question = request.parameters.get("question", "bounded P6 request")
            hypothesis = request.parameters.get("hypothesis", "pre-specified P6 hypothesis")
            if request.tool_name == "quant.run_backtest":
                raw_config = request.parameters.get("config")
                config = CrossSectionalMomentumConfig(**raw_config) if isinstance(raw_config, dict) else None
                response = self.run_momentum(
                    frame,
                    question=_safe_text(question, "question"),
                    hypothesis=_safe_text(hypothesis, "hypothesis"),
                    config=config,
                    request_id=request_id,
                    experiment_fingerprint=request.experiment_fingerprint,
                )
            elif request.tool_name == "quant.run_regression":
                target = request.parameters.get("target")
                features = request.parameters.get("features")
                if not isinstance(target, str) or not isinstance(features, list):
                    raise ValueError("target and features are required")
                response = self.run_regression(
                    frame,
                    target=target,
                    features=tuple(features),
                    question=_safe_text(question, "question"),
                    hypothesis=_safe_text(hypothesis, "hypothesis"),
                    request_id=request_id,
                    experiment_fingerprint=request.experiment_fingerprint,
                )
            return self._typed_response(
                response,
                request_id,
                request_fingerprint=request.fingerprint,
                provenance_context=dict(request.provenance_context),
            )
        except (TypeError, ValueError):
            return TypedToolResponse(
                request.tool_name,
                "REJECTED",
                request_id=request_id,
                failure_code=ToolFailureCode.INVALID_REQUEST.value,
                message="invalid typed tool parameters",
            )
        except Exception:  # noqa: BLE001 - sanitize all typed gateway failures
            return TypedToolResponse(
                request.tool_name,
                "FAILED",
                request_id=request_id,
                failure_code=ToolFailureCode.EXECUTION_ERROR.value,
                message="typed quant service failed",
            )


__all__ = ["P6QuantGateway", "RegressionEvidence"]
