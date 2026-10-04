"""Build a reel: soundtrack, N frames, encode, mux.

    python3 -m finathink_reel.build                 full reel
    python3 -m finathink_reel.build --at 3:1.2      one full-resolution frame
    python3 -m finathink_reel.build --stills 5      review stills from one scene
    python3 -m finathink_reel.build --scenes 2,4    re-render only some scenes

Scenes render in parallel, one worker per scene. Each owns its own state and
its own bar, so a worker starting mid-reel is always that scene's first frame.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import subprocess
import time

import numpy as np

from mg.core import Canvas

from . import chrome
from . import scenes as SC
from . import theme as T

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
FRAMES = os.path.join(OUT, "frames")


def scene_objects():
    # one instance per scene, in bar order: SCENES lives in scenes.py
    return [cls() for cls in SC.SCENES]


def render_one(i, ss=2):
    obj = scene_objects()[i]
    os.makedirs(FRAMES, exist_ok=True)
    f0 = int(round(i * T.BAR * T.FPS))
    f1 = int(round((i + 1) * T.BAR * T.FPS))
    for f in range(f0, f1):
        t = f / T.FPS
        tl = t - i * T.BAR
        c = Canvas(T.W, T.H, ss=ss, out=(T.OUT_W, T.OUT_H))
        obj.render(c, tl, t)
        p = c.pass_()
        chrome.draw(p, t, i, chrome.POST[i].get("light", False))
        c.commit()
        chrome.finish(c, t, i)
        c.image().save(os.path.join(FRAMES, f"f{f:04d}.png"))
    return f1 - f0


def render_at(i, tl, ss=2, name=None):
    obj = scene_objects()[i]
    t = i * T.BAR + tl
    c = Canvas(T.W, T.H, ss=ss, out=(T.OUT_W, T.OUT_H))
    obj.render(c, tl, t)
    p = c.pass_()
    chrome.draw(p, t, i, chrome.POST[i].get("light", False))
    c.commit()
    chrome.finish(c, t, i)
    path = os.path.join(OUT, name or f"at_s{i}_{tl:.3f}.png")
    c.image().save(path)
    return path


def render_still(i, tl_list, ss=2, tag=""):
    from PIL import Image

    os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)
    rows = []
    for k, tl in enumerate(tl_list):
        t = i * T.BAR + tl
        c = Canvas(T.W, T.H, ss=ss, out=(T.OUT_W, T.OUT_H))
        scene_objects()[i].render(c, tl, t)
        p = c.pass_()
        chrome.draw(p, t, i, chrome.POST[i].get("light", False))
        c.commit()
        chrome.finish(c, t, i)
        img = c.image()
        img.save(os.path.join(OUT, f"stills/s{i}_{k}_{tl:.2f}{tag}.png"))
        rows.append(img)
    sheet = Image.new("RGB", (rows[0].width, rows[0].height * len(rows)), (0, 0, 0))
    for k, im in enumerate(rows):
        sheet.paste(im, (0, k * im.height))
    sp = os.path.join(OUT, f"sheet_s{i}{tag}.jpg")
    sheet.resize((sheet.width * 3 // 5, sheet.height * 3 // 5), Image.LANCZOS).save(
        sp, quality=88)
    return sp


def build_audio():
    from . import audio as A

    os.makedirs(OUT, exist_ok=True)
    st, sr = A.build()
    A.write_wav(os.path.join(OUT, "track.wav"), st, sr)
    wave, spec = A.analyse(st, sr, fps=T.FPS)
    np.save(os.path.join(OUT, "wave.npy"), wave)
    np.save(os.path.join(OUT, "spec.npy"), spec)
    return os.path.join(OUT, "track.wav")


# GPU first. Measured on this engine's own 1080p frames: h264_nvenc is 3.7x
# faster than libx264 preset slow and 28% smaller, for about 0.9 dB of PSNR.
# The AQ switches are not optional — without them flat gradients and grain
# band in the shadows. libx264 stays as the fallback where NVENC is missing.
NVENC = ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr",
         "-cq", "19", "-b:v", "0", "-spatial_aq", "1", "-temporal_aq", "1",
         "-aq-strength", "12", "-bf", "3", "-pix_fmt", "yuv420p"]
X264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p"]


def _has_nvenc():
    """Ask ffmpeg what it was built with, instead of trying and reading stderr.

    Handing nvenc's own options to a build without that encoder makes ffmpeg
    die on `Unrecognized option 'rc'` — which reads like the render is broken.
    On a machine with no NVIDIA card that noise shows up on every render, and
    it cost a real debugging session before it was understood.
    """
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                             capture_output=True, text=True).stdout
    except OSError:
        return False
    return "h264_nvenc" in out


def _encode_frames(dst, enc):
    return subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-framerate", str(T.FPS),
        "-i", os.path.join(FRAMES, "f%04d.png"), *enc,
        "-movflags", "+faststart", dst,
    ]).returncode


def encode(name="reel"):
    silent = os.path.join(OUT, f"{name}_silent.mp4")
    for e, enc in enumerate([NVENC, X264] if _has_nvenc() else [X264]):
        if _encode_frames(silent, enc) == 0:
            break
        if e == 0:
            print("  nvenc present but failed, falling back to libx264")
    else:
        raise SystemExit("neither h264_nvenc nor libx264 could encode")
    final = os.path.join(OUT, f"{name}.mp4")
    wav = os.path.join(OUT, "track.wav")
    if os.path.exists(wav):
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", silent, "-i", wav,
            # 384k. At 256k the native AAC encoder puts this material's decoded
            # peak above 0 dBFS (measured +0.72 dBFS on a transient-heavy mix).
            "-c:v", "copy", "-c:a", "aac", "-b:a", "384k", "-shortest",
            "-movflags", "+faststart", final,
        ], check=True)
        os.remove(silent)
        return final
    return silent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="all")
    ap.add_argument("--at", default=None)
    ap.add_argument("--stills", type=int, default=None)
    ap.add_argument("--ss", type=int, default=2)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--skip-frames", action="store_true")
    ap.add_argument("--jobs", type=int, default=0)
    args = ap.parse_args()

    if args.at:
        i, tl = args.at.split(":")
        print(render_at(int(i), float(tl), args.ss))
        return
    if args.stills is not None:
        i = args.stills
        print(render_still(i, [T.BAR * (k / 7.0) for k in range(7)], args.ss))
        return

    os.makedirs(OUT, exist_ok=True)
    if not args.no_audio:
        t0 = time.time()
        build_audio()
        print(f"audio  {time.time() - t0:.1f}s")

    idx = list(range(T.BARS)) if args.scenes == "all" else \
        [int(v) for v in args.scenes.split(",")]
    if not args.skip_frames:
        # One worker per scene, and never the whole machine: a render is a long
        # task and the box has to stay usable while it runs. Asking for more
        # than there are scenes only spins up workers with nothing to do.
        want = args.jobs or max(1, (os.cpu_count() or 4) // 3)
        jobs = max(1, min(len(idx), want))
        if args.jobs and args.jobs > jobs:
            print(f"  --jobs {args.jobs} clamped to {jobs} (one worker per scene)")
        t0 = time.time()
        with mp.Pool(jobs) as pool:
            counts = pool.starmap(render_one, [(i, args.ss) for i in idx])
        print(f"frames {sum(counts)} in {time.time() - t0:.1f}s ({jobs} workers)")

    print("out:", encode("finathink_motion_reel"))


if __name__ == "__main__":
    main()
