"""The eight scenes — one per bar of the 128 BPM grid, same grammar as reel/.

Everything on screen is English, and every claim on screen is structural
(platforms, component counts, UI states) rather than a performance number, so
nothing here reads as a benchmark the product did not make.
"""
from __future__ import annotations

import os

import numpy as np

from mg import anim as A
from mg import fonts as F
from mg import three as TH
from mg.core import clip01, gauss, radial, rgb01

from . import theme as T

W, H = T.W, T.H
BEAT = T.BEAT
CX, CY = W / 2.0, H / 2.0
# The assembly scene samples its target from a logo bitmap. Ship one at
# <project>/assets/mark.png (any RGBA PNG with a transparent background).
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = os.path.join(_REPO, "assets", "mark.png")


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------
def _mono(p, x, y, s, color, size=None, track=None, alpha=1.0, anchor="ls"):
    return p.text(x, y, s, F.mono(size or T.S_TAG), color,
                  T.TRACK_HUD if track is None else track, anchor, alpha)


def reveal_chars(p, x, y, s, f, color, track=0.0, anchor="ls", prog=1.0, alpha=1.0):
    n = len(s)
    wdt = F.measure(f, s, track)
    x0 = x - wdt / 2.0 if anchor[0] == "m" else (x - wdt if anchor[0] == "r" else x)
    xs = F.kerned_layout(f, s, track)
    for i, ch in enumerate(s):
        a = float(np.clip(prog * n - i, 0.0, 1.0))
        if a > 0.01:
            p.text(x0 + xs[i], y, ch, f, color, 0.0, "ls" if anchor[1] == "s" else anchor[1],
                   alpha * a)
    return wdt


def plate(c, center, tint, gain=1.0, rx=640, ry=300):
    c.add += (np.asarray(tint, np.float32).reshape(1, 1, 3) * gain
              * gauss(W, H, CX, center, rx, ry)[..., None])


def mark(c, x, y, h=90.0, alpha=1.0, tint=None, glow=0.0):
    """The pagoda mark, sized by height."""
    im_h = 2340.0
    c.blit(MARK, x, y, scale=h / im_h, alpha=alpha, tint=tint)
    if glow > 0:
        c.blit(MARK, x, y, scale=h / im_h * 1.06, alpha=alpha * 0.5 * glow, tint=tint,
               mode="add")


def status_pill(p, x, y, label, color, alpha=1.0, blink=1.0):
    """The panel's own status chip: a dot plus letterspaced caps."""
    w = F.measure(F.ui(10, 600), label.upper(), 2.4) + 34
    p.rect(x - w / 2, y - 11, w, 22, color, 0.14 * alpha)
    p.rect(x - w / 2, y - 11, 2.4, 22, color, 0.95 * alpha)
    p.dot(x - w / 2 + 15, y, 3.2, color, alpha * blink)
    p.text(x - w / 2 + 26, y + 3.6, label.upper(), F.ui(10, 600), color, 2.4, "ls",
           alpha * 0.92)
    return w


# --------------------------------------------------------------------------
# 01 / OPEN — the title build
# --------------------------------------------------------------------------
class Open:
    Y_MARK = 250.0
    Y_HERO = 410.0
    Y_RULE = 482.0
    Y_SUB1 = 528.0
    Y_SUB2 = 558.0

    def render(self, c, tl, t):
        c.clear(T.INK)
        settle = A.out_expo(clip01(tl / 1.3), 3.0)
        hz = 372 + 92 * settle
        breath = 1.0 + 0.05 * np.sin(t * 1.9)
        c.add += gauss(W, H, CX, hz, 620, 116 * breath)[..., None] * np.array(
            [0.022, 0.072, 0.038], np.float32)
        c.add += gauss(W, H, CX, hz - 24, 900, 240)[..., None] * np.array(
            [0.010, 0.030, 0.018], np.float32)

        p = c.pass_()
        for i in range(1, 16):
            p.line([(W * i / 16.0, 0), (W * i / 16.0, H)], T.ACCENT, 0.7, 0.030)
        for j in range(1, 9):
            p.line([(0, H * j / 9.0), (W, H * j / 9.0)], T.ACCENT, 0.7, 0.024)
        for a, wd in ((0.10, 3.0), (0.06, 1.3)):
            p.line([(96, hz), (W - 96, hz)], T.ACCENT_BR, wd,
                   a * (0.45 + 0.55 * settle) * breath)

        # --- the mark drops in above the wordmark
        e0 = A.out_expo(clip01((tl - 0.04) / 0.55), 3.4)
        if e0 > 0.01:
            mark(c, CX, self.Y_MARK + (1.0 - e0) * -52, h=152 * (0.86 + 0.14 * e0),
                 alpha=e0, glow=0.55 + A.pulse(tl - 0.04, 7.0) * 1.4)

        # --- the wordmark, letters rising one stagger step each.
        # The size is solved so the line occupies 82% of the frame: hard-coding
        # it means a longer brand name overflows the edges.
        word = f"{T.BRAND} {T.PRODUCT}"
        tr_ratio = T.TRACK_HERO / T.S_HERO
        size = F.fit_size(word, W * 0.82, F.display, tr_ratio)
        fh = F.display(size)
        tr = tr_ratio * size
        wm = F.measure(fh, word, tr)
        xm = CX - wm / 2.0
        xs = F.kerned_layout(fh, word, tr)
        for i, ch in enumerate(word):
            e = A.out_expo(clip01((tl - 0.14 - i * 0.042) / 0.60), 4.2)
            p.text(xm + xs[i], self.Y_HERO + (1.0 - e) * 106, ch, fh, T.WHITE, 0.0, "lm",
                   A.out_expo(clip01((tl - 0.14 - i * 0.042) / 0.32), 5.0))

        # --- green rule wiping under the word, then the two technical lines
        wipe = A.out_expo(clip01((tl - 0.56) / 0.38), 4.0)
        if wipe > 0.001:
            x0, x1 = xm - 9, xm + wm + 9
            p.line([(x0, self.Y_RULE), (x0 + (x1 - x0) * wipe, self.Y_RULE)],
                   T.ACCENT, 2.6, 0.96)
        if tl > 0.66:
            half = (wm / 2.0 + 40) * A.out_expo(clip01((tl - 0.92) / 0.45), 4.0)
            p.line([(CX - half, self.Y_RULE + 30), (CX + half, self.Y_RULE + 30)],
                   T.ACCENT_BR, 1.4, 0.72)
        if tl > 0.72:
            reveal_chars(p, CX, self.Y_SUB1, T.TAGLINE, F.mono(17), T.WHITE, 3.4, "ms",
                         A.out_expo(clip01((tl - 0.72) / 0.45), 4.0), 0.95)
        if tl > 0.94:
            reveal_chars(p, CX, self.Y_SUB2, f"{T.PLATFORMS} · {T.DOMAIN}",
                         F.mono(10.5), T.ACCENT_LT, 2.2, "ms",
                         A.out_expo(clip01((tl - 0.94) / 0.5), 3.4), 0.92)
        if tl > 1.12:
            # the product's own vocabulary, as a quiet closing row
            e = A.out_expo(clip01((tl - 1.12) / 0.5), 3.6)
            row = "WEBSITE · DATABASE · DOCKER · FIREWALL · SSL · BACKUP · MONITOR"
            _mono(p, CX, 600, row, T.GREY, 9.5, 2.0, e * 0.72, "ms")
        c.commit()


