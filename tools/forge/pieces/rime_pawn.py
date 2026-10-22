"""rime_pawn - Rime Thrall: a hunched revenant foot-soldier, obsidian plates wired onto a gaunt frame, a jagged ice
cleaver, a comb of icicle spikes breaking out of the spine.  Built from docs/art/rime_pawn.md."""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import geom as g                      # noqa: E402
from geom import TAU, merge, smoothstep  # noqa: E402
from piece import Piece               # noqa: E402
from rig import Clip, Rig             # noqa: E402
import _rime_common as rc             # noqa: E402
from _rime_common import unit, mir, frame_xf, shard, spikes, cluster, frost_layer  # noqa: E402

ASSET_ID = "rime_pawn"

# cleaver geometry (world rest pose)
GUARD = np.array([-0.205, 0.52, 0.20])
TIP = np.array([-0.17, 0.34, 0.44])
BUTT = np.array([-0.12, 0.50, 0.02])


# ======================================================================================= rig
def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.52, -0.02))
    r.add("spine", "body", (0, 0.58, -0.02))
    r.add("head", "spine", (0, 0.80, 0.12))
    r.add("top", "spine", (0, 0.80, -0.07))
    r.add("arm_L", "spine", (0.18, 0.78, 0.07))
    r.add("hand_L", "arm_L", (0.21, 0.60, 0.11))
    r.add("arm_R", "spine", (-0.18, 0.78, 0.07))
    r.add("hand_R", "arm_R", (-0.215, 0.60, 0.14))
    r.socket("socket_weapon_R", "hand_R", (-0.16, 0.51, 0.11))
    r.socket("socket_cast", "head", (0, 0.88, 0.22))
    r.socket("socket_impact", "body", (-0.02, 0.50, 0.55))
    r.socket("socket_head", "head", (0, 0.96, 0.14))
    return r


# ======================================================================================= torso surface helpers
_TY = [0.46, 0.54, 0.65, 0.76, 0.86]
_ZC = [-0.04, -0.02, 0.03, 0.09, 0.125]
_RW = [0.080, 0.085, 0.098, 0.120, 0.120]


def zc(y):
    return np.interp(y, _TY, _ZC)


def rw(y):
    return np.interp(y, _TY, _RW)


def rd(y):
    return rw(y) * 0.76


