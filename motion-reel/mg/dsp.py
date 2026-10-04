"""Shared synthesis DSP.

Filtering is overlap-add FFT with a time-varying response, which is what makes
risers and filtered noise sweeps possible without an IIR loop. Reel-specific
instruments and arrangements live with their own reels; only the generic
plumbing is here.
"""
from __future__ import annotations

import wave

import numpy as np

SR = 48000


# --------------------------------------------------------------------------
# utility
# --------------------------------------------------------------------------
def t_axis(dur, sr=SR):
    return np.arange(int(round(dur * sr)), dtype=np.float32) / sr


def env_ad(n, attack, decay, sr=SR, curve=4.0):
    """Attack/decay envelope over n samples."""
    n = int(n)
    a = min(max(1, int(attack * sr)), n)
    e = np.zeros(n, np.float32)
    e[:a] = np.linspace(0, 1, a, dtype=np.float32) ** 0.6
    e[a:] = np.exp(-np.linspace(0, curve, n - a, dtype=np.float32))
    return e


def noise(n, seed, sr=SR):
    return np.random.default_rng(seed).normal(0, 1, int(n)).astype(np.float32)


def place(dst, src, at_samples, gain=1.0):
    """Mix `src` additively into `dst` starting at a sample offset."""
    i = int(at_samples)
    if i >= len(dst):
        return
    j = min(len(dst), i + len(src))
    dst[i:j] += src[: j - i] * gain


def filt(x, sr=SR, fn=None, block=4096):
    """Overlap-add filtering with a time-varying response.

    `fn(freqs, t_centre) -> gain` is evaluated per block, so one call can do a
    static lowpass, a filter sweep, or a bandpass that tracks a riser.
    """
    n = len(x)
    if fn is None:
        return x
    hop = block // 2
    win = np.hanning(block).astype(np.float32)
    wsum = np.zeros(n, np.float32)
    out = np.zeros(n, np.float32)
    freqs = np.fft.rfftfreq(block, 1.0 / sr)
    pad = np.pad(x, (0, block), mode="constant")
    for start in range(0, n, hop):
        seg = pad[start : start + block]
        if len(seg) < block:
            seg = np.pad(seg, (0, block - len(seg)))
        g = fn(freqs, (start + block / 2) / sr)
        spec = np.fft.rfft(seg * win) * g
        seg_out = np.fft.irfft(spec, block).astype(np.float32)
        end = min(start + block, n)
        out[start:end] += seg_out[: end - start]
        wsum[start:end] += win[: end - start]
    # The window is applied once (analysis only) and frames are overlapped, so
    # uniform overlap-add reconstructs against the summed window. Where that sum
    # vanishes — the first and last few samples, since Hann starts at zero —
    # output silence rather than dividing rounding noise up.
    denom = np.maximum(wsum, 2e-3)
    return np.where(wsum > 2e-3, out / denom, 0.0)


def lp(cut, slope=2.0):
    return lambda f, t, c=cut, s=slope: 1.0 / (1.0 + (f / max(c, 20.0)) ** s)


def hp(cut, slope=2.0):
    return lambda f, t, c=cut, s=slope: (f / max(c, 20.0)) ** s / (
        1.0 + (f / max(c, 20.0)) ** s)


def bp(lo, hi, slope=2.6):
    def fn(f, t, a=lo, b=hi, s=slope):
        lo_part = (f / max(a, 20.0)) ** s / (1.0 + (f / max(a, 20.0)) ** s)
        hi_part = 1.0 / (1.0 + (f / max(b, 20.0)) ** s)
        return lo_part * hi_part

    return fn


def peak_norm(x):
    m = float(np.abs(x).max())
    return (x / m).astype(np.float32) if m > 1e-9 else x.astype(np.float32)


def tape_wow(x, sr=SR, depth=0.0022, rate=0.7, seeds=None):
    """Slow tape pitch drift: resample through a wandering position.

    Cheap and very effective at making a clean synth bed sound like it came off
    a cassette rather than out of a DAW.
    """
    n = len(x)
    t = np.arange(n, dtype=np.float32) / sr
    mod = (np.sin(2 * np.pi * rate * t)
           + 0.4 * np.sin(2 * np.pi * rate * 2.7 * t + 1.3))
    pos = np.clip(np.arange(n, dtype=np.float32) + mod * depth * sr, 0, n - 1)
    i0 = np.floor(pos).astype(np.int32)
    i1 = np.minimum(i0 + 1, n - 1)
    f = (pos - i0).astype(np.float32)
    return (x[i0] * (1 - f) + x[i1] * f).astype(np.float32)


def reverb_tail(x, sr=SR, taps=((0.083, 0.34), (0.137, 0.24), (0.211, 0.16),
                                (0.293, 0.10), (0.401, 0.06))):
    """Cheap multitap delay — just enough to sit a mix in a room."""
    y = x.copy()
    for d, g in taps:
        i = int(d * sr)
        if i < len(x):
            y[i:] += x[: len(x) - i] * g
    return peak_norm(y) * float(np.abs(x).max())


def write_wav(path, st, sr=SR):
    x = np.clip(st, -1, 1)
    pcm = (x * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(st.shape[1] if st.ndim > 1 else 1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def analyse(st, sr=SR, fps=30, bands=56):
    """Waveform envelope + band energies, sampled per output frame."""
    mono = st.mean(axis=1) if st.ndim > 1 else st
    nf = int(round(len(mono) / sr * fps))
    wave = np.zeros((nf, 2), np.float32)
    spec = np.zeros((nf, bands), np.float32)
    block, hop = 1024, int(round(sr / fps))
    win = np.hanning(block).astype(np.float32)
    freqs = np.fft.rfftfreq(block, 1.0 / sr)
    edges = np.geomspace(45.0, 15000.0, bands + 1)
    idx = [np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0] for i in range(bands)]
    for i in range(nf):
        a = i * hop
        seg = mono[a : a + block]
        if len(seg) < block:
            seg = np.pad(seg, (0, block - len(seg)))
        wave[i] = (seg.min(), seg.max())
        sv = np.abs(np.fft.rfft(seg * win)) / (block * 0.5)
        spec[i] = [sv[j].mean() if len(j) else 0.0 for j in idx]
    spec = np.log1p(spec * 26.0)
    spec /= max(1e-6, spec.max())
    return wave, spec


def analyse_beats(st, sr=SR, n_beats=24, fps=30):
    """Per-beat loudness + low-band energy, for charts that must be honest."""
    mono = st.mean(axis=1) if st.ndim > 1 else st
    per = len(mono) // n_beats
    rms, low = np.zeros(n_beats, np.float32), np.zeros(n_beats, np.float32)
    freqs = np.fft.rfftfreq(2048, 1.0 / sr)
    lowband = (freqs > 40) & (freqs < 180)
    w = np.hanning(2048).astype(np.float32)
    for i in range(n_beats):
        seg = mono[i * per : (i + 1) * per]
        rms[i] = float(np.sqrt((seg ** 2).mean()))
        sv = np.abs(np.fft.rfft(seg[:2048] * w)) if len(seg) >= 2048 else np.zeros(1025)
        low[i] = float(sv[lowband].mean()) if len(sv) > lowband.sum() else 0.0
    norm = lambda a: a / max(1e-9, a.max())  # noqa: E731
    return norm(rms), norm(low)
