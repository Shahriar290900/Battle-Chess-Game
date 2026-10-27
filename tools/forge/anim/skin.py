"""skin.py - automatic smooth skin weights computed from the REST-POSE vertex positions (so LOD0, LOD1 and any decimated
mesh get consistent weights) plus a ring-dense limb tube builder.

    Skin.rigid("chest")                                   100 % to one bone (armour plates, weapons, crowns, pedestal)
    Skin.chain(["thigh_L","shin_L","foot_L"], pre="body", tip=toe_pt, zone=0.35)
        limbs / torso: each vertex is projected on the bone polyline, and weight slides between neighbouring bones with a
        smoothstep over +-zone * (shorter adjacent bone) around each joint (30-40 % blend = no candy-wrapper pinch)
    Skin.nearest([("body","body","spine"), ("thigh_L","hip_L","knee_L"), ...], tau=0.03)
        skirts / cloth / mount barrels: softmax of the distance to each bone SEGMENT (a segment end is a bone name or a point)
    Skin.gradient(skin_a, skin_b, axis=1, v0=0.6, v1=0.5)
        cross-fade between two skins along a world axis

Every skin returns <= 4 influences per vertex, normalised.  Pass it to `Piece.add(name, mesh, mat, bone=None, skin=...)`.
"""
from __future__ import annotations

import numpy as np

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import geom as g   # noqa: E402


