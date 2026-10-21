"""geom.py - procedural mesh toolkit for the code forge.

Everything is numpy.  Conventions (identical to glTF):
  * right handed, +Y up, the figure faces +Z, +X is the viewer's right when looking at the front.
  * triangles are counter-clockwise when seen from the outside.
  * units are board squares (pedestal diameter 0.80, pawn 1.05 tall).

A `Mesh` carries positions P, faces F, normals N, UV, vertex colours C (RGBA 0..1) and any extra
per-vertex arrays in `A`.  Primitive builders return already-shaded meshes (smooth normals with
a crease angle).  Typical use:

    body  = lathe([(0, 0), (.10, 0), (.12, .2), (.08, .5), (0, .55)], segments=32)
    arm   = tube([(0, 0, 0), (0, -.1, .05), (0, -.2, .02)], radii=[.03, .026, .02], cap="round")
    plate = extrude(plate_outline, depth=.012, bevel=.004)
    mesh  = merge([body, arm.translated(.1, .5, 0), plate])

Profile convention for `lathe`: points (r, y) walked so the solid is on your LEFT in the
(r right, y up) plane - i.e. counter-clockwise: up the OUTER wall from bottom to top, along the top
toward the axis.  A closed solid starts on the axis at the bottom (0, y0) and ends on the axis at the
top (0, y1).
"""
from __future__ import annotations

import heapq
import math
from typing import Callable, Iterable, Sequence

import numpy as np

TAU = math.pi * 2.0


# ------------------------------------------------------------------ small math
def normalize(v, axis=-1):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-12)


def rot_matrix(rx=0.0, ry=0.0, rz=0.0):
    """3x3 rotation from Euler degrees: X first, then Y, then Z (extrinsic)."""
    ax, ay, az = (math.radians(a) for a in (rx, ry, rz))
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def axis_angle(axis, deg):
    a = normalize(np.asarray(axis, dtype=np.float64))
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    x, y, z = a
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def rot_between(a, b):
    """Rotation matrix taking unit vector a onto unit vector b."""
    a, b = normalize(np.asarray(a, float)), normalize(np.asarray(b, float))
    c = float(np.dot(a, b))
    if c > 0.999999:
        return np.eye(3)
    if c < -0.999999:
        perp = np.cross(a, [1, 0, 0])
        if np.linalg.norm(perp) < 1e-6:
            perp = np.cross(a, [0, 0, 1])
        return axis_angle(perp, 180.0)
    v = np.cross(a, b)
    k = 1.0 / (1.0 + c)
    return np.array([[v[0] * v[0] * k + c, v[0] * v[1] * k - v[2], v[0] * v[2] * k + v[1]],
                     [v[1] * v[0] * k + v[2], v[1] * v[1] * k + c, v[1] * v[2] * k - v[0]],
                     [v[2] * v[0] * k - v[1], v[2] * v[1] * k + v[0], v[2] * v[2] * k + c]])


def xform(pos=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    """4x4 matrix: scale, then rotate (Euler degrees XYZ), then translate."""
    M = np.eye(4)
    s = np.broadcast_to(np.asarray(scale, dtype=np.float64), (3,))
    M[:3, :3] = rot_matrix(*rot) @ np.diag(s)
    M[:3, 3] = pos
    return M


def look_basis(direction, up=(0, 1, 0)):
    """Rotation whose local +Y maps to `direction` (a stable 'point this along d' helper)."""
    return rot_between(np.array([0, 1.0, 0]), direction)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0 + 1e-12), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ gradient noise (3D)
_PERM_CACHE: dict = {}


def _perm(seed):
    if seed not in _PERM_CACHE:
        rng = np.random.default_rng(seed + 12345)
        p = rng.permutation(256)
        _PERM_CACHE[seed] = np.concatenate([p, p])
    return _PERM_CACHE[seed]


