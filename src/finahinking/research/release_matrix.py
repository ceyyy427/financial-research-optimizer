"""The frozen acceptance matrix for the offline research runtime.

The matrix is deliberately data-only.  It records what the local tests and
contracts establish, while retaining explicit states for isolated engines and
unverified external connections.  Those states cannot be promoted to a pass
by a caller or by a report renderer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Final


class CapabilityStatus(str, Enum):
    """Stable status vocabulary used by release reports and the UI."""

    OFFLINE_PASS = "OFFLINE_PASS"
    # Generic PASS is retained only as a sentinel for consumers checking that
    # conservative statuses were not promoted. Matrix records never emit it.
    PASS = "PASS"
    ISOLATED_DEFERRED = "ISOLATED_DEFERRED"
    EXTERNAL_UNVERIFIED = "EXTERNAL_UNVERIFIED"
    NOT_IN_SCOPE = "NOT_IN_SCOPE"


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    """Evidence-bound state for one research capability."""

    name: str
    implemented_offline: bool = False
    isolated_only: bool = False
    external_unverified: bool = False
    not_in_scope: bool = False
    follow_up_tasks: tuple[int, ...] = ()
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("capability name must not be empty")
        if self.not_in_scope and (
            self.implemented_offline or self.isolated_only or self.external_unverified
        ):
            raise ValueError("out-of-scope capability cannot have implementation evidence")
        if self.isolated_only and self.external_unverified:
            raise ValueError("isolated and external-unverified states are mutually exclusive")
        if any(task < 1 for task in self.follow_up_tasks):
            raise ValueError("follow-up task numbers must be positive")

    @property
    def status(self) -> CapabilityStatus:
        """Return the most conservative status supported by this record."""

        if self.not_in_scope:
            return CapabilityStatus.NOT_IN_SCOPE
        if self.external_unverified:
            return CapabilityStatus.EXTERNAL_UNVERIFIED
        if self.isolated_only:
            return CapabilityStatus.ISOLATED_DEFERRED
        if self.implemented_offline:
            return CapabilityStatus.OFFLINE_PASS
        # An empty evidence record is still explicitly unverified rather than
        # being mistaken for a passing capability.
        return CapabilityStatus.EXTERNAL_UNVERIFIED

    def as_dict(self) -> dict[str, object]:
        """Return a serializable representation for reports and tests."""

        return {
            "name": self.name,
            "status": self.status.value,
            "implemented_offline": self.implemented_offline,
            "isolated_only": self.isolated_only,
            "external_unverified": self.external_unverified,
            "not_in_scope": self.not_in_scope,
            "follow_up_tasks": list(self.follow_up_tasks),
            "evidence": list(self.evidence),
        }


_MATRIX: Final[dict[str, CapabilityRecord]] = {
    "provider": CapabilityRecord(
        "provider",
        implemented_offline=True,
        external_unverified=True,
        follow_up_tasks=(2, 3),
        evidence=("docs/RESEARCH_RUNTIME_RELEASE_CHECKLIST.md", "tests/research/test_provider_adapters.py"),
    ),
    "codex": CapabilityRecord(
        "codex",
        implemented_offline=True,
        follow_up_tasks=(4,),
        evidence=("docs/RESEARCH_RUNTIME_RELEASE_CHECKLIST.md", "tests/research/test_codex_bridge.py"),
    ),
    "factor": CapabilityRecord(
        "factor",
        implemented_offline=True,
        follow_up_tasks=(5, 6, 7),
        evidence=("docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md", "tests/research/test_factor_pipeline.py"),
    ),
    "engine": CapabilityRecord(
        "engine",
        implemented_offline=True,
        isolated_only=True,
        follow_up_tasks=(8, 9),
        evidence=("docs/RESEARCH_ENGINE_ADMISSION_CHECKLIST.md", "tests/research/test_engine_registry.py"),
    ),
    "risk": CapabilityRecord(
        "risk",
        implemented_offline=True,
        follow_up_tasks=(10,),
        evidence=("docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md", "tests/research/test_risk_runtime.py"),
    ),
    "portfolio": CapabilityRecord(
        "portfolio",
        implemented_offline=True,
        follow_up_tasks=(11,),
        evidence=("docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md", "tests/research/test_portfolio_runtime.py"),
    ),
    "learning": CapabilityRecord(
        "learning",
        implemented_offline=True,
        follow_up_tasks=(12,),
        evidence=("docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md", "tests/research/test_learning_manager.py"),
    ),
    "queue": CapabilityRecord(
        "queue",
        implemented_offline=True,
        follow_up_tasks=(13, 14),
        evidence=("docs/RESEARCH_RUNTIME_RELEASE_CHECKLIST.md", "tests/research/test_job_queue.py"),
    ),
    "ui": CapabilityRecord(
        "ui",
        implemented_offline=True,
        external_unverified=True,
        follow_up_tasks=(15, 16),
        evidence=("docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md", "tests/research/test_ui.py"),
    ),
    "data_vendor_sdk": CapabilityRecord(
        "data_vendor_sdk",
        not_in_scope=True,
        evidence=("docs/PROJECT_STATE.md", "docs/RESEARCH_CAPABILITY_BACKLOG.md"),
    ),
    "unattended_self_improvement": CapabilityRecord(
        "unattended_self_improvement",
        not_in_scope=True,
        evidence=("docs/PROJECT_STATE.md", "docs/RESEARCH_CAPABILITY_BACKLOG.md"),
    ),
}


_SOURCE_MARKERS: Final[dict[str, tuple[str, ...]]] = {
    "provider": ("provider", "数据"),
    "codex": ("codex", "模型"),
    "factor": ("factor", "因子"),
    "engine": ("engine", "引擎", "qlib", "vectorbt"),
    "risk": ("risk", "风险"),
    "portfolio": ("portfolio", "组合"),
    "learning": ("learning", "学习"),
    "queue": ("queue", "队列", "worker"),
    "ui": ("ui", "前端", "报告"),
    "data_vendor_sdk": ("vendor", "供应商", "sdk"),
    "unattended_self_improvement": ("self-improvement", "自我改进"),
}


def _default_project_root() -> Path:
    # release_matrix.py lives at <root>/src/finahinking/research/.
    return Path(__file__).resolve().parents[3]


def _validate_sources(matrix: Mapping[str, CapabilityRecord], project_root: Path) -> None:
    """Fail closed when checklists or test evidence drift from the matrix."""

    for name, record in matrix.items():
        markers = _SOURCE_MARKERS[name]
        found_marker = False
        for relative in record.evidence:
            path = project_root / relative
            if not path.is_file():
                raise ValueError(f"evidence path does not exist: {relative}")
            if path.suffix.lower() in {".md", ".rst", ".txt"}:
                text = path.read_text(encoding="utf-8").lower()
                if any(marker.lower() in text for marker in markers):
                    found_marker = True
        if not found_marker:
            raise ValueError(f"capability source marker missing: {name}")


def load_release_matrix(project_root: str | Path | None = None) -> Mapping[str, CapabilityRecord]:
    """Load the immutable matrix after validating repository source evidence.

    ``project_root`` is injectable for deterministic drift tests; normal use
    resolves the repository root from this module's location.
    """

    root = Path(project_root) if project_root is not None else _default_project_root()
    _validate_sources(_MATRIX, root)
    return MappingProxyType(_MATRIX)


__all__ = ["CapabilityRecord", "CapabilityStatus", "load_release_matrix"]
