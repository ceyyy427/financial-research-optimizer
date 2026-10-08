from __future__ import annotations

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