_GRADS = np.array([[1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0], [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
                   [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1]], dtype=np.float64)


def noise3(P, seed=0):
    """Improved Perlin noise at points P (n,3) -> (n,) in about [-1, 1]."""
    P = np.asarray(P, dtype=np.float64)
    perm = _perm(seed)
    xi = np.floor(P).astype(np.int64)
    f = P - xi
    xi &= 255
    u = f * f * f * (f * (f * 6 - 15) + 10)

    def grad(ix, iy, iz, dx, dy, dz):
        h = perm[perm[perm[ix] + iy] + iz] % 12
        g = _GRADS[h]
        return g[:, 0] * dx + g[:, 1] * dy + g[:, 2] * dz

    x0, y0, z0 = xi[:, 0], xi[:, 1], xi[:, 2]
    x1, y1, z1 = x0 + 1, y0 + 1, z0 + 1
    fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
    n000 = grad(x0, y0, z0, fx, fy, fz)
    n100 = grad(x1, y0, z0, fx - 1, fy, fz)
    n010 = grad(x0, y1, z0, fx, fy - 1, fz)
    n110 = grad(x1, y1, z0, fx - 1, fy - 1, fz)
    n001 = grad(x0, y0, z1, fx, fy, fz - 1)
    n101 = grad(x1, y0, z1, fx - 1, fy, fz - 1)
    n011 = grad(x0, y1, z1, fx, fy - 1, fz - 1)
    n111 = grad(x1, y1, z1, fx - 1, fy - 1, fz - 1)
    ux, uy, uz = u[:, 0], u[:, 1], u[:, 2]
    nx00 = n000 + ux * (n100 - n000)
    nx10 = n010 + ux * (n110 - n010)
    nx01 = n001 + ux * (n101 - n001)
    nx11 = n011 + ux * (n111 - n011)
    nxy0 = nx00 + uy * (nx10 - nx00)
    nxy1 = nx01 + uy * (nx11 - nx01)
    return (nxy0 + uz * (nxy1 - nxy0)) * 1.15


def fbm3(P, freq=4.0, octaves=4, lacunarity=2.0, gain=0.5, seed=0, ridged=False):
    P = np.asarray(P, dtype=np.float64)
    out = np.zeros(len(P))
    amp, f, norm = 1.0, freq, 0.0
    for o in range(octaves):
        n = noise3(P * f + o * 17.31, seed + o)
        if ridged:
            n = 1.0 - np.abs(n) * 1.6
        out += amp * n
        norm += amp
        amp *= gain
        f *= lacunarity
    return out / norm


# ------------------------------------------------------------------ 2D helpers
def spline(points, samples=6, closed=False, alpha=0.0):
    """Catmull-Rom through `points` (any dimension). `samples` per segment. alpha 0 uniform, .5 centripetal."""
    p = np.asarray(points, dtype=np.float64)
    n = len(p)
    if n < 3:
        return p.copy()
    if closed:
        ext = np.concatenate([p[-1:], p, p[:2]])
        segs = n
    else:
        ext = np.concatenate([2 * p[:1] - p[1:2], p, 2 * p[-1:] - p[-2:-1]])
        segs = n - 1
    out = []
    ts = np.linspace(0, 1, samples, endpoint=False)
    for i in range(segs):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        t = ts[:, None]
        pts = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
        out.append(pts)
    if not closed:
        out.append(p[-1:][None, 0, :] if p.ndim == 2 else p[-1:])
    return np.concatenate(out)


def bevel_polyline(points, radius, segments=3, closed=False, sharp=()):
    """Round the corners of a polyline with quadratic arcs.  `radius` scalar or per-vertex array.
    `sharp` lists vertex indices to leave untouched."""
    p = np.asarray(points, dtype=np.float64)
    n = len(p)
    r = np.broadcast_to(np.asarray(radius, dtype=np.float64), (n,))
    out = []
    for i in range(n):
        if (not closed and (i == 0 or i == n - 1)) or i in sharp or r[i] <= 1e-9:
            out.append(p[i][None])
            continue
        a, b, c = p[(i - 1) % n], p[i], p[(i + 1) % n]
        d1, d2 = a - b, c - b
        l1, l2 = np.linalg.norm(d1), np.linalg.norm(d2)
        if l1 < 1e-9 or l2 < 1e-9:
            out.append(b[None])
            continue
        u1, u2 = d1 / l1, d2 / l2
        cosang = np.clip(np.dot(u1, u2), -1, 1)
        ang = math.acos(cosang)
        if ang > math.pi - 1e-3 or ang < 1e-3:
            out.append(b[None])
            continue
        t = min(r[i] / math.tan(ang / 2), l1 * 0.5, l2 * 0.5)
        s, e = b + u1 * t, b + u2 * t
        ts = np.linspace(0, 1, segments + 2)[:, None]
        arc = (1 - ts) ** 2 * s + 2 * (1 - ts) * ts * b + ts ** 2 * e
        out.append(arc)
    return np.concatenate(out)


def polygon_area(poly):
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def ngon(n, radius=1.0, rotation_deg=0.0, rounded=0.0, rounded_segments=2):
    """Regular polygon (CCW).  `rounded` = corner radius fraction of `radius`."""
    a = np.radians(rotation_deg) + np.arange(n) * TAU / n
    pts = np.stack([np.cos(a), np.sin(a)], 1) * radius
    if rounded > 0:
        pts = bevel_polyline(pts, rounded * radius, rounded_segments, closed=True)
    return pts


def offset_polygon(poly, d):
    """Mitred offset of a CCW polygon (positive d grows it)."""
    p = np.asarray(poly, dtype=np.float64)
    prv, nxt = np.roll(p, 1, 0), np.roll(p, -1, 0)
    e1, e2 = normalize(p - prv), normalize(nxt - p)
    n1 = np.stack([e1[:, 1], -e1[:, 0]], 1)
    n2 = np.stack([e2[:, 1], -e2[:, 0]], 1)
    bis = n1 + n2
    k = 1.0 + np.sum(n1 * n2, 1)
    k = np.maximum(k, 0.35)
    return p + bis / k[:, None] * d


def triangulate_polygon(poly):
    """Ear clipping for a simple polygon (any winding). Returns (m,3) index array into `poly`, CCW."""
    p = np.asarray(poly, dtype=np.float64)
    n = len(p)
    idx = list(range(n))
    if polygon_area(p) < 0:
        idx.reverse()
    tris = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    guard = 0
    while len(idx) > 3 and guard < 10 * n * n:
        guard += 1
        m = len(idx)
        clipped = False
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b, c = p[i0], p[i1], p[i2]
            if cross(a, b, c) <= 1e-14:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                q = p[j]
                if cross(a, b, q) >= -1e-14 and cross(b, c, q) >= -1e-14 and cross(c, a, q) >= -1e-14:
                    ok = False
                    break
            if ok:
                tris.append((i0, i1, i2))
                idx.pop(k)
                clipped = True
                break
        if not clipped:
            # degenerate polygon: drop the flattest vertex
            areas = [abs(cross(p[idx[(k - 1) % len(idx)]], p[idx[k]], p[idx[(k + 1) % len(idx)]])) for k in range(len(idx))]
            idx.pop(int(np.argmin(areas)))
    if len(idx) == 3:
        tris.append(tuple(idx))
    return np.array(tris, dtype=np.int64).reshape(-1, 3)


# ------------------------------------------------------------------ Mesh
class Mesh:
    """Indexed triangle mesh with per-vertex normals, UV, colour and extra attributes."""

    def __init__(self, P, F, UV=None, N=None, C=None, A=None, crease=50.0):
        self.P = np.ascontiguousarray(P, dtype=np.float64).reshape(-1, 3)
        self.F = np.ascontiguousarray(F, dtype=np.int64).reshape(-1, 3)
        n = len(self.P)
        self.UV = np.zeros((n, 2)) if UV is None else np.ascontiguousarray(UV, dtype=np.float64).reshape(n, 2)
        self.N = None if N is None else np.ascontiguousarray(N, dtype=np.float64).reshape(n, 3)
        self.C = None if C is None else np.ascontiguousarray(C, dtype=np.float64).reshape(n, 4)
        self.A = {k: np.asarray(v, dtype=np.float64).reshape(n, -1) for k, v in (A or {}).items()}
        self.crease = crease

    # -- basics
    def copy(self):
        m = Mesh(self.P.copy(), self.F.copy(), self.UV.copy(), None if self.N is None else self.N.copy(),
                 None if self.C is None else self.C.copy(), {k: v.copy() for k, v in self.A.items()}, self.crease)
        return m

    @property
    def tri_count(self):
        return len(self.F)

    @property
    def vert_count(self):
        return len(self.P)

    def bounds(self):
        return self.P.min(0), self.P.max(0)

    def center(self):
        lo, hi = self.bounds()
        return (lo + hi) / 2

    def face_normals(self, unit=True):
        P, F = self.P, self.F
        n = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
        return normalize(n) if unit else n

    def face_areas(self):
        return 0.5 * np.linalg.norm(self.face_normals(False), axis=1)

    def area(self):
        return float(self.face_areas().sum())

    def volume(self):
        P, F = self.P, self.F
        return float(np.sum(np.einsum('ij,ij->i', P[F[:, 0]], np.cross(P[F[:, 1]], P[F[:, 2]]))) / 6.0)

    # -- transforms (all return new meshes)
    def transformed(self, M):
        M = np.asarray(M, dtype=np.float64)
        R = M[:3, :3]
        out = self.copy()
        out.P = self.P @ R.T + M[:3, 3]
        if self.N is not None:
            try:
                Rn = np.linalg.inv(R).T
            except np.linalg.LinAlgError:
                Rn = R
            out.N = normalize(self.N @ Rn.T)
        if np.linalg.det(R) < 0:
            out.F = out.F[:, ::-1].copy()
            if out.N is not None:
                out.N = -out.N
        return out

    def translated(self, x=0.0, y=0.0, z=0.0):
        if np.ndim(x) > 0:
            x, y, z = x
        out = self.copy()
        out.P = out.P + np.array([x, y, z])
        return out

    def scaled(self, sx=1.0, sy=None, sz=None):
        if sy is None:
            sy = sz = sx
        return self.transformed(np.diag([sx, sy, sz, 1.0]))

    def rotated(self, rx=0.0, ry=0.0, rz=0.0, pivot=(0, 0, 0)):
        M = xform(rot=(rx, ry, rz))
        pv = np.asarray(pivot, dtype=np.float64)
        M[:3, 3] = pv - M[:3, :3] @ pv
        return self.transformed(M)

    def rotated_axis(self, axis, deg, pivot=(0, 0, 0)):
        M = np.eye(4)
        M[:3, :3] = axis_angle(axis, deg)
        pv = np.asarray(pivot, dtype=np.float64)
        M[:3, 3] = pv - M[:3, :3] @ pv
        return self.transformed(M)

    def at(self, pos=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
        return self.transformed(xform(pos, rot, scale))

    def aimed(self, direction, pos=(0, 0, 0)):
        """Rotate so local +Y points along `direction`, then translate."""
        M = np.eye(4)
        M[:3, :3] = rot_between([0, 1, 0], direction)
        M[:3, 3] = pos
        return self.transformed(M)

    def flipped(self):
        out = self.copy()
        out.F = out.F[:, ::-1].copy()
        if out.N is not None:
            out.N = -out.N
        return out

    def mirrored(self, axis="x"):
        k = "xyz".index(axis)
        s = np.ones(3)
        s[k] = -1
        return self.transformed(np.diag([*s, 1.0]))

    def symmetrized(self, axis="x"):
        return merge([self, self.mirrored(axis)])

    # -- colour / attribute helpers
    def with_color(self, rgba):
        out = self.copy()
        rgba = np.asarray(rgba, dtype=np.float64)
        if rgba.size == 3:
            rgba = np.append(rgba, 1.0)
        out.C = np.tile(rgba, (len(out.P), 1))
        return out

    def set_attr(self, name, values):
        self.A[name] = np.asarray(values, dtype=np.float64).reshape(len(self.P), -1)
        return self

    # -- topology
    def cleaned(self, eps=1e-12):
        """Drop degenerate (zero area / repeated index) triangles and unused vertices."""
        F = self.F
        ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
        if ok.any():
            n = np.cross(self.P[F[ok, 1]] - self.P[F[ok, 0]], self.P[F[ok, 2]] - self.P[F[ok, 0]])
            good = np.linalg.norm(n, axis=1) > eps
            tmp = np.where(ok)[0][~good]
            ok[tmp] = False
        out = self.copy()
        out.F = F[ok]
        used = np.unique(out.F)
        remap = -np.ones(len(out.P), dtype=np.int64)
        remap[used] = np.arange(len(used))
        out.P, out.UV = out.P[used], out.UV[used]
        out.N = None if out.N is None else out.N[used]
        out.C = None if out.C is None else out.C[used]
        out.A = {k: v[used] for k, v in out.A.items()}
        out.F = remap[out.F]
        return out

    def weld_ids(self, eps=1e-6):
        """Vertex -> position-group id (vertices at the same location share an id)."""
        key = np.round(self.P / eps).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        return inv.reshape(-1)

    def unwelded(self):
        """Every triangle gets private vertices (needed before per-face UV projection)."""
        F = self.F.reshape(-1)
        out = Mesh(self.P[F], np.arange(len(F)).reshape(-1, 3), self.UV[F], None if self.N is None else self.N[F],
                   None if self.C is None else self.C[F], {k: v[F] for k, v in self.A.items()}, self.crease)
        return out

    def compact(self, decimals=5):
        """Merge vertices with identical attributes (after unwelded/shaded work)."""
        cols = [self.P, self.UV]
        if self.N is not None:
            cols.append(self.N)
        if self.C is not None:
            cols.append(self.C)
        for k in sorted(self.A):
            cols.append(self.A[k])
        M = np.round(np.concatenate(cols, 1), decimals)
        _, first, inv = np.unique(M, axis=0, return_index=True, return_inverse=True)
        inv = inv.reshape(-1)
        out = Mesh(self.P[first], inv[self.F], self.UV[first], None if self.N is None else self.N[first],
                   None if self.C is None else self.C[first], {k: v[first] for k, v in self.A.items()}, self.crease)
        return out.cleaned()

    # -- shading
    def smooth_normals(self, eps=1e-6):
        """Per-vertex normals averaged over all vertices sharing a position (no crease)."""
        P, F = self.P, self.F
        fn = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
        gid = self.weld_ids(eps)
        acc = np.zeros((gid.max() + 1, 3))
        for k in range(3):
            np.add.at(acc, gid[F[:, k]], fn)
        return normalize(acc[gid])

    def shade(self, crease=None):
        """Recompute normals: area/angle weighted, split at edges sharper than `crease` degrees.
        Returns a new (unwelded-where-needed) mesh."""
        if crease is None:
            crease = self.crease
        if len(self.F) == 0:
            out = self.copy()
            out.N = np.zeros_like(out.P)
            return out
        P, F = self.P, self.F
        m = len(F)
        fn = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
        area2 = np.linalg.norm(fn, axis=1)
        fu = fn / np.maximum(area2, 1e-20)[:, None]
        # corner angles
        ang = np.zeros((m, 3))
        for k in range(3):
            a = P[F[:, (k + 1) % 3]] - P[F[:, k]]
            b = P[F[:, (k + 2) % 3]] - P[F[:, k]]
            ca = np.einsum('ij,ij->i', a, b) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-20)
            ang[:, k] = np.arccos(np.clip(ca, -1, 1))
        weight = ang * (area2 > 1e-14)[:, None]
        gid = self.weld_ids()
        cg = gid[F].reshape(-1)  # corner group (3m)
        cf = np.repeat(np.arange(m), 3)
        cw = weight.reshape(-1)
        order = np.argsort(cg, kind="stable")
        sg = cg[order]
        starts = np.searchsorted(sg, np.arange(sg.max() + 2))
        cnt = starts[1:] - starts[:-1]
        pos_in_sorted = np.empty_like(order)
        pos_in_sorted[order] = np.arange(len(order))
        my_group = cg
        my_start = starts[my_group]
        my_cnt = cnt[my_group]
        cos_c = math.cos(math.radians(crease))
        acc = np.zeros((3 * m, 3))
        fu_c = fu[cf]
        maxc = int(my_cnt.max())
        sorted_f = cf[order]
        sorted_w = cw[order]
        for k in range(maxc):
            valid = k < my_cnt
            oi = np.where(valid, my_start + k, 0)
            of = sorted_f[oi]
            w = sorted_w[oi]
            d = np.einsum('ij,ij->i', fu_c, fu[of])
            use = valid & (d > cos_c - 1e-9)
            acc += (use * w)[:, None] * fu[of]
        nrm = np.linalg.norm(acc, axis=1)
        bad = nrm < 1e-12
        acc[bad] = fu_c[bad]
        N = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
        flat = F.reshape(-1)
        out = Mesh(P[flat], np.arange(3 * m).reshape(m, 3), self.UV[flat], N, None if self.C is None else self.C[flat],
                   {k: v[flat] for k, v in self.A.items()}, crease)
        return out.compact().cleaned()

    # -- UV
    def uv_box(self, tile=0.25, offset=(0.0, 0.0)):
        """Box/triplanar-by-dominant-axis projection in world units / tile (unwelds)."""
        m = self.unwelded()
        n = m.face_normals()
        ax = np.argmax(np.abs(n), axis=1)
        P = m.P.reshape(-1, 3, 3)
        uv = np.zeros((len(m.F), 3, 2))
        for a in range(3):
            sel = ax == a
            if not sel.any():
                continue
            if a == 0:   # facing x: u=z, v=y
                u, v = P[sel][:, :, 2] * np.sign(n[sel, 0])[:, None], P[sel][:, :, 1]
            elif a == 1:  # facing y: u=x, v=z
                u, v = P[sel][:, :, 0], P[sel][:, :, 2] * np.sign(n[sel, 1])[:, None]
            else:
                u, v = P[sel][:, :, 0] * np.sign(n[sel, 2])[:, None], P[sel][:, :, 1]
            uv[sel, :, 0], uv[sel, :, 1] = u, v
        m.UV = uv.reshape(-1, 2) / tile + np.asarray(offset)
        return m.compact()

    def uv_planar(self, axis="z", tile=0.25, offset=(0.0, 0.0)):
        out = self.copy()
        i, j = {"x": (2, 1), "y": (0, 2), "z": (0, 1)}[axis]
        out.UV = np.stack([out.P[:, i], out.P[:, j]], 1) / tile + np.asarray(offset)
        return out

    def uv_cylindrical(self, axis="y", tile=0.25, repeats=None, center=(0, 0, 0)):
        """Cylindrical projection around `axis` (unwelds, fixes the wrap seam)."""
        m = self.unwelded()
        k = "xyz".index(axis)
        a1, a2 = [i for i in range(3) if i != k]
        c = np.asarray(center)
        P = m.P - c
        th = np.arctan2(P[:, a1], P[:, a2]) / TAU  # -0.5..0.5
        r_mean = float(np.mean(np.hypot(P[:, a1], P[:, a2])))
        rep = repeats if repeats else max(1, int(round(TAU * r_mean / tile)))
        th = th.reshape(-1, 3)
        span = th.max(1) - th.min(1)
        wrap = span > 0.5
        th[wrap] = np.where(th[wrap] < 0, th[wrap] + 1.0, th[wrap])
        m.UV = np.stack([th.reshape(-1) * rep, P[:, k] / tile], 1)
        return m.compact()

    # -- deformation
    def subdivided(self, levels=1):
        """Linear 1->4 midpoint subdivision (welded edges, attributes interpolated)."""
        m = self
        for _ in range(levels):
            m = _subdivide_once(m)
        return m

    def subdivided_to(self, max_edge, max_levels=5):
        m = self
        for _ in range(max_levels):
            e = np.concatenate([np.linalg.norm(m.P[m.F[:, i]] - m.P[m.F[:, (i + 1) % 3]], axis=1) for i in range(3)])
            if e.max() <= max_edge:
                break
            m = _subdivide_once(m)
        return m

    def displaced(self, fn: Callable[[np.ndarray, np.ndarray], np.ndarray], reshade=True):
        """Move vertices along their (position-welded) smooth normal by fn(P, N) -> amount (n,)."""
        n = self.smooth_normals()
        amt = np.asarray(fn(self.P, n), dtype=np.float64).reshape(-1)
        out = self.copy()
        out.P = self.P + n * amt[:, None]
        out.N = None
        return out.shade() if reshade else out

    def noised(self, amp=0.01, freq=8.0, octaves=3, seed=0, ridged=False, mask=None, bias=0.0):
        def f(P, N):
            v = fbm3(P, freq, octaves, seed=seed, ridged=ridged) + bias
            if mask is not None:
                v = v * mask(P, N)
            return v * amp
        return self.displaced(f)

    def dented(self, count=12, radius=0.03, depth=0.006, seed=0, region: Callable | None = None, radius_jitter=0.5):
        """Hammer dents: smooth round depressions scattered over the surface."""
        pts, nrm = scatter_on_surface(self, count * 3, seed=seed)
        if region is not None:
            keep = region(pts)
            pts, nrm = pts[keep], nrm[keep]
        pts, nrm = pts[:count], nrm[:count]
        rng = np.random.default_rng(seed + 7)
        rad = radius * (1 + radius_jitter * (rng.random(len(pts)) - 0.5))
        dep = depth * (0.5 + rng.random(len(pts)))

        def f(P, N):
            tot = np.zeros(len(P))
            for c, r, d in zip(pts, rad, dep):
                dist = np.linalg.norm(P - c, axis=1) / r
                tot -= d * np.clip(1 - dist * dist, 0, 1) ** 2
            return tot
        return self.displaced(f)

    def transformed_uv(self, scale=(1, 1), offset=(0, 0)):
        out = self.copy()
        out.UV = out.UV * np.asarray(scale) + np.asarray(offset)
        return out


# ------------------------------------------------------------------ mesh-level ops
def merge(meshes: Iterable[Mesh]) -> Mesh:
    ms = [m for m in meshes if m is not None and len(m.F)]
    if not ms:
        return Mesh(np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64))
    P = np.concatenate([m.P for m in ms])
    offs = np.cumsum([0] + [len(m.P) for m in ms[:-1]])
    F = np.concatenate([m.F + o for m, o in zip(ms, offs)])
    UV = np.concatenate([m.UV for m in ms])
    N = np.concatenate([m.N for m in ms]) if all(m.N is not None for m in ms) else None
    if any(m.C is not None for m in ms):
        C = np.concatenate([m.C if m.C is not None else np.ones((len(m.P), 4)) for m in ms])
    else:
        C = None
    keys = set().union(*[m.A.keys() for m in ms])
    A = {}
    for k in keys:
        w = max(m.A[k].shape[1] for m in ms if k in m.A)
        A[k] = np.concatenate([m.A[k] if k in m.A else np.zeros((len(m.P), w)) for m in ms])
    return Mesh(P, F, UV, N, C, A, ms[0].crease)


