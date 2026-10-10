import functools

import pytest

from finahinking.research.stage_registry import (
    StageRegistry,
    StageRegistryError,
    StageSpec,
    default_stage_registry,
    run_default_workflow_stage,
)


def top_level_stage(**kwargs):
    return {"status": "completed"}


def second_stage(**kwargs):
    return {"status": "completed"}


def alternate_stage(**kwargs):
    return {"status": "completed"}


class Runner:
    def run(self, **kwargs):
        return {"status": "completed"}


def spec(name="workflow", version="v1", runner_key="workflow.runner"):
    return StageSpec(name=name, version=version, runner_key=runner_key)


def test_register_resolve_and_sorted_immutable_snapshot():
    registry = StageRegistry()
    registry.register(spec("zeta", runner_key="zeta.runner"), second_stage)
    registry.register(spec("alpha", runner_key="alpha.runner"), top_level_stage)
    assert registry.resolve("alpha") is top_level_stage
    assert tuple(item.name for item in registry.snapshot()) == ("alpha", "zeta")
    with pytest.raises((TypeError, AttributeError)):
        registry.snapshot()[0].name = "changed"


def test_registry_rejects_duplicates_non_paper_and_unsafe_refs():
    registry = StageRegistry()
    registry.register(spec(), top_level_stage)
    with pytest.raises(StageRegistryError):
        registry.register(spec(), second_stage)
    with pytest.raises(StageRegistryError):
        registry.register(spec("other", runner_key="workflow.runner"), second_stage)
    with pytest.raises(StageRegistryError):
        StageSpec(name="../escape", version="v1", runner_key="escape.runner")
    with pytest.raises(StageRegistryError):
        StageSpec(name="live", version="v1", runner_key="live.runner", paper_only=False)


def test_registry_rejects_lambda_closure_and_bound_method():
    registry = StageRegistry()
    with pytest.raises(StageRegistryError):
        registry.register(spec(), lambda **kwargs: {"status": "completed"})
    captured = "x"

    def closure(**kwargs):
        return {"status": captured}

    with pytest.raises(StageRegistryError):
        registry.register(spec("closure", runner_key="closure.runner"), closure)
    with pytest.raises(StageRegistryError):
        registry.register(spec("bound", runner_key="bound.runner"), Runner().run)
    with pytest.raises(StageRegistryError):
        registry.register(spec("partial", runner_key="partial.runner"), functools.partial(top_level_stage))


def test_registry_rejects_rebound_or_metadata_spoofed_function():
    registry = StageRegistry()
    original = top_level_stage
    original_name = original.__name__
    original_module = original.__module__
    import finahinking.research.stage_registry as module

    original_export = getattr(module, "run_default_workflow_stage", None)
    try:
        original.__name__ = "run_default_workflow_stage"
        original.__qualname__ = "run_default_workflow_stage"
        original.__module__ = "finahinking.research.stage_registry"
        module.run_default_workflow_stage = original
        with pytest.raises(StageRegistryError):
            registry.register(spec(), original)
    finally:
        original.__name__ = original_name
        original.__qualname__ = original_name
        original.__module__ = original_module
        module.run_default_workflow_stage = original_export


def test_digest_is_stable_across_registration_order_and_changes_on_spec():
    first = StageRegistry()
    first.register(spec("zeta", runner_key="zeta.runner"), second_stage)
    first.register(spec("alpha", runner_key="alpha.runner"), top_level_stage)
    second = StageRegistry()
    second.register(spec("alpha", runner_key="alpha.runner"), top_level_stage)
    second.register(spec("zeta", runner_key="zeta.runner"), second_stage)
    assert first.digest() == second.digest()
    second.register(spec("omega", runner_key="omega.runner"), top_level_stage)
    assert first.digest() != second.digest()
    third = StageRegistry()
    third.register(spec("alpha", runner_key="alpha.runner"), alternate_stage)
    fourth = StageRegistry()
    fourth.register(spec("alpha", runner_key="alpha.runner"), top_level_stage)
    assert third.digest() != fourth.digest()


def test_unknown_stage_fails_closed_and_default_has_no_side_effects():
    registry = default_stage_registry()
    assert tuple(item.name for item in registry.snapshot()) == ("workflow",)
    assert registry.resolve("workflow") is run_default_workflow_stage
    with pytest.raises(StageRegistryError):
        registry.resolve("missing")


def test_default_workflow_requires_persisted_manifest_for_success():
    blocked = type("Workflow", (), {"state": type("State", (), {"current_state": "LEARNING_RECORDED", "decision_eligible": True})(), "decision": object(), "manifest": None})()
    from finahinking.research.stage_registry import _workflow_result_payload

    result = _workflow_result_payload(blocked)
    assert result["status"] == "blocked"
    assert result["failure_kind"] == "WORKFLOW_ARTIFACT_UNAVAILABLE"

    malformed = type("Workflow", (), {"state": None})()
    assert _workflow_result_payload(malformed)["status"] == "blocked"
