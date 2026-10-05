"""Soundtrack — 128 BPM, eight bars, bright and confident.

Same tempo grid as the first reel so the cutting rhythm matches, but a different
mood: where reel/ was dark techno, this is clean uplift — a pluck-led arpeggio
over a solid four-on-the-floor, warm pad, and a bell lead that resolves on the
final bar. The drum and synth voices are shared with reel/audio; the arrangement
is not.
"""
from __future__ import annotations

import numpy as np

from mg.dsp import (SR, analyse, analyse_beats, bp, env_ad, filt, hp, lp, noise,
                    peak_norm, place, reverb_tail, t_axis, write_wav)

from . import theme as T


# --------------------------------------------------------------------------
# voices
# --------------------------------------------------------------------------
def kick(sr=SR, dur=0.55, f0=124.0, f1=46.0, pitch_t=0.070, amp_t=0.28):
    n = int(dur * sr)
    t = t_axis(dur, sr)
    f = f1 + (f0 - f1) * np.exp(-t / pitch_t)
    body = np.sin(2 * np.pi * np.cumsum(f) / sr).astype(np.float32)
    a = np.exp(-t / amp_t).astype(np.float32)
    click = filt((noise(n, 11) * np.exp(-t / 0.004)).astype(np.float32), sr,
                 bp(1400, 6000, 2.0)).astype(np.float32) * 0.30
    return peak_norm(filt(np.tanh((body * a + click) * 1.6) * 0.8, sr,
                          lp(6800, 2.4)).astype(np.float32))


def clap(sr=SR, dur=0.36, seed=5):
    n = int(dur * sr)
    t = t_axis(dur, sr)
    x = np.zeros(n, np.float32)
    for k, (off, g) in enumerate(((0.000, 1.0), (0.009, 0.85), (0.019, 0.70), (0.032, 0.55))):
        b = int(off * sr)
        x[b:] += noise(n - b, seed + k) * np.exp(-np.arange(n - b) / (0.009 * sr)) * g
    x += noise(n, seed + 9) * np.exp(-t / 0.14).astype(np.float32) * 0.45
    x = filt(x, sr, bp(1000, 4000, 2.1)).astype(np.float32)
    return peak_norm(x * env_ad(n, 0.001, 0.26, sr, 5.0))


def hat(sr=SR, dur=0.09, seed=3, open_=False):
    n = int(dur * sr)
    t = t_axis(dur, sr)
    x = filt(noise(n, seed), sr, hp(7600, 2.2)).astype(np.float32)
    x *= np.exp(-t / (0.055 if open_ else 0.018)).astype(np.float32)
    return peak_norm(filt(x, sr, hp(5600, 1.6)).astype(np.float32))


def sub(freq, sr=SR, dur=0.52, amp=0.9):
    n = int(dur * sr)
    t = t_axis(dur, sr)
    x = np.sin(2 * np.pi * freq * t).astype(np.float32)
    x += 0.16 * np.sin(4 * np.pi * freq * t).astype(np.float32)
    x *= env_ad(n, 0.006, 0.44, sr, 2.6)
    return peak_norm(x) * amp


def pluck(freq, sr=SR, dur=0.34, bright=1.0):
    """Bell-ish FM pluck — the arpeggio voice that leads this track."""
    n = int(dur * sr)
    t = t_axis(dur, sr)
    mod = np.sin(2 * np.pi * freq * 3.01 * t).astype(np.float32) * np.exp(-t / 0.05) * 2.1
    x = np.sin(2 * np.pi * freq * t + mod).astype(np.float32)
    x += 0.30 * np.sin(2 * np.pi * freq * 5.02 * t).astype(np.float32) * np.exp(-t / 0.030)
    x *= env_ad(n, 0.0012, 0.24, sr, 5.2)
    return peak_norm(filt(x, sr, lp(9000 * bright, 2.6)).astype(np.float32))


def bell(freq, sr=SR, dur=1.6):
    n = int(dur * sr)
    t = t_axis(dur, sr)
    x = np.sin(2 * np.pi * freq * t).astype(np.float32)
    x += 0.34 * np.sin(2 * np.pi * freq * 2.76 * t).astype(np.float32) * np.exp(-t / 0.35)
    x += 0.16 * np.sin(2 * np.pi * freq * 5.40 * t).astype(np.float32) * np.exp(-t / 0.12)
    x *= env_ad(n, 0.004, 1.30, sr, 2.4)
    return peak_norm(filt(x, sr, lp(8000, 2.2)).astype(np.float32))


