from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


REQUIRED = (
    "P6_EXECUTION_PLAN.md",
    "P6_ARCHITECTURE.md",
    "P6_TASK_CLASSIFIER.md",
    "P6_HYPOTHESIS_CONTRACT.md",
    "P6_EXPERIMENT_PLANNER.md",
    "P6_TYPED_TOOL_GATEWAY.md",
    "P6_EXPLANATION_CONTRACT.md",
    "P6_CLAIM_GROUNDING_POLICY.md",
    "P6_LEARNING_MODEL.md",
    "P6_AGENT_SECURITY.md",
    "P6_EVALUATION_PLAN.md",
    "P6_FINAL_VALIDATION_REPORT.md",
    "P6_GATE_REVIEW.md",
)


def test_p6_contract_documents_exist_and_preserve_boundaries() -> None:
    combined = ""
    for filename in REQUIRED:
        path = ROOT / "docs" / "p6" / filename
        assert path.is_file(), filename
        text = path.read_text(encoding="utf-8")
        assert text.strip(), filename
        combined += text.casefold()
    for marker in (
        "guided",
        "human-controlled",
        "typed",
        "researchrun",
        "quantrun",
        "ground",
        "learning",
        "misconception",
        "predict",
        "reveal",
        "explain",
        "arbitrary",
        "p7",
        "pass",
    ):
        assert marker in combined