def wrap(m, grow=0.0, back=False, edge=0.035, crease=40.0):
    """Subdivide a flat plate lying in XY (thickness along z) and drape it over the front (or back) of the torso."""
    m = m.subdivided_to(edge, max_levels=1)

    def f(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        s = np.clip(x / (rw(y) + grow), -0.97, 0.97)
        sq = np.sqrt(1 - s * s)
        if back:
            return np.column_stack([x, y, zc(y) - (rd(y) + grow) * sq + z])
        return np.column_stack([x, y, zc(y) + (rd(y) + grow) * sq + z])
    return g.warp(m, f, crease)


def torso_point(y, x=0.0, grow=0.0, back=False):
    s = np.clip(x / (rw(y) + grow), -0.97, 0.97)
    sq = math.sqrt(1 - s * s)
    z = zc(y) + (-1 if back else 1) * (rd(y) + grow) * sq
    return np.array([x, y, float(z)])


# ======================================================================================= lower body
def legs(p: Piece):
    for side, nm in ((+1, "L"), (-1, "R")):
        dz = 0.045 if side > 0 else 0.0                     # left foot advanced
        sh = [(0.085, 0.262, 0.05 + dz), (0.088, 0.34, 0.075 + dz), (0.085, 0.41, 0.10 + dz)]
        sh = [(side * x, y, z) for x, y, z in sh]
        shin = g.tube(sh, [0.025, 0.033, 0.040], sides=7, samples=2, cap=None, up=(0, 0, 1)).noised(0.002, 30, 2, seed=2 + side)
        p.add(f"shin_{nm}", shin, "RH_Bone", "body", uv_scale=2)
        th = [(0.085, 0.41, 0.10 + dz), (0.080, 0.48, 0.03 + dz * 0.5), (0.070, 0.55, -0.01)]
        th = [(side * x, y, z) for x, y, z in th]
        thigh = g.tube(th, [0.040, 0.048, 0.054], sides=8, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"thigh_{nm}", thigh, "RH_Armour", "body", uv_scale=2)
        # foot (bare, grey) + claws
        foot = g.superellipsoid((0.044, 0.026, 0.092), 0.55, 0.65, 5, 10).translated(side * 0.080, 0.249, 0.045 + dz)
        heel = g.superellipsoid((0.030, 0.024, 0.030), 0.6, 0.6, 3, 8).translated(side * 0.080, 0.252, -0.018 + dz)
        p.add(f"foot_{nm}", merge([foot, heel]), "RH_Bone", "body", uv_scale=2)
        sab = g.superellipsoid((0.047, 0.020, 0.074), 0.5, 0.6, 4, 10).translated(side * 0.080, 0.266, 0.062 + dz)
        sab2 = g.superellipsoid((0.040, 0.015, 0.020), 0.5, 0.6, 3, 8).translated(side * 0.080, 0.274, 0.118 + dz)
        p.add(f"sabaton_{nm}", merge([sab, sab2]), "RH_Obsidian", "body")
        claws = spikes([((side * (0.080 + k * 0.026), 0.252, 0.128 + dz), (k * 0.25, 0.12, 1.0), 0.052 - abs(k) * 0.010, 0.013) for k in (-1, 0, 1)],
                       seed=10 + (1 if side > 0 else 2), flat=0.35, sides=4, tip=0.55)
        p.add(f"claws_{nm}", claws, "RH_Ice", "body")
        # shin plate (obsidian, forward leaning) with a rolled top and a frost cap
        plate = g.extrude_plane(np.array([(0.272, 0.095), (0.402, 0.13), (0.414, 0.156), (0.290, 0.118)]) + [0, dz], 0.034, "YZ", bevel=0.0065, bevel_segments=1)
        plate = plate.translated(side * 0.087, 0, 0)
        p.add(f"shinplate_{nm}", plate, "RH_Obsidian", "body")
        p.add(f"shin_lames_{nm}", rc.limb_lames(sh, [0.025, 0.033, 0.040], [0.20, 0.42, 0.64], h=0.046, sweep=235, grow=0.005, seg=7), "RH_Armour", "body")
        p.add(f"thigh_lames_{nm}", rc.limb_lames(th, [0.040, 0.048, 0.054], [0.22, 0.48, 0.74], h=0.052, sweep=240, grow=0.006, seg=7), "RH_Obsidian", "body")
        cap = g.superellipsoid((0.036, 0.032, 0.026), 0.55, 0.65, 4, 9).rotated(-20, 0, 0).translated(side * 0.088, 0.432, 0.128 + dz)
        p.add(f"kneecap_{nm}", cap, "RH_Obsidian", "body")
        p.add(f"kneecap_frost_{nm}", frost_layer(cap, 0.006, min_ny=0.3, cover=0.4, seed=11 + (side > 0)), "RH_Frost", "body", lod1=None, tint=lambda P: np.full(len(P), 0.55))
        wire = merge([rc.helix(0.0305, 0.268, 0.305, 2.0, r=0.0032, sides=3, per_turn=7, ax=side * 0.085, az=0.056 + dz),
                      rc.helix(0.038, 0.345, 0.375, 1.5, r=0.0032, sides=3, per_turn=7, ax=side * 0.088, az=0.088 + dz)])
        p.add(f"leg_wire_{nm}", wire, "RH_Silver", "body", lod1=None)
        knee = cluster((side * 0.088, 0.428, 0.138 + dz), (0.0, 0.3, 1.0), 3, (0.05, 0.09), (0.012, 0.018), tilt=35, seed=4 + abs(side) * (1 if side > 0 else 3), flat=0.3)
        p.add(f"knee_ice_{nm}", knee, "RH_Ice", "body")
    # pelvis + loincloth + belt
    pelvis = g.superellipsoid((0.100, 0.052, 0.072), 0.6, 0.6, 5, 12).translated(0, 0.545, -0.02)
    p.add("pelvis", pelvis, "RH_Armour", "body", uv_scale=2)
    for side, nm in ((+1, "L"), (-1, "R")):
        hp = [g.superellipsoid((0.050 - 0.006 * i, 0.034, 0.062 - 0.006 * i), 0.5, 0.6, 3, 8).rotated(0, 0, side * (-22 - 8 * i)).translated(side * (0.104 + 0.012 * i), 0.548 - 0.026 * i, 0.0 + 0.0)
              for i in range(3)]
        p.add(f"hip_plates_{nm}", merge(hp), "RH_Obsidian", "body")
        p.add(f"hip_spike_{nm}", spikes([((side * 0.14, 0.50, 0.0), (side * 1.0, -0.15, -0.2), 0.075, 0.016)], seed=90 + (side > 0), flat=0.3, sides=4), "RH_Ice", "body")
    strips = []
    rng = np.random.default_rng(5)
    for i, x in enumerate(np.arange(-0.08, 0.081, 0.04)):
        ln = 0.15 + 0.05 * rng.random()
        tipx = (rng.random() - 0.5) * 0.012
        poly = np.array([(-0.0185, 0), (0.0185, 0), (0.0135, -ln * 0.78), (tipx + 0.004, -ln), (tipx - 0.004, -ln * 0.92), (-0.0125, -ln * 0.74)])
        s = g.extrude(poly, 0.0075, 0.0015, 1).rotated(-6 - 4 * rng.random(), 0, (x * 30)).translated(x, 0.568, 0.081 + 0.012 * (1 - abs(x) / 0.08))
        strips.append(s)
    p.add("loincloth", merge(strips), "RH_Cloth", "body", uv_scale=2)
    belt = g.tube([(-0.098, 0.572, 0.036), (-0.05, 0.572, 0.080), (0.0, 0.572, 0.090), (0.05, 0.572, 0.080), (0.098, 0.572, 0.036)], 0.012,
                  sides=5, samples=3, cap="round", cap_steps=1, ellipse=(1.0, 1.0), up=(0, 1, 0))
    p.add("belt_rope", belt, "RH_Silver", "body")
    buckle = g.extrude(g.ngon(6, 0.020, 0), 0.008, 0.002, 1).translated(0.0, 0.572, 0.099)
    p.add("belt_buckle", buckle, "RH_Obsidian", "body")
    # frost clusters on loincloth hems + bone knobs
    hem = [cluster((x + 0.002, 0.368 + 0.0 * x, 0.098), (0.0, -0.2, 1.0), 2, (0.018, 0.038), (0.005, 0.008), tilt=30, seed=20 + i, flat=0.2, sides=4)
           for i, x in enumerate(np.arange(-0.08, 0.081, 0.04))]
    p.add("loin_frost", merge(hem), "RH_Frost", "body")


# ======================================================================================= torso
def torso(p: Piece):
    path = [(0, 0.54, -0.02), (0, 0.65, 0.03), (0, 0.76, 0.09)]
    t = g.tube(path, [0.085, 0.098, 0.120], sides=10, samples=3, cap="round", cap_steps=1, ellipse=(0.76, 1.0), up=(0, 0, 1)).noised(0.002, 24, 2, seed=5)
    p.add("torso", t, "RH_Armour", "spine", uv_scale=2)
    # shoulder yoke / hunch
    hump = g.superellipsoid((0.125, 0.052, 0.082), 0.6, 0.7, 5, 12).rotated(-14, 0, 0).translated(0, 0.80, 0.045)
    p.add("hump", hump, "RH_Armour", "spine", uv_scale=2)
    # cracked chest plate: two halves + glow seam in the gap
    crack = [(0.002, 0.805), (0.018, 0.765), (-0.010, 0.725), (0.020, 0.685), (-0.008, 0.645), (0.004, 0.595)]
    gap = 0.0042
    L = np.array([(crack[0][0] + gap, crack[0][1] + 0.0)] + [(c[0] + gap, c[1]) for c in crack[1:]] + [(0.088, 0.595), (0.112, 0.74), (0.082, 0.80)])
    R = np.array([(-0.082, 0.80), (-0.112, 0.74), (-0.088, 0.595)] + [(c[0] - gap, c[1]) for c in crack[::-1]])
    for nm, poly in (("L", L), ("R", R)):
        pl = g.extrude(poly, 0.012, 0.0035, 1)
        p.add(f"chest_plate_{nm}", wrap(pl, 0.004), "RH_Obsidian", "spine")
    seam = np.array([torso_point(c[1], c[0], 0.001) + [0, 0, 0.001] for c in crack])
    seam_m = g.tube(seam, 0.0036, sides=4, samples=1, cap=None, smooth=False)
    p.add("chest_seam_glow", seam_m, "RH_Glow", "spine", bake=False, lod1="keep")
    for nm, poly in (("L", L), ("R", R)):
        wp = [torso_point(y, x, 0.0105) for x, y in poly]
        p.add(f"chest_edge_wire_{nm}", rc.poly_wire(wp, 0.0030, 4, True), "RH_Silver", "spine", lod1=None)
    # silver lacing across the crack (6 loops)
    lace = []
    for k in range(6):
        c = crack[k]
        a = torso_point(c[1] + 0.012, c[0] - 0.030, 0.012)
        b = torso_point(c[1] - 0.006, c[0] + 0.030, 0.012)
        lace.append(g.tube([a, (a + b) / 2 + [0, 0, 0.004], b], 0.0034, sides=4, samples=1, cap=None, smooth=False))
    p.add("chest_lacing", merge(lace), "RH_Silver", "spine", lod1=None)
    # rib bands (front 200 degrees): silver hoops
    bands = []
    for y in (0.62, 0.67, 0.72):
        pts = []
        for a in np.linspace(-100, 100, 9):
            s = math.sin(math.radians(a))
            c = math.cos(math.radians(a))
            pts.append((s * (rw(y) + 0.014), y, zc(y) + c * (rd(y) + 0.014)))
        bands.append(g.tube(pts, 0.0058, sides=4, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 1, 0)))
    p.add("rib_bands", merge(bands), "RH_Silver", "spine", tint=lambda P: np.full(len(P), 0.5))
    # back plates: three overlapping scales, jagged lower edge
    bp = []
    for i, y in enumerate((0.62, 0.69, 0.76)):
        poly = np.array([(-0.085, y + 0.035), (0.085, y + 0.035), (0.088, y - 0.02), (0.060, y - 0.045), (0.030, y - 0.026), (0.0, y - 0.050),
                         (-0.032, y - 0.028), (-0.060, y - 0.046), (-0.088, y - 0.02)])
        bp.append(wrap(g.extrude(poly, 0.010, 0.0035, 1), 0.005 + 0.002 * i, back=True))
    p.add("back_plate_wire", merge([rc.poly_wire([torso_point(yy, xx, 0.0105 + 0.002 * i, back=True) for xx, yy in
                                  [(-0.085, y0 + 0.035), (0.085, y0 + 0.035), (0.088, y0 - 0.02), (0.060, y0 - 0.045), (0.030, y0 - 0.026), (0.0, y0 - 0.050), (-0.032, y0 - 0.028), (-0.060, y0 - 0.046), (-0.088, y0 - 0.02)]], 0.0026, 3, True)
                                  for i, y0 in enumerate((0.62, 0.69, 0.76))]), "RH_Silver", "spine", lod1=None)
    p.add("back_plates", merge(bp), "RH_Obsidian", "spine")
    # vertebrae knobs between the spikes
    kn = g.instances(g.dome(0.012, 0.011, 6, 1), [torso_point(y, 0.0, 0.016, back=True) for y in np.linspace(0.58, 0.79, 8)],
                     [(0, 0.2, -1.0)] * 8)
    p.add("vertebrae", kn, "RH_Bone", "spine", lod1=None)
    # tattered half cape (soft: spine -> top): a jagged-hem grid draped behind the shoulders
    R, K = 8, 9
    rings, tips = [], []
    for r in range(R):
        t = r / (R - 1)
        y = 0.80 - 0.40 * t
        xl = -0.085 + 0.0 * t
        xr = 0.075 + 0.14 * t
        row = []
        for k in range(K):
            u = k / (K - 1)
            x = xl + (xr - xl) * u
            yy = y
            if r >= R - 2:
                tooth = (k % 2)
                yy = y - (0.07 if r == R - 1 else 0.02) * tooth * (0.6 + 0.4 * ((k * 7) % 3) / 2)
            zb = min(zc(yy) - rd(yy) - 0.02 - max(0.78 - yy, 0) * 0.22, -0.012) + 0.010 * math.sin(x * 55 + yy * 20)
            row.append((x + 0.03 * max(0.78 - yy, 0), yy, zb))
        rings.append(row)
        if r == R - 1:
            tips = [row[k] for k in range(1, K, 2)]
    cm = g.loft(np.array(rings)[::-1], closed=False, crease=60, v_tile=0.25, u_tile=0.25)
    p.add("cape", cm, "RH_Cloth", "spine", bone2="top", blend=(0.78, 0.48), uv_scale=2)
    hemf = [cluster((x, y + 0.01, z), (0.0, -1.0, -0.3), 2, (0.022, 0.04), (0.005, 0.008), tilt=35, seed=30 + i, flat=0.2, sides=4)
            for i, (x, y, z) in enumerate(tips)]
    p.add("cape_frost", merge(hemf), "RH_Frost", "spine", bone2="top", blend=(0.78, 0.48), lod1=None)