# --------------------------------------------------------------------------
# 02 / KINETIC TYPE — one word per beat, four treatments
# --------------------------------------------------------------------------
class KineticType:
    def render(self, c, tl, t):
        b = min(len(T.KINETIC_WORDS) - 1, int(tl / BEAT))
        tb = tl - b * BEAT
        fw = F.display(T.S_WORD)
        word = T.KINETIC_WORDS[b]
        sub = T.KINETIC_SUBS[b]
        [self._secure, self._simple, self._stable, self._fast][b](c, tb, fw, word, sub)

    def _secure(self, c, tb, fw, word, sub):
        """Shield: heavy word, marker rule running in from the left."""
        c.clear(T.BG0)
        plate(c, 470, (0.012, 0.040, 0.022), 1.0, 560, 190)
        e = A.out_expo(tb / 0.34, 4.2)
        sx, sy = 1.0 + (1.0 - e) * 0.40, 1.0 - (1.0 - e) * 0.24
        p = c.pass_()
        # a shield outlined behind the word
        yy = CY - 22.0
        # the shield has to contain the word, or it reads as a stray hexagon
        sh = [(CX, yy - 132), (CX + 268, yy - 84), (CX + 268, yy + 30),
              (CX, yy + 128), (CX - 268, yy + 30), (CX - 268, yy - 84)]
        p.path(sh, T.ACCENT, 1.8, 0.44, closed=True)
        p.path([(x, y) for x, y in sh], T.ACCENT, 1.0, 0.16, closed=True)
        p.line([(CX - 268, yy - 84), (CX + 268, yy - 84)], T.ACCENT, 1.0, 0.20)
        wdt = F.measure(fw, word, T.TRACK_WORD)
        p.text_scaled(CX, yy, word, fw, T.WHITE, T.TRACK_WORD, sx, sy, "mm",
                      A.out_expo(tb / 0.20, 5.5))
        if tb > 0.10:
            wp = A.out_expo(clip01((tb - 0.10) / 0.26), 4.6)
            x_end = CX - wdt / 2.0 - 22
            p.line([(64, yy), (64 + (x_end - 64) * wp, yy)], T.ACCENT, 2.2, 0.95)
            p.line([(x_end + 10, yy), (x_end + 10 + 34 * wp, yy)], T.ALT, 1.4, 0.85)
        top, _bot = F.cap_band(fw, yy)
        _mono(p, CX, CY + 96, sub, T.ACCENT_BR, 11, 3.0, 0.88, "ms")
        _mono(p, CX - 190, top - 22, "INSPECT", T.GREY, 9.5, 1.6, 0.7, "ls")
        _mono(p, CX + 190, top - 22, "THEN ALLOW", T.GREY, 9.5, 1.6, 0.7, "rs")
        c.commit()

    def _simple(self, c, tb, fw, word, sub):
        """Full-bleed brand green, near-black type: the loudest brand beat."""
        c.clear(T.BG0)
        p = c.pass_()
        wp = A.out_quint(tb / 0.20)
        ph = H * min(1.0, wp)
        y0, y1 = CY - ph / 2.0, CY + ph / 2.0
        p.rect(0, y0, W, y1 - y0, grad=(T.ACCENT_BR, (18, 122, 46)))
        p.line([(0, y0), (28, y0)], T.INK, 2.0, 0.85)
        p.line([(0, y1), (28, y1)], T.INK, 2.0, 0.85)
        p.line([(W, y0), (W - 28, y0)], T.INK, 2.0, 0.85)
        p.line([(W, y1), (W - 28, y1)], T.INK, 2.0, 0.85)
        rng = np.random.default_rng(21)
        for i in range(24):
            yy = CY - 118 + i * 10.4 + rng.normal(0, 1.4)
            ph2 = (tb * 2.2 + i * 0.083) % 1.0
            ln = 90 + 250 * rng.random()
            x = -ln + (W + 2 * ln) * ph2
            a = 0.18 * (1.0 - abs(ph2 - 0.5) * 1.4) * (0.4 + 0.6 * rng.random())
            p.line([(x, yy), (x + ln, yy)], T.INK, 1.6, max(0.0, a * 0.5))
        e = A.out_expo(tb / 0.26, 5.0)
        dx = (1.0 - e) * 180
        p.text(CX + dx, CY - 22, word, fw, T.INK, T.TRACK_WORD, "mm",
               A.out_expo(tb / 0.16, 6.0))
        _mono(p, CX, CY + 84, sub, T.INK, 11, 3.0, 0.78, "ms")
        _mono(p, 64, CY - 150, "ONE CLICK", T.INK, 9.5, 1.6, 0.62, "ls")
        _mono(p, W - 64, CY - 150, "NO CLI", T.INK, 9.5, 1.6, 0.62, "rs")
        c.commit()

    def _stable(self, c, tb, fw, word, sub):
        """Uptime: blueprint grid, a flat line running the whole frame."""
        c.clear(T.BG0)
        plate(c, 400, (0.010, 0.034, 0.020), 1.0, 620, 210)
        p = c.pass_()
        for i in range(1, 32):
            p.line([(W * i / 32.0, 0), (W * i / 32.0, H)], T.ACCENT, 0.7, 0.034)
        for j in range(1, 18):
            p.line([(0, H * j / 18.0), (W, H * j / 18.0)], T.ACCENT, 0.7, 0.028)
        for i in range(1, 8):
            p.line([(W * i / 8.0, 0), (W * i / 8.0, H)], T.ACCENT, 1.0, 0.070)
        alpha = A.out_expo(tb / 0.30, 4.4)
        yw = CY - 10
        wdt = F.measure(fw, word, T.TRACK_WORD)
        p.text(CX, yw, word, fw, T.WHITE, T.TRACK_WORD, "mm", alpha)
        # the uptime trace: dead flat, drawn in on the beat
        d = A.out_expo(clip01((tb - 0.10) / 0.75), 2.6)
        trace = [(64 + (W - 128) * i / 240.0,
                  CY + 132 - 26 * float(np.sin(i * 0.11)) - 6 * float(np.sin(i * 0.47)))
                 for i in range(241)]
        p.path([(x, y) for x, y in trace if x <= 64 + (W - 128) * d], T.ACCENT_BR, 1.8, 0.95)
        p.line([(64, CY + 132), (W - 64, CY + 132)], T.SLATE, 1.0, 0.6)
        if tb > 0.30:
            dd = A.out_expo(clip01((tb - 0.30) / 0.4), 4.0)
            _mono(p, CX, CY + 176, "UPTIME WATCH · 24/7 MONITORING", T.ACCENT_LT, 10,
                  2.4, 0.9 * dd, "ms")
            _mono(p, 64, CY - 150, "TRACE 24 H", T.GREY, 9.5, 1.6, 0.8 * dd)
            _mono(p, W - 64, CY - 150, "ALERT ON THRESHOLD", T.GREY, 9.5, 1.6, 0.8 * dd, "rs")
        _mono(p, CX, CY + 96, sub, T.ACCENT_BR, 11, 3.0, 0.88, "ms")
        c.commit()

    def _fast(self, c, tb, fw, word, sub):
        """Bright green with gold shockwaves."""
        c.clear(T.INK)
        hit = A.pulse(tb, 7.0)
        c.add += (0.26 + 0.9 * hit) * gauss(W, H, CX, CY, 430, 265)[..., None] * np.array(
            [0.10, 0.44, 0.16], np.float32)
        p = c.pass_()
        for i in range(4):
            r = A.ease_path([(0.0, 42 + i * 30), (0.55, 310 + i * 92)], min(tb, 0.62))
            a = max(0.0, (1.0 - tb / 0.55)) * (0.40 - i * 0.08)
            if a > 0.01:
                p.ellipse(CX, CY - 10, r, r, T.ALT if i % 2 else T.ACCENT_BR, a, width=1.6)
        e = A.out_elastic(tb / 0.5, 0.34, 5.6)
        yy = CY - 10 + (1.0 - e) * 26
        p.text(CX, yy, word, fw, T.ACCENT_BR, T.TRACK_WORD, "mm",
               A.out_expo(tb / 0.16, 6.0))
        p.text(CX, yy, word, fw, T.WHITE, T.TRACK_WORD, "mm",
               0.90 * A.out_expo(tb / 0.20, 5.0))
        _mono(p, 64, CY - 150, "MINUTES, NOT HOURS", T.ACCENT_LT, 10, 1.8,
              0.9 * A.out_expo(tb / 0.3, 4), "ls")
        _mono(p, W - 64, CY - 150, "DEPLOY ×4", T.ALT, 10, 1.8,
              0.9 * A.out_expo(tb / 0.3, 4), "rs")
        _mono(p, CX, CY + 118, sub, T.WHITE, 11, 3.0, 0.9 * A.out_expo(tb / 0.34, 4), "ms")
        c.commit()