def pad_chord(freqs, sr=SR, dur=2.0, cut=2100.0, detune=0.005):
    n = int(dur * sr)
    t = t_axis(dur, sr)
    x = np.zeros(n, np.float32)
    for f in freqs:
        for d, g in ((-detune, 0.8), (0.0, 0.9), (detune, 0.8), (detune * 2.2, 0.5)):
            ph = 2 * np.pi * (f * (1.0 + d)) * t
            x += (2.0 * ((ph / (2 * np.pi)) % 1.0) - 1.0).astype(np.float32) * g / len(freqs)
    x = filt(x, sr, lp(cut, 2.2)).astype(np.float32)
    x *= env_ad(n, 0.30, dur * 0.7, sr, 1.5)
    return peak_norm(x)


def riser(sr=SR, dur=1.875, f0=320.0, f1=7000.0, seed=21):
    n = int(dur * sr)
    x = noise(n, seed)

    def resp(f, tt, a=f0, b=f1, d=dur):
        pos = min(1.0, max(0.0, tt / d)) ** 1.7
        c = a * (b / a) ** pos
        return (f / c) ** 1.6 / (1.0 + (f / c) ** 1.6) * (1.0 / (1.0 + (f / min(c * 5.0, 16000.0)) ** 2.0))

    x = filt(x, sr, resp).astype(np.float32)
    t = np.arange(len(x), dtype=np.float32) / sr
    amp = (t / max(float(t[-1]), 1e-6)) ** 2.0
    x *= amp
    swp = np.sin(2 * np.pi * np.cumsum(np.linspace(220, 1600, len(x))) / sr).astype(np.float32)
    return peak_norm(x + swp * amp * 0.20)


def impact(sr=SR, dur=1.0, seed=33):
    n = int(dur * sr)
    t = t_axis(dur, sr)
    crk = filt(noise(n, seed), sr, bp(400, 7000, 1.6)).astype(np.float32) * np.exp(-t / 0.09)
    f = 160.0 * np.exp(-t / 0.09) + 38.0
    boom = np.sin(2 * np.pi * np.cumsum(f) / sr).astype(np.float32) * np.exp(-t / 0.30)
    return peak_norm(crk * 0.8 + boom)


# --------------------------------------------------------------------------
# arrangement
# --------------------------------------------------------------------------
NOTE = {"A2": 110.0, "B2": 123.47, "C3": 130.81, "D3": 146.83, "E3": 164.81,
        "F3": 174.61, "G3": 196.0, "A3": 220.0, "B3": 246.94, "C4": 261.63,
        "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.0, "A4": 440.0,
        "B4": 493.88, "C5": 523.25, "D5": 587.33, "E5": 659.26, "G5": 783.99}

# A minor lift: Am – F – C – G – Am – F – C – G, brightened on the last bar
PROG = [
    ("A3", ["A3", "C4", "E4", "A4"]),
    ("F3", ["F3", "A3", "C4", "F4"]),
    ("C4", ["C3", "E3", "G3", "C4"]),
    ("G3", ["G3", "B3", "D4", "G4"]),
    ("A3", ["A3", "C4", "E4", "A4"]),
    ("F3", ["F3", "A3", "C4", "F4"]),
    ("C4", ["C3", "E3", "G3", "C4"]),
    ("G3", ["G3", "B3", "D4", "G4"]),
]
ARP = ["A4", "C5", "E5", "C5", "A4", "E5", "C5", "A4"]
LEAD = [(3, 0.0, "A4"), (3, 2.0, "C5"), (4, 0.0, "E5"), (4, 2.5, "D5"),
        (6, 0.0, "E5"), (6, 1.5, "G5"), (7, 0.0, "A4")]


