"""Shared helpers for the Emberhold pieces (rook, bishop, queen, king, knight).  Not a piece itself (leading underscore).

Re-uses the approved pawn's pedestal / small helpers so every Emberhold plinth is geometrically identical."""
from __future__ import annotations

import importlib.util
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import geom as g                      # noqa: E402
from geom import TAU, merge, smoothstep  # noqa: E402

_spec = importlib.util.spec_from_file_location("emberhold_pawn_ref", os.path.join(HERE, "emberhold_pawn.py"))
_pawn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pawn)

pedestal_parts = _pawn.pedestal_parts
torus_axis = _pawn.torus_axis
ring_instances = _pawn.ring_instances
unit = _pawn.unit
mirror_x = _pawn.mirror_x


# ---- a calmer flame material: EH_Ember is x6 (right for a gem or rune, but a whole flame fan blooms to white)
import textures as T                  # noqa: E402


def _gen_flame(n, seed):
    ts = T.gen_ember(n, seed)
    ts.name = "EH_Flame"
    ts.emissive = ts.emissive * np.array([1.0, 0.66, 0.26])
    ts.emissive_strength = 2.4
    return ts


T.register(T.MaterialDef("EH_Flame", _gen_flame, 17))


def _gen_coal(n, seed):
    ts = T.gen_ember(n, seed)
    ts.name = "EH_Coal"
    ts.emissive = ts.emissive * np.array([1.0, 0.42, 0.10])
    ts.emissive_strength = 1.15
    ts.albedo = ts.albedo * 0.6
    return ts


T.register(T.MaterialDef("EH_Coal", _gen_coal, 33))


# ---- forward-kinematics helper: make a rig bone ride a point on another bone (e.g. the bishop's censer on the staff crook)
def _bone_world(rig, clip, bone, t):
    chain, b = [], bone
    while b:
        chain.append(b)
        b = rig.bones[b].parent
    M = np.eye(4)
    for b in reversed(chain):
        loc = rig.local(b).copy()
        tr = clip.tracks.get((b, "pos"))
        if tr:
            loc = loc + tr.eval(t, clip.duration, (0, 0, 0))
        rot = (0, 0, 0)
        tr = clip.tracks.get((b, "rot"))
        if tr:
            rot = tr.eval(t, clip.duration, (0, 0, 0))
        L = np.eye(4)
        L[:3, :3] = g.rot_matrix(*rot)
        L[:3, 3] = loc
        M = M @ L
    return M


def follow(clip, rig, follower, target, step=1 / 30):
    """Add `pos` keys to `follower` so that its pivot stays glued to the point of `target` it occupies at rest.
    Call after every other track of the clip is defined."""
    p_rest = np.append(rig.pos(follower), 1.0)
    Mt_rest = _bone_world(rig, Clip0, target, 0.0)
    inv_rest = np.linalg.inv(Mt_rest)
    parent = rig.bones[follower].parent
    rest_local = rig.local(follower)
    n = int(round(clip.duration / step))
    for i in range(n + 1):
        t = min(i * step, clip.duration)
        want = _bone_world(rig, clip, target, t) @ inv_rest @ p_rest
        Mp = _bone_world(rig, clip, parent, t)
        loc = (np.linalg.inv(Mp) @ want)[:3]
        clip.key(follower, "pos", t, tuple(loc - rest_local), "linear")


class _Empty:
    tracks: dict = {}
    duration = 1.0


Clip0 = _Empty()


