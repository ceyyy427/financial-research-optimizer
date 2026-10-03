from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = (
    "P7_EXECUTION_PLAN.md",
    "P7_ARCHITECTURE.md",
    "P7_CAPABILITY_MATRIX.md",
    "P7_PRIVACY_MODEL.md",
    "P7_PERMISSION_MODEL.md",
    "P7_PERSONAL_KNOWLEDGE_GRAPH.md",
    "P7_MASTERY_MODEL.md",
    "P7_LEARNING_THREADS.md",
    "P7_RESEARCH_HISTORY.md",
    "P7_STRATEGY_HISTORY.md",
    "P7_PERSONALIZATION_BOUNDARY.md",
    "P7_COMMUNITY_MODEL.md",
    "P7_PUBLIC_PROJECTION_MODEL.md",
    "P7_EVIDENCE_LINKED_COMMUNITY.md",
    "P7_SECURITY_REVIEW.md",
    "P7_PRIVACY_REVIEW.md",
    "P7_DATA_QUALITY_REVIEW.md",
    "P7_REPRODUCIBILITY_REVIEW.md",
    "P7_FINAL_VALIDATION_REPORT.md",
    "P7_GATE_MATRIX.md",
    "P8_READINESS_REPORT.md",
    "P7_INDEPENDENT_AUDITS.md",
)


def test_p7_document_set_and_independent_reviews_are_complete() -> None:
    for name in REQUIRED:
        path = ROOT / "docs" / "p7" / name
        assert path.is_file() and path.read_text(encoding="utf-8").strip(), name
    reviews = sorted((ROOT / "docs" / "p7" / "reviews").glob("[A-J]_*.md"))
    assert [path.name[0] for path in reviews] == list("ABCDEFGHIJ")
    assert all("review" in path.read_text(encoding="utf-8").casefold() for path in reviews)


def test_p7_migration_contains_private_and_projection_boundaries() -> None:
    migration = (ROOT / "migrations" / "003_p7_personal_community.sql").read_text(encoding="utf-8")
    for marker in ("p7_personal_nodes", "privacy_scope", "p7_mastery_states", "p7_projections", "p7_projection_attachments", "p7_audit_events"):
        assert marker in migration