def build(dur=None, sr=SR):
    dur = dur or T.DUR
    n = int(round(dur * sr))
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)

    def at(bar, beat=0.0):
        return int(round((bar * T.BAR + beat * T.BEAT) * sr))

    K = kick(sr)
    CL = clap(sr)
    HH = hat(sr)
    HO = hat(sr, dur=0.22, open_=True)

    for bar in range(T.BARS):
        root, chord = PROG[bar]
        full = bar not in (0,)
        # --- pad
        p = pad_chord([NOTE[x] for x in chord], sr, T.BAR * 1.05,
                      cut=1650.0 if bar == 0 else 2300.0)
        g = 0.30 if bar == 0 else (0.24 if bar == 7 else 0.20)
        place(L, p, at(bar), g * 0.95)
        place(R, p, at(bar), g * 1.05)

        # --- sub bass
        riff = [(0.0, 1.0), (0.75, 0.55), (1.5, 0.85), (2.25, 0.5), (3.0, 1.0)]
        if bar == 0:
            riff = [(0.0, 1.0), (2.0, 0.8)]
        for off, gl in riff:
            b = sub(NOTE[root], sr, 0.50)
            place(L, b, at(bar, off), 0.32 * gl)
            place(R, b, at(bar, off), 0.32 * gl)

        # --- drums
        for beat in range(4):
            if bar == 0 and beat not in (0, 2):
                continue
            place(L, K, at(bar, beat), 0.88)
            place(R, K, at(bar, beat), 0.88)
            if beat in (1, 3):
                place(L, CL, at(bar, beat), 0.36)
                place(R, CL, at(bar, beat), 0.35)
            place(L, HO, at(bar, beat + 0.5), 0.15)
            place(R, HO, at(bar, beat + 0.5), 0.16)
            for s_off in (0.25, 0.75):
                place(L, HH, at(bar, beat + s_off), 0.10)
                place(R, HH, at(bar, beat + s_off), 0.095)

        # --- arpeggio: 16ths, octave-jumping, panned across the stereo field
        if full:
            tones = ["A4", "C5", "E5", "A4"]
            for i in range(16):
                nm = ARP[i % len(ARP)]
                f = NOTE[nm] * (0.5 if (i // 8) % 2 == 1 else 1.0)
                pl = pluck(f, sr, 0.30)
                pan = 0.5 + 0.40 * np.sin(i * 1.13)
                place(L, pl, at(bar, i * 0.25), 0.135 * (1.0 - pan * 0.5))
                place(R, pl, at(bar, i * 0.25), 0.135 * pan)

        # --- transitions
        if bar in (3, 6):
            r = riser(sr, T.BAR * 0.96, 320.0, 7000.0, seed=21 + bar)
            place(L, r, at(bar, 0.05), 0.34)
            place(R, r, at(bar, 0.05), 0.34)
        if bar in (1, 4, 7):
            im = impact(sr, 1.1, seed=51 + bar)
            place(L, im, at(bar), 0.70 if bar == 4 else 0.52)
            place(R, im, at(bar), 0.70 if bar == 4 else 0.52)

    # --- bell lead over the back half
    for bar, beat, nm in LEAD:
        b = bell(NOTE[nm], sr, 1.8)
        place(L, b, at(bar, beat), 0.20)
        place(R, b, at(bar, beat), 0.16)

    # --- mix
    L = filt(L, sr, lp(15500, 2.2)).astype(np.float32)
    R = filt(R, sr, lp(15500, 2.2)).astype(np.float32)
    L = filt(L, sr, hp(30, 2.0)).astype(np.float32)
    R = filt(R, sr, hp(30, 2.0)).astype(np.float32)
    L = reverb_tail(L, sr, taps=((0.091, 0.17), (0.157, 0.10), (0.241, 0.06)))
    R = reverb_tail(R, sr, taps=((0.103, 0.17), (0.173, 0.10), (0.263, 0.06)))

    st = np.stack([L, R], -1)
    peak = float(np.abs(st).max())
    st = np.tanh(st / max(peak, 1e-6) * 1.9) / np.tanh(1.9)
    f = int(0.012 * sr)
    st[:f] *= np.linspace(0, 1, f, dtype=np.float32)[:, None]
    g = int(0.30 * sr)
    st[-g:] *= np.linspace(1.0, 0.0, g, dtype=np.float32)[:, None]
    # leave headroom for inter-sample peaks after AAC
    st *= 0.84 / max(1e-6, float(np.abs(st).max()))
    return st.astype(np.float32), sr


__all__ = ["build", "write_wav", "analyse", "analyse_beats", "SR"]
