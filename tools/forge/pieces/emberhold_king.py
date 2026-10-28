"""emberhold_king - Emberhold Ember Sovereign.

An older, broad-shouldered highland king in battle-worn bronze plate: layered cuirass (gambeson, breastplate with a
central ridge, plackart and lame bands), massive telescoping pauldrons (the right one cracked and spiked), a heavy fur
mantle, a front-split tabard over tassets and cuisses, a pelted cloak, a tall CLOSED crown (band, four fleurons, two
crossing arches over an oxblood velvet cap, orb) topped by a bronze cross-pattee with an ember gem, and a great
leaf-bladed greatsword planted point-down before him under both gauntlets.
Built from docs/art/emberhold_king.md on the full humanoid skeleton: smooth-skinned limbs/torso/cloak, rigid armour
plates, both hands IK-pinned to the grip through every clip, procedural IK/gait/strike animation baked to dense tracks.
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
from anim.curves import step_signal, pulse         # noqa: E402
import _emberhold_common as C                      # noqa: E402

ASSET_ID = "emberhold_king"
SW_X, SW_Z = -0.08, 0.24          # sword axis
Y_TIP = 0.222

BODY = C.Body(Y=[0.76, 0.84, 0.90, 0.96, 1.04, 1.12, 1.20, 1.26, 1.30, 1.34],
              RX=[0.170, 0.158, 0.152, 0.158, 0.175, 0.196, 0.212, 0.206, 0.172, 0.100],
              RZ=[0.115, 0.108, 0.104, 0.108, 0.114, 0.121, 0.122, 0.113, 0.092, 0.072],
              ZC=[0, 0, 0, 0, 0.002, 0.005, 0.008, 0.010, 0.010, 0.010])

# ======================================================================================= rig
WR0 = np.array([SW_X, 1.130, SW_Z])      # rest wrist_R (right hand, low on the grip)
WL0 = np.array([SW_X, 1.205, SW_Z])      # rest wrist_L (left hand stacked above)
JOINTS = dict(pelvis=(0, 0.76, 0), spine=(0, 0.90, 0), chest=(0, 1.08, 0), neck=(0, 1.24, 0.005), head=(0, 1.30, 0.01), top=(0, 1.30, -0.12),
              clavicle_L=(0.09, 1.27, 0), shoulder_L=(0.31, 1.30, 0), elbow_L=(0.22, 1.10, 0.17), wrist_L=tuple(WL0),
              hip_L=(0.11, 0.78, 0), knee_L=(0.14, 0.54, 0.085), ankle_L=(0.13, 0.27, 0.04), toe_L=(0.13, 0.245, 0.15),
              clavicle_R=(-0.09, 1.27, 0), shoulder_R=(-0.31, 1.30, 0), elbow_R=(-0.27, 1.06, 0.12), wrist_R=tuple(WR0),
              hip_R=(-0.11, 0.78, 0), knee_R=(-0.14, 0.54, 0.085), ankle_R=(-0.13, 0.27, 0.04), toe_R=(-0.13, 0.245, 0.15))
J_ = lambda k: np.array(JOINTS[k], dtype=float)      # noqa: E731
V = lambda *x: np.array(x, dtype=float)              # noqa: E731
CAPE = [(0, 1.10, -0.20), (0, 0.80, -0.24), (0, 0.50, -0.26)]


def make_rig() -> Rig:
    r = humanoid_rig(JOINTS, weapon=(SW_X, 0.70, SW_Z), cape=CAPE)
    r.socket("socket_weapon_R", "weapon", (SW_X, Y_TIP, SW_Z))
    r.socket("socket_cast", "body", (0, 0.90, 0.30))
    r.socket("socket_impact", "body", (-0.02, 0.70, 0.60))
    r.socket("socket_head", "head", (0, 1.58, 0))
    return r


# ---- smooth-skin recipes: chains blend neighbouring bones around each joint; armour plates stay rigid
LEG_SKIN = {s: Skin.chain([f"thigh_{s}", f"shin_{s}", f"foot_{s}"], pre="body", tip=JOINTS[f"toe_{s}"], zone=0.4) for s in "LR"}
ARM_SKIN = {s: Skin.chain([f"arm_{s}", f"hand_{s}"], pre=f"clavicle_{s}", tip=JOINTS[f"wrist_{s}"], zone=0.42) for s in "LR"}
TORSO_SKIN = Skin.chain(["body", "spine", "chest"], tip=JOINTS["neck"], zone=0.45)
NECK_SKIN = Skin.chain(["neck", "head"], pre="chest", tip=(0, 1.40, 0.012), zone=0.4)
CLOAK_SKIN = Skin.chain(["top", "cape_1", "cape_2", "cape_3"], pre="chest", tip=(0, 0.33, -0.27), zone=0.45)
_HANG = Skin.nearest([("body", J_("pelvis"), J_("spine")), ("thigh_L", J_("hip_L"), J_("knee_L")), ("thigh_R", J_("hip_R"), J_("knee_R"))], tau=0.035, bias={"body": 1.5})
SKIRT_SKIN = Skin.gradient(Skin.rigid("body"), _HANG, axis=1, v0=0.84, v1=0.66)    # waist follows the pelvis, the hem the thighs


def tuft_mesh(scale=1.0):
    return g.tube([(0, 0, 0), (0.004, 0.016 * scale, 0.004), (0.010, 0.028 * scale, 0.012)], [0.024 * scale, 0.015 * scale, 0.0], sides=5, samples=1,
                  cap=None, smooth=False, up=(0, 0, 1))


# ======================================================================================= legs
def lerp3(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


def legs(p: Piece):
    for s, nm in ((1, "L"), (-1, "R")):
        hip, knee, ank = J_(f"hip_{nm}"), J_(f"knee_{nm}"), J_(f"ankle_{nm}")
        x = s * 0.13
        # continuous cloth hose with dense rings at the knee (smooth skin bends it without pinching)
        hose = limb_tube([hip + [0, 0.03, 0], lerp3(hip, knee, 0.5) + [0, 0, 0.004], knee, lerp3(knee, ank, 0.5), ank + [0, 0.01, 0]],
                         [0.074, 0.066, 0.056, 0.050, 0.046], joints=[knee], spacing=0.05, joint_spacing=0.022, joint_zone=0.06, sides=8, cap=None, up=(0, 0, 1))
        p.add(f"hose_{nm}", hose, "EH_Cloth", None, skin=LEG_SKIN[nm], uv_scale=2, tint=lambda P: np.full(len(P), 0.55))
        # boot: shaft + foot + toe plate rigid on the foot
        sole = g.superellipsoid((0.060, 0.014, 0.118), 0.4, 0.55, 3, 10).translated(x, 0.232, 0.05)
        foot = g.superellipsoid((0.058, 0.036, 0.112), 0.5, 0.62, 5, 12).translated(x, 0.262, 0.044)
        shaft = g.tube([(x, 0.345, 0.042), (x, 0.275, 0.044)], [0.054, 0.058], sides=10, samples=1, cap=None, smooth=False)
        p.add(f"boot_{nm}", merge([foot, shaft]), "EH_Leather", f"foot_{nm}", uv_scale=2)
        p.add(f"boot_sole_{nm}", sole, "EH_Steel", f"foot_{nm}", lod1=None)
        toe = g.superellipsoid((0.050, 0.026, 0.044), 0.5, 0.6, 4, 9).translated(x, 0.266, 0.128)
        p.add(f"boot_toe_{nm}", toe, "EH_Bronze", f"foot_{nm}")
        # greave: plate tube along the shin (rigid on shin), cop on the knee
        g0, g1 = lerp3(knee, ank, 0.90) + [0, 0, 0.012], lerp3(knee, ank, 0.12) + [0, 0, 0.012]
        gm = lerp3(g0, g1, 0.5) + [s * 0.003, 0, 0.004]
        greave = g.tube([g0, gm, g1], [0.058, 0.063, 0.070], sides=10, samples=2, cap=None, up=(0, 0, 1)).noised(0.003, 36, 2, seed=3 + s)
        p.add(f"greave_{nm}", greave, "EH_Bronze", f"shin_{nm}")
        for i, (pt, rr) in enumerate(((g0, 0.060), (g1, 0.072))):
            p.add(f"greave_lip_{nm}{i}", g.torus(rr, 0.0055, 16, 4).translated(*pt), "EH_Bronze", f"shin_{nm}", lod1=None)
        fin = g.extrude_plane(np.array([(0.30, 0.05), (0.30, 0.13), (0.44, 0.10), (0.46, 0.05)]), 0.010, "YZ", bevel=0.003, bevel_segments=1).translated(x + s * 0.062, 0, 0)
        p.add(f"greave_fin_{nm}", fin, "EH_Bronze", f"shin_{nm}", lod1=None)
        kc = knee + [s * 0.002, 0.0, 0.052]
        cop = g.superellipsoid((0.058, 0.050, 0.036), 0.6, 0.6, 5, 11).translated(*kc)
        p.add(f"knee_{nm}", cop.noised(0.0014, 32, 2, seed=5), "EH_Bronze", f"shin_{nm}")
        kf = g.extrude_plane(np.array([(0.50, 0.04), (0.50, 0.118), (0.56, 0.104), (0.575, 0.04)]), 0.011, "YZ", bevel=0.0035, bevel_segments=1).translated(x + s * 0.080, 0, 0)
        p.add(f"knee_fin_{nm}", kf, "EH_Bronze", f"shin_{nm}", lod1=None)
        # cuisse (thigh plate) rising into the skirt (rigid on the thigh)
        c0, c1 = lerp3(hip, knee, 0.86), lerp3(hip, knee, 0.10)
        cm = lerp3(c0, c1, 0.5)
        cuisse = g.tube([c0 + [0, 0, 0.008], cm + [0, 0, 0.008], c1 + [0, 0, 0.008]], [0.066, 0.074, 0.082], sides=10, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"cuisse_{nm}", cuisse.noised(0.002, 30, 2, seed=8 + s), "EH_Bronze", f"thigh_{nm}")
        p.add(f"cuisse_lip_{nm}", g.torus(0.073, 0.0055, 16, 4).translated(*(c0 + [0, 0, 0.008])), "EH_Bronze", f"thigh_{nm}", lod1=None)
        rv = [lerp3(hip, knee, u) + [s * 0.085 - s * 0.02 * u, 0, 0.012] for u in (0.25, 0.45, 0.65)]
        p.add(f"cuisse_rivets_{nm}", g.instances(g.dome(0.0075, 0.006, 6, 1), rv, [(s, 0, 0.1)] * 3), "EH_Bronze", f"thigh_{nm}", lod1=None)


def skirt_and_belt(p: Piece):
    # tabard skirt: open loft with a front split, folds growing toward the hem
    ys = [0.925, 0.86, 0.80, 0.74, 0.68, 0.62, 0.565]
    R = [0.150, 0.162, 0.176, 0.189, 0.200, 0.208, 0.212]
    rings = []
    for y, r in zip(ys, R):
        th = np.radians(np.linspace(30, 330, 40))
        f = 1 + (0.012 + 0.05 * float(smoothstep(0.80, 0.565, y))) * (0.6 * np.cos(11 * th + 0.5) + 0.4 * np.cos(17 * th + 1.7))
        rings.append(np.stack([r * f * np.sin(th) * 1.05, np.full(40, y), r * f * np.cos(th) * 0.92 - 0.004], 1))
    sk = g.loft(np.stack(rings[::-1]), closed=False, crease=65).noised(0.003, 14, 2, seed=2)
    p.add("tabard_skirt", sk, "EH_Cloth", None, skin=SKIRT_SKIN, uv_scale=2, tint=lambda P: (0.30 + 0.70 * smoothstep(0.55, 0.85, P[:, 1]))[:, None] * np.array([1.05, 0.95, 0.88]))
    inner = g.loft(np.stack(rings[::-1]) * [0.965, 1, 0.965] , closed=False, crease=65).flipped()
    p.add("tabard_lining", inner, "EH_Cloth", None, skin=SKIRT_SKIN, lod1=None, tint=lambda P: np.full(len(P), 0.22))
    # hem trim: fur-lined edge along the bottom and the split edges
    hem = g.tube(rings[-1], 0.011, sides=5, samples=1, cap="round", cap_steps=1, smooth=False).noised(0.004, 20, 2, seed=3)
    p.add("tabard_hem_fur", hem, "EH_Fur", None, skin=SKIRT_SKIN, uv_scale=2, lod1=None)
    for s, nm in ((1, "L"), (-1, "R")):
        col = np.array([r_[0 if s < 0 else -1] for r_ in rings])
        p.add(f"tabard_edge_{nm}", g.tube(col, 0.0075, sides=5, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", None, skin=SKIRT_SKIN, lod1=None)
    # tassets: overlapping bronze lames hanging from the belt
    plates = []
    for i in range(9):
        a = 40 + i * 35.0 + (0 if i < 5 else 0)
        pl = g.plate(0.092, 0.135, 0.011, 0.005, bend_r=0.17, inner_x=1, taper=lambda t: 1 - 0.16 * (t + 1) / 2, drop_back=True)
        pl = pl.rotated(-12, 0, 0).translated(0, 0.785, 0.188 - 0.012 * (i % 2))
        plates.append(pl.rotated(0, a if a < 200 else a, 0))
    # skip the front split angles (-28..28)
    plates = [m for m, a in zip(plates, [40 + i * 35.0 for i in range(9)])]
    p.add("tassets", merge(plates), "EH_Bronze", "body")
    # belt + buckle (anvil, large) + studs
    belt = BODY.loft([0.872, 0.876, 0.928, 0.934], [0.006, 0.020, 0.020, 0.006], K=40, crease=50)
    p.add("belt", belt, "EH_Leather", "body", uv_scale=2)
    pt, _ = BODY.surf(0.90, 0, 0.022)
    buckle = g.extrude(g.rect_poly(0.082, 0.064, 0.009, 1), 0.018, 0.006, 1).translated(0, 0.902, pt[2] + 0.010)
    p.add("buckle", buckle, "EH_Bronze", "body")
    anvil = g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 1.0, 0.008, 0.002, 1)
    p.add("buckle_anvil", anvil.translated(0, 0.897, pt[2] + 0.024), "EH_Steel", "body", lod1=None)
    studs = []
    for a in np.linspace(-130, 130, 14):
        if abs(a) < 26:
            continue
        pp, nn = BODY.surf(0.903, a, 0.021)
        studs.append((pp, nn))
    p.add("belt_studs", g.instances(g.dome(0.0085, 0.006, 6, 1), [q[0] for q in studs], [q[1] for q in studs]), "EH_Bronze", "body", lod1=None)
    # hanging war-hammer loop & pouch on the right hip (asymmetry)
    pouch = g.superellipsoid((0.036, 0.046, 0.026), 0.5, 0.6, 4, 9).rotated(0, -30, 0).translated(*BODY.surf(0.80, -72, 0.020)[0])
    p.add("pouch", pouch, "EH_Leather", "body", uv_scale=2)


# ======================================================================================= torso
def torso(p: Piece):
    gam = BODY.loft([0.90, 0.98, 1.06, 1.14, 1.22, 1.285, 1.32], [-0.004] * 7, K=36, crease=60)
    p.add("gambeson", gam, "EH_Cloth", None, skin=TORSO_SKIN, uv_scale=2)
    # breastplate: open front shell with a central ridge, dented
    ys = [0.955, 0.985, 1.03, 1.08, 1.13, 1.18, 1.23, 1.275, 1.292]
    grow = [0.010, 0.016, 0.019, 0.020, 0.021, 0.021, 0.019, 0.014, 0.006]
    ridge = [0.0, 0.004, 0.009, 0.013, 0.015, 0.015, 0.012, 0.006, 0.0]
    rings = np.stack([BODY.ring(y, gg, 30, -96, 96, ridge=rd, ridge_w=0.024) for y, gg, rd in zip(ys, grow, ridge)])
    bp = g.loft(rings, closed=False, crease=50).dented(4, 0.034, 0.0045, seed=9)
    p.add("breastplate", bp.noised(0.0012, 40, 2, seed=3), "EH_Bronze", "chest")
    for a, nm in ((-96, "R"), (96, "L")):
        p.add(f"breast_edge_{nm}", BODY.edge(ys[1:-1], [gg + 0.004 for gg in grow[1:-1]], a, 0.0055, 4), "EH_Bronze", "chest", lod1=None)
    p.add("breast_lip_top", g.tube([BODY.surf(1.292, a, 0.011)[0] for a in np.linspace(-96, 96, 16)], 0.0060, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", "chest", lod1=None)
    # plackart + 4 overlapping lame bands, each proud of the one above
    pk = BODY.loft([0.918, 0.940, 0.985, 1.005], [0.012, 0.028, 0.029, 0.018], K=28, a0=-100, a1=100, crease=50)
    p.add("plackart", pk, "EH_Bronze", "spine")
    for i, y in enumerate((0.935, 0.965, 0.995, 1.025)):
        gr = 0.034 - 0.003 * i
        lm = BODY.loft([y - 0.016, y - 0.012, y + 0.012, y + 0.016], [gr - 0.007, gr, gr, gr - 0.005], K=24, a0=-98, a1=98, crease=45)
        p.add(f"lame_{i}", lm, "EH_Bronze", "spine")
        p.add(f"lame_lip_{i}", g.tube([BODY.surf(y - 0.016, a, gr - 0.005)[0] for a in np.linspace(-98, 98, 14)], 0.0042, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", "spine", lod1=None)
    rv = []
    for i, y in enumerate((0.935, 0.965, 0.995, 1.025)):
        for a in (-70, -35, 35, 70):
            rv.append(BODY.surf(y, a, 0.034 - 0.003 * i + 0.002))
    p.add("lame_rivets", g.instances(g.dome(0.0070, 0.0050, 6, 1), [q[0] for q in rv], [q[1] for q in rv]), "EH_Bronze", "spine", lod1=None)
    # steel chest crest relief (anvil in flame ring)
    pp, nn = BODY.surf(1.17, 0, 0.0285)
    crest = [g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 1.15, 0.007, 0.002, 1).translated(0, 1.163, pp[2]),
             g.torus(0.050, 0.0042, 20, 4).rotated(90, 0, 0).translated(0, 1.17, pp[2] - 0.001)]
    fl = g.teardrop(0.020, 0.012, 7)
    for i in range(6):
        a = i * 60 + 30
        q = g.extrude(fl, 0.005, 0.0, 1).rotated(0, 0, a)
        d = np.array([-math.sin(math.radians(a)), math.cos(math.radians(a))]) * 0.058
        crest.append(q.translated(d[0], 1.17 + d[1], pp[2] - 0.001))
    p.add("chest_crest", merge(crest), "EH_Steel", "chest", lod1=None)
    # backplate (open back shell)
    ysb = [0.955, 1.02, 1.09, 1.16, 1.23, 1.285]
    gb = [0.010, 0.016, 0.019, 0.019, 0.016, 0.008]
    rb = np.stack([BODY.ring(y, gg, 24, 120, 240) for y, gg in zip(ysb, gb)])
    p.add("backplate", g.loft(rb, closed=False, crease=50).dented(3, 0.035, 0.004, seed=14), "EH_Bronze", "chest")
    # gorget + neck
    gor = g.lathe(np.array([(0.090, 1.292), (0.102, 1.300), (0.108, 1.328), (0.100, 1.356), (0.088, 1.368), (0.082, 1.366), (0.092, 1.350), (0.095, 1.325), (0.084, 1.300)]), 24, crease=45)
    p.add("gorget", gor.scaled(1.0, 1.0, 0.92).translated(0, 0, 0.008), "EH_Bronze", "chest")
    p.add("neck", g.tube([(0, 1.25, 0.006), (0, 1.37, 0.012)], [0.062, 0.056], sides=10, samples=2, cap=None, smooth=False), "EH_Skin", None, skin=NECK_SKIN, uv_scale=2)


def mantle_and_cloak(p: Piece):
    K = 36
    th = np.linspace(0, TAU, K, endpoint=False) + math.pi      # seam of the closed tube at the BACK (hidden by the drape)
    path = np.stack([0.236 * np.sin(th), 1.286 - 0.036 * np.abs(np.sin(th)) ** 1.6, 0.176 * np.cos(th) - 0.004], 1)
    ring_ = g.tube(path, 0.054, sides=8, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=True).noised(0.010, 16, 3, seed=41)
    p.add("fur_mantle", ring_, "EH_Fur", "chest", uv_scale=2)
    # extra heavy clump over the left shoulder
    clump = g.superellipsoid((0.070, 0.045, 0.080), 0.7, 0.8, 5, 10).noised(0.010, 14, 3, seed=42).translated(0.255, 1.275, -0.01)
    p.add("fur_clump_L", clump, "EH_Fur", "chest", uv_scale=2, lod1=None)
    tuft = tuft_mesh(1.25)
    rng = np.random.default_rng(7)
    pos, nrm = [], []
    for i in range(36):
        a = i * TAU / 36 + rng.normal(0, 0.03)
        ps = np.array([0.262 * math.sin(a), 1.276 - 0.036 * abs(math.sin(a)) ** 1.6 - 0.012, 0.200 * math.cos(a) - 0.004])
        n = np.array([math.sin(a), -0.9, math.cos(a)])
        pos.append(ps)
        nrm.append(n)
    out = g.instances(tuft, pos, nrm, 1.0 + 0.3 * rng.random(len(pos)), spins=rng.random(len(pos)) * 360)
    p.add("fur_tufts", out, "EH_Fur", "chest", uv_scale=2)
    # cloak: soft sheet from the mantle down the back, torn hem on the left, fur-trimmed front edges
    rows, cols = 16, 9
    grid = []
    rng2 = np.random.default_rng(12)
    ph = rng2.random(3) * TAU
    for i in range(rows):
        t = i / (rows - 1)
        y = 1.285 - t * 0.95
        w = (0.215 + 0.100 * smoothstep(0.0, 0.8, t)) * (1 - 0.06 * smoothstep(0.8, 1.0, t))
        row = []
        for j in range(cols):
            u = j / (cols - 1) * 2 - 1
            x = u * w
            z = -(0.135 + 0.17 * t ** 1.15) + (u ** 2) * 0.075 * (0.5 + t) + math.sin(u * 7 + ph[0]) * 0.012 * t
            yy = y - (0.07 * max(0.0, -u) ** 1.2 * (1 + 0.5 * math.sin(u * 15 + ph[1])) if t > 0.8 else 0.0)
            row.append((x, yy, z))
        grid.append(row)
    G = np.array(grid)[::-1]            # rows ascending
    cloak = g.loft(G[:, ::-1], closed=False, crease=70, v_tile=0.25, u_tile=0.25).noised(0.003, 12, 2, seed=15)
    p.add("cloak", cloak, "EH_Cloth", None, skin=CLOAK_SKIN, uv_scale=2,
          tint=lambda P: (0.30 + 0.70 * smoothstep(0.30, 1.1, P[:, 1]))[:, None] * np.array([1.0, 0.92, 0.85]))
    for s, nm in ((1, "L"), (-1, "R")):
        edge = G[:, -1 if s > 0 else 0]
        edge = edge[1:]
        tr = g.tube(edge, 0.020, sides=6, samples=1, cap="round", cap_steps=1, smooth=True).noised(0.006, 16, 2, seed=16 + s)
        p.add(f"cloak_fur_{nm}", tr, "EH_Fur", None, skin=CLOAK_SKIN, uv_scale=2, lod1=None)
    # drape of the mantle at the back (fur + stone-coloured pelt)
    drape = g.superellipsoid((0.20, 0.080, 0.050), 0.6, 0.8, 5, 12).noised(0.011, 14, 3, seed=43).translated(0, 1.205, -0.145)
    p.add("fur_drape", drape, "EH_Fur", "chest", uv_scale=2, lod1=None)
    # cloak clasp chain across the throat
    clasp = merge([g.torus(0.026, 0.0045, 14, 4).rotated(90, 0, 0), g.superellipsoid((0.016, 0.016, 0.010), 0.6, 0.6, 3, 7)]).translated(0, 1.268, 0.150)
    chain = g.tube([(-0.150, 1.258, 0.120), (-0.075, 1.246, 0.162), (0, 1.268, 0.162), (0.075, 1.246, 0.162), (0.150, 1.258, 0.120)], 0.0048, sides=4, samples=2,
                   cap="round", cap_steps=1, radius_fn=lambda t: 0.7 + 0.3 * abs(math.sin(t * 60)))
    p.add("clasp", merge([clasp, chain]), "EH_Bronze", "chest", lod1=None)


# ======================================================================================= arms
def pauldrons(p: Piece):
    L = C.pauldron(+1, (0.288, 1.322, 0.0), 1.45, lames=4, seed=1, tilt_deg=14, flare=0.011)
    R = C.pauldron(-1, (-0.288, 1.312, 0.0), 1.38, lames=4, dent=True, spike=True, seed=2, tilt_deg=14, flare=0.011)
    p.add("pauldron_L", L, "EH_Bronze", "arm_L")
    p.add("pauldron_R", R, "EH_Bronze", "arm_R")
    # rolled trim and rivets on the top caps
    for s, nm, sc, y in ((1, "L", 1.45, 1.322), (-1, "R", 1.38, 1.312)):
        rv = [(s * 0.288 + 0.085 * sc / 1.45 * math.sin(a), y + 0.024, 0.088 * sc / 1.45 * math.cos(a)) for a in np.linspace(0, TAU, 8, endpoint=False)]
        p.add(f"pauldron_studs_{nm}", g.instances(g.dome(0.0085, 0.006, 6, 1), rv, [(0, 1, 0)] * len(rv)), "EH_Bronze", f"arm_{nm}", lod1=None)


def arm_chain(p: Piece, s, nm):
    sh, el, wr = J_(f"shoulder_{nm}"), J_(f"elbow_{nm}"), J_(f"wrist_{nm}")
    fd = C.unit(wr - el)                      # forearm direction
    ud = C.unit(el - sh)
    yh = wr[1]
    # one continuous quilted sleeve shoulder -> elbow -> cuff, with dense rings at the elbow (smooth skin: arm_X / hand_X)
    sleeve = limb_tube([sh + [0, -0.01, 0], lerp3(sh, el, 0.5), el, lerp3(el, wr - fd * 0.05, 0.5), wr - fd * 0.05],
                       [0.056, 0.053, 0.047, 0.041, 0.037], joints=[el], spacing=0.04, joint_spacing=0.018, joint_zone=0.05, sides=10,
                       cap="round", cap_steps=1, up=(0, 1, 0))
    p.add(f"sleeve_{nm}", sleeve.noised(0.002, 14, 2, seed=20 + s), "EH_Cloth", None, skin=ARM_SKIN[nm], uv_scale=2)
    # rerebrace (upper-arm plate, rigid on the arm) with rolled rims
    r0, r1 = lerp3(sh, el, 0.16), lerp3(sh, el, 0.80)
    rere = g.tube([r0, lerp3(r0, r1, 0.5), r1], [0.063, 0.060, 0.057], sides=10, samples=2, cap=None, up=(0, 0, 1))
    p.add(f"rerebrace_{nm}", rere.noised(0.002, 30, 2, seed=22 + s), "EH_Bronze", f"arm_{nm}")
    p.add(f"rerebrace_rim_{nm}", g.torus(0.0585, 0.0052, 16, 4).aimed(ud, r1), "EH_Bronze", f"arm_{nm}", lod1=None)
    # elbow cop + fin (follows the forearm, which pivots at the elbow)
    cop = g.superellipsoid((0.047, 0.050, 0.047), 0.65, 0.65, 5, 11).translated(*(el + [s * 0.022, -0.002, -0.020]))
    fin = g.extrude_plane(np.array([(-0.03, -0.035), (-0.03, 0.045), (0.02, 0.030), (0.03, -0.01)]), 0.010, "YZ", bevel=0.003, bevel_segments=1).translated(*(el + [s * 0.066, 0.0, -0.02]))
    p.add(f"elbow_cop_{nm}", merge([cop, fin]), "EH_Bronze", f"hand_{nm}")
    # vambrace + bands + flared cuff
    v0, v1 = lerp3(el, wr, 0.22), lerp3(el, wr, 0.78)
    vam = g.tube([v0, lerp3(v0, v1, 0.5), v1], [0.050, 0.046, 0.041], sides=10, samples=2, cap="flat", up=(0, 1, 0))
    p.add(f"vambrace_{nm}", vam.noised(0.002, 34, 2, seed=24 + s), "EH_Bronze", f"hand_{nm}")
    for u in (0.34, 0.60):
        q = lerp3(v0, v1, u)
        p.add(f"vambrace_band_{nm}{int(u * 100)}", g.torus(0.050 - 0.008 * u, 0.0058, 14, 4).aimed(fd, q), "EH_Steel", f"hand_{nm}", lod1=None)
    cuff = g.torus(0.044, 0.0075, 16, 4).aimed(fd, wr - fd * 0.052)
    p.add(f"gauntlet_cuff_{nm}", cuff, "EH_Bronze", f"hand_{nm}")
    # gauntlet hand wrapped round the grip (rigid on wrist_X): back of hand, four finger rings, knuckle studs, thumb, ring
    back = g.superellipsoid((0.038, 0.032, 0.036), 0.5, 0.6, 4, 10).translated(SW_X, yh, SW_Z + 0.022)
    knuck = g.instances(g.dome(0.0065, 0.0055, 6, 1), [(SW_X + dx, yh, SW_Z + 0.047) for dx in (-0.020, -0.007, 0.007, 0.020)], [(0, 0, 1)] * 4)
    fing = [g.torus(0.0252, 0.0085, 10, 4).translated(SW_X, yh + dy, SW_Z) for dy in (-0.024, -0.008, 0.008, 0.024)]
    th_s = -s                                   # thumb wraps toward the sword centre line from the forearm side
    thumb = g.tube([(SW_X + s * 0.030, yh - 0.020, SW_Z + 0.030), (SW_X + s * 0.030, yh + 0.004, SW_Z + 0.036), (SW_X + s * 0.014, yh + 0.026, SW_Z + 0.030)],
                   [0.0115, 0.0105, 0.0085], sides=5, samples=1, cap="round", cap_steps=1)
    p.add(f"gauntlet_{nm}", merge([back, thumb]), "EH_Bronze", f"wrist_{nm}")
    p.add(f"gauntlet_fingers_{nm}", merge(fing), "EH_Bronze", f"wrist_{nm}")
    p.add(f"gauntlet_knuckles_{nm}", knuck, "EH_Steel", f"wrist_{nm}", lod1=None)
    p.add(f"gauntlet_ring_{nm}", g.torus(0.0262, 0.0042, 12, 4).translated(SW_X, yh + (0.040 if s > 0 else -0.040), SW_Z), "EH_Bronze", f"wrist_{nm}", lod1=None)


def arms(p: Piece):
    arm_chain(p, +1, "L")
    arm_chain(p, -1, "R")


# ======================================================================================= head, beard, crown
def head(p: Piece):
    cy, cz = 1.375, 0.012
    skull = g.superellipsoid((0.066, 0.088, 0.070), 0.92, 0.95, 7, 16).translated(0, cy, cz)
    skull = g.warp(skull, lambda P: np.column_stack([P[:, 0] * (1 - 0.22 * smoothstep(cy + 0.01, cy - 0.095, P[:, 1])), P[:, 1],
                                                     P[:, 2] + 0.008 * smoothstep(cy - 0.02, cy - 0.095, P[:, 1])]), 60)
    brow = g.rounded_box((0.130, 0.020, 0.044), 0.008, 1).translated(0, cy + 0.030, cz + 0.058)
    brow = g.warp(brow, lambda P: np.column_stack([P[:, 0], P[:, 1] - 0.008 * (np.abs(P[:, 0]) / 0.065) ** 2, P[:, 2] - 0.018 * (np.abs(P[:, 0]) / 0.065) ** 2]), 60)
    nose = g.tube([(0, cy + 0.024, cz + 0.066), (0, cy - 0.004, cz + 0.092), (0, cy - 0.028, cz + 0.084)], [0.011, 0.014, 0.016], sides=6, samples=1, cap="round", cap_steps=1, up=(1, 0, 0))
    cheeks = [g.superellipsoid((0.020, 0.026, 0.016), 0.6, 0.6, 3, 8).translated(s * 0.044, cy - 0.020, cz + 0.060) for s in (-1, 1)]
    ears = [g.superellipsoid((0.009, 0.022, 0.016), 0.6, 0.6, 3, 7).translated(s * 0.070, cy + 0.002, cz - 0.004) for s in (-1, 1)]
    p.add("face", merge([skull, brow, nose] + cheeks + ears).noised(0.0010, 30, 2, seed=3), "EH_Skin", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.72))
    eyes = [g.superellipsoid((0.0125, 0.0070, 0.0075), 0.7, 0.7, 3, 6).translated(s * 0.034, cy + 0.013, cz + 0.067) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "EH_EmberVein", "head", lod1="keep", bake=False)
    # grey-brown beard (clumps) + moustache + side hair
    bt = []
    rng = np.random.default_rng(23)
    for i, (x, l) in enumerate([(0, 0.15), (-0.030, 0.12), (0.030, 0.12), (-0.058, 0.085), (0.058, 0.085), (-0.012, 0.10), (0.014, 0.105)]):
        z0 = cz + 0.088 - 0.01 * abs(x) / 0.06
        l = l * 0.82
        pts = [(x, cy - 0.050, z0), (x * 1.1, cy - 0.050 - l * 0.45, z0 + 0.034), (x * 0.9, cy - 0.050 - l, z0 + 0.046)]
        bt.append(g.tube(pts, [0.026, 0.021, 0.004], sides=6, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)))
    mo = []
    for s in (-1, 1):
        mo.append(g.tube([(s * 0.004, cy - 0.034, cz + 0.090), (s * 0.026, cy - 0.036, cz + 0.088), (s * 0.048, cy - 0.050, cz + 0.070)], [0.011, 0.010, 0.004], sides=5, samples=2, cap="round", cap_steps=1))
    hair = []
    for s in (-1, 1):
        for k in range(4):
            y0 = cy + 0.03 - 0.03 * k
            hair.append(g.tube([(s * 0.070, y0, cz - 0.004), (s * 0.078, y0 - 0.05, cz - 0.020 - 0.01 * k), (s * 0.074, y0 - 0.11 - 0.015 * k, cz - 0.034)], [0.014, 0.012, 0.003], sides=5, samples=1, cap="round", cap_steps=1))
    hair.append(g.superellipsoid((0.072, 0.090, 0.060), 0.8, 0.85, 6, 14).translated(0, cy - 0.004, cz - 0.034).noised(0.007, 16, 3, seed=26))
    fur_m = merge(bt + mo + hair).noised(0.003, 22, 2, seed=24)
    p.add("beard", fur_m, "EH_Fur", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.82) [:, None] * np.array([1.05, 1.02, 1.0]))
    crown(p)


# ======================================================================================= the closed crown + cross-pattee
CROWN_RIB = [(0.092, 1.410), (0.100, 1.410), (0.106, 1.414), (0.109, 1.420), (0.1075, 1.426), (0.1045, 1.430), (0.1045, 1.436), (0.1075, 1.440),
             (0.1095, 1.446), (0.1095, 1.466), (0.1075, 1.470), (0.1045, 1.474), (0.1045, 1.480), (0.1075, 1.484), (0.1095, 1.490),
             (0.1085, 1.496), (0.1055, 1.500), (0.098, 1.499), (0.094, 1.496), (0.092, 1.490), (0.092, 1.412)]
FLEURON = np.array([(-0.026, 0.0), (0.026, 0.0), (0.022, 0.014), (0.036, 0.026), (0.034, 0.040), (0.022, 0.034), (0.012, 0.030), (0.010, 0.040),
                    (0.0, 0.060), (-0.010, 0.040), (-0.012, 0.030), (-0.022, 0.034), (-0.034, 0.040), (-0.036, 0.026), (-0.022, 0.014)])
CROSS = np.array([(-0.026, 1.600), (0.026, 1.600), (0.019, 1.622), (0.019, 1.655), (0.036, 1.655), (0.051, 1.650), (0.053, 1.668), (0.051, 1.686),
                  (0.036, 1.681), (0.019, 1.681), (0.028, 1.700), (-0.028, 1.700), (-0.019, 1.681), (-0.036, 1.681), (-0.051, 1.686),
                  (-0.053, 1.668), (-0.051, 1.650), (-0.036, 1.655), (-0.019, 1.655), (-0.019, 1.622)])


def crown(p: Piece):
    # --- band: rolled rims, two engraved grooves, 16 rivets, three ember gems in bezels
    band = g.lathe(np.array(CROWN_RIB), 40, crease=45)
    p.add("crown_band", band.noised(0.0010, 34, 2, seed=30), "EH_Bronze", "head")
    rv_a = [math.radians(11.25 + 22.5 * k) for k in range(16)]
    rv = [(0.1100 * math.sin(a), 1.456, 0.1100 * math.cos(a)) for a in rv_a]
    p.add("crown_rivets", g.instances(g.dome(0.0070, 0.0055, 6, 1), rv, [(math.sin(a), 0, math.cos(a)) for a in rv_a]), "EH_Bronze", "head", lod1=None)
    gem_a = (0.0, 48.0, -48.0)
    gems = [g.superellipsoid((0.0145, 0.0185, 0.008), 0.85, 0.85, 4, 9).translated(0, 1.456, 0.1100).rotated(0, a, 0) for a in gem_a]
    bez = [g.torus(0.0190, 0.0036, 12, 4).rotated(90, 0, 0).scaled(1, 1.25, 1).translated(0, 1.456, 0.1100).rotated(0, a, 0) for a in gem_a]
    p.add("crown_band_gems", merge(gems), "EH_Coal", "head", lod1="keep", bake=False)
    p.add("crown_bezels", merge(bez), "EH_Bronze", "head", lod1=None)
    # --- oxblood velvet cap filling the crown (dark value for the bronze to read against)
    cap = g.lathe(g.spline(np.array([(0.0905, 1.412), (0.0925, 1.450), (0.0900, 1.490), (0.0780, 1.516), (0.0500, 1.531), (0.0, 1.537)]), 2), 28, crease=60)
    p.add("crown_cap", cap.uv_box(0.25), "EH_Cloth", "head", uv_scale=2)
    # --- four fleurons (diagonals) standing on the band, tilted out 6 deg, with a bronze boss each
    fl, bosses = [], []
    for k in range(4):
        a = 45.0 + 90.0 * k
        m = g.extrude(FLEURON, 0.016, 0.004, 1).rotated(-6, 0, 0).translated(0, 1.4985, 0.1045).rotated(0, a, 0)
        fl.append(m)
        bosses.append(g.superellipsoid((0.011, 0.009, 0.007), 0.7, 0.7, 3, 7).translated(0, 1.5035, 0.1075).rotated(0, a, 0))
    p.add("crown_fleurons", merge(fl + bosses), "EH_Bronze", "head")
    # --- two crossing arches (XY and ZY planes) with foot bosses at the four band points, apex under the orb
    pts = [(-0.100, 1.498, 0), (-0.093, 1.521, 0), (-0.070, 1.545, 0), (-0.036, 1.5605, 0), (0.0, 1.566, 0), (0.036, 1.5605, 0), (0.070, 1.545, 0),
           (0.093, 1.521, 0), (0.100, 1.498, 0)]
    arch = g.tube(pts, 0.0145, sides=6, samples=2, cap=None, up=(0, 0, 1))
    arches = [arch, arch.rotated(0, 90, 0)]
    feet = [g.superellipsoid((0.020, 0.016, 0.020), 0.7, 0.7, 3, 8).translated(0.1015, 1.4995, 0).rotated(0, a, 0) for a in (0, 90, 180, 270)]
    p.add("crown_arches", merge(arches + feet), "EH_Bronze", "head")
    # --- orb + collar + the cross-pattee finial with an ember gem on each face
    orb = g.superellipsoid((0.026, 0.026, 0.026), 1.0, 1.0, 6, 14).translated(0, 1.582, 0)
    band_o = g.torus(0.0272, 0.0034, 16, 4).translated(0, 1.582, 0)
    mer = g.torus(0.0268, 0.0030, 16, 4).rotated(0, 0, 90).translated(0, 1.582, 0)
    p.add("crown_orb", merge([orb, band_o, mer]), "EH_Bronze", "head")
    collar = g.lathe(np.array([(0.0, 1.598), (0.016, 1.600), (0.022, 1.606), (0.020, 1.612), (0.012, 1.617), (0.0, 1.618)]), 14, crease=45)
    p.add("crown_cross_collar", collar, "EH_Bronze", "head")
    cross = g.extrude(CROSS, 0.030, 0.007, 2)
    p.add("crown_cross", cross, "EH_Bronze", "head", lod1="keep")
    gem_f = g.superellipsoid((0.0125, 0.0125, 0.0075), 0.85, 0.85, 4, 9).translated(0, 1.668, 0.0170)
    gem_b = g.superellipsoid((0.0125, 0.0125, 0.0075), 0.85, 0.85, 4, 9).translated(0, 1.668, -0.0170)
    p.add("crown_cross_gem", merge([gem_f, gem_b]), "EH_Flame", "head", lod1="keep", bake=False)
    bz = [g.torus(0.0165, 0.0036, 14, 4).rotated(90, 0, 0).translated(0, 1.668, z) for z in (0.0150, -0.0150)]
    p.add("crown_cross_bezels", merge(bz), "EH_Bronze", "head", lod1="keep")


# ======================================================================================= greatsword
def sword(p: Piece):
    L, W = 0.665, 0.150
    blade = g.blade(L, W, 0.026, tip=0.30, taper=0.80, fuller=0.0045, rows=7)
    blade = blade.rotated(0, 0, 180).translated(SW_X, Y_TIP + L, SW_Z)
    # battle nicks: a few notches along the right edge (small dark steel wedges are enough: shallow displacement)
    p.add("sword_blade", blade, "EH_Steel", "weapon", lod1="keep", occluder=False)
    # fuller ember line (subtle F2): a thin groove seam, both faces
    seam = g.tube([(SW_X, Y_TIP + 0.12, SW_Z + 0.0125), (SW_X, Y_TIP + 0.38, SW_Z + 0.0135), (SW_X, Y_TIP + 0.58, SW_Z + 0.0125)], 0.0030, sides=4, samples=2, cap="round", cap_steps=1, ellipse=(1.4, 0.7), up=(0, 0, 1))
    p.add("sword_fuller_ember", seam, "EH_EmberVein", "weapon", lod1="keep", bake=False)
    # crossguard with down-turned tips
    poly = np.array([(-0.165, 0.905), (-0.150, 0.880), (-0.125, 0.912), (-0.050, 0.896), (0.0, 0.884), (0.050, 0.896), (0.125, 0.912), (0.150, 0.880), (0.165, 0.905),
                     (0.130, 0.948), (0.050, 0.952), (-0.050, 0.952), (-0.130, 0.948)])
    guard = g.extrude(poly - [0, 0.0], 0.040, 0.010, 1).translated(SW_X, 0.0, SW_Z)
    p.add("sword_guard", guard.noised(0.0012, 30, 2, seed=51), "EH_Bronze", "weapon", lod1="keep")
    ball = [g.superellipsoid((0.018, 0.018, 0.020), 0.7, 0.7, 4, 8).translated(SW_X + s * 0.163, 0.903, SW_Z) for s in (-1, 1)]
    p.add("sword_guard_balls", merge(ball), "EH_Bronze", "weapon", lod1=None)
    # grip with leather wraps, collar and pommel
    grip = g.tube([(SW_X, 0.946, SW_Z), (SW_X, 1.245, SW_Z)], 0.0165, sides=8, samples=1, cap="flat", smooth=False)
    p.add("sword_grip", grip, "EH_Leather", "weapon", uv_scale=2, lod1="keep")
    wraps = [g.torus(0.0172, 0.0038, 10, 4).translated(SW_X, 0.962 + 0.0235 * i, SW_Z) for i in range(12)]
    p.add("sword_wraps", merge(wraps), "EH_Leather", "weapon", uv_scale=2, lod1=None)
    collar = g.lathe(np.array([(0.018, 0.940), (0.030, 0.944), (0.032, 0.960), (0.030, 0.972), (0.020, 0.974)]), 14, crease=45).translated(SW_X, 0, SW_Z)
    p.add("sword_collar", collar, "EH_Bronze", "weapon", lod1=None)
    pommel = g.lathe(np.array([(0.0, -0.020), (0.036, -0.020), (0.042, -0.008), (0.042, 0.008), (0.036, 0.020), (0.0, 0.020)]), 24, crease=40).rotated(90, 0, 0).translated(SW_X, 1.272, SW_Z)
    p.add("sword_pommel", pommel, "EH_Bronze", "weapon", lod1="keep")
    nut = g.superellipsoid((0.018, 0.016, 0.018), 0.7, 0.7, 4, 8).translated(SW_X, 1.300, SW_Z)
    p.add("sword_pommel_nut", nut, "EH_Bronze", "weapon", lod1=None)
    # forge ring etched into the pommel face
    pr = g.torus(0.028, 0.0036, 16, 4).rotated(90, 0, 0).translated(SW_X, 1.272, SW_Z + 0.021)
    p.add("sword_pommel_ring", pr, "EH_Steel", "weapon", lod1=None)


# ======================================================================================= clips
A_S = V(0.0, -1.0, 0.0)                      # blade axis at rest (hand -> tip, straight down)
OFF_L = WL0 - WR0                            # left hand relative to the right hand along the grip
GRIP_UP = V(0.0, 1.0, 0.0)


def _anim(rig, cloak=True):
    """Common rig of every clip: planted feet (leg IK + pelvis reach clamp), both hands IK-pinned to the greatsword grip
    (right hand drives the sword; the left follows at a fixed offset along the grip), cloak spring."""
    a = Animator(rig)
    M.plant_feet(a)
    a.goal("ik_hand_R", ("arm_R", "hand_R", "wrist_R"), spaces=(("body", 1.0),), rot=(0, 0, 0), pole=(-0.5, -1, -0.2))
    a.goal("ik_hand_L", ("arm_L", "hand_L", "wrist_L"), spaces=(("body", 1.0),), rot=(0, 0, 0), pole=(0.5, -1, -0.2))
    if cloak:
        a.secondary(["cape_1", "cape_2", "cape_3"], driver="top", freq=2.0, zeta=0.35, follow=0.9, accel=0.05, max_deg=22)
    return a


def _goal(a, name):
    return next(g_ for g_ in a.goals if g_.name == name)


def _sword(a, space_keys, pos_keys, dir_keys, roll=None, grip_slide=None, world_keys=None):
    """Drive the greatsword: `pos_keys` = absolute positions of the RIGHT hand, `dir_keys` = blade direction (hand -> tip).
    `space_keys` blends pelvis space (0) -> chest space (1); `world_keys` blends in the PLINTH frame (1 = sword planted: the tip stays put
    while the body sways).  The left hand rides the same grip at OFF_L (rotated with the blade)."""
    gr, gl = _goal(a, "ik_hand_R"), _goal(a, "ik_hand_L")
    sp = step_signal(space_keys)
    wd = step_signal(world_keys) if world_keys else (lambda t: 0.0)
    for g_ in (gr, gl):
        g_.spaces = (("world", Fn(lambda t, wd=wd: wd(t))), ("body", Fn(lambda t, sp=sp, wd=wd: (1 - wd(t)) * (1 - sp(t)))), ("chest", Fn(lambda t, sp=sp, wd=wd: (1 - wd(t)) * sp(t))))
    P = Curve(pos_keys)
    D = Curve(dir_keys)
    Rf = M.aim(A_S, D)
    if roll is not None:
        Rf = M.blade_roll(Rf, A_S, roll)
    gr.pos = M.abs_pos(WR0, P)
    gr.rot = Rf
    slide = grip_slide if grip_slide is not None else (lambda t: 0.0)
    # left hand offset along the blade: OFF_L is "up the grip" = -blade direction
    gl.pos = Fn(lambda t: P(t) + Rf(t) @ (OFF_L + GRIP_UP * float(slide(t))) - WL0)
    gl.rot = Rf


def _both(a, wave):
    """Add a small signal (metres, pelvis/chest space) to both hand targets."""
    for n in ("ik_hand_R", "ik_hand_L"):
        g_ = _goal(a, n)
        g_.pos = g_.pos + wave if g_.pos is not None else wave


def _keys(a, bone, kind, keys):
    (a.rot if kind == "rot" else a.pos)(bone, Curve(keys))


# ---------------------------------------------------------------------------------------------- Idle
def clip_idle(rig):
    a = _anim(rig)
    T = 4.0
    M.idle(a, period=T, breath=1.2, shift=1.0, sway=0.010, look=1.0, hands=False)
    _sword(a, [(0, 0)], [(0, WR0)], [(0, A_S)], world_keys=[(0, 1)])
    _both(a, Wave(V(-0.0015, 0.0, 0.0), 1 / T, 0.45))             # grip floats with the breath
    a.rot("arm_L", Wave(V(-0.8, 0, 0.6), 1 / T, 0.4))
    a.rot("arm_R", Wave(V(0.6, 0, 0.6), 1 / T, 0.45))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- Move
def clip_move(rig):
    a = _anim(rig)
    T = 1.0
    M.biped_gait(a, T, stride=0.05, lift=0.065, duty=0.6, bob=0.018, sway=0.014, roll=3.4, twist=6.0, lean=4.0, arm_swing=(0, 0),
                 toe_off=22, strike=-8, head_stab=0.5)
    # sword carried: lifted 0.03, blade tilted 15 deg back onto the right pauldron side, both hands pinned to the grip
    carry_d = V(0.0, -0.966, -0.26)
    _sword(a, [(0, 0)], [(0, WR0 + V(0.0, 0.035, 0.02))], [(0, carry_d)])
    _both(a, Wave(V(0.003, 0.010, 0.0), 2 / T, 0.15))                # sword bobs with each step
    a.rot("arm_L", Wave(V(-1.0, 0, 0), 1 / T, 0.0))
    a.rot("arm_R", Wave(V(1.0, 0, 0), 1 / T, 0.0))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- HitReact
def clip_hit(rig):
    a = _anim(rig)
    T = 0.5
    z = V(0, 0, 0)
    a.pos("body", Curve([(0, z), (0.08, V(0, -0.028, -0.060), "out_cubic"), (0.20, V(0, -0.012, -0.022), "in_out_cubic"), (0.32, V(0, -0.014, 0.008), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.08, V(-8, 2, 2), "out_cubic"), (0.20, V(2, -1, 0), "in_out_cubic"), (0.32, V(-1, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.095, V(-8, 3, 2), "out_cubic"), (0.22, V(3, -2, 0), "in_out_cubic"), (0.34, V(-1.2, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.11, V(-10, 4, 3), "out_cubic"), (0.24, V(3, -3, -1), "in_out_cubic"), (0.36, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.12, V(-12, 6, 4), "out_cubic"), (0.26, V(4, -4, -1), "in_out_cubic"), (0.38, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.13, V(-14, 8, 5), "out_cubic"), (0.28, V(5, -4, -2), "in_out_cubic"), (0.40, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.10, V(0, 0, 4), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.10, V(0, 0, -4), "out_cubic"), (T, z, "in_out_cubic")]))
    _sword(a, [(0, 0)], [(0, WR0), (0.09, WR0 + V(0.012, 0.018, -0.045), "out_cubic"), (0.22, WR0 + V(-0.004, -0.006, 0.012), "in_out_cubic"), (T, WR0, "in_out_cubic")],
           [(0, A_S), (0.09, V(0.0, -0.99, -0.12), "out_cubic"), (0.22, V(0.0, -1.0, 0.03), "in_out_cubic"), (T, A_S, "in_out_cubic")],
           world_keys=[(0, 1)])
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.1, V(0, 0, -0.012), "out_cubic"), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.25)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Attack
IMPACT = 1.20
D_WIND = V(0.0, 0.84, -0.54)
D_HIT = V(-0.16, -0.22, 0.96)
H_WIND = V(-0.06, 1.60, 0.12)
H_HIT = V(-0.05, 1.08, 0.32)
H_FOLLOW = V(-0.05, 1.03, 0.35)
D_FOLLOW = V(-0.12, -0.40, 0.91)


def clip_attack(rig):
    a = _anim(rig)
    T, I = 2.3, IMPACT
    z = V(0, 0, 0)
    TW = 1.00                                                    # wind-up peak (held to 1.04), then the 0.16 s cleave
    # ---- greatsword: sinks onto the back leg, hoists tip-first off the plinth (forward, up), rolls over to an overhead wind-up with
    # a held coil, then the CLEAVE lands exactly at impactTime; follow-through, then back to the plant.
    _sword(a, [(0, 0), (0.22, 0), (0.42, 1), (1.95, 1), (2.22, 0)],
           [(0, WR0), (0.25, WR0, "in_out_cubic"), (0.72, V(-0.07, 1.40, 0.36), "in_out_cubic"),
            (TW, H_WIND, "anticipate"), (TW + 0.05, H_WIND + V(0, 0.015, -0.015), {"tan": "flat"}), (I, H_HIT, "snap_in"), (1.30, H_FOLLOW, "out_cubic"),
            (1.52, H_FOLLOW, {"tan": "flat"}), (2.00, V(-0.07, 1.16, 0.27), "in_out_cubic"), (T, WR0, "in_out_cubic")],
           [(0, A_S), (0.25, A_S, "in_out_cubic"), (0.72, V(0.0, 0.05, 1.0), "in_out_cubic"), (TW, D_WIND, "anticipate"),
            (TW + 0.05, D_WIND + V(0, 0.03, -0.03), {"tan": "flat"}), (I, D_HIT, "snap_in"), (1.30, D_FOLLOW, "out_cubic"), (1.52, D_FOLLOW, {"tan": "flat"}),
            (2.00, V(0.0, -0.92, 0.38), "in_out_cubic"), (T, A_S, "in_out_cubic")],
           world_keys=[(0, 1), (0.22, 1), (0.46, 0), (2.05, 0), (2.28, 1)])
    # ---- pelvis leads: sink, rise, coil back, then LUNGE into the blow just ahead of the weapon (kinetic chain), squash on impact
    a.pos("body", Curve([(0, z), (0.25, V(0, -0.018, -0.010), "in_out_cubic"), (0.72, V(0, 0.004, -0.030), "in_out_cubic"), (TW, V(0, -0.012, -0.040), "in_out_cubic"),
                         (I - 0.05, V(0, -0.040, 0.200), "snap_in"), (1.30, V(0, -0.062, 0.215), "out_cubic"), (1.52, V(0, -0.050, 0.210), {"tan": "flat"}),
                         (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.25, V(2, 0, 0), "in_out_cubic"), (0.72, V(-3, -2, 0), "in_out_cubic"), (TW, V(-6, -6, 0), "in_out_cubic"),
                         (I - 0.07, V(6, 3, 0), "snap_in"), (1.34, V(5, 3, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.25, V(2, 0, 0), "in_out_cubic"), (0.72, V(-5, -3, 0), "in_out_cubic"), (TW, V(-11, -8, -1), "in_out_cubic"),
                          (I - 0.04, V(8, 4, 1), "snap_in"), (1.34, V(6, 4, 1), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.25, V(1, 0, 0), "in_out_cubic"), (0.72, V(-5, -3, 0), "in_out_cubic"), (TW, V(-10, -10, -2), "in_out_cubic"),
                          (I - 0.02, V(8, 5, 2), "snap_in"), (1.34, V(6, 5, 1), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.25, V(4, 0, 0), "in_out_cubic"), (TW, V(-6, 8, 0), "in_out_cubic"), (I + 0.04, V(8, -4, 0), "snap_in"), (1.34, V(6, -4, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.25, V(4, 0, 0), "in_out_cubic"), (TW, V(-5, 6, 0), "in_out_cubic"), (I + 0.06, V(7, -4, 0), "snap_in"), (1.36, V(5, -4, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.72, V(0, 0, -4), "in_out_cubic"), (TW, V(0, 0, -9), "in_out_cubic"), (I, V(0, 0, 3), "snap_in"), (1.4, V(0, 0, 3)), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.72, V(0, 0, 4), "in_out_cubic"), (TW, V(0, 0, 8), "in_out_cubic"), (I, V(0, 0, -3), "snap_in"), (1.4, V(0, 0, -3)), (T, z, "in_out_cubic")]))
    # ---- feet: left foot steps INTO the lunge during the wind-up and holds; right foot drags back, planted; both re-centre in the recovery
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.62, z), (0.78, V(0, 0.07, 0.10), "in_out_cubic"), (1.00, V(0, 0, 0.235), "in_out_cubic"), (1.60, V(0, 0, 0.235)),
                                       (1.78, V(0, 0.06, 0.12), "in_out_cubic"), (2.00, z, "in_out_cubic")]),
               rot=Curve([(0, z), (0.62, z), (0.72, V(22, 0, 0), "in_out_cubic"), (0.88, V(-9, 0, 0), "in_out_cubic"), (1.00, z, "in_out_cubic"),
                          (1.60, z), (1.70, V(16, 0, 0), "in_out_cubic"), (1.90, V(-6, 0, 0), "in_out_cubic"), (2.00, z, "in_out_cubic")]))
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.7, z), (1.10, V(0, 0, -0.05), "in_out_cubic"), (1.60, V(0, 0, -0.05)), (2.05, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.35)
    return a, T, False, 60, (I,)


# ---------------------------------------------------------------------------------------------- Victory
def clip_victory(rig):
    a = _anim(rig)
    T = 2.0
    z = V(0, 0, 0)
    P_UP, D_UP = V(-0.19, 1.50, 0.20), V(-0.24, 0.78, 0.58)
    _sword(a, [(0, 0), (0.10, 0), (0.30, 1)],
           [(0, WR0), (0.10, WR0 + V(0, -0.01, 0), "in_out_cubic"), (0.38, V(-0.07, 1.30, 0.34), "in_out_cubic"), (0.70, P_UP, ("spring", 0.10, 1.5)), (T, P_UP + V(0, 0.012, 0), "in_out_cubic")],
           [(0, A_S), (0.10, A_S, "in_out_cubic"), (0.38, V(0.0, 0.3, 0.95), "in_out_cubic"), (0.70, D_UP, ("spring", 0.12, 1.5)), (T, D_UP + V(0, 0.01, 0), "in_out_cubic")],
           world_keys=[(0, 1), (0.12, 1), (0.34, 0)])
    a.pos("body", Curve([(0, z), (0.18, V(0, -0.018, 0), "in_out_cubic"), (0.62, V(0, 0.020, 0.01), ("spring", 0.2, 1.5)), (T, V(0, 0.016, 0.01), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.18, V(3, 0, 0)), (0.62, V(-3, -4, 0), "out_cubic"), (T, V(-2, -3, 0), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.18, V(4, 0, 0)), (0.66, V(-7, -4, 0), ("spring", 0.15, 1.5)), (T, V(-6, -3, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.18, V(5, 0, 0)), (0.68, V(-10, -6, -2), ("spring", 0.15, 1.5)), (T, V(-9, -4, -1.5), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.7, V(-6, 4, 0), "out_cubic"), (T, V(-5, 3, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.72, V(-10, 6, 0), ("spring", 0.15, 1.5)), (T, V(-9, 5, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.7, V(0, 0, -9), "out_cubic"), (T, V(0, 0, -9))]))
    a.rot("clavicle_L", Curve([(0, z), (0.7, V(0, 0, 8), "out_cubic"), (T, V(0, 0, 8))]))
    for nm in ("foot_L", "foot_R"):
        M.set_foot(a, nm, rot=Curve([(0, z), (0.25, z), (0.6, V(8, 0, 0), "out_cubic"), (T, V(8, 0, 0))]),
                   pos=Curve([(0, z), (0.25, z), (0.6, V(0, 0.008, 0), "out_cubic"), (T, V(0, 0.008, 0))]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Taunt
def clip_taunt(rig):
    """Lifts the blade and levels it at the enemy king, a slow deliberate nod, then raises it and SLAMS it point-down into the plinth."""
    a = _anim(rig)
    T = 1.4
    z = V(0, 0, 0)
    P_PT, D_PT = V(-0.07, 1.30, 0.30), V(0.0, 0.06, 1.0)
    P_UP, D_UP = V(-0.08, 1.52, 0.27), V(0.0, -0.95, 0.30)
    TS = 0.74                                  # slam contact
    _sword(a, [(0, 0), (0.12, 0), (0.30, 1), (1.05, 1), (1.30, 0)],
           [(0, WR0), (0.10, WR0 + V(0, -0.01, 0), "in_out_cubic"), (0.32, P_PT, "in_out_cubic"), (0.46, P_PT + V(0, 0, 0.01), {"tan": "flat"}), (0.62, P_UP, "in_out_cubic"),
            (TS - 0.02, P_UP + V(0, 0.02, -0.01), "out_cubic"), (TS, WR0 + V(0, -0.012, 0), "snap_in"), (TS + 0.07, WR0 + V(0, 0.004, 0), "out_cubic"),
            (TS + 0.20, WR0, "in_out_cubic"), (T, WR0, "in_out_cubic")],
           [(0, A_S), (0.10, A_S, "in_out_cubic"), (0.32, D_PT, "in_out_cubic"), (0.46, D_PT, {"tan": "flat"}), (0.62, D_UP, "in_out_cubic"),
            (TS - 0.02, D_UP, "out_cubic"), (TS, A_S, "snap_in"), (T, A_S, "in_out_cubic")],
           world_keys=[(0, 1), (0.12, 1), (0.30, 0), (0.62, 0), (TS, 1)])
    a.pos("body", Curve([(0, z), (0.32, V(0, -0.010, 0.012), "in_out_cubic"), (0.50, V(0, -0.010, 0.012)), (0.62, V(0, 0.016, 0.0), "out_cubic"),
                         (TS - 0.02, V(0, 0.020, 0.0)), (TS + 0.03, V(0, -0.034, 0.014), "snap_in"), (TS + 0.14, V(0, -0.016, 0.008), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.32, V(-3, 0, 0), "in_out_cubic"), (0.62, V(-4, 0, 0), "in_out_cubic"), (TS + 0.03, V(7, 0, 0), "snap_in"), (TS + 0.20, V(3, 0, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.32, V(-3, 0, 0), "in_out_cubic"), (0.62, V(-7, 0, 0), "in_out_cubic"), (TS + 0.03, V(8, 0, 0), "snap_in"), (TS + 0.20, V(3, 0, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.32, V(-5, 0, 0), "in_out_cubic"), (0.62, V(-8, 0, 0), "in_out_cubic"), (TS + 0.04, V(9, 0, 0), "snap_in"), (TS + 0.22, V(3, 0, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.32, V(-6, 0, 0), "in_out_cubic"), (0.46, V(-6, 0, 0)), (0.54, V(6, 0, 0), "in_out_cubic"), (0.64, V(-4, 0, 0), "in_out_cubic"), (TS + 0.06, V(7, 0, 0), "snap_in"), (1.0, V(-3, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.32, V(-6, 0, 0), "in_out_cubic"), (0.46, V(-6, 0, 0)), (0.54, V(7, 0, 0), "in_out_cubic"), (0.64, V(-5, 0, 0), "in_out_cubic"), (TS + 0.08, V(6, 0, 0), "snap_in"), (1.0, V(-5, 0, 0), ("spring", 0.15, 1.5)), (T, z, "in_out_cubic")]))
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.30, V(0, 0, -0.04), "in_out_cubic"), (1.0, V(0, 0, -0.04)), (T, z, "in_out_cubic")]))
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.56, z), (0.64, V(0, 0.035, 0.0), "out_cubic"), (TS + 0.01, z, "snap_in"), (T, z)]),
               rot=Curve([(0, z), (0.56, z), (0.64, V(-10, 0, 0), "out_cubic"), (TS + 0.01, z, "snap_in"), (T, z)]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Surrender
def clip_surrender(rig):
    """Stagger, open the hands (the greatsword drops, bounces twice, lies on the plinth), then a one-knee KNEEL (left foot planted, right knee
    down, shin and instep flat on the plinth), the torso folds, the head bows, the right hand opens palm-up on the thigh."""
    a = _anim(rig)
    T = 2.4
    z = V(0, 0, 0)
    sk = a.sk
    L1 = float(np.linalg.norm(sk.rest[sk.ix["shin_R"]] - sk.rest[sk.ix["thigh_R"]]))
    L2 = float(np.linalg.norm(sk.rest[sk.ix["foot_R"]] - sk.rest[sk.ix["shin_R"]]))
    KNEE_Y = 0.287                                  # kneeling knee axis above world 0 (plinth top 0.22 + greave radius)
    HIP_Y = KNEE_Y + L1
    DROP = JOINTS["hip_R"][1] - HIP_Y
    PZ = 0.05
    # ---- hands: hold, loosen (0.30), open and fall (0.45 release), right hand to the side, left hand onto the left thigh
    LOW = V(-0.08, 1.05, 0.26)
    _sword(a, [(0, 0), (0.4, 0)],
           [(0, WR0), (0.20, WR0 + V(0, -0.03, 0.02), "in_out_cubic"), (0.45, WR0 + V(0, -0.05, 0.03), "in_out_cubic"), (0.80, V(-0.20, 0.96, 0.22), "in_out_cubic"),
            (1.45, V(-0.21, 0.84, 0.28), "in_out_cubic"), (1.95, V(-0.21, 0.85, 0.33), "in_out_cubic"), (T, V(-0.21, 0.85, 0.33), {"tan": "flat"})],
           [(0, A_S), (0.30, V(0.0, -1.0, 0.04), "in_out_cubic"), (0.80, V(0.0, -0.95, 0.2), "in_out_cubic"), (1.45, V(0.2, -0.9, 0.4), "in_out_cubic"), (T, V(0.25, -0.88, 0.4))],
           world_keys=[(0, 1), (0.30, 0)])
    gl = _goal(a, "ik_hand_L")
    gl.pos = M.abs_pos(WL0, Curve([(0, WL0), (0.20, WL0 + V(0, -0.03, 0.02), "in_out_cubic"), (0.45, WL0 + V(0, -0.04, 0.03), "in_out_cubic"), (0.85, V(0.12, 0.92, 0.18), "in_out_cubic"),
                                  (1.50, V(0.15, 0.83, 0.30), "in_out_cubic"), (T, V(0.15, 0.83, 0.30), {"tan": "flat"})]))
    gl.rot = M.aim(A_S, Curve([(0, A_S), (0.30, V(0.0, -1.0, 0.04), "in_out_cubic"), (1.0, V(-0.2, -0.9, 0.3), "in_out_cubic"), (T, V(-0.25, -0.88, 0.4))]))
    # ---- pelvis: stagger back (0-0.3), then sink into the kneel (0.55-1.35), small settle
    a.pos("body", Curve([(0, z), (0.30, V(0, -0.012, -0.040), "out_cubic"), (0.55, V(0, -0.020, -0.020), "in_out_cubic"), (1.38, V(0, -DROP, PZ), "in_out_cubic"),
                         (1.60, V(0, -DROP + 0.007, PZ), "out_cubic"), (1.95, V(0, -DROP, PZ), "in_out_cubic"), (T, V(0, -DROP - 0.004, PZ), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.30, V(-6, 0, 0), "out_cubic"), (0.55, V(0, 0, 0), "in_out_cubic"), (1.38, V(3, 0, -2), "in_out_cubic"), (T, V(4, 0, -2), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.30, V(-3, 0, 0), "out_cubic"), (0.9, V(4, 0, 0), "in_out_cubic"), (1.6, V(7, 0, 0), "in_out_cubic"), (T, V(8, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.30, V(-2, 0, 0), "out_cubic"), (0.9, V(4, 0, 0), "in_out_cubic"), (1.7, V(5, 0, 0), "in_out_cubic"), (T, V(6, 0, 0.0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.30, V(-4, 0, 0), "out_cubic"), (1.0, V(8, 0, 0), "in_out_cubic"), (1.75, V(8, 0, 0), "in_out_cubic"), (T, V(9, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.30, V(-10, 0, 0), "out_cubic"), (1.0, V(8, 0, 0), "in_out_cubic"), (1.75, V(12, 2, 3), "in_out_cubic"), (T, V(13, 2, 4), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (1.0, V(0, 0, 4), "in_out_cubic"), (T, V(0, 0, 6))]))
    a.rot("clavicle_L", Curve([(0, z), (1.0, V(0, 0, -4), "in_out_cubic"), (T, V(0, 0, -6))]))
    # ---- legs: left foot steps forward and plants (knee ~90), right foot slides back to lie flat behind the right knee, instep down
    ankL = V(0.0, 0.0, PZ + 0.165 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.55, z), (0.85, ankL + V(0, 0.06, -0.06), "in_out_cubic"), (1.15, ankL, "in_out_cubic"), (T, ankL)]),
               rot=Curve([(0, z), (0.55, z), (0.70, V(18, 0, 0), "in_out_cubic"), (0.95, V(-10, 0, 0), "in_out_cubic"), (1.15, z, "in_out_cubic"), (T, z)]))
    ankR = V(0.0, 0.287 - JOINTS["ankle_R"][1], PZ - L2 - JOINTS["ankle_R"][2])
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.60, z), (1.00, ankR + V(0, 0.10, 0.10), "in_out_cubic"), (1.38, ankR, "in_out_cubic"), (T, ankR)]),
               rot=Curve([(0, z), (0.60, z), (1.00, V(95, 0, 0), "in_out_cubic"), (1.38, V(172, 0, 0), "in_out_cubic"), (T, V(172, 0, 0))]))
    # ---- the greatsword leaves the hands at 0.45: free fall, two bounces, lies flat on the plinth heading +X
    M.release_weapon(a, "weapon", 0.45, 0.22, 0.024, A_S, (1.0, 0.0, 0.20), land_xz=(-0.04, 0.33), kick=(0.0, 0.0, 0.0), up_local=(0, 0, 1))
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
    p = Piece("emberhold", "king", rig, make_clips(rig), impact_time=1.20, strike_range=0.60, attack_style="melee", seed=9)
    C.pedestal_parts(p)
    legs(p)
    skirt_and_belt(p)
    torso(p)
    mantle_and_cloak(p)
    pauldrons(p)
    arms(p)
    head(p)
    sword(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
