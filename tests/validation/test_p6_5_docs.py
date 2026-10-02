"""Contract checks for the P6.5 documentation set.

This test intentionally checks the existence and semantic anchors of the
required documents, not a particular number of tests, rows, or other volatile
validation output.  The final report owns those fresh measurements.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


REQUIRED_DOCS = (
    "P6_5_EXECUTION_PLAN.md",
    "P6_5_ARCHITECTURE.md",
    "P6_5_CAPABILITY_MATRIX.md",
    "SOURCE_ADMISSION_POLICY.md",
    "SOURCE_TIER_MODEL.md",
    "BLS_SOURCE_ADMISSION.md",
    "A_STOCK_DATA_DISCOVERY_REVIEW.md",
    "AKSHARE_ADMISSION_REVIEW.md",
    "TUSHARE_ADMISSION_REVIEW.md",
    "P6_5_CANONICAL_DATA_MODEL.md",
    "P6_5_TEMPORAL_MODEL.md",
    "P6_5_SQL_SCHEMA.md",
    "P6_5_EVENT_MODEL.md",
    "P6_5_CLAIM_EVIDENCE_MODEL.md",
    "P6_5_UNDERSTANDING_CONTRACT.md",
    "P6_5_PRODUCT_JOURNEY.md",
    "P6_5_EVALUATION_PLAN.md",
    "P6_5_SECURITY_REVIEW.md",
    "P6_5_DATA_QUALITY_REVIEW.md",
    "P6_5_FINAL_VALIDATION_REPORT.md",
    "P6_5_GATE_REVIEW.md",
    "P7_READINESS_REPORT.md",
)


DOC_MARKERS: dict[str, tuple[str, ...]] = {
    "P6_5_EXECUTION_PLAN.md": ("P6.5", "gate", "evaluation"),
    "P6_5_ARCHITECTURE.md": ("source", "capture", "event", "claim"),
    "P6_5_CAPABILITY_MATRIX.md": ("capability", "MCP", "install"),
    "SOURCE_ADMISSION_POLICY.md": ("authoritative", "provider", "discovery"),
    "SOURCE_TIER_MODEL.md": ("TIER_0", "TIER_3", "admission"),
    "BLS_SOURCE_ADMISSION.md": ("BLS", "authoritative", "capture"),
    "A_STOCK_DATA_DISCOVERY_REVIEW.md": ("a-stock-data", "discovery"),
    "AKSHARE_ADMISSION_REVIEW.md": ("AKShare", "discovery"),
    "TUSHARE_ADMISSION_REVIEW.md": ("Tushare", "discovery"),
    "P6_5_CANONICAL_DATA_MODEL.md": ("observation", "fingerprint", "revision"),
    "P6_5_TEMPORAL_MODEL.md": (
        "occurred_at",
        "effective_at",
        "published_at",
        "available_at",
        "retrieved_at",
    ),
    "P6_5_SQL_SCHEMA.md": ("migration", "postgres", "parameterized"),
    "P6_5_EVENT_MODEL.md": ("event", "observation", "evidence"),
    "P6_5_CLAIM_EVIDENCE_MODEL.md": ("claim", "evidence", "hypothesis"),
    "P6_5_UNDERSTANDING_CONTRACT.md": ("fact", "interpretation", "unknown"),
    "P6_5_PRODUCT_JOURNEY.md": ("CPI", "show evidence", "learning"),
    "P6_5_EVALUATION_PLAN.md": ("understanding gain", "misconception", "causal"),
    "P6_5_SECURITY_REVIEW.md": ("prompt injection", "SQL", "untrusted"),
    "P6_5_DATA_QUALITY_REVIEW.md": ("quarantine", "duplicate", "missingness"),
    "P6_5_FINAL_VALIDATION_REPORT.md": ("evidence", "pytest", "git diff"),
    "P6_5_GATE_REVIEW.md": ("P6.5", "gate"),
    "P7_READINESS_REPORT.md": ("P7", "decision", "remaining"),
}


def _read_doc(filename: str) -> str:
    path = ROOT / "docs" / "p6_5" / filename
    assert path.is_file(), f"missing required P6.5 document: {path}"
    text = path.read_text(encoding="utf-8")
    assert text.strip(), f"empty required P6.5 document: {path}"
    return text


def test_p6_5_required_documents_exist_with_contract_anchors() -> None:
    documents = {filename: _read_doc(filename) for filename in REQUIRED_DOCS}
    for filename, markers in DOC_MARKERS.items():
        folded = documents[filename].casefold()
        for marker in markers:
            assert marker.casefold() in folded, f"{filename} is missing semantic marker: {marker}"


def test_p6_5_readiness_report_uses_the_required_three_way_decision() -> None:
    report = _read_doc("P7_READINESS_REPORT.md")
    assert re.search(
        r"(?:^|\n)\s*(?:A|B|C)\s*[—-]\s*(?:READY|P6\.5 REWORK REQUIRED)",
        report,
        flags=re.IGNORECASE,
    ), "P7 readiness report must state A/B/C decision"
