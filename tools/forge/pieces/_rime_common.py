"""_rime_common - shared helpers for the six Rime Host pieces (leading underscore: skipped by build_all discovery).

* Rime pedestal (art README section 2): obsidian tiers, silver trim with notches, frost in the groove, snow-crystal emblem.
* `shard` / `spikes`: faceted, flattened, bent ice spikes (far more character than a hex prism).
* `frost_layer`: snow build-up copied off the upward faces of any mesh (the "frost on every upward face" rule).
* `fk`: tiny forward-kinematics evaluator so hand grips / "nothing detached" can be checked numerically per clip.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geom as g                      # noqa: E402
from geom import TAU, merge, smoothstep  # noqa: E402
from piece import Piece               # noqa: E402

FRONT_FLAT = 0.3696


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def mir(pts):
    return [(-x, y, z) for x, y, z in pts]


def torus_axis(R, r, axis="z", segments=40, sides=8, arc=360.0):
    t = g.torus(R, r, segments, sides, arc=arc)
    if axis == "z":
        return t.rotated(90, 0, 0)
    if axis == "x":
        return t.rotated(0, 0, 90)
    return t


def frame_xf(origin, xdir, ydir):
    """4x4 matrix taking local (x, y, z) to world: x -> xdir, y -> ydir (orthogonalised), z -> x cross y."""
    x = unit(xdir)
    y = np.asarray(ydir, dtype=float)
    y = unit(y - np.dot(y, x) * x)
    z = np.cross(x, y)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, origin
    return M


# ====================================================================================== ice
def shard(length, radius, sides=5, tip=0.38, flat=0.35, bend=0.0, jitter=0.22, seed=0, taper=0.8, cap=True, chip=0.0):
    """Faceted ice shard standing on y=0 with its point at y=length.  `flat` squashes it into a blade-like prism,
    `bend` (fraction of length) curves the tip sideways along +X, `jitter` randomises facet radii, `chip` slices one
    facet off near the tip.  Cost: sides*2*3 + sides."""
    rng = np.random.default_rng(seed)
    th = np.linspace(0, TAU, sides, endpoint=False) + rng.random() * 0.8
    rs = 1.0 + jitter * (rng.random(sides) - 0.5) * 2
    body = length * (1 - tip)
    levels = [(0.0, radius * 0.92), (length * 0.05, radius), (body, radius * taper * (1 - chip * 0.2)), (length, 0.0)]
    rings = []
    for y, r in levels:
        f = y / length
        sx = r * rs * np.sin(th)
        sz = r * rs * np.cos(th) * (1 - flat)
        off = bend * length * f ** 2
        rings.append(np.stack([sx + off, np.full(sides, y), sz], 1))
    return g.loft(np.stack(rings), closed=True, cap_start=cap, crease=28.0, v_tile=0.1)


def spikes(specs, seed=0, **kw):
    """specs: [(pos, dir, length, radius)] -> merged shards; per-shard seed so no two look alike."""
    out = []
    for i, (pos, d, ln, r) in enumerate(specs):
        s = shard(ln, r, seed=seed + i * 7, bend=kw.get("bend", 0.05) * (1 if i % 2 else -1), flat=kw.get("flat", 0.3),
                  sides=kw.get("sides", 5), tip=kw.get("tip", 0.38), jitter=kw.get("jitter", 0.2))
        out.append(s.aimed(d, pos))
    return merge(out)


def cluster(base, up, n, length, radius, spread=0.03, tilt=28.0, seed=0, **kw):
    """n shards growing from `base`, fanning around the `up` axis by up to `tilt` degrees; lengths in the range."""
    rng = np.random.default_rng(seed)
    up = unit(up)
    t1 = unit(np.cross(up, [0.0, 0.0, 1.0] if abs(up[2]) < 0.9 else [1.0, 0.0, 0.0]))
    t2 = np.cross(up, t1)
    specs = []
    for i in range(n):
        a = rng.random() * TAU
        k = 0.0 if i == 0 else (0.35 + 0.65 * rng.random())
        tl = math.radians(tilt) * k
        d = up * math.cos(tl) + (t1 * math.cos(a) + t2 * math.sin(a)) * math.sin(tl)
        off = (t1 * math.cos(a) + t2 * math.sin(a)) * spread * k * rng.random()
        ln = length[0] + (length[1] - length[0]) * (1.0 if i == 0 else rng.random() ** 0.8)
        r = radius[0] + (radius[1] - radius[0]) * (1.0 if i == 0 else rng.random())
        specs.append((np.asarray(base) + off, d, ln, r))
    return spikes(specs, seed=seed, **kw)


def frost_layer(m, thick=0.006, min_ny=0.55, cover=0.35, freq=16.0, seed=0, lift=0.55):
    """Snow build-up: copies the upward-facing triangles of `m` (noise-masked so the edge is ragged), pushed out along
    the welded smooth normal by `thick`.  Returns a new mesh for an RH_Frost part."""
    m = m.compact() if m.N is None else m
    P, F = m.P, m.F
    fn = m.face_normals(True)
    cen = P[F].mean(1)
    nz = g.fbm3(cen * freq, 1.0, 2, seed=seed)
    sel = (fn[:, 1] > min_ny) & (nz < cover + 0.5 * (fn[:, 1] - min_ny))
    if not sel.any():
        return g.Mesh(np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64))
    sn = m.smooth_normals()
    sn[:, 1] += lift                                   # snow drifts up, not sideways
    sn = sn / np.linalg.norm(sn, axis=1, keepdims=True)
    amt = thick * (0.6 + 0.8 * (g.fbm3(P * freq * 1.7, 1.0, 2, seed=seed + 5) * 0.5 + 0.5))
    out = g.Mesh(P + sn * amt[:, None], F[sel], m.UV.copy(), crease=80.0)
    out = out.cleaned()
    return out.uv_box(0.25).shade(80.0)


def wire_ring(y, R, r=0.004, sides=4, segments=18, ax=0.0, az=0.0):
    return g.torus(R, r, segments, sides).translated(ax, y, az)


def helix(R, y0, y1, turns, r=0.004, sides=4, per_turn=10, ax=0.0, az=0.0, R1=None):
    n = max(4, int(turns * per_turn))
    t = np.linspace(0, 1, n)
    th = t * turns * TAU
    rr = R + ((R1 if R1 is not None else R) - R) * t
    pts = np.stack([ax + rr * np.sin(th), y0 + (y1 - y0) * t, az + rr * np.cos(th)], 1)
    return g.tube(pts, r, sides=sides, samples=1, cap=None, smooth=False)


def zigzag(p0, p1, n, amp, r=0.004, side=(1, 0, 0), sides=4, seed=0):
    """Wire zig-zag from p0 to p1 (n segments) swinging +-amp along `side`."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    side = unit(side)
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(p0 + (p1 - p0) * t + side * amp * (1 if i % 2 else -1) * (0.0 if i in (0, n) else 1.0))
    return g.tube(pts, r, sides=sides, samples=1, cap=None, smooth=False)


