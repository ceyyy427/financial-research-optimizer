from __future__ import annotations

from pathlib import Path

import pytest

from finahinking.research.release_matrix import CapabilityStatus, load_release_matrix


def test_release_matrix_freezes_research_capability_surface() -> None:
    matrix = load_release_matrix()

    expected = {
        "provider",
        "codex",
        "factor",
        "engine",
        "risk",
        "portfolio",
        "learning",
        "queue",
        "ui",
    }
    assert expected <= set(matrix)

    assert {name for name, item in matrix.items() if item.not_in_scope} == {
        "data_vendor_sdk",
        "unattended_self_improvement",
    }
    assert matrix["provider"].external_unverified is True
    assert matrix["engine"].isolated_only is True
    assert matrix["engine"].status is CapabilityStatus.ISOLATED_DEFERRED


def test_deferred_and_external_capabilities_are_never_reported_as_pass() -> None:
    matrix = load_release_matrix()

    for item in matrix.values():
        if item.isolated_only or item.external_unverified:
            assert item.status not in {
                CapabilityStatus.OFFLINE_PASS,
                CapabilityStatus.PASS,
            }

    assert matrix["data_vendor_sdk"].status is CapabilityStatus.NOT_IN_SCOPE
    assert matrix["unattended_self_improvement"].status is CapabilityStatus.NOT_IN_SCOPE


def test_matrix_validates_checklists_and_test_evidence(tmp_path: Path) -> None:
    root = tmp_path
    (root / "docs").mkdir()
    (root / "tests/research").mkdir(parents=True)
    (root / "docs/RESEARCH_RUNTIME_RELEASE_CHECKLIST.md").write_text("provider Codex queue", encoding="utf-8")
    (root / "docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md").write_text(
        "factor engine risk portfolio learning UI", encoding="utf-8"
    )
    (root / "docs/RESEARCH_ENGINE_ADMISSION_CHECKLIST.md").write_text("engine", encoding="utf-8")
    (root / "docs/PROJECT_STATE.md").write_text("data vendor SDK unattended self-improvement", encoding="utf-8")
    (root / "docs/RESEARCH_CAPABILITY_BACKLOG.md").write_text(
        "vendor SDK unattended self-improvement", encoding="utf-8"
    )
    for evidence in (
        "test_provider_adapters.py",
        "test_codex_bridge.py",
        "test_factor_pipeline.py",
        "test_engine_registry.py",
        "test_risk_runtime.py",
        "test_portfolio_runtime.py",
        "test_learning_manager.py",
        "test_job_queue.py",
        "test_ui.py",
    ):
        (root / "tests/research" / evidence).touch()

    assert len(load_release_matrix(root)) == 11

    (root / "tests/research/test_ui.py").unlink()
    with pytest.raises(ValueError, match="evidence path does not exist"):
        load_release_matrix(root)


def test_record_constructor_rejects_contradictory_or_invalid_evidence() -> None:
    from finahinking.research.release_matrix import CapabilityRecord

    with pytest.raises(ValueError, match="out-of-scope"):
        CapabilityRecord("x", not_in_scope=True, implemented_offline=True)
    with pytest.raises(ValueError, match="mutually exclusive"):
        CapabilityRecord("x", isolated_only=True, external_unverified=True)
    with pytest.raises(ValueError, match="positive"):
        CapabilityRecord("x", follow_up_tasks=(0,))