# --------------------------------------------------------------------------
# 03 / HARDWARE — a 12U rack, modelled and rendered in 3D
# --------------------------------------------------------------------------
class Dimensional:
    KEY = "bt_rack"
    NODES = 6

    def _cloud(self):
        if Dimensional.KEY in _CACHE:
            return _CACHE[Dimensional.KEY]
        parts, norms, wts = [], [], []
        for i in range(self.NODES):
            y = (i - (self.NODES - 1) / 2.0) * 0.42
            P, N, w = TH.box_surface((0.0, y, 0.0), (2.90, 0.32, 1.00), 150, 40,
                                     front_bias=4.0)
            parts.append(P)
            norms.append(N)
            wts.append(w)
        rail = []
        for sx in (-1, 1):
            P, N, w = TH.box_surface((sx * 1.53, 0.0, 0.0), (0.10, 3.05, 1.10), 150, 40,
                                     front_bias=1.0)
            rail.append((P, N, w))
        for P, N, w in rail:
            parts.append(P)
            norms.append(N)
            wts.append(w)
        out = (np.concatenate(parts, 0), np.concatenate(norms, 0),
               np.concatenate(wts, 0))
        _CACHE[Dimensional.KEY] = out
        return out

    def render(self, c, tl, t):
        c.clear(T.BG0)
        plate(c, CY, (0.008, 0.026, 0.016), 1.0, 700, 400)
        p = c.pass_()
        p.text(CX, CY + 16, "OBJECT", F.display(196), T.ACCENT, -5.0, "mm", 0.030)
        for i in range(1, 20):
            p.line([(W * i / 20.0, 96), (W * i / 20.0, H - 96)], T.ACCENT, 0.7, 0.030)
        for j in range(1, 12):
            p.line([(40, 96 + (H - 192) * j / 12.0), (W - 40, 96 + (H - 192) * j / 12.0)],
                   T.ACCENT, 0.7, 0.024)
        c.commit()

        P, N, wt = self._cloud()
        # a modest turn: at 35-65° a tall stack reads as a leaning tower rather
        # than as a rack seen at an angle
        ang = 0.30 + A.ease_path([(0.0, 0.0), (T.BAR, 0.26)], tl)
        tilt = -0.17
        bob = np.sin(t * 1.1) * 3.0
        Pp, Np = TH.rot_x(P, tilt), TH.rot_x(N, tilt)
        Pp, Np = TH.rot_y(Pp, ang), TH.rot_y(Np, ang)
        cam = TH.Camera(eye=(0.0, 0.34, 11.4), target=(0, 0, 0), fov=30, w=W, h=H,
                        shift=(0.0, 42.0 + bob))
        cov, lum, dep = TH.render(cam, Pp, Np, splat=2, soften=1, ambient=0.13,
                                  key_gain=1.25, rim_gain=1.05)
        rgb = c.rgb
        # body: brushed metal. The first pass used 0.10 + lum*0.55, which made the
        # rack a black shape on a dark plate.
        grey = np.clip(0.13 + lum * 0.74, 0, 1)
        metal = np.stack([grey * 0.92, grey, grey * 0.99], -1)
        rgb = rgb * (1.0 - (cov * 0.96)[..., None]) + metal * (cov * 0.96)[..., None]
        # front panels catch the brand colour, so the object reads as this brand
        front = cov * clip01((lum - 0.34) / 0.42)
        ink = np.asarray(rgb01(T.ACCENT_BR), np.float32).reshape(1, 1, 3)
        rgb = rgb * (1.0 - (front * 0.34)[..., None] * (1.0 - ink))
        c.rgb = np.clip(rgb, 0, 1)

        # --- front-panel detail, drawn in the plane of each face
        # The corners are rotated and projected exactly as the cloud was, so the
        # vents and bays sit in the chassis in perspective instead of being
        # approximated in screen space.
        def proj(pts):
            q = TH.rot_y(TH.rot_x(np.asarray(pts, np.float32), tilt), ang)
            r = cam.project(q)
            return [(float(p[0]), float(p[1])) if p[2] > 0 else None for p in r]

        p = c.pass_()
        a = A.out_expo(clip01((tl - 0.45) / 0.6), 3.4)
        if a > 0.01:
            hx, hy, hz = 2.90 / 2, 0.32 / 2, 1.00 / 2
            for i in range(self.NODES):
                y = (i - (self.NODES - 1) / 2.0) * 0.42
                col = T.ALT if i == 0 else T.ACCENT_BR
                # vent slats across the middle of the front face
                for k in range(7):
                    y0 = y - hy + 0.055 + k * 0.036
                    seg = proj([(-0.55, y0, hz + 0.004), (0.42, y0, hz + 0.004)])
                    if seg[0] and seg[1]:
                        p.line([seg[0], seg[1]], T.INK, 1.3, 0.42 * a)
                # drive bay on the left, LEDs on the right
                bay = proj([(-hx + 0.10, y - hy + 0.045, hz + 0.006),
                            (-hx + 0.62, y + hy - 0.045, hz + 0.006)])
                if bay[0] and bay[1]:
                    p.rect(min(bay[0][0], bay[1][0]), min(bay[0][1], bay[1][1]),
                           abs(bay[1][0] - bay[0][0]), abs(bay[1][1] - bay[0][1]),
                           T.INK, 0.34 * a)
                for k in range(3):
                    q = proj([(hx - 0.34 + k * 0.11, y - 0.04, hz + 0.008)])[0]
                    if q:
                        blink = 0.5 + 0.5 * np.sin(t * (3.2 + k * 0.9) + i * 1.7 + k)
                        p.dot(q[0], q[1], 2.0, col, a * (0.35 + 0.65 * blink))
                led = proj([(-hx + 0.04, y, hz + 0.008)])[0]
                if led:
                    p.dot(led[0], led[1], 3.4, col, a * (0.55 + 0.45 * np.sin(t * 4 + i)))
        left = ["MESH / CHASSIS", f"BODIES {self.NODES}", "NIC 16", "PSU 2N",
                "FANS 12"]
        for i, s in enumerate(left):
            _mono(p, 64, 152 + i * 17, s, T.ACCENT_BR if i == 0 else T.GREY, 9.5, 1.5,
                  a * (0.9 if i else 1.0))
        right = ["BUILD / PYTHON", "MOTION 30F", "POINTS 900K", "SOURCE OPEN"]
        for i, s in enumerate(right):
            _mono(p, W - 64, 152 + i * 17, s, T.ACCENT_BR if i == 0 else T.GREY, 9.5, 1.5,
                  a * (0.9 if i else 1.0), "rs")
        _mono(p, CX, 624, "MODELLED IN PYTHON · POINT-CLOUD RENDER · NO EXTERNAL MESH",
               T.GREY, 9.5, 1.6, a * 0.85, "ms")
        c.commit()