# ---- generic "torso family": one set of ellipse curves so skin / plates / belts / strips always nest
class Body:
    """Y (ascending), RX, RZ, ZC arrays describe the torso cross-section ellipse at each height."""

    def __init__(self, Y, RX, RZ, ZC=None):
        self.Y, self.RX, self.RZ = np.asarray(Y, float), np.asarray(RX, float), np.asarray(RZ, float)
        self.ZC = np.zeros_like(self.Y) if ZC is None else np.asarray(ZC, float)

    def rx(self, y):
        return np.interp(y, self.Y, self.RX)

    def rz(self, y):
        return np.interp(y, self.Y, self.RZ)

    def zc(self, y):
        return np.interp(y, self.Y, self.ZC)

    def ring(self, y, grow=0.0, K=48, a0=0.0, a1=360.0, ridge=0.0, ridge_w=0.022, fold=0.0, ph=0.0, yoff=None, sx=1.0):
        full = abs(a1 - a0 - 360.0) < 1e-6
        th = np.radians(np.linspace(a0, a1, K, endpoint=not full))
        f = 1.0
        if fold:
            f = 1 + fold * (0.55 * np.cos(10 * th + 0.4 + ph) + 0.30 * np.cos(17 * th + 2.1 + ph) + 0.15 * np.cos(5 * th + ph))
        x = (self.rx(y) + grow) * f * np.sin(th) * sx
        z = (self.rz(y) + grow) * f * np.cos(th) + self.zc(y)
        if ridge:
            z = z + ridge * np.exp(-(x / ridge_w) ** 2) * (np.cos(th) > 0)
        yy = np.full(len(th), y) if yoff is None else y + yoff(th)
        return np.stack([x, yy, z], 1)

    def loft(self, ys, grows, K=48, a0=0.0, a1=360.0, crease=55.0, **kw):
        full = abs(a1 - a0 - 360.0) < 1e-6
        gr = np.broadcast_to(np.asarray(grows, float), (len(ys),))
        rings = np.stack([self.ring(y, g_, K, a0, a1, **kw) for y, g_ in zip(ys, gr)])
        return g.loft(rings, closed=full, crease=crease)

    def surf(self, y, ang_deg, lift=0.0):
        a = math.radians(ang_deg)
        p = np.array([(self.rx(y) + lift) * math.sin(a), y, (self.rz(y) + lift) * math.cos(a) + self.zc(y)])
        n = np.array([math.sin(a) / max(self.rx(y), 1e-3), 0, math.cos(a) / max(self.rz(y), 1e-3)])
        return p, n / np.linalg.norm(n)

    def edge(self, ys, grows, ang, r=0.005, sides=4):
        """Rolled edge tube along a column (fixed angle) of an open arc shell."""
        gr = np.broadcast_to(np.asarray(grows, float), (len(ys),))
        pts = [self.surf(y, ang, gg)[0] for y, gg in zip(ys, gr)]
        return g.tube(pts, r, sides=sides, samples=1, cap="round", cap_steps=1, smooth=len(pts) > 2)


def pauldron(sign, centre, scale=1.0, lames=4, dent=False, spike=False, seed=1, tilt_deg=14.0, flare=0.0075):
    """Layered telescoping pauldron (the pawn idiom, scaled): partial hoops around the upper-arm axis under a domed cap."""
    c = np.array(centre, float)
    parts = []
    r0 = 0.057 * scale
    h = 0.030 * scale
    for i in range(lames):
        r = r0 + flare * scale * i
        y = -0.012 * scale - i * 0.022 * scale
        prof = np.array([(r - 0.003 * scale, h / 2), (r + 0.0035 * scale, h / 2 - 0.002 * scale), (r + 0.0075 * scale, h / 2 - 0.006 * scale),
                         (r + 0.0095 * scale, 0), (r + 0.0085 * scale, -h / 2 + 0.003 * scale), (r + 0.0105 * scale, -h / 2 - 0.001 * scale),
                         (r + 0.004 * scale, -h / 2 - 0.004 * scale), (r - 0.003 * scale, -h / 2), (r - 0.003 * scale, h / 2)])
        lam = g.lathe(prof, 18, sweep=250, start=-125, crease=45)
        parts.append(lam.rotated(0, 90 if sign > 0 else 270, 0).translated(0, y, 0))
    rc = r0 + 0.004 * scale
    cap = g.superellipsoid((rc, 0.026 * scale, rc * 1.04), 0.65, 0.9, 5, 14)
    cap = g.warp(cap, lambda P: np.column_stack([P[:, 0], np.where(P[:, 1] < 0, P[:, 1] * 0.2, P[:, 1]), P[:, 2]]), 60)
    cap = cap.translated(0, 0.010 * scale, 0)
    if dent:
        cap = cap.dented(5, 0.028 * scale, 0.005 * scale, seed=21 + seed)
    parts.append(cap.noised(0.0012 * scale, 36, 2, seed=4 + seed))
    if spike:
        sp = g.tube([(0, 0, 0), (0, 0.030 * scale, 0), (0, 0.075 * scale, 0)], [0.016 * scale, 0.011 * scale, 0.0], sides=6, samples=1, cap=None, smooth=False)
        parts.append(sp.translated(0, 0.030 * scale, 0))
    m = merge(parts)
    return m.rotated(0, 0, -sign * tilt_deg).translated(*c)


