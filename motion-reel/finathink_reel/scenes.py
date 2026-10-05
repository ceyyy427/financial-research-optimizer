"""Eight light-editorial Finathink scenes.

The first two scenes use the real product images. The remaining scenes draw
small structural UI studies so the film communicates product direction without
inventing performance claims.
"""
from __future__ import annotations

import math

import numpy as np

from mg import anim as A
from mg import fonts as F
from mg.core import clip01, gauss, rgb01

from . import theme as T

W, H = T.W, T.H
CX, CY = W / 2.0, H / 2.0
BEAT = T.BEAT


def _alpha(tl, start=0.0, duration=0.42):
    return float(A.out_expo(clip01((tl - start) / max(duration, 0.001)), 4.2))


def _light_bg(c, focus=(0.84, 0.90, 0.98), strength=0.15):
    c.clear(T.BG0)
    c.add += gauss(W, H, CX, CY - 30, 520, 330)[..., None] * rgb01(focus) * strength
    c.add += gauss(W, H, CX + 260, CY + 80, 500, 280)[..., None] * rgb01((255, 241, 220)) * 0.055


def _grid(p, alpha=0.11):
    for x in np.linspace(T.SAFE_X, W - T.SAFE_X, 12):
        p.line([(x, T.SAFE_Y), (x, H - T.SAFE_Y)], T.SLATE, 0.7, alpha)
    for y in np.linspace(T.SAFE_Y, H - T.SAFE_Y, 7):
        p.line([(T.SAFE_X, y), (W - T.SAFE_X, y)], T.SLATE, 0.7, alpha)


def _mono(p, x, y, text, color=T.GREY, size=10.0, alpha=1.0, anchor="ls", track=None):
    return p.text(x, y, text, F.mono(size), color,
                  T.TRACK_HUD if track is None else track, anchor, alpha)


def _cjk_size(text, target):
    return F.fit_size(text, target, F.cjk, 0.0, lo=14.0, hi=32.0)


def draw_bilingual_title(p, title, subtitle, tl, y=106.0, accent=T.ACCENT_BR):
    """Draw a width-fitted English title and Chinese explanation line."""
    a = _alpha(tl, 0.04, 0.36)
    title_size = F.fit_size(title, W * 0.62, F.bodoni, -0.012, lo=34.0, hi=132.0)
    title_font = F.bodoni(title_size, 700)
    p.text(CX, y, title, title_font, T.INK, -0.012 * title_size, "mm", a)
    sub_size = _cjk_size(subtitle, W * 0.42)
    p.text(CX, y + 55.0, subtitle, F.cjk(sub_size), T.GREY, 0.0, "mm", a * 0.94)
    rule = _alpha(tl, 0.18, 0.32)
    p.line([(CX - 38, y + 82), (CX + 38, y + 82)], accent, 2.0, rule)
    return title_size, sub_size


def draw_card_image(c, path, cx, cy, scale, alpha=1.0, radius=16.0):
    """Place an image as a softly framed card in authoring coordinates."""
    p = c.pass_()
    # The shadow is deliberately broad and low contrast on the paper plate.
    p.rect(cx - 450 * scale + 7, cy - 450 * scale + 9,
           900 * scale, 900 * scale, (15, 23, 42), 0.08 * alpha, radius=radius)
    c.blit(path, cx, cy, scale=scale, alpha=alpha)
    p = c.pass_()
    p.rect(cx - 450 * scale, cy - 450 * scale,
           900 * scale, 900 * scale, T.WHITE, 0.55 * alpha, radius=radius)


def draw_bridge_wipe(p, progress, center=(CX, CY), accent=T.ACCENT_BR):
    """Draw a radial connector wipe used between the two real product images."""
    cx, cy = center
    progress = clip01(progress)
    for i in range(12):
        ang = (i / 12.0) * math.tau - 0.12
        length = 120 + 430 * progress + i * 7
        x1 = cx + math.cos(ang) * 48
        y1 = cy + math.sin(ang) * 48
        x2 = cx + math.cos(ang) * length
        y2 = cy + math.sin(ang) * length
        p.line([(x1, y1), (x2, y2)], accent, 1.3, 0.12 + 0.58 * progress)
    p.ellipse(cx, cy, 46 + progress * 210, 46 + progress * 210,
              accent, 0.35 * (1.0 - progress), width=1.3)
    p.dot(cx, cy, 5.5 + 9 * progress, accent, 0.88)


def _card(p, x, y, w, h, alpha=1.0, tint=T.CARD, border=T.SLATE):
    p.rect(x + 7, y + 8, w, h, T.INK, 0.055 * alpha, radius=15)
    p.rect(x, y, w, h, tint, 0.96 * alpha, radius=15)
    p.path([(x + 15, y), (x + w - 15, y), (x + w, y + 15),
            (x + w, y + h - 15), (x + w - 15, y + h),
            (x + 15, y + h), (x, y + h - 15), (x, y + 15)],
           border, 1.0, 0.82 * alpha, closed=True)


