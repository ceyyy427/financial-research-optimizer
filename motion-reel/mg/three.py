"""A small 3D engine: parametric surfaces, a camera, and a point renderer.

Deliberately not a triangle rasteriser. Surfaces are sampled densely as points,
projected, and occluded by a sorted scatter — far points scattered first, near
points last, so numpy's "last write wins" for duplicate indices resolves the
nearest sample per pixel. That is exact for a point cloud, needs no per-triangle
Python loop, and its dense slightly-stippled coverage is exactly what prints
well: stipple engraving is a printmaking technique for the same reason.

Normals come from the surface's partial derivatives rather than from faces, so
shading is smooth with no vertex work and no mesh topology to maintain.
"""
from __future__ import annotations

import numpy as np

from .core import clip01

# --------------------------------------------------------------------------
# vectors and rotations
# --------------------------------------------------------------------------
def norm(v, axis=-1):
    return v / np.maximum(np.linalg.norm(v, axis=axis, keepdims=True), 1e-9)


def cross(a, b):
    return np.cross(a, b)


def rot_x(p, a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([p[..., 0], c * p[..., 1] - s * p[..., 2],
                     s * p[..., 1] + c * p[..., 2]], -1)


def rot_y(p, a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([c * p[..., 0] + s * p[..., 2], p[..., 1],
                     -s * p[..., 0] + c * p[..., 2]], -1)


def rot_z(p, a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([c * p[..., 0] - s * p[..., 1],
                     s * p[..., 0] + c * p[..., 1], p[..., 2]], -1)


def fit_radius(p, r=1.0):
    """Uniformly rescale so the furthest vertex sits at radius `r`."""
    m = float(np.linalg.norm(p.reshape(-1, 3), axis=1).max())
    return p * (r / max(m, 1e-9))


# --------------------------------------------------------------------------
# parametric surfaces
# --------------------------------------------------------------------------
_E = 8e-4


def sample(fn, nu, nv):
    """Sample `fn(u, v) -> (..., 3)` on a grid, with analytic normals.

    Returns (P, N, (nu, nv)) with P and N shaped (nu, nv, 3).
    """
    u = np.linspace(0, 1, nu, dtype=np.float32)
    v = np.linspace(0, 1, nv, dtype=np.float32)
    U, V = np.meshgrid(u, v, indexing="ij")
    P = np.asarray(fn(U, V), np.float32)
    du = np.asarray(fn(U + _E, V), np.float32) - np.asarray(fn(U - _E, V), np.float32)
    dv = np.asarray(fn(U, V + _E), np.float32) - np.asarray(fn(U, V - _E), np.float32)
    return P, norm(cross(du, dv)), (nu, nv)


def mobius(width=0.42, radius=1.0):
    """A one-sided band. Thematically apt for a piece about overprinting."""
    def fn(u, v):
        phi = 2 * np.pi * u
        vv = (v - 0.5) * 2.0
        r = radius + vv * width * np.cos(phi * 0.5)
        return np.stack([r * np.cos(phi), r * np.sin(phi),
                         vv * width * np.sin(phi * 0.5)], -1)

    return lambda u, v: fit_radius(fn(u, v), 1.0)


def knot_tube(tube=0.24, p=2, q=3, scale=1.0):
    """A (p, q) torus knot swept as a solid tube."""
    def curve(t):
        return np.stack([(2 + np.cos(q * t)) * np.cos(p * t),
                         (2 + np.cos(q * t)) * np.sin(p * t),
                         np.sin(q * t)], -1)

    def fn(u, v):
        t = 2 * np.pi * u
        a = 2 * np.pi * v
        h = 1e-3
        tng = norm(curve(t + h) - curve(t - h))
        ref = np.stack([np.zeros_like(t), np.zeros_like(t), np.ones_like(t)], -1)
        n1 = norm(cross(tng, ref))
        n2 = norm(cross(tng, n1))
        off = np.cos(a)[..., None] * n1 + np.sin(a)[..., None] * n2
        # normalise to unit radius so a camera distance means the same thing for
        # every form in the piece
        return fit_radius(curve(t) + off * tube, 1.0 * scale)

    return fn


def box_surface(centre, size, nu=64, nv=64, front_bias=3.0):
    """A rectangular box as a point cloud — six sampled faces.

    Sampling the front face more densely than the others is what lets a rack of
    chassis show slats, bays and vents without a mesh or a texture.
    """
    cx, cy, cz = centre
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    u = np.linspace(0, 1, nu, dtype=np.float32)
    v = np.linspace(0, 1, nv, dtype=np.float32)
    U, V = np.meshgrid(u, v, indexing="ij")          # both (nu, nv)
    X = cx - hx + 2 * hx * U
    Y = cy - hy + 2 * hy * V
    Z = cz - hz + 2 * hz * U
    W = cz - hz + 2 * hz * V
    fronts = [
        np.stack([X, Y, np.full_like(X, cz + hz)], -1),
        np.stack([X, Y, np.full_like(X, cz - hz)], -1),
        np.stack([np.full_like(X, cx + hx), Y, W], -1),
        np.stack([np.full_like(X, cx - hx), Y, W], -1),
        np.stack([X, np.full_like(X, cy + hy), W], -1),
        np.stack([X, np.full_like(X, cy - hy), W], -1),
    ]
    normals = [(0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)]
    P = np.concatenate(fronts, 0)
    N = np.concatenate([np.broadcast_to(np.asarray(n, np.float32).reshape(1, 1, 3),
                                        f.shape).copy()
                        for f, n in zip(fronts, normals)], 0)
    dw = np.concatenate([np.full(f.shape[:2], front_bias if i == 0 else 1.0, np.float32)
                         for i, f in enumerate(fronts)], 0)
    return P, N, dw


def supershape(m1=7.0, m2=9.0, n1=0.32, n2=1.7, n3=1.1, scale=1.0):
    """Gielis superformula sphere — spiky and organic, reads as sculpture."""
    def rr(a, m, n1_, n2_, n3_):
        return (np.abs(np.cos(m * a / 4.0)) ** n2_
                + np.abs(np.sin(m * a / 4.0)) ** n3_) ** (-1.0 / n1_)

    def fn(u, v):
        theta = np.pi * (u - 0.5)
        phi = 2 * np.pi * v
        r = rr(theta, m1, n1, n2, n3) * rr(phi, m2, n1, n2, n3)
        q = np.stack([r * np.cos(theta) * np.cos(phi),
                      r * np.cos(theta) * np.sin(phi),
                      r * np.sin(theta)], -1)
        return fit_radius(q, 1.45 * scale)

    return fn


def band(curve_fn, width_fn, twist=1.0, depth=0.0):
    """A thickening band swept along a space curve with a modulated width.

    Used as a data sculpture: `width_fn` reads the track's own spectrum, so a
    figure is a solid object rather than a row of bars.
    """
    def frame(t):
        h = 1e-3
        p = curve_fn(t)
        tng = norm(curve_fn(np.clip(t + h, 0, 1)) - curve_fn(np.clip(t - h, 0, 1)))
        ref = np.stack([np.zeros_like(t), np.zeros_like(t), np.ones_like(t)], -1)
        n1 = norm(cross(tng, ref))
        n2 = norm(cross(tng, n1))
        return p, n1, n2

    def fn(u, v):
        p, n1, n2 = frame(u)
        ang = 2 * np.pi * twist * u
        side = (v - 0.5) * 2.0                       # -1..1 across the band
        across = np.cos(ang)[..., None] * n1 + np.sin(ang)[..., None] * n2
        return p + across * (width_fn(u) * side)[..., None]

    return fn


def sweep_ellipse(curve_fn, half_w_fn, half_t=0.045, twist=0.5):
    """Sweep a flattened ellipse along a space curve — a ribbon with thickness.

    A zero-thickness band degenerates when it turns edge-on to the camera: the
    projected width collapses, adjacent samples land far apart, and the form
    shreds into spikes. A closed, thin elliptical section cannot do that.
    """
    def fn(u, v):
        t = u
        h = 1e-3
        p = curve_fn(t)
        tng = norm(curve_fn(np.clip(t + h, 0, 1)) - curve_fn(np.clip(t - h, 0, 1)))
        ref = np.stack([np.zeros_like(t), np.zeros_like(t), np.ones_like(t)], -1)
        n1 = norm(cross(tng, ref))
        n2 = norm(cross(tng, n1))
        ang = 2 * np.pi * twist * u
        e1 = np.cos(ang)[..., None] * n1 + np.sin(ang)[..., None] * n2
        e2 = -np.sin(ang)[..., None] * n1 + np.cos(ang)[..., None] * n2
        a = 2 * np.pi * v
        return (p + e1 * (np.cos(a) * half_w_fn(u))[..., None]
                + e2 * (np.sin(a) * half_t)[..., None])

    return fn


def spiral_ribbon(radius=1.25, height=2.2, turns=1.6, width=0.55):
    """A wide ribbon spiralling on a cone — a large, legible form."""
    def curve(t):
        a = 2 * np.pi * turns * t
        r = radius * (1.0 - 0.45 * t)
        return np.stack([r * np.cos(a), r * np.sin(a), (t - 0.5) * height], -1)

    def width_fn(t):
        return width * (0.55 + 0.45 * np.sin(np.pi * t))

    return curve, width_fn


# --------------------------------------------------------------------------
# camera
# --------------------------------------------------------------------------
class Camera:
    """Pinhole camera. View space looks down +z from the eye."""

    def __init__(self, eye=(0, 0, 4), target=(0, 0, 0), up=(0, 1, 0),
                 fov=34.0, w=1920, h=1080, shift=(0.0, 0.0)):
        eye = np.asarray(eye, np.float32)
        self.eye = eye
        fwd = norm(np.asarray(target, np.float32) - eye)
        right = norm(cross(fwd, np.asarray(up, np.float32)))
        self.basis = np.stack([right, cross(right, fwd), fwd], 0)
        self.f = (h / 2.0) / np.tan(np.radians(fov) / 2.0)
        self.cx, self.cy = w / 2.0 + shift[0], h / 2.0 + shift[1]
        self.near = 0.08
        self.w, self.h = w, h

    def view(self, p):
        q = p - self.eye
        return np.stack([q @ self.basis[0], q @ self.basis[1], q @ self.basis[2]], -1)

    def project(self, p):
        q = self.view(p)
        z = q[..., 2]
        ok = z > self.near
        zz = np.where(ok, z, 1.0)
        sx = self.cx + q[..., 0] / zz * self.f
        sy = self.cy - q[..., 1] / zz * self.f
        return np.stack([sx, sy, np.where(ok, z, -1.0)], -1)


# --------------------------------------------------------------------------
# shading
# --------------------------------------------------------------------------
KEY = norm(np.asarray([-0.46, 0.58, -0.67], np.float32))   # in view space


def luminance(nv, key=KEY, ambient=0.17, key_gain=1.0, rim_gain=0.52,
              rim_power=2.3, floor=0.0):
    """Clay shading from camera-space normals: key + ambient + view rim.

    Camera-space so the key follows the shot; two-sided because a single
    surface like a Mobius band has no inside to reject.
    """
    n = norm(nv)
    n = np.where((n[:, 2] > 0)[:, None], -n, n)
    lam = np.clip(n @ np.asarray(key, np.float32), 0.0, None)
    rim = (1.0 - np.clip(np.abs(n[:, 2]), 0.0, 1.0)) ** rim_power
    return clip01(floor + ambient + key_gain * lam + rim_gain * rim)


def render(cam, P, N, splat=2, ambient=0.17, key_gain=1.0, rim_gain=0.52,
           clip_pad=0, depth_cue=0.0, soften=0):
    """Project, sort, scatter. Returns (coverage, luminance, depth) buffers."""
    w, h = cam.w, cam.h
    P = P.reshape(-1, 3)
    N = N.reshape(-1, 3)
    q = cam.view(P)
    z = q[:, 2]
    ok = z > cam.near
    if clip_pad:
        sx = cam.cx + q[:, 0] / np.maximum(z, 1e-6) * cam.f
        sy = cam.cy - q[:, 1] / np.maximum(z, 1e-6) * cam.f
        ok &= (sx > -clip_pad) & (sx < w + clip_pad) & (sy > -clip_pad) & (sy < h + clip_pad)
    if not ok.any():
        z0 = np.zeros((h, w), np.float32)
        return z0, z0.copy(), z0.copy()

    q, nn, zz = q[ok], N[ok], z[ok]
    nv = np.stack([nn @ cam.basis[0], nn @ cam.basis[1], nn @ cam.basis[2]], -1)
    lum = luminance(nv, ambient=ambient, key_gain=key_gain, rim_gain=rim_gain)
    if depth_cue:
        dz = (zz - zz.min()) / max(1e-6, zz.max() - zz.min())
        lum = clip01(lum * (1.0 - depth_cue * dz))

    sx = cam.cx + q[:, 0] / zz * cam.f
    sy = cam.cy - q[:, 1] / zz * cam.f
    ix = np.round(sx).astype(np.int32)
    iy = np.round(sy).astype(np.int32)

    # Expand every sample to its splat footprint, then do a single far-to-near
    # scatter. Sorting once over the whole expanded set (rather than per tap)
    # keeps depth ordering exact even where footprints overlap.
    s = max(1, int(splat))
    offs = np.array([(dx, dy) for dy in range(s) for dx in range(s)], np.int32)
    px = (ix[:, None] + offs[None, :, 0]).ravel()
    py = (iy[:, None] + offs[None, :, 1]).ravel()
    zr = np.repeat(zz, len(offs))
    lr = np.repeat(lum, len(offs))

    m = (px >= 0) & (px < w) & (py >= 0) & (py < h)
    cove = np.zeros(h * w, np.float32)
    shad = np.zeros(h * w, np.float32)
    dept = np.zeros(h * w, np.float32)
    if m.any():
        sel = np.flatnonzero(m)
        o = sel[np.argsort(-zr[sel])]
        idx = py[o].astype(np.int64) * w + px[o].astype(np.int64)
        cove[idx] = 1.0
        shad[idx] = lr[o]
        dept[idx] = zr[o]
    cove = cove.reshape(h, w)
    shad = shad.reshape(h, w)
    dept = dept.reshape(h, w)
    if soften:
        # A dense point cloud still leaves sampling structure at grazing angles,
        # which beats against the halftone screen and shows as moire. A sub-pixel
        # blur on coverage and luminance removes it before screening.
        from .core import blur as _blur
        r = max(1, int(round(soften)))
        cove = np.clip(_blur(cove, r, 1) * 1.35, 0.0, 1.0)
        m = cove > 0.02
        shad = np.where(m, _blur(shad, r, 1) / np.maximum(_blur(m.astype(np.float32), r, 1), 1e-3), 0.0)
        shad = np.clip(shad, 0.0, 1.2)
    zmax = max(1e-6, float(zz.max()))
    return cove, shad, dept / zmax


def visible_grid(cam, Pgrid, depth, tol=0.010):
    """Per-sample visibility against a depth buffer, as a boolean grid.

    Used to draw iso-parametric lines with hidden-line removal so only the near
    side of the form draws — the engraved-plate look.
    """
    nu, nv = Pgrid.shape[:2]
    pr = cam.project(Pgrid.reshape(-1, 3))
    z = pr[:, 2].reshape(nu, nv) / max(1e-6, float(pr[:, 2].max()))
    sx = pr[:, 0].reshape(nu, nv)
    sy = pr[:, 1].reshape(nu, nv)
    ix = np.clip(np.round(sx).astype(np.int32), 0, cam.w - 1)
    iy = np.clip(np.round(sy).astype(np.int32), 0, cam.h - 1)
    d = depth[iy, ix]
    return (z <= d + tol) & (pr[:, 2].reshape(nu, nv) > 0)


def contour_grid(cam, Pgrid, vis):
    """Visible runs of iso-parametric curves, as a list of point lists."""
    nu, nv = Pgrid.shape[:2]
    pr = cam.project(Pgrid.reshape(-1, 3)).reshape(nu, nv, 3)
    runs = []
    for axis in (0, 1):
        # axis 0 walks along v at fixed u; axis 1 walks along u at fixed v
        n_lines = nu if axis == 0 else nv
        for i in range(0, n_lines, max(1, n_lines // 42)):
            pts = pr[i, :, :2] if axis == 0 else pr[:, i, :2]
            v = vis[i, :] if axis == 0 else vis[:, i]
            start = None
            for j, ok in enumerate(v):
                if ok and start is None:
                    start = j
                elif not ok and start is not None:
                    if j - start > 2:
                        runs.append([tuple(pts[k]) for k in range(start, j)])
                    start = None
            if start is not None and len(v) - start > 2:
                runs.append([tuple(pts[k]) for k in range(start, len(v))])
    return runs