# ---- IK-lite: keep a rest point of (b1 -> b2) glued to a point carried by `driver` (e.g. the king's off-hand on the sword grip)
def solve_hold(clip, rig, driver, b1, b2, rest_point, step=1 / 30, axes=(0,)):
    from scipy.optimize import least_squares
    p = np.append(np.asarray(rest_point, float), 1.0)
    inv_rest = np.linalg.inv(_bone_world(rig, Clip0, driver, 0.0))
    inv_rest2 = np.linalg.inv(_bone_world(rig, Clip0, b2, 0.0))

    def world(bone, t, ov):
        chain, b = [], bone
        while b:
            chain.append(b)
            b = rig.bones[b].parent
        M = np.eye(4)
        for b in reversed(chain):
            loc = rig.local(b).copy()
            tr = clip.tracks.get((b, "pos"))
            if tr:
                loc = loc + tr.eval(t, clip.duration, (0, 0, 0))
            rot = np.zeros(3)
            tr = clip.tracks.get((b, "rot"))
            if tr:
                rot = tr.eval(t, clip.duration, (0, 0, 0))
            if b in ov:
                rot = ov[b]
            L = np.eye(4)
            L[:3, :3] = g.rot_matrix(*rot)
            L[:3, 3] = loc
            M = M @ L
        return M
    n = int(round(clip.duration / step))
    x0 = np.zeros(2 * len(axes))
    keys1, keys2 = [], []
    for i in range(n + 1):
        t = min(i * step, clip.duration)
        target = (world(driver, t, {}) @ inv_rest @ p)[:3]

        def res(x):
            r1, r2 = np.zeros(3), np.zeros(3)
            for k, ax in enumerate(axes):
                r1[ax], r2[ax] = x[k], x[len(axes) + k]
            q = (world(b2, t, {b1: r1, b2: r2}) @ inv_rest2 @ p)[:3]
            return q - target
        sol = least_squares(res, x0, xtol=1e-9, ftol=1e-9)
        x0 = sol.x
        r1, r2 = [0.0] * 3, [0.0] * 3
        for k, ax in enumerate(axes):
            r1[ax], r2[ax] = float(sol.x[k]), float(sol.x[len(axes) + k])
        keys1.append((t, tuple(r1)))
        keys2.append((t, tuple(r2)))
    for t, v in keys1:
        clip.key(b1, "rot", t, v, "linear")
    for t, v in keys2:
        clip.key(b2, "rot", t, v, "linear")


def _gen_gem(n, seed):
    ts = T.gen_ember(n, seed)
    ts.name = "EH_Gem"
    ts.emissive = ts.emissive * np.array([1.0, 0.50, 0.14])
    ts.emissive_strength = 2.0
    return ts


T.register(T.MaterialDef("EH_Gem", _gen_gem, 37))