def _chip(p, x, y, label, color, alpha=1.0):
    width = max(62.0, F.measure(F.mono(9), label, 1.2) + 22)
    p.rect(x, y, width, 22, color, 0.12 * alpha, radius=11)
    p.dot(x + 11, y + 11, 3.0, color, alpha)
    p.text(x + 20, y + 14.5, label, F.mono(9), color, 1.2, "ls", alpha)
    return width


def _section_footer(p, left, right, alpha=1.0):
    _mono(p, T.SAFE_X, H - 82, left, T.GREY_D, 9.0, alpha)
    _mono(p, W - T.SAFE_X, H - 82, right, T.GREY_D, 9.0, alpha, "rs")


class OpenResearch:
    def render(self, c, tl, t):
        _light_bg(c, (0.92, 0.95, 1.0), 0.11)
        p = c.pass_()
        _grid(p, 0.055)
        e = _alpha(tl, 0.0, 0.75)
        scale = 0.55 + 0.075 * A.out_expo(clip01(tl / 1.75), 2.3)
        draw_card_image(c, T.ASSET_RESEARCH, CX, 310, scale, e)
        p = c.pass_()
        draw_bilingual_title(p, T.SCENES[0][2], T.SCENES[0][3], tl, 623, T.ACCENT)
        _mono(p, T.SAFE_X, 42, "LOCAL-FIRST / RESEARCH WORKSPACE", T.GREY, 9.2, _alpha(tl, 0.38, 0.35))
        _mono(p, W - T.SAFE_X, 42, "01 / 08", T.ACCENT, 9.2, _alpha(tl, 0.38, 0.35), "rs")
        c.commit()


class ArchitectureBridge:
    def render(self, c, tl, t):
        _light_bg(c, (0.90, 0.94, 1.0), 0.13)
        p = c.pass_()
        _grid(p, 0.035)
        bridge = _alpha(tl, 0.02, 0.68)
        # The map is height-fit rather than cover-cropped, preserving its lower
        # tagline and allowing the paper background to continue into the sides.
        c.blit(T.ASSET_MAP, CX, CY, scale=0.70, alpha=bridge)
        p = c.pass_()
        draw_bridge_wipe(p, _alpha(tl, 0.0, 0.72), (CX, CY), T.ACCENT_BR)
        draw_bilingual_title(p, T.SCENES[1][2], T.SCENES[1][3], tl, 100, T.ALT)
        _mono(p, T.SAFE_X, H - 82, "MAP THE QUESTION", T.GREY_D, 9.0, bridge)
        _mono(p, W - T.SAFE_X, H - 82, "02 / 08", T.ACCENT, 9.0, bridge, "rs")
        c.commit()


class Evidence:
    def render(self, c, tl, t):
        _light_bg(c, (0.86, 0.95, 0.91), 0.17)
        p = c.pass_()
        _grid(p, 0.07)
        draw_bilingual_title(p, T.SCENES[2][2], T.SCENES[2][3], tl, 104, T.EVIDENCE)
        a = _alpha(tl, 0.24, 0.42)
        _card(p, 82, 228, 420, 255, a)
        _mono(p, 110, 260, "EVENT BRIEF / CAPTURED", T.GREY, 9.5, a)
        p.text(110, 318, "CPI", F.bodoni(50, 700), T.INK, -0.8, "ls", a)
        p.text(110, 365, "2.7%", F.bodoni(64, 700), T.ACCENT, -1.0, "ls", a)
        _mono(p, 110, 424, "TIME-BOUND · SOURCE-LINKED", T.GREY_D, 9, a)
        _card(p, 778, 228, 420, 255, a * 0.98)
        _mono(p, 808, 260, "SOURCE VERIFICATION", T.GREY, 9.5, a)
        for i, label in enumerate(("BLS", "FEDERAL RESERVE", "SEC EDGAR")):
            yy = 310 + i * 45
            p.line([(810, yy + 17), (1130, yy + 17)], T.SLATE, 1.0, a)
            p.dot(832, yy + 17, 6, T.EVIDENCE, a)
            p.text(852, yy + 21, label, F.ui(13, 700), T.INK, 0.0, "ls", a)
            p.text(1110, yy + 21, "VERIFIED", F.mono(9), T.EVIDENCE, 1.0, "rs", a)
        draw_bridge_wipe(p, 0.24 * _alpha(tl, 0.52, 0.36), (640, 475), T.EVIDENCE)
        _section_footer(p, "CLAIMS / SOURCES / LIMITATIONS", "03 / 08", a)
        c.commit()


