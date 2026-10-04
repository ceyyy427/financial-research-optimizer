from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_opening_assets_exist_with_expected_dimensions():
    expected = {
        "finathink-research-splash.jpg": (900, 900),
        "finathink-splash-map.jpg": (1536, 1024),
    }
    for name, dimensions in expected.items():
        path = ROOT / "assets" / name
        assert path.is_file(), path
        with Image.open(path) as image:
            assert image.size == dimensions