def _subdivide_once(m: Mesh) -> Mesh:
    F = m.F
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    es = np.sort(e, axis=1)
    uniq, inv = np.unique(es, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    nv = len(m.P)
    mid = nv + np.arange(len(uniq))
    nf = len(F)
    m01, m12, m20 = mid[inv[:nf]], mid[inv[nf:2 * nf]], mid[inv[2 * nf:]]
    a, b, c = F[:, 0], F[:, 1], F[:, 2]
    newF = np.concatenate([np.stack([a, m01, m20], 1), np.stack([m01, b, m12], 1),
                           np.stack([m20, m12, c], 1), np.stack([m01, m12, m20], 1)])

    def interp(X):
        return np.concatenate([X, 0.5 * (X[uniq[:, 0]] + X[uniq[:, 1]])])
    N = None
    if m.N is not None:
        N = normalize(interp(m.N))
    return Mesh(interp(m.P), newF, interp(m.UV), N, None if m.C is None else interp(m.C),
                {k: interp(v) for k, v in m.A.items()}, m.crease)


def scatter_on_surface(mesh: Mesh, count: int, seed=0, weights: np.ndarray | None = None):
    """Area-weighted random surface points -> (points (n,3), normals (n,3))."""
    rng = np.random.default_rng(seed)
    area = mesh.face_areas()
    if weights is not None:
        area = area * weights
    area = area / max(area.sum(), 1e-12)
    fi = rng.choice(len(mesh.F), size=count, p=area)
    r1, r2 = rng.random(count), rng.random(count)
    s = np.sqrt(r1)
    u, v = 1 - s, s * (1 - r2)
    w = s * r2
    F = mesh.F[fi]
    pts = mesh.P[F[:, 0]] * u[:, None] + mesh.P[F[:, 1]] * v[:, None] + mesh.P[F[:, 2]] * w[:, None]
    nrm = mesh.face_normals()[fi]
    return pts, nrm


def instances(base: Mesh, positions, normals=None, scales=1.0, spins=None, up=(0, 1, 0)) -> Mesh:
    """Copies of `base` (modelled pointing along +Y) placed at positions, aligned to normals."""
    positions = np.asarray(positions, dtype=np.float64).reshape(-1, 3)
    k = len(positions)
    if k == 0:
        return Mesh(np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64))
    scales = np.broadcast_to(np.asarray(scales, dtype=np.float64), (k,))
    if normals is None:
        normals = np.tile(np.asarray(up, dtype=np.float64), (k, 1))
    normals = normalize(np.asarray(normals, dtype=np.float64).reshape(-1, 3))
    Rs = np.stack([rot_between([0, 1, 0], n) for n in normals])
    if spins is not None:
        spins = np.broadcast_to(np.asarray(spins, dtype=np.float64), (k,))
        for i in range(k):
            Rs[i] = Rs[i] @ axis_angle([0, 1, 0], spins[i])
    v = len(base.P)
    P = np.einsum('kij,vj->kvi', Rs, base.P) * scales[:, None, None] + positions[:, None, :]
    N = None if base.N is None else np.einsum('kij,vj->kvi', Rs, base.N)
    F = np.concatenate([base.F + i * v for i in range(k)])
    UV = np.tile(base.UV, (k, 1))
    C = None if base.C is None else np.tile(base.C, (k, 1))
    return Mesh(P.reshape(-1, 3), F, UV, None if N is None else N.reshape(-1, 3), C,
                {kk: np.tile(vv, (k, 1)) for kk, vv in base.A.items()}, base.crease)


