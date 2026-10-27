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
from anim import Animator, Curve, Fn, Wave, Skin, humanoid_rig, limb_tube, key   # noqa: E402
from anim import motion as M         # noqa: E402
from anim.curves import step_signal, pulse   # noqa: E402

ASSET_ID = "emberhold_pawn"
FRONT_FLAT = 0.3696                   # octagon apothem (flats face +-Z, +-X)


# ======================================================================================= rig
MOUTH = np.array([-0.165, 0.585, 0.06])         # scabbard mouth (sword hilt end rests here)
TIP = np.array([-0.206, 0.30, -0.075])          # scabbard tip
WR0 = np.array([-0.168, 0.630, 0.092])          # rest wrist_R (hand on the hilt)
WL0 = np.array([0.108, 0.689, 0.186])           # rest wrist_L (fist behind the shield)
JOINTS = dict(pelvis=(0, 0.56, 0), spine=(0, 0.64, 0), chest=(0, 0.75, 0), neck=(0, 0.868, 0), head=(0, 0.90, 0), top=(0, 0.86, -0.09),
              clavicle_L=(0.045, 0.855, 0.010), shoulder_L=(0.19, 0.86, 0), elbow_L=(0.205, 0.775, 0.03), wrist_L=tuple(WL0),
              hip_L=(0.075, 0.565, 0), knee_L=(0.080, 0.430, 0.065), ankle_L=(0.075, 0.272, 0.016), toe_L=(0.075, 0.236, 0.104),
              clavicle_R=(-0.045, 0.855, 0.010), shoulder_R=(-0.185, 0.86, 0), elbow_R=(-0.200, 0.765, 0), wrist_R=tuple(WR0),
              hip_R=(-0.075, 0.565, 0), knee_R=(-0.080, 0.430, 0.030), ankle_R=(-0.075, 0.272, 0.016), toe_R=(-0.075, 0.236, 0.104))


def make_rig() -> Rig:
    """Full humanoid skeleton (anim.templates.humanoid_rig): root > body(pelvis) > spine > chest > neck > head ; clavicle > arm (upper arm)
    > hand_* (FOREARM, pivot at the elbow: legacy contract name, alias forearm_*) > wrist_* (the hand) ; thigh > shin > foot > toe ;
    `top` (bedroll) under chest ; `weapon` (the sword, centre of mass) under wrist_R."""
    r = humanoid_rig(JOINTS, weapon=(-0.179, 0.487, 0.013))
    r.socket("socket_weapon_R", "wrist_R", (-0.15, 0.64, 0.09))
    r.socket("socket_cast", "wrist_L", (0.065, 0.80, 0.25))
    r.socket("socket_impact", "body", (-0.03, 0.62, 0.55))
    r.socket("socket_head", "head", (0, 1.04, 0))
    return r


# ---- smooth-skin recipes (anim.skin): chains blend neighbouring bones over +-zone of the shorter bone; plates stay rigid
J_ = lambda k: np.array(JOINTS[k], dtype=float)      # noqa: E731
LEG_SKIN = {s: Skin.chain([f"thigh_{s}", f"shin_{s}", f"foot_{s}"], pre="body", tip=JOINTS[f"toe_{s}"], zone=0.4) for s in "LR"}
ARM_SKIN = {s: Skin.chain([f"arm_{s}", f"hand_{s}"], pre=f"clavicle_{s}", tip=JOINTS[f"wrist_{s}"], zone=0.42) for s in "LR"}
TORSO_SKIN = Skin.chain(["body", "spine", "chest"], tip=JOINTS["neck"], zone=0.45)
NECK_SKIN = Skin.chain(["neck", "head"], pre="chest", tip=(0, 0.95, 0.01), zone=0.4)
_HANG = Skin.nearest([("body", "pelvis", "spine"), ("thigh_L", J_("hip_L"), J_("knee_L")), ("thigh_R", J_("hip_R"), J_("knee_R"))], tau=0.03, bias={"body": 1.6})
SKIRT_SKIN = Skin.gradient(Skin.rigid("body"), _HANG, axis=1, v0=0.58, v1=0.50)       # waist follows the pelvis, the hem follows the thighs
TABARD_SKIN = Skin.gradient(Skin.rigid("body"), Skin.nearest([("body", "pelvis", "spine"), ("thigh_L", J_("hip_L"), J_("knee_L")), ("thigh_R", J_("hip_R"), J_("knee_R"))], tau=0.05, bias={"body": 2.5}),
                            axis=1, v0=0.60, v1=0.50)


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
        hip, knee, ank = J_(f"hip_{name}"), J_(f"knee_{name}"), J_(f"ankle_{name}")
        # one continuous cloth leg with dense rings around the knee: smooth skin bends it without pinching
        leg = limb_tube([hip + [0, 0.02, 0], (hip + knee) / 2 + [0.002, 0, 0.004], knee, (knee + ank) / 2, ank], [0.060, 0.054, 0.046, 0.040, 0.034],
                        joints=[knee], spacing=0.034, joint_spacing=0.016, joint_zone=0.05, sides=8, cap=None, up=(0, 0, 1))
        p.add(f"leg_{name}", leg, "EH_Cloth", None, skin=LEG_SKIN[name], uv_scale=2)
        # boot: shaft + foot + toecap, all rigid on the foot bone
        shaft = g.tube([(side * 0.075, 0.30, 0.012), (side * 0.075, 0.262, 0.016)], [0.039, 0.043], sides=8, samples=1, cap=None, smooth=False)
        foot = g.superellipsoid((0.051, 0.030, 0.100), 0.55, 0.65, 6, 12).translated(side * 0.075, 0.252, 0.040)
        sole = g.superellipsoid((0.054, 0.012, 0.106), 0.35, 0.5, 3, 10).translated(side * 0.075, 0.226, 0.040)
        toe = g.superellipsoid((0.040, 0.024, 0.036), 0.5, 0.6, 4, 9).translated(side * 0.075, 0.256, 0.104)
        p.add(f"boot_{name}", merge([shaft, foot]), "EH_Leather", f"foot_{name}", uv_scale=2)
        p.add(f"boot_sole_{name}", sole, "EH_Steel", f"foot_{name}", lod1=None)
        p.add(f"boot_toe_{name}", toe, "EH_Bronze", f"foot_{name}")
        greave = g.tube([(side * 0.076, 0.285, 0.048 + kz * 0.5), (side * 0.080, 0.36, 0.05 + kz * 0.8), (side * 0.080, 0.425, 0.052 + kz)],
                        [0.040, 0.044, 0.050], sides=8, samples=2, cap=None, up=(0, 0, 1))
        greave = greave.noised(0.0025, 38, 2, seed=3 + side)
        p.add(f"greave_{name}", greave, "EH_Bronze", f"shin_{name}")
        knee_m = g.superellipsoid((0.040, 0.033, 0.027), 0.6, 0.6, 5, 10).translated(side * 0.080, 0.438, 0.066 + kz)
        p.add(f"knee_{name}", knee_m, "EH_Bronze", f"shin_{name}")
        for y, k in ((0.288, 0), (0.425, 1)):
            ring = g.torus(0.043 + 0.006 * k, 0.0042, 14, 4).translated(side * (0.076 + 0.004 * k), y, 0.048 + kz * (0.5 + 0.5 * k))
            p.add(f"greave_lip_{name}{k}", ring, "EH_Bronze", f"shin_{name}", lod1=None)