class KnowledgeMath:
    def render(self, c, tl, t):
        _light_bg(c, (0.90, 0.92, 1.0), 0.18)
        p = c.pass_()
        _grid(p, 0.06)
        draw_bilingual_title(p, T.SCENES[3][2], T.SCENES[3][3], tl, 104, T.ACCENT_BR)
        a = _alpha(tl, 0.22, 0.45)
        # Concept graph on the left.
        nodes = [(250, 350, "EVENT"), (420, 286, "RATES"), (420, 414, "VALUE"), (590, 350, "WHY")]
        for x, y, label in nodes[:-1]:
            p.line([(x, y), (590, 350)], T.ACCENT_LT, 1.5, a)
            p.dot(x, y, 14, T.CARD, a)
            p.ellipse(x, y, 14, 14, T.ACCENT_BR, a, width=2.0)
            _mono(p, x, y + 32, label, T.GREY, 8.5, a, "ms")
        p.dot(590, 350, 22, T.ACCENT_BR, a)
        p.dot(590, 350, 8, T.WHITE, a)
        _mono(p, 590, 394, "CONNECT", T.ACCENT, 9.0, a, "ms")
        # Equation card.
        _card(p, 735, 242, 445, 240, a, tint=(252, 253, 255), border=(182, 198, 220))
        _mono(p, 770, 278, "KNOWLEDGE UNIT / EQUATION", T.GREY, 9.5, a)
        p.text(958, 365, "BETA = COV(Ri, Rm)", F.mono(20), T.INK, 0.0, "mm", a)
        p.text(958, 402, "VAR(Rm)", F.mono(20), T.ACCENT_BR, 0.0, "mm", a)
        p.line([(793, 380), (1120, 380)], T.ALT, 1.5, a)
        _mono(p, 770, 445, "INTUITION  →  FORMAL  →  CODE", T.GREY_D, 9.0, a)
        _section_footer(p, "CONCEPTS / DERIVATIONS / APPLICATIONS", "04 / 08", a)
        c.commit()


class QuantResearch:
    def render(self, c, tl, t):
        _light_bg(c, (0.90, 0.94, 1.0), 0.16)
        p = c.pass_()
        _grid(p, 0.06)
        draw_bilingual_title(p, T.SCENES[4][2], T.SCENES[4][3], tl, 104, T.ACCENT_BR)
        a = _alpha(tl, 0.20, 0.45)
        _card(p, 94, 235, 430, 300, a)
        _mono(p, 126, 270, "FACTOR ANALYSIS", T.GREY, 9.5, a)
        bars = [0.74, 0.54, 0.82, 0.34, 0.62]
        labels = ["MOM", "VALUE", "QUALITY", "RATES", "LIQ"]
        for i, (value, label) in enumerate(zip(bars, labels)):
            yy = 318 + i * 38
            _mono(p, 126, yy + 14, label, T.GREY, 8.5, a)
            p.rect(210, yy, 240, 18, T.SLATE, 0.45 * a, radius=9)
            p.rect(210, yy, 240 * value * clip01(tl / 0.7), 18,
                   T.ACCENT_BR if i < 3 else T.ALT, 0.82 * a, radius=9)
        _card(p, 640, 235, 545, 300, a * 0.98)
        _mono(p, 675, 270, "RESEARCH RUN / TRACE", T.GREY, 9.5, a)
        points = []
        for i in range(90):
            x = 678 + i * 5.2
            y = 470 - 110 * (i / 89) - 12 * math.sin(i * 0.23) - 7 * math.sin(i * 0.61)
            points.append((x, y))
        reveal = clip01((tl - 0.25) / 0.9)
        p.line([(678, 470), (1140, 470)], T.SLATE, 1.0, 0.8 * a)
        p.path([pt for j, pt in enumerate(points) if j <= int(len(points) * reveal)],
               T.ACCENT_BR, 2.2, a)
        p.line([(678, 442), (1140, 342)], T.ALT, 1.0, 0.65 * a)
        _mono(p, 675, 515, "QUESTION  →  FEATURE  →  RESULT", T.GREY_D, 9.0, a)
        _section_footer(p, "DETERMINISTIC / RESEARCH-ONLY", "05 / 08", a)
        c.commit()


