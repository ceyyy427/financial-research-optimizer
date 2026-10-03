from __future__ import annotations

from finahinking.p8_2b.identity import capability_inventory, project_identity


def test_public_identity_is_finathink_while_python_import_stays_compatible() -> None:
    identity = project_identity()
    assert identity["project_id"] == "finathink"
    assert identity["distribution_name"] == "finathink"
    assert identity["legacy_distribution_name"] == "finahinking"
    assert identity["python_import"] == "finahinking"
    assert identity["cli"] == "finathink"


def test_capability_inventory_is_json_safe_and_does_not_import_optional_engines() -> None:
    inventory = capability_inventory()
    assert {item["id"] for item in inventory} >= {
        "math_renderer",
        "sympy",
        "codemirror",
        "crossref",
    }
    assert all(set(item) == {"id", "status", "version", "reason"} for item in inventory)
