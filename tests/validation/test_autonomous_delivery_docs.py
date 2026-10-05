from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_validation_matrix_covers_implemented_and_deferred_boundaries() -> None:
    text = (ROOT / "docs/FINATHINK_AUTONOMOUS_VALIDATION.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "factor expression safety",
        "candidate mining",
        "factor metrics",
        "provider/api-key boundary",
        "paper-only",
        "broker/account/order operations",
        "github",
    ):
        assert phrase in text


def test_validation_matrix_requires_fresh_release_commands() -> None:
    text = (ROOT / "docs/FINATHINK_AUTONOMOUS_VALIDATION.md").read_text(encoding="utf-8")
    for command in (
        "python3 -m ruff check src tests",
        "python3 -m compileall -q src tests",
        "python3 -m pytest -q",
        "npm test",
        "npm run build",
        "python3 scripts/secret_scan.py",
        "python3 scripts/validate_governance.py .",
        "git diff --check",
    ):
        assert command in text
