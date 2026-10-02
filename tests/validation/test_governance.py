"""Tests for the dependency-free repository governance validator."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_governance.py"

REQUIRED_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "LICENSE",
    "CHANGELOG.md",
    "DEPENDENCY_RECORD.md",
    "EVOLUTION_LOG.md",
    "UPGRADE_PROPOSAL.md",
    "ARCHITECTURE.md",
    "docs/PROJECT_STATE.md",
    "docs/phases/P0_GATE_DESIGN.md",
    ".agents/README.md",
    ".agents/implementer.md",
    ".agents/researcher.md",
    ".agents/reviewer.md",
)


def _write_complete_repository(root: Path) -> None:
    """Create the smallest repository that should satisfy the P0 contract."""

    text_by_path = {
        "README.md": "# Finahinking\nPersonal financial research laboratory.\nNo investment advice.\n",
        "CONTRIBUTING.md": "# Contributing\nRun the validation checks before proposing a change.\n",
        "CODE_OF_CONDUCT.md": "# Code of Conduct\nBe respectful and constructive.\n",
        "LICENSE": "MIT License\n",
        "CHANGELOG.md": "# Changelog\n\n## Unreleased\n",
        "DEPENDENCY_RECORD.md": "# Dependency Record\n\nNo dependency is added without a purpose and owner.\n",
        "EVOLUTION_LOG.md": "# Evolution Log\n\nRecord material architecture changes and review results here.\n",
        "UPGRADE_PROPOSAL.md": "# Upgrade Proposal\n\nProposals require evidence, compatibility notes, and review.\n",
        "ARCHITECTURE.md": (
            "# Architecture\n\n"
            "provider -> dataset/provenance -> validation -> feature functions -> factors\n"
            "\nP4 is explicitly out of scope.\n"
        ),
        "docs/PROJECT_STATE.md": (
            "# Project State\n\n"
            "Current phase: P0\n"
            "P0 gate: PASS\n"
            "Next phase: P1\n"
            "P4 status: out of scope\n"
        ),
        "docs/phases/P0_GATE_DESIGN.md": (
            "# P0 Gate Design\n\n"
            "## Entry criteria\nRepository scope and safety constraints are documented.\n\n"
            "## Checks\nRun the governance validator and inspect required documents.\n\n"
            "## Independent review\nReview result: PASS\n\n"
            "## Exit criteria\nP0 gate status: PASS\n"
        ),
        ".agents/README.md": "# Agent Contracts\nEvery agent follows the project scope and safety rules.\n",
        ".agents/implementer.md": "# Implementer\n## Scope\nImplement approved changes.\n## Must not\nAdd P4 behavior or investment advice.\n",
        ".agents/researcher.md": "# Researcher\n## Scope\nInvestigate sources and assumptions.\n## Must not\nUse secrets or provide investment advice.\n",
        ".agents/reviewer.md": "# Reviewer\n## Scope\nCheck evidence and acceptance criteria.\n## Must not\nApprove missing tests or governance evidence.\n",
    }
    assert set(text_by_path) == set(REQUIRED_FILES)
    for relative, contents in text_by_path.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")


def _run_validator(repository: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(repository)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


class GovernanceValidatorTests(unittest.TestCase):
    def test_validator_accepts_complete_governance_repository(self) -> None:
        # unittest does not provide pytest's tmp_path fixture. Use a unique
        # temporary directory and clean it up after the assertion.
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)

            result = _run_validator(tmp_path)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)

    def test_validator_reports_missing_required_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            (tmp_path / "DEPENDENCY_RECORD.md").unlink()

            result = _run_validator(tmp_path)

            self.assertNotEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            self.assertIn("DEPENDENCY_RECORD.md", output)

    def test_validator_rejects_invalid_phase_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace("Current phase: P0", "Current phase: P4"),
                encoding="utf-8",
            )

            result = _run_validator(tmp_path)

            self.assertNotEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            self.assertIn("P4", output)
            self.assertIn("P5", output)

    def test_validator_accepts_p4_completion_state(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace(
                    "Current phase: P0\nP0 gate: PASS\nNext phase: P1\nP4 status: out of scope",
                    "Current phase: P4\nP0 gate: PASS\nP4 gate: PASS\nNext action: human review\nP5 status: out of scope",
                ),
                encoding="utf-8",
            )
            result = _run_validator(tmp_path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_accepts_p4_5_validation_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace(
                    "Current phase: P0\nP0 gate: PASS\nNext phase: P1\nP4 status: out of scope",
                    "Current phase: P4.5 Research OS Validation\n"
                    "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\n"
                    "P3 gate: PASS\nP4 gate: PASS\n"
                    "Next action: P5 human approval\n"
                    "P5 implementation scope: out of scope until approval",
                ),
                encoding="utf-8",
            )

            result = _run_validator(tmp_path)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_unknown_decimal_phase(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace(
                    "Current phase: P0\nP0 gate: PASS\nNext phase: P1\nP4 status: out of scope",
                    "Current phase: P4.6 Research OS Validation\n"
                    "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\n"
                    "P3 gate: PASS\nP4 gate: PASS\n"
                    "Next action: P5 human approval\n"
                    "P5 implementation scope: out of scope until approval",
                ),
                encoding="utf-8",
            )

            result = _run_validator(tmp_path)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid phase", result.stdout + result.stderr)

    def test_validator_rejects_p4_5_state_without_all_completed_gates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace(
                    "Current phase: P0\nP0 gate: PASS\nNext phase: P1\nP4 status: out of scope",
                    "Current phase: P4.5 Research OS Validation\n"
                    "P0 gate: PASS\nP5 implementation scope: out of scope until approval",
                ),
                encoding="utf-8",
            )

            result = _run_validator(tmp_path)

            self.assertNotEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            self.assertIn("P4 gate: PASS", output)

    def test_validator_accepts_p5_foundation_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace(
                    "Current phase: P0\nP0 gate: PASS\nNext phase: P1\nP4 status: out of scope",
                    "Current phase: P5 Quant Engine Foundation\n"
                    "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\n"
                    "P3 gate: PASS\nP4 gate: PASS\n"
                    "P4.5 Research OS Validation: PASS\n"
                    "Next action: P5 Gate Review\n"
                    "P6 implementation scope: out of scope until approval",
                ),
                encoding="utf-8",
            )

            result = _run_validator(tmp_path)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_accepts_p5_5_state_when_gate_evidence_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                "Current phase: P5.5 Quant Platform Stabilization\n"
                "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\nP3 gate: PASS\n"
                "P4 gate: PASS\nP4.5 Research OS Validation: PASS\nP5 gate: PASS\n"
                "P5.5 gate: PASS\nP6: ready\n",
                encoding="utf-8",
            )
            for relative in (
                "docs/p5_5/QUANT_RESEARCH_VALIDITY_CONTRACT.md",
                "docs/p5_5/P5_5_TOOL_API_SPEC.md",
                "docs/p5_5/P5_5_FINAL_VALIDATION_REPORT.md",
                "docs/p5_5/P6_READINESS_REPORT.md",
            ):
                target = tmp_path / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("PASS\n", encoding="utf-8")
            result = _run_validator(tmp_path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_accepts_p6_stop_state_when_gate_evidence_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                "Current phase: P6 Guided Quant Research & Learning\n"
                "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\nP3 gate: PASS\n"
                "P4 gate: PASS\nP4.5 Research OS Validation: PASS\nP5 gate: PASS\n"
                "P5.5 gate: PASS\nP6 gate: PASS\nP7: WAITING FOR HUMAN APPROVAL\n",
                encoding="utf-8",
            )
            for relative in ("docs/p6/P6_FINAL_VALIDATION_REPORT.md", "docs/p6/P6_GATE_REVIEW.md"):
                target = tmp_path / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("PASS\n", encoding="utf-8")
            result = _run_validator(tmp_path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_accepts_p6_5_stop_state_when_gate_evidence_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                "Current phase: P6.5 Understanding Engine\n"
                "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\nP3 gate: PASS\n"
                "P4 gate: PASS\nP4.5 Research OS Validation: PASS\nP5 gate: PASS\n"
                "P5.5 gate: PASS\nP6 gate: PASS\nP6.5 gate: PASS\n"
                "P7: WAITING FOR HUMAN APPROVAL\n",
                encoding="utf-8",
            )
            for relative in (
                "docs/p6_5/P6_5_FINAL_VALIDATION_REPORT.md",
                "docs/p6_5/P6_5_GATE_REVIEW.md",
                "docs/p6_5/P7_READINESS_REPORT.md",
            ):
                target = tmp_path / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("PASS\n", encoding="utf-8")
            result = _run_validator(tmp_path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