# ======================================================================================= spikes
def spine_spikes(p: Piece):
    # base points along the back, directions up-and-back, a fan; tallest tip y = 1.05
    ys = [0.64, 0.69, 0.735, 0.775, 0.805, 0.835, 0.86]
    lens = [0.15, 0.20, 0.25, 0.30, 0.23, 0.17, 0.12]
    rads = [0.020, 0.023, 0.025, 0.026, 0.022, 0.018, 0.014]
    specs, collars = [], []
    for i, (y, ln, r) in enumerate(zip(ys, lens, rads)):
        bpt = torso_point(min(y, 0.80), 0.0, 0.012, back=True) + [0.0, max(0, y - 0.80), -0.0]
        fan = (i - 3) * 0.10
        d = unit((fan, 1.0, -0.62 - 0.07 * (3 - abs(i - 3))))
        specs.append((bpt, d, ln, r))
        collars.append(g.superellipsoid((r * 1.5, r * 0.8, r * 1.5), 0.5, 0.6, 3, 7).rotated(-28, 0, 0).translated(*bpt))
    # tallest tip check
    tops = [s[0][1] + s[1][1] * s[2] for s in specs]
    k = 1.0 + (1.05 - max(tops)) / max(s[2] * s[1][1] for s in specs if s[0][1] + s[1][1] * s[2] == max(tops))
    specs = [(a, b, c * k if (a[1] + b[1] * c == max(tops)) else c, d) for a, b, c, d in specs]
    p.add("spine_spikes", spikes(specs, seed=40, bend=0.07, flat=0.28, sides=5, tip=0.42), "RH_Ice", "top")
    p.add("spike_collars", merge(collars), "RH_Obsidian", "top")
    # small secondary thorns between the big ones
    sm = []
    for i in range(6):
        y = 0.66 + 0.035 * i
        bpt = torso_point(min(y, 0.80), 0.0, 0.010, back=True) + [0.0, max(0, y - 0.80), 0.0]
        for sx in (-1, 1):
            sm.append((bpt + [sx * 0.032, 0, 0], unit((sx * 0.75, 0.55, -0.45)), 0.05 + 0.02 * ((i + (sx > 0)) % 3), 0.011))
    p.add("spine_thorns", spikes(sm, seed=70, flat=0.3, sides=4, tip=0.5), "RH_Ice", "top", lod1=None)