def _ss(e0, e1, x):
    t = np.clip((x - e0) / max(e1 - e0, 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def _top4(Wd):
    """dense (n, nb) -> J (n,4) int, W (n,4) normalised."""
    n, nb = Wd.shape
    k = min(4, nb)
    idx = np.argsort(-Wd, axis=1)[:, :k]
    w = np.take_along_axis(Wd, idx, 1)
    w = w / np.maximum(w.sum(1, keepdims=True), 1e-12)
    J = np.zeros((n, 4), dtype=np.int64)
    W = np.zeros((n, 4))
    J[:, :k], W[:, :k] = idx, w
    J[W == 0] = idx[:, 0:1].repeat(4, 1)[W == 0]
    return J, W


def _pt(rig, p):
    if isinstance(p, str):
        return rig.pos(p)
    return np.asarray(p, dtype=np.float64)


class Skin:
    def primary(self, rig):
        raise NotImplementedError

    def dense(self, P, rig):
        raise NotImplementedError

    def weights(self, P, rig):
        return _top4(self.dense(np.asarray(P, dtype=np.float64), rig))

    # ---- constructors
    @staticmethod
    def rigid(bone):
        return Rigid(bone)

    @staticmethod
    def chain(bones, **kw):
        return Chain(bones, **kw)

    @staticmethod
    def nearest(segs, **kw):
        return Nearest(segs, **kw)

    @staticmethod
    def gradient(a, b, axis=1, v0=0.0, v1=1.0):
        return Gradient(a, b, axis, v0, v1)


class Rigid(Skin):
    def __init__(self, bone):
        self.bone = bone

    def primary(self, rig):
        return rig.resolve(self.bone)

    def dense(self, P, rig):
        W = np.zeros((len(P), len(rig.order)))
        W[:, rig.index(self.bone)] = 1.0
        return W


class Chain(Skin):
    def __init__(self, bones, tip=None, pre=None, zone=0.35, zones=None, min_half=0.0, seg_pts=None):
        self.bones, self.tip, self.pre = list(bones), tip, pre
        self.zone, self.zones, self.min_half = zone, zones or {}, min_half
        self.seg_pts = seg_pts

    def primary(self, rig):
        return rig.resolve(self.bones[0])

    def _joints(self, rig):
        Q = [rig.pos(b) for b in self.bones]
        if self.tip is not None:
            tip = _pt(rig, self.tip)
        else:
            kids = [n for n, b in rig.bones.items() if b.parent == rig.resolve(self.bones[-1])]
            tip = rig.pos(kids[0]) if kids else (Q[-1] + (Q[-1] - Q[-2] if len(Q) > 1 else np.array([0, -0.05, 0])))
        return np.array(Q + [tip])

    def dense(self, P, rig):
        Q = self._joints(rig)
        m = len(self.bones)
        seg = Q[1:] - Q[:-1]
        L = np.linalg.norm(seg, axis=1)
        cum = np.concatenate([[0], np.cumsum(L)])
        n = len(P)
        best_d = np.full(n, np.inf)
        best_s = np.zeros(n)
        for j in range(m):
            a, d = Q[j], seg[j]
            t = ((P - a) @ d) / max(L[j] ** 2, 1e-12)
            tc = np.clip(t, 0, 1)
            if m == 1:
                tc = t
            elif j == 0:
                tc = np.minimum(t, 1.0)             # first segment projects below its joint (for `pre`)
            elif j == m - 1:
                tc = np.maximum(t, 0.0)             # last segment projects beyond the tip
            sel = np.linalg.norm(P - (a + np.clip(t, 0, 1)[:, None] * d), axis=1)
            better = sel < best_d - 1e-12
            best_d = np.where(better, sel, best_d)
            best_s = np.where(better, cum[j] + tc * L[j], best_s)
        # joint blend zones
        u = np.ones((n, m + 1))
        u[:, m] = 0.0
        for k in range(m):
            if k == 0 and self.pre is None:
                continue
            Lm = L[k] if k == 0 else min(L[k - 1], L[k])
            f = self.zones.get(self.bones[k], self.zone)
            half = max(f * Lm, min(self.min_half, 0.5 * Lm))
            half = min(half, 0.5 * Lm if k else 0.5 * L[0])
            u[:, k] = _ss(cum[k] - half, cum[k] + half, best_s)
        Wd = np.zeros((n, len(rig.order)))
        for i, b in enumerate(self.bones):
            Wd[:, rig.index(b)] += np.clip(u[:, i] - u[:, i + 1], 0, None)
        if self.pre is not None:
            Wd[:, rig.index(self.pre)] += np.clip(1 - u[:, 0], 0, None)
        return Wd


class Nearest(Skin):
    def __init__(self, segs, tau=0.03, bias=None):
        """segs: [(bone, p0, p1)] with p0/p1 = bone names (joint position) or points.  bias: {bone: multiplier}."""
        self.segs, self.tau, self.bias = list(segs), tau, bias or {}

    def primary(self, rig):
        return rig.resolve(self.segs[0][0])

    def dense(self, P, rig):
        n = len(P)
        D = np.zeros((n, len(self.segs)))
        for i, (b, p0, p1) in enumerate(self.segs):
            a, c = _pt(rig, p0), _pt(rig, p1)
            d = c - a
            t = np.clip(((P - a) @ d) / max(float(d @ d), 1e-12), 0, 1)
            D[:, i] = np.linalg.norm(P - (a + t[:, None] * d), axis=1)
        dmin = D.min(1, keepdims=True)
        E = np.exp(-(D - dmin) / self.tau)
        for i, (b, _, _) in enumerate(self.segs):
            E[:, i] *= self.bias.get(b, 1.0)
        Wd = np.zeros((n, len(rig.order)))
        for i, (b, _, _) in enumerate(self.segs):
            Wd[:, rig.index(b)] += E[:, i]
        return Wd / Wd.sum(1, keepdims=True)


class Gradient(Skin):
    def __init__(self, a, b, axis, v0, v1):
        self.a, self.b, self.axis, self.v0, self.v1 = a, b, axis, v0, v1

    def primary(self, rig):
        return self.a.primary(rig)

    def dense(self, P, rig):
        t = _ss(self.v0, self.v1, P[:, self.axis])[:, None]      # works for v0 > v1 too (np.clip on reversed ramp)
        if self.v0 > self.v1:
            t = np.clip((P[:, self.axis] - self.v0) / (self.v1 - self.v0), 0, 1)[:, None]
            t = t * t * (3 - 2 * t)
        return self.a.dense(P, rig) * (1 - t) + self.b.dense(P, rig) * t


# ------------------------------------------------------------------ geometry helper
def limb_tube(ctrl, radii, joints=(), spacing=0.03, joint_spacing=0.013, joint_zone=0.045, sides=8, cap=None, up=(0, 0, 1), **kw):
    """Tube through `ctrl` (spline) whose rings are dense around the world-space `joints` (knee/elbow...), so smooth skin
    has geometry to bend.  radii: one per ctrl point.  Cost = sides * 2 * rings."""
    ctrl = np.asarray(ctrl, dtype=np.float64)
    poly = g.spline(ctrl, 10) if len(ctrl) > 2 else np.linspace(ctrl[0], ctrl[1], 24)
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    jpos = []
    for j in joints:
        d = np.linalg.norm(poly - np.asarray(j), axis=1)
        jpos.append(cum[int(np.argmin(d))])
    s, out = 0.0, [0.0]
    while s < total - 1e-6:
        near = min([abs(s - jp) for jp in jpos], default=1e9)
        step = joint_spacing if near < joint_zone else spacing
        s = min(total, s + step)
        out.append(s)
    out = np.array(out)
    pts = np.stack([np.interp(out, cum, poly[:, i]) for i in range(3)], 1)
    cc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(ctrl, axis=0), axis=1))])
    cc = cc / cc[-1]
    # radii: smooth interpolation over normalised arc length (PCHIP-like via cosine blend)
    tn = out / total
    r = np.interp(tn, cc, np.asarray(radii, dtype=np.float64))
    r = np.convolve(np.pad(r, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
    return g.tube(pts, r, sides=sides, smooth=False, cap=cap, up=up, **kw)