_CACHE = {}


# --------------------------------------------------------------------------
# 04 / MONITOR — the panel's own readouts, dark
# --------------------------------------------------------------------------
class Readouts:
    def render(self, c, tl, t):
        c.clear(T.BG0)
        plate(c, 300, (0.008, 0.028, 0.018), 1.0, 700, 220)
        p = c.pass_()
        a = A.out_expo(tl / 0.4, 4.5)
        p.text(CX, 128, "MONITOR", F.display(T.S_MONO), T.WHITE, -3.0, "mm", a)
        _mono(p, CX, 176, "CPU · MEMORY · DISK · NETWORK — LIVE IN THE PANEL", T.ACCENT_BR,
              10.5, 3.0, A.out_expo(clip01((tl - 0.16) / 0.5), 4.0), "ms")
        _mono(p, 64, 128, "UPDATED 1 S", T.GREY, 10, 1.8, 0.9 * a)
        _mono(p, W - 64, 128, "DARK THEME", T.GREY, 10, 1.8, 0.9 * a, "rs")

        # --- four ring gauges, nudged on every beat
        beat_i = int(tl / BEAT)
        for i, (name, base, col) in enumerate(T.GAUGES):
            e = A.out_expo(clip01((tl - 0.28 - i * 0.12) / 0.55), 3.6)
            if e <= 0.01:
                continue
            gx = 208.0 + i * 288.0
            gy = 320.0
            r = 62.0
            wob = 0.045 * np.sin(t * 2.1 + i * 1.3) + 0.02 * np.sin(t * 7.3 + i)
            v = clip01(base + wob + (0.03 if beat_i % 2 == 0 else -0.015))
            p.ellipse(gx, gy, r, r, T.SLATE, 0.9, width=7.0)
            p.arc(gx, gy, r, r, -90, -90 + 360 * v * e, col, 7.0, 1.0)
            p.arc(gx, gy, r, r, -90, -90 + 360 * v * e, T.WHITE, 2.0, 0.45)
            p.text(gx, gy + 4, f"{int(round(v * 100))}", F.display(38), T.WHITE, -1.0,
                   "mm", e)
            p.text(gx, gy + 30, "%", F.mono(12), T.GREY, 0, "mm", e * 0.9)
            _mono(p, gx, gy + 98, name, col, 12, 3.2, e, "ms")
        c.commit()

        # --- history trace across the frame, scrolling with time
        p = c.pass_()
        a2 = A.out_expo(clip01((tl - 0.62) / 0.6), 3.4)
        if a2 > 0.01:
            base_y = 560.0
            pts = []
            n = 150
            for i in range(n):
                u = i / (n - 1.0)
                x = 64 + (W - 128) * u
                ph = t * 0.9 + u * 7.0
                v = (0.42 + 0.22 * np.sin(ph) + 0.12 * np.sin(ph * 2.7 + 1.1)
                     + 0.07 * np.sin(ph * 6.3 + 0.4))
                pts.append((x, base_y - v * 132 * a2))
            p.path(pts, T.ACCENT_BR, 1.8, 0.95)
            p.path([(x, y + 30) for x, y in pts], T.ACCENT, 1.1, 0.30)
            for j in range(5):
                yy = base_y - j * 33
                p.line([(64, yy), (W - 64, yy)], T.SLATE, 1.0, 0.35)
                _mono(p, 58, yy + 3.5, f"{j * 25}", T.GREY_D, 8.5, 1.0, 0.9 * a2, "rs")
            p.line([(64, base_y), (W - 64, base_y)], T.GREY_D, 1.2, 0.8)
            for i, (name, val) in enumerate(T.METRICS):
                x = 64 + i * 300
                _mono(p, x, 620, name, T.GREY, 9.5, 1.6, 0.9 * a2)
                _mono(p, x + 96, 620, val, T.ACCENT_LT, 12, 1.6, a2, "ls")
            _mono(p, W - 64, 620, "SPARKLINE 24 H", T.GREY, 9.5, 1.6, 0.85 * a2, "rs")
        c.commit()