def solve_reach(clip, rig, driver, driver_pt, b1, b2, hand_pt, weight, step=1 / 30, axes=(0, 1, 2), lam=0.03):
    """Blend a free hand (rest point `hand_pt` on b2) toward a point `driver_pt` carried by `driver` (weapon grip).
    weight(t) in 0..1: 0 = hand stays where its own rot keys (if any) put it, 1 = hand glued to the grip."""
    from scipy.optimize import least_squares
    dp = np.append(np.asarray(driver_pt, float), 1.0)
    hp = np.append(np.asarray(hand_pt, float), 1.0)
    inv_d = np.linalg.inv(_bone_world(rig, Clip0, driver, 0.0))
    inv_h = np.linalg.inv(_bone_world(rig, Clip0, b2, 0.0))
    own = {b: clip.tracks.pop((b, "rot"), None) for b in (b1, b2)}      # the hand's own authored motion = its free pose

    def world(bone, t, ov, use_own=False):
        chain, b = [], bone
        while b:
            chain.append(b)
            b = rig.bones[b].parent
        M = np.eye(4)
        for b in reversed(chain):
            loc = rig.local(b).copy()
            tr = clip.tracks.get((b, "pos"))
            if tr:
                loc = loc + tr.eval(t, clip.duration, (0, 0, 0))
            rot = np.zeros(3)
            tr = clip.tracks.get((b, "rot"))
            if tr:
                rot = tr.eval(t, clip.duration, (0, 0, 0))
            if b in own and own[b] is not None and use_own:
                rot = own[b].eval(t, clip.duration, (0, 0, 0))
            elif b in (b1, b2) and not use_own:
                rot = np.zeros(3)
            if b in ov:
                rot = ov[b]
            L = np.eye(4)
            L[:3, :3] = g.rot_matrix(*rot)
            L[:3, 3] = loc
            M = M @ L
        return M
    n = int(round(clip.duration / step))
    x0 = np.zeros(2 * len(axes))
    k1, k2 = [], []
    for i in range(n + 1):
        t = min(i * step, clip.duration)
        w = float(weight(t))
        free = (world(b2, t, {}, use_own=True) @ inv_h @ hp)[:3]
        goal = (world(driver, t, {}) @ inv_d @ dp)[:3]
        target = (1 - w) * free + w * goal

        def res(x):
            r1, r2 = np.zeros(3), np.zeros(3)
            for k, ax in enumerate(axes):
                r1[ax], r2[ax] = x[k], x[len(axes) + k]
            q = (world(b2, t, {b1: r1, b2: r2}) @ inv_h @ hp)[:3]
            return np.concatenate([(q - target) * 10.0, lam * w * x * 0.01])
        if w < 1e-4:
            fr = [own[b].eval(t, clip.duration, (0, 0, 0)) if own[b] is not None else np.zeros(3) for b in (b1, b2)]
            k1.append((t, tuple(float(v) for v in fr[0])))
            k2.append((t, tuple(float(v) for v in fr[1])))
            x0 = np.zeros_like(x0)
            continue
        x = least_squares(res, x0, xtol=1e-9, ftol=1e-9).x
        x0 = x
        r1, r2 = [0.0] * 3, [0.0] * 3
        for k, ax in enumerate(axes):
            r1[ax], r2[ax] = float(x[k]), float(x[len(axes) + k])
        k1.append((t, tuple(r1)))
        k2.append((t, tuple(r2)))
    for t, v in k1:
        clip.key(b1, "rot", t, v, "linear")
    for t, v in k2:
        clip.key(b2, "rot", t, v, "linear")


# ---- a dropped weapon: ballistic fall + bounces + spin, authored as world motion and converted to the `weapon` bone's local keys
def _mat_to_euler(R):
    ry = -math.asin(max(-1.0, min(1.0, R[2, 0])))
    if abs(math.cos(ry)) < 1e-6:
        return (0.0, math.degrees(ry), math.degrees(math.atan2(-R[0, 1], R[1, 1])))
    return (math.degrees(math.atan2(R[2, 1], R[2, 2])), math.degrees(ry), math.degrees(math.atan2(R[1, 0], R[0, 0])))


