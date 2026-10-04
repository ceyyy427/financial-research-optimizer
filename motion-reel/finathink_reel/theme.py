"""Finathink bilingual motion-reel configuration.

The film is authored at 1280x720 and delivered at 1920x1080. Copy, timing,
palette, and source asset paths live here so scene code stays about motion and
composition rather than identity decisions.
"""
from __future__ import annotations

import os
from pathlib import Path


# --- identity ---------------------------------------------------------------
BRAND = "FINATHINK"
DOMAIN = "FINATHINK.CLOUD"
PRODUCT = "FINANCIAL RESEARCH OPTIMIZER"
STUDIO = "THINK THROUGH FINANCE"
PLATFORMS = "EVENTS · KNOWLEDGE · QUANT · YOU"
TAGLINE = "THINK THROUGH FINANCE"

# --- timeline ---------------------------------------------------------------
FPS = 30
BPM = 128
BEAT = 60.0 / BPM
BAR = BEAT * 4
BARS = 8
DUR = BAR * BARS
NFRAMES = int(round(DUR * FPS))

# --- layout -----------------------------------------------------------------
OUT_W, OUT_H = 1920, 1080
W, H = 1280, 720
SAFE_X = 80.0
SAFE_Y = 54.0
INFO_W = W * 0.72
INFO_H = H * 0.68
HUD_M = 28.0
HUD_TOP = 22.0
HUD_BOT = H - 28.0
M = 58.0

# --- source assets ----------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_RESEARCH = str(PROJECT_ROOT / "assets" / "finathink-research-splash.jpg")
ASSET_MAP = str(PROJECT_ROOT / "assets" / "finathink-splash-map.jpg")

# Pillow can load a macOS TrueType Collection directly. The font is deliberately
# referenced by path rather than copied into the project, so the source project
# does not redistribute a system font.
CJK_FONT_PATH = os.environ.get(
    "FINATHINK_CJK_FONT", "/System/Library/Fonts/Hiragino Sans GB.ttc"
)

# --- measured product palette ----------------------------------------------
INK = (15, 23, 42)
BG0 = (248, 250, 252)
BG1 = (239, 244, 247)
BG2 = (226, 234, 241)
PAPER = (248, 250, 252)
CARD = (255, 255, 255)
WHITE = (255, 255, 255)
ACCENT = (30, 58, 95)       # #1E3A5F
ACCENT_BR = (37, 99, 235)   # #2563EB
ACCENT_LT = (161, 185, 214)
ACCENT_DK = (18, 42, 72)
ALT = (161, 98, 7)          # #A16207
INFO = (37, 99, 235)
WARN = (161, 98, 7)
ERR = (165, 65, 62)
EVIDENCE = (47, 107, 87)
GREY = (71, 85, 105)
GREY_D = (100, 116, 135)
SLATE = (203, 213, 225)

# --- type -------------------------------------------------------------------
S_HERO = 126.0
S_WORD = 120.0
S_MONO = 72.0
S_LOGOTYPE = 58.0
S_SUB = 18.0
S_HUD = 9.0
S_TAG = 10.0
TRACK_HERO = -2.6
TRACK_WORD = -2.4
TRACK_SUB = 1.0
TRACK_HUD = 1.2

# Each entry is (id, chrome label, English title, Chinese subtitle).
SCENES = [
    ("01", "OPEN", "FINATHINK", "穿透金融，形成判断"),
    ("02", "BRIDGE", "FROM NOISE TO KNOWLEDGE", "从噪声，到知识"),
    ("03", "EVIDENCE", "EVIDENCE FIRST", "先看证据，再下判断"),
    ("04", "KNOWLEDGE", "UNDERSTAND THE WHY", "理解背后的逻辑"),
    ("05", "QUANT", "TEST, DON'T GUESS", "用量化验证，不靠猜测"),
    ("06", "STRATEGY", "BACKTEST / OUT OF SAMPLE", "回测，也要守住样本外边界"),
    ("07", "LEARNING", "LEARN WITH AN AGENT", "与智能代理一起学习"),
    ("08", "SIGNOFF", "THINK THROUGH FINANCE", "把金融问题，想得更清楚"),
]

# Kept for the template audio/chrome interfaces; scene code replaces the
# original neon copy with the light editorial treatment.
KINETIC_WORDS = ["EVIDENCE", "KNOWLEDGE", "QUANT", "LEARNING"]
KINETIC_SUBS = [
    "SOURCE BEFORE STORY",
    "EQUATIONS INTO INSIGHT",
    "TEST THE QUESTION",
    "KEEP THE THREAD",
]
GAUGES = [("EVIDENCE", 0.86, EVIDENCE), ("OOS", 0.64, INFO),
          ("RISK", 0.42, WARN), ("TRACE", 0.78, ACCENT)]
METRICS = [("CLAIMS", "04"), ("SOURCES", "12"), ("NODES", "38"), ("STEPS", "08")]