# ====================================================================================== pedestal
PED_PROFILE = [(0.392, 0.000), (0.400, 0.008), (0.400, 0.074), (0.386, 0.088), (0.372, 0.100),
               (0.372, 0.108), (0.360, 0.108), (0.360, 0.138), (0.372, 0.142), (0.372, 0.178), (0.352, 0.192),
               (0.352, 0.208), (0.340, 0.220), (0.000, 0.220)]


def _pedestal_loft(K=32):
    th = np.linspace(0, TAU, K, endpoint=False)
    t = np.mod(th + math.radians(22.5), math.radians(45)) - math.radians(22.5)
    rho = (FRONT_FLAT / np.cos(t)) / 0.4001
    rings = []
    for r, y in PED_PROFILE:
        s = float(smoothstep(0.085, 0.100, y))
        k = rho * (1 - s) + s
        rr = r * k
        rings.append(np.stack([rr * np.sin(th), np.full(K, y), rr * np.cos(th)], 1))
    return g.loft(np.stack(rings), closed=True, crease=40.0, cap_start=False, cap_end=False)


def pedestal_parts(p: Piece):
    tier = _pedestal_loft(32)
    tier = tier.noised(0.0016, 22, 2, seed=4)
    fade = lambda P: 0.45 + 0.55 * smoothstep(0.0, 0.2, P[:, 1])
    p.add("ped_tiers", tier, "RH_Basalt", "root", tint=fade)
    # silver trim band with 16 dark notch cuts
    trim = g.lathe([(0.360, 0.110), (0.378, 0.112), (0.380, 0.122), (0.378, 0.134), (0.360, 0.136)], 32, crease=35)
    p.add("ped_trim", trim, "RH_Silver", "root")
    notch = g.extrude(g.rect_poly(0.012, 0.022), 0.006, 0.0, 1).translated(0, 0.123, 0.0)
    th = np.arange(16) * TAU / 16 + TAU / 32
    nm = []
    for t in th:
        nm.append(notch.translated(0, 0, 0.3805).rotated(0, math.degrees(t), 0))
    p.add("ped_trim_notches", merge(nm), "RH_Obsidian", "root", lod1=None)
    # groove: a faint, broken cold seam (not a neon ring) + a few patches of frost with a dark baked tint
    arcs = []
    for a0, span in [(14, 40), (112, 30), (190, 44), (276, 28)]:
        arc = torus_axis(0.28, 0.0030, "y", max(4, span // 6), 3, arc=span)
        arcs.append(arc.rotated(0, a0, 0).scaled(1, 0.5, 1).translated(0, 0.2205, 0))
    p.add("ped_groove_seam", merge(arcs), "RH_Seam", "root", lod1="keep", bake=False)
    groove = torus_axis(0.28, 0.0034, "y", 32, 3, arc=360).scaled(1, 0.4, 1).translated(0, 0.2203, 0)
    p.add("ped_groove_frost", groove, "RH_Frost", "root", lod1=None, tint=lambda P: np.full(len(P), 0.28))
    patches = []
    for a0, span, r0, r1 in [(30, 40, 0.20, 0.31), (150, 34, 0.24, 0.32), (232, 46, 0.18, 0.31), (330, 26, 0.24, 0.32)]:
        prof = [(r0, 0.2206), (r0 + 0.02, 0.2216), ((r0 + r1) / 2, 0.2221), (r1 - 0.01, 0.2213), (r1, 0.2205)]
        pt = g.lathe(prof, 6, sweep=span, start=a0, crease=70)
        patches.append(pt.noised(0.003, 24, 2, seed=int(a0)))
    p.add("ped_top_frost", merge(patches), "RH_Frost", "root", lod1=None, tint=lambda P: np.full(len(P), 0.42))
    # three small crystals at the rear-left octagon corner
    cl = cluster((0.272, 0.078, -0.272), (0.45, 0.8, -0.45), 3, (0.04, 0.07), (0.010, 0.016), spread=0.02, tilt=32, seed=3, flat=0.2)
    p.add("ped_corner_crystals", cl, "RH_Ice", "root", lod1=None)
    # emblem on tier 1's +Z flat: obsidian plaque, silver snow-crystal pierced by a downward blade
    z0 = FRONT_FLAT
    cx, cy = 0.0, 0.044
    plaque = g.lathe([(0, 0), (0.040, 0), (0.040, 0.004), (0, 0.0045)], 18).rotated(90, 0, 0).translated(cx, cy, z0)
    p.add("ped_emblem_plaque", plaque, "RH_Obsidian", "root", lod1="keep")
    bars = []
    for a in (0, 60, 120):
        b = g.extrude(g.rect_poly(0.060, 0.0085), 0.0052, 0.0012, 1).rotated(0, 0, a).translated(cx, cy, z0 + 0.0045)
        bars.append(b)
    for a in range(6):
        tip = g.extrude(np.array([(-0.0045, 0), (0.0045, 0), (0, 0.0075)]), 0.0052, 0.0, 1).rotated(0, 0, a * 60 + 0)
        d = np.array([-math.sin(math.radians(a * 60)), math.cos(math.radians(a * 60))]) * 0.030
        bars.append(tip.translated(cx + d[0], cy + d[1], z0 + 0.0045))
    blade = g.extrude(np.array([(-0.004, 0.029), (0.004, 0.029), (0.0, -0.029)]), 0.0075, 0.001, 1).translated(cx, cy, z0 + 0.0075)
    p.add("ped_emblem", merge(bars + [blade]), "RH_Silver", "root", lod1="keep")


# ====================================================================================== forward kinematics (tuning aid)
def fk(rig, clip, t):
    """-> dict bone -> 4x4 world matrix at time t (rest-pose points bound to `bone` map with
    W[bone] @ translate(-rest_pos[bone]) @ point).  Uses the clip's own tracks / easing."""
    from rig import _euler_to_quat   # noqa: F401  (kept for parity)
    W = {}
    for name in rig.order:
        b = rig.bones[name]
        loc = rig.local(name).copy()
        R = np.eye(3)
        S = np.ones(3)
        for path in ("rot", "pos", "scale"):
            tr = clip.tracks.get((name, path))
            if tr is None:
                continue
            if path == "rot":
                R = g.rot_matrix(*tr.eval(t, clip.duration, (0, 0, 0)))
            elif path == "pos":
                loc = loc + tr.eval(t, clip.duration, (0, 0, 0))
            else:
                S = tr.eval(t, clip.duration, (1, 1, 1))
        M = np.eye(4)
        M[:3, :3] = R * S[None, :]
        M[:3, 3] = loc
        W[name] = M if b.parent is None else W[b.parent] @ M
    return W


def fk_point(rig, W, bone, rest_point):
    """World position of a point that sits at `rest_point` in the rest pose, rigidly bound to `bone`."""
    M = W[bone]
    local = np.asarray(rest_point, float) - rig.pos(bone)
    return (M @ np.append(local, 1.0))[:3]


# ====================================================================================== armour helpers
def path_at(path, t):
    """Point and unit tangent at arc-length fraction t along a polyline."""
    path = np.asarray(path, float)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    s = t * cum[-1]
    i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(seg) - 1))
    u = (s - cum[i]) / max(seg[i], 1e-9)
    return path[i] + (path[i + 1] - path[i]) * u, unit(path[i + 1] - path[i])