# ------------------------------------------------------------------ surfaces
def loft(rings, closed=True, cap_start=False, cap_end=False, u_rep=None, v_tile=0.25, u_tile=None, crease=50.0,
         uv=None, shade=True) -> Mesh:
    """Skin a stack of rings.  rings: (R, K, 3).  Triangles follow normal = t_column x t_ring, so rings
    must progress such that this points outward (see module docstring).  Closed rings get a duplicated
    seam column so texture coordinates wrap cleanly (u_rep = integer number of texture repeats)."""
    rings = np.asarray(rings, dtype=np.float64)
    R, K, _ = rings.shape
    if closed:
        rings = np.concatenate([rings, rings[:, :1]], axis=1)
    Kc = rings.shape[1]
    P = rings.reshape(-1, 3)
    # uv: v along rings, u along columns
    seg_v = np.linalg.norm(np.diff(rings, axis=0), axis=2).mean(axis=1) if R > 1 else np.zeros(0)
    v = np.concatenate([[0], np.cumsum(seg_v)]) / v_tile
    if closed:
        circ = np.linalg.norm(np.diff(rings, axis=1), axis=2).sum(axis=1).max()
        rep = u_rep if u_rep else max(1, int(round(circ / (u_tile or v_tile))))
        u = np.linspace(0, rep, Kc)
    else:
        seg_u = np.linalg.norm(np.diff(rings, axis=1), axis=2).mean(axis=0)
        u = np.concatenate([[0], np.cumsum(seg_u)]) / (u_tile or v_tile)
    UV = np.stack(np.broadcast_arrays(u[None, :], v[:, None]), axis=2).reshape(-1, 2)
    if uv is not None:
        UV = uv
    idx = np.arange(R * Kc).reshape(R, Kc)
    a, b = idx[:-1, :-1], idx[:-1, 1:]
    c, d = idx[1:, 1:], idx[1:, :-1]
    F = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
    mesh = Mesh(P, F, UV, crease=crease)
    parts = [mesh]
    if closed and (cap_start or cap_end):
        for flag, ring_i, sign in ((cap_start, 0, -1), (cap_end, R - 1, 1)):
            if not flag:
                continue
            ring = rings[ring_i][:-1]
            ctr = ring.mean(0)
            Pc = np.vstack([ctr[None], ring])
            kk = len(ring)
            j = np.arange(kk)
            tri = np.stack([np.zeros(kk, dtype=np.int64), 1 + j, 1 + (j + 1) % kk], 1)
            if sign < 0:
                tri = tri[:, ::-1]
            cuv = (Pc[:, [0, 2]] / (u_tile or v_tile))
            parts.append(Mesh(Pc, tri, cuv, crease=crease))
    out = merge(parts) if len(parts) > 1 else mesh
    out.crease = crease
    out = out.cleaned()
    return out.shade(crease) if shade else out


