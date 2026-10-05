"""Easing + small animation utilities.

Every scene animates on the beat grid, so most helpers take normalised time
(0..1 across a beat, bar, or scene) and return a 0..1 progress.
"""
import numpy as np

from .core import clip01


def lin(t):
    return clip01(t)


def out_expo(t, k=5.0):
    t = clip01(t)
    return 1.0 - np.exp(-k * np.maximum(t, 0.0))


def out_quint(t):
    t = clip01(t)
    return 1.0 - (1.0 - t) ** 5


def out_quart(t):
    t = clip01(t)
    return 1.0 - (1.0 - t) ** 4


def out_cubic(t):
    t = clip01(t)
    return 1.0 - (1.0 - t) ** 3


def in_cubic(t):
    t = clip01(t)
    return t ** 3


def out_back(t, s=1.42):
    t = clip01(t) - 1.0
    return t * t * ((s + 1) * t + s) + 1.0


def out_elastic(t, period=0.36, damp=5.2):
    t = clip01(t)
    return 1.0 - np.exp(-damp * t) * np.cos(2 * np.pi * t / period)


def in_out(t):
    t = clip01(t)
    return t * t * (3 - 2 * t)


def smooth(t):
    return in_out(t)


def bounce_out(t, k=2.6):
    """Decaying bounce in 0..1, used for settling type."""
    t = clip01(t)
    return 1.0 - np.exp(-k * t) * np.cos(t * np.pi * 2.1)


def spring(t, freq=1.7, damp=6.0):
    t = clip01(t)
    return 1.0 - np.exp(-damp * t) * np.cos(2 * np.pi * freq * t)


def pulse(t, decay=6.0):
    """Single decaying hit — for flashes and accents on a beat."""
    t = np.maximum(np.asarray(t, np.float32), 0.0)
    return np.exp(-decay * t)


def across(t0, dur, t, ease=out_expo):
    """Eased 0..1 progress of a sub-span starting at t0 lasting dur."""
    return ease(clip01((t - t0) / max(1e-6, dur)))


def stagger(i, n, t, t0=0.0, span=0.30, every=0.045, ease=out_expo, k=5.0):
    """Staggered per-item reveal for a sequence of n items."""
    return ease(clip01((t - t0 - i * every) / max(1e-6, span)))


def ping(t, t0, dur=0.16):
    """0 -> 1 -> 0 over `dur`, starting at t0. Handy for flashes."""
    u = (np.asarray(t, np.float32) - t0) / max(1e-6, dur)
    return np.where((u >= 0) & (u <= 1), np.sin(np.clip(u, 0, 1) * np.pi), 0.0)


class Noise:
    """Deterministic value noise for organic motion (film jitter, breathing)."""

    def __init__(self, seed=7):
        rng = np.random.default_rng(seed)
        self.tab = rng.random(4096).astype(np.float32)

    def at(self, x, salt=0):
        i = int((x * 61.7 + salt * 137.3) * 4096) & 4095
        j = (i + 1) & 4095
        f = (x * 61.7 + salt * 137.3) % 1.0
        f = f * f * (3 - 2 * f)
        return float(self.tab[i] * (1 - f) + self.tab[j] * f)

    def wave(self, x, salt=0):
        """-1..1 value noise."""
        return self.at(x, salt) * 2.0 - 1.0

    def fbm(self, x, octaves=4, salt=0):
        v, amp, freq = 0.0, 0.5, 1.0
        for o in range(octaves):
            v += self.wave(x * freq, salt + o * 31) * amp
            amp *= 0.5
            freq *= 2.07
        return v


def ease_path(keys, t):
    """Piecewise-smooth interpolation over [(time, value), ...] keyframes."""
    ts = [k[0] for k in keys]
    vs = [k[1] for k in keys]
    return float(np.interp(t, ts, vs))