# ======================================================================================= arms
def hand(side, wrist, fwd, curl=1.0, seed=0):
    """Gaunt clawed hand at `wrist` (world), fingers hooking along `fwd`."""
    palm = g.superellipsoid((0.021, 0.024, 0.022), 0.6, 0.6, 3, 8)
    palm = palm.aimed(fwd, wrist)
    fing = []
    right = unit(np.cross([0, 1, 0], fwd))
    for k, o in enumerate((-0.0135, -0.0045, 0.0045, 0.0135)):
        base = wrist + unit(fwd) * 0.028 + right * o
        pts = [base, base + unit(fwd) * 0.022 + [0, -0.010 * curl, 0], base + unit(fwd) * 0.030 + [0, -0.032 * curl, 0]]
        fing.append(g.tube(pts, [0.0066, 0.0055, 0.0035], sides=4, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 0, 1)))
    thumb = g.tube([wrist + right * side * 0.016, wrist + right * side * 0.026 + unit(fwd) * 0.022], [0.007, 0.004], sides=4, samples=1, cap="round", cap_steps=1, smooth=False)
    return merge([palm] + fing + [thumb])


def arms(p: Piece):
    for side, nm in ((+1, "L"), (-1, "R")):
        up = [(0.185, 0.775, 0.07), (0.200, 0.735, 0.085), (0.205, 0.69, 0.10)]
        up = [(side * x, y, z) for x, y, z in up]
        upper = g.tube(up, [0.030, 0.026, 0.025], sides=7, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"arm_{nm}", upper, "RH_Bone", f"arm_{nm}", uv_scale=2)
        fore_pts = [(0.205, 0.69, 0.10), (0.210, 0.60, 0.11), (0.200, 0.54, 0.14)]
        if side < 0:
            fore_pts = [(0.205, 0.69, 0.10), (0.215, 0.60, 0.13), (0.185, 0.545, 0.165)]
        fore_pts = [(side * x, y, z) for x, y, z in fore_pts]
        fore = g.tube(fore_pts, [0.025, 0.026, 0.019], sides=7, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"forearm_{nm}", fore, "RH_Bone", f"hand_{nm}", uv_scale=2)
        # armour on the limb: telescoping lames, silver wire bindings, tattered sleeve rags
        p.add(f"upper_lames_{nm}", rc.limb_lames(up, [0.030, 0.026, 0.025], [0.12, 0.42], h=0.040, sweep=230, grow=0.005, seg=7), "RH_Armour", f"arm_{nm}")
        p.add(f"vambrace_{nm}", rc.limb_lames(fore_pts, [0.025, 0.026, 0.019], [0.30, 0.52, 0.74], h=0.052, sweep=240, grow=0.005, seg=7), "RH_Obsidian", f"hand_{nm}")
        c0 = np.array(fore_pts[1])
        p.add(f"arm_wire_{nm}", merge([rc.helix(0.0275, 0.560, 0.600, 2.2, r=0.0032, sides=3, per_turn=7, ax=c0[0], az=c0[2] + 0.0),
                                       rc.helix(0.0285, 0.640, 0.680, 1.6, r=0.0032, sides=3, per_turn=7, ax=side * 0.212, az=0.098)]), "RH_Silver", f"hand_{nm}", lod1=None)
        rags = []
        for k, (dy, ln) in enumerate(((0.0, 0.085), (0.02, 0.11), (-0.02, 0.07))):
            poly = np.array([(-0.011, 0), (0.011, 0), (0.008, -ln * 0.8), (0.0, -ln), (-0.009, -ln * 0.7)])
            rags.append(g.extrude(poly, 0.006, 0.0012, 1).rotated(0, side * (-70 + 70 * k), 0).translated(side * (0.196 + 0.012 * k), 0.772 + dy, 0.07 + (-0.03 + 0.03 * k)))
        p.add(f"arm_rags_{nm}", merge(rags), "RH_Cloth", f"arm_{nm}", uv_scale=2)
        # elbow ice spur
        sp = cluster((side * 0.222, 0.645, 0.075), (side * 1.0, 0.1, -0.3), 2, (0.07, 0.11), (0.011, 0.013), tilt=24, seed=60 + (side > 0), flat=0.3)
        p.add(f"elbow_ice_{nm}", sp, "RH_Ice", f"hand_{nm}")
    # hands
    p.add("hand_L", hand(+1, np.array([0.200, 0.520, 0.145]), (0.0, -0.45, 1.0), 1.0), "RH_Bone", "hand_L", uv_scale=2)
    p.add("hand_R", hand(-1, np.array([-0.178, 0.515, 0.130]), (0.1, -0.25, 1.0), 0.4), "RH_Bone", "hand_R", uv_scale=2)
    # shoulders: L big layered plate with frost, R small cracked plate
    big = g.superellipsoid((0.072, 0.026, 0.064), 0.55, 0.7, 5, 12).noised(0.0016, 36, 2, seed=3)
    big = big.rotated(0, 0, -12).translated(0.205, 0.805, 0.07)
    big2 = g.superellipsoid((0.068, 0.020, 0.060), 0.55, 0.7, 4, 10).rotated(0, 0, -16).translated(0.215, 0.778, 0.065)
    big3 = g.superellipsoid((0.060, 0.018, 0.055), 0.55, 0.7, 4, 10).rotated(0, 0, -20).translated(0.222, 0.754, 0.06)
    p.add("shoulder_L", merge([big, big2, big3]), "RH_Obsidian", "arm_L")
    p.add("shoulder_L_frost", frost_layer(big, 0.006, min_ny=0.45, cover=0.28, seed=2), "RH_Frost", "arm_L", lod1=None, tint=lambda P: np.full(len(P), 0.45))
    p.add("shoulder_L_ice", cluster((0.215, 0.822, 0.03), (0.2, 1.0, -0.2), 4, (0.08, 0.16), (0.012, 0.022), spread=0.035, tilt=30, seed=8), "RH_Ice", "arm_L")
    small = g.superellipsoid((0.050, 0.023, 0.052), 0.5, 0.65, 4, 10).noised(0.0016, 36, 2, seed=4).rotated(0, 0, 10).translated(-0.198, 0.797, 0.07)
    small = small.dented(2, 0.02, 0.004, seed=4)
    p.add("shoulder_R", small, "RH_Obsidian", "arm_R")
    p.add("shoulder_R_frost", frost_layer(small, 0.006, min_ny=0.45, cover=0.28, seed=3), "RH_Frost", "arm_R", lod1=None, tint=lambda P: np.full(len(P), 0.45))
    crackline = g.tube([(-0.216, 0.808, 0.056), (-0.206, 0.806, 0.074), (-0.212, 0.802, 0.090)], 0.0028, sides=4, samples=1, cap=None, smooth=False)
    p.add("shoulder_R_crack", crackline, "RH_Silver", "arm_R", lod1=None)