def lathe(profile, segments=32, sweep=360.0, start=0.0, shape: Callable | None = None, crease=50.0, tile=0.25,
          u_rep=None, round_profile=0.0, round_segments=2, close_axis=True, shape_v: Callable | None = None) -> Mesh:
    """Revolve a (r, y) profile around Y.  Seam starts at +Z and sweeps toward +X.
    shape(theta)->scale lets you make polygons/lobes (e.g. `polygon_shape(8)` for an octagon)."""
    prof = np.asarray(profile, dtype=np.float64)
    if round_profile > 0:
        prof = bevel_polyline(prof, round_profile, round_segments)
    full = abs(sweep - 360.0) < 1e-6
    K = segments if full else segments + 1
    th = np.radians(start) + np.linspace(0, math.radians(sweep), K, endpoint=not full)
    rho = np.ones(K) if shape is None else shape(th)
    r = prof[:, 0][:, None] * rho[None, :]
    if shape_v is not None:   # shape_v(theta (K,), v (R,) 0..1 along the profile) -> (R,K) radial scale
        v = np.linspace(0, 1, len(prof))
        r = r * np.asarray(shape_v(th, v))
    rings = np.stack([r * np.sin(th)[None, :], np.broadcast_to(prof[:, 1][:, None], r.shape), r * np.cos(th)[None, :]], axis=2)
    if full:
        return loft(rings, closed=True, crease=crease, v_tile=tile, u_rep=u_rep)
    return loft(rings, closed=False, crease=crease, v_tile=tile)


def polygon_shape(n, rotation_deg=0.0, roundness=0.0):
    """shape(theta) for `lathe`: regular n-gon with circumradius 1 (flat sides)."""
    def f(th):
        seg = TAU / n
        t = np.mod(th - math.radians(rotation_deg) + seg / 2, seg) - seg / 2
        rho = math.cos(math.pi / n) / np.cos(t)
        if roundness > 0:
            rho = rho * (1 - roundness) + roundness * math.cos(math.pi / n)
        return rho
    return f


def superformula_shape(lobes, depth=0.15, rotation_deg=0.0):
    return lambda th: 1.0 + depth * np.cos(lobes * (th - math.radians(rotation_deg)))


def _frames(path, up_hint):
    T = np.gradient(path, axis=0)
    T = normalize(T)
    up = normalize(np.asarray(up_hint, dtype=np.float64))
    n0 = up - np.dot(up, T[0]) * T[0]
    if np.linalg.norm(n0) < 1e-4:
        alt = np.array([1.0, 0, 0]) if abs(T[0][0]) < 0.9 else np.array([0, 0, 1.0])
        n0 = alt - np.dot(alt, T[0]) * T[0]
    N = np.zeros_like(T)
    N[0] = normalize(n0)
    for i in range(1, len(T)):
        n = N[i - 1] - np.dot(N[i - 1], T[i]) * T[i]
        if np.linalg.norm(n) < 1e-6:
            n = N[i - 1]
        N[i] = normalize(n)
    B = np.cross(T, N)
    return T, N, B


def tube(path, radii=0.02, sides=12, samples=6, cap="round", up=(0, 1, 0), twist=0.0, ellipse=(1.0, 1.0),
         section: Callable | None = None, smooth=True, crease=60.0, tile=0.25, cap_steps=2, radius_fn=None,
         closed=False, u_rep=None) -> Mesh:
    """Sweep a circle along a polyline/spline with varying radius.
    path: control points (n,3); radii: scalar, one per control point (smoothly interpolated) or callable(t)->r.
    cap: 'round' | 'flat' | None.  section(theta, t)->scale for fluted / non-round sections.
    twist: total roll in degrees along the path.  ellipse: (scale along frame-N, scale along frame-B)."""
    ctrl = np.asarray(path, dtype=np.float64)
    if smooth and len(ctrl) > 2:
        pts = spline(ctrl, samples, closed=closed)
    elif len(ctrl) == 2:
        pts = np.linspace(ctrl[0], ctrl[1], max(2, samples + 1))
    else:
        pts = ctrl
    if closed:
        pts = np.concatenate([pts, pts[:1]])
    seglen = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    t = np.concatenate([[0], np.cumsum(seglen)])
    tn = t / max(t[-1], 1e-9)
    if callable(radii):
        r = np.array([radii(x) for x in tn], dtype=np.float64)
    elif np.ndim(radii) == 0:
        r = np.full(len(pts), float(radii))
    else:
        rc = np.asarray(radii, dtype=np.float64)
        ctrl_t = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(ctrl, axis=0), axis=1))])
        ctrl_t = ctrl_t / max(ctrl_t[-1], 1e-9)
        r = np.interp(tn, ctrl_t, rc)
        if len(rc) > 2 and smooth:  # soften piecewise-linear radius
            pad = np.pad(r, 2, mode="edge")
            r = np.convolve(pad, np.ones(5) / 5, mode="valid")
    if radius_fn is not None:
        r = r * np.array([radius_fn(x) for x in tn])
    T, Nf, Bf = _frames(pts, up)
    th = np.linspace(0, TAU, sides, endpoint=False)

    def ring_points(c, Nv, Bv, rad, tt, roll):
        cr, sr = math.cos(roll), math.sin(roll)
        Nr, Br = Nv * cr + Bv * sr, -Nv * sr + Bv * cr
        sc = np.ones(sides) if section is None else np.asarray(section(th, tt), dtype=np.float64)
        a = np.cos(th) * sc * ellipse[0] * rad
        b = np.sin(th) * sc * ellipse[1] * rad
        return c + a[:, None] * Nr + b[:, None] * Br

    rounded = cap == "round" and not closed
    all_rings = []
    if rounded:
        first = pts[0] - T[0] * r[0]
        all_rings.append(np.repeat(first[None], sides, 0))
        for s in range(cap_steps, 0, -1):
            phi = (math.pi / 2) * s / (cap_steps + 1)
            all_rings.append(ring_points(pts[0] - T[0] * math.sin(phi) * r[0], Nf[0], Bf[0], math.cos(phi) * r[0], 0.0, 0.0))
    for i in range(len(pts)):
        all_rings.append(ring_points(pts[i], Nf[i], Bf[i], r[i], tn[i], math.radians(twist) * tn[i]))
    if rounded:
        for s in range(1, cap_steps + 1):
            phi = (math.pi / 2) * s / (cap_steps + 1)
            all_rings.append(ring_points(pts[-1] + T[-1] * math.sin(phi) * r[-1], Nf[-1], Bf[-1], math.cos(phi) * r[-1],
                                         1.0, math.radians(twist)))
        last = pts[-1] + T[-1] * r[-1]
        all_rings.append(np.repeat(last[None], sides, 0))
    rings = np.stack(all_rings)
    flat = cap == "flat" and not closed
    return loft(rings, closed=True, cap_start=flat, cap_end=flat, crease=crease, v_tile=tile, u_rep=u_rep)


def extrude(poly, depth, bevel=0.0, bevel_segments=2, z_center=0.0, tile=0.25, crease=40.0, caps=True) -> Mesh:
    """Extrude a CCW polygon (x, y) along Z, centred on z_center, with a rounded bevel of size `bevel`.
    Front (+Z) face is the visible one."""
    poly = np.asarray(poly, dtype=np.float64)
    if polygon_area(poly) < 0:
        poly = poly[::-1]
    h = depth / 2.0
    b = min(bevel, depth * 0.499)
    ring_defs = []  # (offset, z) bottom -> top
    if b > 1e-9:
        for k in range(bevel_segments + 1):
            phi = (math.pi / 2) * k / bevel_segments
            ring_defs.append((-b + b * math.sin(phi), -(h - b + b * math.cos(phi))))
        for k in range(bevel_segments + 1):
            phi = (math.pi / 2) * (1 - k / bevel_segments)
            ring_defs.append((-b + b * math.sin(phi), (h - b + b * math.cos(phi))))
    else:
        ring_defs = [(0.0, -h), (0.0, h)]
    rings = np.stack([np.column_stack([offset_polygon(poly, o), np.full(len(poly), z + z_center)]) for o, z in ring_defs])
    parts = [loft(rings, closed=True, crease=crease, v_tile=tile, shade=False)]
    if caps:
        inner = rings[0][:, :2]
        tris = triangulate_polygon(inner)
        parts.append(Mesh(np.column_stack([inner, np.full(len(inner), h + z_center)]), tris, inner / tile))
        parts.append(Mesh(np.column_stack([inner, np.full(len(inner), -h + z_center)]), tris[:, ::-1], inner / tile))
    return merge(parts).shade(crease)


def sphere(radius=0.5, rings=12, segments=24, crease=80.0) -> Mesh:
    a = np.linspace(-math.pi / 2, math.pi / 2, rings + 1)
    prof = np.column_stack([np.cos(a) * radius, np.sin(a) * radius])
    prof[0, 0] = prof[-1, 0] = 0.0
    return lathe(prof, segments, crease=crease)