def skirt_belt(p: Piece):
    # quilted skirt: folded lathe
    prof = g.spline(np.array([(0.100, 0.595), (0.116, 0.54), (0.128, 0.49), (0.136, 0.45), (0.134, 0.438)]), 1)
    folds = 7

    def fold(th, v):
        return 1 + (0.012 + 0.048 * v ** 1.5)[:, None] * np.cos(folds * th)[None, :] + 0.0
    sk = g.lathe(prof, 28, shape_v=fold, crease=75)
    sk = sk.scaled(1, 1, 0.9).noised(0.004, 14, 2, seed=5)
    hem = lambda P: np.clip(0.4 + 0.6 * smoothstep(0.43, 0.54, P[:, 1]), 0, 1)       # soot toward the hem
    p.add("skirt", sk, "EH_Cloth", None, skin=SKIRT_SKIN, uv_scale=2, tint=hem)
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
    p.add("gambeson", gam, "EH_Cloth", None, skin=TORSO_SKIN, uv_scale=2, bake=True)
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
    p.add("cuirass", cuirass, "EH_Bronze", "chest")
    p.add("cuirass_lip_lo", rolled_lip(0.702, 0.0095, 0.0045, 22), "EH_Bronze", "chest", lod1=None)
    # chest strap + studs (leather) - an asymmetric baldric from left shoulder to right hip
    sp = [(0.075, 0.886, 0.02), (0.045, 0.82, 0.098), (-0.0, 0.775, 0.118), (-0.06, 0.725, 0.112), (-0.108, 0.665, 0.10)]
    strap = g.tube(sp, 0.0105, sides=5, samples=2, cap=None, ellipse=(1.0, 0.45), up=(0, 0, 1))
    p.add("baldric", strap, "EH_Leather", "chest", lod1=None, uv_scale=2)
    p.add("baldric_studs", g.instances(g.dome(0.0055, 0.0045, 6, 1), g.spline(np.array(sp), 2)[3:-3:3] + [0, 0, 0.0095],
                                       [(0, 0, 1)] * len(g.spline(np.array(sp), 2)[3:-3:3])), "EH_Bronze", "chest", lod1=None)
    # tabard flap (soft: spine -> body) with bronze hem trim
    tab = g.cloth_panel(0.13, 0.215, cols=7, rows=6, fold_amp=0.006, folds=3, flare=0.35, curve=40, seed=4, thickness=0.004)
    tab = tab.rotated(-9, 0, 0).translated(0, 0.628, 0.118)
    hemf = lambda P: np.clip(0.45 + 0.55 * smoothstep(0.41, 0.55, P[:, 1]), 0, 1)
    p.add("tabard", tab, "EH_Cloth", None, skin=TABARD_SKIN, uv_scale=2, tint=hemf)
    trim = g.tube([(-0.0875, 0.408, 0.152), (0.0, 0.397, 0.160), (0.0875, 0.408, 0.152)],
                  0.0065, sides=5, samples=2, cap="round", cap_steps=1)
    p.add("tabard_trim", trim.rotated(-9, 0, 0, pivot=(0, 0.628, 0.118)), "EH_Bronze", None, skin=TABARD_SKIN, lod1=None)


