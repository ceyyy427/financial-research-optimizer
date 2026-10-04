"""Colour, computed from physics instead of chosen from a swatch.

Every colour here is a measured quantity rather than a chosen one. Two questions generate the
whole palette:

    what colour is a body at T kelvin?        -> blackbody(T), Planck + CIE 1931
    what colour is light at L nanometres?     -> spectral(L), same machinery

So the plate is not "a nice amber" — it is 2000 K, the temperature where a star
stops being white and starts being an ember. The accent is not "a teal" — it is
the corona's Fe XIV line at 530.3 nm, which is why the corona looks green in a
photograph. Nothing here was picked, and nothing here needs a designer's taste
to justify: it needs a thermometer and a spectroscope.

The chain, per colour:

    Planck's law B(lambda, T)   ->  integrate against CIE 1931 xyzbar
    ->  XYZ  ->  linear sRGB (Rec. 709 primaries)  ->  gamut-fit  ->  sRGB

The CIE curves use the multi-lobe piecewise-Gaussian fit from Wyman, Sloan &
Shirley (JCGT 2013), max error about 1% of peak — far below the error introduced
by a display's own primaries.

Gamut fitting matters: a 2000 K body and a 420 nm line both fall outside sRGB.
Rather than clip (which bends hue) each colour is desaturated toward the equal
energy white until every channel is non-negative, then gamma-encoded. That is
what a camera does when it cannot record a colour: it loses saturation, not hue.
"""
from __future__ import annotations

import numpy as np

# --- constants --------------------------------------------------------------
H = 6.62607015e-34        # Planck
C = 2.99792458e8          # speed of light
KB = 1.380649e-23         # Boltzmann

LAM = np.linspace(380.0, 780.0, 401)      # nm, the visible band at 1 nm steps
_LAM_M = LAM * 1e-9


def planck(lam_nm, T):
    """Spectral radiance of a blackbody, arbitrary units (W/sr/m^3, in fact).

    `lam_nm` in nanometres, `T` in kelvin. Scalar or array, broadcast together.
    """
    lam = np.asarray(lam_nm, np.float64) * 1e-9
    x = H * C / (lam * KB * float(T))
    # expm1 keeps precision in the Rayleigh-Jeans tail instead of dividing by a
    # difference of two nearly equal exponentials
    return (2.0 * H * C * C) / (lam ** 5) / np.expm1(x)


def _g(x, mu, s1, s2):
    s = np.where(x < mu, s1, s2)
    return np.exp(-0.5 * ((x - mu) / s) ** 2)


def cmf(lam_nm):
    """CIE 1931 2-deg colour matching functions, (xbar, ybar, zbar)."""
    x = np.asarray(lam_nm, np.float64)
    xb = (1.056 * _g(x, 599.8, 37.9, 31.0) + 0.362 * _g(x, 442.0, 16.0, 26.7)
          - 0.065 * _g(x, 501.1, 20.4, 26.2))
    yb = 0.821 * _g(x, 568.8, 46.9, 40.5) + 0.286 * _g(x, 530.9, 16.3, 31.1)
    zb = 1.217 * _g(x, 437.0, 11.8, 36.0) + 0.681 * _g(x, 459.0, 26.0, 13.8)
    return xb, yb, zb


_XB, _YB, _ZB = cmf(LAM)
_DL = float(LAM[1] - LAM[0])

# XYZ -> linear sRGB, Rec. 709 primaries (D65 white point)
_M = np.asarray([[3.2404542, -1.5371385, -0.4985314],
                 [-0.9692660, 1.8760108, 0.0415560],
                 [0.0556434, -0.2040259, 1.0572252]], np.float64)

# equal-energy white in XYZ-normalised form (Y = 1); every colour is pulled
# toward this when it falls outside the display's gamut
_WHITE = np.asarray([1.0, 1.0, 1.0], np.float64)
_WHITE /= _WHITE[1]


def _encode(c):
    """Linear sRGB -> sRGB transfer (the display's own gamma)."""
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1.0 / 2.4) - 0.055)