def ellipsoid(radii=(0.5, 0.5, 0.5), rings=12, segments=24, crease=80.0) -> Mesh:
    return sphere(1.0, rings, segments, crease).scaled(*radii)


def superellipsoid(radii=(0.5, 0.5, 0.5), e_lat=0.4, e_lon=0.4, rings=14, segments=28, crease=80.0) -> Mesh:
    """Rounded blocky blobs: e=1 ellipsoid, e->0 box.  Good for pauldrons, helmets, torsos."""
    v = np.linspace(-math.pi / 2, math.pi / 2, rings + 1)
    u = np.linspace(0, TAU, segments, endpoint=False)

    def sgnpow(x, p):
        return np.sign(x) * np.abs(x) ** p
    cv, sv = sgnpow(np.cos(v), e_lat), sgnpow(np.sin(v), e_lat)
    cu, su = sgnpow(np.cos(u), e_lon), sgnpow(np.sin(u), e_lon)
    X = np.outer(cv, su) * radii[0]
    Z = np.outer(cv, cu) * radii[2]
    Y = np.broadcast_to(sv[:, None], X.shape) * radii[1]
    X[0] = X[-1] = 0
    Z[0] = Z[-1] = 0
    rings_a = np.stack([X, Y, Z], axis=2)
    return loft(rings_a, closed=True, crease=crease)


def rounded_box(size=(1, 1, 1), radius=0.05, segments=2, crease=40.0, tile=0.25, uv=True, inner=(0, 0, 0)) -> Mesh:
    """Box with rounded edges (cube-sphere construction). `segments` = cells across each rounded corner."""
    half = np.array([float(s) / 2 for s in size])
    r = min(radius, *half) * 0.999
    coords = []
    for h in half:
        k = len(coords)
        mid = np.linspace(-h + r, h - r, inner[k] + 2)[1:-1] if inner[k] > 0 else np.zeros(0)
        coords.append(np.concatenate([np.linspace(-h, -h + r, segments + 1), mid, np.linspace(h - r, h, segments + 1)]))
    Ps, Fs = [], []
    base = 0
    for ax in range(3):
        for sgn in (-1, 1):
            u_ax, v_ax = [i for i in range(3) if i != ax]
            U, V = np.meshgrid(coords[u_ax], coords[v_ax], indexing="ij")
            p = np.zeros(U.shape + (3,))
            p[..., ax] = sgn * half[ax]
            p[..., u_ax], p[..., v_ax] = U, V
            p = p.reshape(-1, 3)
            inner = np.clip(p, -(half - r), (half - r))
            d = p - inner
            L = np.linalg.norm(d, axis=1, keepdims=True)
            q = inner + np.where(L > 1e-12, d / np.maximum(L, 1e-12), 0) * r
            idx = np.arange(U.shape[0] * U.shape[1]).reshape(U.shape) + base
            a_, b_, c_, d_ = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
            tri = np.concatenate([np.stack([a_, b_, c_], -1).reshape(-1, 3), np.stack([a_, c_, d_], -1).reshape(-1, 3)])
            nn = np.cross(q[tri[:, 1] - base] - q[tri[:, 0] - base], q[tri[:, 2] - base] - q[tri[:, 0] - base])
            out_dir = np.zeros(3)
            out_dir[ax] = sgn
            if np.mean(nn @ out_dir) < 0:
                tri = tri[:, ::-1]
            Ps.append(q)
            Fs.append(tri)
            base += len(q)
    m = Mesh(np.concatenate(Ps), np.concatenate(Fs), crease=crease).cleaned().shade(crease)
    return m.uv_box(tile) if uv else m


def box(size=(1, 1, 1), tile=0.25) -> Mesh:
    return rounded_box(size, radius=1e-4, segments=1, crease=30, tile=tile)


def torus(R=0.5, r=0.05, segments=32, sides=12, crease=60.0, arc=360.0, ellipse=(1.0, 1.0)) -> Mesh:
    """Ring of radius R, tube radius r, lying in the XZ plane (axis Y)."""
    pts = [(R * math.sin(a), 0.0, R * math.cos(a)) for a in np.linspace(0, math.radians(arc), segments + 1)]
    pts = np.array(pts)
    closed = abs(arc - 360.0) < 1e-6
    if closed:
        pts = pts[:-1]
    return tube(pts, r, sides=sides, samples=1, cap=None if closed else "round", smooth=False, closed=closed,
                crease=crease, ellipse=ellipse, up=(0, 1, 0))


def cylinder(radius=0.1, height=0.2, segments=24, taper=1.0, bevel=0.0, bevel_segments=2, crease=40.0, y0=0.0) -> Mesh:
    """Capped cylinder standing on y0 (optionally tapered / bevelled)."""
    r0, r1 = radius, radius * taper
    if bevel > 0:
        b = min(bevel, radius * 0.9, height * 0.45)
        prof = [(0, y0), (r0 - b, y0), (r0, y0 + b), (r1, y0 + height - b), (r1 - b, y0 + height), (0, y0 + height)]
        prof = bevel_polyline(np.array(prof), b * 0.9, bevel_segments, sharp=(0, len(prof) - 1))
    else:
        prof = np.array([(0, y0), (r0, y0), (r1, y0 + height), (0, y0 + height)])
    return lathe(prof, segments, crease=crease)


def cone(radius=0.1, height=0.2, segments=24, y0=0.0, crease=60.0) -> Mesh:
    return lathe([(0, y0), (radius, y0), (0, y0 + height)], segments, crease=crease)


def disc_ring(r_in, r_out, thickness, segments=48, bevel=0.0, y0=0.0, crease=40.0) -> Mesh:
    """Flat washer (annulus) with optional bevel."""
    b = min(bevel, thickness * 0.45, (r_out - r_in) * 0.45)
    prof = [(r_in, y0), (r_out, y0), (r_out, y0 + thickness), (r_in, y0 + thickness)]
    prof = np.array(prof)
    if b > 0:
        prof = bevel_polyline(prof, b, 2, closed=True)
        return lathe(np.concatenate([prof, prof[:1]]), segments, crease=crease)
    return lathe(np.concatenate([prof, prof[:1]]), segments, crease=crease)


def capsule(a, b, radius, sides=12, rings=4, crease=80.0) -> Mesh:
    return tube([a, b], radius, sides=sides, samples=1, cap="round", cap_steps=rings, smooth=False, crease=crease)


def blade(length, width, thickness, tip=0.25, taper=0.72, fuller=0.0, rows=5, crease=35.0) -> Mesh:
    """Double-edged leaf blade along +Y from y=0 to y=length; width along X, thickness along Z (front = +Z).
    fuller = groove depth on both faces (0 = none).  tip = fraction of the length that tapers to the point."""
    ys = np.linspace(0, 1, rows * 3 + 1)
    w = taper + (1 - taper) * smoothstep(0.0, 0.38, ys)
    s_tip = np.clip((ys - (1 - tip)) / tip, 0, 1)
    w = w * np.cos(s_tip * math.pi / 2) ** 0.65
    th = (1 - 0.45 * ys) * (1 - s_tip ** 2)
    hw = w * width / 2
    tz = th * thickness / 2
    fa = smoothstep(0.04, 0.12, ys) * (1 - smoothstep(0.78, 0.92, ys)) * fuller
    sec = [(-0.3, 1, 0), (0.0, 1, -1), (0.3, 1, 0), (0.62, 0.52, 0), (1.0, 0.0, 0), (0.62, -0.52, 0), (0.3, -1, 0),
           (0.0, -1, 1), (-0.3, -1, 0), (-0.62, -0.52, 0), (-1.0, 0.0, 0), (-0.62, 0.52, 0)]
    rings = []
    for i, y in enumerate(ys):
        ring = []
        for sx, sz, fg in sec:
            z = sz * tz[i] + (fg * fa[i] * np.sign(sz))
            ring.append((sx * hw[i], y * length, z))
        rings.append(ring)
    return loft(np.array(rings), closed=True, cap_start=True, crease=crease, v_tile=0.2)


