"""Font stack + tracked typesetting helpers.

The reference reel pairs a heavy grotesque (hero type) with a technical
monospace (HUD chrome). We mirror that pairing, with Inter for mid-weight copy.
"""
import os
from PIL import ImageFont

def _find_font_dir():
    """Locate the bundled faces.

    The engine gets copied into each project, so the fonts are not always at a
    fixed relative path. Search the plausible spots and fail loudly with the
    fix, rather than at the first glyph with a bare "cannot open resource".
    """
    here = os.path.dirname(os.path.abspath(__file__))
    up = os.path.dirname(here)
    probe = "ArchivoBlack.woff"
    for c in (os.environ.get("MOTION_REEL_FONTS"),
              os.path.join(up, "assets", "fonts"),
              os.path.join(up, "fonts"),
              os.path.join(here, "assets", "fonts"),
              os.path.join(here, "fonts"),
              os.path.expanduser("~/mograph/fonts")):
        if c and os.path.exists(os.path.join(c, probe)):
            return os.path.normpath(c)
    raise RuntimeError(
        "font directory not found (looked for %s).\n"
        "Copy the skill's assets/fonts next to the engine as <project>/assets/fonts, "
        "or set MOTION_REEL_FONTS to the directory holding the .woff faces." % probe)


FONT_DIR = _find_font_dir()

_CACHE = {}


def font(name, size):
    """Load a font at `size` px. Cached — FreeType handles are expensive."""
    key = (name, round(size, 2))
    f = _CACHE.get(key)
    if f is None:
        f = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
        _CACHE[key] = f
    return f


def scaled(f, k):
    """`f` re-loaded at k× its size, for drawing into a supersampled layer."""
    key = ("__scaled__", f.path, round(f.size, 2), round(k, 3))
    g = _CACHE.get(key)
    if g is None:
        g = ImageFont.truetype(f.path, round(f.size * k))
        _CACHE[key] = g
    return g


# --- stack -----------------------------------------------------------------
def display(size):
    """Hero type — heavy grotesque.

    Archivo Black, not Inter Black: measured against the reference's settled
    MOTION (cap 105 px, width 676 px, ratio 6.44) Archivo sits at 6.63 and
    Inter 900 at 5.83. The reference is the wider face.
    """
    return font("ArchivoBlack.woff", size)


def bodoni(size, weight=900):
    """High-contrast Didone — the editorial voice of the print reel."""
    return font({400: "BodoniModa400.woff", 700: "BodoniModa700.woff",
                 900: "BodoniModa900.woff"}[weight], size)


def bodoni_it(size):
    return font("BodoniModaIt.woff", size)


def fraunces(size):
    return font("Fraunces900.woff", size)


def ui(size, weight=700):
    """Secondary sans — Inter. Weights snap to the nearest cached face."""
    table = {500: "Inter500.woff", 700: "Inter700.woff", 900: "Inter900.woff"}
    key = min(table, key=lambda k: abs(k - weight))
    return font(table[key], size)


def mono(size, weight=500):
    """Technical / HUD mono — JetBrains Mono."""
    return font({400: "JBMono400.woff", 500: "JBMono500.woff"}[weight], size)


# --- tracked typesetting ---------------------------------------------------
def kerned_layout(f, s, track=0.0):
    """Per-char x offsets, preserving the font's kerning and adding uniform
    tracking. Cumulative advance is what brings pair kerning along."""
    return [f.getlength(s[:i]) + track * i for i in range(len(s))]


def measure(f, s, track=0.0):
    if not s:
        return 0.0
    return f.getlength(s) + track * (len(s) - 1)


def char_span(f, s, track, i):
    """Inked box of char `i` as (x0, y0, x1, y1) relative to the string origin.

    Lets an accent bar be dropped exactly onto one letter's stem, the way the
    reference flips a single glyph to red inside an otherwise white word.
    """
    x0 = kerned_layout(f, s, track)[i]
    bx0, by0, bx1, by1 = f.getbbox(s[i])
    return x0 + bx0, by0, x0 + bx1, by1


def fit_size(s, target_w, make, track_ratio=0.0, lo=30.0, hi=440.0, iters=30):
    """Binary-search a font size so `s` measures `target_w` px.

    Display sizes must not be hard-coded: a brand name one word longer than the
    one the layout was designed around overflows the frame. Specify the width
    you want the line to occupy and let the size follow.

    `track_ratio` is tracking expressed as a fraction of the size (e.g. -0.026),
    so tracking scales with the type instead of staying a fixed pixel value.
    """
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        if measure(make(mid), s, track_ratio * mid) < target_w:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def cap_metrics(f):
    """(cap_top, cap_bottom) for 'H', as offsets from the **baseline**.

    PIL reports glyph boxes relative to the ascender line, which sits `ascent`
    above the baseline; anything anchored by cap centre or cap line has to
    subtract it or the type lands a full ascender too low.
    """
    a = f.getmetrics()[0]
    x0, y0, x1, y1 = f.getbbox("H")
    return y0 - a, y1 - a


def cap_band(f, cy):
    """(top, bottom) of the cap band in canvas space, caps centred on `cy`."""
    top, bot = cap_metrics(f)
    h = bot - top
    return cy - h / 2.0, cy + h / 2.0


def baseline_for_cap_centre(f, cy):
    """Baseline y that vertically centres capital letters on `cy`."""
    top, bot = cap_metrics(f)
    return cy - (top + bot) / 2.0


def baseline_for_cap_top(f, cy):
    """Baseline y that puts the cap line on `cy`."""
    return cy - cap_metrics(f)[0]
