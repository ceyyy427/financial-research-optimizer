from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ROOT = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
)
REQUIRED_DOCS = (
    "GETTING_STARTED.md",
    "QUICKSTART.md",
    "INSTALLATION.md",
    "PRIVACY.md",
    "DATA_SOURCES.md",
    "KNOWN_LIMITATIONS.md",
    "KNOWLEDGE_CONTRIBUTION.md",
    "DATA_ADAPTER_CONTRIBUTION.md",
    "FEATURE_CONTRIBUTION.md",
    "STRATEGY_RESEARCH_GUIDE.md",
)
REQUIRED_P8 = (
    "P8_RELEASE_PLAN.md",
    "P8_CAPABILITY_MATRIX.md",
    "P8_LICENSE_REVIEW.md",
    "P8_SECURITY_REVIEW.md",
    "P8_PACKAGING_REVIEW.md",
    "P8_CLEAN_INSTALL_REPORT.md",
    "P8_PUBLIC_BETA_GATE.md",
    "P8_FINAL_VALIDATION_REPORT.md",
)


def test_p8_document_set_is_present_and_nonempty() -> None:
    for name in REQUIRED_ROOT:
        path = ROOT / name
        assert path.is_file() and path.read_text(encoding="utf-8").strip(), name
    for name in REQUIRED_DOCS:
        path = ROOT / "docs" / name
        assert path.is_file() and path.read_text(encoding="utf-8").strip(), name
    for name in REQUIRED_P8:
        path = ROOT / "docs" / "p8" / name
        assert path.is_file() and path.read_text(encoding="utf-8").strip(), name
    site = ROOT / "site" / "index.html"
    assert site.is_file() and "Download" in site.read_text(encoding="utf-8") and "quickstart" in site.read_text(encoding="utf-8").casefold()


def test_p8_public_beta_docs_expose_safety_and_distribution_boundaries() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "REAL EVENT" in readme and "IDEA" in readme
    assert "real-money" in readme.casefold()
    privacy = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8").casefold()
    assert "telemetry" in privacy and "api key" in privacy
    limits = (ROOT / "docs" / "KNOWN_LIMITATIONS.md").read_text(encoding="utf-8").casefold()
    assert "real-money" in limits and "beta" in limits
    gate = (ROOT / "docs" / "p8" / "P8_PUBLIC_BETA_GATE.md").read_text(encoding="utf-8")
    assert "47" in gate and "CONDITIONAL" in gate
    cloud = (ROOT / "docs" / "FINATHINK_CLOUD.md").read_text(encoding="utf-8")
    assert "DOWNLOAD" in cloud and "GitHub page" in cloud


def test_release_and_security_automation_is_defined() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "pytest" in ci and "ruff" in ci and "secret_scan.py" in ci
    assert "pip wheel" in release and "SHA256SUMS" in release and "verify-tag" in release
    templates = sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
    assert len(templates) >= 6
    reviews = sorted((ROOT / "docs" / "p8" / "reviews").glob("[A-J]_*.md"))
    assert [path.name[0] for path in reviews] == list("ABCDEFGHIJ")