# ------------------------------------------------------------------ crystals
def crystal(radius=0.03, height=0.12, sides=6, tip=0.25, taper=0.85, skew=(0, 0), jitter=0.0, seed=0, crease=30.0) -> Mesh:
    """Hexagonal crystal shard standing on y=0 with a pointed (faceted) tip."""
    rng = np.random.default_rng(seed)
    th = np.linspace(0, TAU, sides, endpoint=False)
    rs = 1.0 + jitter * (rng.random(sides) - 0.5)
    body = height * (1 - tip)
    levels = [(0.0, radius * 0.9), (body * 0.15, radius), (body, radius * taper), (height, 0.0)]
    rings = []
    for i, (y, r) in enumerate(levels):
        f = y / height
        rings.append(np.stack([r * rs * np.sin(th) + skew[0] * f * height, np.full(sides, y), r * rs * np.cos(th) + skew[1] * f * height], 1))
    return loft(np.stack(rings), closed=True, cap_start=True, crease=crease, v_tile=0.1)


def crystal_cluster(count=7, spread=0.06, height=(0.08, 0.2), radius=(0.012, 0.03), tilt=22.0, seed=0, sides=6,
                    up=(0, 1, 0)) -> Mesh:
    """A clump of shards leaning outward from the origin, tallest in the middle."""
    rng = np.random.default_rng(seed)
    parts = []
    for i in range(count):
        a = rng.random() * TAU
        d = spread * (0.2 + 0.8 * rng.random()) * (0 if i == 0 else 1)
        h = height[0] + (height[1] - height[0]) * (1.0 if i == 0 else rng.random() ** 0.8) * (1.0 - 0.45 * d / max(spread, 1e-6))
        r = radius[0] + (radius[1] - radius[0]) * (1.0 if i == 0 else rng.random())
        c = crystal(r, h, sides=sides, tip=0.18 + 0.15 * rng.random(), jitter=0.2, seed=seed + i)
        tl = tilt * (0.3 if i == 0 else 0.4 + rng.random()) * (d / max(spread, 1e-6) + 0.2)
        c = c.rotated(0, rng.random() * 90, 0).rotated_axis([math.cos(a), 0, -math.sin(a)], tl)
        parts.append(c.translated(d * math.sin(a), 0, d * math.cos(a)))
    m = merge(parts)
    if tuple(up) != (0, 1, 0):
        m = m.transformed(np.block([[rot_between([0, 1, 0], up), np.zeros((3, 1))], [np.zeros((1, 3)), 1]]))
    return m


def cloth_panel(width, height, cols=14, rows=10, fold_amp=0.01, folds=6, sag=0.0, flare=0.0, curve=0.0, seed=0,
                bone_free=True, crease=80.0, hem_wave=0.0, thickness=0.0) -> Mesh:
    """A hanging cloth sheet in the XY plane (x across, y from top (0) down to -height), +Z is the outside.
    Vertical sine folds grow toward the hem; `flare` widens toward the bottom; `curve` wraps it around Y."""
    u = np.linspace(-0.5, 0.5, cols + 1)
    v = np.linspace(0, 1, rows + 1)
    U, V = np.meshgrid(u, v, indexing="ij")
    rng = np.random.default_rng(seed)
    ph = rng.random(3) * TAU
    f = (np.sin(U * folds * math.pi * 2 + ph[0]) * 0.6 + np.sin(U * folds * 1.9 * math.pi * 2 + ph[1]) * 0.3 +
         np.sin(U * folds * 3.1 * math.pi * 2 + ph[2]) * 0.1)
    Z = f * fold_amp * (0.25 + 0.75 * V)
    X = U * width * (1 + flare * V)
    Y = -V * height + sag * np.sin(V * math.pi) * 0.0
    Y = Y - hem_wave * np.sin(U * folds * math.pi * 2 + ph[0]) * V ** 3
    if curve:
        ang = X / max(width, 1e-6) * math.radians(curve)
        rad = width / math.radians(curve) if curve else 1e9
        X, Z2 = rad * np.sin(ang), rad * (1 - np.cos(ang))
        Z = Z - Z2
    P = np.stack([X, Y, Z], axis=2)  # (cols+1, rows+1, 3)
    # ring order: rows go downward; columns along +x -> normal = t_col x t_ring = x x (-y) = -z, so reverse rows
    m = loft(P[:, ::-1], closed=False, crease=crease, v_tile=0.25, u_tile=0.25)
    m = m.flipped()
    if thickness > 0:
        m = merge([m, m.flipped().translated(0, 0, -thickness)])
    return m


# ------------------------------------------------------------------ quadric decimation
def _q_plane(p0, p1, p2):
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    if ln < 1e-14:
        return None
    a, b, c = nx / ln, ny / ln, nz / ln
    d = -(a * p0[0] + b * p0[1] + c * p0[2])
    w = ln * 0.5
    return [w * a * a, w * a * b, w * a * c, w * a * d, w * b * b, w * b * c, w * b * d, w * c * c, w * c * d, w * d * d]


def _q_err(q, p):
    x, y, z = p
    return (q[0] * x * x + 2 * q[1] * x * y + 2 * q[2] * x * z + 2 * q[3] * x + q[4] * y * y + 2 * q[5] * y * z +
            2 * q[6] * y + q[7] * z * z + 2 * q[8] * z + q[9])


def decimate(mesh: Mesh, target_tris: int, preserve_borders=True, crease=None) -> Mesh:
    """Quadric edge-collapse down to ~target_tris triangles.
    Works on position-welded topology; UV / colour / extra attributes stay attached to face corners so seams survive.
    Collapsed vertices land on one endpoint or the midpoint (keeps texture coordinates sane)."""
    if len(mesh.F) <= target_tris:
        return mesh
    m = mesh.cleaned()
    gid = m.weld_ids()
    ng = int(gid.max()) + 1
    Pw0 = np.zeros((ng, 3))
    Pw0[gid] = m.P
    Pw = [tuple(p) for p in Pw0.tolist()]
    forig = m.F.tolist()
    fw = [[int(gid[a]), int(gid[b]), int(gid[c])] for a, b, c in m.F]
    nf = len(fw)
    alive = [not (t[0] == t[1] or t[1] == t[2] or t[0] == t[2]) for t in fw]
    vfaces = [set() for _ in range(ng)]
    edge_faces: dict = {}
    Q = [[0.0] * 10 for _ in range(ng)]
    for i in range(nf):
        if not alive[i]:
            continue
        a, b, c = fw[i]
        q = _q_plane(Pw[a], Pw[b], Pw[c])
        for v in (a, b, c):
            vfaces[v].add(i)
            if q is not None:
                Qv = Q[v]
                for k in range(10):
                    Qv[k] += q[k]
        for u, v in ((a, b), (b, c), (c, a)):
            edge_faces.setdefault((min(u, v), max(u, v)), []).append(i)
    if preserve_borders:
        for (u, v), fl in edge_faces.items():
            if len(fl) == 1:
                a, b, c = fw[fl[0]]
                pa, pb, pc = (np.array(Pw[t]) for t in (a, b, c))
                fn = np.cross(pb - pa, pc - pa)
                e = np.array(Pw[v]) - np.array(Pw[u])
                bn = np.cross(e, fn)
                ln = np.linalg.norm(bn)
                if ln > 1e-14:
                    bn /= ln
                    d = -float(np.dot(bn, Pw[u]))
                    w = float(np.dot(e, e)) * 4.0
                    qq = [w * bn[0] * bn[0], w * bn[0] * bn[1], w * bn[0] * bn[2], w * bn[0] * d, w * bn[1] * bn[1],
                          w * bn[1] * bn[2], w * bn[1] * d, w * bn[2] * bn[2], w * bn[2] * d, w * d * d]
                    for t in (u, v):
                        for k in range(10):
                            Q[t][k] += qq[k]
    members = [[] for _ in range(ng)]
    for v in range(len(m.P)):
        members[int(gid[v])].append(v)
    nbr = [set() for _ in range(ng)]
    for (u, v) in edge_faces:
        nbr[u].add(v)
        nbr[v].add(u)
    version = [0] * ng
    removed = [False] * ng

    def best(u, v):
        qs = [Q[u][k] + Q[v][k] for k in range(10)]
        pu, pv = Pw[u], Pw[v]
        mid = ((pu[0] + pv[0]) * .5, (pu[1] + pv[1]) * .5, (pu[2] + pv[2]) * .5)
        cands = (pu, pv, mid)
        errs = [_q_err(qs, c) for c in cands]
        k = errs.index(min(errs))
        d = math.dist(pu, pv)
        return errs[k] + 1e-12 * d, cands[k]

    def normal_dot(old, new):
        ux, uy, uz = old[1][0] - old[0][0], old[1][1] - old[0][1], old[1][2] - old[0][2]
        vx, vy, vz = old[2][0] - old[0][0], old[2][1] - old[0][1], old[2][2] - old[0][2]
        n1 = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        ux, uy, uz = new[1][0] - new[0][0], new[1][1] - new[0][1], new[1][2] - new[0][2]
        vx, vy, vz = new[2][0] - new[0][0], new[2][1] - new[0][1], new[2][2] - new[0][2]
        n2 = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        l1 = math.sqrt(n1[0] ** 2 + n1[1] ** 2 + n1[2] ** 2)
        l2 = math.sqrt(n2[0] ** 2 + n2[1] ** 2 + n2[2] ** 2)
        if l1 < 1e-14:
            return 1.0
        if l2 < 1e-14:
            return -1.0
        return (n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2]) / (l1 * l2)

    heap = []
    for (u, v) in edge_faces:
        c, _ = best(u, v)
        heap.append((c, u, v, 0, 0))
    heapq.heapify(heap)
    cur = sum(alive)
    while cur > target_tris and heap:
        c, u, v, vu, vv = heapq.heappop(heap)
        if removed[u] or removed[v] or version[u] != vu or version[v] != vv:
            continue
        shared = vfaces[u] & vfaces[v]
        if len(nbr[u] & nbr[v]) > len(shared):
            continue
        cost, newp = best(u, v)
        bad = False
        for w_ in (u, v):
            for fi in vfaces[w_]:
                if fi in shared:
                    continue
                tri = fw[fi]
                old = [Pw[t] for t in tri]
                new = [newp if t == w_ else Pw[t] for t in tri]
                if normal_dot(old, new) < 0.4:
                    bad = True
                    break
            if bad:
                break
        if bad:
            continue
        Pw[u] = newp
        for k in range(10):
            Q[u][k] += Q[v][k]
        removed[v] = True
        version[u] += 1
        for fi in list(vfaces[v]):
            if fi in shared:
                alive[fi] = False
                cur -= 1
                for t in fw[fi]:
                    if t != v:
                        vfaces[t].discard(fi)
            else:
                fw[fi] = [u if t == v else t for t in fw[fi]]
                vfaces[u].add(fi)
        vfaces[v] = set()
        members[u].extend(members[v])
        nbr[u] |= nbr[v]
        nbr[u].discard(u)
        nbr[u].discard(v)
        for w_ in nbr[v]:
            nbr[w_].discard(v)
            if w_ != u:
                nbr[w_].add(u)
        nbr[v] = set()
        for w_ in nbr[u]:
            cc, _ = best(u, w_)
            a_, b_ = min(u, w_), max(u, w_)
            heapq.heappush(heap, (cc, a_, b_, version[a_], version[b_]))
    keep = [i for i in range(nf) if alive[i]]
    used: dict = {}
    P_out, src = [], []
    newF = []
    for fi in keep:
        tri = []
        for corner in range(3):
            orig, w_ = forig[fi][corner], fw[fi][corner]
            key = (orig, w_)
            if key not in used:
                used[key] = len(P_out)
                P_out.append(Pw[w_])
                src.append(orig)
            tri.append(used[key])
        newF.append(tri)
    src = np.array(src, dtype=np.int64)
    out = Mesh(np.array(P_out), np.array(newF), m.UV[src], None, None if m.C is None else m.C[src],
               {k: v[src] for k, v in m.A.items()}, m.crease if crease is None else crease)
    out = out.cleaned()
    return out.shade(out.crease)