class StrategyBacktest:
    def render(self, c, tl, t):
        _light_bg(c, (0.98, 0.93, 0.84), 0.14)
        p = c.pass_()
        _grid(p, 0.055)
        draw_bilingual_title(p, T.SCENES[5][2], T.SCENES[5][3], tl, 104, T.ALT)
        a = _alpha(tl, 0.20, 0.44)
        _card(p, 112, 238, 1056, 272, a, tint=(255, 255, 255), border=(224, 211, 187))
        p.line([(640, 270), (640, 478)], T.SLATE, 1.2, a)
        _chip(p, 150, 268, "IN-SAMPLE", T.ACCENT_BR, a)
        _chip(p, 680, 268, "OUT-OF-SAMPLE", T.ALT, a)
        for offset, color in ((0, T.ACCENT_BR), (530, T.ALT)):
            pts = []
            for i in range(38):
                x = 160 + offset + i * 11.8
                y = 440 - 3.0 * i - 13 * math.sin(i * 0.31 + offset)
                pts.append((x, y))
            p.path(pts, color, 2.4, a)
            p.line([(160 + offset, 442), (610 + offset, 442)], T.SLATE, 0.8, 0.6 * a)
        p.line([(640, 290), (640, 465)], T.ERR, 1.8, a)
        _mono(p, 640, 492, "BOUNDARY", T.ERR, 8.5, a, "ms")
        _mono(p, 150, 548, "IDEA  →  FEATURES  →  BACKTEST", T.GREY, 9.0, a)
        _mono(p, 1130, 548, "PAPER ONLY", T.ALT, 9.0, a, "rs")
        _section_footer(p, "NO REAL-MONEY EXECUTION", "06 / 08", a)
        c.commit()


class LearningAgent:
    def render(self, c, tl, t):
        _light_bg(c, (0.93, 0.90, 1.0), 0.15)
        p = c.pass_()
        _grid(p, 0.06)
        draw_bilingual_title(p, T.SCENES[6][2], T.SCENES[6][3], tl, 104, (99, 82, 138))
        a = _alpha(tl, 0.20, 0.44)
        _card(p, 230, 236, 820, 286, a, border=(211, 203, 230))
        steps = [("OBSERVE", T.ACCENT_BR), ("ANALYZE", T.EVIDENCE),
                 ("PLAN", T.ALT), ("EXECUTE", (99, 82, 138))]
        x0, gap = 310, 205
        p.line([(x0, 365), (x0 + gap * 3, 365)], T.SLATE, 3.0, a)
        for i, (label, color) in enumerate(steps):
            x = x0 + i * gap
            e = _alpha(tl, 0.22 + i * 0.14, 0.24)
            p.dot(x, 365, 24, T.CARD, e * a)
            p.ellipse(x, 365, 24, 24, color, e * a, width=2.2)
            p.dot(x, 365, 7, color, e * a)
            _mono(p, x, 415, label, color, 9.0, e * a, "ms")
        p.line([(x0, 466), (x0 + gap * 3, 466)], T.ACCENT_LT, 1.0, 0.8 * a)
        p.text(640, 466, "PERSONAL LEARNING  +  AI AGENT", F.ui(13, 700), T.INK, 1.1, "mm", a)
        _section_footer(p, "QUESTION → INSIGHT → MASTERY", "07 / 08", a)
        c.commit()


class Signoff:
    def render(self, c, tl, t):
        _light_bg(c, (0.88, 0.93, 1.0), 0.13)
        p = c.pass_()
        # Three leaf-like strokes echo the supplied brand mark without inventing
        # a new product icon system; the real logo has already appeared in the
        # opening product image.
        e = _alpha(tl, 0.04, 0.42)
        for pts, color in (
            ([(CX, 246), (CX - 22, 205), (CX - 8, 170)], T.ACCENT),
            ([(CX, 246), (CX + 18, 200), (CX + 36, 182)], T.ACCENT_BR),
            ([(CX, 246), (CX - 2, 208), (CX + 6, 160)], T.ALT),
        ):
            p.path(pts, color, 7.0, e)
        p.text(CX, 326, "Finathink", F.bodoni(88, 700), T.INK, -1.8, "mm", e)
        p.text(CX, 412, T.SCENES[7][2], F.bodoni(34, 400), T.GREY, -0.2, "mm", e * 0.95)
        p.text(CX, 478, T.SCENES[7][3], F.cjk(_cjk_size(T.SCENES[7][3], W * 0.42)),
               T.GREY_D, 0.0, "mm", e * 0.92)
        p.line([(CX - 70, 530), (CX + 70, 530)], T.ACCENT_BR, 2.0, _alpha(tl, 0.42, 0.28))
        _mono(p, CX, 575, T.PLATFORMS, T.ACCENT, 10.0, _alpha(tl, 0.52, 0.35), "ms", 2.6)
        _mono(p, CX, H - 82, "A MORE THOUGHTFUL WAY TO LEARN ABOUT FINANCE", T.GREY_D,
              8.8, _alpha(tl, 0.70, 0.36), "ms", 2.0)
        c.commit()


SCENES = [OpenResearch, ArchitectureBridge, Evidence, KnowledgeMath,
          QuantResearch, StrategyBacktest, LearningAgent, Signoff]
