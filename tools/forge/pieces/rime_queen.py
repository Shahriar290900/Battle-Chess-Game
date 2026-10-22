"""rime_queen - Rime Pale Tide Queen: a tall spectral queen in obsidian gown-armour whose hem frays into drifting ice,
a translucent ice veil, silver wire lacing, a floating crescent halo, one crystal wing shoulder, frost trailing across
the floor.  Her crystal glaive is pulled out of the air in Attack (`weapon_summon`, scale 0 everywhere else).
Built from docs/art/rime_queen.md."""
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
from _rime_common import unit, shard, spikes, cluster, frost_layer  # noqa: E402

ASSET_ID = "rime_queen"
GRIP = np.array([-0.24, 0.80, 0.12])        # weapon_summon origin (right palm)


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.78, 0))
    r.add("spine", "body", (0, 0.90, 0))
    r.add("head", "spine", (0, 1.19, 0.01))
    r.add("top", "spine", (0, 1.40, -0.12))
    r.add("arm_L", "spine", (0.19, 1.12, 0))
    r.add("hand_L", "arm_L", (0.23, 0.92, 0.04))
    r.add("arm_R", "spine", (-0.19, 1.12, 0))
    r.add("hand_R", "arm_R", (-0.24, 0.92, 0.04))
    r.node("weapon_summon", "hand_R", GRIP)
    r.socket("socket_weapon_R", "hand_R", tuple(GRIP))
    r.socket("socket_cast", "top", (0, 1.38, -0.10))
    r.socket("socket_impact", "body", (0, 0.70, 0.70))
    r.socket("socket_head", "top", (0, 1.52, -0.12))
    return r


# ======================================================================================= gown
SK_Y = [0.26, 0.34, 0.50, 0.66, 0.80, 0.88]
SK_R = [0.215, 0.222, 0.200, 0.160, 0.120, 0.100]


def sk_r(y):
    return float(np.interp(y, SK_Y, SK_R))