# --------------------------------------------------------------------------
# 05 / TRAFFIC — streamlines through a curl field, as ingress/egress
# --------------------------------------------------------------------------
class Flow:
    N = 2400
    K = 13
    STEP = 4.4
    SUBS = 2
    DECAY = 0.62
    BASE = (27.0, 7.5)
    TURB = 790.0

    def __init__(self, seed=9):
        rng = np.random.default_rng(seed)
        self.rng = rng
        self.buf = np.zeros((H, W, 3), np.float32)
        self.span = (0.35 + 0.65 * rng.random(self.N)).astype(np.float32)
        self.gain = (0.50 + 0.85 * rng.random(self.N)).astype(np.float32)
        k = 4
        self.kk = (rng.random((k, 2)) * 2 - 1).astype(np.float32) * np.array(
            [0.0090, 0.0210], np.float32)
        self.ph = (rng.random(k) * 6.283).astype(np.float32)
        self.am = (rng.random(k).astype(np.float32) * 0.6 + 0.7)
        self.om = (rng.random(k).astype(np.float32) * 0.5 + 0.30) * (2 * rng.choice([-1, 1], k))
        self._respawn(self.N, first=True)
        r = 2.0
        n = int(np.ceil(r))
        ys, xs = np.mgrid[-n:n + 1, -n:n + 1]
        d = np.sqrt(ys ** 2 + xs ** 2)
        wgt = np.clip(1.0 - d / (r + 0.8), 0.0, None) ** 2.0
        m = wgt > 0.02
        self._bo = np.stack([ys[m], xs[m]], -1).astype(np.int32)
        self._bw = wgt[m].astype(np.float32)

    def _respawn(self, nb, first=False):
        rng = self.rng
        gx = rng.normal(0.0, 0.42, nb).clip(-1.10, 1.10)
        gy = rng.normal(0.0, 0.34, nb).clip(-1.05, 1.05)
        x = CX + gx * (W * 0.55)
        y = 424 + gy * 268.0
        if first:
            self.pos = np.stack([x, y], -1).astype(np.float32)
        else:
            self.pos[self._bad] = np.stack([x, y], -1).astype(np.float32)

    def _psi(self, x, y, t):
        s = np.zeros_like(x)
        for i in range(len(self.am)):
            s += self.am[i] * np.sin(self.kk[i, 0] * x + self.kk[i, 1] * y
                                     + self.om[i] * t + self.ph[i])
        return s

    def _field(self, x, y, t):
        h = 2.0
        dy = (self._psi(x, y + h, t) - self._psi(x, y - h, t)) / (2 * h)
        dx = (self._psi(x + h, y, t) - self._psi(x - h, y, t)) / (2 * h)
        vx = dy * self.TURB + self.BASE[0]
        vy = -dx * self.TURB + self.BASE[1]
        ox, oy = x - CX, y - 424.0
        vx += -oy * 0.020
        vy += ox * 0.020
        spine = 424.0 + 46.0 * np.sin(x * 0.0055 + 0.8)
        vy += (spine - y) * 0.011
        vy += 11.0 * np.sin(x * 0.0033 + 1.7)
        return vx, vy

    def render(self, c, tl, t):
        K, L, S = self.K, self.STEP, self.SUBS
        x = self.pos[:, 0].copy()
        y = self.pos[:, 1].copy()
        pts = [(x.copy(), y.copy())]
        speed = np.zeros(self.N, np.float32)
        for _ in range(K):
            vx, vy = self._field(x, y, t * 0.5)
            sp = np.sqrt(vx * vx + vy * vy) + 1e-3
            speed += sp
            x = x + vx / sp * L
            y = y + vy / sp * L
            pts.append((x.copy(), y.copy()))
        speed /= K
        sn = np.clip(speed / 165.0, 0.0, 1.0)
        # brand green core, pale green tips, a few gold strands for accent
        gold = (np.arange(self.N) % 37 == 0).astype(np.float32)
        cr, cg, cb = 0.16 + 0.24 * sn, 0.62 + 0.36 * sn, 0.26 + 0.30 * sn
        cr = cr * (1 - gold) + 0.95 * gold
        cg = cg * (1 - gold) + 0.78 * gold
        cb = cb * (1 - gold) + 0.10 * gold
        cols = np.stack([cr, cg, cb], -1).astype(np.float32)
        near = np.exp(-(((pts[0][1] - 424.0) / 210.0) ** 2))
        energy = ((0.235 + 0.235 * sn) * self.gain * (0.55 + 0.80 * near)).astype(np.float32)

        bo, bw = self._bo, self._bw
        nT = len(bw)
        acc = [np.zeros(H * W, np.float32) for _ in range(3)]
        span = self.span * (0.45 + 0.55 * np.exp(-(((pts[0][1] - 424.0) / 235.0) ** 2)))
        for k in range(K):
            fpos = (k + 0.5) / float(K)
            keep = np.clip(1.0 - fpos / np.maximum(span, 1e-3), 0.0, None)
            taper = np.where(fpos <= span, keep ** 0.45, 0.0)
            en = (energy * taper).astype(np.float32)
            if en.max() <= 1e-4:
                continue
            x0, y0 = pts[k]
            x1, y1 = pts[k + 1]
            for j in range(1, S + 1):
                f = j / float(S)
                px = x0 + (x1 - x0) * f
                py = y0 + (y1 - y0) * f
                ix = np.round(px[:, None] + bo[None, :, 1]).astype(np.int32)
                iy = np.round(py[:, None] + bo[None, :, 0]).astype(np.int32)
                msk = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H) & (en[:, None] > 1e-4)
                if not msk.any():
                    continue
                idx = (iy[msk].astype(np.int64) * W + ix[msk])
                ww = (en[:, None] * bw[None, :])[msk]
                for ch in range(3):
                    cv = np.broadcast_to(cols[:, None, ch], (self.N, nT))[msk]
                    acc[ch] += np.bincount(idx, weights=ww * cv, minlength=H * W)
        self.buf *= self.DECAY
        for ch in range(3):
            self.buf[..., ch] += acc[ch].reshape(H, W)

        adv = 0.26
        newpos = np.stack([x, y], -1).astype(np.float32)
        self.pos = self.pos + adv * (newpos - self.pos)
        bad = ((self.pos[:, 0] < -80) | (self.pos[:, 0] > W + 80)
               | (self.pos[:, 1] < -80) | (self.pos[:, 1] > H + 80))
        self._bad = bad | (self.rng.random(self.N) < 0.040)
        nb = int(self._bad.sum())
        if nb:
            self._respawn(nb)

        c.clear(T.INK)
        c.add += self.buf * 0.86
        c.add += gauss(W, H, CX, 424, 700, 310)[..., None] * np.array(
            [0.004, 0.014, 0.007], np.float32)
        p = c.pass_()
        p.text(CX, 128, "TRAFFIC", F.display(104), T.WHITE, -3.0, "mm",
               A.out_expo(tl / 0.42, 4.5))
        _mono(p, CX, 176, "2400 STREAMLINES / CURL NOISE / ADDITIVE TRAILS", T.ACCENT_BR,
              10.5, 3.0, A.out_expo(clip01((tl - 0.16) / 0.5), 4.0), "ms")
        e = A.out_expo(clip01((tl - 0.28) / 0.6), 3.6)
        _mono(p, 64, 128, f"INGRESS  {tl * 12.4:7.2f} MB/S", T.GREY, 10, 1.8, 0.9 * e)
        _mono(p, W - 64, 128, f"EGRESS  {tl * 9.1:7.2f} MB/S", T.GREY, 10, 1.8, 0.9 * e, "rs")
        _mono(p, 64, 624, "REQ/S 1180 · NODES 8 · LAT 24 MS", T.GREY, 9.5, 1.6, 0.85)
        _mono(p, W - 64, 624, f"FPS {T.FPS} / {T.NFRAMES} FRAMES", T.GREY, 9.5, 1.6, 0.85, "rs")
        c.commit()


