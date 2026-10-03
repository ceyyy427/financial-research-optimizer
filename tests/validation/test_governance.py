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
    ".agents/orchestrator.md",
    ".agents/planner.md",
    ".agents/architect.md",
    ".agents/builder.md",
    ".agents/researcher.md",
    ".agents/reviewer.md",
    ".agents/security-reviewer.md",
    ".agents/dependency-manager.md",
    ".agents/release-manager.md",
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
        ".agents/orchestrator.md": "# Orchestrator\n## Scope\nOwn phase gates.\n## Must not\nSkip a gate.\n",
        ".agents/planner.md": "# Planner\n## Scope\nDefine testable plans.\n## Must not\nChoose unrecorded dependencies.\n",
        ".agents/architect.md": "# Architect\n## Scope\nReview boundaries.\n## Must not\nApprove unsafe shortcuts.\n",
        ".agents/builder.md": "# Builder\n## Scope\nImplement approved plans.\n## Must not\nAdd trading automation.\n",
        ".agents/researcher.md": "# Researcher\n## Scope\nInvestigate sources and assumptions.\n## Must not\nUse secrets or provide investment advice.\n",
        ".agents/reviewer.md": "# Reviewer\n## Scope\nCheck evidence and acceptance criteria.\n## Must not\nApprove missing tests or governance evidence.\n",
        ".agents/security-reviewer.md": "# Security Reviewer\n## Scope\nCheck security.\n## Must not\nApprove secrets.\n",
        ".agents/dependency-manager.md": "# Dependency Manager\n## Scope\nControl dependencies.\n## Must not\nInstall silently.\n",
        ".agents/release-manager.md": "# Release Manager\n## Scope\nPrepare reviewed snapshots.\n## Must not\nPublish without review.\n",
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

    def test_validator_reports_missing_required_role_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            (tmp_path / ".agents" / "security-reviewer.md").unlink()

            result = _run_validator(tmp_path)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("security-reviewer.md", result.stdout + result.stderr)

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

    def test_validator_accepts_p3_stop_state_with_required_gates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace(
                    "Current phase: P0\nP0 gate: PASS\nNext phase: P1\nP4 status: out of scope",
                    "Current phase: P3 Quant Research Engine\n"
                    "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\nP3 gate: PASS\n"
                    "Next action: human review\nP4 status: out of scope",
                ),
                encoding="utf-8",
            )
            result = _run_validator(tmp_path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_p3_stop_state_without_prior_gates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace(
                    "Current phase: P0\nP0 gate: PASS\nNext phase: P1\nP4 status: out of scope",
                    "Current phase: P3 Quant Research Engine\nP0 gate: PASS\nP4 status: out of scope",
                ),
                encoding="utf-8",
            )
            result = _run_validator(tmp_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("P1 gate: PASS", result.stdout + result.stderr)

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

    def test_validator_accepts_p8_1_conditional_state_with_report_set(self) -> None:
        """P8.1 is a governed phase, even when publication remains conditional."""

        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                "Current phase: P8.1 Product UI/UX Polish\n"
                "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\nP3 gate: PASS\n"
                "P4 gate: PASS\nP5 gate: PASS\nP5.5 gate: PASS\nP6 gate: PASS\n"
                "P6.5 gate: PASS\nP6.6 gate: PASS\nP7 gate: PASS\n"
                "P7.5 gate: PASS\nP8.1 status: CONDITIONAL\n"
                "canonical GitHub: conditional\npublic-beta: conditional\n",
                encoding="utf-8",
            )
            report_names = (
                "P8_1_EXECUTION_PLAN.md",
                "P8_1_CAPABILITY_MATRIX.md",
                "P8_1_REPOSITORY_BASELINE.md",
                "P8_1_UI_AUDIT.md",
                "P8_1_DESIGN_SYSTEM_AUDIT.md",
                "P8_1_INFORMATION_ARCHITECTURE.md",
                "P8_1_PRODUCT_POLISH_REPORT.md",
                "P8_1_ACCESSIBILITY_REVIEW.md",
                "P8_1_PERFORMANCE_REVIEW.md",
                "P8_1_HISTORY_RECONCILIATION.md",
                "P8_1_REMOTE_CI_REPORT.md",
                "P8_1_RELEASE_REPORT.md",
                "P8_1_SECURITY_REVIEW.md",
                "P8_1_FINAL_VALIDATION_REPORT.md",
            )
            for name in report_names:
                target = tmp_path / "docs" / "p8_1" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("P8.1 conditional public-beta canonical\n", encoding="utf-8")

            result = _run_validator(tmp_path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_accepts_p8_2_stop_state_with_report_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _write_complete_repository(tmp_path)
            state = tmp_path / "docs/PROJECT_STATE.md"
            state.write_text(
                "Current phase: P8.2 Capability Expansion\n"
                "P0 gate: PASS\nP1 gate: PASS\nP2 gate: PASS\nP3 gate: PASS\n"
                "P4 gate: PASS\nP5 gate: PASS\nP5.5 gate: PASS\nP6 gate: PASS\n"
                "P6.5 gate: PASS\nP6.6 gate: PASS\nP7 gate: PASS\nP7.5 gate: PASS\n"
                "P8.1 status: CONDITIONAL\nP8.2 status: CONDITIONAL\n"
                "P8.2B: WAITING FOR HUMAN REVIEW\n",
                encoding="utf-8",
            )
            report_names = (
                "P8_2_EXECUTION_PLAN.md",
                "P8_2_CAPABILITY_MATRIX.md",
                "P8_2_DEPENDENCY_TOPOLOGY.md",
                "P8_2_VISUALIZATION_ARCHITECTURE.md",
                "P8_2_RESEARCH_ENGINE_ARCHITECTURE.md",
                "P8_2_DATA_SOURCE_ARCHITECTURE.md",
                "P8_2_QMT_BRIDGE.md",
                "P8_2_QLIB_ADAPTER.md",
                "P8_2_VECTORBT_SANDBOX.md",
                "P8_2_UI_INTERACTION_STANDARD.md",
                "P8_2_PERFORMANCE_REVIEW.md",
                "P8_2_SECURITY_REVIEW.md",
                "P8_2_FINAL_VALIDATION_REPORT.md",
                "TRADINGAGENTS_REFERENCE.md",
                "QLIB_REFERENCE.md",
                "VECTORBT_REFERENCE.md",
                "QMT_INTEGRATION_REVIEW.md",
                "EXTERNAL_QUANT_TOOL_MATRIX.md",
            )
            for name in report_names:
                target = tmp_path / "docs" / "p8_2" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("P8.2 conditional human review\n", encoding="utf-8")
            target = tmp_path / "docs" / "p8_1" / "P8_1_FINAL_VALIDATION_REPORT.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("P8.1 conditional\n", encoding="utf-8")

            result = _run_validator(tmp_path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