def gown(p: Piece):
    K = 32
    th = np.arange(K) * TAU / K
    rings = []
    for i, (y, r) in enumerate(zip(SK_Y, SK_R)):
        fold = 1 + 0.030 * np.cos(8 * th + 0.5 * i) * (1 - i / 6)
        rings.append(np.stack([r * fold * np.sin(th), np.full(K, y), r * fold * np.cos(th)], 1))
    inner = g.loft(np.stack(rings), closed=True, crease=38.0, cap_end=True)
    p.add("gown_inner", inner, "RH_Armour", "body", uv_scale=2, tint=lambda P: 0.5 + 0.5 * smoothstep(0.26, 0.8, P[:, 1]))
    # eight tall obsidian panels, V-pointed lower edge, alternating lengths, flaring
    panels = []
    wire = []
    for k in range(8):
        a0 = k * 45.0 + 8
        half = 0.19 if k % 2 == 0 else 0.17            # half angular width (rad)
        bot = 0.265 if k % 2 == 0 else 0.34
        rows, cols = 8, 6
        grid = []
        for ci in range(cols):
            u = ci / (cols - 1)
            ang = math.radians(a0) + (u - 0.5) * 2 * half
            ybot = bot + (0.21 + 0.10 * (k % 2)) * (abs(2 * u - 1) ** 1.3) * -1 + 0.0
            ybot = bot + 0.12 * abs(2 * u - 1) ** 1.2 - 0.0
            col = []
            for ri in range(rows):
                v = ri / (rows - 1)
                y = 0.88 - (0.88 - ybot) * v
                r = sk_r(max(y, 0.26)) + 0.014 + 0.022 * v ** 1.5
                col.append((r * math.sin(ang), y, r * math.cos(ang)))
            grid.append(col)
        grid = np.array(grid)                                  # (cols, rows, 3)
        m = g.loft(grid[:, ::-1], closed=False, crease=40, v_tile=0.25, u_tile=0.25).flipped()
        panels.append(m)
        edge = [tuple(grid[ci, -1]) for ci in range(cols)]
        wire.append(g.tube([(e[0] * 1.004, e[1] + 0.003, e[2] * 1.004) for e in edge], 0.0042, sides=4, samples=1, cap="round", cap_steps=1, smooth=False))
    p.add("gown_panels", merge(panels), "RH_Obsidian", "body", uv_scale=2)
    p.add("gown_panel_wire", merge(wire), "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    # tide-wave trim: scalloped silver arcs in three rows on the panels
    waves = []
    for row, y in enumerate((0.40, 0.55, 0.70)):
        r = sk_r(y) + 0.040
        for k in range(6):
            a = math.radians(k * 60 + 15 + 10 * row)
            pts = []
            for t in np.linspace(-1, 1, 7):
                aa = a + t * 0.20
                pts.append((r * math.sin(aa), y - 0.022 * (1 - t * t), r * math.cos(aa)))
            waves.append(g.tube(pts, 0.0038, sides=3, samples=1, cap="round", cap_steps=1, smooth=True))
    p.add("tide_trim", merge(waves), "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    # fraying hem tongues (translucent ice), tilted out so they lie across the plinth
    rng = np.random.default_rng(4)
    tg = []
    for k in range(16):
        a = k * TAU / 16 + 0.1
        ln = 0.09 + 0.07 * rng.random()
        poly = np.array([(-0.03, 0), (0.03, 0), (0.02, -ln * 0.6), (0.0, -ln), (-0.02, -ln * 0.6)])
        m = g.extrude(poly, 0.005, 0.0012, 1).rotated(-38, 0, 0).translated(0, 0.345, 0.205 + 0.01 * (k % 2)).rotated(0, math.degrees(a), 0)
        tg.append(m)
    p.add("hem_tongues", merge(tg), "RH_Ice", "body")
    # trailing ice train dragging behind (rear)
    train = cluster((0.0, 0.265, -0.19), (0.0, 0.35, -1.0), 7, (0.10, 0.22), (0.020, 0.040), spread=0.10, tilt=20, seed=7, flat=0.3)
    p.add("ice_train", train, "RH_Ice", "body")
    # floor frost trail: ragged fan + fringe of tiny crystals
    fan = g.extrude_plane(np.array([(0.0, -0.10), (0.20, -0.25), (0.15, -0.34), (0.05, -0.30), (-0.02, -0.36), (-0.12, -0.31), (-0.21, -0.27)]), 0.006, "XZ", bevel=0.002, bevel_segments=1)
    p.add("floor_frost", fan.translated(0, 0.2255, 0), "RH_Frost", "body", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    fr = spikes([((0.2 * math.sin(a), 0.226, -0.30 + 0.04 * abs(math.sin(2 * a)) - 0.1 * (1 - math.cos(a))), (0, 1, 0), 0.025 + 0.015 * (k % 2), 0.007)
                 for k, a in enumerate(np.linspace(-1.2, 1.2, 14))], seed=19, flat=0.2, sides=4, tip=0.5)
    p.add("floor_frost_crystals", fr, "RH_Ice", "body", lod1=None)
    # belt of linked plates
    belt = g.lathe([(0.098, 0.84), (0.106, 0.845), (0.106, 0.880), (0.098, 0.885)], 14, crease=30)
    p.add("belt", belt, "RH_Obsidian", "body")
    diamonds = [g.extrude(np.array([(0, -0.028), (0.020, 0), (0, 0.028), (-0.020, 0)]), 0.012, 0.003, 1).translated(0, 0.862, 0.108).rotated(0, k * 72, 0) for k in range(5)]
    p.add("belt_diamonds", merge(diamonds), "RH_Silver", "body", tint=lambda P: np.full(len(P), 0.7))
    # knee-bone spikes pushing through the cloth
    for s in (-1, 1):
        p.add(f"knee_spikes_{'L' if s > 0 else 'R'}", cluster((s * 0.08, 0.50, 0.20), (s * 0.3, 0.4, 1.0), 2, (0.05, 0.08), (0.011, 0.015), spread=0.02, tilt=22, seed=3 + (s > 0), flat=0.3, sides=4), "RH_Ice", "body")


# ======================================================================================= bodice, shoulders, arms
def bodice(p: Piece):
    t = g.tube([(0, 0.86, 0), (0, 0.98, 0), (0, 1.10, 0)], [0.095, 0.112, 0.135], sides=10, samples=3, cap=None, ellipse=(0.62, 1.0), up=(0, 0, 1))
    p.add("torso", t, "RH_Armour", "spine", uv_scale=2)
    yoke = g.superellipsoid((0.165, 0.040, 0.085), 0.55, 0.7, 5, 12).translated(0, 1.125, 0.0)
    p.add("yoke", yoke, "RH_Armour", "spine", uv_scale=2)
    # layered faceted bodice: a ridged cuirass shell, three rib lames below it, silver wire along every plate edge
    QY = np.array([0.84, 0.90, 0.98, 1.06, 1.12, 1.15])
    QW = np.array([0.098, 0.108, 0.124, 0.140, 0.140, 0.100])
    QF = np.array([0.064, 0.070, 0.078, 0.086, 0.084, 0.060])
    QB = np.array([0.058, 0.062, 0.066, 0.070, 0.068, 0.052])

    def qring(y, grow=0.0, K=14, ridge=0.0):
        hw, zf, zb = np.interp(y, QY, QW) + grow, np.interp(y, QY, QF) + grow, np.interp(y, QY, QB) + grow
        th = np.linspace(0, TAU, K, endpoint=False)
        sn, cs = np.sin(th), np.cos(th)
        x = hw * np.sign(sn) * np.abs(sn) ** 0.85
        z = np.where(cs > 0, zf * cs, zb * cs) + ridge * np.exp(-(x / 0.03) ** 2) * (cs > 0)
        return np.stack([x, np.full(K, y), z], 1)

    def qshell(specs, K=14):
        return g.loft(np.stack([qring(y, gr, K, rd) for y, gr, rd in specs]), closed=True, crease=34)
    for i, y0 in enumerate((0.855, 0.885, 0.915)):
        gr = 0.004 + 0.003 * (2 - i)
        p.add(f"rib_lame_{i}", qshell([(y0, gr - 0.004, 0), (y0 + 0.006, gr + 0.004, 0), (y0 + 0.030, gr + 0.005, 0), (y0 + 0.036, gr - 0.003, 0)]), "RH_Obsidian", "spine")
    ridge = lambda y: 0.014 * smoothstep(0.95, 1.02, y) * (1 - smoothstep(1.08, 1.14, y))
    ys = [0.935, 0.942, 0.99, 1.04, 1.09, 1.125, 1.148]
    gs = [0.002, 0.009, 0.013, 0.014, 0.013, 0.009, 0.0]
    cu = g.loft(np.stack([qring(y, a_, 14, ridge(y)) for y, a_ in zip(ys, gs)]), closed=True, crease=30)
    p.add("bodice_plate", cu.dented(3, 0.03, 0.002, seed=5), "RH_Obsidian", "spine")
    p.add("bodice_lip", g.tube(qring(0.938, 0.0075, 18), 0.0055, sides=4, samples=1, cap=None, smooth=False, closed=True, up=(0, 1, 0)), "RH_Silver", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.45))
    p.add("bodice_frost", frost_layer(cu, 0.006, min_ny=0.5, cover=0.28, seed=4), "RH_Frost", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    # silver filigree: a central vertical wire with scrolls, three snow-crystal studs, 5 laced crossings
    cw = [(0.0, y, float(np.interp(y, QY, QF)) + 0.016 + float(ridge(y)) * 1.0) for y in np.linspace(0.945, 1.12, 8)]
    p.add("bodice_center_wire", g.tube(cw, 0.0032, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "RH_Silver", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.45))
    studs = []
    for y in (0.985, 1.035, 1.085):
        z = float(np.interp(y, QY, QF)) + 0.020 + float(ridge(y))
        for a_ in (0, 60, 120):
            studs.append(g.extrude(g.rect_poly(0.024, 0.0050), 0.004, 0.001, 1).rotated(0, 0, a_).translated(0, y, z))
    p.add("bodice_studs", merge(studs), "RH_Silver", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.55))
    lace = []
    for k in range(5):
        y = 0.955 + 0.030 * k
        z = float(np.interp(y, QY, QF)) + 0.016 + float(ridge(y))
        w = 0.070 * (0.7 + 0.3 * (k % 2))
        lace.append(g.tube([(-w, y - 0.010, z - 0.01), (0.0, y + 0.004, z + 0.002), (w, y - 0.010, z - 0.01)], 0.0026, sides=3, samples=1, cap="round", cap_steps=1, smooth=True))
    p.add("lacing", merge(lace), "RH_Silver", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.25))
    # gorget crystals around the neck
    gc = cluster((0, 1.145, 0.0), (0, 1, 0), 1, (0.01, 0.02), (0.005, 0.01), seed=1) if False else None
    col = [(((0.075 * math.sin(a)), 1.14, 0.075 * math.cos(a)), (math.sin(a) * 0.45, 1.0, math.cos(a) * 0.45), 0.05 + 0.06 * ((k * 3) % 4) / 3, 0.0100)
           for k, a in enumerate(np.linspace(0, TAU, 7, endpoint=False) + 0.3)]
    p.add("collar_crystals", spikes(col, seed=3, flat=0.28, sides=5, tip=0.42), "RH_Ice", "spine")
    # crystal wing on the left shoulder: five fanned shards, tallest tip 1.30
    wing = []
    for k, (ln, rd, fan) in enumerate(((0.10, 0.020, -34), (0.15, 0.026, -14), (0.19, 0.032, 6), (0.15, 0.026, 26), (0.095, 0.020, 44))):
        d = unit((0.5 + math.sin(math.radians(fan)) * 0.9, 1.0, -0.2 + 0.0 * k))
        wing.append(((0.20 + 0.012 * k * 0.0, 1.14, 0.0 - 0.03 * (k - 2) * 0.4), d, ln, rd))
    p.add("wing_L", spikes(wing, seed=33, flat=0.3, sides=6, tip=0.38, bend=0.06), "RH_Ice", "arm_L")
    p.add("wing_L_secondary", spikes([((0.24, 1.135, -0.04), unit((0.9, 0.8, -0.4)), 0.09, 0.016), ((0.16, 1.14, -0.05), unit((0.2, 1.0, -0.5)), 0.11, 0.016), ((0.27, 1.12, 0.03), unit((1.0, 0.5, 0.1)), 0.08, 0.014)], seed=41, flat=0.3, sides=5, tip=0.42), "RH_Ice", "arm_L", lod1=None)
    pl_L = g.superellipsoid((0.065, 0.026, 0.066), 0.5, 0.7, 4, 10).translated(0.19, 1.12, 0.0)
    pl_L2 = g.superellipsoid((0.058, 0.020, 0.058), 0.5, 0.7, 4, 10).rotated(0, 0, -20).translated(0.21, 1.09, 0.0)
    p.add("pauldron_L", merge([pl_L, pl_L2]), "RH_Obsidian", "arm_L")
    # right: a smaller obsidian guard with a frost cap (asymmetric)
    pr = g.superellipsoid((0.058, 0.025, 0.058), 0.5, 0.7, 4, 10).rotated(0, 0, 8).translated(-0.19, 1.14, 0.0)
    p.add("shoulder_R", pr, "RH_Obsidian", "arm_R")
    p.add("shoulder_R_frost", frost_layer(pr, 0.007, min_ny=0.4, cover=0.3, seed=2), "RH_Frost", "arm_R", lod1=None, tint=lambda P: np.full(len(P), 0.5))


def arms(p: Piece):
    for s, nm in ((+1, "L"), (-1, "R")):
        up = [(s * 0.19, 1.12, 0), (s * 0.22, 0.98, 0.02), (s * 0.23, 0.93, 0.04)]
        fore = [(s * 0.23, 0.93, 0.04), (s * 0.24, 0.86, 0.12), (s * 0.24, 0.80, 0.17)]
        p.add(f"arm_{nm}", g.tube(up, [0.034, 0.027, 0.024], sides=7, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Armour", f"arm_{nm}", uv_scale=2)
        p.add(f"arm_lames_{nm}", rc.limb_lames(up, [0.034, 0.027, 0.024], [0.28, 0.58], h=0.034, sweep=240, grow=0.005, seg=7), "RH_Obsidian", f"arm_{nm}")
        p.add(f"forearm_{nm}", g.tube(fore, [0.026, 0.021, 0.016], sides=7, samples=2, cap=None, up=(0, 0, 1)), "RH_Armour", f"hand_{nm}", uv_scale=2)
        p.add(f"vambrace_{nm}", rc.limb_lames(fore, [0.026, 0.021, 0.016], [0.25, 0.55, 0.8], h=0.036, sweep=250, grow=0.005, seg=7), "RH_Obsidian", f"hand_{nm}")
        slv = g.tube([(s * 0.19, 1.10, 0.0), (s * 0.21, 1.00, 0.02), (s * 0.235, 0.90, 0.05)], [0.040, 0.044, 0.058], sides=8, samples=2, cap=None, up=(0, 0, 1))
        hem = [(s * 0.235 + 0.050 * math.sin(a), 0.90 - 0.03 * (k % 2) - 0.01, 0.05 + 0.050 * math.cos(a)) for k, a in enumerate(np.linspace(0, TAU, 12, endpoint=False))]
        p.add(f"sleeve_{nm}", slv.noised(0.003, 14, 2, seed=3 + (s > 0)), "RH_Cloth", f"arm_{nm}", uv_scale=2)
        p.add(f"sleeve_ice_{nm}", spikes([((h[0], h[1], h[2]), (h[0] - s * 0.235, -1.0, h[2] - 0.05), 0.045 + 0.02 * (k % 2), 0.006) for k, h in enumerate(hem[::2])], seed=70 + (s > 0), flat=0.25, sides=4, tip=0.5), "RH_Ice", f"arm_{nm}", lod1=None)
        fins = g.extrude_plane(np.array([(0.90, 0.06), (0.84, 0.14), (0.86, 0.17), (0.91, 0.10)]), 0.006, "YZ", bevel=0.002, bevel_segments=1).translated(s * 0.262, 0, 0)
        p.add(f"vambrace_fins_{nm}", fins, "RH_Silver", f"hand_{nm}", tint=lambda P: np.full(len(P), 0.7))
        p.add(f"arm_wire_{nm}", merge([rc.helix(0.0275, 0.84, 0.88, 1.6, r=0.0030, sides=3, per_turn=7, ax=s * 0.241, az=0.12)]), "RH_Silver", f"hand_{nm}", lod1=None)
        wrist = np.array([s * 0.245, 0.785, 0.18])
        p.add(f"hand_{nm}", rc.claw_hand(s, wrist, (0.0, -0.55, 1.0), 0.9, 1.05, 1.6), "RH_Bone", f"hand_{nm}", uv_scale=2)
        claws = spikes([((s * 0.245 + o, 0.745, 0.215), (0, -0.7, 1.0), 0.032, 0.0042) for o in (-0.0135, -0.0045, 0.0045, 0.0135)], seed=60 + (s > 0), flat=0.2, sides=4, tip=0.6)
        p.add(f"claws_{nm}", claws, "RH_Ice", f"hand_{nm}", lod1=None)


# ======================================================================================= head, veil, halo
def head(p: Piece):
    neck = g.tube([(0, 1.13, 0.0), (0, 1.22, 0.01)], [0.030, 0.026], sides=7, samples=1, cap=None, smooth=False)
    p.add("neck", neck, "RH_Bone", "head", uv_scale=2)
    skull = g.superellipsoid((0.052, 0.084, 0.056), 0.8, 0.85, 6, 12).noised(0.002, 24, 2, seed=3).rotated(0, 0, 3)
    cheek = [g.superellipsoid((0.011, 0.014, 0.011), 0.6, 0.6, 3, 6).translated(s * 0.030, -0.020, 0.042) for s in (-1, 1)]
    nose = g.superellipsoid((0.007, 0.014, 0.011), 0.6, 0.6, 3, 6).translated(0, -0.005, 0.054)
    p.add("head", merge([skull, nose] + cheek).translated(0, 1.305, 0.01), "RH_Bone", "head", uv_scale=2)
    eyes = [g.extrude(np.array([(-0.009, -0.003), (0.009, 0.001), (0.007, 0.005), (-0.009, 0.002)]) * [s, 1], 0.005, 0.0012, 1).translated(s * 0.027, 1.318, 0.0645) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "RH_Glow", "head", bake=False, lod1="keep")
    # translucent ice veil with a jagged hem, curving back at the sides
    vp = np.array([(-0.065, 1.285), (-0.020, 1.290), (0.020, 1.290), (0.065, 1.285), (0.078, 1.20), (0.045, 1.185), (0.030, 1.150), (0.0, 1.175), (-0.030, 1.150), (-0.048, 1.190), (-0.078, 1.20)])
    veil = g.extrude(vp, 0.004, 0.001, 1).subdivided_to(0.04, max_levels=1)

    def vf(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        return np.column_stack([x, y, 0.066 - 0.55 * x * x + z + 0.006 * np.sin(x * 90 + y * 40)])
    p.add("veil", g.warp(veil, vf, 40), "RH_Ice", "head", occluder=False)
    # circlet with a gem point
    p.add("circlet", g.torus(0.058, 0.0050, 18, 4).translated(0, 1.37, 0.012), "RH_Silver", "head")
    p.add("circlet_gem", spikes([((0.0, 1.372, 0.068), (0, 0.9, 0.5), 0.050, 0.0085)], seed=5, flat=0.2, sides=5), "RH_Ice", "head")
    # tresses of dark frosted hair streaming back in a slow curve, ice beads at the tips
    strands = []
    for k in range(7):
        sx = (k - 3) * 0.020
        pts = [(sx * 0.9, 1.350, -0.030), (sx * 1.7, 1.27, -0.095 - 0.012 * (k % 3)), (sx * 2.6 + 0.03 * ((k % 2) - 0.5), 1.12 - 0.04 * (k % 3), -0.150 - 0.01 * k), (sx * 3.0, 0.98 - 0.05 * (k % 3), -0.185)]
        strands.append(g.tube(pts, [0.016, 0.014, 0.009, 0.002], sides=5, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)))
    p.add("hair", merge(strands), "RH_Cloth", "head", uv_scale=2)
    p.add("hair_frost", merge([g.tube([(k * 0.02 - 0.06, 1.33, -0.03), (k * 0.045 - 0.135, 1.2, -0.12)], 0.0045, sides=3, samples=1, cap="round", cap_steps=1, smooth=False) for k in range(7)]), "RH_Frost", "head", lod1=None, tint=lambda P: np.full(len(P), 0.45))
    p.add("hair_ice", spikes([((k * 0.06 - 0.18, 1.0 - 0.05 * (k % 3), -0.19), (0, -0.5, -1.0), 0.05 + 0.02 * (k % 3), 0.007) for k in range(7)], seed=8, flat=0.2, sides=4, tip=0.5), "RH_Ice", "head", lod1=None)


def halo(p: Piece):
    cx, cy, z0 = 0.0, 1.31, -0.125
    ts = np.linspace(20, 160, 15)
    outer = [(cx + 0.20 * math.cos(math.radians(t)), cy + 0.20 * math.sin(math.radians(t))) for t in ts]
    inner = []
    for t in ts[::-1]:
        w = 0.058 * (math.sin(math.radians((t - 20) / 140 * 180)) ** 0.7) + 0.004
        inner.append((cx + (0.20 - w) * math.cos(math.radians(t)), cy + (0.20 - w) * math.sin(math.radians(t))))
    poly = np.array(outer + inner)
    cr = g.extrude(poly, 0.040, 0.007, 1).translated(0, 0, z0)
    p.add("halo", cr, "RH_Ice", "top")
    p.add("halo_frost", frost_layer(cr, 0.006, min_ny=0.6, cover=0.2, seed=3), "RH_Frost", "top", lod1=None, tint=lambda P: np.full(len(P), 0.55))
    th = []
    for k in range(9):
        t = 28 + k * 13.5
        pos = (cx + 0.195 * math.cos(math.radians(t)), cy + 0.195 * math.sin(math.radians(t)), z0)
        th.append((pos, (math.cos(math.radians(t)), math.sin(math.radians(t)), 0.0), 0.022 + 0.028 * ((k * 5) % 3) / 2, 0.009))
    p.add("halo_thorns", spikes(th, seed=12, flat=0.2, sides=4, tip=0.5), "RH_Ice", "top")
    arc = g.tube([(cx + 0.150 * math.cos(math.radians(t)), cy + 0.150 * math.sin(math.radians(t)), z0 + 0.003) for t in np.linspace(34, 146, 12)], 0.0042, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
    p.add("halo_glow", arc, "RH_Glow", "top", bake=False, lod1="keep")
    orb = spikes([((cx + 0.23 * math.cos(math.radians(t)) + 0.0, cy + 0.17 * math.sin(math.radians(t)) - 0.03, z0 + 0.0), unit((math.cos(math.radians(t)), 0.3, 0.1)), 0.05, 0.010) for t in (12, 168, 96)], seed=15, flat=0.2, sides=4, tip=0.5)
    p.add("halo_orbit_shards", orb, "RH_Ice", "top", lod1=None)
    # shrouded mist cloak (soft: spine -> top), ragged ice-fray hem
    R, K = 8, 9
    rings = []
    tips = []
    for r in range(R):
        v = r / (R - 1)
        row = []
        for k in range(K):
            u = k / (K - 1)
            y = 1.14 - 0.84 * v
            if r >= R - 2:
                y -= (0.07 if r == R - 1 else 0.02) * (k % 2) * (0.7 + 0.3 * ((k * 5) % 3) / 2)
            xw = 0.14 + 0.08 * v ** 0.8
            x = -xw + 2 * xw * u
            z = -0.118 - 0.07 * v ** 1.3 + 0.01 * math.sin(u * TAU * 2.5)
            row.append((x, y, z))
        rings.append(row)
        if r == R - 1:
            tips = [row[k] for k in range(1, K, 2)]
    cm = g.loft(np.array(rings)[::-1], closed=False, crease=60, v_tile=0.25, u_tile=0.25)
    p.add("cape", cm, "RH_Cloth", "spine", bone2="body", blend=(1.05, 0.55), uv_scale=2)
    caps = []
    rng = np.random.default_rng(2)
    for k in range(12):
        r = int(rng.random() * (R - 2))
        kk = int(rng.random() * K)
        x, y, z = rings[r][kk]
        caps.append(((x, y + 0.01, z - 0.004), (0, 0.4, -1.0), 0.02 + 0.03 * rng.random(), 0.008))
    p.add("cape_frost", spikes(caps, seed=5, flat=0.3, sides=4, tip=0.5), "RH_Frost", "spine", bone2="body", blend=(1.05, 0.55), lod1=None, tint=lambda P: np.full(len(P), 0.55))
    p.add("cape_hem_ice", spikes([((x, y + 0.01, z), (0.1, -1, -0.3), 0.05, 0.010) for x, y, z in tips], seed=6, flat=0.3, sides=4, tip=0.5), "RH_Ice", "spine", bone2="body", blend=(1.05, 0.55), lod1=None)


# ======================================================================================= weapon_summon glaive (grip-local frame placed at GRIP; blade toward -Y)
def glaive(p: Piece):
    def W(m):
        return m.translated(*GRIP)
    shaft = g.tube([(0, 0.34, 0), (0, 0.0, 0), (0, -0.25, 0), (0, -0.48, 0)], [0.015, 0.017, 0.0145, 0.015], sides=7, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)).noised(0.0015, 20, 2, seed=3)
    p.add("glaive_shaft", W(shaft), "RH_Obsidian", "weapon_summon", uv_scale=2)
    wraps = merge([g.torus(0.0195, 0.0036, 8, 3).translated(0, 0.06 - 0.016 * i, 0) for i in range(6)])
    p.add("glaive_wraps", W(wraps), "RH_Silver", "weapon_summon", tint=lambda P: np.full(len(P), 0.6))
    collar = g.lathe([(0.019, -0.44), (0.029, -0.455), (0.029, -0.52), (0.019, -0.535)], 10, crease=35)
    p.add("glaive_collar", W(collar), "RH_Silver", "weapon_summon", tint=lambda P: np.full(len(P), 0.7))
    collar2 = g.lathe([(0.019, 0.24), (0.025, 0.25), (0.025, 0.27), (0.019, 0.28)], 10, crease=35)
    p.add("glaive_collar2", W(collar2), "RH_Silver", "weapon_summon", lod1=None, tint=lambda P: np.full(len(P), 0.7))
    butt = spikes([((0, 0.35, 0), (0, 1, 0), 0.07, 0.016)], seed=3, flat=0.1, sides=5, tip=0.5)
    p.add("glaive_butt", W(butt), "RH_Ice", "weapon_summon")
    # curved glaive blade: slender, swelling then hooking forward (+Z) into a point; a short back-hook
    poly = np.array([(-0.50, -0.026), (-0.58, -0.050), (-0.70, -0.056), (-0.82, -0.030), (-0.92, 0.050), (-0.97, 0.150),
                     (-0.86, 0.108), (-0.76, 0.078), (-0.66, 0.056), (-0.58, 0.040), (-0.50, 0.026)])
    blade = g.extrude_plane(poly, 0.030, "YZ", bevel=0.007, bevel_segments=1)
    p.add("glaive_blade", W(blade), "RH_Ice", "weapon_summon", occluder=False)
    core = g.extrude_plane(np.array([(-0.54, -0.010), (-0.66, -0.020), (-0.78, 0.0), (-0.88, 0.060), (-0.76, 0.045), (-0.62, 0.030)]), 0.011, "YZ", bevel=0.003, bevel_segments=1)
    p.add("glaive_core", W(core), "RH_Frost", "weapon_summon", occluder=False, bake=False, tint=lambda P: np.full(len(P), 0.55))
    hook = spikes([((0.0, -0.50, -0.020), unit((0.0, -0.1, -1.0)), 0.085, 0.014)], seed=3, flat=0.3, sides=5, tip=0.5)
    p.add("glaive_hook", W(hook), "RH_Ice", "weapon_summon")
    gr = []
    for k, (yy, ln, rr) in enumerate(((-0.56, 0.07, 0.012), (-0.66, 0.10, 0.015), (-0.76, 0.12, 0.016), (-0.84, 0.09, 0.013), (-0.62, 0.06, 0.011), (-0.72, 0.08, 0.012))):
        gr.append((np.array([0.0, yy, -0.055]) + GRIP, unit((0.25 * (k % 2 - 0.5), -0.3, -1.0)), ln, rr))
    p.add("glaive_growths", spikes(gr, seed=20, flat=0.3, sides=5, tip=0.42), "RH_Ice", "weapon_summon")


# ======================================================================================= clips
def make_clips() -> list[Clip]:
    def sm(c, vals):
        c.keys("weapon_summon", "scale", vals)

    idle = Clip("Idle", 3.8, loop=True)
    idle.keys("body", "pos", [(0, (0, 0, 0)), (1.2, (0, 0.012, 0), "in_out_cubic"), (2.6, (0, -0.004, 0), "in_out_cubic"), (3.8, (0, 0, 0), "in_out_cubic")])
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.2, (1.2, 0, 0), "in_out_cubic"), (3.8, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.9, (0, 6, 3), "in_out_cubic"), (2.6, (0, -4, 0), "in_out_cubic"), (3.8, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (1.9, (0, 0, 1.5), "in_out_cubic"), (3.8, (0, 0, 0), "in_out_cubic")])
    sm(idle, [(0, 0), (3.8, 0)])

    mv = Clip("Move", 1.0, loop=True)
    mv.keys("body", "rot", [(0, (5, 0, 0)), (0.5, (7, 0, 2), "in_out_cubic"), (1.0, (5, 0, 0), "in_out_cubic")])
    mv.keys("body", "pos", [(0, (0, 0.02, 0)), (0.25, (0, 0.03, 0), "out_quad"), (0.5, (0, 0.02, 0), "in_quad"), (0.75, (0, 0.03, 0), "out_quad"), (1.0, (0, 0.02, 0), "in_quad")])
    mv.keys("top", "rot", [(0, (-6, 0, 0)), (0.5, (-10, 8, 0), "in_out_cubic"), (1.0, (-6, 0, 0), "in_out_cubic")])
    sm(mv, [(0, 0), (1.0, 0)])

    A = Clip("Attack", 2.4, fps=60)
    sm(A, [(0, 0), (0.30, 1.15, "out_cubic"), (0.45, 1.0, "in_out_cubic"), (2.1, 1.0), (2.4, 0, "in_quad")])
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.45, (-75, 0, 0), "out_cubic"), (1.05, (-85, -20, 0), "in_out_cubic"), (1.30, (-85, -20, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.45, (-12, 0, 0), "out_cubic"), (1.30, (-8, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.45, (-3, 0, 0), "out_cubic"), (1.05, (0, -60, 0), "in_out_cubic"), (1.17, (0, -60, 0)), (1.30, (0, 72, 0), "in_cubic"), (1.55, (0, 60, 0), "out_quad"), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.45, (0, 0, 0)), (1.05, (-6, -5, 0), "in_out_cubic"), (1.17, (-6, -5, 0)), (1.30, (0, 15, 0), "in_cubic"), (1.55, (0, 12, 0), "out_quad"), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.45, (0, 0, 0)), (1.05, (0, 0.03, -0.10), "in_out_cubic"), (1.17, (0, 0.03, -0.10)), (1.30, (0, 0.0, 0.28), "in_cubic"), (1.55, (0, 0, 0.26), "out_quad"), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.45, (-5, 0, 0), "out_cubic"), (1.05, (0, 20, 0), "in_out_cubic"), (1.17, (0, 20, 0)), (1.30, (0, -10, 0), "in_cubic"), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.45, (0, 0, 0)), (1.05, (-40, 0, 20), "in_out_cubic"), (1.30, (-40, 0, 20)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.45, (0, 20, 0), "out_cubic"), (1.17, (0, 20, 0)), (1.30, (0, -20, 0), "in_cubic"), (2.4, (0, 0, 0), "in_out_cubic")])

    hit = Clip("HitReact", 0.5)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.10, (-10, 0, 0), "out_cubic"), (0.50, (-4, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.07), "out_cubic"), (0.50, (0, 0, -0.02), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-9, 0, 0), "out_cubic"), (0.50, (-3, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.10, (-14, 0, 6), "out_cubic"), (0.50, (-5, 0, 2), "in_out_cubic")])
    hit.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.10, (12, 0, 0), "out_cubic"), (0.50, (3, 0, 0), "in_out_cubic")])
    hit.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.10, (12, 0, 0), "out_cubic"), (0.50, (3, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (14, 12, 0), "out_cubic"), (0.50, (0, 0, 0), "in_out_cubic")])
    sm(hit, [(0, 0), (0.5, 0)])

    vic = Clip("Victory", 2.0)
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.6, (-60, 0, 0), "out_back"), (2.0, (-60, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.6, (-25, 0, 0), "out_cubic"), (2.0, (-25, 0, 0))])
    vic.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.6, (-30, 0, 0), "out_cubic"), (2.0, (-30, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.6, (-12, 0, 0), "out_cubic"), (2.0, (-12, 0, 0))])
    vic.keys("spine", "rot", [(0, (0, 0, 0)), (0.6, (-6, 0, 0), "out_cubic"), (2.0, (-6, 0, 0))])
    vic.keys("body", "pos", [(0, (0, 0, 0)), (0.6, (0, 0.03, 0), "out_cubic"), (2.0, (0, 0.03, 0))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (1.2, (0, 30, 0), "out_cubic"), (2.0, (0, 30, 0))])
    sm(vic, [(0, 0), (2.0, 0)])
    T = Clip("Taunt", 1.6)           # halo flares, then a slow beckoning gesture with the free hand
    sm(T, [(0, 0), (1.6, 0)])
    T.keys("top", "scale", [(0, (1, 1, 1)), (0.40, (1.30, 1.30, 1.30), "out_back"), (0.80, (1.12, 1.12, 1.12), "in_out_cubic"), (1.6, (1, 1, 1), "in_out_cubic")])
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.40, (-6, 20, 0), "out_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.45, (0, 0, 0)), (0.80, (-72, 0, 14), "out_cubic"), (1.30, (-72, 0, 14)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("hand_L", "rot", [(0, (0, 0, 0)), (0.80, (-10, 0, 0), "out_cubic"), (0.95, (-42, 0, 0), "in_out_quad"), (1.10, (0, 0, 0), "in_out_quad"), (1.25, (-42, 0, 0), "in_out_quad"), (1.40, (-10, 0, 0)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("head", "rot", [(0, (0, 0, 0)), (0.80, (-4, -6, 6), "in_out_cubic"), (1.30, (-4, -6, 6)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("spine", "rot", [(0, (0, 0, 0)), (0.80, (-3, -8, 0), "in_out_cubic"), (1.30, (-3, -8, 0)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "pos", [(0, (0, 0, 0)), (0.40, (0, 0.03, 0), "out_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    return [idle, mv, A, hit, vic, T]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "queen", rig, make_clips(), impact_time=1.30, strike_range=0.70, attack_style="summon", seed=9)
    rc.pedestal_parts(p)
    gown(p)
    bodice(p)
    arms(p)
    head(p)
    halo(p)
    glaive(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris (+{p.node_tri_count()} weapon_summon) before baking")
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