# --------------------------------------------------------------------------
# 06 / THE PANEL — the product's own light theme
# --------------------------------------------------------------------------
class Grid:
    NAV = ["WORK", "INDEX", "STUDIO", "CONTACT", "JOURNAL"]
    ROWS = [("studio.dev", "LIVE", "OK"), ("index.studio", "LIVE", "OK"),
            ("draft.build", "HOLD", "—")]

    def render(self, c, tl, t):
        c.clear(T.PAPER)
        c.rgb *= (0.985 + 0.015 * gauss(W, H, CX, CY, 900, 560))[..., None]
        p = c.pass_()
        a = A.out_expo(tl / 0.4, 4.2)
        # The product's own window, inset inside the live area so the reel's HUD
        # sits above it rather than colliding with a second brand line.
        TOP, BAR = 56.0, 48.0
        p.rect(T.M, TOP, W - 2 * T.M, BAR, T.CARD, a)
        p.rect(T.M, TOP + BAR, W - 2 * T.M, 1.0, T.SLATE, 0.30 * a)
        p.rect(T.M + 18, TOP + 12, 24, 24, T.ACCENT, a)
        p.text(T.M + 52, TOP + 30, f"{T.BRAND} PANEL", F.display(15), T.INK, 0.6, "lm", a)
        for i, s in enumerate(self.NAV):
            ea = A.out_expo(clip01((tl - 0.10 - i * 0.05) / 0.35), 4.0)
            _mono(p, T.M + 214 + i * 108, TOP + 30, s, T.INK if i == 0 else T.GREY_D,
                  8.5, 1.5, ea * 0.85)
        p.rect(T.M + 214, TOP + 42, 56, 2.2, T.ACCENT, a)
        status_pill(p, W - T.M - 86, TOP + 24, "running", T.ACCENT, a * 0.95,
                    0.6 + 0.4 * np.sin(t * 4.2))
        c.commit()

        # --- overview cards
        p = c.pass_()
        cards = [("SITES", "38", T.ACCENT), ("SSL CERTS", "12", T.INFO),
                 ("CONTAINERS", "6", T.ACCENT), ("ALERTS", "1", T.WARN)]
        for i, (name, val, col) in enumerate(cards):
            e = A.out_expo(clip01((tl - 0.24 - i * 0.10) / 0.5), 4.2)
            if e <= 0.01:
                continue
            x = T.M + i * 295.0
            y = 126.0 + (1.0 - e) * 20
            p.rect(x, y, 272, 104, T.CARD, e)
            p.rect(x, y, 272, 1.0, T.SLATE, 0.28 * e)
            p.rect(x, y + 103, 272, 1.0, T.SLATE, 0.28 * e)
            p.rect(x, y, 1.0, 104, T.SLATE, 0.28 * e)
            p.rect(x + 271, y, 1.0, 104, T.SLATE, 0.28 * e)
            p.rect(x, y, 4.0, 30.0, col, e)
            _mono(p, x + 20, y + 32, name, T.GREY, 9.0, 1.6, e * 0.85)
            p.text(x + 20, y + 76, val, F.display(34), T.INK, -1.0, "lm", e)
            p.line([(x + 20, y + 88), (x + 20 + 60 * e, y + 88)], col, 2.0, e)
        c.commit()

        # --- site table
        p = c.pass_()
        e = A.out_expo(clip01((tl - 0.72) / 0.55), 4.2)
        if e > 0.01:
            x0, y0, cw = T.M, 262.0, 690.0
            p.rect(x0, y0, cw, 250, T.CARD, e)
            p.rect(x0, y0, cw, 34, T.PAPER, e)
            p.rect(x0, y0 + 34, cw, 1.0, T.SLATE, 0.3 * e)
            for lab, xo in (("DOMAIN", 20), ("STATE", 350), ("SSL", 550)):
                _mono(p, x0 + xo, y0 + 22, lab, T.GREY_D, 8.5, 1.6, e * 0.9)
            for i, (dom, st, ssl) in enumerate(self.ROWS):
                ea = A.out_expo(clip01((tl - 0.86 - i * 0.12) / 0.45), 4.2)
                if ea <= 0.01:
                    continue
                yy = y0 + 72 + i * 56
                p.rect(x0 + 1, yy + 24, cw - 2, 1.0, T.SLATE, 0.18 * ea)
                p.text(x0 + 20, yy, dom, F.mono(12), T.INK, 0.4, "ls", ea)
                col = T.ACCENT if st == "RUNNING" else T.WARN
                p.rect(x0 + 350, yy - 10, 62, 18, col, 0.16 * ea)
                p.rect(x0 + 350, yy - 10, 2.4, 18, col, 0.95 * ea)
                _mono(p, x0 + 362, yy, st, col, 8.5, 1.4, ea)
                _mono(p, x0 + 550, yy, ssl, T.GREY_D, 9.0, 1.4, ea * 0.9)
            p.rect(x0, y0, cw, 1.0, T.SLATE, 0.3 * e)
            p.rect(x0, y0 + 249, cw, 1.0, T.SLATE, 0.3 * e)
            p.rect(x0, y0, 1.0, 250, T.SLATE, 0.3 * e)
            p.rect(x0 + cw - 1, y0, 1.0, 250, T.SLATE, 0.3 * e)
            # a second block so the page does not die below the table
            p.rect(x0, y0 + 266, cw, 96, T.CARD, e)
            p.rect(x0, y0 + 266, cw, 1.0, T.SLATE, 0.3 * e)
            p.rect(x0, y0 + 361, cw, 1.0, T.SLATE, 0.3 * e)
            p.rect(x0, y0 + 266, 1.0, 96, T.SLATE, 0.3 * e)
            p.rect(x0 + cw - 1, y0 + 266, 1.0, 96, T.SLATE, 0.3 * e)
            _mono(p, x0 + 20, y0 + 292, "SELECTED WORK", T.GREY, 9.0, 1.6, e * 0.85)
            for k, stack in enumerate(("ONE", "TWO", "THREE", "FOUR")):
                ea = A.out_expo(clip01((tl - 0.86 - k * 0.07) / 0.4), 4.2)
                p.rect(x0 + 20 + k * 168, y0 + 308, 150, 30, T.PAPER, ea)
                p.rect(x0 + 20 + k * 168, y0 + 308, 3.0, 30, T.ACCENT, ea)
                _mono(p, x0 + 34 + k * 168, y0 + 328, stack, T.INK, 9.5, 1.6, ea)
        c.commit()

        # --- right column: a load meter and a one-click block
        p = c.pass_()
        e2 = A.out_expo(clip01((tl - 1.00) / 0.55), 4.0)
        if e2 > 0.01:
            x0, cw2 = 772.0, W - T.M - 772.0
            p.rect(x0, 262, cw2, 362, T.CARD, e2)
            p.rect(x0, 262, cw2, 1.0, T.SLATE, 0.3 * e2)
            p.rect(x0, 623, cw2, 1.0, T.SLATE, 0.3 * e2)
            p.rect(x0, 262, 1.0, 362, T.SLATE, 0.3 * e2)
            p.rect(x0 + cw2 - 1, 262, 1.0, 362, T.SLATE, 0.3 * e2)
            _mono(p, x0 + 20, 292, "SERVER LOAD", T.GREY, 9.0, 1.6, e2 * 0.85)
            v = 0.38 + 0.05 * np.sin(t * 2.2)
            bx, by, bw2, bh = x0 + 20, 312.0, 300.0, 22.0
            p.rect(bx, by, bw2, bh, T.PAPER, e2)
            p.rect(bx, by, bw2 * v * e2, bh, grad=(T.ACCENT_BR, T.ACCENT))
            _mono(p, bx + bw2 + 14, by + 15, f"{int(round(v * 100))}%", T.INK, 11, 1.2, e2)
            _mono(p, x0 + 20, 366, "CPU · MEMORY · DISK · UPLOAD · DOWNLOAD", T.GREY_D, 8.5,
                  1.4, e2 * 0.85)
            for j in range(4):
                yy = 396.0 + j * 30.0
                _mono(p, x0 + 20, yy, ("CPU", "MEM", "DISK", "NET")[j], T.GREY, 8.5, 1.5,
                      e2 * 0.8)
                vv = clip01(0.30 + 0.34 * abs(np.sin(t * (0.9 + j * 0.23) + j)))
                p.rect(x0 + 64, yy - 9, 220, 12, T.PAPER, e2)
                p.rect(x0 + 64, yy - 9, 220 * vv * e2, 12, T.ACCENT, e2)
                _mono(p, x0 + 294, yy, f"{int(round(vv * 100))}%", T.INK, 9.0, 1.2, e2)
            p.line([(x0 + 20, 536), (x0 + cw2 - 20, 536)], T.SLATE, 1.0, 0.3 * e2)
            status_pill(p, x0 + cw2 / 2, 570, "one click", T.ACCENT, e2,
                        0.65 + 0.35 * np.sin(t * 5.0))
            _mono(p, x0 + cw2 / 2, 600, "LAMP · LNMP · DOCKER · SSL", T.GREY_D, 8.5, 1.6,
                  e2 * 0.85, "ms")
        _mono(p, T.M + 8, 660, "LIGHT AND DARK THEMES · ONE SYSTEM", T.GREY, 9.0, 1.6,
              A.out_expo(clip01((tl - 1.20) / 0.5), 3.6) * 0.8)
        _mono(p, W - T.M - 8, 660, "SERVER OPERATIONS PANEL", T.GREY, 9.0, 1.6,
              A.out_expo(clip01((tl - 1.20) / 0.5), 3.6) * 0.8, "rs")
        c.commit()


