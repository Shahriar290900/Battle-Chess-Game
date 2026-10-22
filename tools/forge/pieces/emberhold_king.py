"""emberhold_king - Emberhold Ember Sovereign.

An older, broad-shouldered highland king in battle-worn bronze plate: layered cuirass (gambeson, breastplate with a
central ridge, plackart and lame bands), massive telescoping pauldrons (the right one cracked and spiked), a heavy fur
mantle, a front-split tabard over tassets and cuisses, a pelted cloak, a plain heavy crown of six squat points with ember
gems, and a great leaf-bladed greatsword planted point-down before him under both gauntlets.
Built from docs/art/emberhold_king.md.  The off-hand is IK-held on the grip through every clip.
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
import _emberhold_common as C                      # noqa: E402

ASSET_ID = "emberhold_king"
SW_X, SW_Z = -0.08, 0.24          # sword axis
Y_TIP = 0.222

BODY = C.Body(Y=[0.76, 0.84, 0.90, 0.96, 1.04, 1.12, 1.20, 1.26, 1.30, 1.34],
              RX=[0.170, 0.158, 0.152, 0.158, 0.175, 0.196, 0.212, 0.206, 0.172, 0.100],
              RZ=[0.115, 0.108, 0.104, 0.108, 0.114, 0.121, 0.122, 0.113, 0.092, 0.072],
              ZC=[0, 0, 0, 0, 0.002, 0.005, 0.008, 0.010, 0.010, 0.010])


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.76, 0))
    r.add("spine", "body", (0, 0.90, 0))
    r.add("head", "spine", (0, 1.33, 0.01))
    r.add("top", "spine", (0, 1.30, -0.12))
    r.add("arm_L", "spine", (0.31, 1.30, 0))
    r.add("hand_L", "arm_L", (0.30, 1.05, 0.05))
    r.add("arm_R", "spine", (-0.31, 1.30, 0))
    r.add("hand_R", "arm_R", (-0.30, 1.05, 0.05))
    r.socket("socket_weapon_R", "hand_R", (SW_X, Y_TIP, SW_Z))
    r.socket("socket_cast", "body", (0, 0.90, 0.30))
    r.socket("socket_impact", "body", (-0.02, 0.70, 0.60))
    r.socket("socket_head", "head", (0, 1.64, 0))
    return r


def tuft_mesh(scale=1.0):
    return g.tube([(0, 0, 0), (0.004, 0.016 * scale, 0.004), (0.010, 0.028 * scale, 0.012)], [0.024 * scale, 0.015 * scale, 0.0], sides=5, samples=1,
                  cap=None, smooth=False, up=(0, 0, 1))


# ======================================================================================= legs
def legs(p: Piece):
    for s, nm in ((1, "L"), (-1, "R")):
        x = s * 0.13
        sole = g.superellipsoid((0.060, 0.014, 0.118), 0.4, 0.55, 3, 10).translated(x, 0.232, 0.05)
        foot = g.superellipsoid((0.058, 0.036, 0.112), 0.5, 0.62, 5, 12).translated(x, 0.262, 0.044)
        shaft = g.tube([(x, 0.34, 0.040), (x, 0.275, 0.044)], [0.054, 0.058], sides=10, samples=1, cap=None, smooth=False)
        p.add(f"boot_{nm}", merge([foot, shaft]), "EH_Leather", "body", uv_scale=2)
        p.add(f"boot_sole_{nm}", sole, "EH_Steel", "body", lod1=None)
        toe = g.superellipsoid((0.050, 0.026, 0.044), 0.5, 0.6, 4, 9).translated(x, 0.266, 0.128)
        p.add(f"boot_toe_{nm}", toe, "EH_Bronze", "body")
        path = [(x, 0.285, 0.056), (x + s * 0.004, 0.38, 0.060), (x + s * 0.010, 0.47, 0.054)]
        greave = g.tube(path, [0.060, 0.066, 0.072], sides=10, samples=2, cap=None, up=(0, 0, 1)).noised(0.003, 36, 2, seed=3 + s)
        p.add(f"greave_{nm}", greave, "EH_Bronze", "body")
        for i, (y, rr) in enumerate(((0.292, 0.058), (0.476, 0.069))):
            p.add(f"greave_lip_{nm}{i}", g.torus(rr, 0.0055, 16, 4).translated(x + s * 0.010 * i, y, 0.056 - 0.002 * i), "EH_Bronze", "body", lod1=None)
        # side fin ridge down the greave and rivets
        fin = g.extrude_plane(np.array([(0.30, 0.04), (0.30, 0.12), (0.44, 0.095), (0.46, 0.04)]), 0.010, "YZ", bevel=0.003, bevel_segments=1).translated(x + s * 0.062, 0, 0)
        p.add(f"greave_fin_{nm}", fin, "EH_Bronze", "body", lod1=None)
        knee = g.superellipsoid((0.058, 0.048, 0.034), 0.6, 0.6, 5, 11).translated(x + s * 0.012, 0.512, 0.108)
        p.add(f"knee_{nm}", knee.noised(0.0014, 32, 2, seed=5), "EH_Bronze", "body")
        kf = g.extrude_plane(np.array([(0.49, 0.03), (0.49, 0.108), (0.545, 0.095), (0.56, 0.04)]), 0.011, "YZ", bevel=0.0035, bevel_segments=1).translated(x + s * 0.072, 0, 0)
        p.add(f"knee_fin_{nm}", kf, "EH_Bronze", "body", lod1=None)
        # cuisse (thigh plate) rising into the skirt
        thigh = g.tube([(x + s * 0.010, 0.50, 0.060), (x, 0.62, 0.046), (x - s * 0.012, 0.80, 0.020)], [0.064, 0.074, 0.086], sides=10, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"cuisse_{nm}", thigh.noised(0.002, 30, 2, seed=8 + s), "EH_Bronze", "body")
        p.add(f"cuisse_cloth_{nm}", g.tube([(x - s * 0.003, 0.55, 0.050), (x - s * 0.012, 0.80, 0.020)], [0.074, 0.088], sides=8, samples=1, cap=None, smooth=False), "EH_Cloth", "body", lod1=None, uv_scale=2)


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
    p.add("tabard_skirt", sk, "EH_Cloth", "body", uv_scale=2, tint=lambda P: (0.30 + 0.70 * smoothstep(0.55, 0.85, P[:, 1]))[:, None] * np.array([1.05, 0.95, 0.88]))
    inner = g.loft(np.stack(rings[::-1]) * [0.965, 1, 0.965] , closed=False, crease=65).flipped()
    p.add("tabard_lining", inner, "EH_Cloth", "body", lod1=None, tint=lambda P: np.full(len(P), 0.22))
    # hem trim: fur-lined edge along the bottom and the split edges
    hem = g.tube(rings[-1], 0.011, sides=5, samples=1, cap="round", cap_steps=1, smooth=False).noised(0.004, 20, 2, seed=3)
    p.add("tabard_hem_fur", hem, "EH_Fur", "body", uv_scale=2, lod1=None)
    for s, nm in ((1, "L"), (-1, "R")):
        col = np.array([r_[0 if s < 0 else -1] for r_ in rings])
        p.add(f"tabard_edge_{nm}", g.tube(col, 0.0075, sides=5, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", "body", lod1=None)
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
    p.add("gambeson", gam, "EH_Cloth", "spine", uv_scale=2)
    # breastplate: open front shell with a central ridge, dented
    ys = [0.955, 0.985, 1.03, 1.08, 1.13, 1.18, 1.23, 1.275, 1.292]
    grow = [0.010, 0.016, 0.019, 0.020, 0.021, 0.021, 0.019, 0.014, 0.006]
    ridge = [0.0, 0.004, 0.009, 0.013, 0.015, 0.015, 0.012, 0.006, 0.0]
    rings = np.stack([BODY.ring(y, gg, 30, -96, 96, ridge=rd, ridge_w=0.024) for y, gg, rd in zip(ys, grow, ridge)])
    bp = g.loft(rings, closed=False, crease=50).dented(4, 0.034, 0.0045, seed=9)
    p.add("breastplate", bp.noised(0.0012, 40, 2, seed=3), "EH_Bronze", "spine")
    for a, nm in ((-96, "R"), (96, "L")):
        p.add(f"breast_edge_{nm}", BODY.edge(ys[1:-1], [gg + 0.004 for gg in grow[1:-1]], a, 0.0055, 4), "EH_Bronze", "spine", lod1=None)
    p.add("breast_lip_top", g.tube([BODY.surf(1.292, a, 0.011)[0] for a in np.linspace(-96, 96, 16)], 0.0060, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", "spine", lod1=None)
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
    p.add("chest_crest", merge(crest), "EH_Steel", "spine", lod1=None)
    # backplate (open back shell)
    ysb = [0.955, 1.02, 1.09, 1.16, 1.23, 1.285]
    gb = [0.010, 0.016, 0.019, 0.019, 0.016, 0.008]
    rb = np.stack([BODY.ring(y, gg, 24, 120, 240) for y, gg in zip(ysb, gb)])
    p.add("backplate", g.loft(rb, closed=False, crease=50).dented(3, 0.035, 0.004, seed=14), "EH_Bronze", "spine")
    # gorget + neck
    gor = g.lathe(np.array([(0.090, 1.292), (0.102, 1.300), (0.108, 1.328), (0.100, 1.356), (0.088, 1.368), (0.082, 1.366), (0.092, 1.350), (0.095, 1.325), (0.084, 1.300)]), 24, crease=45)
    p.add("gorget", gor.scaled(1.0, 1.0, 0.92).translated(0, 0, 0.008), "EH_Bronze", "spine")
    p.add("neck", g.tube([(0, 1.30, 0.006), (0, 1.37, 0.012)], [0.062, 0.056], sides=10, samples=1, cap=None, smooth=False), "EH_Skin", "head", uv_scale=2)


def mantle_and_cloak(p: Piece):
    K = 36
    th = np.linspace(0, TAU, K, endpoint=False)
    path = np.stack([0.236 * np.sin(th), 1.302 - 0.040 * np.abs(np.sin(th)) ** 1.6, 0.176 * np.cos(th) - 0.004], 1)
    ring_ = g.tube(path, 0.058, sides=8, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.012, 16, 3, seed=41)
    p.add("fur_mantle", ring_, "EH_Fur", "spine", uv_scale=2)
    # extra heavy clump over the left shoulder
    clump = g.superellipsoid((0.070, 0.045, 0.080), 0.7, 0.8, 5, 10).noised(0.010, 14, 3, seed=42).translated(0.255, 1.275, -0.01)
    p.add("fur_clump_L", clump, "EH_Fur", "arm_L", uv_scale=2, lod1=None)
    tuft = tuft_mesh(1.25)
    rng = np.random.default_rng(7)
    pos, nrm = [], []
    for i in range(36):
        a = i * TAU / 36 + rng.normal(0, 0.03)
        ps = np.array([0.262 * math.sin(a), 1.292 - 0.040 * abs(math.sin(a)) ** 1.6 - 0.012, 0.200 * math.cos(a) - 0.004])
        n = np.array([math.sin(a), -0.9, math.cos(a)])
        pos.append(ps)
        nrm.append(n)
    out = g.instances(tuft, pos, nrm, 1.0 + 0.3 * rng.random(len(pos)), spins=rng.random(len(pos)) * 360)
    pos2, nrm2 = [], []
    for i in range(14):
        a = i * TAU / 14 + 0.1
        pos2.append((0.190 * math.sin(a), 1.352 - 0.020 * abs(math.sin(a)), 0.140 * math.cos(a) + 0.004))
        nrm2.append((math.sin(a) * 0.5, 1, math.cos(a) * 0.5))
    inn = g.instances(tuft, pos2, nrm2, 0.8, spins=rng.random(14) * 360)
    p.add("fur_tufts", merge([out, inn]), "EH_Fur", "spine", uv_scale=2)
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
    p.add("cloak", cloak, "EH_Cloth", "spine", bone2="top", blend=(1.15, 0.80), uv_scale=2,
          tint=lambda P: (0.30 + 0.70 * smoothstep(0.30, 1.1, P[:, 1]))[:, None] * np.array([1.0, 0.92, 0.85]))
    for s, nm in ((1, "L"), (-1, "R")):
        edge = G[:, -1 if s > 0 else 0]
        edge = edge[1:]
        tr = g.tube(edge, 0.020, sides=6, samples=1, cap="round", cap_steps=1, smooth=True).noised(0.006, 16, 2, seed=16 + s)
        p.add(f"cloak_fur_{nm}", tr, "EH_Fur", "spine", bone2="top", blend=(1.15, 0.80), uv_scale=2, lod1=None)
    # drape of the mantle at the back (fur + stone-coloured pelt)
    drape = g.superellipsoid((0.20, 0.080, 0.050), 0.6, 0.8, 5, 12).noised(0.011, 14, 3, seed=43).translated(0, 1.205, -0.145)
    p.add("fur_drape", drape, "EH_Fur", "spine", bone2="top", blend=(1.25, 1.1), uv_scale=2, lod1=None)
    # cloak clasp chain across the throat
    clasp = merge([g.torus(0.026, 0.0045, 14, 4).rotated(90, 0, 0), g.superellipsoid((0.016, 0.016, 0.010), 0.6, 0.6, 3, 7)]).translated(0, 1.268, 0.150)
    chain = g.tube([(-0.150, 1.258, 0.120), (-0.075, 1.246, 0.162), (0, 1.268, 0.162), (0.075, 1.246, 0.162), (0.150, 1.258, 0.120)], 0.0048, sides=4, samples=2,
                   cap="round", cap_steps=1, radius_fn=lambda t: 0.7 + 0.3 * abs(math.sin(t * 60)))
    p.add("clasp", merge([clasp, chain]), "EH_Bronze", "spine", lod1=None)


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
    sh = np.array([s * 0.31, 1.30, 0.0])
    elb = np.array([s * 0.30, 1.05, 0.05])
    upper = g.tube([(s * 0.31, 1.27, 0.0), (s * 0.315, 1.16, 0.02), tuple(elb)], [0.054, 0.049, 0.045], sides=10, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
    p.add(f"upper_arm_{nm}", upper.noised(0.003, 14, 2, seed=20 + s), "EH_Cloth", f"arm_{nm}", uv_scale=2)
    rere = g.tube([(s * 0.312, 1.20, 0.012), (s * 0.315, 1.13, 0.028), (s * 0.306, 1.08, 0.042)], [0.057, 0.053, 0.050], sides=10, samples=2, cap=None, up=(0, 0, 1))
    p.add(f"rerebrace_{nm}", rere.noised(0.002, 30, 2, seed=22 + s), "EH_Bronze", f"arm_{nm}")
    cop = g.superellipsoid((0.044, 0.046, 0.046), 0.65, 0.65, 5, 11).translated(s * 0.318, 1.052, 0.046)
    fin = g.extrude_plane(np.array([(1.02, -0.02), (1.02, 0.06), (1.072, 0.04), (1.075, -0.01)]), 0.010, "YZ", bevel=0.003, bevel_segments=1).translated(s * 0.366, 0, 0)
    p.add(f"elbow_cop_{nm}", merge([cop, fin]), "EH_Bronze", f"hand_{nm}")
    # forearm to the grip: right low, left high and crossing
    if s < 0:
        path = [tuple(elb), (-0.19, 1.105, 0.15), (-0.105, 1.118, 0.222)]
    else:
        path = [tuple(elb), (0.17, 1.14, 0.17), (0.02, 1.185, 0.228)]
    fore = g.tube(path, [0.040, 0.036, 0.033], sides=9, samples=2, cap="round", cap_steps=1, up=(0, 1, 0))
    p.add(f"forearm_{nm}", fore, "EH_Cloth", f"hand_{nm}", uv_scale=2)
    vam = g.tube([tuple(0.5 * (np.array(path[0]) + np.array(path[1]))), path[1], path[2]], [0.046, 0.042, 0.038], sides=9, samples=2, cap="flat", up=(0, 1, 0))
    p.add(f"vambrace_{nm}", vam.noised(0.002, 34, 2, seed=24 + s), "EH_Bronze", f"hand_{nm}")
    for u in (0.38, 0.72):
        q = np.array(path[1]) + (np.array(path[2]) - np.array(path[1])) * u - (np.array(path[1]) - np.array(path[0])) * 0.0
        dq = C.unit(np.array(path[2]) - np.array(path[1]))
        p.add(f"vambrace_band_{nm}{int(u * 100)}", g.torus(0.047 - 0.006 * u, 0.0060, 14, 4).aimed(dq, q), "EH_Steel", f"hand_{nm}", lod1=None)
    # flared gauntlet cuff + hand wrapped on the grip
    yh = 1.118 if s < 0 else 1.192
    cuff_dir = C.unit(np.array(path[2]) - np.array(path[1]))
    cuff = g.torus(0.040, 0.0070, 16, 4).aimed(cuff_dir, np.array(path[2]) - cuff_dir * 0.012)
    p.add(f"gauntlet_cuff_{nm}", cuff, "EH_Bronze", f"hand_{nm}")
    back = g.superellipsoid((0.036, 0.030, 0.036), 0.5, 0.6, 4, 10).translated(SW_X, yh, SW_Z + 0.024)
    knuck = g.instances(g.dome(0.0065, 0.0055, 6, 1), [(SW_X + dx, yh + 0.0, SW_Z + 0.046) for dx in (-0.020, -0.007, 0.007, 0.020)], [(0, 0, 1)] * 4)
    fing = [g.torus(0.0245, 0.0085, 10, 4).rotated(90, 0, 0).translated(SW_X, yh + dy, SW_Z) for dy in (-0.020, -0.007, 0.007, 0.020)]
    thumb = g.tube([(SW_X + s * 0.030, yh - 0.012, SW_Z + 0.030), (SW_X + s * 0.030, yh + 0.012, SW_Z + 0.036), (SW_X + s * 0.012, yh + 0.030, SW_Z + 0.030)], [0.0105, 0.0095, 0.0075], sides=5, samples=1, cap="round", cap_steps=1)
    p.add(f"gauntlet_{nm}", merge([back, thumb]), "EH_Bronze", f"hand_{nm}")
    p.add(f"gauntlet_fingers_{nm}", merge(fing), "EH_Bronze", f"hand_{nm}")
    p.add(f"gauntlet_knuckles_{nm}", knuck, "EH_Steel", f"hand_{nm}", lod1=None)
    # rings (one bright)
    ring_ = g.torus(0.0176, 0.0042, 10, 4).rotated(90, 0, 0).translated(SW_X + 0.0, yh + (0.0 if s < 0 else 0.0), SW_Z + 0.0) if False else None


def arms(p: Piece):
    arm_chain(p, +1, "L")
    arm_chain(p, -1, "R")
    rings = [g.torus(0.0275, 0.0050, 12, 4).rotated(90, 0, 0).translated(SW_X, y, SW_Z) for y in (1.100, 1.176)]
    p.add("gauntlet_rings", merge(rings), "EH_Bronze", "hand_R", lod1=None)


# ======================================================================================= head, beard, crown
def head(p: Piece):
    cy, cz = 1.445, 0.012
    skull = g.superellipsoid((0.068, 0.095, 0.072), 0.92, 0.95, 7, 16).translated(0, cy, cz)
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
        z0 = cz + 0.080 - 0.01 * abs(x) / 0.06
        pts = [(x, cy - 0.050, z0), (x * 1.1, cy - 0.050 - l * 0.45, z0 + 0.026), (x * 0.9, cy - 0.050 - l, z0 + 0.034)]
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
    # --- crown: thick band with ring grooves, six squat points, ember gems, cross-braces
    band = g.lathe(np.array([(0.090, 1.475), (0.1010, 1.480), (0.1055, 1.490), (0.1055, 1.504), (0.1030, 1.508), (0.1055, 1.512), (0.1055, 1.544),
                             (0.1030, 1.548), (0.1055, 1.552), (0.1055, 1.568), (0.1010, 1.576), (0.0945, 1.572), (0.0945, 1.484), (0.090, 1.475)]), 40, crease=45)
    p.add("crown_band", band.noised(0.0012, 34, 2, seed=30), "EH_Bronze", "head")
    pts_, gems = [], []
    poly = np.array([(-0.036, 0.0), (0.036, 0.0), (0.030, 0.030), (0.025, 0.070), (0.0, 0.078), (-0.025, 0.070), (-0.030, 0.030)])
    for k in range(6):
        a = k * 60.0
        m = g.extrude(poly, 0.020, 0.006, 1).translated(0, 0, 0.0)
        m = m.rotated(-4, 0, 0).translated(0, 1.570, 0.101)
        pts_.append(m.rotated(0, a, 0))
        gr = 0.021 if k == 0 else 0.016
        gm = g.superellipsoid((gr, gr * 1.15, gr * 0.9), 0.85, 0.85, 5, 10)
        gems.append(gm.translated(0, 1.648 + 0.010, 0.102 + 0.008).rotated(0, a, 0))
    p.add("crown_points", merge(pts_), "EH_Bronze", "head")
    p.add("crown_gems", merge(gems), "EH_Gem", "head", lod1="keep", bake=False)
    bg = [g.superellipsoid((0.014, 0.017, 0.007), 0.6, 0.6, 3, 8).translated(0, 1.525, 0.1070).rotated(0, a, 0) for a in (0, 120, 240)]
    bz = [g.torus(0.0175, 0.0035, 12, 4).rotated(90, 0, 0).translated(0, 1.525, 0.1075).rotated(0, a, 0) for a in (0, 120, 240)]
    p.add("crown_band_gems", merge(bg), "EH_Gem", "head", lod1=None, bake=False)
    p.add("crown_bezels", merge(bz), "EH_Bronze", "head", lod1=None)
    arcs = []
    for a in (0, 90):
        arcs.append(g.tube([(0.098, 1.568, 0), (0.062, 1.600, 0), (0, 1.616, 0), (-0.062, 1.600, 0), (-0.098, 1.568, 0)], 0.0065, sides=5, samples=2, cap="round", cap_steps=1).rotated(0, a, 0))
    arcs.append(g.superellipsoid((0.012, 0.010, 0.012), 0.7, 0.7, 3, 7).translated(0, 1.618, 0))
    p.add("crown_braces", merge(arcs), "EH_Steel", "head", lod1=None)
    # engraved pips on the points (tiny bronze studs)
    pips = []
    for k in range(6):
        a = math.radians(k * 60)
        pips.append((0.108 * math.sin(a), 1.560, 0.108 * math.cos(a)))
    p.add("crown_studs", g.instances(g.dome(0.0072, 0.005, 6, 1), pips, [(math.sin(math.radians(k * 60)), 0, math.cos(math.radians(k * 60))) for k in range(6)]), "EH_Steel", "head", lod1=None)


# ======================================================================================= greatsword
def sword(p: Piece):
    L, W = 0.665, 0.150
    blade = g.blade(L, W, 0.026, tip=0.30, taper=0.80, fuller=0.0045, rows=7)
    blade = blade.rotated(0, 0, 180).translated(SW_X, Y_TIP + L, SW_Z)
    # battle nicks: a few notches along the right edge (small dark steel wedges are enough: shallow displacement)
    p.add("sword_blade", blade, "EH_Steel", "hand_R", lod1="keep", occluder=False)
    # fuller ember line (subtle F2): a thin groove seam, both faces
    seam = g.tube([(SW_X, Y_TIP + 0.12, SW_Z + 0.0125), (SW_X, Y_TIP + 0.38, SW_Z + 0.0135), (SW_X, Y_TIP + 0.58, SW_Z + 0.0125)], 0.0030, sides=4, samples=2, cap="round", cap_steps=1, ellipse=(1.4, 0.7), up=(0, 0, 1))
    p.add("sword_fuller_ember", seam, "EH_EmberVein", "hand_R", lod1="keep", bake=False)
    # crossguard with down-turned tips
    poly = np.array([(-0.165, 0.905), (-0.150, 0.880), (-0.125, 0.912), (-0.050, 0.896), (0.0, 0.884), (0.050, 0.896), (0.125, 0.912), (0.150, 0.880), (0.165, 0.905),
                     (0.130, 0.948), (0.050, 0.952), (-0.050, 0.952), (-0.130, 0.948)])
    guard = g.extrude(poly - [0, 0.0], 0.040, 0.010, 1).translated(SW_X, 0.0, SW_Z)
    p.add("sword_guard", guard.noised(0.0012, 30, 2, seed=51), "EH_Bronze", "hand_R", lod1="keep")
    ball = [g.superellipsoid((0.018, 0.018, 0.020), 0.7, 0.7, 4, 8).translated(SW_X + s * 0.163, 0.903, SW_Z) for s in (-1, 1)]
    p.add("sword_guard_balls", merge(ball), "EH_Bronze", "hand_R", lod1=None)
    # grip with leather wraps, collar and pommel
    grip = g.tube([(SW_X, 0.946, SW_Z), (SW_X, 1.245, SW_Z)], 0.0165, sides=8, samples=1, cap="flat", smooth=False)
    p.add("sword_grip", grip, "EH_Leather", "hand_R", uv_scale=2, lod1="keep")
    wraps = [g.torus(0.0172, 0.0038, 10, 4).translated(SW_X, 0.962 + 0.0235 * i, SW_Z) for i in range(12)]
    p.add("sword_wraps", merge(wraps), "EH_Leather", "hand_R", uv_scale=2, lod1=None)
    collar = g.lathe(np.array([(0.018, 0.940), (0.030, 0.944), (0.032, 0.960), (0.030, 0.972), (0.020, 0.974)]), 14, crease=45).translated(SW_X, 0, SW_Z)
    p.add("sword_collar", collar, "EH_Bronze", "hand_R", lod1=None)
    pommel = g.lathe(np.array([(0.0, -0.020), (0.036, -0.020), (0.042, -0.008), (0.042, 0.008), (0.036, 0.020), (0.0, 0.020)]), 24, crease=40).rotated(90, 0, 0).translated(SW_X, 1.272, SW_Z)
    p.add("sword_pommel", pommel, "EH_Bronze", "hand_R", lod1="keep")
    nut = g.superellipsoid((0.018, 0.016, 0.018), 0.7, 0.7, 4, 8).translated(SW_X, 1.300, SW_Z)
    p.add("sword_pommel_nut", nut, "EH_Bronze", "hand_R", lod1=None)
    # forge ring etched into the pommel face
    pr = g.torus(0.028, 0.0036, 16, 4).rotated(90, 0, 0).translated(SW_X, 1.272, SW_Z + 0.021)
    p.add("sword_pommel_ring", pr, "EH_Steel", "hand_R", lod1=None)


# ======================================================================================= clips
def make_clips(rig) -> list[Clip]:
    grip_pt = (SW_X, 1.19, SW_Z)

    def hold(c):
        C.solve_hold(c, rig, "hand_R", "arm_L", "hand_L", grip_pt)

    idle = Clip("Idle", 4.0, loop=True)
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.4, (1.2, 0, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (1.4, (-0.8, 0, 0), "in_out_cubic"), (2.8, (0, -2, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("arm_R", "rot", [(0, (0, 0, 0)), (1.4, (-1, 0, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("body", "pos", [(0, (0, 0, 0)), (1.4, (0, 0.004, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (2.8, (2, 0, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])
    hold(idle)

    move = Clip("Move", 1.0, loop=True)
    move.keys("body", "rot", [(0, (5, 0, 0)), (0.5, (5, 0, 0))])
    move.keys("body", "rot", [(0.25, (5, 0, 3), "in_out_cubic"), (0.75, (5, 0, -3), "in_out_cubic"), (1.0, (5, 0, 0), "in_out_cubic")])
    move.keys("body", "pos", [(0, (0, 0, 0)), (0.25, (0, 0.02, 0), "out_quad"), (0.5, (0, 0, 0), "in_quad"), (0.75, (0, 0.02, 0), "out_quad"), (1.0, (0, 0, 0), "in_quad")])
    move.keys("spine", "rot", [(0, (2, 0, 0)), (1.0, (2, 0, 0))])
    move.keys("head", "rot", [(0, (0, 0, 0)), (0.25, (0, 0, -2), "in_out_cubic"), (0.75, (0, 0, 2), "in_out_cubic"), (1.0, (0, 0, 0), "in_out_cubic")])
    move.keys("top", "rot", [(0, (0, 0, 0)), (0.5, (-6, 0, 0), "in_out_cubic"), (1.0, (0, 0, 0), "in_out_cubic")])
    hold(move)

    A = Clip("Attack", 2.3, fps=60)
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.30, (2, 0, 0), "in_out_cubic"), (0.95, (-4, 0, 0), "in_out_cubic"), (1.07, (-8, 0, 0)), (1.20, (16, 0, 0), "in_cubic"),
                           (1.50, (16, 0, 0)), (2.3, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.95, (0, 0.02, 0), "in_out_cubic"), (1.07, (0, 0.02, 0)), (1.20, (0, 0.0, 0.26), "in_cubic"), (1.24, (0, -0.035, 0.26), "out_quad"),
                           (1.50, (0, -0.035, 0.26), "in_out_cubic"), (2.3, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.95, (-12, 0, 0), "in_out_cubic"), (1.07, (-14, 0, 0)), (1.20, (20, 0, 0), "in_cubic"), (1.50, (20, 0, 0)), (2.3, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.30, (4, 0, 0), "in_out_cubic"), (0.95, (-4, 0, 0), "in_out_cubic"), (1.07, (-4, 0, 0)), (1.20, (8, 0, 0), "in_cubic"), (1.50, (8, 0, 0)), (2.3, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.95, (-125, 0, 0), "in_out_cubic"), (1.07, (-150, 0, 0)), (1.20, (-45, 0, 0), "in_cubic"), (1.50, (-45, 0, 0)), (2.3, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.95, (-45, 0, 0), "in_out_cubic"), (1.07, (-45, 0, 0)), (1.20, (-15, 0, 0), "in_cubic"), (1.50, (-15, 0, 0)), (2.3, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.95, (6, 0, 0), "in_out_cubic"), (1.20, (22, 0, 0), "in_cubic"), (1.50, (30, 0, 0), "out_quad"), (2.3, (0, 0, 0), "in_out_cubic")])
    hold(A)

    hit = Clip("HitReact", 0.5)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.10, (-8, 0, 0), "out_cubic"), (0.50, (-3, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.06), "out_cubic"), (0.50, (0, 0, -0.02), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-8, 0, 0), "out_cubic"), (0.50, (-3, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.10, (-12, 0, 0), "out_cubic"), (0.50, (-4, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (16, 0, 0), "out_cubic"), (0.50, (0, 0, 0), "in_out_cubic")])
    hit.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.10, (8, 0, 0), "out_cubic"), (0.50, (2, 0, 0), "in_out_cubic")])
    hold(hit)

    vic = Clip("Victory", 2.0)
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.7, (-150, 0, 0), "out_back"), (2.0, (-150, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.7, (-35, 0, 0), "out_back"), (2.0, (-35, 0, 0))])
    vic.keys("spine", "rot", [(0, (0, 0, 0)), (0.7, (-10, 0, 0), "out_cubic"), (2.0, (-10, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.7, (-10, 0, 0), "out_cubic"), (2.0, (-10, 0, 0))])
    vic.keys("body", "pos", [(0, (0, 0, 0)), (0.7, (0, 0.02, 0), "out_cubic"), (2.0, (0, 0.02, 0))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (0.7, (14, 0, 0), "out_cubic"), (1.2, (-4, 0, 0), "in_out_cubic"), (2.0, (4, 0, 0), "in_out_cubic")])
    hold(vic)
    return [idle, move, A, hit, vic]


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
