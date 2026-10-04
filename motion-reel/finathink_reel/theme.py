"""REEL CONFIG — everything a new film needs to change lives in this file.

A 15-second reel on a musical grid. One scene per bar, so every cut lands on a
downbeat and picture and music share one timeline instead of being married up
in the edit.

Replace the identity, palette and copy below. The palette shipped here is a
placeholder: for a real brand, sample the values from the brand's own assets
(its website stylesheet, or the product's own screenshots) rather than picking
them by eye. The dark version of a light product's palette is not a different
palette — it is the same colours read at the other end of the exposure.
"""

# --- identity ---------------------------------------------------------------
BRAND = "STUDIO"
DOMAIN = "STUDIO.DEV"
PRODUCT = "PANEL"
STUDIO = "REEL"
PLATFORMS = "DESIGN · MOTION · CODE"
TAGLINE = "MADE WITH CODE"

# --- timeline ---------------------------------------------------------------
# 15.000 s exactly. One scene per bar, every cut lands on a downbeat.
#   seconds = bars * 4 * 60 / BPM      BPM = 240 * bars / seconds
#   8 bars -> 128 BPM | 6 bars -> 96 | 5 bars -> 80 | 4 bars -> 64
# 30 fps: 450 frames. At 30 a 6-frame settle is 0.2 s, so entrances settle in
# about 4~6 frames again and out_expo(x, 4~4.5) is the general-purpose landing.
FPS = 30
BPM = 128
BEAT = 60.0 / BPM          # 0.46875 s
BAR = BEAT * 4             # 1.875 s
BARS = 8
DUR = BAR * BARS           # 15.000 s
NFRAMES = int(round(DUR * FPS))   # 450

# Layout is authored in W/H; OUT_W/OUT_H is the file that comes out. Delivery
# is 1920x1080 at 30 fps. Keeping the authoring space at 720p is what makes
# that cheap to lay out: type, rules and everything vector is rendered at the
# delivery size regardless, so only the soft masks (glow, grain, paper tooth)
# are built at the authoring size and resampled once. A film that leans on
# fine print texture — halftone dots, stipple — should instead author at the
# delivery size by setting W, H = OUT_W, OUT_H, so those masks are born sharp.
OUT_W, OUT_H = 1920, 1080
W, H = 1280, 720

# --- palette ----------------------------------------------------------------
# Every colour should trace to a measured brand value, never to taste. See
# references/design-grammar.md for how to sample them.
INK = (5, 9, 15)           # deepest plate
BG0 = (8, 15, 24)
BG1 = (13, 24, 38)
BG2 = (20, 34, 52)

ACCENT = (32, 165, 58)     # primary brand colour
ACCENT_BR = (62, 224, 106)  # primary pushed into glow
ACCENT_LT = (169, 229, 189)  # light tint of the brand
ACCENT_DK = (10, 122, 36)

ALT = (255, 215, 0)        # secondary / highlight
INFO = (48, 144, 232)
WARN = (240, 128, 24)
ERR = (230, 52, 52)

WHITE = (238, 246, 240)
PAPER = (240, 245, 240)    # the light scene's plate
CARD = (255, 255, 255)
GREY = (127, 143, 158)
GREY_D = (58, 74, 92)
SLATE = (29, 44, 62)

# --- type -------------------------------------------------------------------
S_HERO = 153.0
S_WORD = 156.0
S_MONO = 96.0
S_LOGOTYPE = 62.0
S_SUB = 17.0
S_HUD = 9.5
S_TAG = 10.5

TRACK_HERO = -4.0
TRACK_WORD = -3.5
TRACK_SUB = 3.2
TRACK_HUD = 1.5

# --- HUD chrome -------------------------------------------------------------
M = 58.0           # live-area margin for panel-style layouts
HUD_M = 27.0
HUD_TOP = 24.0
HUD_BOT = 700.0

SCENES = [
    ("01", "OPEN",        "Title build"),
    ("02", "KINETIC TYPE", "Four words, one beat each"),
    ("03", "HARDWARE",     "Rack, modelled in 3D"),
    ("04", "MONITOR",      "Live panel readouts"),
    ("05", "TRAFFIC",      "Data streamlines"),
    ("06", "THE PANEL",    "Product UI, light theme"),
    ("07", "DEPLOY",       "Speed ramp"),
    ("08", "SIGN OFF",     "Lockup"),
]

KINETIC_WORDS = ["BOLD", "SIMPLE", "STABLE", "FAST"]
KINETIC_SUBS = [
    "WEIGHT 900 / TIGHT TRACKING",
    "ONE IDEA PER BEAT",
    "STEADY, THEN SUDDEN",
    "SHORT WORDS HIT HARDER",
]

# readouts for the data scene — illustrative UI values, not product claims
GAUGES = [("CPU", 0.42, ACCENT), ("MEM", 0.61, ACCENT), ("DISK", 0.73, WARN),
          ("NET", 0.28, INFO)]
METRICS = [("LOAD", "0.84"), ("PROC", "212"), ("NODES", "38"), ("WORK", "12")]