def weld_vertices(mesh: Mesh) -> Mesh:
    return mesh.compact()


# ------------------------------------------------------------------ extra shaping helpers
def warp(mesh: Mesh, fn: Callable[[np.ndarray], np.ndarray], crease=None) -> Mesh:
    """Move every vertex through fn(P (n,3)) -> P' and reshade."""
    out = mesh.copy()
    out.P = np.asarray(fn(mesh.P.copy()), dtype=np.float64)
    out.N = None
    return out.shade(crease if crease is not None else mesh.crease)


def bend(mesh: Mesh, arc_axis="x", normal_axis="z", radius=0.1, crease=None) -> Mesh:
    """Wrap a flat plate around a cylinder: coordinate `arc_axis` becomes arc length on a cylinder of `radius`
    whose axis is the third axis; `normal_axis` is the plate thickness direction (+ = outside)."""
    a, n = "xyz".index(arc_axis), "xyz".index(normal_axis)

    def f(P):
        ang = P[:, a] / radius
        rr = radius + P[:, n]
        P2 = P.copy()
        P2[:, a] = rr * np.sin(ang)
        P2[:, n] = rr * np.cos(ang) - radius
        return P2
    return warp(mesh, f, crease)


def extrude_plane(poly, depth, plane="XY", **kw) -> Mesh:
    """`extrude` for polygons in another plane. plane='YZ': points are (y, z), thickness along X;
    plane='XZ': points are (x, z), thickness along Y (up).  Result is centred on the plane's normal axis."""
    poly = np.asarray(poly, dtype=np.float64)
    if plane == "XY":
        return extrude(poly, depth, **kw)
    if plane == "YZ":
        m = extrude(np.column_stack([-poly[:, 1], poly[:, 0]]), depth, **kw)     # local x=-z, local y=y, thickness z
        return m.rotated(0, 90, 0)                                                # local z -> +x, local x -> -z
    if plane == "XZ":
        m = extrude(np.column_stack([poly[:, 0], -poly[:, 1]]), depth, **kw)      # local (x, -z)
        return m.rotated(-90, 0, 0)                                               # local y -> -z... then z-> +y
    raise ValueError(plane)


def dome(radius=0.01, height=None, segments=8, rings=2, crease=70.0) -> Mesh:
    """Rivet / stud: half ellipsoid standing on y=0."""
    h = radius if height is None else height
    a = np.linspace(0, math.pi / 2, rings + 1)
    prof = np.column_stack([np.cos(a) * radius, np.sin(a) * h])
    prof = np.vstack([[0.0, 0.0], [radius, 0.0], prof[1:]])
    prof[-1, 0] = 0.0
    return lathe(prof, segments, crease=crease)


def teardrop(length=0.04, width=0.02, n=14, curl=0.0) -> np.ndarray:
    """2D flame/teardrop outline (CCW), base at y=0, tip at y=length."""
    t = np.linspace(0, 1, n, endpoint=False)
    ang = t * TAU
    # widest near the base; pointed tip with optional sideways curl
    x = np.sin(ang) * width / 2 * (1 - 0.0)
    y = (1 - np.cos(ang)) / 2 * length
    prof = np.sin(ang / 2) ** 1.0
    x = -np.sin(ang) * (width / 2) * np.sin(ang / 2) ** 0.6 * 1.0
    pts = np.column_stack([x + curl * (y / length) ** 2, y])
    return pts[::-1] if polygon_area(pts) < 0 else pts


def rect_poly(w, h, r=0.0, seg=2):
    pts = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    return bevel_polyline(pts, r, seg, closed=True) if r > 0 else pts


def plate(w, h, t, radius=0.004, bend_r=None, inner_x=None, inner_y=1, taper=None, crease=45.0, curve_y=None, drop_back=False) -> Mesh:
    """Bevelled rectangular armour plate (front = +Z, width w along X, height h along Y, thickness t).
    bend_r wraps it around a vertical cylinder (convex toward +Z); curve_y wraps it around a horizontal one.
    taper(y_norm -1..1) -> x scale narrows/widens the plate vertically (pauldron lames, tassets)."""
    ix = inner_x if inner_x is not None else (max(1, int(w / 0.025)) if bend_r else 0)
    iy = max(inner_y, int(h / 0.03)) if curve_y else inner_y
    m = rounded_box((w, h, t), radius, 1, crease, uv=False, inner=(ix, iy if (bend_r or curve_y or taper) else 0, 0))
    if drop_back:   # hidden back side (plate sits against something): cull faces pointing away from +Z
        keep = m.face_normals()[:, 2] > -0.35
        m = m.copy()
        m.F = m.F[keep]
        m = m.cleaned().shade(crease)
    if taper is not None:
        m = warp(m, lambda P: np.column_stack([P[:, 0] * taper(P[:, 1] / (h / 2)), P[:, 1], P[:, 2]]), crease)
    if bend_r:
        m = bend(m, "x", "z", bend_r, crease)
    if curve_y:
        m = bend(m, "y", "z", curve_y, crease)
    return m.uv_box(0.25)