def drop_weapon(clip, rig, bone, t0, axis_local, floor_y, rest_y_off, heading, land_xz=None, grav=9.8, restitution=0.34, bounces=2,
                roll_deg=180.0, kick=(0.0, 0.0, 0.0), step=1 / 30):
    """Release `bone` (pivot = its centre of mass) from its hand at t0.  The centre falls under gravity to `floor_y + rest_y_off`,
    bounces `bounces` times, and the long axis (`axis_local`, rest-frame direction) swings to the horizontal `heading`.
    Call after all other tracks of the clip are final.  Holds the final pose to the end of the clip."""
    parent = rig.bones[bone].parent
    p0 = rig.pos(bone)
    rest_local = rig.local(bone)
    Mp0 = _bone_world(rig, clip, parent, t0)
    Lrest = np.eye(4)
    Lrest[:3, 3] = rest_local
    W0 = Mp0 @ Lrest
    R0, pa = W0[:3, :3], W0[:3, 3]
    a0 = R0 @ np.asarray(axis_local, float)
    d_h = np.asarray(heading, float)
    d_h = d_h / np.linalg.norm(d_h)
    R_align = g.rot_between(a0, d_h)
    Rf_total = R_align                                  # world rotation applied on top of R0
    # axis / angle of the alignment rotation
    ang = math.acos(max(-1.0, min(1.0, (np.trace(Rf_total) - 1) / 2)))
    if ang < 1e-4:
        ax = np.array([0.0, 1.0, 0.0])
    else:
        ax = np.array([Rf_total[2, 1] - Rf_total[1, 2], Rf_total[0, 2] - Rf_total[2, 0], Rf_total[1, 0] - Rf_total[0, 1]]) / (2 * math.sin(ang))
    yf = floor_y + rest_y_off
    pf = np.array([pa[0], yf, pa[2]]) if land_xz is None else np.array([land_xz[0], yf, land_xz[1]])
    # time line: free fall, then bounces
    h = max(pa[1] - yf, 0.02)
    t_fall = math.sqrt(2 * h / grav)
    v = grav * t_fall
    impacts = [t0 + t_fall]
    arcs = []                                           # (t_start, t_end, v0) of each bounce arc
    for k in range(bounces):
        vb = v * restitution ** (k + 1)
        dur = 2 * vb / grav
        arcs.append((impacts[-1], impacts[-1] + dur, vb))
        impacts.append(impacts[-1] + dur)
    t_land = impacts[-1]
    n = int(round(clip.duration / step))
    s_at_impact = [0.78, 0.94, 1.0, 1.0][: len(impacts)]

    def smooth(u):
        u = min(max(u, 0.0), 1.0)
        return u * u * (3 - 2 * u)

    def state(t):
        if t <= t0:
            return pa, 0.0
        if t < impacts[0]:
            tt = t - t0
            y = pa[1] - 0.5 * grav * tt * tt
            u = (t - t0) / max(impacts[0] - t0, 1e-6)
            s = s_at_impact[0] * (u ** 1.4)
            frac = u * 0.8
        else:
            y, s, frac = yf, 1.0, 1.0
            for k, (ta, tb, vb) in enumerate(arcs):
                if ta <= t < tb:
                    tt = t - ta
                    y = yf + vb * tt - 0.5 * grav * tt * tt
                    u = (t - ta) / max(tb - ta, 1e-6)
                    s = s_at_impact[k] + (s_at_impact[k + 1] - s_at_impact[k]) * smooth(u)
                    frac = min(1.0, (t - t0) / max(t_land - t0, 1e-6) * 0.9 + 0.1)
                    break
            if t >= t_land:
                s, frac = 1.0, 1.0
        horiz = min(1.0, (t - t0) / max(t_land - t0, 1e-6))
        horiz = horiz * (2 - horiz)
        pos = np.array([pa[0] + (pf[0] - pa[0]) * horiz + kick[0] * (t - t0), y, pa[2] + (pf[2] - pa[2]) * horiz + kick[2] * (t - t0)])
        return pos, s

    for i in range(n + 1):
        t = min(i * step, clip.duration)
        pos, s = state(t)
        Rt = g.axis_angle(ax, math.degrees(ang) * s) @ R0
        if roll_deg:
            Rt = g.axis_angle(d_h if s > 0 else a0, roll_deg * s * (1 - 0.0)) @ Rt if s > 0 else Rt
        Wt = np.eye(4)
        Wt[:3, :3] = Rt
        Wt[:3, 3] = pos
        if t <= t0:
            Wt = Mp0 @ Lrest if False else _bone_world(rig, clip, parent, t) @ Lrest
        Mp = _bone_world(rig, clip, parent, t)
        L = np.linalg.inv(Mp) @ Wt
        clip.key(bone, "pos", t, tuple(L[:3, 3] - rest_local), "linear")
        clip.key(bone, "rot", t, _mat_to_euler(L[:3, :3]), "linear")
