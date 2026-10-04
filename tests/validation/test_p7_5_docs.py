from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = (
    "P7_5_EXECUTION_PLAN.md",
    "P7_5_CAPABILITY_MATRIX.md",
    "P7_5_ARCHITECTURE.md",
    "P7_5_KNOWLEDGE_ENGINE.md",
    "P7_5_KNOWLEDGE_SCHEMA.md",
    "P7_5_LEARNING_PATHS.md",
    "P7_5_DATA_MATH_CODE_FINANCE.md",
    "P7_5_INFORMATION_ARCHITECTURE.md",
    "P7_5_DESIGN_SYSTEM.md",
    "P7_5_LOCAL_RUNTIME_DECISION.md",
    "P7_5_USER_JOURNEYS.md",
    "P7_5_ACCESSIBILITY_REVIEW.md",
    "P7_5_PERFORMANCE_REVIEW.md",
    "P7_5_SECURITY_REVIEW.md",
    "P7_5_E2E_REPORT.md",
    "P7_5_FINAL_VALIDATION_REPORT.md",
    "P8_READINESS_REPORT.md",
)


def test_p7_5_document_set_and_independent_reviews_are_complete() -> None:
    for name in REQUIRED:
        path = ROOT / "docs" / "p7_5" / name
        assert path.is_file() and path.read_text(encoding="utf-8").strip(), name
    reviews = sorted((ROOT / "docs" / "p7_5" / "reviews").glob("[A-J]_*.md"))
    assert [path.name[0] for path in reviews] == list("ABCDEFGHIJ")
    assert all("review" in path.read_text(encoding="utf-8").casefold() for path in reviews)


def test_p7_5_docs_state_local_boundaries() -> None:
    combined = "\n".join(
        (ROOT / "docs" / "p7_5" / name).read_text(encoding="utf-8") for name in REQUIRED
    ).casefold()
    assert "sqlite" in combined
    assert "sample" in combined and "offline" in combined
    assert "real-money" in combined
    assert "p7" in combined