def lame(r, h=0.03, sweep=220.0, seg=7, rim=0.004):
    """A partial hoop (telescoping armour lame) of inner radius r around +Y, opening toward -Z, rolled lip at the bottom."""
    prof = np.array([(r - 0.003, h / 2), (r + 0.004, h / 2 - 0.003), (r + 0.007, 0.002), (r + 0.007 + rim, -h / 2 + 0.002),
                     (r + 0.003, -h / 2 - 0.003), (r - 0.003, -h / 2)])
    m = g.lathe(prof[::-1], seg, sweep=sweep, start=-sweep / 2, crease=45)
    return m


def limb_lames(path, radii, ts, h=0.03, sweep=220.0, grow=0.006, seg=7, spin=0.0, hscale=None):
    """Overlapping lames strapped around a limb: each is a little larger than the one above (lower lames proud)."""
    out = []
    n = len(ts)
    for i, t in enumerate(ts):
        pos, d = path_at(path, t)
        r = float(np.interp(t, np.linspace(0, 1, len(radii)), radii)) + grow
        hh = h * (hscale[i] if hscale else 1.0)
        m = lame(r + 0.003 * (i / max(n - 1, 1)), hh, sweep, seg).rotated(0, spin, 0)
        out.append(m.aimed(d, pos))
    return merge(out)


