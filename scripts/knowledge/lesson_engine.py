"""Turn saved results and evidence into short, non-causal learning lessons."""
from __future__ import annotations

from typing import Any

from .knowledge_registry import get_knowledge_for_metric, get_knowledge_for_model, get_knowledge_for_reason


def build_lesson(*, result: dict[str, Any], claim: dict[str, Any], user_level: str = "beginner") -> dict[str, Any]:
    formula_id = claim.get("formula_id")
    knowledge = get_knowledge_for_model(result.get("forecast", {}).get("model", "")) if claim.get("claim_type") == "model_mechanism" else get_knowledge_for_metric(formula_id or "")
    if claim.get("claim_type") in {"uncertainty_explanation", "failure_boundary"}:
        knowledge = get_knowledge_for_reason(claim.get("statement", ""))
    available = bool(claim.get("evidence_refs") and (claim.get("input_hash") or claim.get("calculation_refs")))
    return {
        "lesson_id": "lesson_" + str(claim.get("claim_id", "unknown")),
        "title": claim.get("title", "研究结果学习卡"),
        "level": user_level,
        "observation": claim.get("statement", "not_available") if available else "not_available：本次运行没有足够的可追溯证据。",
        "mechanism": knowledge.get("definition", "not_available") if available else "not_available",
        "formula_ref": formula_id,
        "knowledge_ref": knowledge.get("knowledge_id"),
        "evidence_refs": claim.get("evidence_refs", []),
        "lineage_refs": claim.get("calculation_refs", []),
        "caveat": (claim.get("caveats") or ["not_available"])[0],
        "next_question": (claim.get("next_check") or "下一次刷新后是否仍然成立？"),
        "status": "available" if available else "not_available",
    }
