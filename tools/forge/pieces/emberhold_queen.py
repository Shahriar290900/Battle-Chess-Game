"""emberhold_queen - Emberhold Flamecrown Warden.

An armoured warrior-queen in swept bronze pauldrons and a layered scale cloak, with a pinched waist over an A-line skirt-armour of
overlapping bronze lames.  She is crowned with an OPEN coronet of nine pointed bronze tines (five tall, four short) with an ember bead on
every tip and a small ember orb on a stalk in the centre: no cross, no arches, no dome, so she can never be mistaken for the king.
Hands are empty at rest; the great hammer-staff lives on the `weapon_summon` node (scale 0 in every clip except Attack and the Taunt
flash, where it is forged from embers).
Built from docs/art/emberhold_queen.md on the full humanoid skeleton: smooth-skinned limbs/torso/cloak/braid, rigid armour plates,
procedural IK/gait/strike animation baked to dense tracks (the spin-slam pins both hands to the hammer haft).
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geom as g                                   # noqa: E402
from geom import TAU, merge, smoothstep            # noqa: E402
from piece import Piece                            # noqa: E402
from rig import Clip, Rig                          # noqa: E402
from anim import Animator, Curve, Fn, Wave, Skin, humanoid_rig, limb_tube   # noqa: E402
from anim import motion as M                       # noqa: E402
from anim.curves import step_signal                # noqa: E402
import _emberhold_common as C                      # noqa: E402

ASSET_ID = "emberhold_queen"

BODY = C.Body(Y=[0.76, 0.82, 0.88, 0.96, 1.04, 1.10, 1.15, 1.19, 1.23],
              RX=[0.150, 0.118, 0.104, 0.118, 0.138, 0.152, 0.142, 0.086, 0.050],
              RZ=[0.110, 0.088, 0.078, 0.084, 0.092, 0.094, 0.086, 0.062, 0.045],
              ZC=[0, 0, 0, 0.002, 0.004, 0.006, 0.006, 0.006, 0.006])
SK_Y = [0.865, 0.80, 0.74, 0.66, 0.58, 0.50, 0.42, 0.35, 0.295]
SK_R = [0.118, 0.134, 0.150, 0.172, 0.192, 0.212, 0.230, 0.245, 0.256]


def sk_r(y):
    return float(np.interp(y, SK_Y[::-1], SK_R[::-1]))


# ======================================================================================= rig
JOINTS = dict(pelvis=(0, 0.78, 0), spine=(0, 0.90, 0), chest=(0, 1.02, 0), neck=(0, 1.15, 0.005), head=(0, 1.19, 0.01), top=(0, 1.17, -0.10),
              clavicle_L=(0.07, 1.13, 0), shoulder_L=(0.20, 1.12, 0), elbow_L=(0.24, 0.93, 0.04), wrist_L=(0.25, 0.80, 0.18),
              hip_L=(0.07, 0.79, 0), knee_L=(0.08, 0.55, 0.07), ankle_L=(0.075, 0.27, 0.04), toe_L=(0.075, 0.245, 0.12))
J_ = lambda k: np.array(JOINTS[k] if k in JOINTS else ((-JOINTS[k[:-1] + "L"][0],) + tuple(JOINTS[k[:-1] + "L"][1:])), dtype=float)   # noqa: E731
V = lambda *x: np.array(x, dtype=float)              # noqa: E731
CAPE = [(0, 1.10, -0.16), (0, 0.78, -0.22), (0, 0.50, -0.28)]
BRAID = [(0.0, 1.20, -0.136), (0.02, 1.05, -0.152), (0.010, 0.93, -0.147)]
WR0, WL0 = J_("wrist_R"), J_("wrist_L")
GRIP = WR0.copy()                                    # weapon_summon origin = the right palm on the haft
A_S = V(0.0, -1.0, 0.0)                              # haft axis at rest: hand -> hammer head (straight down)


def make_rig() -> Rig:
    r = humanoid_rig(JOINTS, cape=CAPE)
    prev = "top"
    for i, p in enumerate(BRAID, 1):
        r.add(f"braid_{i}", prev, p)
        prev = f"braid_{i}"
    r.add("skirt_1", "body", (0, 0.60, 0))               # skirt compression bones: the kneel gathers the A-line skirt instead of sinking it into the plinth
    r.add("skirt_2", "body", (0, 0.32, 0))
    r.node("weapon_summon", "wrist_R", tuple(GRIP))
    r.socket("socket_weapon_R", "wrist_R", tuple(GRIP))
    r.socket("socket_cast", "body", (0, 0.90, 0.30))
    r.socket("socket_impact", "body", (0, 0.30, 0.70))
    r.socket("socket_head", "head", (0, 1.62, 0))
    return r


# ---- smooth-skin recipes: chains blend neighbouring bones around each joint; armour plates stay rigid
LEG_SKIN = {s: Skin.chain([f"thigh_{s}", f"shin_{s}", f"foot_{s}"], pre="body", tip=JOINTS["toe_L"] if s == "L" else tuple(J_("toe_R")), zone=0.4) for s in "LR"}
ARM_SKIN = {s: Skin.chain([f"arm_{s}", f"hand_{s}"], pre=f"clavicle_{s}", tip=tuple(J_(f"wrist_{s}")), zone=0.42) for s in "LR"}
TORSO_SKIN = Skin.chain(["body", "spine", "chest"], tip=JOINTS["neck"], zone=0.45)
NECK_SKIN = Skin.chain(["neck", "head"], pre="chest", tip=(0, 1.32, 0.012), zone=0.45)
CLOAK_SKIN = Skin.chain(["top", "cape_1", "cape_2", "cape_3"], pre="chest", tip=(0, 0.30, -0.30), zone=0.45)
BRAID_SKIN = Skin.gradient(Skin.rigid("head"), Skin.chain(["braid_1", "braid_2", "braid_3"], pre="top", tip=(0.0, 0.84, -0.142), zone=0.45), axis=1, v0=1.36, v1=1.25)
SKIRT_SKIN = Skin.nearest([("body", J_("pelvis"), J_("spine")), ("skirt_1", (0, 0.60, 0), (0, 0.60, 0)), ("skirt_2", (0, 0.32, 0), (0, 0.32, 0)),
                           ("thigh_L", J_("hip_L"), J_("knee_L")), ("thigh_R", J_("hip_R"), J_("knee_R"))], tau=0.07, bias={"thigh_L": 0.40, "thigh_R": 0.40})


# ======================================================================================= legs (mostly hidden by the skirt; boots peek out)
def lerp3(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


def legs(p: Piece):
    for s, nm in ((1, "L"), (-1, "R")):
        hip, knee, ank = J_(f"hip_{nm}"), J_(f"knee_{nm}"), J_(f"ankle_{nm}")
        x = s * 0.075
        hose = limb_tube([hip + [0, 0.03, 0], lerp3(hip, knee, 0.5) + [0, 0, 0.004], knee, lerp3(knee, ank, 0.5), ank + [0, 0.01, 0]],
                         [0.062, 0.055, 0.047, 0.041, 0.038], joints=[knee], spacing=0.05, joint_spacing=0.022, joint_zone=0.06, sides=8, cap=None, up=(0, 0, 1))
        p.add(f"hose_{nm}", hose, "EH_Cloth", None, skin=LEG_SKIN[nm], uv_scale=2, tint=lambda P: np.full(len(P), 0.5))
        foot = g.superellipsoid((0.040, 0.030, 0.125), 0.5, 0.62, 5, 12).translated(x, 0.262, 0.150)
        shaft = g.tube([(x, 0.350, 0.050), (x, 0.275, 0.046)], [0.046, 0.050], sides=10, samples=1, cap=None, smooth=False)
        p.add(f"boot_{nm}", merge([foot, shaft]), "EH_Leather", f"foot_{nm}", uv_scale=2)
        toe = g.superellipsoid((0.036, 0.022, 0.040), 0.5, 0.6, 4, 9).translated(x, 0.264, 0.262)
        p.add(f"boot_toe_{nm}", toe, "EH_Bronze", f"foot_{nm}")
        g0, g1 = lerp3(knee, ank, 0.92) + [0, 0, 0.010], lerp3(knee, ank, 0.12) + [0, 0, 0.010]
        gm = lerp3(g0, g1, 0.5) + [s * 0.002, 0, 0.004]
        greave = g.tube([g0, gm, g1], [0.048, 0.052, 0.056], sides=10, samples=2, cap=None, up=(0, 0, 1)).noised(0.002, 36, 2, seed=3 + s)
        p.add(f"greave_{nm}", greave, "EH_Bronze", f"shin_{nm}")
        p.add(f"greave_lip_{nm}", g.torus(0.058, 0.0050, 14, 4).translated(*g1), "EH_Bronze", f"shin_{nm}", lod1=None)
        cop = g.superellipsoid((0.048, 0.042, 0.032), 0.6, 0.6, 4, 10).translated(*(knee + [0, 0, 0.046]))
        p.add(f"knee_{nm}", cop, "EH_Bronze", f"shin_{nm}")
        c0, c1 = lerp3(hip, knee, 0.86), lerp3(hip, knee, 0.10)
        cuisse = g.tube([c0 + [0, 0, 0.008], lerp3(c0, c1, 0.5) + [0, 0, 0.008], c1 + [0, 0, 0.008]], [0.056, 0.062, 0.066], sides=10, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"cuisse_{nm}", cuisse.noised(0.0016, 30, 2, seed=8 + s), "EH_Bronze", f"thigh_{nm}", lod1=None)


# ======================================================================================= skirt armour
def skirt(p: Piece):
    rings = []
    for y, r in zip(SK_Y[::-1], SK_R[::-1]):
        th = np.linspace(0, TAU, 56, endpoint=False)
        f = 1 + (0.010 + 0.040 * float(smoothstep(0.80, 0.30, y))) * (0.6 * np.cos(9 * th + 0.4) + 0.4 * np.cos(14 * th + 1.9))
        rings.append(np.stack([r * f * np.sin(th) * 1.0, np.full(56, y), r * f * np.cos(th) * 0.94], 1))
    sk = g.loft(np.stack(rings), closed=True, crease=60).noised(0.0025, 14, 2, seed=2)
    p.add("skirt_under", sk, "EH_Cloth", None, skin=SKIRT_SKIN, uv_scale=2, tint=lambda P: (0.26 + 0.74 * smoothstep(0.28, 0.72, P[:, 1]))[:, None] * np.array([1.05, 0.95, 0.88]))
    rows = [(12, 0.28, 0.48, 0.150, 0.0, "row1"), (12, 0.44, 0.62, 0.128, 15.0, "row2"), (10, 0.60, 0.76, 0.108, 0.0, "row3")]
    for n, y0, y1, w, off, nm in rows:
        plates = []
        h = y1 - y0
        yc = 0.5 * (y0 + y1)
        rr = sk_r(yc) * 1.0 + 0.010
        slope = math.degrees(math.atan((sk_r(y0) - sk_r(y1)) / (y1 - y0)))
        for k in range(n):
            a = off + k * 360.0 / n
            pl = g.plate(w, h, 0.012, 0.006, bend_r=rr, inner_x=1, taper=lambda t: 1 - 0.16 * (t + 1) / 2, drop_back=True)
            pl = pl.rotated(-slope, 0, 0).translated(0, yc, rr * 0.94)
            plates.append(pl.rotated(0, a, 0))
        p.add(f"skirt_lames_{nm}", merge(plates), "EH_Bronze", None, skin=SKIRT_SKIN)
        rim = g.tube(np.stack([[(rr + 0.006) * math.sin(t), y0 + 0.004, (rr + 0.006) * math.cos(t) * 0.94] for t in np.linspace(0, TAU, 40, endpoint=False)]), 0.0050,
                     sides=4, samples=1, cap=None, closed=True, smooth=False, up=(0, 1, 0))
        p.add(f"skirt_rim_{nm}", rim, "EH_Bronze", None, skin=SKIRT_SKIN, lod1=None)
        pos = [((rr + 0.014) * math.sin(math.radians(off + (k + 0.5) * 360 / n)), yc + h * 0.25, (rr + 0.014) * math.cos(math.radians(off + (k + 0.5) * 360 / n)) * 0.94) for k in range(n)]
        nr = [(math.sin(math.radians(off + (k + 0.5) * 360 / n)), 0.25, math.cos(math.radians(off + (k + 0.5) * 360 / n))) for k in range(n)]
        p.add(f"skirt_rivets_{nm}", g.instances(g.dome(0.0070, 0.0050, 6, 1), pos, nr), "EH_Bronze", None, skin=SKIRT_SKIN, lod1=None)
    # front split tabard (oxblood) hanging over the lames, bronze edge piping and a flame-chevron embroidery
    ys = np.linspace(0.86, 0.22, 14)
    grid = []
    for y in ys:
        t = (0.86 - y) / 0.64
        w = 0.100 + 0.024 * t
        R = (sk_r(max(y, 0.295)) + 0.026) if y > 0.295 else 0.282
        row = []
        for u in np.linspace(-0.5, 0.5, 5):
            x = u * w
            z = math.sqrt(max(R * R - x * x, 0)) * 0.94 + 0.004 + 0.008 * math.sin(u * 6 + t * 5) * t
            row.append((x, y, z))
        grid.append(row)
    tab = g.loft(np.array(grid)[::-1], closed=False, crease=60, v_tile=0.25, u_tile=0.25)
    p.add("tabard", tab, "EH_Cloth", None, skin=SKIRT_SKIN, uv_scale=2, tint=lambda P: (0.38 + 0.62 * smoothstep(0.24, 0.8, P[:, 1]))[:, None] * np.array([1.2, 0.98, 0.84]))
    for s, nm in ((-1, "R"), (1, "L")):
        pts = []
        for y in ys[1:]:
            t = (0.86 - y) / 0.64
            w = 0.100 + 0.024 * t
            R = (sk_r(max(y, 0.295)) + 0.026) if y > 0.295 else 0.282
            x = s * w / 2
            pts.append((x, y, math.sqrt(max(R * R - x * x, 0)) * 0.94 + 0.010))
        p.add(f"tabard_edge_{nm}", g.tube(pts, 0.0050, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", None, skin=SKIRT_SKIN, lod1=None)
    emb = []
    for k, y in enumerate((0.74, 0.62, 0.50, 0.38)):
        t = (0.86 - y) / 0.64
        w = (0.100 + 0.024 * t) * 0.34
        R = sk_r(max(y, 0.295)) + 0.036
        zf = lambda x, yy: math.sqrt(max(R * R - x * x, 0)) * 0.94 + 0.013           # noqa: E731
        emb.append(g.tube([(-w, y - 0.035, zf(-w, y)), (0, y, zf(0, y)), (w, y - 0.035, zf(w, y))], 0.0034, sides=4, samples=3, cap="round", cap_steps=1, smooth=True))
    emb.append(g.tube([(0, 0.80, sk_r(0.80) + 0.038), (0, 0.55, sk_r(0.55) + 0.040), (0, 0.30, 0.268)], 0.0030, sides=4, samples=2, cap="round", cap_steps=1, smooth=True))
    p.add("tabard_embroidery", merge(emb), "EH_Bronze", None, skin=SKIRT_SKIN, lod1=None)
    # belt + faulds + anvil medallion
    belt = BODY.loft([0.805, 0.810, 0.868, 0.874], [0.004, 0.014, 0.014, 0.004], K=36, crease=50)
    p.add("belt", belt, "EH_Leather", None, skin=TORSO_SKIN, uv_scale=2)
    fa = []
    for i in range(7):
        a = -90 + i * 30
        pl = g.plate(0.064, 0.085, 0.012, 0.006, bend_r=0.125, inner_x=1, drop_back=True).rotated(-8, 0, 0).translated(0, 0.775, 0.112)
        fa.append(pl.rotated(0, a, 0))
    p.add("faulds", merge(fa), "EH_Bronze", "body")
    pt, _ = BODY.surf(0.84, 0, 0.016)
    med = g.lathe(np.array([(0, 0), (0.030, 0), (0.032, 0.005), (0.030, 0.012), (0, 0.013)]), 20, crease=40).rotated(90, 0, 0).translated(0, 0.842, pt[2])
    anv = g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 0.62, 0.006, 0.0, 1).translated(0, 0.838, pt[2] + 0.015)
    p.add("belt_medallion", merge([med, anv]), "EH_Bronze", "body")
    studs = [BODY.surf(0.841, a, 0.016) for a in np.linspace(-120, 120, 13) if abs(a) > 22]
    p.add("belt_studs", g.instances(g.dome(0.0055, 0.004, 5, 1), [q[0] for q in studs], [q[1] for q in studs]), "EH_Bronze", "body", lod1=None)


# ======================================================================================= torso
def torso(p: Piece):
    gam = BODY.loft([0.84, 0.90, 0.97, 1.04, 1.10, 1.15, 1.19, 1.23], [-0.004] * 8, K=32, crease=60)
    p.add("gambeson", gam, "EH_Cloth", None, skin=TORSO_SKIN, uv_scale=2)
    ys = [0.895, 0.93, 0.98, 1.03, 1.08, 1.115, 1.14]
    grow = [0.008, 0.014, 0.018, 0.021, 0.022, 0.018, 0.010]
    ridge = [0.0, 0.004, 0.008, 0.012, 0.014, 0.010, 0.0]
    rings = np.stack([BODY.ring(y, gg, 28, -92, 92, ridge=rd, ridge_w=0.020) for y, gg, rd in zip(ys, grow, ridge)])
    bp = g.loft(rings, closed=False, crease=50)
    bp = g.warp(bp, lambda P: P + np.column_stack([np.zeros(len(P)), np.zeros(len(P)), 0.008 * np.exp(-((P[:, 1] - 1.05) / 0.03) ** 2) * np.exp(-((np.abs(P[:, 0]) - 0.05) / 0.03) ** 2)]), 50)
    p.add("breastplate", bp.noised(0.0012, 40, 2, seed=3), "EH_Bronze", "chest")
    for a, nm in ((-92, "R"), (92, "L")):
        p.add(f"breast_edge_{nm}", BODY.edge(ys[1:-1], [gg + 0.004 for gg in grow[1:-1]], a, 0.0050, 4), "EH_Bronze", "chest", lod1=None)
    p.add("breast_lip_top", g.tube([BODY.surf(1.14, a, 0.012)[0] for a in np.linspace(-92, 92, 14)], 0.0055, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", "chest", lod1=None)
    pp, _ = BODY.surf(1.03, 0, 0.0245)
    spirals = []
    for i in range(6):
        a0 = i * 60
        pts = []
        for t in np.linspace(0, 1, 9):
            r = 0.006 + 0.040 * t
            ang = math.radians(a0 + 80 * t)
            pts.append((r * math.cos(ang), 1.03 + r * math.sin(ang), pp[2] + 0.0008))
        spirals.append(g.tube(pts, 0.0036, sides=4, samples=1, cap="round", cap_steps=1, smooth=True))
    boss = g.superellipsoid((0.012, 0.012, 0.007), 0.7, 0.7, 3, 8).translated(0, 1.03, pp[2] + 0.004)
    p.add("filigree", merge(spirals + [boss]), "EH_Steel", "chest", lod1=None)
    for i, y in enumerate((0.905, 0.935, 0.965)):
        gr = 0.020 - 0.002 * i
        lm = BODY.loft([y - 0.013, y - 0.010, y + 0.010, y + 0.013], [gr - 0.006, gr, gr, gr - 0.004], K=24, a0=-98, a1=98, crease=45)
        p.add(f"lame_{i}", lm, "EH_Bronze", "spine")
    rbk = np.stack([BODY.ring(y, gg, 22, 118, 242) for y, gg in zip([0.90, 0.96, 1.02, 1.08, 1.13], [0.008, 0.013, 0.016, 0.016, 0.010])])
    p.add("backplate", g.loft(rbk, closed=False, crease=50), "EH_Bronze", "chest")
    gor = g.lathe(np.array([(0.058, 1.138), (0.074, 1.146), (0.082, 1.170), (0.070, 1.192), (0.054, 1.192), (0.064, 1.172), (0.060, 1.150)]), 22, crease=45)
    p.add("gorget", gor.translated(0, 0, 0.008), "EH_Bronze", "chest")
    neck = limb_tube([(0, 1.135, 0.008), (0, 1.17, 0.010), (0, 1.22, 0.012)], [0.040, 0.037, 0.034], joints=[(0, 1.15, 0.005), (0, 1.19, 0.01)], spacing=0.03,
                     joint_spacing=0.016, joint_zone=0.03, sides=9, cap=None, up=(0, 0, 1))
    p.add("neck", neck, "EH_Skin", None, skin=NECK_SKIN, uv_scale=2)


# ======================================================================================= cloak
def yoke_and_cloak(p: Piece):
    K = 32
    th = np.linspace(0, TAU, K, endpoint=False)
    path = np.stack([0.160 * np.sin(th), 1.160 - 0.030 * np.abs(np.sin(th)) ** 1.5, 0.116 * np.cos(th) - 0.004], 1)
    yoke = g.tube(path, 0.032, sides=7, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.008, 18, 3, seed=40)
    p.add("cloak_yoke", yoke, "EH_Fur", "chest", uv_scale=2)
    tuft = g.tube([(0, 0, 0), (0.004, 0.014, 0.004), (0.010, 0.024, 0.010)], [0.019, 0.012, 0.0], sides=5, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    rng = np.random.default_rng(3)
    pos, nr = [], []
    for i in range(28):
        a = i * TAU / 28 + rng.normal(0, 0.03)
        pos.append((0.176 * math.sin(a), 1.150 - 0.030 * abs(math.sin(a)) ** 1.5, 0.130 * math.cos(a) - 0.004))
        nr.append((math.sin(a), -0.8, math.cos(a)))
    p.add("yoke_tufts", g.instances(tuft, pos, nr, 1.0 + 0.3 * rng.random(28), spins=rng.random(28) * 360), "EH_Fur", "chest", uv_scale=2)
    rows, cols = 12, 9
    grid = []
    ph = np.random.default_rng(6).random(2) * TAU
    for i in range(rows):
        t = i / (rows - 1)
        y = 1.13 - t * 0.84
        w = 0.150 + 0.108 * smoothstep(0.0, 0.75, t)
        row = []
        for j in range(cols):
            u = j / (cols - 1) * 2 - 1
            x = u * w
            z = -(0.120 + 0.150 * t ** 1.2) + u * u * 0.060 * (0.4 + t) + math.sin(u * 6 + ph[0]) * 0.008 * t
            yy = y - (0.060 * max(0.0, -u) ** 1.3 * (1 + 0.4 * math.sin(u * 14 + ph[1])) if t > 0.75 else 0.0)
            row.append((x, yy, z))
        grid.append(row)
    G = np.array(grid)[::-1]
    back = g.loft(G[:, ::-1], closed=False, crease=70, v_tile=0.25, u_tile=0.25)
    p.add("cloak_backing", back, "EH_Cloth", None, skin=CLOAK_SKIN, uv_scale=2,
          tint=lambda P: (0.30 + 0.70 * smoothstep(0.30, 1.1, P[:, 1]))[:, None] * np.array([1.0, 0.92, 0.85]))
    shape = np.array([(-0.5, 0.5), (0.5, 0.5), (0.5, -0.12), (0.0, -0.58), (-0.5, -0.12)])
    base = g.extrude(shape, 0.008, 0.003, 1)
    bronze, steel = [], []
    for k in range(10):
        n = 6 + k
        yrow = 1.12 - 0.075 * k
        wrow = 0.28 + 0.030 * k
        zrow = -0.136 - 0.014 * k
        sw = wrow / n * 1.18
        for j in range(n):
            u = (j + 0.5) / n - 0.5 + (0.0 if k % 2 == 0 else 0.5 / n)
            if abs(u) > 0.5 + 1e-6:
                continue
            x = u * wrow
            zz = zrow + u * u * 0.060 * (0.4 + 0.1 * k)
            m = base.scaled(sw, 0.082 / 1.1, 1.0).rotated(-6 - 0.6 * k, 0, 0).rotated(0, -u * 40, 0).rotated(0, 180, 0).translated(x, yrow, zz)
            (steel if (k % 4 == 3 and j % 2 == 0) else bronze).append(m)
    p.add("cloak_scales", merge(bronze), "EH_Bronze", None, skin=CLOAK_SKIN)
    p.add("cloak_scales_steel", merge(steel), "EH_Steel", None, skin=CLOAK_SKIN, lod1=None)
    rim = []
    for (k, j) in ((3, 2), (5, 6), (7, 3), (8, 9)):
        n = 6 + k
        u = (j + 0.5) / n - 0.5 + (0.0 if k % 2 == 0 else 0.5 / n)
        x = u * (0.28 + 0.030 * k)
        zz = -0.136 - 0.014 * k + u * u * 0.060 * (0.4 + 0.1 * k)
        e = g.tube([(-0.020, 1.12 - 0.075 * k - 0.030, 0), (0, 1.12 - 0.075 * k - 0.044, 0), (0.020, 1.12 - 0.075 * k - 0.030, 0)], 0.0028, sides=4, samples=2, cap="round", cap_steps=1)
        rim.append(e.translated(x, 0, zz - 0.009))
    p.add("scale_ember_rims", merge(rim), "EH_EmberVein", None, skin=CLOAK_SKIN, lod1=None, bake=False)
    for s in (-1, 1):
        d = g.lathe(np.array([(0, 0), (0.016, 0), (0.017, 0.004), (0.015, 0.007), (0, 0.008)]), 14, crease=40).rotated(90, 0, 0).translated(s * 0.100, 1.125, 0.118)
        p.add(f"brooch_{'L' if s > 0 else 'R'}", d, "EH_Bronze", "chest", lod1=None)
    chain = g.tube([(-0.100, 1.120, 0.122), (-0.05, 1.100, 0.148), (0.0, 1.108, 0.152), (0.05, 1.100, 0.148), (0.100, 1.120, 0.122)], 0.0036, sides=4, samples=2,
                   cap="round", cap_steps=1, radius_fn=lambda t: 0.7 + 0.3 * abs(math.sin(t * 50)))
    p.add("clasp_chain", chain, "EH_Bronze", "chest", lod1=None)


# ======================================================================================= pauldrons & arms
def wing(s, scale, spikes):
    """Swept pauldron wing: three overlapping lames in a plane tilted 25 degrees, rear tip sweeping back."""
    poly = np.array([(0, 0), (0.12, 0.03), (0.19, 0.10), (0.17, 0.14), (0.04, 0.08)])
    parts = []
    for i, k in enumerate((1.0, 0.85, 0.70)):
        m = g.extrude(poly * scale * k, 0.012, 0.0045, 1)
        m = m.translated(0.010 * i * scale, -0.032 * i * scale, 0.0)
        parts.append(m.translated(0, 0, -0.010 * i))
    dome = g.superellipsoid((0.060 * scale, 0.026 * scale, 0.070 * scale), 0.6, 0.7, 5, 11).translated(0.050 * scale, 0.040 * scale, 0.0)
    parts.append(dome)
    if spikes:
        for j, xx in enumerate((0.060, 0.105, 0.150)):
            sp = g.tube([(0, 0, 0), (0, 0.020, 0), (0, 0.070 - 0.010 * j, 0)], [0.012, 0.009, 0.0], sides=5, samples=1, cap=None, smooth=False)
            parts.append(sp.translated(xx * scale, 0.065 * scale + 0.01 * j, 0.0))
    m = merge(parts)
    m = g.warp(m, lambda P: np.column_stack([P[:, 0], P[:, 1], P[:, 2] - 0.30 * np.clip(P[:, 0], 0, None) ** 1.5]), 50)
    m = m.rotated(0, 0, 25)
    if s < 0:
        m = m.mirrored("x")
    return m


def arms(p: Piece):
    for s, nm, sc, sp in ((1, "L", 1.0, False), (-1, "R", 1.06, True)):
        w = wing(s, sc, sp).translated(s * 0.20, 1.115 + (0.012 if s < 0 else 0.0), 0.0)
        p.add(f"pauldron_{nm}", w.noised(0.0010, 36, 2, seed=11 + s), "EH_Bronze", f"arm_{nm}")
        cap = g.superellipsoid((0.046, 0.030, 0.052), 0.65, 0.7, 4, 11).translated(s * 0.208, 1.128, 0)
        p.add(f"shoulder_cap_{nm}", cap.noised(0.0012, 34, 2, seed=14 + s), "EH_Bronze", f"arm_{nm}")
    for s, nm in ((1, "L"), (-1, "R")):
        sh, el, wr = J_(f"shoulder_{nm}"), J_(f"elbow_{nm}"), J_(f"wrist_{nm}")
        fd = C.unit(wr - el)
        ud = C.unit(el - sh)
        sleeve = limb_tube([sh + [0, -0.01, 0], lerp3(sh, el, 0.5), el, lerp3(el, wr - fd * 0.03, 0.5), wr - fd * 0.03], [0.044, 0.041, 0.037, 0.033, 0.030],
                           joints=[el], spacing=0.04, joint_spacing=0.018, joint_zone=0.05, sides=9, cap="round", cap_steps=1, up=(0, 1, 0))
        p.add(f"sleeve_{nm}", sleeve.noised(0.0016, 14, 2, seed=20 + s), "EH_Cloth", None, skin=ARM_SKIN[nm], uv_scale=2)
        r0, r1 = lerp3(sh, el, 0.16), lerp3(sh, el, 0.82)
        rere = g.tube([r0, lerp3(r0, r1, 0.5), r1], [0.051, 0.049, 0.046], sides=10, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"rerebrace_{nm}", rere.noised(0.0016, 30, 2, seed=22 + s), "EH_Bronze", f"arm_{nm}")
        p.add(f"rerebrace_rim_{nm}", g.torus(0.0475, 0.0045, 14, 4).aimed(ud, r1), "EH_Bronze", f"arm_{nm}", lod1=None)
        cop = g.superellipsoid((0.038, 0.040, 0.038), 0.65, 0.65, 4, 10).translated(*(el + [s * 0.018, -0.002, -0.014]))
        fin = g.extrude_plane(np.array([(-0.025, -0.030), (-0.025, 0.036), (0.016, 0.024), (0.024, -0.008)]), 0.009, "YZ", bevel=0.003, bevel_segments=1).translated(*(el + [s * 0.054, 0.0, -0.016]))
        p.add(f"elbow_cop_{nm}", merge([cop, fin]), "EH_Bronze", f"hand_{nm}")
        v0, v1 = lerp3(el, wr, 0.22), lerp3(el, wr, 0.80)
        vam = g.tube([v0, lerp3(v0, v1, 0.5), v1], [0.041, 0.038, 0.034], sides=10, samples=2, cap="flat", up=(0, 1, 0))
        p.add(f"vambrace_{nm}", vam.noised(0.0016, 34, 2, seed=24 + s), "EH_Bronze", f"hand_{nm}")
        fin2 = g.extrude_plane(np.array([(0.88, 0.07), (0.84, 0.15), (0.86, 0.185), (0.90, 0.12)]), 0.011, "YZ", bevel=0.004, bevel_segments=1).translated(s * 0.290, 0, 0)
        p.add(f"vambrace_fin_{nm}", fin2, "EH_Bronze", f"hand_{nm}", lod1=None)
        for u in (0.40, 0.65):
            p.add(f"vambrace_band_{nm}{int(u * 100)}", g.torus(0.040 - 0.006 * u, 0.0048, 14, 4).aimed(fd, lerp3(v0, v1, u)), "EH_Steel", f"hand_{nm}", lod1=None)
        p.add(f"gauntlet_cuff_{nm}", g.torus(0.035, 0.0065, 14, 4).aimed(fd, wr - fd * 0.040), "EH_Bronze", f"hand_{nm}")
        # gauntlet hand: back plate in front of the grip axis (vertical at rest), curled fingers (rings with a gap at the palm side), thumb
        hx, hy, hz = wr
        back = g.superellipsoid((0.032, 0.030, 0.026), 0.5, 0.6, 4, 10).translated(hx, hy, hz + 0.020)
        thumb = g.tube([(hx + s * 0.028, hy - 0.020, hz + 0.022), (hx + s * 0.027, hy + 0.002, hz + 0.028), (hx + s * 0.013, hy + 0.024, hz + 0.024)],
                       [0.0105, 0.0095, 0.0078], sides=5, samples=1, cap="round", cap_steps=1)
        p.add(f"gauntlet_{nm}", merge([back, thumb]), "EH_Bronze", f"wrist_{nm}")
        fing = [g.torus(0.0235, 0.0078, 10, 4, arc=300).rotated(0, -150, 0).translated(hx, hy + dy, hz) for dy in (-0.022, -0.007, 0.008, 0.023)]
        p.add(f"gauntlet_fingers_{nm}", merge(fing), "EH_Leather", f"wrist_{nm}", uv_scale=2)
        knuck = g.instances(g.dome(0.0060, 0.0050, 6, 1), [(hx + dx, hy, hz + 0.044) for dx in (-0.016, -0.005, 0.006, 0.017)], [(0, 0, 1)] * 4)
        p.add(f"gauntlet_knuckles_{nm}", knuck, "EH_Steel", f"wrist_{nm}", lod1=None)


# ======================================================================================= head, coronet, braid
def head(p: Piece):
    cy, cz = 1.305, 0.012
    skull = g.superellipsoid((0.0575, 0.085, 0.060), 0.92, 0.95, 7, 14).translated(0, cy, cz)
    skull = g.warp(skull, lambda P: np.column_stack([P[:, 0] * (1 - 0.28 * smoothstep(cy + 0.01, cy - 0.085, P[:, 1])), P[:, 1],
                                                     P[:, 2] + 0.006 * smoothstep(cy - 0.03, cy - 0.085, P[:, 1])]), 60)
    nose = g.tube([(0, cy + 0.016, cz + 0.052), (0, cy - 0.004, cz + 0.066), (0, cy - 0.020, cz + 0.060)], [0.0070, 0.0095, 0.0110], sides=6, samples=1, cap="round", cap_steps=1, up=(1, 0, 0))
    brow = g.rounded_box((0.096, 0.012, 0.030), 0.0055, 1).translated(0, cy + 0.026, cz + 0.044)
    brow = g.warp(brow, lambda P: np.column_stack([P[:, 0], P[:, 1] - 0.006 * (np.abs(P[:, 0]) / 0.048) ** 2, P[:, 2] - 0.012 * (np.abs(P[:, 0]) / 0.048) ** 2]), 60)
    chin = g.superellipsoid((0.016, 0.012, 0.018), 0.6, 0.6, 3, 8).translated(0, cy - 0.062, cz + 0.040)
    lip = g.tube([(-0.014, cy - 0.040, cz + 0.050), (0, cy - 0.043, cz + 0.056), (0.014, cy - 0.040, cz + 0.050)], 0.0036, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
    cheeks = [g.superellipsoid((0.011, 0.016, 0.010), 0.6, 0.6, 3, 7).translated(s * 0.034, cy - 0.016, cz + 0.044) for s in (-1, 1)]
    ears = [g.superellipsoid((0.0065, 0.016, 0.012), 0.6, 0.6, 3, 6).translated(s * 0.056, cy + 0.002, cz - 0.002) for s in (-1, 1)]
    p.add("face", merge([skull, nose, brow, chin, lip] + cheeks + ears), "EH_Skin", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.8))
    eyes = [g.superellipsoid((0.0085, 0.0040, 0.0050), 0.7, 0.7, 3, 6).rotated(0, 0, s * -6).translated(s * 0.027, cy + 0.010, cz + 0.055) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "EH_EmberVein", "head", lod1="keep", bake=False)
    nasal = g.extrude(np.array([(-0.004, 0.0), (0.004, 0.0), (0.0035, 0.07), (-0.0035, 0.07)]), 0.008, 0.002, 1).translated(0, cy - 0.030, cz + 0.062)
    p.add("nasal_guard", nasal, "EH_Bronze", "head", lod1=None)
    hair = g.superellipsoid((0.058, 0.086, 0.054), 0.85, 0.9, 6, 12).translated(0, cy + 0.006, cz - 0.046).noised(0.004, 20, 3, seed=61)
    sides = []
    for s in (-1, 1):
        sides.append(g.tube([(s * 0.056, cy + 0.030, cz + 0.020), (s * 0.066, cy - 0.020, cz + 0.004), (s * 0.064, cy - 0.074, cz - 0.014)], [0.014, 0.012, 0.004], sides=5, samples=1, cap="round", cap_steps=1))
    p.add("hair", merge([hair] + sides), "EH_Fur", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.45))
    coronet(p)


# the open nine-tine coronet: band y 1.350-1.410, tines on it up to 1.55 (5 tall) / 1.515 (4 short), ember bead on every tip, ember orb centred on a stalk
BAND_Y1 = 1.410
TINE_R = 0.094
TINE_ANGLES = [(k * 40.0, 0.140 if k in (0, 2, 4, 5, 7) else 0.105) for k in range(9)]       # 0, +-80, +-160 tall; +-40, +-120 short


def tine_poly(h):
    return np.array([(-0.025, 0.0), (0.025, 0.0), (0.0235, 0.18 * h), (0.0165, 0.45 * h), (0.009, 0.75 * h), (0.0035, 0.92 * h), (0.0, h),
                     (-0.0035, 0.92 * h), (-0.009, 0.75 * h), (-0.0165, 0.45 * h), (-0.0235, 0.18 * h)])


def coronet(p: Piece):
    band = g.lathe(np.array([(0.082, 1.350), (0.088, 1.354), (0.096, 1.368), (0.096, 1.405), (0.090, 1.410), (0.084, 1.405), (0.082, 1.360), (0.082, 1.350)]), 40, crease=45)
    p.add("crown_band", band.noised(0.0008, 34, 2, seed=30), "EH_Bronze", "head")
    p.add("crown_inlay", g.torus(0.0968, 0.0028, 40, 4).translated(0, 1.381, 0), "EH_Steel", "head", lod1=None)
    rva = [math.radians(10 + 20 * k) for k in range(18)]
    p.add("crown_rivets", g.instances(g.dome(0.0060, 0.0050, 6, 1), [(0.0965 * math.sin(a), 1.360, 0.0965 * math.cos(a)) for a in rva], [(math.sin(a), 0, math.cos(a)) for a in rva]),
          "EH_Bronze", "head", lod1=None)
    tines, ribs, beads, collars = [], [], [], []
    for a, h in TINE_ANGLES:
        ang = math.radians(a)
        m = g.extrude(tine_poly(h), 0.020, 0.004, 1).rotated(8, 0, 0).translated(0, BAND_Y1 - 0.004, TINE_R)
        tines.append(m.rotated(0, a, 0))
        rb = g.tube([(0, 0.20 * h, 0.0125), (0, 0.55 * h, 0.0115), (0, 0.86 * h, 0.0085)], [0.0042, 0.0034, 0.0016], sides=5, samples=1, cap="round", cap_steps=1, up=(1, 0, 0))
        ribs.append(rb.rotated(8, 0, 0).translated(0, BAND_Y1 - 0.004, TINE_R).rotated(0, a, 0))
        tip = V(0, h, 0)
        tip = g.rot_matrix(8, 0, 0) @ tip
        tipw = V(0, BAND_Y1 - 0.004 + tip[1], TINE_R + tip[2])
        c, s_ = math.cos(ang), math.sin(ang)
        tw = V(tipw[2] * s_, tipw[1], tipw[2] * c)
        beads.append(g.superellipsoid((0.0140, 0.0150, 0.0140), 0.9, 0.9, 4, 9).translated(*(tw + V(0, 0.002, 0))))
        collars.append(g.torus(0.0090, 0.0030, 10, 4).translated(*(tw + V(0, -0.010, 0))))
    p.add("crown_tines", merge(tines), "EH_Bronze", "head")
    p.add("crown_tine_ribs", merge(ribs), "EH_Steel", "head", lod1=None)
    p.add("crown_tine_collars", merge(collars), "EH_Bronze", "head", lod1=None)
    p.add("crown_beads", merge(beads), "EH_Gem", "head", lod1="keep", bake=False)
    # dark oxblood lining inside the band (value contrast for the bronze) + the small cap disc the orb stands on
    p.add("crown_lining", g.lathe(np.array([(0, 1.398), (0.080, 1.398), (0.082, 1.404), (0.0, 1.404)]), 28, crease=60), "EH_Cloth", "head", uv_scale=2, lod1=None)
    p.add("crown_cap", g.lathe(np.array([(0, 1.405), (0.060, 1.408), (0.060, 1.414), (0, 1.416)]), 24, crease=50), "EH_Bronze", "head")
    stalk = g.tube([(0, 1.414, 0), (0, 1.462, 0), (0, 1.510, 0)], [0.0085, 0.0070, 0.0070], sides=8, samples=1, cap=None, smooth=False)
    p.add("crown_stalk", stalk, "EH_Bronze", "head")
    p.add("crown_orb_bezel", g.torus(0.0240, 0.0040, 16, 4).translated(0, 1.510, 0), "EH_Bronze", "head")
    orb = g.superellipsoid((0.0170, 0.0170, 0.0170), 1.0, 1.0, 5, 12).translated(0, 1.528, 0)
    p.add("crown_orb", orb, "EH_Ember", "head", lod1="keep", bake=False)
    cage = [g.torus(0.0222, 0.0030, 16, 4).rotated(90, 0, a).translated(0, 1.528, 0) for a in (0, 60, 120)] + [g.torus(0.0222, 0.0030, 16, 4).translated(0, 1.528, 0)]
    p.add("crown_orb_cage", merge(cage), "EH_Bronze", "head")


def braid(p: Piece):
    path = [(0, 1.36, -0.08), (0, 1.27, -0.125), (0, 1.17, -0.142), (0.02, 1.07, -0.152), (0.026, 0.97, -0.150), (0.004, 0.89, -0.142)]
    br = g.tube(path, [0.034, 0.032, 0.029, 0.025, 0.020, 0.014], sides=10, samples=4, cap="round", cap_steps=2, twist=1080, section=lambda th, t: 1.0 + 0.30 * np.cos(3 * th + 0.0),
                up=(1, 0, 0))
    p.add("braid", br.noised(0.0016, 30, 2, seed=70), "EH_Fur", None, skin=BRAID_SKIN, uv_scale=2, tint=lambda P: np.full(len(P), 0.5))
    rings = []
    for y in (1.24, 1.07, 0.93):
        yy = np.array(path)[:, 1]
        i = int(np.argmin(np.abs(yy - y)))
        rings.append(g.torus(0.030 - 0.0025 * len(rings), 0.0060, 12, 4).translated(*path[i]))
    p.add("braid_rings", merge(rings), "EH_Bronze", None, skin=BRAID_SKIN, lod1=None)
    tail = g.tube([(0.004, 0.89, -0.142), (0.004, 0.865, -0.141), (0.004, 0.842, -0.139)], [0.012, 0.015, 0.0], sides=6, samples=1, cap=None, smooth=False)
    p.add("braid_tip", tail, "EH_Bronze", None, skin=BRAID_SKIN, lod1=None)


# ======================================================================================= summoned hammer-staff
def hammer(p: Piece):
    """Grip-local coordinates (origin = right palm, +Y toward the butt, HEAD toward -Y), translated to GRIP."""
    def W(m):
        return m.translated(*GRIP)
    hy = -0.80
    shaft = g.tube([(0, 0.30, 0), (0, -0.10, 0), (0, -0.45, 0), (0, -0.68, 0)], [0.022, 0.020, 0.0185, 0.021], sides=10, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("hammer_shaft", W(shaft.noised(0.0012, 30, 2, seed=80)), "EH_Steel", "weapon_summon", uv_scale=2)
    wraps = [g.torus(0.0225, 0.0050, 10, 4).translated(0, 0.27 - 0.0145 * i, 0) for i in range(20)] + [g.torus(0.0215, 0.0050, 10, 4).translated(0, -0.20 - 0.0145 * i, 0) for i in range(5)]
    p.add("hammer_wraps", W(merge(wraps)), "EH_Leather", "weapon_summon", uv_scale=2)
    pommel = g.superellipsoid((0.034, 0.028, 0.034), 0.6, 0.7, 5, 11).translated(0, 0.325, 0)
    collar = [g.lathe(np.array([(0.026, 0.0), (0.034, 0.008), (0.036, 0.022), (0.030, 0.032), (0.0215, 0.034)]), 12, crease=45).translated(0, y, 0) for y in (-0.255, 0.285)]
    p.add("hammer_fittings", W(merge([pommel] + collar)), "EH_Bronze", "weapon_summon")
    core = g.rounded_box((0.250, 0.175, 0.175), 0.022, 2).translated(0, hy, 0)
    p.add("hammer_head", W(core.noised(0.0018, 28, 2, seed=81)), "EH_Bronze", "weapon_summon")
    for s in (-1, 1):
        face = g.lathe(np.array([(0.0, 0.0), (0.078, 0.0), (0.086, 0.012), (0.080, 0.036), (0.0, 0.042)]), 20, crease=50).rotated(0, 0, -90 * s).translated(s * 0.118, hy, 0)
        p.add(f"hammer_face_{'R' if s > 0 else 'L'}", W(face.noised(0.0030, 24, 3, seed=82 + s)), "EH_Stone", "weapon_summon", uv_scale=2)
    hoops = [g.rounded_box((0.026, 0.196, 0.196), 0.008, 1).translated(xx, hy, 0) for xx in (-0.088, 0.088)]
    p.add("hammer_bands", W(merge(hoops)), "EH_Steel", "weapon_summon")
    spike = g.tube([(-0.125, hy, 0), (-0.190, hy, 0), (-0.255, hy - 0.012, 0)], [0.050, 0.036, 0.0], sides=8, samples=2, cap=None, smooth=True, up=(0, 0, 1))
    p.add("hammer_spike", W(spike), "EH_Bronze", "weapon_summon")
    crown = [g.tube([(0, hy - 0.088, 0), (0, hy - 0.130, 0), (0, hy - 0.175, 0)], [0.030, 0.021, 0.0], sides=6, samples=1, cap=None, smooth=False)]
    for sgn in (-1, 1):
        crown.append(g.tube([(sgn * 0.040, hy - 0.088, 0), (sgn * 0.044, hy - 0.116, 0), (sgn * 0.040, hy - 0.140, 0)], [0.016, 0.011, 0.0], sides=5, samples=1, cap=None, smooth=False))
    p.add("hammer_tines", W(merge(crown)), "EH_Bronze", "weapon_summon", lod1=None)
    seams = []
    for zf in (0.0885, -0.0885):
        for dy in (-0.045, 0.0, 0.045):
            seams.append(g.tube([(-0.072, hy + dy, zf), (0.0, hy + dy + 0.006, zf), (0.072, hy + dy, zf)], 0.0040, sides=4, samples=2, cap="round", cap_steps=1))
    core_g = g.superellipsoid((0.050, 0.030, 0.030), 0.7, 0.7, 4, 9).translated(0, hy, 0.0880)
    core_b = g.superellipsoid((0.050, 0.030, 0.030), 0.7, 0.7, 4, 9).translated(0, hy, -0.0880)
    p.add("hammer_ember_core", W(merge([core_g, core_b])), "EH_Gem", "weapon_summon", bake=False)
    p.add("hammer_ember_seams", W(merge(seams)), "EH_EmberVein", "weapon_summon", bake=False)
    tas = g.tube([(0, -0.68, 0), (0.012, -0.72, 0.01), (0.018, -0.77, 0.01)], [0.012, 0.010, 0.0], sides=5, samples=1, cap=None, smooth=False)
    p.add("hammer_tassel", W(tas), "EH_Cloth", "weapon_summon", lod1=None)


# ======================================================================================= clips
def _anim(rig):
    """Common rig of every clip: planted feet (leg IK + pelvis reach clamp), cloak and braid springs."""
    a = Animator(rig)
    M.plant_feet(a)
    a.secondary(["cape_1", "cape_2", "cape_3"], driver="top", freq=2.0, zeta=0.35, follow=0.9, accel=0.05, max_deg=22)
    a.secondary(["braid_1", "braid_2", "braid_3"], driver="top", freq=2.7, zeta=0.30, follow=1.0, accel=0.07, max_deg=26)
    return a


def _goal(a, name):
    return next(g_ for g_ in a.goals if g_.name == name)


def _ik_hands(a):
    a.goal("ik_hand_R", ("arm_R", "hand_R", "wrist_R"), spaces=(("chest", 1.0),), rot=(0, 0, 0), pole=(-0.5, -1, -0.2))
    a.goal("ik_hand_L", ("arm_L", "hand_L", "wrist_L"), spaces=(("chest", 1.0),), rot=(0, 0, 0), pole=(0.5, -1, -0.2))


def _hammer(a, pos_keys, dir_keys, grip_keys, left_w):
    """Drive the hammer-staff with both hands.  pos_keys = absolute chest-space position of the RIGHT wrist (the weapon_summon origin);
    dir_keys = haft direction hand -> hammer head; grip_keys = signed distance of the LEFT hand from the right one along the haft,
    toward the head (negative = toward the butt); left_w = IK weight of the left hand (0 = its own FK pose)."""
    gr, gl = _goal(a, "ik_hand_R"), _goal(a, "ik_hand_L")
    sg = lambda x: x if callable(x) else Curve(x)                       # noqa: E731
    P, D, S = sg(pos_keys), sg(dir_keys), sg(grip_keys)
    Rf = M.aim(A_S, D)
    gr.pos = M.abs_pos(WR0, P)
    gr.rot = Rf
    gl.pos = Fn(lambda t: P(t) + (Rf(t) @ A_S) * float(S(t)[0]) - WL0)
    gl.rot = Rf
    gl.weight = sg(left_w)
    return P, D, Rf


def _z():
    return V(0, 0, 0)


# ---------------------------------------------------------------------------------------------- Idle
def clip_idle(rig):
    a = _anim(rig)
    T = 3.6
    M.idle(a, period=T, breath=1.0, shift=0.9, sway=0.008, look=0.8, hands=True)
    a.rot("wrist_L", Wave(V(-2.0, 0, 0), 1 / T, 0.55))                  # fingers breathe
    a.rot("wrist_R", Wave(V(-2.5, 0, 0), 1 / T, 0.60))
    a.rot("top", Wave(V(1.6, 0, 0), 1 / T, 0.30))                       # cloak settles
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- Move
def clip_move(rig):
    a = _anim(rig)
    T = 1.0
    M.biped_gait(a, T, stride=0.04, lift=0.055, duty=0.6, bob=0.016, sway=0.012, roll=3.0, twist=4.5, lean=4.5, arm_swing=(7, 7), elbow=10,
                 toe_off=20, strike=-6, head_stab=0.5)
    a.rot("top", Wave(V(2.5, 0, 0), 2 / T, 0.15))
    a.rot("wrist_L", Wave(V(4, 0, 0), 1 / T, 0.30))
    a.rot("wrist_R", Wave(V(-4, 0, 0), 1 / T, 0.30))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- HitReact
def clip_hit(rig):
    a = _anim(rig)
    T = 0.5
    z = _z()
    a.pos("body", Curve([(0, z), (0.08, V(0, -0.026, -0.060), "out_cubic"), (0.20, V(0, -0.010, -0.022), "in_out_cubic"), (0.32, V(0, -0.012, 0.008), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.08, V(-8, 2, 3), "out_cubic"), (0.20, V(2, -1, -1), "in_out_cubic"), (0.32, V(-1, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.095, V(-8, 3, 2), "out_cubic"), (0.22, V(3, -2, 0), "in_out_cubic"), (0.34, V(-1.2, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.11, V(-10, 4, 3), "out_cubic"), (0.24, V(3, -3, -1), "in_out_cubic"), (0.36, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.12, V(-12, 6, 4), "out_cubic"), (0.26, V(4, -4, -1), "in_out_cubic"), (0.38, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.13, V(-14, 8, 5), "out_cubic"), (0.28, V(5, -4, -2), "in_out_cubic"), (0.40, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.10, V(0, 0, 5), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.10, V(0, 0, -5), "out_cubic"), (T, z, "in_out_cubic")]))
    for s, sg in (("L", 1), ("R", -1)):                                  # arms fling out and back, forearms trail
        a.rot(f"arm_{s}", Curve([(0, z), (0.10, V(11, 0, sg * 7), "out_cubic"), (0.24, V(-4, 0, sg * 2), "in_out_cubic"), (T, z, "in_out_cubic")]))
        a.rot(f"hand_{s}", Curve([(0, z), (0.12, V(8, 0, 0), "out_cubic"), (0.26, V(-12, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
        a.rot(f"wrist_{s}", Curve([(0, z), (0.14, V(10, 0, 0), "out_cubic"), (0.28, V(-8, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.1, V(0, 0, -0.012), "out_cubic"), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.25)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Victory
def clip_victory(rig):
    a = _anim(rig)
    T = 2.0
    z = _z()
    a.pos("body", Curve([(0, z), (0.18, V(0, -0.016, 0), "in_out_cubic"), (0.62, V(0, 0.020, 0.008), ("spring", 0.2, 1.5)), (T, V(0, 0.016, 0.008), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.18, V(3, 0, 0)), (0.62, V(-3, -4, -1), "out_cubic"), (T, V(-2, -3, -1), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.18, V(4, 0, 0)), (0.66, V(-6, -3, 0), ("spring", 0.15, 1.5)), (T, V(-5, -2, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.18, V(5, 0, 0)), (0.68, V(-9, -5, 0), ("spring", 0.15, 1.5)), (T, V(-8, -3, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.7, V(-6, 4, 0), "out_cubic"), (T, V(-5, 3, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.72, V(-10, 6, 0), ("spring", 0.15, 1.5)), (T, V(-9, 5, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.20, V(0, 0, 2), "in_out_cubic"), (0.70, V(0, 0, -10), "out_cubic"), (T, V(0, 0, -10))]))
    a.rot("clavicle_L", Curve([(0, z), (0.70, V(0, 0, 4), "out_cubic"), (T, V(0, 0, 4))]))
    # right fist thrust skyward (anticipation: drops back first), forearm and wrist whip after the arm
    a.rot("arm_R", Curve([(0, z), (0.20, V(14, 0, -4), "in_out_cubic"), (0.62, V(-146, 0, -14), ("spring", 0.10, 1.5)), (T, V(-146, 0, -14), "in_out_cubic")]))
    a.rot("hand_R", Curve([(0, z), (0.20, V(10, 0, 0), "in_out_cubic"), (0.66, V(-24, 0, 0), ("spring", 0.18, 1.5)), (T, V(-24, 0, 0), "in_out_cubic")]))
    a.rot("wrist_R", Curve([(0, z), (0.70, V(-14, 0, 0), ("spring", 0.2, 1.5)), (T, V(-14, 0, 0), "in_out_cubic")]))
    a.rot("arm_L", Curve([(0, z), (0.24, V(6, 0, 4), "in_out_cubic"), (0.80, V(-14, 0, 14), ("spring", 0.12, 1.5)), (T, V(-12, 0, 13), "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.80, V(-30, 0, 0), ("spring", 0.12, 1.5)), (T, V(-28, 0, 0), "in_out_cubic")]))
    a.rot("top", Curve([(0, z), (0.9, V(10, 0, 0), "in_out_cubic"), (T, V(8, 0, 0), "in_out_cubic")]))
    for nm in ("foot_L", "foot_R"):
        M.set_foot(a, nm, rot=Curve([(0, z), (0.25, z), (0.6, V(6, 0, 0), "out_cubic"), (T, V(6, 0, 0))]),
                   pos=Curve([(0, z), (0.25, z), (0.6, V(0, 0.006, 0), "out_cubic"), (T, V(0, 0.006, 0))]))
    a.rot("chest", Wave(V(-0.6, 0, 0), 1.0, 0.0) * step_signal([(0.9, 0), (1.3, 1)]))      # breathes in the held pose
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Taunt
def clip_taunt(rig):
    """A hammer flashes into her fist (ember flicker), she weighs it, lets it burn out, then leans back and points at the enemy king."""
    a = _anim(rig)
    T = 1.4
    z = _z()
    a.rot("arm_R", Curve([(0, z), (0.22, V(-30, 0, -3), "out_cubic"), (0.62, V(-34, 0, -3)), (0.90, V(-92, 0, -5), "out_cubic"), (1.10, V(-95, 0, -5), {"tan": "flat"}), (T, z, "in_out_cubic")]))
    a.rot("hand_R", Curve([(0, z), (0.22, V(-20, 0, 0), "out_cubic"), (0.62, V(-24, 0, 0)), (0.90, V(-6, 0, 0), "out_cubic"), (1.10, V(-5, 0, 0)), (T, z, "in_out_cubic")]))
    a.rot("wrist_R", Curve([(0, z), (0.30, V(-18, 0, 0), "out_cubic"), (0.62, V(-14, 0, 0)), (0.90, V(8, 0, 0), ("spring", 0.2, 1.5)), (T, z, "in_out_cubic")]))
    a.rot("arm_L", Curve([(0, z), (0.30, V(5, 0, 12), "out_cubic"), (0.70, V(6, 0, 15), "in_out_cubic"), (T, z, "in_out_cubic")]))              # hand on hip
    a.rot("hand_L", Curve([(0, z), (0.30, V(-62, 0, 0), "out_cubic"), (0.70, V(-70, 0, 0)), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.9, V(0, 0, -4), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.22, V(-3, 0, 0), "out_cubic"), (0.88, V(-5, -3, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.22, V(-4, 0, 0), "out_cubic"), (0.88, V(-6, -5, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.24, V(-3, 0, 2), "out_cubic"), (0.90, V(-5, -4, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.24, V(-6, 0, 5), "out_cubic"), (0.90, V(-8, -6, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.40, V(-2, 0, 3), "in_out_cubic"), (1.00, V(-2, 0, -3), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.pos("body", Curve([(0, z), (0.30, V(0.006, -0.006, 0), "in_out_cubic"), (0.90, V(-0.004, 0.012, 0.03), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("top", Curve([(0, z), (0.3, V(-8, 0, 0), "out_cubic"), (0.9, V(5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.30, V(0, 0, -0.035), "in_out_cubic"), (1.0, V(0, 0, -0.035)), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Surrender
def clip_surrender(rig):
    """Stagger, then a one-knee KNEEL (left foot planted, right knee on the plinth, shin and instep flat), the torso folds, the coronet bows,
    both hands open palm-up and lowered onto the thighs.  She holds nothing, so there is nothing to drop."""
    a = _anim(rig)
    T = 2.4
    z = _z()
    sk = a.sk
    L1 = float(np.linalg.norm(sk.rest[sk.ix["shin_R"]] - sk.rest[sk.ix["thigh_R"]]))
    L2 = float(np.linalg.norm(sk.rest[sk.ix["foot_R"]] - sk.rest[sk.ix["shin_R"]]))
    KNEE_Y = 0.272                                  # kneeling knee axis above world 0 (plinth top 0.22 + greave radius)
    DROP = JOINTS["hip_L"][1] - (KNEE_Y + L1)
    PZ = 0.05
    a.pos("body", Curve([(0, z), (0.30, V(0, -0.012, -0.040), "out_cubic"), (0.55, V(0, -0.020, -0.020), "in_out_cubic"), (1.38, V(0, -DROP, PZ), "in_out_cubic"),
                         (1.60, V(0, -DROP + 0.007, PZ), "out_cubic"), (1.95, V(0, -DROP, PZ), "in_out_cubic"), (T, V(0, -DROP - 0.004, PZ), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.30, V(-6, 0, 0), "out_cubic"), (0.55, z, "in_out_cubic"), (1.38, V(3, 0, -2), "in_out_cubic"), (T, V(4, 0, -2), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.30, V(-3, 0, 0), "out_cubic"), (0.9, V(3, 0, 0), "in_out_cubic"), (1.6, V(7, 0, 0), "in_out_cubic"), (T, V(8, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.30, V(-2, 0, 0), "out_cubic"), (0.9, V(2, 0, 0), "in_out_cubic"), (1.7, V(5, 0, 0), "in_out_cubic"), (T, V(6, 0, 0.0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.30, V(-4, 0, 0), "out_cubic"), (1.0, V(5, 0, 0), "in_out_cubic"), (1.75, V(8, 0, 0), "in_out_cubic"), (T, V(9, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.30, V(-10, 0, 0), "out_cubic"), (1.0, V(6, 0, 0), "in_out_cubic"), (1.75, V(13, 2, 3), "in_out_cubic"), (T, V(15, 2, 4), "in_out_cubic")]))
    comp = Curve([(0, z), (0.55, z, "in_out_cubic"), (1.38, V(0, 1, 0), "in_out_cubic"), (T, V(0, 1, 0))])         # skirt gathers as she sinks
    a.pos("skirt_1", Fn(lambda t: comp(t) * (DROP * 0.20)))
    a.pos("skirt_2", Fn(lambda t: comp(t) * (DROP * 0.46)))
    a.rot("clavicle_R", Curve([(0, z), (1.0, V(0, 0, 4), "in_out_cubic"), (T, V(0, 0, 6))]))
    a.rot("clavicle_L", Curve([(0, z), (1.0, V(0, 0, -4), "in_out_cubic"), (T, V(0, 0, -6))]))
    # arms: hang loose through the stagger, then the forearms turn palm-up and settle on the thighs
    for s, sg in (("L", 1), ("R", -1)):
        a.rot(f"arm_{s}", Curve([(0, z), (0.30, V(8, 0, sg * 6), "out_cubic"), (1.2, V(-22, 0, sg * 3), "in_out_cubic"), (1.8, V(-30, 0, sg * 2), "in_out_cubic"), (T, V(-31, 0, sg * 2), "in_out_cubic")]))
        a.rot(f"hand_{s}", Curve([(0, z), (0.30, V(6, 0, 0), "out_cubic"), (1.2, V(-48, 0, 0), "in_out_cubic"), (1.8, V(-56, 0, 0), "in_out_cubic"), (T, V(-57, 0, 0), "in_out_cubic")]))
        a.rot(f"wrist_{s}", Curve([(0, z), (0.5, V(10, 0, 0), "in_out_cubic"), (1.4, V(-34, 0, 0), "in_out_cubic"), (T, V(-40, 0, 0), "in_out_cubic")]))
    a.rot("top", Curve([(0, z), (0.9, V(16, 0, 0), "in_out_cubic"), (1.4, V(8, 0, 0), "in_out_cubic"), (T, V(11, 0, 0))]))
    ankL = V(0.0, 0.0, PZ + 0.165 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.55, z), (0.85, ankL + V(0, 0.06, -0.06), "in_out_cubic"), (1.15, ankL, "in_out_cubic"), (T, ankL)]),
               rot=Curve([(0, z), (0.55, z), (0.70, V(18, 0, 0), "in_out_cubic"), (0.95, V(-10, 0, 0), "in_out_cubic"), (1.15, z, "in_out_cubic"), (T, z)]))
    ankR = V(0.0, KNEE_Y - JOINTS["ankle_L"][1], PZ - L2 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.60, z), (1.00, ankR + V(0, 0.10, 0.10), "in_out_cubic"), (1.38, ankR, "in_out_cubic"), (T, ankR)]),
               rot=Curve([(0, z), (0.60, z), (1.00, V(95, 0, 0), "in_out_cubic"), (1.38, V(172, 0, 0), "in_out_cubic"), (T, V(172, 0, 0))]))
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Attack
IMPACT = 1.30
SP0, SP1 = 0.42, 0.92                      # spin window
TW = 1.08                                  # wind-up peak (held to TW + 0.04), then the cleave lands at IMPACT
nrm = lambda v: np.asarray(v, float) / np.linalg.norm(v)                 # noqa: E731
P_SUM, D_SUM = V(-0.12, 1.08, 0.34), nrm((-0.05, 0.50, 0.87))             # hammer forged in the air ahead of her
P_SPIN, D_SPIN = V(-0.14, 1.00, 0.28), nrm((0.97, -0.05, 0.25))           # held across the body, head out to her left for the spin
P_WIND, D_WIND = V(-0.10, 1.34, 0.10), nrm((-0.15, 0.82, -0.55))          # overhead, head high behind her
D_MID = nrm((-0.10, 0.55, 0.83))                                          # the cleave sweeps over the top
P_HIT, D_HIT = V(-0.08, 0.99, 0.30), nrm((-0.05, -0.74, 0.67))
P_FOL, D_FOL = V(-0.08, 0.95, 0.30), nrm((-0.06, -0.80, 0.60))


def _slerp(a, b, u):
    a, b = nrm(a), nrm(b)
    d = float(np.clip(a @ b, -1, 1))
    th = math.acos(d)
    if th < 1e-5:
        return a
    return (math.sin((1 - u) * th) * a + math.sin(u * th) * b) / math.sin(th)


def spin_prog(t):
    u = min(max((t - SP0) / (SP1 - SP0), 0.0), 1.0)
    return u * u * (3 - 2 * u)


def psi(t):
    return -360.0 * spin_prog(t)


def clip_attack(rig):
    a = _anim(rig)
    _ik_hands(a)
    T, I = 2.4, IMPACT
    z = _z()
    TA = TW + 0.04                                                    # end of the wind-up hold = start of the cleave
    TM = 0.5 * (TA + I)

    def cleave_u(t):
        u = min(max((t - TA) / (I - TA), 0.0), 1.0)
        return u ** 2.4                                                # accelerates all the way into the blow

    Pc = Curve([(0, WR0), (0.22, V(-0.20, 0.94, 0.26), "in_out_cubic"), (0.40, P_SUM, "in_out_cubic"), (0.60, P_SPIN, "in_out_cubic"), (0.80, P_SPIN),
                (TW, P_WIND, "anticipate"), (TA, P_WIND + V(0, 0.01, -0.01), {"tan": "flat"}), (I, P_HIT, "snap_in"), (1.42, P_FOL, "out_cubic"),
                (1.60, P_FOL, {"tan": "flat"}), (1.90, V(-0.17, 0.98, 0.30), "in_out_cubic"), (T, WR0, "in_out_cubic")])
    Dc = Curve([(0, A_S), (0.22, nrm((0, 0.05, 1.0)), "in_out_cubic"), (0.40, D_SUM, "in_out_cubic"), (0.60, D_SPIN, "in_out_cubic"), (0.80, D_SPIN),
                (TW, D_WIND, "anticipate"), (TA, D_WIND, {"tan": "flat"}), (I, D_HIT, "snap_in"), (1.42, D_FOL, "out_cubic"),
                (1.60, D_FOL, {"tan": "flat"}), (1.90, nrm((0, -0.5, 0.85)), "in_out_cubic"), (T, A_S, "in_out_cubic")])
    Sc = Curve([(0, 0.0), (0.58, 0.17, "in_out_cubic"), (0.78, 0.17), (1.0, 0.02), (TA, -0.22), (I, -0.20), (1.6, -0.20), (2.0, 0.0, "in_out_cubic"), (T, 0.0)])

    def P_fn(t):
        if TA < t < I:
            e = cleave_u(t)
            return P_WIND + V(0, 0.01, -0.01) + (P_HIT - P_WIND - V(0, 0.01, -0.01)) * e + V(0.0, 0.05, 0.09) * math.sin(math.pi * e)
        return Pc(t)

    def D_fn(t):
        if TA < t < I:
            e = cleave_u(t)
            s = 2 * e
            return _slerp(D_WIND, D_MID, s) if s < 1 else _slerp(D_MID, D_HIT, s - 1)
        return Dc(t)
    P, D, _ = _hammer(a, Fn(P_fn), Fn(D_fn), Sc, [(0, 0), (0.36, 0), (0.60, 1, "in_out_cubic"), (1.78, 1), (2.16, 0, "in_out_cubic"), (T, 0)])
    # free left arm while the right hand conjures the hammer (the left IK takes the haft from 0.40 to 0.60)
    a.rot("arm_L", Curve([(0, z), (0.24, V(-14, 0, 8), "out_cubic"), (0.50, V(-20, 0, 10), "in_out_cubic"), (T, V(-20, 0, 10))]))
    a.rot("hand_L", Curve([(0, z), (0.30, V(-30, 0, 0), "out_cubic"), (T, V(-30, 0, 0))]))

    # ---- pelvis leads: coil, spring up through the spin, sink into the wind-up, LUNGE into the blow just ahead of the weapon, squash on impact
    a.pos("body", Curve([(0, z), (0.20, V(0, -0.020, -0.012), "in_out_cubic"), (0.42, V(0, -0.034, -0.020), "in_out_cubic"), (0.66, V(0, 0.014, 0.0), "in_out_cubic"),
                         (0.92, V(0, 0.004, -0.010), "in_out_cubic"), (TW, V(0, -0.014, -0.040), "in_out_cubic"), (I - 0.05, V(0, -0.040, 0.200), "snap_in"),
                         (1.36, V(0, -0.062, 0.215), "out_cubic"), (1.56, V(0, -0.050, 0.210), {"tan": "flat"}), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.20, V(3, 0, 0), "in_out_cubic"), (0.42, V(5, 0, 0), "in_out_cubic"), (0.66, V(-1, 0, 0), "in_out_cubic"), (TW, V(-6, 0, 0), "in_out_cubic"),
                         (I - 0.07, V(6, 0, 0), "snap_in"), (1.36, V(5, 0, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Fn(lambda t: V(0, psi(t), 0)))
    bell = lambda t: math.sin(math.pi * spin_prog(t))                  # noqa: E731
    a.rot("spine", Curve([(0, z), (0.20, V(2, 0, 0), "in_out_cubic"), (0.42, V(-4, 0, 0), "in_out_cubic"), (0.70, V(-3, 0, 0), "in_out_cubic"), (TW, V(-11, -8, -1), "in_out_cubic"),
                          (I - 0.04, V(8, 4, 1), "snap_in"), (1.36, V(6, 4, 1), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Fn(lambda t: V(0, 20.0 * bell(t), 0)))                # upper body trails the hips through the spin
    a.rot("chest", Curve([(0, z), (0.20, V(1, 0, 0), "in_out_cubic"), (0.42, V(-3, 0, 0), "in_out_cubic"), (0.70, V(-2, 0, 0), "in_out_cubic"), (TW, V(-10, -10, -2), "in_out_cubic"),
                          (I - 0.02, V(8, 5, 2), "snap_in"), (1.36, V(6, 5, 1), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Fn(lambda t: V(0, 16.0 * bell(t), 0)))

    def head_rel(t):                                                  # head spots ahead of the turn, then the body catches up
        u = min(max((t - SP0) / (SP1 - SP0), 0.0), 1.0)
        q = min(max((u - 0.12) / 0.55, 0.0), 1.0)
        return -360.0 * (q * q * (3 - 2 * q)) - psi(t) - 20.0 * bell(t) * 0.0
    a.rot("neck", Curve([(0, z), (0.20, V(4, 0, 0), "in_out_cubic"), (TW, V(-6, 8, 0), "in_out_cubic"), (I + 0.04, V(8, -4, 0), "snap_in"), (1.36, V(6, -4, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Fn(lambda t: V(0, 0.35 * head_rel(t) - 7.0 * bell(t), 0)))
    a.rot("head", Curve([(0, z), (0.20, V(4, 0, 0), "in_out_cubic"), (TW, V(-5, 6, 0), "in_out_cubic"), (I + 0.06, V(7, -4, 0), "snap_in"), (1.40, V(5, -4, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Fn(lambda t: V(0, 0.65 * head_rel(t) - 13.0 * bell(t), 0)))
    a.rot("clavicle_R", Curve([(0, z), (0.72, V(0, 0, -4), "in_out_cubic"), (TW, V(0, 0, -9), "in_out_cubic"), (I, V(0, 0, 3), "snap_in"), (1.4, V(0, 0, 3)), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.72, V(0, 0, 4), "in_out_cubic"), (TW, V(0, 0, 8), "in_out_cubic"), (I, V(0, 0, -3), "snap_in"), (1.4, V(0, 0, -3)), (T, z, "in_out_cubic")]))

    # ---- feet pivot with the spin (alternating small lifts), then the left foot steps INTO the lunge and holds; the right drags back; both re-centre
    lunL = Curve([(0, z), (0.98, z), (1.10, V(0, 0.07, 0.10), "in_out_cubic"), (1.24, V(0, 0, 0.235), "in_out_cubic"), (1.62, V(0, 0, 0.235)), (1.80, V(0, 0.06, 0.12), "in_out_cubic"), (2.04, z, "in_out_cubic")])
    lunR = Curve([(0, z), (1.02, z), (1.26, V(0, 0, -0.05), "in_out_cubic"), (1.62, V(0, 0, -0.05)), (2.08, z, "in_out_cubic")])
    pitL = Curve([(0, z), (0.98, z), (1.06, V(20, 0, 0), "in_out_cubic"), (1.18, V(-9, 0, 0), "in_out_cubic"), (1.26, z, "in_out_cubic"),
                  (1.64, z), (1.72, V(16, 0, 0), "in_out_cubic"), (1.90, V(-6, 0, 0), "in_out_cubic"), (2.04, z, "in_out_cubic")])

    def foot_spin(t, side):
        ang = math.radians(psi(t))
        ax, az = side * JOINTS["ankle_L"][0], JOINTS["ankle_L"][2]
        c, s = math.cos(ang), math.sin(ang)
        x, zz = ax * c + az * s, -ax * s + az * c
        u = min(max((t - SP0) / (SP1 - SP0), 0.0), 1.0)
        lift = 0.04 * max(0.0, side * math.sin(3 * math.pi * u)) if 0 < u < 1 else 0.0
        return V(x - ax, lift, zz - az)
    for nm, side, lun in (("foot_L", 1, lunL), ("foot_R", -1, lunR)):
        gg = _goal(a, nm)
        gg.pos = Fn(lambda t, side=side, lun=lun: foot_spin(t, side) + lun(t))
        gg.rot = Fn(lambda t, nm=nm: V(0, psi(t), 0) + (pitL(t) if nm == "foot_L" else V(0, 0, 0)))
    return a, T, False, 60, (I,)


def make_clips(rig):
    out = []
    for name, fn in (("Idle", clip_idle), ("Move", clip_move), ("Attack", clip_attack), ("HitReact", clip_hit), ("Victory", clip_victory),
                     ("Taunt", clip_taunt), ("Surrender", clip_surrender)):
        a, dur, loop, fps, keep = fn(rig)
        c = a.bake(name, dur, loop=loop, fps=fps, keep_times=keep)
        if name == "Attack":                                           # forged from embers, held, dissolved again
            c.keys("weapon_summon", "scale", [(0, 0.0), (0.05, 0.0), (0.30, 1.15, "out_cubic"), (0.40, 1.0, "in_out_cubic"), (1.90, 1.0), (2.30, 0.0, "in_cubic"), (dur, 0.0)])
        elif name == "Taunt":                                          # a brief hammer flash in her fist
            c.keys("weapon_summon", "scale", [(0, 0.0), (0.10, 0.0), (0.30, 0.65, "out_cubic"), (0.62, 0.0, "in_cubic"), (dur, 0.0)])
        else:
            c.keys("weapon_summon", "scale", [(0, 0.0), (dur, 0.0)])
        out.append(c)
    return out


# ======================================================================================= build
def impact_socket(rig):
    """Place socket_impact (under body) exactly where the hammer head meets the board at impactTime."""
    a, dur, loop, fps, keep = clip_attack(rig)
    ix = a.sk.ix
    c = a.pose(keep[0])
    R = c.Rw[ix["wrist_R"]]
    ph = c.Pw[ix["wrist_R"]] + R @ V(0, -0.80, 0)
    pc = V(ph[0], 0.05, ph[2])
    Rb, Pb = c.Rw[ix["body"]], c.Pw[ix["body"]]
    return rig.pos("body") + Rb.T @ (pc - Pb)


def build(log=print):
    rig = make_rig()
    rig.socket("socket_impact", "body", tuple(impact_socket(rig)))
    p = Piece("emberhold", "queen", rig, make_clips(rig), impact_time=IMPACT, strike_range=0.70, attack_style="summon", seed=11)
    C.pedestal_parts(p)
    legs(p)
    skirt(p)
    torso(p)
    yoke_and_cloak(p)
    arms(p)
    head(p)
    braid(p)
    hammer(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris (+{p.node_tri_count()} on weapon_summon) before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
