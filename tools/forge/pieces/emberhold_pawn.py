"""emberhold_pawn - Emberhold Shieldbearer (reference piece for the code forge).

A young highland levy in bronze half-plate: layered plate over a quilted gambeson, fur collar, a huge
dented round shield with a forge ring and one ember rune, a short sword on the right hip that the Attack draws.
Built from docs/art/emberhold_pawn.md.  Read this file as the worked example for tools/forge/README.md.
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
from rig import Clip, Rig             # noqa: E402

ASSET_ID = "emberhold_pawn"
FRONT_FLAT = 0.3696                   # octagon apothem (flats face +-Z, +-X)


# ======================================================================================= rig
def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.56, 0))
    r.add("spine", "body", (0, 0.62, 0))
    r.add("head", "spine", (0, 0.90, 0))
    r.add("top", "spine", (0, 0.86, -0.09))
    r.add("arm_L", "spine", (0.19, 0.86, 0))
    r.add("hand_L", "arm_L", (0.205, 0.77, 0.03))
    r.add("arm_R", "spine", (-0.185, 0.86, 0))
    r.add("hand_R", "arm_R", (-0.20, 0.76, 0))
    r.add("weapon", "hand_R", (-0.179, 0.487, 0.013))     # the short sword (centre of mass): lets Surrender drop it
    r.socket("socket_weapon_R", "hand_R", (-0.15, 0.64, 0.09))
    r.socket("socket_cast", "hand_L", (0.065, 0.80, 0.25))
    r.socket("socket_impact", "body", (-0.03, 0.62, 0.55))
    r.socket("socket_head", "head", (0, 1.04, 0))
    return r


# ======================================================================================= helpers
def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def mirror_x(pts):
    return [(-x, y, z) for x, y, z in pts]


def torus_axis(R, r, axis="z", segments=40, sides=8, arc=360.0):
    """Torus whose axis is X/Y/Z (centred on the origin)."""
    t = g.torus(R, r, segments, sides, arc=arc)
    if axis == "z":
        return t.rotated(90, 0, 0)
    if axis == "x":
        return t.rotated(0, 0, 90)
    return t


def ring_instances(base, count, radius, y, normal_tilt=0.0, scale=1.0, jitter=0.0, seed=0, start=0.0, z_scale=1.0):
    """Copies of `base` (modelled along +Y) around a ring, pointing outward (+tilt up)."""
    rng = np.random.default_rng(seed)
    th = start + np.arange(count) * TAU / count + (rng.random(count) - 0.5) * jitter
    pos = np.stack([radius * np.sin(th), np.full(count, y), radius * z_scale * np.cos(th)], 1)
    n = np.stack([np.sin(th) * math.cos(normal_tilt), np.full(count, math.sin(normal_tilt)), np.cos(th) * math.cos(normal_tilt)], 1)
    sc = scale * (1 + jitter * 2 * (rng.random(count) - 0.5))
    return g.instances(base, pos, n, sc, spins=rng.random(count) * 360)


# ---- torso ring family: one set of curves describes gambeson, cuirass, lames, belt so layers always nest
Y_LV = np.array([0.585, 0.62, 0.66, 0.70, 0.74, 0.78, 0.82, 0.855, 0.885])
HW = np.array([0.100, 0.102, 0.105, 0.110, 0.119, 0.126, 0.125, 0.112, 0.095]) * 0.93
ZF = np.array([0.080, 0.083, 0.087, 0.093, 0.102, 0.108, 0.104, 0.092, 0.075]) * 0.95
ZB = np.array([0.077, 0.078, 0.080, 0.085, 0.090, 0.094, 0.092, 0.082, 0.066]) * 0.95


def torso_ring(y, grow=0.0, K=48, ridge=0.0):
    hw = np.interp(y, Y_LV, HW) + grow
    zf = np.interp(y, Y_LV, ZF) + grow
    zb = np.interp(y, Y_LV, ZB) + grow
    th = np.linspace(0, TAU, K, endpoint=False)
    s, c = np.sin(th), np.cos(th)
    x = hw * np.sign(s) * np.abs(s) ** 0.9
    z = np.where(c > 0, zf * c, zb * c)
    z = z + ridge * np.exp(-(x / 0.02) ** 2) * (c > 0)
    return np.stack([x, np.full(K, y), z], 1)


def shell(specs, K=48, crease=45.0, cap_end=False, cap_start=False):
    """specs: [(y, grow, ridge)] bottom -> top; returns a closed-ring loft around the torso."""
    rings = np.stack([torso_ring(y, gr, K, rd) for y, gr, rd in specs])
    return g.loft(rings, closed=True, crease=crease, cap_end=cap_end, cap_start=cap_start)


def rolled_lip(y, grow, radius=0.0045, K=28):
    path = torso_ring(y, grow, K)
    return g.tube(path, radius, sides=4, samples=1, cap=None, smooth=False, closed=True, up=(0, 1, 0))


# ======================================================================================= pedestal
PED_PROFILE = [(0.392, 0.000), (0.400, 0.008), (0.400, 0.074), (0.386, 0.088), (0.372, 0.100),
               (0.372, 0.108), (0.360, 0.108), (0.360, 0.138), (0.372, 0.142), (0.372, 0.178), (0.352, 0.192),
               (0.352, 0.208), (0.340, 0.220), (0.000, 0.220)]


def pedestal(K=48):
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
    tier = pedestal()
    soot = lambda P: 0.55 + 0.45 * smoothstep(0.0, 0.2, P[:, 1])      # soot gradient toward the base
    p.add("ped_tiers", tier, "EH_Stone", "root", tint=soot)
    trim = g.lathe([(0.360, 0.110), (0.378, 0.112), (0.380, 0.122), (0.378, 0.134), (0.360, 0.136)], 32, crease=35)
    p.add("ped_trim", trim, "EH_Bronze", "root")
    riv = g.dome(0.0105, 0.009, 6, 1)
    th = np.arange(12) * TAU / 12 + TAU / 24
    pos = np.stack([0.381 * np.sin(th), np.full(12, 0.123), 0.381 * np.cos(th)], 1)
    p.add("ped_trim_rivets", g.instances(riv, pos, np.stack([np.sin(th), np.zeros(12), np.cos(th)], 1)), "EH_Bronze", "root", lod1=None)
    # broken ember cracks in the groove of the top plate (the only emissive on the plinth besides the sparse stone veins)
    arcs = []
    for a0, span in [(10, 30), (130, 40), (215, 24), (290, 34)]:
        arc = torus_axis(0.28, 0.0034, "y", max(4, span // 6), 3, arc=span)
        arcs.append(arc.rotated(0, a0, 0).scaled(1, 0.5, 1).translated(0, 0.2205, 0))
    p.add("ped_groove_embers", merge(arcs), "EH_EmberVein", "root", lod1="keep", bake=False)
    # emblem on tier 1's +Z flat: bronze frame + dark plaque + anvil inside six flames
    z0 = FRONT_FLAT
    cx, cy = 0.0, 0.044
    plaque = g.lathe([(0, 0), (0.044, 0), (0.044, 0.004), (0, 0.0045)], 20).rotated(90, 0, 0).translated(cx, cy, z0)
    p.add("ped_emblem_plaque", plaque, "EH_Steel", "root", lod1="keep")
    frame = g.torus(0.047, 0.0035, 20, 5).rotated(90, 0, 0).translated(cx, cy, z0 + 0.004)
    anvil_poly = np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 0.78
    relief = [g.extrude(anvil_poly, 0.005, 0.0, 1).translated(cx, cy - 0.002, z0 + 0.0065)]
    fl = g.teardrop(0.016, 0.010, 8)
    for i in range(6):
        a = i * 60
        m = g.extrude(fl, 0.005, 0.0, 1)
        m = m.rotated(0, 0, a)                               # point outward from +Y by `a`
        d = np.array([-math.sin(math.radians(a)), math.cos(math.radians(a))]) * 0.027
        relief.append(m.translated(cx + d[0], cy + d[1], z0 + 0.0065))
    p.add("ped_emblem", merge(relief + [frame]), "EH_Bronze", "root", lod1="keep")


# ======================================================================================= lower body
def legs(p: Piece):
    for side, name in ((+1, "L"), (-1, "R")):
        kz = 0.045 if side > 0 else 0.0        # left knee advanced a little: weight on the right leg
        path = [(0.075, 0.27, 0.02), (0.078, 0.34, 0.01), (0.080, 0.43, 0.02 + kz), (0.074, 0.51, 0.0), (0.070, 0.58, 0.0)]
        path = [(side * x, y, z) for x, y, z in path]
        leg = g.tube(path, [0.034, 0.040, 0.046, 0.056, 0.060], sides=8, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"leg_{name}", leg, "EH_Cloth", "body", uv_scale=2)
        # boot: shaft + foot + toecap
        shaft = g.tube([(side * 0.075, 0.30, 0.012), (side * 0.075, 0.262, 0.016)], [0.039, 0.043], sides=8, samples=1, cap=None, smooth=False)
        foot = g.superellipsoid((0.051, 0.030, 0.100), 0.55, 0.65, 6, 12).translated(side * 0.075, 0.252, 0.040)
        sole = g.superellipsoid((0.054, 0.012, 0.106), 0.35, 0.5, 3, 10).translated(side * 0.075, 0.226, 0.040)
        toe = g.superellipsoid((0.040, 0.024, 0.036), 0.5, 0.6, 4, 9).translated(side * 0.075, 0.256, 0.104)
        p.add(f"boot_{name}", merge([shaft, foot]), "EH_Leather", "body", uv_scale=2)
        p.add(f"boot_sole_{name}", sole, "EH_Steel", "body", lod1=None)
        p.add(f"boot_toe_{name}", toe, "EH_Bronze", "body")
        greave = g.tube([(side * 0.076, 0.285, 0.048 + kz * 0.5), (side * 0.080, 0.36, 0.05 + kz * 0.8), (side * 0.080, 0.425, 0.052 + kz)],
                        [0.040, 0.044, 0.050], sides=8, samples=2, cap=None, up=(0, 0, 1))
        greave = greave.noised(0.0025, 38, 2, seed=3 + side)
        p.add(f"greave_{name}", greave, "EH_Bronze", "body")
        knee = g.superellipsoid((0.040, 0.033, 0.027), 0.6, 0.6, 5, 10).translated(side * 0.080, 0.438, 0.066 + kz)
        p.add(f"knee_{name}", knee, "EH_Bronze", "body")
        # greave rolled lips
        for y, k in ((0.288, 0), (0.425, 1)):
            ring = g.torus(0.043 + 0.006 * k, 0.0042, 14, 4).translated(side * (0.076 + 0.004 * k), y, 0.048 + kz * (0.5 + 0.5 * k))
            p.add(f"greave_lip_{name}{k}", ring, "EH_Bronze", "body", lod1=None)


def skirt_belt(p: Piece):
    # quilted skirt: folded lathe
    prof = g.spline(np.array([(0.100, 0.595), (0.116, 0.54), (0.128, 0.49), (0.136, 0.45), (0.134, 0.438)]), 1)
    folds = 7

    def fold(th, v):
        return 1 + (0.012 + 0.048 * v ** 1.5)[:, None] * np.cos(folds * th)[None, :] + 0.0
    sk = g.lathe(prof, 28, shape_v=fold, crease=75)
    sk = sk.scaled(1, 1, 0.9).noised(0.004, 14, 2, seed=5)
    hem = lambda P: np.clip(0.4 + 0.6 * smoothstep(0.43, 0.54, P[:, 1]), 0, 1)       # soot toward the hem
    p.add("skirt", sk, "EH_Cloth", "body", uv_scale=2, tint=hem)
    # tasset plates: overlapping bronze lames hanging from the belt
    parts = []
    for i in range(5):
        th = (i + 0.5) * TAU / 5 + 0.0
        pl = g.plate(0.135, 0.082, 0.010, 0.0045, bend_r=0.12, inner_x=1, taper=lambda t: 1 - 0.18 * (t + 1) / 2, drop_back=True)
        pl = pl.rotated(-14, 0, 0).translated(0, 0.50, 0.118)
        parts.append(pl.rotated(0, math.degrees(th), 0))
    p.add("tassets", merge(parts), "EH_Bronze", "body")
    # belt + buckle + pouch
    belt = shell([(0.585, 0.003, 0), (0.589, 0.012, 0), (0.62, 0.012, 0), (0.625, 0.003, 0)], 32, 60)
    p.add("belt", belt, "EH_Leather", "body", uv_scale=2)
    buckle = g.extrude(g.rect_poly(0.040, 0.032, 0.004, 1), 0.010, 0.003, 1).translated(0, 0.604, 0.098)
    p.add("buckle", buckle, "EH_Bronze", "body")
    rv = g.dome(0.006, 0.005, 6, 1)
    p.add("belt_studs", g.instances(rv, [(x, 0.605, 0.0955) for x in np.linspace(-0.09, 0.09, 7)] , [(0, 0, 1)] * 7), "EH_Bronze", "body", lod1=None)
    pouch = g.superellipsoid((0.028, 0.030, 0.018), 0.45, 0.5, 4, 9).translated(0.066, 0.560, 0.108).rotated(0, 0, 0)
    p.add("pouch", merge([pouch]), "EH_Leather", "body", uv_scale=2)


# ======================================================================================= torso
def torso(p: Piece):
    gam = shell([(0.585, -0.014, 0), (0.64, -0.014, 0), (0.78, -0.012, 0), (0.887, -0.014, 0)], 28, 60)
    p.add("gambeson", gam, "EH_Cloth", "spine", uv_scale=2, bake=True)
    # waist lames (three overlapping bands, each lower one proud of the one above)
    for i, (y0, y1) in enumerate(((0.625, 0.662), (0.650, 0.688), (0.676, 0.714))):
        gr = 0.004 + 0.003 * (2 - i)
        lame = shell([(y0, gr - 0.004, 0), (y0 + 0.005, gr + 0.004, 0), (y1 - 0.006, gr + 0.005, 0), (y1, gr - 0.003, 0)], 24, 55)
        p.add(f"lame_{i}", lame, "EH_Bronze", "spine")
        rv = g.dome(0.0065, 0.005, 6, 1)
        ths = np.linspace(-1.1, 1.1, 7)
        pos = []
        nrm = []
        for t in ths:
            rr = torso_ring(y0 + (y1 - y0) * 0.5, gr + 0.005, 400)
            k = int(((math.degrees(t) % 360) / 360) * 400)
            pos.append(rr[k])
            nrm.append((math.sin(t), 0, math.cos(t)))
        p.add(f"lame_rivets_{i}", g.instances(rv, pos, nrm), "EH_Bronze", "spine", lod1=None)
    # cuirass with central ridge
    ridge = lambda y: 0.012 * smoothstep(0.70, 0.76, y) * (1 - smoothstep(0.83, 0.887, y))
    ys = [0.700, 0.708, 0.74, 0.78, 0.82, 0.862, 0.887]
    gr = [-0.001, 0.006, 0.008, 0.008, 0.008, 0.0065, 0.0]
    cuirass = g.loft(np.stack([torso_ring(y, a, 40, ridge(y)) for y, a in zip(ys, gr)]), closed=True, crease=50)
    cuirass = cuirass.dented(5, 0.03, 0.0022, seed=9)
    p.add("cuirass", cuirass, "EH_Bronze", "spine")
    p.add("cuirass_lip_lo", rolled_lip(0.702, 0.0095, 0.0045, 28), "EH_Bronze", "spine", lod1=None)
    # chest strap + studs (leather) - an asymmetric baldric from left shoulder to right hip
    sp = [(0.075, 0.886, 0.02), (0.045, 0.82, 0.098), (-0.0, 0.775, 0.118), (-0.06, 0.725, 0.112), (-0.108, 0.665, 0.10)]
    strap = g.tube(sp, 0.0105, sides=5, samples=2, cap=None, ellipse=(1.0, 0.45), up=(0, 0, 1))
    p.add("baldric", strap, "EH_Leather", "spine", lod1=None, uv_scale=2)
    p.add("baldric_studs", g.instances(g.dome(0.0055, 0.0045, 6, 1), g.spline(np.array(sp), 2)[3:-3:3] + [0, 0, 0.0095],
                                       [(0, 0, 1)] * len(g.spline(np.array(sp), 2)[3:-3:3])), "EH_Bronze", "spine", lod1=None)
    # tabard flap (soft: spine -> body) with bronze hem trim
    tab = g.cloth_panel(0.13, 0.215, cols=7, rows=6, fold_amp=0.006, folds=3, flare=0.35, curve=40, seed=4, thickness=0.004)
    tab = tab.rotated(-9, 0, 0).translated(0, 0.628, 0.118)
    hemf = lambda P: np.clip(0.45 + 0.55 * smoothstep(0.41, 0.55, P[:, 1]), 0, 1)
    p.add("tabard", tab, "EH_Cloth", "spine", bone2="body", blend=(0.60, 0.46), uv_scale=2, tint=hemf)
    trim = g.tube([(-0.0875, 0.408, 0.152), (0.0, 0.397, 0.160), (0.0875, 0.408, 0.152)],
                  0.0065, sides=5, samples=2, cap="round", cap_steps=1)
    p.add("tabard_trim", trim.rotated(-9, 0, 0, pivot=(0, 0.628, 0.118)), "EH_Bronze", "body", lod1=None)


def collar_and_neck(p: Piece):
    neck = g.tube([(0, 0.868, 0.0), (0, 0.918, 0.006)], [0.034, 0.030], sides=8, samples=1, cap=None, smooth=False)
    p.add("neck", neck, "EH_Skin", "head", uv_scale=2)
    # fur collar: base ring + tufts (outer row sweeps out/down, inner row stands up around the neck)
    path = torso_ring(0.882, 0.014, 20)
    ring = g.tube(path * [1.0, 1.0, 1.0], 0.032, sides=7, samples=1, cap=None, smooth=False, closed=True, up=(0, 1, 0))
    ring = ring.noised(0.010, 20, 3, seed=11)
    p.add("fur_collar", ring, "EH_Fur", "spine", uv_scale=2)
    tuft = g.tube([(0, 0, 0), (0.003, 0.016, 0.004), (0.007, 0.028, 0.013)], [0.0125, 0.0075, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    outer = ring_instances(tuft, 20, 0.104, 0.874, normal_tilt=-0.75, scale=1.1, jitter=0.5, seed=1)
    outer2 = ring_instances(tuft, 16, 0.092, 0.905, normal_tilt=0.35, scale=0.9, jitter=0.5, seed=2, start=0.1)
    outer3 = ring_instances(tuft, 6, 0.068, 0.912, normal_tilt=1.0, scale=0.7, jitter=0.5, seed=3, start=0.2)
    p.add("fur_tufts", merge([outer, outer2, outer3]).transformed(np.diag([1, 1, 0.92, 1])), "EH_Fur", "spine", uv_scale=2)


# ======================================================================================= arms, shield, sword
def pauldron(sign, big=True, dent=False):
    """Articulated pauldron: a low domed cap over telescoping partial hoops (lames) around the upper-arm axis.
    Each lame is a little larger than the one above and rolled at the lip, so the layers read from far away."""
    c = np.array([sign * (0.190 if big else 0.178), 0.866 if big else 0.862, 0.0])
    axis = unit([sign * 0.015, -0.085, 0.03])
    tilt = math.degrees(math.atan2(axis[0], -axis[1]))
    parts = []
    r0 = 0.057 if big else 0.046
    n = 3 if big else 2
    h = 0.030 if big else 0.026
    for i in range(n):
        r = r0 + 0.0075 * i
        y = -0.012 - i * 0.025
        prof = np.array([(r - 0.003, h / 2), (r + 0.0035, h / 2 - 0.002), (r + 0.0075, h / 2 - 0.006), (r + 0.0095, 0),
                         (r + 0.0085, -h / 2 + 0.003), (r + 0.0105, -h / 2 - 0.001), (r + 0.004, -h / 2 - 0.004), (r - 0.003, -h / 2),
                         (r - 0.003, h / 2)])
        lam = g.lathe(prof, 15, sweep=250, start=-125, crease=45)
        parts.append(lam.rotated(0, 90 if sign > 0 else 270, 0).translated(0, y, 0))
    rc = r0 + 0.004
    cap = g.superellipsoid((rc, 0.026 if big else 0.022, rc * 1.04), 0.65, 0.9, 5, 12)
    cap = g.warp(cap, lambda P: np.column_stack([P[:, 0], np.where(P[:, 1] < 0, P[:, 1] * 0.2, P[:, 1]), P[:, 2]]), 60)
    cap = cap.translated(0, 0.010, 0)
    if dent:
        cap = cap.dented(4, 0.026, 0.005, seed=21)
    parts.append(cap.noised(0.0012, 36, 2, seed=4 + int(sign)))
    m = merge(parts)
    return m.rotated(0, 0, -sign * tilt * 0.8).translated(*c)


def arms(p: Piece):
    # ---------------- left arm (shield arm), bones arm_L / hand_L
    up_L = g.tube([(0.190, 0.855, 0.0), (0.198, 0.815, 0.015), (0.205, 0.775, 0.03)], [0.037, 0.037, 0.032], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
    p.add("arm_L_sleeve", up_L, "EH_Cloth", "arm_L", uv_scale=2)
    p.add("pauldron_L", pauldron(+1, True), "EH_Bronze", "arm_L")
    fore_path = [(0.205, 0.775, 0.03), (0.172, 0.727, 0.118), (0.108, 0.689, 0.186)]
    fore_L = g.tube(fore_path, [0.034, 0.030, 0.026], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 1, 0))
    p.add("forearm_L_sleeve", fore_L, "EH_Cloth", "hand_L", uv_scale=2)
    vamb = g.tube([(0.188, 0.748, 0.074), (0.150, 0.712, 0.140), (0.108, 0.689, 0.186)], [0.0385, 0.0335, 0.0295], sides=8, samples=2, cap="flat", up=(0, 1, 0)).noised(0.002, 40, 2, seed=8)
    p.add("vambrace_L", vamb, "EH_Bronze", "hand_L")
    cuff = g.tube([(0.128, 0.700, 0.168), (0.112, 0.690, 0.184)], [0.034, 0.033], sides=8, samples=1, cap="flat", smooth=False, up=(0, 1, 0))
    p.add("cuff_L", cuff, "EH_Leather", "hand_L", uv_scale=2)
    fist = g.superellipsoid((0.025, 0.021, 0.032), 0.6, 0.7, 5, 10).rotated(0, 0, 8).translated(0.095, 0.682, 0.196)
    thumb = g.tube([(0.082, 0.698, 0.206), (0.072, 0.693, 0.192)], [0.0085, 0.007], sides=5, samples=1, cap="round", cap_steps=1, smooth=False)
    knuckles = g.instances(g.dome(0.0055, 0.0045, 6, 1), [(0.085 + 0.0, 0.686 + dy, 0.2255) for dy in (-0.014, -0.005, 0.005, 0.014)], [(0, 0.0, 1)] * 4)
    p.add("hand_L", merge([fist, thumb, knuckles]), "EH_Leather", "hand_L", uv_scale=2)
    # ---------------- right arm (sword arm), bones arm_R / hand_R
    up_R = g.tube([(-0.185, 0.855, 0.0), (-0.192, 0.81, 0.0), (-0.200, 0.765, 0.0)], [0.036, 0.036, 0.031], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
    p.add("arm_R_sleeve", up_R, "EH_Cloth", "arm_R", uv_scale=2)
    p.add("pauldron_R", pauldron(-1, False, dent=True), "EH_Bronze", "arm_R")
    fore_R = g.tube([(-0.200, 0.765, 0.0), (-0.190, 0.690, 0.048), (-0.168, 0.630, 0.092)], [0.033, 0.029, 0.025], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 1, 0))
    p.add("forearm_R_sleeve", fore_R, "EH_Cloth", "hand_R", uv_scale=2)
    vamb_r = g.tube([(-0.196, 0.730, 0.025), (-0.186, 0.676, 0.056), (-0.170, 0.640, 0.084)], [0.0365, 0.0325, 0.0285], sides=8, samples=2, cap="flat", up=(0, 1, 0)).noised(0.002, 40, 2, seed=14)
    p.add("vambrace_R", vamb_r, "EH_Leather", "hand_R", uv_scale=2)
    cuff_r = g.tube([(-0.178, 0.653, 0.076), (-0.168, 0.634, 0.090)], [0.032, 0.031], sides=8, samples=1, cap="flat", smooth=False, up=(0, 1, 0))
    p.add("cuff_R", cuff_r, "EH_Bronze", "hand_R")
    hand_r = g.superellipsoid((0.024, 0.022, 0.030), 0.6, 0.7, 5, 10).rotated(-10, 0, -8).translated(-0.160, 0.619, 0.099)
    fing = g.instances(g.dome(0.0055, 0.0045, 6, 1), [(-0.150, 0.610 + dy, 0.118 - 0.0) for dy in (-0.012, -0.004, 0.004, 0.012)], [(0.2, 0, 1)] * 4)
    p.add("hand_R", merge([hand_r, fing]), "EH_Leather", "hand_R", uv_scale=2)


SHIELD_C = np.array([0.065, 0.68, 0.20])
SHIELD_ROT = (-6, 10, 0)


def shield_xf(m):
    """Local shield space (face toward +Z, centre at origin) -> world rest pose."""
    return m.rotated(*SHIELD_ROT).translated(*SHIELD_C)


def shield(p: Piece):
    prof = [(0, -0.008), (0.100, -0.010), (0.196, -0.008), (0.210, 0.0), (0.205, 0.020), (0.180, 0.014), (0.150, 0.0125), (0.105, 0.014),
            (0.066, 0.020), (0.055, 0.032), (0.046, 0.040), (0.030, 0.0455), (0.0, 0.047)]
    disc = g.lathe(np.array(prof), 28, crease=55).uv_box(0.25).rotated(90, 0, 0)
    disc = disc.noised(0.0016, 30, 2, seed=2).dented(5, 0.04, 0.0055, seed=7, region=lambda P: np.hypot(P[:, 0], P[:, 1]) > 0.07)
    p.add("shield_disc", shield_xf(disc), "EH_Bronze", "hand_L")
    # oxblood painted band between boss and forge ring (cloth inlay) - gives value/hue contrast to the bronze mass
    band = g.lathe([(0.082, 0.0125), (0.138, 0.0135), (0.136, 0.0172), (0.084, 0.0165)], 32, crease=60).rotated(90, 0, 0)
    p.add("shield_paint", shield_xf(band), "EH_Cloth", "hand_L", uv_scale=2, lod1=None)
    ring = torus_axis(0.150, 0.0095, "z", 28, 5).translated(0, 0, 0.0195)
    lugs = []
    fl = g.teardrop(0.034, 0.020, 8)
    for i in range(6):
        a = i * 60 + 30
        m = g.extrude(fl, 0.010, 0.0, 1).rotated(0, 0, a)
        d = np.array([-math.sin(math.radians(a)), math.cos(math.radians(a))]) * 0.158
        lugs.append(m.translated(d[0], d[1], 0.022))
    p.add("shield_forge_ring", shield_xf(merge([ring] + lugs)), "EH_Steel", "hand_L")
    rim = torus_axis(0.204, 0.0105, "z", 32, 5).translated(0, 0, 0.0115)
    p.add("shield_rim", shield_xf(rim.noised(0.0016, 25, 2, seed=5)), "EH_Bronze", "hand_L")
    # radial steel straps with rivets
    straps = []
    for i in range(4):
        a = 45 + i * 90
        bar = g.extrude(g.rect_poly(0.021, 0.060), 0.0075, 0.0025, 1).translated(0, 0.1075, 0.0165)
        straps.append(bar.rotated(0, 0, a))
    p.add("shield_straps", shield_xf(merge(straps)), "EH_Steel", "hand_L")
    rv = g.dome(0.0100, 0.0085, 6, 1)
    pos, nrm = [], []
    for i in range(12):
        a = i * 30 + 15
        pos.append((0.172 * math.sin(math.radians(a)), 0.172 * math.cos(math.radians(a)), 0.0125))
        nrm.append((0, 0, 1))
    for i in range(4):
        a = 45 + i * 90
        for rr in (0.108, 0.135):
            pos.append((rr * math.sin(math.radians(a)), rr * math.cos(math.radians(a)), 0.0185))
            nrm.append((0, 0, 1))
    p.add("shield_rivets", shield_xf(g.instances(rv.rotated(90, 0, 0), pos, nrm)), "EH_Bronze", "hand_L", lod1=None)
    # focal ember rune on the boss
    rune = g.extrude(g.ngon(6, 0.0155, 0), 0.0075, 0.002, 1).translated(0, 0, 0.0505)
    rune2 = g.extrude(np.array([(-.004, -.010), (.004, -.010), (.004, .010), (-.004, .010)]), 0.003, 0.0006, 1).translated(0, 0, 0.0558)
    p.add("shield_ember_rune", shield_xf(merge([rune, rune2])), "EH_Ember", "hand_L", lod1="keep", bake=False)


def sword(p: Piece):
    mouth = np.array([-0.165, 0.585, 0.06])
    tip = np.array([-0.206, 0.30, -0.075])
    a_s = unit(tip - mouth)               # blade direction (down/back along the scabbard)
    h_dir = -a_s                          # hilt direction (up/forward)
    # scabbard on the body bone
    sc = g.tube([mouth, (-0.188, 0.425, -0.010), tip], [0.0215, 0.0225, 0.0155], sides=8, samples=2, cap="round", cap_steps=1, ellipse=(1.0, 0.78), up=(0, 0, 1))
    p.add("scabbard", sc, "EH_Leather", "body", uv_scale=2)
    # orient ring so its axis follows the scabbard
    def along(mesh, pos, d=a_s):
        return mesh.aimed(d, pos)
    locket = along(g.torus(0.0225, 0.0058, 10, 4).scaled(1, 1, 0.82), mouth - a_s * 0.012)
    band2 = along(g.torus(0.0235, 0.0042, 10, 3).scaled(1, 1, 0.82), mouth + a_s * 0.075)
    chape = g.superellipsoid((0.0185, 0.034, 0.0155), 0.5, 0.7, 4, 10)
    chape = along(chape, tip + h_dir * 0.018, a_s * -1).rotated(0, 0, 0)
    p.add("scabbard_fittings", merge([locket, band2, chape]), "EH_Bronze", "body")
    # hilt: grip + guard + pommel, on hand_R
    grip_end = mouth + h_dir * 0.066
    grip = g.tube([mouth + h_dir * 0.004, grip_end], 0.0118, sides=7, samples=1, cap="flat", smooth=False, up=(0, 0, 1))
    wraps = g.instances(g.torus(0.0125, 0.0022, 10, 4), [mouth + h_dir * (0.020 + 0.024 * i) for i in range(2)], [h_dir] * 2)
    p.add("sword_grip", merge([grip, wraps]), "EH_Leather", "weapon", lod1="keep", uv_scale=2)
    guard = g.extrude(g.rect_poly(0.108, 0.014, 0.005, 1), 0.022, 0.004, 1).rotated(90, 0, 0)
    guard = guard.aimed(h_dir, mouth + h_dir * 0.002)
    guard = guard.rotated_axis(h_dir, 78, pivot=mouth)
    pommel = g.superellipsoid((0.0185, 0.015, 0.0185), 0.6, 0.8, 4, 10).aimed(h_dir, grip_end + h_dir * 0.010)
    p.add("sword_guard_pommel", merge([guard, pommel]), "EH_Bronze", "weapon", lod1="keep")
    blade = g.blade(0.30, 0.044, 0.0085, tip=0.28, taper=0.7, fuller=0.0018, rows=3)
    blade = blade.aimed(a_s, mouth + h_dir * 0.0)
    p.add("sword_blade", blade, "EH_Steel", "weapon", lod1="keep", occluder=False)


def bedroll_and_mantle(p: Piece):
    roll = g.cylinder(0.037, 0.200, 11, bevel=0.007, bevel_segments=1, y0=-0.1).rotated(0, 0, 90).translated(0, 0.800, -0.128)
    roll = roll.noised(0.003, 26, 2, seed=12)
    p.add("bedroll", roll, "EH_Cloth", "top", uv_scale=2)
    straps = [torus_axis(0.0385, 0.0062, "x", 10, 4).translated(x, 0.800, -0.128) for x in (-0.062, 0.062)]
    p.add("bedroll_straps", merge(straps), "EH_Leather", "top", lod1=None, uv_scale=2)
    # left-only fur pelt draped behind the shoulder: staggered rows of hanging tufts (no flat panel)
    tuft = g.tube([(0, 0, 0), (0.002, -0.014, 0.001), (0.004, -0.028, 0.005)], [0.0135, 0.0085, 0.0], sides=4, samples=1, cap=None,
                  smooth=False, up=(0, 0, 1))
    pos, nrm = [], []
    rng = np.random.default_rng(31)
    for row, (y, n_, x0, dx) in enumerate(((0.866, 5, 0.03, 0.036), (0.828, 5, 0.022, 0.037), (0.790, 4, 0.04, 0.036), (0.752, 3, 0.055, 0.036))):
        for i in range(n_):
            pos.append((x0 + dx * i + rng.normal(0, 0.003), y, -0.100 - 0.012 * row * 0.3))
            nrm.append((0.1, -1, -0.15))
    p.add("mantle_pelt", g.instances(tuft.rotated(180, 0, 0), pos, nrm, 1.25, spins=rng.random(len(pos)) * 360), "EH_Fur", "top", uv_scale=2)
    pelt_base = g.superellipsoid((0.095, 0.052, 0.020), 0.7, 0.8, 5, 12).noised(0.006, 24, 2, seed=9).translated(0.105, 0.846, -0.106)
    p.add("mantle_pelt_base", pelt_base, "EH_Fur", "top", uv_scale=2)


# ======================================================================================= head
def head(p: Piece):
    skull = g.superellipsoid((0.0475, 0.0575, 0.054), 0.85, 0.92, 7, 14).translated(0, 0.952, 0.006)
    skull = g.warp(skull, lambda P: np.column_stack([P[:, 0] * (1 - 0.18 * smoothstep(0.955, 0.895, P[:, 1])), P[:, 1], P[:, 2]]), 70)
    nose = g.superellipsoid((0.007, 0.012, 0.011), 0.6, 0.6, 3, 6).rotated(-20, 0, 0).translated(0, 0.944, 0.0585)
    brow = g.rounded_box((0.086, 0.011, 0.028), 0.0045, 1).translated(0, 0.967, 0.044)
    brow = g.warp(brow, lambda P: np.column_stack([P[:, 0], P[:, 1] + 0.004 * (np.abs(P[:, 0]) / 0.043) ** 2 * -1, P[:, 2] - 0.012 * (np.abs(P[:, 0]) / 0.043) ** 2]), 60)
    chin = g.superellipsoid((0.020, 0.012, 0.020), 0.6, 0.6, 3, 8).translated(0, 0.902, 0.042)
    ears = [g.superellipsoid((0.006, 0.014, 0.011), 0.6, 0.6, 3, 6).translated(s * 0.0485, 0.948, 0.002) for s in (-1, 1)]
    p.add("head", merge([skull, nose, brow, chin] + ears), "EH_Skin", "head", uv_scale=2)
    eyes = [g.superellipsoid((0.0058, 0.0042, 0.003), 0.7, 0.7, 3, 6).translated(s * 0.0185, 0.9565, 0.0535) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "EH_Steel", "head", lod1=None)
    # helm dome
    prof = np.array([(0.058, 0.926), (0.0625, 0.940), (0.0645, 0.966), (0.0585, 0.996), (0.043, 1.014), (0.018, 1.022), (0.0, 1.0245)])
    dome = g.lathe(g.spline(prof, 1), 20, crease=55).uv_box(0.25).noised(0.0016, 40, 2, seed=2)
    dome = g.warp(dome, lambda P: np.column_stack([P[:, 0] * 0.97, P[:, 1], P[:, 2] * 1.04 - 0.002]), 55)
    p.add("helm_dome", dome, "EH_Bronze", "head")
    band = g.torus(0.0625, 0.0052, 20, 4).scaled(0.98, 1.0, 1.06).translated(0, 0.939, -0.002)
    p.add("helm_band", band, "EH_Bronze", "head")
    rv = g.dome(0.0042, 0.0036, 6, 1)
    pos, nrm = [], []
    for i in range(9):
        a = math.radians(-80 + i * 20)
        pos.append((0.0625 * math.sin(a) * 0.98, 0.939, 0.0625 * math.cos(a) * 1.06 - 0.002 + 0.0))
        nrm.append((math.sin(a), 0, math.cos(a)))
    p.add("helm_rivets", g.instances(rv, pos, nrm), "EH_Bronze", "head", lod1=None)
    nasal = g.extrude(np.array([(-0.0075, 0.918), (0.0075, 0.918), (0.0062, 0.995), (-0.0062, 0.995)]), 0.0065, 0.0016, 1).translated(0, 0, 0.0585)
    nasal = nasal.rotated(-8, 0, 0, pivot=(0, 0.995, 0.06))
    p.add("helm_nasal", nasal, "EH_Steel", "head")
    for s, nm in ((1, "L"), (-1, "R")):
        cheek = g.extrude_plane(np.array([(0.930, -0.030), (0.926, 0.030), (0.962, 0.040), (0.986, 0.026), (0.984, -0.026), (0.966, -0.036)]),
                                0.0075, "YZ", bevel=0.0015, bevel_segments=1)
        cheek = cheek.translated(s * 0.0555, 0, 0)
        p.add(f"cheek_guard_{nm}", cheek, "EH_Steel", "head")
    # crest fin (silhouette part): sail rising to the tallest point 1.05
    top = g.spline(np.array([(0.990, -0.064), (1.014, -0.052), (1.038, -0.030), (1.050, -0.002), (1.046, 0.024), (1.030, 0.046), (1.010, 0.058)]), 3)
    bot = np.array([(1.0045, 0.052), (1.014, 0.030), (1.020, 0.004), (1.016, -0.024), (1.002, -0.050)])
    fin = g.extrude_plane(np.vstack([top, bot]), 0.016, "YZ", bevel=0.0045, bevel_segments=1).noised(0.0012, 40, 1, seed=15)
    p.add("helm_crest", fin, "EH_Bronze", "head", lod1="keep")
    p.add("helm_crest_rivets", g.instances(g.dome(0.0045, 0.004, 6, 1), [(0.0085, 1.028, z) for z in (-0.034, -0.008, 0.018)], [(1, 0, 0)] * 3), "EH_Bronze", "head", lod1=None)


# ======================================================================================= clips
def make_clips(rig=None) -> list[Clip]:
    hilt_dir = unit(-(np.array([-0.206, 0.30, -0.075]) - np.array([-0.165, 0.585, 0.06])))

    idle = Clip("Idle", 3.0, loop=True)
    idle.hold("body", "pos", (0, 0, 0))
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.5, (1.6, 0, 0), "in_out_cubic"), (3.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (1.5, (-1.0, 1.2, 0), "in_out_cubic"), (3.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("body", "pos", [(0, (0, 0, 0)), (1.5, (0, 0.004, 0), "in_out_cubic"), (3.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("arm_L", "rot", [(0, (0, 0, 0)), (1.5, (-1.5, 0, 0), "in_out_cubic"), (3.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.65, (2.5, 0, 0), "in_out_cubic"), (3.0, (0, 0, 0), "in_out_cubic")])

    move = Clip("Move", 0.8, loop=True)
    move.keys("body", "rot", [(0, (6, 0, 3)), (0.2, (6, 0, 0), "in_out_cubic"), (0.4, (6, 0, -3), "in_out_cubic"), (0.6, (6, 0, 0), "in_out_cubic"), (0.8, (6, 0, 3), "in_out_cubic")])
    move.keys("body", "pos", [(0, (0, 0, 0)), (0.2, (0, 0.02, 0), "out_quad"), (0.4, (0, 0, 0), "in_quad"), (0.6, (0, 0.02, 0), "out_quad"), (0.8, (0, 0, 0), "in_quad")])
    move.keys("arm_R", "rot", [(0, (10, 0, 0)), (0.4, (-10, 0, 0), "in_out_cubic"), (0.8, (10, 0, 0), "in_out_cubic")])
    move.keys("arm_L", "rot", [(0, (-4, 0, 0)), (0.4, (-8, 0, 0), "in_out_cubic"), (0.8, (-4, 0, 0), "in_out_cubic")])
    move.keys("top", "rot", [(0, (0, 0, 0)), (0.4, (-6, 0, 0), "in_out_cubic"), (0.8, (0, 0, 0), "in_out_cubic")])

    # ---- Attack: draw (0-.30), shield bash (.30-.55), wind-up (.55-.82), strike (.82-.95 impact), recover
    A = Clip("Attack", 2.0, loop=False, fps=60)
    draw = tuple(hilt_dir * 0.30)
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.30, (3, 0, 0), "in_out_cubic"), (0.55, (8, 0, 0), "out_back"), (0.82, (-8, 0, 0), "in_out_cubic"),
                          (0.95, (16, 0, 0), "in_cubic"), (1.10, (16, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.55, (0, 0, 0.15), "out_back"), (0.82, (0, 0, 0.05), "in_out_cubic"),
                          (0.95, (0, 0, 0.28), "in_cubic"), (0.98, (0, -0.02, 0.28), "out_quad"), (1.10, (0, -0.02, 0.28), "in_out_cubic"), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.55, (0, 0, 0)), (0.82, (-6, 0, 0), "in_out_cubic"), (0.95, (14, 0, 0), "in_cubic"), (1.10, (14, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.55, (0, 0, 0)), (0.82, (-4, 0, 0), "in_out_cubic"), (0.95, (6, 0, 0), "in_cubic"), (1.10, (6, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.30, (-40, 0, 0), "in_out_cubic"), (0.55, (-60, 0, -8), "in_out_cubic"), (0.82, (-165, 0, 0), "in_out_cubic"),
                          (0.95, (-75, 0, 0), "in_cubic"), (1.10, (-75, 0, 0)), (2.0, (-20, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.30, (-70, 0, 0), "in_out_cubic"), (0.55, (-50, 0, 0), "in_out_cubic"), (0.82, (-35, 0, 0), "in_out_cubic"),
                           (0.95, (-5, 0, 0), "in_cubic"), (1.10, (-5, 0, 0)), (2.0, (-10, 0, 0), "in_out_cubic")])
    A.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.55, (-25, 0, 0), "out_back"), (0.82, (-10, 0, 0), "in_out_cubic"), (1.10, (-10, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_L", "pos", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.55, (0, 0, 0.10), "out_back"), (0.82, (0, 0, 0.0), "in_out_cubic"), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.55, (0, 0, 0)), (0.82, (-10, 0, 0), "in_out_cubic"), (0.95, (10, 0, 0), "in_cubic"), (1.2, (6, 0, 0), "out_quad"), (2.0, (0, 0, 0), "in_out_cubic")])

    hit = Clip("HitReact", 0.4)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.10, (-12, 0, 0), "out_cubic"), (0.40, (-6, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.08), "out_cubic"), (0.40, (0, 0, -0.03), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-8, 0, 0), "out_cubic"), (0.40, (-4, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.10, (-14, 0, 0), "out_cubic"), (0.40, (-6, 0, 0), "in_out_cubic")])
    hit.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.10, (15, 0, 0), "out_cubic"), (0.40, (6, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (12, 0, 0), "out_cubic"), (0.40, (4, 0, 0), "in_out_cubic")])

    vic = Clip("Victory", 1.6)
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.5, (-150, 0, 10), "out_back"), (1.6, (-150, 0, 10))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.5, (-30, 0, 0), "out_back"), (1.6, (-30, 0, 0))])
    vic.keys("body", "pos", [(0, (0, 0, 0)), (0.5, (0, 0.03, 0), "out_back"), (1.6, (0, 0.03, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.5, (-8, 0, 0), "out_cubic"), (1.6, (-8, 0, 0))])
    vic.keys("arm_L", "rot", [(0, (0, 0, 0)), (1.0, (-35, 0, 0), "out_cubic"), (1.6, (-35, 0, 0))])

    # ---- Taunt (1.4 s): draw, beat the sword on the shield three times, then a chin-up challenge
    T = Clip("Taunt", 1.4)
    beat = [(0.30, -96), (0.40, -46), (0.50, -96), (0.60, -46), (0.70, -96), (0.80, -46), (0.88, -92)]
    T.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.22, (-96, 30, 0), "in_out_cubic")] + [(t, (rx, 30, 0), "in_cubic" if rx > -60 else "out_cubic") for t, rx in beat] + [(1.02, (-150, 0, 8), "out_cubic"), (1.2, (-150, 0, 8)), (1.4, (0, 0, 0), "in_out_cubic")])
    T.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.22, (-38, 0, 0), "in_out_cubic"), (0.88, (-38, 0, 0)), (1.02, (-30, 0, 0), "out_cubic"), (1.2, (-30, 0, 0)), (1.4, (0, 0, 0), "in_out_cubic")])
    T.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.22, (-14, 0, 0), "in_out_cubic"), (0.42, (-14, 0, 0)), (0.46, (-10, 0, 0)), (0.66, (-14, 0, 0)), (0.70, (-10, 0, 0)), (0.9, (-14, 0, 0)), (1.2, (-30, 0, 0), "out_cubic"), (1.4, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "pos", [(0, (0, 0, 0)), (0.42, (0, 0, 0)), (0.46, (0, 0.012, 0.0)), (0.5, (0, 0, 0)), (0.66, (0, 0, 0)), (0.70, (0, 0.012, 0)), (0.74, (0, 0, 0)), (0.88, (0, 0, 0)), (0.92, (0, 0.014, 0)), (0.96, (0, 0, 0)), (1.02, (0, 0.03, 0), "out_cubic"), (1.2, (0, 0.03, 0)), (1.4, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "rot", [(0, (0, 0, 0)), (0.22, (4, 0, 0), "in_out_cubic"), (0.9, (6, 0, 0)), (1.02, (-6, 0, 0), "out_cubic"), (1.2, (-6, 0, 0)), (1.4, (0, 0, 0), "in_out_cubic")])
    T.keys("head", "rot", [(0, (0, 0, 0)), (0.9, (2, 0, 0)), (1.02, (-16, 0, 0), "out_cubic"), (1.2, (-16, 0, 0)), (1.4, (0, 0, 0), "in_out_cubic")])
    T.keys("spine", "rot", [(0, (0, 0, 0)), (1.02, (-6, 0, 0), "out_cubic"), (1.2, (-6, 0, 0)), (1.4, (0, 0, 0), "in_out_cubic")])
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.5, (-4, 0, 0), "in_out_cubic"), (1.02, (8, 0, 0), "out_cubic"), (1.4, (0, 0, 0), "in_out_cubic")])

    # ---- Surrender (2.0 s, holds): slumps, bows, the sword slips from his hand and clatters on the plinth
    S = Clip("Surrender", 2.0)
    S.keys("body", "rot", [(0, (0, 0, 0)), (0.7, (10, 0, 0), "in_out_cubic"), (2.0, (12, 0, 0), "in_out_cubic")])
    S.keys("body", "pos", [(0, (0, 0, 0)), (0.7, (0, -0.03, 0.02), "in_out_cubic"), (2.0, (0, -0.035, 0.02))])
    S.keys("spine", "rot", [(0, (0, 0, 0)), (0.8, (14, 0, 0), "in_out_cubic"), (2.0, (16, 0, 0), "in_out_cubic")])
    S.keys("head", "rot", [(0, (0, 0, 0)), (0.8, (24, 0, 0), "in_out_cubic"), (2.0, (30, 0, 0), "in_out_cubic")])
    S.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.35, (-8, 0, 0), "in_out_cubic"), (1.0, (10, 0, 0), "in_out_cubic"), (2.0, (14, 0, 0), "in_out_cubic")])
    S.keys("hand_R", "rot", [(0, (0, 0, 0)), (1.0, (6, 0, 0), "in_out_cubic"), (2.0, (10, 0, 0))])
    S.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.5, (12, 0, 0), "in_out_cubic"), (1.2, (18, 0, 0), "in_out_cubic"), (2.0, (20, 0, 0))])
    S.keys("arm_L", "pos", [(0, (0, 0, 0)), (0.6, (0, -0.02, -0.04), "in_out_cubic"), (2.0, (0, -0.03, -0.06))])
    S.keys("top", "rot", [(0, (0, 0, 0)), (0.8, (18, 0, 0), "in_out_cubic"), (2.0, (14, 0, 0))])
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import _emberhold_common as _C
    _C.drop_weapon(S, rig, "weapon", 0.40, tuple(unit(np.array([-0.206, 0.30, -0.075]) - np.array([-0.165, 0.585, 0.06]))), 0.22, 0.016, (0.9, 0.0, 0.45), land_xz=(-0.10, 0.20))
    return [idle, move, A, hit, vic, T, S]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("emberhold", "pawn", rig, make_clips(rig), impact_time=0.95, strike_range=0.55, attack_style="melee", seed=3)
    pedestal_parts(p)
    legs(p)
    skirt_belt(p)
    torso(p)
    collar_and_neck(p)
    arms(p)
    shield(p)
    sword(p)
    bedroll_and_mantle(p)
    head(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