# ======================================================================================= head
HEAD_C = np.array([0.0, 0.875, 0.17])


def head_xf(m):
    return m.rotated(20, 0, 10).translated(*HEAD_C)


def head(p: Piece):
    neck = g.tube([(0, 0.765, 0.075), (0, 0.80, 0.105), (0, 0.835, 0.145)], [0.034, 0.028, 0.027], sides=7, samples=2, cap=None, up=(0, 0, 1))
    p.add("neck", neck, "RH_Bone", "head", uv_scale=2)
    skull = g.superellipsoid((0.044, 0.053, 0.050), 0.8, 0.85, 6, 12)
    brow = g.superellipsoid((0.047, 0.012, 0.026), 0.6, 0.6, 3, 8).translated(0, 0.016, 0.034)
    jaw = g.superellipsoid((0.030, 0.020, 0.036), 0.6, 0.6, 3, 8).translated(0, -0.044, 0.016)
    nose = g.superellipsoid((0.007, 0.011, 0.010), 0.6, 0.6, 3, 6).translated(0, -0.003, 0.053)
    cheek = [g.superellipsoid((0.011, 0.012, 0.012), 0.6, 0.6, 3, 6).translated(s * 0.027, -0.013, 0.038) for s in (-1, 1)]
    p.add("head", head_xf(merge([skull, brow, jaw, nose] + cheek)), "RH_Bone", "head", uv_scale=2)
    # half-helm: faceted obsidian dome over the upper skull
    helm_prof = [(0.049, -0.040), (0.054, -0.0), (0.049, 0.038), (0.030, 0.060), (0.0, 0.067)]
    helm = g.lathe(helm_prof, 14, crease=35, shape=g.polygon_shape(14)).scaled(1.0, 1.0, 1.04).translated(0, -0.002, -0.004)
    p.add("helm", head_xf(helm), "RH_Obsidian", "head")
    nasal = g.extrude(np.array([(-0.0075, -0.040), (0.0075, -0.040), (0.0062, 0.030), (-0.0062, 0.030)]), 0.006, 0.0014, 1).translated(0, 0.004, 0.056).rotated(-10, 0, 0)
    p.add("helm_nasal", head_xf(nasal), "RH_Obsidian", "head", lod1=None)
    brim = g.torus(0.0505, 0.0050, 14, 4).scaled(1.0, 1.0, 1.04).translated(0, -0.034, -0.004)
    p.add("helm_band", head_xf(brim), "RH_Silver", "head", lod1=None)
    # glowing eye slits (focal point 1)
    eyes = [g.extrude(np.array([(-0.0075, -0.0035), (0.0075, 0.0, ), (0.0065, 0.0045), (-0.0075, 0.0015)]) * [s, 1], 0.005, 0.0012, 1).translated(s * 0.0205, 0.0035, 0.0525)
            for s in (-1, 1)]
    p.add("eye_slits", head_xf(merge(eyes)), "RH_Glow", "head", bake=False, lod1="keep")
    # frozen jaw icicles + helm horn stubs
    ic = cluster((0.0, -0.057, 0.040), (0.0, -1.0, 0.3), 5, (0.030, 0.070), (0.006, 0.010), spread=0.035, tilt=20, seed=9, flat=0.3, sides=4)
    p.add("jaw_icicles", head_xf(ic), "RH_Ice", "head")
    horns = [shard(0.075, 0.0125, sides=5, flat=0.25, bend=0.12 * s, seed=14 + s).aimed((s * 0.6, 1.0, -0.2), (s * 0.042, 0.037, -0.002)) for s in (-1, 1)]
    p.add("helm_horns", head_xf(merge(horns)), "RH_Ice", "head")


