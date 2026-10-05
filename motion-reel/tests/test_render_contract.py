from pathlib import Path
import json
import subprocess

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "out" / "finathink_motion_reel.mp4"


def _probe():
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,nb_frames,r_frame_rate",
            "-show_entries", "format=duration",
            "-of", "json", str(OUTPUT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_output_metadata_is_15_seconds_1080p30():
    assert OUTPUT.exists(), f"rendered deliverable missing: {OUTPUT}"
    data = _probe()
    stream = data["streams"][0]
    assert (stream["width"], stream["height"]) == (1920, 1080)
    assert stream["r_frame_rate"] == "30/1"
    assert int(stream["nb_frames"]) == 450
    assert abs(float(data["format"]["duration"]) - 15.0) < 0.02


def test_representative_frames_have_visible_dynamic_range():
    stills = sorted((ROOT / "out" / "representative").glob("*.png"))
    assert len(stills) == 8, "expected one extracted representative frame per scene"
    for path in stills:
        image = Image.open(path).convert("RGB")
        extrema = image.getextrema()
        assert any(hi - lo > 30 for lo, hi in extrema), f"frame is too flat: {path}"