# --------------------------------------------------------------------------
# 07 / DEPLOY — the speed ramp
# --------------------------------------------------------------------------
class SpeedRamp:
    def render(self, c, tl, t):
        b = min(3, int(tl / BEAT))
        tb = tl - b * BEAT
        [self._split, self._slice, self._radar, self._ready][b](c, tb, t)

    def _split(self, c, tb, t):
        c.clear(T.INK)
        p = c.pass_()
        rng = np.random.default_rng(23)
        for i in range(30):
            yy = rng.random() * H
            ln = 120 + 400 * rng.random()
            ph = (tb * 3.0 + i * 0.11) % 1.0
            x = -ln + (W + 2 * ln) * ph
            p.line([(x, yy), (x + ln, yy)], T.ACCENT_DK, 1.4,
                   max(0.0, 0.18 * (1 - abs(ph - 0.5) * 1.5)))
        c.commit()
        f = F.display(T.S_WORD)
        e = A.out_expo(tb / 0.3, 4.6)
        sh = A.pulse(tb, 9.0) * 8.0
        r2 = np.random.default_rng(int(tb * 90) + 11)
        dx, dy = r2.normal(0, sh), r2.normal(0, sh * 0.4)
        for off, col, mode in ((-7.0 * e, T.ACCENT_BR, "add"),
                               (7.0 * e, T.ALT, "add"),
                               (0.0, T.WHITE, "normal")):
            p = c.pass_()
            p.text(CX + dx + off, CY - 16 + dy, "DEPLOY", f, col, T.TRACK_WORD, "mm",
                   A.out_expo(tb / 0.18, 5.5))
            c.commit(mode)
        p = c.pass_()
        _mono(p, CX, CY + 92, "FROM CLICK TO LIVE", T.WHITE, 11, 3.2, 0.88, "ms")
        _mono(p, 64, CY - 140, "CHANNEL STABLE", T.ACCENT_BR, 9.5, 1.6, 0.8)
        _mono(p, W - 64, CY - 140, "ZERO DOWNTIME", T.ALT, 9.5, 1.6, 0.8, "rs")
        c.commit()

    def _slice(self, c, tb, t):
        c.clear(T.INK)
        p = c.pass_()
        f = F.display(196)
        n = 15
        k = A.out_expo(tb / 0.72, 2.2)
        rng = np.random.default_rng(77)
        base = rng.normal(0, 1, n) * 148.0
        offs = [float(base[i] * (1.0 - k) * (0.55 + 0.45 * np.sin(tb * 22 + i)))
                for i in range(n)]
        p.text_slices(CX, CY - 16, "ONE CLICK", f, T.ACCENT_BR, -6.0, n, offs, 1.0,
                      anchor="mm")
        for i in (3, 9, 13):
            yy = CY - 96 + i * 12.4
            p.rect(0, yy, W, 3.0, T.WHITE, 0.20 * (1.0 - k))
        _mono(p, CX, CY + 92, "GLITCH / SLICE", T.ACCENT, 11, 3.2, 0.9, "ms")
        _mono(p, 64, CY - 140, "FRAME 412", T.GREY, 9.5, 1.6, 0.8)
        _mono(p, W - 64, CY - 140, "SCRIPTED", T.GREY, 9.5, 1.6, 0.8, "rs")
        c.commit()

    def _radar(self, c, tb, t):
        c.clear(T.BG0)
        c.add += gauss(W, H, CX, CY, 460, 320)[..., None] * np.array(
            [0.010, 0.036, 0.018], np.float32)
        p = c.pass_()
        for i, r in enumerate((250, 196, 142, 90)):
            a = 0.46 - i * 0.070
            p.ellipse(CX, CY - 8, r, r, T.ACCENT_BR if i % 2 == 0 else T.ALT, a, width=1.1)
        ang = tb / 0.62 * 360.0
        for k in range(16):
            aa = np.radians(ang - k * 3.2)
            a = (1 - k / 16.0) ** 1.5 * 0.42
            p.line([(CX, CY - 8), (CX + 250 * np.cos(aa), CY - 8 + 250 * np.sin(aa))],
                   T.ACCENT_BR, 1.9, a)
        for i in range(48):
            aa = np.radians(i * 7.5)
            r0 = 264.0
            p.line([(CX + r0 * np.cos(aa), CY - 8 + r0 * np.sin(aa)),
                    (CX + (r0 + (11 if i % 4 == 0 else 6)) * np.cos(aa),
                     CY - 8 + (r0 + (11 if i % 4 == 0 else 6)) * np.sin(aa))],
                   T.ACCENT_BR, 1.0, 0.42)
        f = F.display(T.S_WORD)
        e = A.out_expo(tb / 0.42, 4.0)
        p.text_outline(CX - 5.0, CY - 8, "SSL", f, T.ACCENT_BR, T.TRACK_WORD, 2.0, 0.80 * e)
        p.text_outline(CX + 5.0, CY - 8, "SSL", f, T.ALT, T.TRACK_WORD, 2.0, 0.70 * e)
        p.text_outline(CX, CY - 8, "SSL", f, T.WHITE, T.TRACK_WORD, 2.9, e)
        _mono(p, CX, CY + 128, "ISSUED AND RENEWED IN THE PANEL", T.WHITE, 11, 3.2,
              0.88, "ms")
        _mono(p, 64, CY - 150, "ACME", T.GREY, 9.5, 1.6, 0.8)
        _mono(p, W - 64, CY - 150, f"ANG  {int(ang) % 360:03d}°", T.GREY, 9.5, 1.6, 0.8, "rs")
        c.commit()

    def _ready(self, c, tb, t):
        # a white blowout, then the word flips to brand green on a wipe
        c.post_override = dict(bloom=(0.97, 0.20), chroma=0.7, vig=0.10,
                               grain=0.007, scan=0.0)
        c.clear(T.PAPER)
        c.rgb *= (0.84 + 0.28 * gauss(W, H, CX, CY, 560, 420))[..., None]
        c.rgb = np.clip(c.rgb, 0, 1)
        p = c.pass_()
        e0 = max(0.0, 1.0 - tb / 0.30)
        if e0 > 0.01:
            rng = np.random.default_rng(31)
            for i in range(20):
                aa = rng.random() * 6.283
                ln = 120 + rng.random() * 420
                p.line([(CX + 40 * np.cos(aa), CY + 40 * np.sin(aa)),
                        (CX + ln * np.cos(aa), CY + ln * np.sin(aa))],
                       T.WHITE, 2.0, 0.20 * e0 * rng.random())
        f = F.display(T.S_WORD)
        settle = A.out_expo(tb / 0.40, 3.8)
        p.text_scaled(CX, CY - 18, "READY", f, T.INK, -6.0,
                      1.0 + (1.0 - settle) * 0.10, 1.0 + (1.0 - settle) * 0.10, "mm",
                      A.out_expo(tb / 0.24, 5.0))
        _mono(p, CX, CY + 96, "ONE CLICK / NO CLI", T.GREY_D, 11, 3.2,
              0.9 * A.out_expo(clip01((tb - 0.3) / 0.4), 4.0), "ms")
        wp = A.out_expo(clip01((tb - 0.86) / 0.26), 5.0)
        if wp > 0.004:
            p.clip(CX - 300, 0, CX - 300 + 600 * wp, H)
            p.text(CX, CY - 18, "READY", f, T.ACCENT, -6.0, "mm",
                   A.out_expo(tb / 0.24, 5.0))
            p.unclip()
            p.rect(CX - 300 + 600 * wp - 1.0, CY - 120, 2.0, 240, T.ACCENT, 0.45)
        _mono(p, 64, CY - 150, "DEPLOY ×4", T.GREY_D, 9.5, 1.6, 0.8)
        _mono(p, W - 64, CY - 150, "TAKE 04", T.GREY_D, 9.5, 1.6, 0.8, "rs")
        c.commit()