# ======================================================================================= cleaver
def cleaver(p: Piece):
    d = unit(TIP - GUARD)                                      # along the blade
    n_up = unit(np.array([0.0, 1.0, 0.0]) - d * d[1] + np.array([0.0, 0.0, -0.15]))   # back of the blade faces up/back
    # jagged top edge: five teeth
    top = [(0.0, 0.0), (0.03, 0.02), (0.12, 0.05)]
    top += [(0.17, 0.082), (0.175, 0.064), (0.215, 0.116), (0.222, 0.098), (0.26, 0.15), (0.268, 0.126), (0.30, 0.158), (0.312, 0.128), (0.332, 0.115)]
    poly = np.array(top + [(0.34, 0.06), (0.31, 0.02), (0.22, -0.02), (0.14, -0.03), (0.04, -0.04)])
    blade = g.extrude(poly, 0.026, 0.0065, 1).translated(0, 0, 0)
    M = frame_xf(GUARD, d, n_up)
    blade_w = blade.transformed(M)
    p.add("cleaver_blade", blade_w, "RH_Ice", "hand_R", lod1="keep", occluder=False)
    # inner frozen core (frosty slab visible through the translucent ice) + crack lines
    core_poly = np.array([(0.04, 0.0), (0.14, 0.03), (0.24, 0.06), (0.30, 0.07), (0.31, 0.03), (0.22, 0.0), (0.12, -0.012)])
    core = g.extrude(core_poly, 0.010, 0.002, 1).transformed(M)
    p.add("cleaver_core", core, "RH_Frost", "hand_R", occluder=False, lod1=None)
    # spine crystals along the back
    crystals = []
    for i, (u, ln) in enumerate(((0.07, 0.05), (0.16, 0.07), (0.25, 0.08), (0.31, 0.06))):
        pos = M[:3, :3] @ np.array([u, 0.06 + 0.07 * u, 0.0]) + GUARD
        dirv = unit(n_up + 0.3 * d * (i - 1.5) / 2)
        crystals.append((pos, dirv, ln, 0.0105))
    p.add("cleaver_crystals", spikes(crystals, seed=50, flat=0.3, sides=4, tip=0.5), "RH_Ice", "hand_R")
    # guard, handle (silver wire wrap), pommel
    guard = g.extrude(g.rect_poly(0.074, 0.030, 0.005, 1), 0.024, 0.005, 1)
    guard = guard.transformed(frame_xf(GUARD - d * 0.004, np.cross(d, n_up), d))
    p.add("cleaver_guard", guard, "RH_Obsidian", "hand_R")
    h_dir = unit(BUTT - GUARD)
    handle = g.tube([GUARD, BUTT], [0.0165, 0.0155], sides=7, samples=1, cap="flat", smooth=False, up=(0, 1, 0))
    p.add("cleaver_handle", handle, "RH_Armour", "hand_R", uv_scale=2)
    wraps = merge([g.torus(0.0175, 0.0034, 8, 3).aimed(h_dir, GUARD + (BUTT - GUARD) * u) for u in np.linspace(0.12, 0.88, 6)])
    p.add("cleaver_wire", wraps, "RH_Silver", "hand_R", lod1=None)
    pommel = g.superellipsoid((0.022, 0.020, 0.022), 0.6, 0.7, 4, 9).aimed(h_dir, BUTT + h_dir * 0.012)
    p.add("cleaver_pommel", pommel, "RH_Obsidian", "hand_R")