def poly_wire(pts, r=0.0034, sides=4, closed=True):
    return g.tube(np.asarray(pts, float), r, sides=sides, samples=1, cap=None, smooth=False, closed=closed)


def claw_hand(side, wrist, fwd, curl=1.0, scale=1.0, spread=1.0):
    """Gaunt clawed hand at `wrist` (world), fingers hooking along `fwd` (shared by the humanoid Rime pieces)."""
    fwd = unit(fwd)
    palm = g.superellipsoid((0.021 * scale, 0.024 * scale, 0.022 * scale), 0.6, 0.6, 3, 8).aimed(fwd, wrist)
    fing = []
    right = unit(np.cross([0, 1, 0], fwd))
    for o in (-0.0135, -0.0045, 0.0045, 0.0135):
        base = wrist + fwd * 0.028 * scale + right * o * scale * spread
        pts = [base, base + fwd * 0.022 * scale + [0, -0.010 * curl * scale, 0] + right * o * 0.8 * (spread - 1),
               base + fwd * 0.030 * scale + [0, -0.032 * curl * scale, 0] + right * o * 1.6 * (spread - 1)]
        fing.append(g.tube(pts, [0.0066 * scale, 0.0055 * scale, 0.0035 * scale], sides=4, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 0, 1)))
    thumb = g.tube([wrist + right * side * 0.016 * scale, wrist + right * side * 0.026 * scale + fwd * 0.022 * scale], [0.007 * scale, 0.004 * scale],
                   sides=4, samples=1, cap="round", cap_steps=1, smooth=False)
    return merge([palm] + fing + [thumb])


def follow_keys(rig, clip, bone, parent, world_fn, times, parent_rest_ok=True):
    """Add `pos` keys to `bone` (child of `parent`) so that it tracks the world point returned by world_fn(W) at each time
    (used to make a floating element - orbiting runes - follow a held lantern).  Linear keys, dense sampling."""
    rest_local = rig.local(bone)
    for t in times:
        W = fk(rig, clip, t)
        T = world_fn(W)
        Pm = W[parent]
        loc = (np.linalg.inv(Pm) @ np.append(T, 1.0))[:3]
        clip.key(bone, "pos", float(t), tuple(loc - rest_local), "linear")


# ---- weapon drop (ballistic fall + bounces), shared logic with the Emberhold set; the world-matrix helper is local
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