def _decode(c):
    """sRGB transfer -> linear. The inverse of `_encode`."""
    c = np.clip(np.asarray(c, np.float64) / 255.0, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _xyz_to_srgb255(xyz, fit=True):
    xyz = np.asarray(xyz, np.float64)
    if fit:
        # desaturate toward white until the colour is representable, so a
        # thermometer state that the display cannot show loses saturation
        # rather than changing hue
        k = 0.0
        for _ in range(40):
            lin = _M @ (xyz * (1.0 - k) + _WHITE * k)
            if lin.min() > -1e-6:
                break
            k += 0.025
        xyz = xyz * (1.0 - k) + _WHITE * k
    lin = np.clip(_M @ xyz, 0.0, None)
    lin = lin / max(1e-12, float(lin.max()))
    return _encode(lin) * 255.0


_LUT = {}


def blackbody(T):
    """sRGB triple (0..255 floats) of a blackbody at `T` kelvin."""
    key = float(T)
    hit = _LUT.get(("bb", round(key, 1)))
    if hit is not None:
        return hit
    B = planck(LAM, key)
    X = float(np.sum(_XB * B)) * _DL
    Y = float(np.sum(_YB * B)) * _DL
    Z = float(np.sum(_ZB * B)) * _DL
    out = _xyz_to_srgb255(np.asarray([X / Y, 1.0, Z / Y]))
    _LUT[("bb", round(key, 1))] = out
    return out


def spectral(lam_nm, band=12.0, T=5772.0):
    """sRGB of a narrow band of starlight centred on `lam_nm`.

    A spectroscope does not show a pure wavelength: it shows a slit-limited
    band. `band` is that width in nm, and the light in the band is a 5772 K
    continuum, which is what makes the rendered spectrum read as a photograph
    of a solar spectrum rather than as a rainbow gradient.
    """
    key = ("sp", round(float(lam_nm), 1), round(float(band), 2), round(float(T), 1))
    hit = _LUT.get(key)
    if hit is not None:
        return hit
    w = np.exp(-0.5 * ((LAM - float(lam_nm)) / max(0.5, band / 2.355)) ** 2)
    B = planck(LAM, T) * w
    X = float(np.sum(_XB * B)) * _DL
    Y = float(np.sum(_YB * B)) * _DL
    Z = float(np.sum(_ZB * B)) * _DL
    if Y <= 0:
        out = np.zeros(3)
    else:
        out = _xyz_to_srgb255(np.asarray([X / Y, 1.0, Z / Y]))
        # a slit sees a lot of light; scale so the brightest part of the band is
        # the brightest thing, which is how a spectrogram is printed
        out = out / max(1.0, out.max() / 255.0)
    _LUT[key] = out
    return out


def blackbody_locus(t0, t1, n=900, gamma=1.0):
    """A block of `n` blackbody colours across [t0, t1], shape (n, 3) 0..255.

    `gamma` < 1 spends more of the strip on the cool end, which is where the
    visible change is: 2000 K to 6000 K is a whole story, 20000 K to 24000 K
    is not.
    """
    u = np.linspace(0.0, 1.0, int(n)) ** float(gamma)
    return np.stack([blackbody(t0 + (t1 - t0) * float(x)) for x in u], 0)


def bgr(t):
    """`blackbody` as a 0..1 float triple, ready for the engine."""
    return blackbody(t) / 255.0


def shade(T, k):
    """A blackbody at `T`, read at `k` times the exposure.

    This is how the dark end of the palette is made. A dark version of a bright
    colour is not another colour: it is the same chromaticity with less light on
    it, so the scale happens in linear light and is re-encoded afterwards.
    Doing it in display values would darken the shadows faster than the
    highlights and shift the hue.
    """
    lin = _decode(blackbody(T)) * float(k)
    return _encode(np.clip(lin, 0.0, 1.0)) * 255.0


def spec(lam_nm, band=12.0, T=5772.0):
    """Alias for `spectral` — a palette reads better as spec(656.3)."""
    return spectral(lam_nm, band, T)


if __name__ == "__main__":       # python3 -m mg.color
    print("blackbody, T -> sRGB")
    for T in (1000, 1800, 2000, 2500, 3000, 3800, 4500, 5772, 6500, 8000,
              10000, 15000, 20000, 30000):
        c = blackbody(T)
        print(f"  {T:>7} K  {c[0]:6.1f} {c[1]:6.1f} {c[2]:6.1f}")
    print("spectral lines, nm -> sRGB")
    for w in (400, 434, 470, 486, 510, 530.3, 550, 589, 620, 656.3, 700):
        c = spectral(w)
        print(f"  {w:>7} nm {c[0]:6.1f} {c[1]:6.1f} {c[2]:6.1f}")
    print("2000 K at exposure -> the dark end of the palette")
    for k in (0.020, 0.045, 0.070, 0.130, 0.200, 0.320, 0.520, 1.0):
        c = shade(2000, k)
        print(f"  k={k:<6} {c[0]:6.1f} {c[1]:6.1f} {c[2]:6.1f}")