# ======================================================================================= clips
def make_clips() -> list[Clip]:
    idle = Clip("Idle", 3.4, loop=True)
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.0, (2.0, 0, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (1.0, (-2, 0, 4), "in_out_cubic"), (2.2, (-1, -3, 1), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.0, (3, 0, 0), "in_out_cubic"), (2.3, (-1.5, 0, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("arm_L", "rot", [(0, (0, 0, 0)), (2.2, (-4, 0, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("hand_L", "rot", [(0, (0, 0, 0)), (2.2, (-6, 0, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("body", "pos", [(0, (0, 0, 0)), (2.2, (0, -0.004, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])

    mv = Clip("Move", 0.9, loop=True)
    mv.keys("body", "rot", [(0, (8, 0, 4)), (0.45, (10, 0, -4), "in_out_cubic"), (0.9, (8, 0, 4), "in_out_cubic")])
    mv.keys("body", "pos", [(0, (0, 0, 0)), (0.2, (0, 0.015, 0), "out_quad"), (0.325, (0, 0, 0), "in_quad"), (0.65, (0, 0.015, 0), "out_quad"), (0.775, (0, 0, 0), "in_quad"), (0.9, (0, 0, 0))])
    mv.keys("spine", "rot", [(0, (4, 0, 0)), (0.45, (5, 0, 0), "in_out_cubic"), (0.9, (4, 0, 0), "in_out_cubic")])
    mv.keys("head", "rot", [(0, (0, 0, 0)), (0.45, (6, 0, 0), "in_out_cubic"), (0.9, (0, 0, 0), "in_out_cubic")])
    mv.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.45, (14, 0, 0), "in_out_cubic"), (0.9, (0, 0, 0), "in_out_cubic")])
    mv.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.45, (-4, 0, 0), "in_out_cubic"), (0.9, (0, 0, 0), "in_out_cubic")])
    mv.keys("top", "rot", [(0, (0, 0, 0)), (0.45, (-8, 0, 0), "in_out_cubic"), (0.9, (0, 0, 0), "in_out_cubic")])

    A = Clip("Attack", 2.1, fps=60)
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.30, (12, 0, 0), "in_out_cubic"), (0.80, (-14, 0, 0), "in_out_cubic"), (0.95, (24, 0, 0), "in_cubic"),
                           (1.10, (24, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.30, (0, 0, 0.12), "in_out_cubic"), (0.80, (0, -0.02, -0.10), "in_out_cubic"), (0.95, (0, 0, 0.28), "in_cubic"),
                           (0.98, (0, -0.025, 0.28), "out_quad"), (1.10, (0, -0.025, 0.28)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.80, (-12, 0, 0), "in_out_cubic"), (0.95, (18, 0, 0), "in_cubic"), (1.10, (18, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.30, (8, 0, 0), "in_out_cubic"), (0.80, (-6, 0, 0), "in_out_cubic"), (0.95, (10, 0, 0), "in_cubic"), (1.10, (10, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.30, (25, 0, 0), "in_out_cubic"), (0.80, (-88.7, 34.4, 0), "in_out_cubic"), (0.95, (-59.5, 28.5, 0), "in_cubic"), (1.10, (-59.5, 28.5, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0), "in_out_cubic"), (0.80, (-4.8, 0, 0), "in_out_cubic"), (0.95, (0.7, 0, 0), "in_cubic"), (1.10, (0.7, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.80, (-62.6, -41.7, -8.4), "in_out_cubic"), (0.95, (-33.7, -46, -16.6), "in_cubic"), (1.10, (-33.7, -46, -16.6)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_L", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.80, (-12.3, 0, 0), "in_out_cubic"), (0.95, (2.1, 0, 0), "in_cubic"), (1.10, (2.1, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.80, (10, 0, 0), "in_out_cubic"), (0.95, (-4, 0, 0), "in_cubic"), (1.10, (20, 0, 0), "out_quad"), (2.1, (0, 0, 0), "in_out_cubic")])

    hit = Clip("HitReact", 0.4)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.08, (-13, 0, 0), "out_cubic"), (0.40, (-5, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.08, (0, 0, -0.09), "out_cubic"), (0.40, (0, 0, -0.03), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.08, (-9, 0, 0), "out_cubic"), (0.40, (-4, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.08, (-16, 0, -10), "out_cubic"), (0.40, (-6, 0, -3), "in_out_cubic")])
    hit.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.08, (22, 0, 0), "out_cubic"), (0.40, (8, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.08, (16, 0, 0), "out_cubic"), (0.40, (5, 0, 0), "in_out_cubic")])

    vic = Clip("Victory", 1.5)
    vic.keys("spine", "rot", [(0, (0, 0, 0)), (0.6, (-12, 0, 0), "out_cubic"), (1.5, (-12, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.6, (-18, 0, 0), "out_cubic"), (1.5, (-18, 0, 0))])
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.6, (-130, 0, 0), "out_back"), (1.5, (-130, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.6, (-20, 0, 0), "out_cubic"), (1.5, (-20, 0, 0))])
    vic.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.6, (-100, 0, 0), "out_cubic"), (1.5, (-100, 0, 0))])
    vic.keys("body", "pos", [(0, (0, 0, 0)), (0.6, (0, 0.02, 0), "out_back"), (1.5, (0, 0.02, 0))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (0.6, (8, 0, 0), "out_cubic"), (1.5, (8, 0, 0))])
    T = Clip("Taunt", 1.5)           # cleaver scrape, then a hunched snarling lunge, ends at rest
    T.keys("body", "rot", [(0, (0, 0, 0)), (0.30, (-8, 0, 0), "in_out_cubic"), (0.62, (20, 0, 0), "in_cubic"), (1.0, (18, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "pos", [(0, (0, 0, 0)), (0.30, (0, -0.01, -0.05), "in_out_cubic"), (0.62, (0, -0.02, 0.16), "in_cubic"), (1.0, (0, -0.02, 0.16)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("spine", "rot", [(0, (0, 0, 0)), (0.30, (-8, 0, 0), "in_out_cubic"), (0.62, (14, 0, 0), "in_cubic"), (1.0, (12, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("head", "rot", [(0, (0, 0, 0)), (0.30, (-8, 0, 0), "in_out_cubic"), (0.62, (16, 0, 4), "in_cubic"), (0.78, (14, 6, -4), "in_out_quad"), (0.94, (16, -6, 4), "in_out_quad"), (1.1, (14, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.30, (30, 0, 0), "in_out_cubic"), (0.62, (22, 0, 0), "in_cubic"), (1.0, (26, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.62, (-30, 0, 0), "in_cubic"), (1.0, (-30, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.30, (10, 0, 0), "in_out_cubic"), (0.62, (-14, 0, 0), "in_cubic"), (0.9, (24, 0, 0), "out_quad"), (1.5, (0, 0, 0), "in_out_cubic")])
    return [idle, mv, A, hit, vic, T]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "pawn", rig, make_clips(), impact_time=0.95, strike_range=0.55, attack_style="melee", seed=5)
    rc.pedestal_parts(p)
    legs(p)
    torso(p)
    spine_spikes(p)
    arms(p)
    head(p)
    cleaver(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
