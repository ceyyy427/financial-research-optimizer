import inspect
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_scene_objects_match_eight_bars_and_named_product_sections():
    from finathink_reel import scenes

    expected = [
        "OpenResearch",
        "ArchitectureBridge",
        "Evidence",
        "KnowledgeMath",
        "QuantResearch",
        "StrategyBacktest",
        "LearningAgent",
        "Signoff",
    ]
    assert [scene.__name__ for scene in scenes.SCENES] == expected
    instances = [scene() for scene in scenes.SCENES]
    assert all(callable(getattr(scene, "render", None)) for scene in instances)
    assert all(len(inspect.signature(scene.render).parameters) == 3 for scene in instances)


def test_scene_helpers_and_opening_assets_are_available():
    from finathink_reel import scenes, theme

    for helper in ("draw_bilingual_title", "draw_card_image", "draw_bridge_wipe"):
        assert callable(getattr(scenes, helper))
    assert Path(theme.ASSET_RESEARCH).is_file()
    assert Path(theme.ASSET_MAP).is_file()


def test_light_post_processing_preserves_editorial_contrast():
    from finathink_reel import chrome

    for settings in chrome.POST.values():
        assert settings["light"] is True
        assert settings["bloom"][0] >= 0.99
        assert settings["chroma"] == 0.0
