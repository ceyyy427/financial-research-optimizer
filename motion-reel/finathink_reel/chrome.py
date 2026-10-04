"""HUD chrome and finishing.

The furniture that turns eight unrelated shots into one reel: a brand bug, a
running timecode, an N-dot scene indicator, a scene name, and a progress bar.
Scenes draw their content; this draws the frame around it.

`POST` holds the per-scene finishing settings and `finish()` walks the chain:
bloom -> chromatic aberration -> grade -> vignette -> cut flash -> grain ->
tone map. The cut flash goes in *after* the vignette, or its corners grey out
and a light burst reads as a grey wash.
"""
from __future__ import annotations

import numpy as np

from mg import fonts as F
from mg.core import corner_brackets

from . import scenes as SC
from . import theme as T

W, H = T.W, T.H
DOT_X, DOT_Y = W / 2.0, 604.0
BAR_Y = H - 4.0


def _tc(t):
    fr = int(round(t * T.FPS))
    return "TC %02d:%02d:%02d" % (fr // (T.FPS * 3600) % 100, fr // T.FPS % 60, fr % T.FPS)


def draw(p, t, scene_i, light=False):
    ink = T.INK if light else T.GREY
    dim = T.SLATE if light else T.GREY_D
    acc = T.ACCENT if light else T.ACCENT_BR

    # --- brand bug, top left: the mark plus the domain
    p.rect(T.HUD_M, T.HUD_TOP - 5.5, 9, 9, acc, 0.95)
    p.rect(T.HUD_M + 3.0, T.HUD_TOP - 2.5, 3, 3, T.PAPER if light else T.INK, 0.95)
    p.text(T.HUD_M + 17, T.HUD_TOP, f"{T.DOMAIN} — {T.STUDIO}", F.mono(T.S_HUD), ink,
           T.TRACK_HUD)

    # --- product reel title, top right
    p.text(W - T.HUD_M, T.HUD_TOP, "PRODUCT REEL // 15 SEC", F.mono(T.S_HUD), ink,
           T.TRACK_HUD, anchor="rs")

    _ = SC  # scenes owns the mark helper; chrome keeps to vector furniture

    # --- timecode, bottom left
    p.text(T.HUD_M, T.HUD_BOT, _tc(t), F.mono(T.S_HUD), ink, T.TRACK_HUD)

    # --- scene name, bottom right
    sid, sname, _ = T.SCENES[scene_i]
    wlab = p.text(W - T.HUD_M, T.HUD_BOT, f"SCENE {sid} / {sname}", F.mono(T.S_HUD),
                  ink, T.TRACK_HUD, anchor="rs")
    p.rect(W - T.HUD_M - wlab - 11, T.HUD_BOT - 3.0, 5, 5, acc, 0.9)

    # --- eight-dot indicator
    gap = 15.0
    x0 = DOT_X - gap * (T.BARS - 1) / 2.0
    for i in range(T.BARS):
        cx = x0 + i * gap
        if i == scene_i:
            p.rect(cx - 6.5, DOT_Y - 1.6, 13, 3.2, acc, 1.0, radius=1.6)
        elif i < scene_i:
            p.dot(cx, DOT_Y, 2.0, ink, 0.62)
        else:
            p.dot(cx, DOT_Y, 2.0, dim, 0.55)

    corner_brackets(p, W, H, acc, 26, 15, 0.34 if not light else 0.30)

    # --- progress bar
    p.rect(0, BAR_Y, W, 3.0, dim, 0.30)
    prog = t / T.DUR
    p.rect(0, BAR_Y, W * prog, 3.0, acc, 0.95)
    p.rect(W * prog - 1.5, BAR_Y - 1.0, 3.0, 5.0, T.WHITE if not light else T.INK, 0.85)

    # --- live status chip, bottom-centre-left: the panel's own idiom
    up = min(1.0, t / 0.35)
    if up > 0.01:
        p.dot(T.HUD_M + 4, T.HUD_BOT - 14, 3.0, T.ACCENT_BR,
              up * (0.55 + 0.45 * np.sin(t * 4.6)))
        p.text(T.HUD_M + 13, T.HUD_BOT - 11, "ONLINE", F.mono(8.5), T.ACCENT_LT,
               T.TRACK_HUD, alpha=up * 0.9)


# --------------------------------------------------------------------------
# finishing — the default neon look; retune per film
# --------------------------------------------------------------------------
POST = {
    0: dict(bloom=(0.70, 0.24), chroma=1.4, vig=0.44, grain=0.0120, scan=0.014, white=1.16),
    1: dict(bloom=(0.68, 0.26), chroma=1.8, vig=0.46, grain=0.0140, scan=0.016, white=1.16),
    2: dict(bloom=(0.70, 0.26), chroma=1.3, vig=0.54, grain=0.0125, scan=0.016, white=1.16),
    3: dict(bloom=(0.66, 0.28), chroma=1.3, vig=0.50, grain=0.0130, scan=0.016, white=1.18),
    4: dict(bloom=(0.60, 0.30), chroma=1.2, vig=0.54, grain=0.0135, scan=0.016, white=1.20),
    5: dict(bloom=(0.95, 0.26), chroma=0.9, vig=0.16, grain=0.0060, scan=0.000, white=1.00,
            light=True),
    6: dict(bloom=(0.64, 0.28), chroma=2.2, vig=0.52, grain=0.0150, scan=0.018, white=1.16),
    7: dict(bloom=(0.70, 0.26), chroma=1.5, vig=0.44, grain=0.0125, scan=0.014, white=1.16),
}


def finish(c, t, scene_i):
    q = dict(POST[scene_i])
    q.update(getattr(c, "post_override", None) or {})

    c.bloom(thr=q["bloom"][0], knee=q["bloom"][1])
    c.chroma(q["chroma"])

    if q.get("light"):
        c.rgb = np.clip(c.rgb, 0.0, 1.0)
        c.vignette(q["vig"], 2.0)
    else:
        # cool-to-brand grade: lift the blue channel least, the green most, so
        # shadows stay navy and the brand green keeps its hue under bloom
        c.rgb = c.rgb * np.asarray((1.0, 1.02, 1.03), np.float32).reshape(1, 1, 3)
        c.rgb = c.rgb + np.asarray((0.004, 0.010, 0.018), np.float32).reshape(1, 1, 3)
        l = c.rgb.mean(axis=2, keepdims=True)
        c.rgb = np.clip(l + (c.rgb - l) * 1.07, 0.0, 1.0)
        c.vignette(q["vig"], 1.7)

    # light-burst on every cut: the bar line is also the downbeat
    tl = t % T.BAR
    k = 1.00 if scene_i == 0 else (0.72 if scene_i == 1 else 0.58)
    if scene_i in (4, 7):
        k = 0.72
    if scene_i == 2:
        k = 0.40      # a 3D plate cannot take a full whiteout on the cut
    flash = k * np.exp(-tl / 0.055)
    if scene_i == 5:
        flash = 0.90 * np.exp(-tl / 0.10)
    if flash > 0.004:
        # a green-biased burst rather than a neutral white one
        c.add += flash * np.asarray((0.86, 1.0, 0.90), np.float32).reshape(1, 1, 3)

    if q["scan"]:
        c.scanlines(q["scan"], 3)
    c.grain(q["grain"])
    c.tonemap(0.80 if not q.get("light") else 0.86)
    return c