def collar_and_neck(p: Piece):
    neck = g.tube([(0, 0.868, 0.0), (0, 0.918, 0.006)], [0.034, 0.030], sides=8, samples=1, cap=None, smooth=False)
    p.add("neck", neck, "EH_Skin", None, skin=NECK_SKIN, uv_scale=2)
    # fur collar: base ring + tufts (outer row sweeps out/down, inner row stands up around the neck)
    path = torso_ring(0.882, 0.014, 20)
    ring = g.tube(path * [1.0, 1.0, 1.0], 0.032, sides=7, samples=1, cap=None, smooth=False, closed=True, up=(0, 1, 0))
    ring = ring.noised(0.010, 20, 3, seed=11)
    p.add("fur_collar", ring, "EH_Fur", "chest", uv_scale=2)
    tuft = g.tube([(0, 0, 0), (0.003, 0.016, 0.004), (0.007, 0.028, 0.013)], [0.0125, 0.0075, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    outer = ring_instances(tuft, 16, 0.104, 0.874, normal_tilt=-0.75, scale=1.1, jitter=0.5, seed=1)
    outer2 = ring_instances(tuft, 12, 0.092, 0.905, normal_tilt=0.35, scale=0.9, jitter=0.5, seed=2, start=0.1)
    outer3 = ring_instances(tuft, 6, 0.068, 0.912, normal_tilt=1.0, scale=0.7, jitter=0.5, seed=3, start=0.2)
    p.add("fur_tufts", merge([outer, outer2, outer3]).transformed(np.diag([1, 1, 0.92, 1])), "EH_Fur", "chest", uv_scale=2)


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
    # ---------------- left arm (shield arm): one continuous sleeve shoulder -> elbow -> wrist, smooth-skinned over arm_L / hand_L (forearm)
    sl = limb_tube([(0.190, 0.855, 0.0), (0.198, 0.815, 0.015), (0.205, 0.775, 0.03), (0.172, 0.727, 0.118), (0.108, 0.689, 0.186)],
                   [0.037, 0.037, 0.034, 0.030, 0.026], joints=[J_("elbow_L")], spacing=0.032, joint_spacing=0.015, joint_zone=0.045, sides=8,
                   cap="round", cap_steps=1, up=(0, 1, 0))
    p.add("arm_L_sleeve", sl, "EH_Cloth", None, skin=ARM_SKIN["L"], uv_scale=2)
    p.add("pauldron_L", pauldron(+1, True), "EH_Bronze", "arm_L")
    vamb = g.tube([(0.188, 0.748, 0.074), (0.150, 0.712, 0.140), (0.108, 0.689, 0.186)], [0.0385, 0.0335, 0.0295], sides=8, samples=2, cap="flat", up=(0, 1, 0)).noised(0.002, 40, 2, seed=8)
    p.add("vambrace_L", vamb, "EH_Bronze", "hand_L")
    cuff = g.tube([(0.128, 0.700, 0.168), (0.112, 0.690, 0.184)], [0.034, 0.033], sides=8, samples=1, cap="flat", smooth=False, up=(0, 1, 0))
    p.add("cuff_L", cuff, "EH_Leather", "hand_L", uv_scale=2)
    fist = g.superellipsoid((0.025, 0.021, 0.032), 0.6, 0.7, 5, 10).rotated(0, 0, 8).translated(0.095, 0.682, 0.196)
    thumb = g.tube([(0.082, 0.698, 0.206), (0.072, 0.693, 0.192)], [0.0085, 0.007], sides=5, samples=1, cap="round", cap_steps=1, smooth=False)
    knuckles = g.instances(g.dome(0.0055, 0.0045, 6, 1), [(0.085 + 0.0, 0.686 + dy, 0.2255) for dy in (-0.014, -0.005, 0.005, 0.014)], [(0, 0.0, 1)] * 4)
    p.add("hand_L", merge([fist, thumb, knuckles]), "EH_Leather", "wrist_L", uv_scale=2)
    # ---------------- right arm (sword arm)
    sr = limb_tube([(-0.185, 0.855, 0.0), (-0.192, 0.81, 0.0), (-0.200, 0.765, 0.0), (-0.190, 0.690, 0.048), (-0.168, 0.630, 0.092)],
                   [0.036, 0.036, 0.032, 0.029, 0.025], joints=[J_("elbow_R")], spacing=0.032, joint_spacing=0.015, joint_zone=0.045, sides=8,
                   cap="round", cap_steps=1, up=(0, 1, 0))
    p.add("arm_R_sleeve", sr, "EH_Cloth", None, skin=ARM_SKIN["R"], uv_scale=2)
    p.add("pauldron_R", pauldron(-1, False, dent=True), "EH_Bronze", "arm_R")
    vamb_r = g.tube([(-0.196, 0.730, 0.025), (-0.186, 0.676, 0.056), (-0.170, 0.640, 0.084)], [0.0365, 0.0325, 0.0285], sides=8, samples=2, cap="flat", up=(0, 1, 0)).noised(0.002, 40, 2, seed=14)
    p.add("vambrace_R", vamb_r, "EH_Leather", "hand_R", uv_scale=2)
    cuff_r = g.tube([(-0.178, 0.653, 0.076), (-0.168, 0.634, 0.090)], [0.032, 0.031], sides=8, samples=1, cap="flat", smooth=False, up=(0, 1, 0))
    p.add("cuff_R", cuff_r, "EH_Bronze", "hand_R")
    hand_r = g.superellipsoid((0.024, 0.022, 0.030), 0.6, 0.7, 5, 10).rotated(-10, 0, -8).translated(-0.160, 0.619, 0.099)
    fing = g.instances(g.dome(0.0055, 0.0045, 6, 1), [(-0.150, 0.610 + dy, 0.118 - 0.0) for dy in (-0.012, -0.004, 0.004, 0.012)], [(0.2, 0, 1)] * 4)
    p.add("hand_R", merge([hand_r, fing]), "EH_Leather", "wrist_R", uv_scale=2)


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
H_DIR = unit(MOUTH - TIP)                     # hilt direction (up / forward out of the scabbard)
A_S = -H_DIR                                  # blade axis at rest (down / back into the scabbard)
DRAW = 0.31                                   # blade length + guard: how far the hand travels to clear the scabbard
P_DRAWN = WR0 + H_DIR * DRAW
V = lambda *x: np.array(x, dtype=float)       # noqa: E731


def _anim(rig, hand_L=True, hand_R=True, bedroll=True):
    """Common rig of every clip: planted feet (leg IK + pelvis reach clamp), shield hand pinned to the chest, sword hand pinned to
    the hilt (pelvis space) so the sword stays in the scabbard through any body motion, bedroll spring."""
    a = Animator(rig)
    M.plant_feet(a)
    if hand_L:
        a.goal("ik_hand_L", ("arm_L", "hand_L", "wrist_L"), spaces=(("chest", 1.0),), pole=(0.3, -1, -0.3))
    if hand_R:
        a.goal("ik_hand_R", ("arm_R", "hand_R", "wrist_R"), spaces=(("body", 1.0),), rot=(0, 0, 0), pole=(-0.3, -1, -0.6))
    if bedroll:
        a.secondary(["top"], driver="chest", freq=2.3, zeta=0.32, follow=0.9, accel=0.05, max_deg=14)
    return a


def _goal(a, name):
    return next(g for g in a.goals if g.name == name)


def _sword_hand(a, space_keys, pos_keys, dir_keys, roll=None):
    """Drive the sword hand: `space_keys` blends pelvis space (0) -> chest space (1); pos in absolute rest-frame coordinates; dir = blade direction."""
    g = _goal(a, "ik_hand_R")
    s = step_signal(space_keys)
    g.spaces = (("body", Fn(lambda t: 1 - s(t))), ("chest", s))
    g.pos = M.abs_pos(WR0, Curve(pos_keys))
    d = M.aim(A_S, Curve(dir_keys))
    g.rot = M.blade_roll(d, A_S, roll) if roll is not None else d


def _shield_hand(a, pos_keys):
    g = _goal(a, "ik_hand_L")
    g.pos = M.abs_pos(WL0, Curve(pos_keys))


def clip_idle(rig):
    a = _anim(rig)
    M.idle(a, period=3.0, breath=1.0, shift=1.0, sway=0.009, look=1.0)
    _goal(a, "ik_hand_L").pos = Wave(V(0.0025, 0.004, 0.003), 1 / 3.0, 0.30)
    _goal(a, "ik_hand_R").pos = Wave(V(-0.002, 0.003, 0.0), 1 / 3.0, 0.45)
    return a, 3.0, True, 30, ()


def clip_move(rig):
    a = _anim(rig)
    T = 0.8
    M.biped_gait(a, T, stride=0.035, lift=0.055, duty=0.6, bob=0.014, sway=0.011, roll=3.2, twist=6.5, lean=5.0, arm_swing=(0, 0),
                 toe_off=24, strike=-8, head_stab=0.5)
    _goal(a, "ik_hand_L").pos = Wave(V(0.002, 0.008, 0.004), 2 / T, 0.1)       # shield bobs with each step
    _goal(a, "ik_hand_R").pos = Wave(V(0.0, 0.004, 0.0), 2 / T, 0.2)
    return a, T, True, 30, ()


def clip_hit(rig):
    a = _anim(rig)
    T = 0.4
    # the blow shoves the pelvis back over planted feet (knees buckle through the leg IK), the spine whips back then rebounds
    a.pos("body", Curve([(0, V(0, 0, 0)), (0.07, V(0, -0.030, -0.075), "out_cubic"), (0.17, V(0, -0.012, -0.020), "in_out_cubic"),
                         (0.27, V(0, -0.016, 0.012), "in_out_cubic"), (T, V(0, 0, 0), "in_out_cubic")]))
    a.rot("body", Curve([(0, V(0, 0, 0)), (0.07, V(-8, 3, 2), "out_cubic"), (0.18, V(2, -1, 0), "in_out_cubic"), (0.28, V(-1, 0, 0), "in_out_cubic"), (T, V(0, 0, 0), "in_out_cubic")]))
    a.rot("spine", Curve([(0, V(0, 0, 0)), (0.085, V(-10, 4, 3), "out_cubic"), (0.2, V(3, -2, 0), "in_out_cubic"), (0.3, V(-1.5, 0, 0), "in_out_cubic"), (T, V(0, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, V(0, 0, 0)), (0.10, V(-12, 5, 4), "out_cubic"), (0.22, V(4, -3, -1), "in_out_cubic"), (0.31, V(-2, 0, 0), "in_out_cubic"), (T, V(0, 0, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, V(0, 0, 0)), (0.11, V(-12, 8, 5), "out_cubic"), (0.24, V(5, -4, -1), "in_out_cubic"), (0.33, V(-2, 0, 0), "in_out_cubic"), (T, V(0, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, V(0, 0, 0)), (0.12, V(-14, 10, 6), "out_cubic"), (0.26, V(6, -5, -2), "in_out_cubic"), (0.34, V(-2, 0, 0), "in_out_cubic"), (T, V(0, 0, 0), "in_out_cubic")]))
    _shield_hand(a, [(0, WL0), (0.08, WL0 + V(-0.01, 0.07, -0.05), "out_cubic"), (0.2, WL0 + V(0, -0.015, 0.02), "in_out_cubic"), (T, WL0, "in_out_cubic")])
    _goal(a, "ik_hand_R").pos = Curve([(0, V(0, 0, 0)), (0.09, V(0.01, 0.01, -0.02), "out_cubic"), (T, V(0, 0, 0), "in_out_cubic")])
    return a, T, False, 30, ()


G_PT = V(-0.125, 0.84, 0.24)     # guard: sword out, blade forward
W_PT = V(-0.17, 1.02, -0.02)     # wind-up: sword up and behind the head
H_PT = V(-0.13, 0.79, 0.20)      # strike: arm fully forward
F_PT = V(-0.12, 0.75, 0.17)      # follow-through
D_GUARD = V(0.0, 0.25, 0.97)
D_WIND = V(0.0, 0.82, -0.57)
D_HIT = V(0.0, -0.28, 0.96)
D_FOLLOW = V(0.0, -0.5, 0.86)
IMPACT = 0.95


def clip_attack(rig):
    a = _anim(rig)
    T = 2.0
    I = IMPACT
    # ---- sword hand: draw (.12-.30) -> guard (.40) -> wind-up (.84) -> CHOP lands exactly at impactTime -> follow -> back to guard -> sheathe (1.55-1.90)
    _sword_hand(a, [(0, 0), (0.12, 0), (0.40, 1), (1.45, 1), (1.62, 0)],
                [(0, WR0), (0.12, WR0, "ease_in_out"), (0.30, P_DRAWN, "ease_in_out"), (0.42, G_PT, "ease_in_out"), (0.62, G_PT + V(0.0, 0.0, -0.03)),
                 (0.84, W_PT, "anticipate"), (I, H_PT, "snap_in"), (1.04, F_PT, "out_quad"), (1.14, F_PT, {"tan": "flat"}), (1.34, G_PT, "in_out_cubic"),
                 (1.60, P_DRAWN, "in_out_cubic"), (1.88, WR0, "in_out_cubic")],
                [(0, A_S), (0.12, A_S, "ease_in_out"), (0.30, A_S, "ease_in_out"), (0.42, D_GUARD, "ease_in_out"), (0.62, D_GUARD), (0.84, D_WIND, "anticipate"),
                 (I, D_HIT, "snap_in"), (1.04, D_FOLLOW, "out_quad"), (1.14, D_FOLLOW, {"tan": "flat"}), (1.34, D_GUARD, "in_out_cubic"),
                 (1.60, A_S, "in_out_cubic"), (1.90, A_S)])
    # ---- shield: guard up, then a punch forward with the bash (.40-.60), back to guard
    SG, SB = WL0 + V(-0.01, 0.045, 0.015), WL0 + V(-0.01, 0.055, 0.045)
    _shield_hand(a, [(0, WL0), (0.20, SG, "ease_in_out"), (0.42, SG), (0.52, WL0 + V(-0.02, 0.05, -0.02), "in_out_cubic"), (0.60, SB, "snap_in"), (0.72, SG, "out_cubic"),
                     (0.86, SG + V(0.0, 0.03, -0.02), "in_out_cubic"), (I, SG + V(0.015, 0.0, 0.02), "in_out_cubic"), (1.2, SG, "in_out_cubic"), (1.7, WL0, "in_out_cubic")])
    # ---- pelvis: dip, drive (bash), coil back, then LUNGE into the chop (peaks just before the weapon: kinetic chain)
    a.pos("body", Curve([(0, V(0, 0, 0)), (0.14, V(0, -0.010, -0.008), "ease_in_out"), (0.42, V(0, -0.006, 0.02), "ease_in_out"), (0.60, V(0, -0.016, 0.08), "out_cubic"),
                         (0.78, V(0, -0.012, 0.01), "in_out_cubic"), (I - 0.05, V(0, -0.02, 0.185), "snap_in"), (1.14, V(0, -0.02, 0.185), {"tan": "flat"}),
                         (1.80, V(0, 0, 0), "in_out_cubic")]))
    a.rot("body", Curve([(0, V(0, 0, 0)), (0.14, V(1, 0, 0)), (0.60, V(2, -3, 0), "in_out_cubic"), (0.78, V(-1, -9, -1), "in_out_cubic"), (I - 0.07, V(3, 9, 1), "snap_in"),
                         (1.14, V(3, 7, 0), "out_cubic"), (1.8, V(0, 0, 0), "in_out_cubic")]))
    a.rot("spine", Curve([(0, V(0, 0, 0)), (0.14, V(1, 0, 0)), (0.60, V(2, -4, 0), "in_out_cubic"), (0.80, V(-2, -9, -1), "in_out_cubic"), (I - 0.04, V(5, 9, 1), "snap_in"),
                          (1.14, V(4, 7, 0), "out_cubic"), (1.8, V(0, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, V(0, 0, 0)), (0.14, V(1, 0, 0)), (0.42, V(0, -2, 0), "in_out_cubic"), (0.58, V(3, -6, 0), "out_cubic"), (0.82, V(-5, -16, -2), "in_out_cubic"),
                          (I - 0.02, V(10, 14, 2), "snap_in"), (1.14, V(9, 11, 1), "out_cubic"), (1.8, V(0, 0, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, V(0, 0, 0)), (0.58, V(2, 6, 0), "in_out_cubic"), (0.82, V(-3, 16, 2), "in_out_cubic"), (I, V(8, -10, 0), "snap_in"), (1.14, V(7, -8, 0), "out_cubic"), (1.8, V(0, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, V(0, 0, 0)), (0.58, V(1, 4, 0), "in_out_cubic"), (0.82, V(-2, 10, 1), "in_out_cubic"), (I, V(5, -6, 0), "snap_in"), (1.14, V(5, -5, 0), "out_cubic"), (1.8, V(0, 0, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, V(0, 0, 0)), (0.30, V(0, 0, -3), "in_out_cubic"), (0.84, V(0, 0, -9), "in_out_cubic"), (I, V(0, 0, 4), "snap_in"), (1.14, V(0, 0, 3)), (1.8, V(0, 0, 0), "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, V(0, 0, 0)), (0.60, V(0, 0, 4), "in_out_cubic"), (1.0, V(0, 0, 0), "in_out_cubic")]))
    # ---- feet: left foot steps INTO the lunge during the wind-up, back out in the recovery; right foot stays planted (leg IK + reach clamp = deep lunge)
    M.set_foot(a, "foot_L", pos=Curve([(0, V(0, 0, 0)), (0.60, V(0, 0, 0)), (0.72, V(0, 0.07, 0.09), "ease_in_out"), (0.86, V(0, 0, 0.17), "ease_in_out"), (1.25, V(0, 0, 0.17)),
                                         (1.40, V(0, 0.06, 0.08), "ease_in_out"), (1.58, V(0, 0, 0), "ease_in_out")]),
               rot=Curve([(0, V(0, 0, 0)), (0.60, V(0, 0, 0)), (0.68, V(22, 0, 0), "ease_in_out"), (0.80, V(-9, 0, 0), "ease_in_out"), (0.86, V(0, 0, 0), "ease_in_out"),
                          (1.25, V(0, 0, 0)), (1.33, V(16, 0, 0), "ease_in_out"), (1.50, V(-6, 0, 0), "ease_in_out"), (1.58, V(0, 0, 0), "ease_in_out")]))
    M.set_foot(a, "foot_R", pos=Curve([(0, V(0, 0, 0)), (0.9, V(0, 0, 0)), (1.1, V(0, 0, -0.01), "out_cubic"), (1.7, V(0, 0, 0), "in_out_cubic")]))
    M.stabilize(a, "head", 0.35)
    return a, T, False, 60, (I,)



def clip_victory(rig):
    a = _anim(rig)
    T = 1.6
    P_UP, D_UP = V(-0.11, 1.08, 0.08), V(0.0, 0.96, 0.28)
    _sword_hand(a, [(0, 0), (0.08, 0), (0.30, 1)],
                [(0, WR0), (0.08, WR0, "ease_in_out"), (0.26, P_DRAWN, "ease_in_out"), (0.62, P_UP, ("spring", 0.10, 1.5)), (T, P_UP + V(0.0, 0.01, 0.0), "in_out_cubic")],
                [(0, A_S), (0.08, A_S, "ease_in_out"), (0.26, A_S, "ease_in_out"), (0.40, D_GUARD, "ease_in_out"), (0.62, D_UP, ("spring", 0.12, 1.5)), (T, D_UP)])
    _shield_hand(a, [(0, WL0), (0.20, WL0, "ease_in_out"), (0.62, WL0 + V(-0.012, 0.15, -0.02), ("spring", 0.10, 1.5)), (T, WL0 + V(-0.012, 0.155, -0.02))])
    a.pos("body", Curve([(0, V(0, 0, 0)), (0.12, V(0, -0.012, 0), "ease_in_out"), (0.46, V(0, 0.010, 0.01), ("spring", 0.2, 1.5)), (T, V(0, 0.006, 0.01), "in_out_cubic")]))
    a.rot("body", Curve([(0, V(0, 0, 0)), (0.12, V(3, 0, 0)), (0.5, V(-3, -4, 0), "out_cubic"), (T, V(-2, -3, 0), "in_out_cubic")]))
    a.rot("spine", Curve([(0, V(0, 0, 0)), (0.12, V(4, 0, 0)), (0.5, V(-6, -4, 0), ("spring", 0.15, 1.5)), (T, V(-5, -3, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, V(0, 0, 0)), (0.12, V(5, 0, 0)), (0.52, V(-9, -6, -2), ("spring", 0.15, 1.5)), (T, V(-8, -4, -1.5), "in_out_cubic")]))
    a.rot("neck", Curve([(0, V(0, 0, 0)), (0.55, V(-5, 4, 0), "out_cubic"), (T, V(-4, 3, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, V(0, 0, 0)), (0.55, V(-9, 6, 0), ("spring", 0.15, 1.5)), (T, V(-8, 5, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, V(0, 0, 0)), (0.6, V(0, 0, -8), "out_cubic"), (T, V(0, 0, -8))]))
    a.rot("clavicle_L", Curve([(0, V(0, 0, 0)), (0.6, V(0, 0, 6), "out_cubic"), (T, V(0, 0, 6))]))
    M.set_foot(a, "foot_L", rot=Curve([(0, V(0, 0, 0)), (0.2, V(0, 0, 0)), (0.5, V(14, 0, 0), "out_cubic"), (T, V(12, 0, 0))]),
               pos=Curve([(0, V(0, 0, 0)), (0.2, V(0, 0, 0)), (0.5, V(0, 0.012, 0), "out_cubic"), (T, V(0, 0.010, 0))]))
    M.set_foot(a, "foot_R", rot=Curve([(0, V(0, 0, 0)), (0.2, V(0, 0, 0)), (0.5, V(14, 0, 0), "out_cubic"), (T, V(12, 0, 0))]),
               pos=Curve([(0, V(0, 0, 0)), (0.2, V(0, 0, 0)), (0.5, V(0, 0.012, 0), "out_cubic"), (T, V(0, 0.010, 0))]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


def clip_taunt(rig):
    a = _anim(rig)
    T = 1.4
    DH = lambda u: V(0.35 + 0.2 * (1 - u), -0.25 + 0.7 * (1 - u), 0.8)       # noqa: E731  blade direction: u=1 on the shield, u=0 raised
    HIT_W, UP_W = V(-0.127, 0.79, 0.03), V(-0.12, 0.93, 0.03)
    beats = [0.30, 0.46, 0.62]
    pk, dk = [(0, WR0), (0.06, WR0, "ease_in_out"), (0.16, P_DRAWN, "ease_in_out"), (0.22, UP_W, "ease_in_out")], [(0, A_S), (0.06, A_S), (0.16, A_S, "ease_in_out"), (0.22, DH(0), "ease_in_out")]
    for i, tb in enumerate(beats):
        pk += [(tb - 0.08, UP_W + V(0, 0.015, -0.01), "out_cubic"), (tb, HIT_W, "snap_in"), (tb + 0.035, HIT_W + V(0, 0.012, -0.006), "out_quad")]
        dk += [(tb - 0.08, DH(0), "out_cubic"), (tb, DH(1), "snap_in"), (tb + 0.035, DH(0.75), "out_quad")]
    pk += [(0.78, V(-0.10, 1.07, 0.07), ("spring", 0.12, 1.5)), (1.0, V(-0.10, 1.07, 0.07)), (1.18, P_DRAWN, "in_out_cubic"), (1.38, WR0, "in_out_cubic")]
    dk += [(0.78, V(0.0, 0.95, 0.3), ("spring", 0.12, 1.5)), (1.0, V(0.0, 0.95, 0.3)), (1.12, A_S, "in_out_cubic"), (1.4, A_S)]
    _sword_hand(a, [(0, 0), (0.06, 0), (0.2, 1), (1.0, 1), (1.2, 0)], pk, dk)
    _shield_hand(a, [(0, WL0), (0.2, WL0 + V(-0.01, 0.03, 0.02), "ease_in_out")] + sum([[(tb, WL0 + V(-0.01, 0.03, 0.02) + V(0, -0.012, -0.012), "snap_in"), (tb + 0.07, WL0 + V(-0.01, 0.03, 0.02), "out_cubic")] for tb in beats], [])
                  + [(0.8, WL0 + V(-0.012, 0.10, 0.0), "out_cubic"), (1.0, WL0 + V(-0.012, 0.10, 0.0)), (1.35, WL0, "in_out_cubic")])
    body = [(0, V(0, 0, 0)), (0.2, V(0, -0.012, 0.01), "ease_in_out")]
    for tb in beats:
        body += [(tb - 0.04, V(0, 0.004, 0.0), "out_cubic"), (tb + 0.01, V(0, -0.018, 0.012), "snap_in"), (tb + 0.09, V(0, -0.008, 0.008), "out_cubic")]
    body += [(0.80, V(0, 0.014, 0.0), ("spring", 0.2, 1.5)), (1.0, V(0, 0.012, 0)), (1.38, V(0, 0, 0), "in_out_cubic")]
    a.pos("body", Curve(body))
    chest = [(0, V(0, 0, 0)), (0.2, V(5, -4, 0), "ease_in_out")]
    for tb in beats:
        chest += [(tb - 0.05, V(1, -2, 0), "out_cubic"), (tb + 0.01, V(8, -8, 0), "snap_in"), (tb + 0.09, V(5, -5, 0), "out_cubic")]
    chest += [(0.80, V(-9, 2, 0), ("spring", 0.15, 1.5)), (1.0, V(-8, 2, 0)), (1.38, V(0, 0, 0), "in_out_cubic")]
    a.rot("chest", Curve(chest))
    a.rot("spine", Curve([(0, V(0, 0, 0)), (0.2, V(3, -2, 0), "ease_in_out"), (0.66, V(3, -3, 0)), (0.80, V(-5, 1, 0), ("spring", 0.15, 1.5)), (1.0, V(-4, 1, 0)), (1.38, V(0, 0, 0), "in_out_cubic")]))
    a.rot("body", Curve([(0, V(0, 0, 0)), (0.2, V(2, -2, 0), "ease_in_out"), (0.66, V(3, -3, 0)), (0.80, V(-2, 2, 0), ("spring", 0.15, 1.5)), (1.0, V(-2, 2, 0)), (1.38, V(0, 0, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, V(0, 0, 0)), (0.2, V(2, -3, 0), "ease_in_out"), (0.7, V(2, -3, 0)), (0.85, V(-10, 4, 0), ("spring", 0.15, 1.5)), (1.0, V(-9, 4, 0)), (1.38, V(0, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, V(0, 0, 0)), (0.2, V(3, -4, 0), "ease_in_out"), (0.7, V(3, -4, 0)), (0.85, V(-14, 5, 3), ("spring", 0.15, 1.5)), (1.0, V(-13, 5, 3)), (1.38, V(0, 0, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, V(0, 0, 0)), (0.78, V(0, 0, -7), "in_out_cubic"), (1.0, V(0, 0, -7)), (1.38, V(0, 0, 0), "in_out_cubic")]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


def clip_surrender(rig):
    """Draw, lower the blade, let it fall (physics: fall, two bounces, roll flat), then sink to BOTH KNEES (leg IK: shins lie back on the
    plinth, insteps down), head bowed, hands slack.  Holds the last pose."""
    a = _anim(rig)
    T = 2.0
    sk = a.sk
    l1 = {s: float(np.linalg.norm(sk.rest[sk.ix[f"shin_{s}"]] - sk.rest[sk.ix[f"thigh_{s}"]])) for s in "LR"}
    l2 = {s: float(np.linalg.norm(sk.rest[sk.ix[f"foot_{s}"]] - sk.rest[sk.ix[f"shin_{s}"]])) for s in "LR"}
    KNEE_Y, PELV_Z = 0.262, 0.04
    hip_y = KNEE_Y + 0.5 * (l1["L"] + l1["R"]) + 0.0
    drop = hip_y - JOINTS["hip_L"][1]
    # sword: draw low (blade forward-down), hold, then open the hand at t=.62 -> release_weapon
    LOW, D_LOW = V(-0.13, 0.80, 0.19), V(0.0, -0.35, 0.94)
    _sword_hand(a, [(0, 0), (0.1, 0), (0.34, 1)],
                [(0, WR0), (0.10, WR0, "ease_in_out"), (0.30, P_DRAWN, "ease_in_out"), (0.46, LOW, "ease_in_out"), (0.62, LOW + V(0, -0.02, 0), "ease_in_out"),
                 (0.95, V(-0.17, 0.52, 0.14), "in_out_cubic"), (1.5, V(-0.17, 0.46, 0.10), "in_out_cubic"), (T, V(-0.17, 0.45, 0.09), {"tan": "flat"})],
                [(0, A_S), (0.10, A_S), (0.30, A_S, "ease_in_out"), (0.46, D_LOW, "ease_in_out"), (0.62, D_LOW), (1.0, V(0.0, -0.9, 0.3), "in_out_cubic"), (T, V(0.0, -0.9, 0.2))])
    _shield_hand(a, [(0, WL0), (0.5, WL0 + V(0.0, 0.03, 0.0), "ease_in_out"), (1.2, V(0.14, 0.60, 0.10), "in_out_cubic"), (T, V(0.15, 0.58, 0.09), {"tan": "flat"})])
    a.pos("body", Curve([(0, V(0, 0, 0)), (0.5, V(0, -0.012, 0.0), "ease_in_out"), (0.9, V(0, -0.02, 0.0), "ease_in_out"), (1.55, V(0, -drop, PELV_Z), "in_out_cubic"),
                         (1.78, V(0, -drop + 0.006, PELV_Z), "out_cubic"), (T, V(0, -drop, PELV_Z), "in_out_cubic")]))
    for s, lg in (("L", "foot_L"), ("R", "foot_R")):
        kz = JOINTS[f"hip_{s}"][2] + PELV_Z + (0.02 if s == "L" else 0.0)
        ank = V(0.0, 0.0, 0.0) + V(0, 0.2655 - JOINTS[f"ankle_{s}"][1], (kz - l2[s]) - JOINTS[f"ankle_{s}"][2])
        M.set_foot(a, lg, pos=Curve([(0, V(0, 0, 0)), (0.7, V(0, 0, 0), "ease_in_out"), (1.15, ank + V(0, 0.05, 0.1), "ease_in_out"), (1.55, ank, "in_out_cubic"), (T, ank)]),
                   rot=Curve([(0, V(0, 0, 0)), (0.7, V(0, 0, 0)), (1.15, V(90, 0, 0), "ease_in_out"), (1.55, V(172, 0, 0), "in_out_cubic"), (T, V(172, 0, 0))]))
    a.rot("body", Curve([(0, V(0, 0, 0)), (0.9, V(2, 0, 0), "ease_in_out"), (1.55, V(3, 0, 0), "in_out_cubic"), (T, V(3, 0, 0))]))
    a.rot("spine", Curve([(0, V(0, 0, 0)), (0.9, V(5, 0, 0), "ease_in_out"), (1.6, V(10, 0, 1), "in_out_cubic"), (T, V(11, 0, 1), "in_out_cubic")]))
    a.rot("chest", Curve([(0, V(0, 0, 0)), (0.9, V(4, 0, 0), "ease_in_out"), (1.7, V(8, 0, 0), "in_out_cubic"), (T, V(9, 0, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, V(0, 0, 0)), (1.0, V(8, 0, 0), "in_out_cubic"), (T, V(12, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, V(0, 0, 0)), (1.0, V(10, 0, 0), "in_out_cubic"), (T, V(15, 2, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, V(0, 0, 0)), (1.0, V(0, 0, 4), "in_out_cubic"), (T, V(0, 0, 5))]))
    a.rot("clavicle_L", Curve([(0, V(0, 0, 0)), (1.0, V(0, 0, -4), "in_out_cubic"), (T, V(0, 0, -5))]))
    M.release_weapon(a, "weapon", 0.64, 0.22, 0.016, A_S, (0.9, 0.0, 0.45), land_xz=(-0.10, 0.20), kick=(0.0, 0.0, 0.0))
    return a, T, False, 30, ()


def make_clips(rig):
    out = []
    for name, fn in (("Idle", clip_idle), ("Move", clip_move), ("Attack", clip_attack), ("HitReact", clip_hit), ("Victory", clip_victory),
                     ("Taunt", clip_taunt), ("Surrender", clip_surrender)):
        a, dur, loop, fps, keep = fn(rig)
        out.append(a.bake(name, dur, loop=loop, fps=fps, keep_times=keep))
    return out


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
