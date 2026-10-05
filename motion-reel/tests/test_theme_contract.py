import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _theme():
    return importlib.import_module("finathink_reel.theme")


def test_theme_has_exact_delivery_timing_and_authoring_ratio():
    theme = _theme()
    assert theme.FPS == 30
    assert theme.BPM == 128
    assert theme.BARS == 8
    assert (theme.OUT_W, theme.OUT_H) == (1920, 1080)
    assert (theme.W, theme.H) == (1280, 720)
    assert theme.NFRAMES == 450


def test_theme_has_bilingual_scene_copy_and_cjk_font():
    theme = _theme()
    assert len(theme.SCENES) == 8
    assert all(len(scene) >= 4 for scene in theme.SCENES)
    assert all(scene[2] and scene[3] for scene in theme.SCENES)
    assert Path(theme.CJK_FONT_PATH).is_file()