# --------------------------------------------------------------------------
# 08 / SIGN OFF — the mark is assembled out of particles, then locks up
# --------------------------------------------------------------------------
class Assemble:
    """Thousands of particles swirl in and settle onto the pagoda mark.

    Targets are sampled from the mark's own alpha channel, so the shape the
    particles form is the real logo rather than an approximation. Each particle
    travels a decaying spiral into place with its own delay, and the additive
    buffer keeps a short trail so the arrival reads as motion, not as teleport.
    Once the cloud has settled it cross-fades to the crisp mark, which is what
    turns a particle effect into a logo.
    """

    N = 5200
    MARK_H = 176.0

    def __init__(self, seed=17):
        self.rng = rng = np.random.default_rng(seed)
        tgt = self._targets(self.N)
        self.tgt = tgt
        # per-particle start: a ring far outside the mark, plus a swirl phase
        ang = rng.random(self.N) * 2 * np.pi
        rad = 360.0 + rng.random(self.N) ** 0.7 * 760.0
        self.ang0 = ang
        self.rad0 = rad.astype(np.float32)
        self.swirl = (1.6 + 2.4 * rng.random(self.N)).astype(np.float32)
        self.delay = (rng.random(self.N) ** 1.6 * 0.62).astype(np.float32)
        self.dur = (0.34 + 0.34 * rng.random(self.N)).astype(np.float32)
        self.buf = np.zeros((H, W, 3), np.float32)
        r = 2.3
        n = int(np.ceil(r))
        ys, xs = np.mgrid[-n:n + 1, -n:n + 1]
        d = np.sqrt(ys ** 2 + xs ** 2)
        wgt = np.clip(1.0 - d / (r + 0.85), 0.0, None) ** 2.0
        m = wgt > 0.02
        self._bo = np.stack([ys[m], xs[m]], -1).astype(np.int32)
        self._bw = wgt[m].astype(np.float32)

    def _targets(self, n):
        from PIL import Image as _I
        im = _I.open(MARK).convert("RGBA").getchannel("A")
        h = int(self.MARK_H)
        w = int(round(im.width * h / im.height))
        a = np.asarray(im.resize((w, h), _I.LANCZOS), np.float32) / 255.0
        ys, xs = np.nonzero(a > 0.45)
        wts = a[ys, xs].astype(np.float64)
        idx = self.rng.choice(len(ys), n, p=wts / wts.sum())
        X = CX - w / 2.0 + xs[idx]
        Y = 202.0 - h / 2.0 + ys[idx]
        return np.stack([X, Y], -1).astype(np.float32)

    def _positions(self, tl):
        """Spiral-in position per particle at local time `tl`."""
        u = np.clip((tl - self.delay) / self.dur, 0.0, 1.0)
        e = 1.0 - (1.0 - u) ** 3.0                      # ease-out cubic
        e = e + 0.055 * np.sin(np.pi * u) * (1.0 - u)   # a touch of overshoot
        ang = self.ang0 + self.swirl * (1.0 - e)
        # clamp before the fractional power: the overshoot term can push e past 1
        rad = self.rad0 * np.clip(1.0 - e, 0.0, None) ** 1.35
        x = self.tgt[:, 0] + np.cos(ang) * rad
        y = self.tgt[:, 1] + np.sin(ang) * rad * 0.72
        # a little jitter that dies as the particle lands, so the cloud is alive
        j = (1.0 - e) * 9.0
        x = x + self.rng.normal(0, 1, self.N).astype(np.float32) * j
        y = y + self.rng.normal(0, 1, self.N).astype(np.float32) * j
        return x.astype(np.float32), y.astype(np.float32), u, e

    def render(self, c, tl, t):
        c.clear(T.INK)
        plate(c, 190, (0.006, 0.024, 0.014), 1.0, 660, 300)
        x, y, u, e = self._positions(tl)
        arrived = np.clip((u - 0.86) / 0.14, 0.0, 1.0)

        # speed -> colour: fast arrivals are hot, settled particles are deep green
        sp = np.abs(1.0 - e) * self.rad0 / 60.0
        sn = np.clip(sp / 6.0, 0.0, 1.0)
        warm = 1.0 - sn            # 1 for slow, settled particles
        cr = 0.10 + 0.22 * warm + 0.24 * arrived
        cg = 0.44 + 0.50 * warm + 0.16 * arrived
        cb = 0.14 + 0.20 * warm + 0.20 * arrived
        cols = np.stack([cr, cg, cb], -1).astype(np.float32)
        energy = (0.55 + 0.85 * warm + 0.55 * arrived) * (0.30 + 0.70 * u)
        energy = energy.astype(np.float32)

        bo, bw = self._bo, self._bw
        nT = len(bw)
        acc = [np.zeros(H * W, np.float32) for _ in range(3)]
        ix = np.round(x[:, None] + bo[None, :, 1]).astype(np.int32)
        iy = np.round(y[:, None] + bo[None, :, 0]).astype(np.int32)
        msk = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        idx = (iy[msk].astype(np.int64) * W + ix[msk])
        ww = (energy[:, None] * bw[None, :])[msk]
        for ch in range(3):
            cv = np.broadcast_to(cols[:, None, ch], (self.N, nT))[msk]
            acc[ch] += np.bincount(idx, weights=ww * cv, minlength=H * W)
        self.buf *= 0.70
        for ch in range(3):
            self.buf[..., ch] += acc[ch].reshape(H, W)

        # particles hand over to the real mark as the cloud settles
        hand = A.out_expo(clip01((tl - 0.86) / 0.40), 3.6)
        heat = clip01(0.22 + float(np.mean(u)) * 0.9)
        c.add += self.buf * (1.15 * (1.0 - hand) + 0.10) * heat
        c.add += gauss(W, H, CX, 202, 420, 200)[..., None] * np.array(
            [0.010, 0.046, 0.024], np.float32) * (0.4 + 0.9 * hand)
        if hand > 0.01:
            mark(c, CX, 202, h=self.MARK_H * (0.985 + 0.015 * hand),
                 alpha=hand, glow=hand * (0.55 + A.pulse(tl - 1.30, 8.0) * 1.1))

        # --- ring that fires outward the moment the mark exists
        p = c.pass_()
        for i in range(3):
            rr = A.ease_path([(0.0, 80 + i * 26), (1.6, 200 + i * 54)], max(0.0, tl - 1.30))
            aa = max(0.0, 1.0 - max(0.0, tl - 1.30) / 1.0) * (0.34 - i * 0.08)
            if aa > 0.008:
                p.ellipse(CX, 202, rr, rr, T.ACCENT_BR, aa, width=1.3)
        for i in range(60):
            a2 = np.radians(i * 6 + t * 20)
            r0 = 116.0
            ln = 8.0 if i % 5 == 0 else 4.0
            p.line([(CX + r0 * np.cos(a2), 202 + r0 * np.sin(a2)),
                    (CX + (r0 + ln) * np.cos(a2), 202 + (r0 + ln) * np.sin(a2))],
                   T.ACCENT, 1.1, 0.5 if i % 5 else 0.9)
        c.commit()

        p = c.pass_()
        e2 = A.out_expo(clip01((tl - 0.92) / 0.5), 4.0)
        if e2 > 0.01:
            p.text(CX, 366, T.DOMAIN, F.display(T.S_LOGOTYPE), T.WHITE, 3.0, "mm", e2)
            tw = F.measure(F.display(T.S_LOGOTYPE), T.DOMAIN, 3.0)
            rw = (tw / 2 + 30) * A.out_expo(clip01((tl - 1.08) / 0.45), 4.2)
            if rw > 0.5:
                p.line([(CX - rw, 408), (CX + rw, 408)], T.ACCENT, 2.0, 0.95)
        e3 = A.out_expo(clip01((tl - 1.02) / 0.5), 4.0)
        reveal_chars(p, CX, 440, T.PRODUCT, F.mono(18), T.WHITE, 6.5, "ms", e3, 0.95)
        e4 = A.out_expo(clip01((tl - 1.14) / 0.5), 4.0)
        reveal_chars(p, CX, 472, T.PLATFORMS, F.mono(10.5), T.ACCENT_LT, 2.6, "ms",
                     e4, 0.9)
        e5 = A.out_expo(clip01((tl - 1.26) / 0.5), 4.0)
        reveal_chars(p, CX, 494, T.TAGLINE, F.mono(10.5), T.GREY, 2.6, "ms",
                     e5, 0.85)
        e6 = A.out_expo(clip01((tl - 1.44) / 0.5), 4.0)
        if e6 > 0.01:
            status_pill(p, CX, 556, "available", T.ACCENT_BR, e6,
                        0.6 + 0.4 * np.sin(t * 6.2))
        c.commit()


SCENES = [Open, KineticType, Dimensional, Readouts, Flow, Grid, SpeedRamp, Assemble]
