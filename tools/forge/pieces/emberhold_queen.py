"""emberhold_queen - Emberhold Flamecrown Warden.

An armoured warrior-queen: A-line skirt-armour of three rows of overlapping bronze lames over an oxblood under-skirt, a pinched
waist, a filigreed breastplate, swept winged pauldrons (the right taller, spiked), a cloak of overlapping bevelled bronze scales
on a fur yoke, a braid, and a tall forged crown of seven upward blades with one ember gem.  Hands are empty at rest: the great
hammer-staff lives on the `weapon_summon` node (scale 0 in every clip except Attack, where it is forged from embers).
Built from docs/art/emberhold_queen.md.
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

ASSET_ID = "emberhold_queen"
GRIP = np.array([-0.25, 0.80, 0.12])               # weapon_summon origin (right palm)

BODY = C.Body(Y=[0.76, 0.82, 0.88, 0.96, 1.04, 1.10, 1.15, 1.19, 1.23],
              RX=[0.150, 0.118, 0.104, 0.118, 0.138, 0.152, 0.142, 0.086, 0.050],
              RZ=[0.110, 0.088, 0.078, 0.084, 0.092, 0.094, 0.086, 0.062, 0.045],
              ZC=[0, 0, 0, 0.002, 0.004, 0.006, 0.006, 0.006, 0.006])
SK_Y = [0.865, 0.80, 0.74, 0.66, 0.58, 0.50, 0.42, 0.35, 0.295]
SK_R = [0.118, 0.134, 0.150, 0.172, 0.192, 0.212, 0.230, 0.245, 0.256]


def sk_r(y):
    return float(np.interp(y, SK_Y[::-1], SK_R[::-1]))


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.78, 0))
    r.add("spine", "body", (0, 0.90, 0))
    r.add("head", "spine", (0, 1.19, 0.01))
    r.add("top", "spine", (0, 1.17, -0.10))
    r.add("arm_L", "spine", (0.20, 1.12, 0))
    r.add("hand_L", "arm_L", (0.24, 0.92, 0.04))
    r.add("arm_R", "spine", (-0.20, 1.12, 0))
    r.add("hand_R", "arm_R", (-0.25, 0.92, 0.04))
    r.node("weapon_summon", "hand_R", GRIP)
    r.socket("socket_weapon_R", "hand_R", tuple(GRIP))
    r.socket("socket_cast", "body", (0, 0.90, 0.30))
    r.socket("socket_impact", "body", (0, 0.30, 0.70))
    r.socket("socket_head", "head", (0, 1.50, 0))
    return r


# ======================================================================================= skirt armour
def skirt(p: Piece):
    rings = []
    for y, r in zip(SK_Y[::-1], SK_R[::-1]):
        th = np.linspace(0, TAU, 56, endpoint=False)
        f = 1 + (0.010 + 0.040 * float(smoothstep(0.80, 0.30, y))) * (0.6 * np.cos(9 * th + 0.4) + 0.4 * np.cos(14 * th + 1.9))
        rings.append(np.stack([r * f * np.sin(th) * 1.0, np.full(56, y), r * f * np.cos(th) * 0.94], 1))
    sk = g.loft(np.stack(rings), closed=True, crease=60).noised(0.0025, 14, 2, seed=2)
    p.add("skirt_under", sk, "EH_Cloth", "body", uv_scale=2, tint=lambda P: (0.26 + 0.74 * smoothstep(0.28, 0.72, P[:, 1]))[:, None] * np.array([1.05, 0.95, 0.88]))
    # three rows of overlapping bronze lames, each row smaller and offset by half a plate
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
        p.add(f"skirt_lames_{nm}", merge(plates), "EH_Bronze", "body")
        # rolled hem rim along each row's lower edge + rivets
        rim = g.tube(np.stack([[(rr + 0.006) * math.sin(t) * 1.0, y0 + 0.004, (rr + 0.006) * math.cos(t) * 0.94] for t in np.linspace(0, TAU, 40, endpoint=False)]), 0.0050,
                     sides=4, samples=1, cap=None, closed=True, smooth=False, up=(0, 1, 0))
        p.add(f"skirt_rim_{nm}", rim, "EH_Bronze", "body", lod1=None)
        pos = [((rr + 0.014) * math.sin(math.radians(off + (k + 0.5) * 360 / n)), yc + h * 0.25, (rr + 0.014) * math.cos(math.radians(off + (k + 0.5) * 360 / n)) * 0.94) for k in range(n)]
        nrm = [(math.sin(math.radians(off + (k + 0.5) * 360 / n)), 0.25, math.cos(math.radians(off + (k + 0.5) * 360 / n))) for k in range(n)]
        p.add(f"skirt_rivets_{nm}", g.instances(g.dome(0.0070, 0.0050, 6, 1), pos, nrm), "EH_Bronze", "body", lod1=None)
    # front split tabard (oxblood) hanging over the lames with embroidery lines
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
    p.add("tabard", tab, "EH_Cloth", "body", uv_scale=2, tint=lambda P: (0.38 + 0.62 * smoothstep(0.24, 0.8, P[:, 1]))[:, None] * np.array([1.2, 0.98, 0.84]))
    for s, nm in ((-1, "R"), (1, "L")):
        pts = []
        for y in ys[1:]:
            t = (0.86 - y) / 0.64
            w = 0.100 + 0.024 * t
            R = (sk_r(max(y, 0.295)) + 0.026) if y > 0.295 else 0.282
            x = s * w / 2
            pts.append((x, y, math.sqrt(max(R * R - x * x, 0)) * 0.94 + 0.010))
        p.add(f"tabard_edge_{nm}", g.tube(pts, 0.0050, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", "body", lod1=None)
    # boots (toes show under the hem) + greaves
    for s, nm in ((1, "L"), (-1, "R")):
        toe = g.superellipsoid((0.044, 0.026, 0.074), 0.5, 0.6, 4, 9).translated(s * 0.075, 0.246, 0.255)
        p.add(f"boot_{nm}", toe, "EH_Leather", "body", uv_scale=2)
        cap = g.superellipsoid((0.034, 0.018, 0.030), 0.5, 0.6, 3, 8).translated(s * 0.075, 0.252, 0.312)
        p.add(f"boot_cap_{nm}", cap, "EH_Bronze", "body", lod1=None)
    # belt + faulds + anvil medallion
    belt = BODY.loft([0.805, 0.810, 0.868, 0.874], [0.004, 0.014, 0.014, 0.004], K=36, crease=50)
    p.add("belt", belt, "EH_Leather", "body", uv_scale=2)
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


# ======================================================================================= torso
def torso(p: Piece):
    gam = BODY.loft([0.84, 0.90, 0.97, 1.04, 1.10, 1.15, 1.19, 1.23], [-0.004] * 8, K=32, crease=60)
    p.add("gambeson", gam, "EH_Cloth", "spine", uv_scale=2)
    ys = [0.895, 0.93, 0.98, 1.03, 1.08, 1.115, 1.14]
    grow = [0.008, 0.014, 0.018, 0.021, 0.022, 0.018, 0.010]
    ridge = [0.0, 0.004, 0.008, 0.012, 0.014, 0.010, 0.0]
    rings = np.stack([BODY.ring(y, gg, 28, -92, 92, ridge=rd, ridge_w=0.020) for y, gg, rd in zip(ys, grow, ridge)])
    bp = g.loft(rings, closed=False, crease=50)
    bp = g.warp(bp, lambda P: P + np.column_stack([np.zeros(len(P)), np.zeros(len(P)), 0.008 * np.exp(-((P[:, 1] - 1.05) / 0.03) ** 2) * np.exp(-((np.abs(P[:, 0]) - 0.05) / 0.03) ** 2)]), 50)
    p.add("breastplate", bp.noised(0.0012, 40, 2, seed=3), "EH_Bronze", "spine")
    for a, nm in ((-92, "R"), (92, "L")):
        p.add(f"breast_edge_{nm}", BODY.edge(ys[1:-1], [gg + 0.004 for gg in grow[1:-1]], a, 0.0050, 4), "EH_Bronze", "spine", lod1=None)
    p.add("breast_lip_top", g.tube([BODY.surf(1.14, a, 0.012)[0] for a in np.linspace(-92, 92, 14)], 0.0055, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Bronze", "spine", lod1=None)
    # flame rosette filigree (blackened steel): six spiral arcs around an anvil-ember-less boss
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
    p.add("filigree", merge(spirals + [boss]), "EH_Steel", "spine", lod1=None)
    for i, y in enumerate((0.905, 0.935, 0.965)):
        gr = 0.020 - 0.002 * i
        lm = BODY.loft([y - 0.013, y - 0.010, y + 0.010, y + 0.013], [gr - 0.006, gr, gr, gr - 0.004], K=24, a0=-98, a1=98, crease=45)
        p.add(f"lame_{i}", lm, "EH_Bronze", "spine")
    rbk = np.stack([BODY.ring(y, gg, 22, 118, 242) for y, gg in zip([0.90, 0.96, 1.02, 1.08, 1.13], [0.008, 0.013, 0.016, 0.016, 0.010])])
    p.add("backplate", g.loft(rbk, closed=False, crease=50), "EH_Bronze", "spine")
    gor = g.lathe(np.array([(0.058, 1.138), (0.074, 1.146), (0.082, 1.170), (0.070, 1.192), (0.054, 1.192), (0.064, 1.172), (0.060, 1.150)]), 22, crease=45)
    p.add("gorget", gor.translated(0, 0, 0.008), "EH_Bronze", "spine")
    p.add("neck", g.tube([(0, 1.14, 0.008), (0, 1.215, 0.012)], [0.040, 0.034], sides=9, samples=1, cap=None, smooth=False), "EH_Skin", "head", uv_scale=2)


def yoke_and_cloak(p: Piece):
    K = 32
    th = np.linspace(0, TAU, K, endpoint=False)
    path = np.stack([0.160 * np.sin(th), 1.160 - 0.030 * np.abs(np.sin(th)) ** 1.5, 0.116 * np.cos(th) - 0.004], 1)
    yoke = g.tube(path, 0.032, sides=7, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.008, 18, 3, seed=40)
    p.add("cloak_yoke", yoke, "EH_Fur", "spine", uv_scale=2)
    tuft = g.tube([(0, 0, 0), (0.004, 0.014, 0.004), (0.010, 0.024, 0.010)], [0.019, 0.012, 0.0], sides=5, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    rng = np.random.default_rng(3)
    pos, nrm = [], []
    for i in range(28):
        a = i * TAU / 28 + rng.normal(0, 0.03)
        pos.append((0.176 * math.sin(a), 1.150 - 0.030 * abs(math.sin(a)) ** 1.5, 0.130 * math.cos(a) - 0.004))
        nrm.append((math.sin(a), -0.8, math.cos(a)))
    p.add("yoke_tufts", g.instances(tuft, pos, nrm, 1.0 + 0.3 * rng.random(28), spins=rng.random(28) * 360), "EH_Fur", "spine", uv_scale=2)
    # cloak backing (soft: spine -> top), hem cut on the left
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
    p.add("cloak_backing", back, "EH_Cloth", "spine", bone2="top", blend=(1.10, 0.75), uv_scale=2,
          tint=lambda P: (0.30 + 0.70 * smoothstep(0.30, 1.1, P[:, 1]))[:, None] * np.array([1.0, 0.92, 0.85]))
    # scales: ten staggered rows of bevelled bronze scales (every fourth row blackened steel)
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
    p.add("cloak_scales", merge(bronze), "EH_Bronze", "spine", bone2="top", blend=(1.10, 0.75))
    p.add("cloak_scales_steel", merge(steel), "EH_Steel", "spine", bone2="top", blend=(1.10, 0.75), lod1=None)
    # ember rims on a few scales (3% of scales get an ember edge)
    rim = []
    for (k, j) in ((3, 2), (5, 6), (7, 3), (8, 9)):
        n = 6 + k
        u = (j + 0.5) / n - 0.5 + (0.0 if k % 2 == 0 else 0.5 / n)
        x = u * (0.28 + 0.030 * k)
        zz = -0.136 - 0.014 * k + u * u * 0.060 * (0.4 + 0.1 * k)
        e = g.tube([(-0.020, 1.12 - 0.075 * k - 0.030, 0), (0, 1.12 - 0.075 * k - 0.044, 0), (0.020, 1.12 - 0.075 * k - 0.030, 0)], 0.0028, sides=4, samples=2, cap="round", cap_steps=1)
        rim.append(e.translated(-x, 0, -zz + 0.0) if False else e.translated(x, 0, zz - 0.009))
    p.add("scale_ember_rims", merge(rim), "EH_EmberVein", "spine", bone2="top", blend=(1.10, 0.75), lod1=None, bake=False)
    # shoulder brooches (discs) at the yoke fronts + clasp chain
    for s in (-1, 1):
        d = g.lathe(np.array([(0, 0), (0.016, 0), (0.017, 0.004), (0.015, 0.007), (0, 0.008)]), 14, crease=40).rotated(90, 0, 0).translated(s * 0.100, 1.125, 0.118)
        p.add(f"brooch_{'L' if s > 0 else 'R'}", d, "EH_Bronze", "spine", lod1=None)
    chain = g.tube([(-0.100, 1.120, 0.122), (-0.05, 1.100, 0.148), (0.0, 1.108, 0.152), (0.05, 1.100, 0.148), (0.100, 1.120, 0.122)], 0.0036, sides=4, samples=2,
                   cap="round", cap_steps=1, radius_fn=lambda t: 0.7 + 0.3 * abs(math.sin(t * 50)))
    p.add("clasp_chain", chain, "EH_Bronze", "spine", lod1=None)


# ======================================================================================= pauldrons & arms
def wing(s, scale, spikes):
    """Swept pauldron wing: three overlapping lames in a plane tilted 25 degrees, rear tip sweeping back."""
    poly = np.array([(0, 0), (0.12, 0.03), (0.19, 0.10), (0.17, 0.14), (0.04, 0.08)])
    parts = []
    for i, k in enumerate((1.0, 0.85, 0.70)):
        m = g.extrude(poly * scale * k, 0.012, 0.0045, 1)
        m = m.translated(0.010 * i * scale, -0.032 * i * scale, 0.0)
        m = m.rotated(0, 0, 0)
        parts.append(m.translated(0, 0, -0.010 * i))
    dome = g.superellipsoid((0.060 * scale, 0.026 * scale, 0.070 * scale), 0.6, 0.7, 5, 11).translated(0.050 * scale, 0.040 * scale, 0.0)
    parts.append(dome)
    if spikes:
        for j, xx in enumerate((0.060, 0.105, 0.150)):
            sp = g.tube([(0, 0, 0), (0, 0.020, 0), (0, 0.070 - 0.010 * j, 0)], [0.012, 0.009, 0.0], sides=5, samples=1, cap=None, smooth=False)
            parts.append(sp.translated(xx * scale, 0.065 * scale + 0.01 * j, 0.0))
    m = merge(parts)
    # sweep: tilt up 25 deg, rear tip back 0.06
    m = g.warp(m, lambda P: np.column_stack([P[:, 0], P[:, 1], P[:, 2] - 0.30 * np.clip(P[:, 0], 0, None) ** 1.5]), 50)
    m = m.rotated(0, 0, 25)
    if s < 0:
        m = m.mirrored("x")
    return m


def arms(p: Piece):
    for s, nm, sc, sp in ((1, "L", 1.0, False), (-1, "R", 1.06, True)):
        w = wing(s, sc, sp).translated(s * (0.20 if s > 0 else 0.20), 1.115 + (0.012 if s < 0 else 0.0), 0.0)
        p.add(f"pauldron_{nm}", w.noised(0.0010, 36, 2, seed=11 + s), "EH_Bronze", f"arm_{nm}")
        cap = g.superellipsoid((0.046, 0.030, 0.052), 0.65, 0.7, 4, 11).translated(s * 0.208, 1.128, 0)
        p.add(f"shoulder_cap_{nm}", cap.noised(0.0012, 34, 2, seed=14 + s), "EH_Bronze", f"arm_{nm}")
    for s, nm in ((1, "L"), (-1, "R")):
        sh = (s * 0.20, 1.12, 0.0)
        elb = (s * 0.24 if s > 0 else -0.25, 0.92, 0.04)
        up = g.tube([(s * 0.205, 1.10, 0.0), (s * 0.228, 1.02, 0.02), elb], [0.044, 0.040, 0.036], sides=9, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"upper_arm_{nm}", up.noised(0.002, 16, 2, seed=20 + s), "EH_Cloth", f"arm_{nm}", uv_scale=2)
        rere = g.tube([(s * 0.208, 1.085, 0.004), (s * 0.228, 1.025, 0.020), (s * 0.236 if s > 0 else -0.244, 0.968, 0.032)], [0.050, 0.046, 0.043], sides=9, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"rerebrace_{nm}", rere.noised(0.0016, 30, 2, seed=22 + s), "EH_Bronze", f"arm_{nm}")
        wr = (s * 0.25 if s > 0 else -0.25, 0.80, 0.18 if s > 0 else 0.15)
        fore = g.tube([elb, (s * 0.248 if s > 0 else -0.252, 0.86, 0.12 if s > 0 else 0.10), wr], [0.036, 0.031, 0.027], sides=9, samples=2, cap="round", cap_steps=1, up=(0, 1, 0))
        p.add(f"forearm_{nm}", fore, "EH_Cloth", f"hand_{nm}", uv_scale=2)
        vam = g.tube([(elb[0], 0.915, elb[2] + 0.004), (s * 0.248 if s > 0 else -0.252, 0.86, 0.12 if s > 0 else 0.10), wr], [0.043, 0.037, 0.032], sides=9, samples=2, cap="flat", up=(0, 1, 0))
        p.add(f"vambrace_{nm}", vam.noised(0.0016, 34, 2, seed=24 + s), "EH_Bronze", f"hand_{nm}")
        fin = g.extrude_plane(np.array([(0.88, 0.07), (0.84, 0.15), (0.86, 0.185), (0.90, 0.12)]), 0.012, "YZ", bevel=0.004, bevel_segments=1).translated(s * 0.285 if s > 0 else -0.285, 0, 0)
        p.add(f"vambrace_fin_{nm}", fin, "EH_Bronze", f"hand_{nm}", lod1=None)
        p.add(f"elbow_{nm}", g.superellipsoid((0.034, 0.034, 0.032), 0.65, 0.65, 4, 10).translated(elb[0] + s * 0.010, elb[1] + 0.012, elb[2] + 0.014), "EH_Bronze", f"hand_{nm}")
        # gauntlet hand: mitten + fingers; right hand open to take the haft, left a loose fist
        hx, hy, hz = wr[0], wr[1] - 0.030, wr[2] + 0.012
        palm = g.superellipsoid((0.025, 0.020, 0.032), 0.55, 0.6, 4, 10).translated(hx, hy, hz)
        fing = []
        for i, dx in enumerate((-0.014, -0.005, 0.005, 0.014)):
            if s < 0:
                pts = [(hx + dx, hy - 0.002, hz + 0.026), (hx + dx, hy - 0.020, hz + 0.040), (hx + dx, hy - 0.040, hz + 0.036)]   # curling around the haft
            else:
                pts = [(hx + dx, hy - 0.012, hz + 0.024), (hx + dx, hy - 0.034, hz + 0.034), (hx + dx, hy - 0.046, hz + 0.018)]
            fing.append(g.tube(pts, [0.0072, 0.0064, 0.0052], sides=5, samples=1, cap="round", cap_steps=1))
        th = g.tube([(hx + s * 0.022, hy + 0.004, hz + 0.014), (hx + s * 0.030, hy - 0.012, hz + 0.034), (hx + s * 0.016, hy - 0.026, hz + 0.044)], [0.0092, 0.0080, 0.0058], sides=5, samples=1, cap="round", cap_steps=1)
        p.add(f"hand_{nm}", merge([palm, th] + fing), "EH_Leather", f"hand_{nm}", uv_scale=2)
        cuff = g.torus(0.034, 0.0070, 14, 4).aimed(C.unit(np.array(wr) - np.array([s * 0.248 if s > 0 else -0.252, 0.86, 0.12 if s > 0 else 0.10])), np.array(wr) - [0, 0.002, 0.0])
        p.add(f"gauntlet_cuff_{nm}", cuff, "EH_Bronze", f"hand_{nm}", lod1=None)


# ======================================================================================= head, hair, crown
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
    cheek = [g.extrude(np.array([(-0.004, 0.0), (0.004, 0.0), (0.0035, 0.07), (-0.0035, 0.07)]), 0.008, 0.002, 1) for _ in range(1)]
    nasal = cheek[0].translated(0, cy - 0.030, cz + 0.062)
    p.add("nasal_guard", nasal, "EH_Bronze", "head", lod1=None)
    # dark hair framing the face and covering the back of the skull
    hair = g.superellipsoid((0.058, 0.086, 0.054), 0.85, 0.9, 6, 12).translated(0, cy + 0.006, cz - 0.046).noised(0.004, 20, 3, seed=61)
    sides = []
    for s in (-1, 1):
        sides.append(g.tube([(s * 0.056, cy + 0.030, cz + 0.020), (s * 0.066, cy - 0.020, cz + 0.004), (s * 0.064, cy - 0.074, cz - 0.014)], [0.014, 0.012, 0.004], sides=5, samples=1, cap="round", cap_steps=1))
    p.add("hair", merge([hair] + sides), "EH_Fur", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.45))
    # --- crown: band, seven upward blades, ember gem in a bezel, inner cross-straps
    band = g.lathe(np.array([(0.080, 1.335), (0.0910, 1.340), (0.0925, 1.350), (0.0925, 1.382), (0.0895, 1.388), (0.0795, 1.384), (0.0795, 1.343), (0.080, 1.335)]), 36, crease=45)
    p.add("crown_band", band.noised(0.0010, 34, 2, seed=30), "EH_Bronze", "head")
    blades = []
    specs = [(0, 0.160), (37, 0.150), (-37, 0.150), (77, 0.120), (-77, 0.120), (120, 0.100), (-120, 0.100)]
    for a, h in specs:
        poly = np.array([(-0.017, 0.0), (0.017, 0.0), (0.014, h * 0.35), (0.0075, h * 0.78), (0.0, h), (-0.0075, h * 0.78), (-0.014, h * 0.35)])
        m = g.extrude(poly, 0.011, 0.004, 1).rotated(-6, 0, 0).translated(0, 1.386, 0.0915)
        blades.append(m.rotated(0, a, 0))
    p.add("crown_blades", merge(blades), "EH_Bronze", "head")
    gem = g.superellipsoid((0.016, 0.020, 0.010), 0.75, 0.75, 5, 10).translated(0, 1.360, 0.0985)
    bez = g.torus(0.0215, 0.0048, 14, 4).scaled(0.9, 1.1, 1).rotated(90, 0, 0).translated(0, 1.360, 0.0955)
    p.add("crown_gem", gem, "EH_Gem", "head", lod1="keep", bake=False)
    p.add("crown_bezel", bez, "EH_Bronze", "head")
    arcs = [g.tube([(0.082, 1.384, 0), (0.044, 1.420, 0), (0, 1.432, 0), (-0.044, 1.420, 0), (-0.082, 1.384, 0)], 0.0045, sides=5, samples=2, cap="round", cap_steps=1).rotated(0, a, 0) for a in (0, 90)]
    p.add("crown_straps", merge(arcs), "EH_Steel", "head", lod1=None)
    studs = g.instances(g.dome(0.0050, 0.0040, 6, 1), [(0.0935 * math.sin(math.radians(a)), 1.366, 0.0935 * math.cos(math.radians(a))) for a in range(20, 341, 40) if abs(a - 180) > 5],
                        [(math.sin(math.radians(a)), 0, math.cos(math.radians(a))) for a in range(20, 341, 40) if abs(a - 180) > 5])
    p.add("crown_studs", studs, "EH_Steel", "head", lod1=None)


def braid(p: Piece):
    path = [(0, 1.36, -0.08), (0, 1.27, -0.125), (0, 1.17, -0.142), (0.02, 1.07, -0.152), (0.026, 0.97, -0.150), (0.004, 0.89, -0.142)]
    br = g.tube(path, [0.034, 0.032, 0.029, 0.025, 0.020, 0.014], sides=10, samples=4, cap="round", cap_steps=2, twist=1080, section=lambda th, t: 1.0 + 0.30 * np.cos(3 * th + 0.0),
                up=(1, 0, 0))
    p.add("braid", br.noised(0.0016, 30, 2, seed=70), "EH_Fur", "top", uv_scale=2, tint=lambda P: np.full(len(P), 0.5))
    rings = []
    for y, x in ((1.24, 0.0), (1.07, 0.02), (0.93, 0.016)):
        yy = np.array(path)[:, 1]
        i = int(np.argmin(np.abs(yy - y)))
        rings.append(g.torus(0.030 - 0.0025 * (len(rings)), 0.0060, 12, 4).translated(*path[i]))
    p.add("braid_rings", merge(rings), "EH_Bronze", "top", lod1=None)
    tail = g.tube([(0.004, 0.89, -0.142), (0.004, 0.865, -0.141), (0.004, 0.842, -0.139)], [0.012, 0.015, 0.0], sides=6, samples=1, cap=None, smooth=False)
    p.add("braid_tip", tail, "EH_Bronze", "top", lod1=None)


# ======================================================================================= summoned hammer-staff
def hammer(p: Piece):
    """Modelled in grip-local coordinates (origin = palm, +Y toward the butt end, HEAD toward -Y: the arm numbers of the
    sheet turn it head-up overhead and head-forward-down on the slam), then translated to GRIP."""
    def W(m):
        return m.translated(*GRIP)
    shaft = g.tube([(0, 0.30, 0), (0, -0.10, 0), (0, -0.50, 0), (0, -0.74, 0)], [0.022, 0.020, 0.0185, 0.021], sides=10, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("hammer_shaft", W(shaft.noised(0.0012, 30, 2, seed=80)), "EH_Steel", "weapon_summon", uv_scale=2)
    wraps = [g.torus(0.0225, 0.0050, 10, 4).translated(0, 0.08 - 0.0145 * i, 0) for i in range(6)] + [g.torus(0.0215, 0.0050, 10, 4).translated(0, -0.20 - 0.0145 * i, 0) for i in range(5)]
    p.add("hammer_wraps", W(merge(wraps)), "EH_Leather", "weapon_summon", uv_scale=2)
    pommel = g.superellipsoid((0.034, 0.028, 0.034), 0.6, 0.7, 5, 11).translated(0, 0.325, 0)
    collar = [g.lathe(np.array([(0.026, 0.0), (0.034, 0.008), (0.036, 0.022), (0.030, 0.032), (0.0215, 0.034)]), 12, crease=45).translated(0, y, 0) for y in (0.255, -0.255)]
    p.add("hammer_fittings", W(merge([pommel] + collar)), "EH_Bronze", "weapon_summon")
    # head: bronze block with stone striking faces, bands and a back spike
    hy = -0.88
    core = g.rounded_box((0.250, 0.175, 0.175), 0.022, 2).translated(0, hy, 0)
    cheeks = [g.rounded_box((0.014, 0.150, 0.150), 0.006, 1).translated(0, hy, 0.0) for _ in range(0)]
    p.add("hammer_head", W(core.noised(0.0018, 28, 2, seed=81)), "EH_Bronze", "weapon_summon")
    for s in (-1, 1):
        face = g.lathe(np.array([(0.0, 0.0), (0.078, 0.0), (0.086, 0.012), (0.080, 0.036), (0.0, 0.042)]), 20, crease=50).rotated(0, 0, -90 * s).translated(s * 0.118, hy, 0)
        p.add(f"hammer_face_{'R' if s > 0 else 'L'}", W(face.noised(0.0030, 24, 3, seed=82 + s)), "EH_Stone", "weapon_summon", uv_scale=2)
    bands = [g.torus(0.1, 0.0, 4, 3)] if False else []
    for xx in (-0.085, 0.085):
        b = g.extrude(g.rect_poly(0.034, 0.200, 0.006), 0.205, 0.008, 1).rotated(0, 90, 0).translated(xx, hy, 0) if False else None
    hoops = []
    for xx in (-0.088, 0.088):
        hoops.append(g.torus(0.100, 0.0085, 4, 3).rotated(0, 0, 90).translated(xx, hy, 0) if False else
                     g.rounded_box((0.026, 0.196, 0.196), 0.008, 1).translated(xx, hy, 0))
    p.add("hammer_bands", W(merge(hoops)), "EH_Steel", "weapon_summon")
    spike = g.tube([(-0.125, hy, 0), (-0.190, hy, 0), (-0.255, hy - 0.012, 0)], [0.050, 0.036, 0.0], sides=8, samples=2, cap=None, smooth=True, up=(0, 0, 1))
    p.add("hammer_spike", W(spike), "EH_Bronze", "weapon_summon")
    crown = [g.tube([(0, hy - 0.088, 0), (0, hy - 0.130, 0), (0, hy - 0.175, 0)], [0.030, 0.021, 0.0], sides=6, samples=1, cap=None, smooth=False)]
    for sgn in (-1, 1):
        crown.append(g.tube([(sgn * 0.040, hy - 0.088, 0), (sgn * 0.044, hy - 0.116, 0), (sgn * 0.040, hy - 0.140, 0)], [0.016, 0.011, 0.0], sides=5, samples=1, cap=None, smooth=False))
    p.add("hammer_tines", W(merge(crown)), "EH_Bronze", "weapon_summon", lod1=None)
    # ember core: glowing seams in the head (attack-only focal point F2)
    seams = []
    for zf in (0.0885, -0.0885):
        for dy in (-0.045, 0.0, 0.045):
            seams.append(g.tube([(-0.072, hy + dy, zf), (0.0, hy + dy + 0.006, zf), (0.072, hy + dy, zf)], 0.0040, sides=4, samples=2, cap="round", cap_steps=1))
    core_g = g.superellipsoid((0.050, 0.030, 0.030), 0.7, 0.7, 4, 9).translated(0, hy, 0.0880)
    core_b = g.superellipsoid((0.050, 0.030, 0.030), 0.7, 0.7, 4, 9).translated(0, hy, -0.0880)
    p.add("hammer_ember_core", W(merge([core_g, core_b])), "EH_Gem", "weapon_summon", bake=False)
    p.add("hammer_ember_seams", W(merge(seams)), "EH_EmberVein", "weapon_summon", bake=False)
    # pennon / tassel under the head collar
    tas = g.tube([(0, -0.74, 0), (0.012, -0.78, 0.01), (0.018, -0.83, 0.01)], [0.012, 0.010, 0.0], sides=5, samples=1, cap=None, smooth=False)
    p.add("hammer_tassel", W(tas), "EH_Cloth", "weapon_summon", lod1=None)


# ======================================================================================= clips
def make_clips(rig) -> list[Clip]:
    def summon(c, vals):
        c.keys("weapon_summon", "scale", vals)

    def zero(c):
        c.key("weapon_summon", "scale", 0.0, 0.0)
        c.key("weapon_summon", "scale", c.duration, 0.0)

    idle = Clip("Idle", 3.6, loop=True)
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.2, (1.4, 0, 0), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (1.2, (-1, 1.5, 0), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.8, (3, 0, 0), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    idle.keys("arm_R", "rot", [(0, (0, 0, 0)), (2.4, (-1.5, 0, 0), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    idle.keys("hand_R", "rot", [(0, (0, 0, 0)), (2.4, (-3, 0, 0), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    zero(idle)

    move = Clip("Move", 1.0, loop=True)
    move.keys("body", "rot", [(0, (4, 0, 0)), (0.25, (4, 0, 2), "in_out_cubic"), (0.5, (6, 0, 0), "in_out_cubic"), (0.75, (4, 0, -2), "in_out_cubic"), (1.0, (4, 0, 0), "in_out_cubic")])
    move.keys("body", "pos", [(0, (0, 0, 0)), (0.25, (0, 0.02, 0), "out_quad"), (0.5, (0, 0, 0), "in_quad"), (0.75, (0, 0.02, 0), "out_quad"), (1.0, (0, 0, 0), "in_quad")])
    move.keys("top", "rot", [(0, (6, 0, 0)), (0.5, (-8, 0, 0), "in_out_cubic"), (1.0, (6, 0, 0), "in_out_cubic")])
    move.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.25, (6, 0, 0), "in_out_cubic"), (0.75, (-6, 0, 0), "in_out_cubic"), (1.0, (0, 0, 0), "in_out_cubic")])
    move.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.25, (-6, 0, 0), "in_out_cubic"), (0.75, (6, 0, 0), "in_out_cubic"), (1.0, (0, 0, 0), "in_out_cubic")])
    zero(move)

    A = Clip("Attack", 2.4, fps=60)
    summon(A, [(0, 0.0), (0.05, 0.0), (0.30, 1.15, "out_cubic"), (0.40, 1.0, "in_out_cubic"), (2.10, 1.0), (2.40, 0.0, "in_cubic")])
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.40, (-35, 0, 0), "in_out_cubic"), (1.00, (-110, 0, 0), "in_out_cubic"), (1.10, (-140, 0, 0), "in_out_cubic"), (1.17, (-165, 0, 0)),
                            (1.30, (-40, 0, 0), "in_cubic"), (1.55, (-40, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.40, (-20, 0, 0), "in_out_cubic"), (1.00, (-35, 0, 0), "in_out_cubic"), (1.17, (-30, 0, 0)), (1.30, (-10, 0, 0), "in_cubic"), (1.55, (-10, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.40, (0, 0, 0)), (0.95, (0, -360, 0), "linear"), (1.00, (0, -360, 0)), (1.17, (-6, -360, 0), "in_out_cubic"), (1.30, (20, -360, 0), "in_cubic"),
                           (1.55, (20, -360, 0)), (2.4, (0, -360, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.40, (0, 0, 0)), (1.00, (0, 0.02, 0), "in_out_cubic"), (1.17, (0, 0.02, 0)), (1.30, (0, 0.0, 0.25), "in_cubic"), (1.34, (0, -0.03, 0.25), "out_quad"),
                           (1.55, (0, -0.03, 0.25)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.40, (-4, 0, 0), "in_out_cubic"), (1.17, (-10, 0, 0), "in_out_cubic"), (1.30, (18, 0, 0), "in_cubic"), (1.55, (18, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.40, (-6, 0, 0), "in_out_cubic"), (1.17, (-8, 0, 0), "in_out_cubic"), (1.30, (6, 0, 0), "in_cubic"), (1.55, (6, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.40, (0, 0, 0)), (1.00, (-15, 0, 0), "in_out_cubic"), (1.30, (25, 0, 0), "in_cubic"), (1.55, (30, 0, 0), "out_quad"), (2.4, (0, 0, 0), "in_out_cubic")])
    # left hand reaches up and takes the lower grip of the haft (grip-local y = -0.20), stays glued through the swing
    ramp = lambda t: float(smoothstep(0.30, 0.60, t) * (1 - smoothstep(1.85, 2.30, t)))
    C.solve_reach(A, rig, "hand_R", tuple(GRIP + np.array([0, -0.20, 0])), "arm_L", "hand_L", (0.25, 0.80, 0.18), ramp, axes=(0, 1, 2))

    hit = Clip("HitReact", 0.5)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.10, (-11, 0, 0), "out_cubic"), (0.50, (-4, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.07), "out_cubic"), (0.50, (0, 0, -0.02), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-9, 0, 0), "out_cubic"), (0.50, (-3, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.10, (-14, 0, 0), "out_cubic"), (0.50, (-5, 0, 0), "in_out_cubic")])
    hit.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.10, (12, 0, 0), "out_cubic"), (0.50, (3, 0, 0), "in_out_cubic")])
    hit.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.10, (12, 0, 0), "out_cubic"), (0.50, (3, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (16, 0, 0), "out_cubic"), (0.50, (0, 0, 0), "in_out_cubic")])
    zero(hit)

    vic = Clip("Victory", 2.0)
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.5, (-150, 0, 0), "out_back"), (2.0, (-150, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.5, (-20, 0, 0), "out_back"), (2.0, (-20, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.5, (-10, 0, 0), "out_cubic"), (2.0, (-10, 0, 0))])
    vic.keys("spine", "rot", [(0, (0, 0, 0)), (0.5, (-6, 0, 0), "out_cubic"), (2.0, (-6, 0, 0))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (1.0, (10, 0, 0), "in_out_cubic"), (2.0, (10, 0, 0))])
    vic.keys("body", "pos", [(0, (0, 0, 0)), (1.0, (0, 0.015, 0), "in_out_cubic"), (2.0, (0, 0.015, 0))])
    zero(vic)
    return [idle, move, A, hit, vic]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("emberhold", "queen", rig, make_clips(rig), impact_time=1.30, strike_range=0.70, attack_style="summon", seed=11)
    C.pedestal_parts(p)
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
