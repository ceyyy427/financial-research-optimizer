#!/usr/bin/env python3
"""Validate the repository's P0 governance contract without third-party packages."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_FILES: tuple[str, ...] = (
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

AGENT_CONTRACTS: tuple[str, ...] = (
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


def _read(root: Path, relative: str, issues: list[str]) -> str:
    path = root / relative
    if not path.is_file():
        issues.append(f"missing required file: {relative}")
        return ""
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append(f"file is not valid UTF-8: {relative}")
        return ""
    if not content.strip():
        issues.append(f"required file is empty: {relative}")
    return content


def _require_markers(
    content: str,
    relative: str,
    markers: tuple[str, ...],
    issues: list[str],
) -> None:
    folded = content.casefold()
    for marker in markers:
        if marker.casefold() not in folded:
            issues.append(f"{relative} is missing required text: {marker}")


def validate_repository(root: Path | str) -> list[str]:
    """Return human-readable governance issues for ``root``.

    An empty list means that the repository satisfies the P0 contract. The
    function intentionally reads only local text files and has no network or
    package-manager side effects.
    """

    repository = Path(root).expanduser().resolve()
    issues: list[str] = []
    if not repository.is_dir():
        return [f"repository root is not a directory: {repository}"]

    contents = {
        relative: _read(repository, relative, issues)
        for relative in REQUIRED_FILES
    }

    _require_markers(
        contents["README.md"],
        "README.md",
        ("金融研究", "量化学习"),
        issues,
    )
    _require_markers(
        contents["DEPENDENCY_RECORD.md"],
        "DEPENDENCY_RECORD.md",
        ("dependency", "record"),
        issues,
    )
    _require_markers(
        contents["EVOLUTION_LOG.md"],
        "EVOLUTION_LOG.md",
        ("change", "review"),
        issues,
    )
    _require_markers(
        contents["UPGRADE_PROPOSAL.md"],
        "UPGRADE_PROPOSAL.md",
        ("proposal", "compatibility", "review"),
        issues,
    )
    _require_markers(
        contents["ARCHITECTURE.md"],
        "ARCHITECTURE.md",
        (
            "provider",
            "dataset",
            "validation",
            "feature",
            "factor",
            "P4",
            "out of scope",
        ),
        issues,
    )
    _require_markers(
        contents[".agents/README.md"],
        ".agents/README.md",
        ("agent", "contract"),
        issues,
    )

    for relative in AGENT_CONTRACTS:
        _require_markers(
            contents[relative],
            relative,
            ("scope", "must not"),
            issues,
        )

    state = contents["docs/PROJECT_STATE.md"]
    # PROJECT_STATE retains historical compatibility markers for older phase
    # fixtures.  The authoritative declaration lives in the Current state
    # section; scope the lookup there so history cannot mask a completed P6.
    current_section = re.search(
        r"^##\s+Current state\s*$([\s\S]*?)(?=^##\s+|\Z)",
        state,
        re.IGNORECASE | re.MULTILINE,
    )
    phase_source = current_section.group(1) if current_section else state
    phase_match = re.search(r"current\s+phase\s*:\s*(P\d+(?:\.\d+)?)\b", phase_source, re.IGNORECASE)
    if phase_match is None:
        issues.append("docs/PROJECT_STATE.md must declare the current phase")
    elif phase_match.group(1).upper() not in {"P0", "P1", "P2", "P3", "P4", "P4.5", "P5", "P5.5", "P6", "P6.5", "P6.6", "P7", "P7.5", "P8", "P8.1", "P8.2"}:
        issues.append("docs/PROJECT_STATE.md declares an invalid phase")
    current_phase = phase_match.group(1).upper() if phase_match else ""
    if current_phase == "P3":
        _require_markers(
            state,
            "docs/PROJECT_STATE.md",
            (
                "P0 gate: PASS",
                "P1 gate: PASS",
                "P2 gate: PASS",
                "P3 gate: PASS",
                "P4",
                "out of scope",
            ),
            issues,
        )
    elif current_phase == "P4":
        _require_markers(state, "docs/PROJECT_STATE.md", ("P4 gate: PASS", "P5", "out of scope"), issues)
    elif current_phase == "P4.5":
        _require_markers(
            state,
            "docs/PROJECT_STATE.md",
            (
                "P0 gate: PASS",
                "P1 gate: PASS",
                "P2 gate: PASS",
                "P3 gate: PASS",
                "P4 gate: PASS",
                "P5",
                "out of scope",
            ),
            issues,
        )
    elif current_phase == "P5":
        _require_markers(
            state,
            "docs/PROJECT_STATE.md",
            (
                "P0 gate: PASS",
                "P1 gate: PASS",
                "P2 gate: PASS",
                "P3 gate: PASS",
                "P4 gate: PASS",
                "P4.5 Research OS Validation: PASS",
                "P6",
                "out of scope",
            ),
            issues,
        )
    elif current_phase == "P5.5":
        _require_markers(
            state,
            "docs/PROJECT_STATE.md",
            (
                "P0 gate: PASS",
                "P1 gate: PASS",
                "P2 gate: PASS",
                "P3 gate: PASS",
                "P4 gate: PASS",
                "P4.5 Research OS Validation: PASS",
                "P5 gate: PASS",
                "P5.5 gate: PASS",
                "P6",
            ),
            issues,
        )
        for relative in (
            "docs/p5_5/QUANT_RESEARCH_VALIDITY_CONTRACT.md",
            "docs/p5_5/P5_5_TOOL_API_SPEC.md",
            "docs/p5_5/P5_5_FINAL_VALIDATION_REPORT.md",
            "docs/p5_5/P6_READINESS_REPORT.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P5.5 phase file: {relative}")
    elif current_phase == "P6":
        _require_markers(
            state,
            "docs/PROJECT_STATE.md",
            (
                "P0 gate: PASS",
                "P1 gate: PASS",
                "P2 gate: PASS",
                "P3 gate: PASS",
                "P4 gate: PASS",
                "P4.5 Research OS Validation: PASS",
                "P5 gate: PASS",
                "P5.5 gate: PASS",
                "P6 gate: PASS",
                "P7",
                "WAITING FOR HUMAN APPROVAL",
            ),
            issues,
        )
        for relative in (
            "docs/p6/P6_FINAL_VALIDATION_REPORT.md",
            "docs/p6/P6_GATE_REVIEW.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P6 phase file: {relative}")
    elif current_phase == "P6.5":
        _require_markers(
            state,
            "docs/PROJECT_STATE.md",
            (
                "P0 gate: PASS",
                "P1 gate: PASS",
                "P2 gate: PASS",
                "P3 gate: PASS",
                "P4 gate: PASS",
                "P4.5 Research OS Validation: PASS",
                "P5 gate: PASS",
                "P5.5 gate: PASS",
                "P6 gate: PASS",
                "P6.5 gate: PASS",
                "P7",
                "WAITING FOR HUMAN APPROVAL",
            ),
            issues,
        )
        for relative in (
            "docs/p6_5/P6_5_FINAL_VALIDATION_REPORT.md",
            "docs/p6_5/P6_5_GATE_REVIEW.md",
            "docs/p6_5/P7_READINESS_REPORT.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P6.5 phase file: {relative}")
    elif current_phase == "P6.6":
        _require_markers(
            state,
            "docs/PROJECT_STATE.md",
            (
                "P0 gate: PASS",
                "P1 gate: PASS",
                "P2 gate: PASS",
                "P3 gate: PASS",
                "P4 gate: PASS",
                "P4.5 Research OS Validation: PASS",
                "P5 gate: PASS",
                "P5.5 gate: PASS",
                "P6 gate: PASS",
                "P6.5 gate: PASS",
                "P6.6 gate: PASS",
                "P7",
                "WAITING FOR HUMAN APPROVAL",
            ),
            issues,
        )
        for relative in (
            "docs/p6_6/P6_6_FINAL_VALIDATION_REPORT.md",
            "docs/p6_6/P6_6_GATE_REVIEW.md",
            "docs/p6_6/P7_READINESS_REPORT.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P6.6 phase file: {relative}")
    elif current_phase == "P7":
        _require_markers(
            state,
            "docs/PROJECT_STATE.md",
            (
                "P0 gate: PASS",
                "P1 gate: PASS",
                "P2 gate: PASS",
                "P3 gate: PASS",
                "P4 gate: PASS",
                "P5 gate: PASS",
                "P5.5 gate: PASS",
                "P6 gate: PASS",
                "P6.5 gate: PASS",
                "P6.6 gate: PASS",
                "P7 gate: PASS",
                "P8",
                "readiness",
            ),
            issues,
        )
        for relative in (
            "docs/p6_6/P6_6_FINAL_VALIDATION_REPORT.md",
            "docs/p6_6/P6_6_GATE_REVIEW.md",
            "docs/p7/P7_EXECUTION_PLAN.md",
            "docs/p7/P7_ARCHITECTURE.md",
            "docs/p7/P7_CAPABILITY_MATRIX.md",
            "docs/p7/P7_FINAL_VALIDATION_REPORT.md",
            "docs/p7/P8_READINESS_REPORT.md",
            "docs/P8_READINESS_REPORT.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P7 phase file: {relative}")
    elif current_phase == "P7.5":
        _require_markers(
            contents["docs/PROJECT_STATE.md"],
            "docs/PROJECT_STATE.md",
            ("P7 gate: PASS", "P7.5 gate: PASS", "P8", "conditional"),
            issues,
        )
        for relative in (
            "docs/p7_5/P7_5_EXECUTION_PLAN.md",
            "docs/p7_5/P7_5_ARCHITECTURE.md",
            "docs/p7_5/P7_5_CAPABILITY_MATRIX.md",
            "docs/p7_5/P7_5_FINAL_VALIDATION_REPORT.md",
            "docs/p7_5/P8_READINESS_REPORT.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P7.5 phase file: {relative}")
    elif current_phase == "P8":
        _require_markers(
            contents["docs/PROJECT_STATE.md"],
            "docs/PROJECT_STATE.md",
            ("P7.5 gate: PASS", "P8 status: CONDITIONAL", "public-beta"),
            issues,
        )
        for relative in (
            "docs/p7_5/P7_5_FINAL_VALIDATION_REPORT.md",
            "docs/p8/P8_RELEASE_PLAN.md",
            "docs/p8/P8_CAPABILITY_MATRIX.md",
            "docs/p8/P8_PUBLIC_BETA_GATE.md",
            "docs/p8/P8_FINAL_VALIDATION_REPORT.md",
            "SECURITY.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P8 phase file: {relative}")
    elif current_phase == "P8.1":
        _require_markers(
            contents["docs/PROJECT_STATE.md"],
            "docs/PROJECT_STATE.md",
            ("P7.5 gate: PASS", "P8.1 status:", "canonical", "public-beta"),
            issues,
        )
        for relative in (
            "docs/p8_1/P8_1_EXECUTION_PLAN.md",
            "docs/p8_1/P8_1_CAPABILITY_MATRIX.md",
            "docs/p8_1/P8_1_REPOSITORY_BASELINE.md",
            "docs/p8_1/P8_1_UI_AUDIT.md",
            "docs/p8_1/P8_1_DESIGN_SYSTEM_AUDIT.md",
            "docs/p8_1/P8_1_INFORMATION_ARCHITECTURE.md",
            "docs/p8_1/P8_1_PRODUCT_POLISH_REPORT.md",
            "docs/p8_1/P8_1_ACCESSIBILITY_REVIEW.md",
            "docs/p8_1/P8_1_PERFORMANCE_REVIEW.md",
            "docs/p8_1/P8_1_HISTORY_RECONCILIATION.md",
            "docs/p8_1/P8_1_REMOTE_CI_REPORT.md",
            "docs/p8_1/P8_1_RELEASE_REPORT.md",
            "docs/p8_1/P8_1_SECURITY_REVIEW.md",
            "docs/p8_1/P8_1_FINAL_VALIDATION_REPORT.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P8.1 phase file: {relative}")
    elif current_phase == "P8.2":
        _require_markers(
            contents["docs/PROJECT_STATE.md"],
            "docs/PROJECT_STATE.md",
            ("P7.5 gate: PASS", "P8.1 status:", "P8.2 status:", "P8.2B", "human review"),
            issues,
        )
        for relative in (
            "docs/p8_1/P8_1_FINAL_VALIDATION_REPORT.md",
            "docs/p8_2/P8_2_EXECUTION_PLAN.md",
            "docs/p8_2/P8_2_CAPABILITY_MATRIX.md",
            "docs/p8_2/P8_2_DEPENDENCY_TOPOLOGY.md",
            "docs/p8_2/P8_2_VISUALIZATION_ARCHITECTURE.md",
            "docs/p8_2/P8_2_RESEARCH_ENGINE_ARCHITECTURE.md",
            "docs/p8_2/P8_2_DATA_SOURCE_ARCHITECTURE.md",
            "docs/p8_2/P8_2_QMT_BRIDGE.md",
            "docs/p8_2/P8_2_QLIB_ADAPTER.md",
            "docs/p8_2/P8_2_VECTORBT_SANDBOX.md",
            "docs/p8_2/P8_2_UI_INTERACTION_STANDARD.md",
            "docs/p8_2/P8_2_PERFORMANCE_REVIEW.md",
            "docs/p8_2/P8_2_SECURITY_REVIEW.md",
            "docs/p8_2/P8_2_FINAL_VALIDATION_REPORT.md",
            "docs/p8_2/TRADINGAGENTS_REFERENCE.md",
            "docs/p8_2/QLIB_REFERENCE.md",
            "docs/p8_2/VECTORBT_REFERENCE.md",
            "docs/p8_2/QMT_INTEGRATION_REVIEW.md",
            "docs/p8_2/EXTERNAL_QUANT_TOOL_MATRIX.md",
        ):
            if not (repository / relative).is_file():
                issues.append(f"missing P8.2 phase file: {relative}")
    else:
        _require_markers(state, "docs/PROJECT_STATE.md", ("P0 gate: PASS", "P4", "out of scope"), issues)

    gate = contents["docs/phases/P0_GATE_DESIGN.md"]
    _require_markers(
        gate,
        "docs/phases/P0_GATE_DESIGN.md",
        (
            "## Entry criteria",
            "## Checks",
            "## Independent review",
            "## Exit criteria",
            "Review result: PASS",
            "P0 gate status: PASS",
        ),
        issues,
    )

    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="repository root to validate (default: current directory)",
    )
    args = parser.parse_args(argv)

    issues = validate_repository(args.root)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        print(f"FAIL: governance validation found {len(issues)} issue(s)")
        return 1

    print("PASS: governance validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
