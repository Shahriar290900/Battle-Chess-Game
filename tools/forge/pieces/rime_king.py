"""rime_king - Rime Glacier Tyrant: a colossal armoured revenant lord in faceted obsidian plate, the glacier he was
buried in breaking out through his back as a ridge of ice, a ring of short ice prisms hovering over his helm, a frozen
cape swept back, a cracked visor glowing.  Unarmed: fist and backhand.  Built from docs/art/rime_king.md."""
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

ASSET_ID = "rime_king"


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.76, 0))
    r.add("spine", "body", (0, 0.92, 0))
    r.add("head", "spine", (0, 1.33, 0.02))
    r.add("top", "spine", (0, 1.62, 0))
    r.add("arm_L", "spine", (0.32, 1.30, 0))
    r.add("hand_L", "arm_L", (0.33, 1.05, 0.04))
    r.add("arm_R", "spine", (-0.32, 1.30, 0))
    r.add("hand_R", "arm_R", (-0.33, 1.05, 0.04))
    r.socket("socket_weapon_R", "hand_R", (-0.35, 0.86, 0.17))
    r.socket("socket_cast", "hand_R", (-0.35, 0.86, 0.17))
    r.socket("socket_impact", "body", (-0.15, 1.00, 0.60))
    r.socket("socket_head", "top", (0, 1.74, 0))
    return r


# ---- torso ring family: one set of curves describes chest, lames, belt so layers always nest
Y_LV = np.array([0.88, 0.94, 1.02, 1.10, 1.18, 1.25, 1.30])
HW = np.array([0.132, 0.148, 0.176, 0.204, 0.224, 0.208, 0.150])
ZF = np.array([0.092, 0.098, 0.110, 0.124, 0.130, 0.116, 0.090])
ZB = np.array([0.090, 0.095, 0.100, 0.105, 0.108, 0.100, 0.080])


def tring(y, grow=0.0, K=14, ridge=0.0, facet=0.0):
    hw = np.interp(y, Y_LV, HW) + grow
    zf = np.interp(y, Y_LV, ZF) + grow
    zb = np.interp(y, Y_LV, ZB) + grow
    th = np.linspace(0, TAU, K, endpoint=False)
    s, c = np.sin(th), np.cos(th)
    x = hw * np.sign(s) * np.abs(s) ** 0.85
    z = np.where(c > 0, zf * c, zb * c)
    z = z + ridge * np.exp(-(x / 0.035) ** 2) * (c > 0)
    return np.stack([x, np.full(K, y), z], 1)


def shell(specs, K=14, crease=35.0, cap_end=False, cap_start=False):
    rings = np.stack([tring(y, gr, K, rd) for y, gr, rd in specs])
    return g.loft(rings, closed=True, crease=crease, cap_end=cap_end, cap_start=cap_start)


# ======================================================================================= legs, kilt
def lower_body(p: Piece):
    for s, nm in ((+1, "L"), (-1, "R")):
        dz = 0.03 if s > 0 else 0.0                     # weight on the left leg, right foot a little back
        boot = g.superellipsoid((0.066, 0.036, 0.122), 0.4, 0.5, 4, 10).translated(s * 0.14, 0.258, 0.05 + dz)
        toe = g.superellipsoid((0.058, 0.026, 0.040), 0.4, 0.5, 3, 8).translated(s * 0.14, 0.270, 0.150 + dz)
        p.add(f"boot_{nm}", merge([boot, toe]), "RH_Obsidian", "body")
        p.add(f"boot_spike_{nm}", spikes([((s * 0.14, 0.262, 0.185 + dz), (0.0, 0.1, 1.0), 0.065, 0.016)], seed=3 + (s > 0), flat=0.3, sides=5), "RH_Ice", "body")
        gp = [(s * 0.14, 0.28, 0.05 + dz), (s * 0.145, 0.40, 0.06 + dz), (s * 0.15, 0.52, 0.05 + dz * 0.5)]
        ridge_sec = lambda th, t: 1 + 0.30 * np.exp(-(np.arctan2(np.sin(th), np.cos(th)) / 0.55) ** 2) * (0.5 + 0.5 * np.sin(math.pi * t))
        greave = g.tube(gp, [0.050, 0.064, 0.072], sides=10, samples=3, cap=None, up=(0, 0, 1), section=ridge_sec).noised(0.0015, 20, 2, seed=4)
        p.add(f"greave_{nm}", greave, "RH_Obsidian", "body")
        p.add(f"greave_lames_{nm}", rc.limb_lames(gp, [0.050, 0.064, 0.072], [0.12, 0.88], h=0.050, sweep=250, grow=0.012, seg=8), "RH_Armour", "body")
        bands = merge([g.torus(0.060 + 0.012 * k, 0.0052, 14, 4).translated(s * (0.142 + 0.004 * k), y, 0.054 + dz) for k, y in enumerate((0.34, 0.455))])
        p.add(f"greave_bands_{nm}", bands, "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
        pol = g.superellipsoid((0.066, 0.056, 0.052), 0.4, 0.5, 5, 12).translated(s * 0.15, 0.555, 0.088 + dz * 0.5)
        pol2 = g.superellipsoid((0.016, 0.052, 0.040), 0.4, 0.5, 3, 8).translated(s * 0.15, 0.560, 0.126 + dz * 0.5)
        p.add(f"knee_{nm}", merge([pol, pol2]), "RH_Obsidian", "body")
        p.add(f"knee_fins_{nm}", merge([g.extrude(np.array([(0, 0), (0.05, 0.016), (0.0, 0.034)]), 0.010, 0.002, 1).rotated(0, s * 90, 0).translated(s * (0.150 + 0.058), 0.560 + 0.012 * q, 0.09 + dz * 0.5) for q in (-1, 1)]), "RH_Obsidian", "body", lod1=None)
        p.add(f"knee_spike_{nm}", spikes([((s * 0.15, 0.560, 0.135 + dz * 0.5), (0.3 * s, 0.3, 1.0), 0.11, 0.030)], seed=6 + (s > 0), flat=0.3, sides=5, tip=0.4), "RH_Ice", "body")
        p.add(f"knee_frost_{nm}", cluster((s * 0.15, 0.605, 0.075 + dz * 0.5), (0, 1, 0.2), 3, (0.03, 0.06), (0.008, 0.012), spread=0.03, tilt=30, seed=7 + (s > 0), flat=0.3, sides=4), "RH_Frost", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
        tp = [(s * 0.145, 0.54, 0.04 + dz * 0.4), (s * 0.135, 0.68, 0.02), (s * 0.120, 0.80, 0.0)]
        thigh = g.tube(tp, [0.070, 0.084, 0.090], sides=8, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"thigh_{nm}", thigh, "RH_Armour", "body", uv_scale=2)
        p.add(f"thigh_lames_{nm}", rc.limb_lames(tp, [0.070, 0.084, 0.090], [0.25, 0.5, 0.75], h=0.075, sweep=215, grow=0.008, seg=8), "RH_Obsidian", "body")
    pelvis = g.superellipsoid((0.15, 0.065, 0.11), 0.4, 0.5, 4, 12).translated(0, 0.82, 0)
    p.add("pelvis", pelvis, "RH_Armour", "body", uv_scale=2)
    # frozen mail kilt: 14 stiff jagged strips, flaring out 12 degrees, frost on the upper face
    rng = np.random.default_rng(9)
    strips, frost = [], []
    for k in range(14):
        a = k * TAU / 14 + 0.12
        r = 0.185 + 0.03 * (abs(math.sin(a)) > 0.7)
        ln = 0.17 + 0.10 * rng.random()
        poly = np.array([(-0.040, 0), (0.040, 0), (0.034, -ln * 0.75), (0.004, -ln), (-0.030, -ln * 0.78)])
        m = g.extrude(poly, 0.012, 0.0028, 1).rotated(-12, 0, 0).translated(0, 0.805, r).rotated(0, math.degrees(a), 0)
        strips.append(m)
        frost.append(((r + 0.004) * math.sin(a), 0.812, (r + 0.004) * math.cos(a)))
    p.add("kilt", merge(strips), "RH_Cloth", "body", uv_scale=2)
    p.add("kilt_frost", spikes([(f, (math.sin(math.atan2(f[0], f[2])), 0.7, math.cos(math.atan2(f[0], f[2]))), 0.035, 0.010) for f in frost], seed=5, flat=0.3, sides=4, tip=0.5), "RH_Frost", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    # layered tassets: two rows of curved obsidian plates hanging over the kilt, each with a silver rim
    tas = []
    for row, (y0, ww) in enumerate(((0.80, 0.105), (0.745, 0.095))):
        for k, a in enumerate(np.arange(-60, 61, 30) + (15 if row else 0)):
            if abs(a) > 61:
                continue
            pl = g.plate(ww, 0.13, 0.012, 0.005, bend_r=0.20, inner_x=2, taper=lambda t: 1 - 0.22 * (t + 1) / 2, drop_back=True)
            tas.append(pl.rotated(-12 - 3 * row, 0, 0).translated(0, y0 - 0.05, 0.205 + 0.012 * row).rotated(0, float(a), 0))
    p.add("tassets", merge(tas), "RH_Obsidian", "body")
    p.add("tasset_studs", g.instances(g.dome(0.008, 0.007, 6, 1), [(0.205 * math.sin(math.radians(a)) * 1.0, 0.80 - 0.003, 0.205 * math.cos(math.radians(a)) + 0.012) for a in range(-60, 61, 30)],
                                      [(math.sin(math.radians(a)), 0.1, math.cos(math.radians(a))) for a in range(-60, 61, 30)]), "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    # belt + rune plate (snow-crystal glyph) + chain with shards
    belt = shell([(0.855, 0.0, 0), (0.862, 0.014, 0), (0.905, 0.014, 0), (0.912, 0.0, 0)], 20, 40)
    belt = g.lathe([(0.150, 0.86), (0.162, 0.865), (0.162, 0.905), (0.150, 0.91)], 16, crease=35)
    p.add("belt", belt, "RH_Obsidian", "body")
    plate = g.extrude(g.rect_poly(0.11, 0.09, 0.008, 1), 0.016, 0.004, 1).translated(0, 0.882, 0.168)
    p.add("belt_plate", plate, "RH_Obsidian", "body")
    bars = [g.extrude(g.rect_poly(0.058, 0.0075), 0.005, 0.001, 1).rotated(0, 0, a).translated(0, 0.882, 0.178) for a in (0, 60, 120)]
    p.add("belt_glyph", merge(bars), "RH_Silver", "body")
    chain = rc.zigzag((0.0, 0.84, 0.17), (0.07, 0.62, 0.17), 7, 0.007, r=0.0045, side=(1, 0, 0))
    p.add("belt_chain", chain, "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.55))
    p.add("belt_shards", spikes([((0.07, 0.625, 0.17), (0.1, -1, 0.1), 0.08, 0.012), ((0.02, 0.66, 0.17), (0, -1, 0.1), 0.06, 0.010), ((0.1, 0.68, 0.16), (0.2, -1, 0.1), 0.05, 0.009)], seed=8, flat=0.3, sides=4, tip=0.5), "RH_Ice", "body")


# ======================================================================================= torso
def torso(p: Piece):
    barrel = g.tube([(0, 0.92, 0), (0, 1.08, 0), (0, 1.24, 0)], [0.130, 0.170, 0.205], sides=12, samples=3, cap="round", cap_steps=1, ellipse=(0.62, 1.0), up=(0, 0, 1))
    p.add("barrel", barrel, "RH_Armour", "spine", uv_scale=2)
    # abdominal plates: three overlapping curved lames, narrower than the chest (V-taper) with silver rims
    for i, y0 in enumerate((0.915, 0.965, 1.015)):
        w = 0.128 + 0.018 * i
        pl = g.plate(2 * w, 0.062, 0.016, 0.006, bend_r=0.15 + 0.01 * i, inner_x=4, taper=lambda t: 1 - 0.12 * (1 - abs(t)), drop_back=True)
        pl = pl.rotated(8 - 2 * i, 0, 0).translated(0, y0 + 0.03, 0.085 + 0.006 * i + 0.012 * i)
        p.add(f"abs_plate_{i}", pl, "RH_Obsidian", "spine")
    side = []
    for sx in (-1, 1):
        for i, y0 in enumerate((0.95, 1.0, 1.05)):
            side.append(g.superellipsoid((0.040, 0.026, 0.060), 0.5, 0.6, 3, 8).rotated(0, sx * 25, 0).translated(sx * (0.150 + 0.012 * i), y0, 0.0))
    p.add("side_plates", merge(side), "RH_Obsidian", "spine")
    # sculpted pectorals, keel ridge, collarbone plates, trapezius slopes up to the pauldrons
    pec = [g.superellipsoid((0.100, 0.082, 0.050), 0.45, 0.6, 5, 12).rotated(0, sx * 12, 0).translated(sx * 0.095, 1.17, 0.095) for sx in (-1, 1)]
    p.add("pectorals", merge(pec), "RH_Obsidian", "spine")
    keel = g.extrude(np.array([(-0.012, 1.02), (0.012, 1.02), (0.018, 1.17), (0.0, 1.27), (-0.018, 1.17)]), 0.040, 0.012, 1).translated(0, 0, 0.123)
    p.add("keel_ridge", keel, "RH_Obsidian", "spine", lod1=None)
    col = [g.superellipsoid((0.100, 0.020, 0.050), 0.45, 0.6, 3, 9).rotated(0, 0, sx * -14).translated(sx * 0.115, 1.285, 0.045) for sx in (-1, 1)]
    p.add("collar_plates", merge(col), "RH_Obsidian", "spine")
    trap = [g.superellipsoid((0.110, 0.034, 0.085), 0.5, 0.65, 4, 10).rotated(0, 0, sx * -24).translated(sx * 0.185, 1.305, -0.005) for sx in (-1, 1)]
    p.add("trapezius", merge(trap), "RH_Obsidian", "spine")
    # faceted breast/back shell with a central ridge: cracked open along the spine
    ridge = lambda y: 0.020 * smoothstep(1.04, 1.12, y) * (1 - smoothstep(1.22, 1.30, y))
    ys = [1.100, 1.108, 1.14, 1.18, 1.22, 1.26, 1.295]
    gr = [0.002, 0.012, 0.016, 0.018, 0.018, 0.014, 0.0]
    cuirass = g.loft(np.stack([tring(y, a, 14, ridge(y)) for y, a in zip(ys, gr)]), closed=True, crease=32)
    cuirass = cuirass.dented(5, 0.04, 0.003, seed=11)
    p.add("cuirass", cuirass, "RH_Obsidian", "spine")
    p.add("cuirass_lip", g.tube(tring(1.102, 0.0105, 20), 0.0075, sides=4, samples=1, cap=None, smooth=False, closed=True, up=(0, 1, 0)), "RH_Silver", "spine", lod1=None)
    p.add("cuirass_frost", frost_layer(cuirass, 0.008, min_ny=0.5, cover=0.3, seed=3), "RH_Frost", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    # three silver rune glyphs on the breastplate (one lit)
    glyphs = []
    for k, (x, y) in enumerate(((-0.07, 1.20), (0.07, 1.20), (0.0, 1.13))):
        def bar(x0, y0, x1, y1, w=0.0055):
            L = math.hypot(x1 - x0, y1 - y0)
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) - 90
            return g.extrude(g.rect_poly(w, L), 0.005, 0.001, 1).rotated(0, 0, ang).translated((x0 + x1) / 2, (y0 + y1) / 2, 0)
        parts = [bar(0, -0.035, 0, 0.035), bar(0, 0.035, 0.022, 0.012), bar(0, 0.008, 0.022, -0.016)] if k != 1 else [bar(-0.018, 0.035, 0.008, 0.004), bar(0.008, 0.004, -0.012, -0.008), bar(-0.012, -0.008, 0.016, -0.035)]
        z = float(np.interp(y, Y_LV, ZF)) + 0.020 + float(ridge(y)) * math.exp(-(x / 0.035) ** 2)
        glyphs.append(merge(parts).translated(x, y, z))
    p.add("chest_glyphs", merge(glyphs), "RH_Silver", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.7))
    # ice breaking through the chest (right side)
    p.add("chest_ice", cluster((-0.13, 1.10, 0.125), (-0.3, 0.5, 1.0), 4, (0.06, 0.11), (0.015, 0.026), spread=0.05, tilt=30, seed=13, flat=0.3), "RH_Ice", "spine")
    # backplate cracked along the spine: two halves
    bp = []
    for sx in (-1, 1):
        poly = np.array([(sx * 0.012, 0.96), (sx * 0.18, 0.96), (sx * 0.21, 1.12), (sx * 0.19, 1.27), (sx * 0.012, 1.27)])
        m = g.extrude(poly, 0.020, 0.005, 1)
        bp.append(m.subdivided_to(0.07, max_levels=1))
    back = merge(bp)

    def warp_back(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        zb = np.interp(y, Y_LV, ZB) * np.sqrt(np.clip(1 - (x / (np.interp(y, Y_LV, HW) + 0.02)) ** 2, 0.05, 1))
        return np.column_stack([x, y, -zb - 0.014 + z])
    p.add("backplate", g.warp(back, warp_back, 40), "RH_Obsidian", "spine")
    # the back ridge: seven crystals breaking out along the spine, tallest tip 1.55
    ys_ = [0.98, 1.06, 1.14, 1.22, 1.30, 1.38, 1.44]
    ln_ = [0.14, 0.20, 0.27, 0.30, 0.28, 0.21, 0.14]
    rr_ = [0.030, 0.036, 0.044, 0.050, 0.046, 0.038, 0.030]
    specs = []
    rng = np.random.default_rng(14)
    for i, (y, ln, r) in enumerate(zip(ys_, ln_, rr_)):
        z = -float(np.interp(min(y, 1.30), Y_LV, ZB)) - 0.01 - 0.01 * i * 0.3
        d = unit((0.14 * (rng.random() - 0.5), 1.0, -0.36 - 0.05 * (i % 2)))
        specs.append(((0.0, y, z), d, ln, r))
    tops = [s[0][1] + s[1][1] * s[2] for s in specs]
    k = 1.0 + (1.55 - max(tops)) / (max(tops) - 0.0 + 1e-9) * 0.9
    specs = [(a, b, c * (k if (a[1] + b[1] * c) == max(tops) else 1.0), d) for a, b, c, d in specs]
    p.add("back_ridge", spikes(specs, seed=70, bend=0.05, flat=0.26, sides=6, tip=0.42, jitter=0.15), "RH_Ice", "spine")
    sub = []
    for i, (y, ln, r) in enumerate(zip(ys_, ln_, rr_)):
        for sx in (-1, 1):
            sub.append(((sx * 0.055, y - 0.02, -float(np.interp(min(y, 1.30), Y_LV, ZB)) - 0.005), unit((sx * 0.6, 0.8, -0.5)), 0.07 + 0.03 * (i % 3), 0.014))
    p.add("back_ridge_sub", spikes(sub, seed=90, flat=0.3, sides=5, tip=0.45), "RH_Ice", "spine", lod1=None)
    seam = [g.torus(0.040 + 0.004 * (i % 2), 0.0034, 12, 3).rotated(80, 0, 0).translated(0, y - 0.005, -float(np.interp(min(y, 1.30), Y_LV, ZB)) - 0.004) for i, y in enumerate(ys_)]
    p.add("ridge_seams", merge(seam), "RH_Seam", "spine", bake=False, lod1=None)
    # neck + gorget
    neck = g.tube([(0, 1.30, 0), (0, 1.37, 0.02)], [0.064, 0.058], sides=8, samples=1, cap=None, smooth=False)
    p.add("neck", neck, "RH_Armour", "head", uv_scale=2)
    gor = g.lathe([(0.095, 1.30), (0.114, 1.31), (0.118, 1.36), (0.098, 1.385), (0.076, 1.385)], 8, crease=30)
    p.add("gorget", gor, "RH_Obsidian", "spine")
    p.add("gorget_wire", g.torus(0.118, 0.0055, 16, 4).translated(0, 1.335, 0), "RH_Silver", "spine", lod1=None)


# ======================================================================================= cape
def cape(p: Piece):
    R, K = 11, 12
    rings = []
    tips = []
    for r in range(R):
        v = r / (R - 1)
        row = []
        for k in range(K):
            u = k / (K - 1)
            y = 1.30 - 0.90 * v
            if r >= R - 2:
                y -= (0.07 if r == R - 1 else 0.018) * (k % 2) * (0.7 + 0.3 * ((k * 5) % 3) / 2)
            xl, xr = -0.20 * (1 + 0.08 * v), 0.20 * (1 + 0.35 * v)
            x = xl + (xr - xl) * u + 0.12 * v ** 1.5
            z = -0.125 - 0.17 * v ** 1.3 + 0.014 * math.sin(u * TAU * 3 + 0.8) * (0.3 + v) * (1 if k % 2 else -1) * 0.7
            z += -0.02 * math.sin(u * math.pi)
            row.append((x, y, z))
        rings.append(row)
        if r == R - 1:
            tips = [row[k] for k in range(1, K, 2)]
    cm = g.loft(np.array(rings)[::-1], closed=False, crease=40, v_tile=0.25, u_tile=0.25)
    p.add("cape", cm, "RH_Cloth", "spine", bone2="body", blend=(1.25, 0.55), uv_scale=2)
    # ice sheath along the leading (left) edge + frost caps on the folds
    sheath = []
    for r in range(R):
        row = []
        for k in range(K - 3, K):
            x, y, z = rings[r][k]
            row.append((x, y, z - 0.014))
        sheath.append(row)
    sh = g.loft(np.array(sheath)[::-1], closed=False, crease=40, v_tile=0.25, u_tile=0.25)
    p.add("cape_sheath", sh, "RH_Ice", "spine", bone2="body", blend=(1.25, 0.55))
    caps = []
    rng = np.random.default_rng(3)
    for k in range(14):
        r = 1 + int(rng.random() * (R - 3))
        kk = int(rng.random() * K)
        x, y, z = rings[r][kk]
        caps.append(((x, y + 0.012, z - 0.004), unit((0.0, 0.5, -1.0)), 0.025 + 0.03 * rng.random(), 0.010))
    p.add("cape_frost", spikes(caps, seed=40, flat=0.3, sides=4, tip=0.5), "RH_Frost", "spine", bone2="body", blend=(1.25, 0.55), lod1=None, tint=lambda P: np.full(len(P), 0.6))
    p.add("cape_hem_ice", spikes([((x, y + 0.01, z), (0.2, -1, -0.2), 0.06, 0.012) for x, y, z in tips], seed=44, flat=0.3, sides=4, tip=0.5), "RH_Ice", "spine", bone2="body", blend=(1.25, 0.55), lod1=None)
    # snow-crystal fasteners at the yoke fronts
    for s in (-1, 1):
        d = g.lathe([(0, 0), (0.026, 0), (0.026, 0.008), (0, 0.010)], 12).rotated(90, 0, 0)
        bars = [g.extrude(g.rect_poly(0.040, 0.005), 0.004, 0.001, 1).rotated(0, 0, a) for a in (0, 60, 120)]
        pos = (s * 0.115, 1.27, 0.115)
        p.add(f"fastener_{'L' if s > 0 else 'R'}", merge([d.translated(*pos), merge(bars).translated(pos[0], pos[1], pos[2] + 0.012)]), "RH_Silver", "spine", lod1=None)


# ======================================================================================= pauldrons, arms
BELL = [(0.0, 0.070), (0.060, 0.068), (0.105, 0.046), (0.128, 0.0), (0.120, -0.007), (0.136, -0.013), (0.153, -0.052), (0.144, -0.059), (0.160, -0.066),
        (0.178, -0.108), (0.168, -0.115), (0.180, -0.122), (0.192, -0.152), (0.0, -0.152)]


def bell(side, scale=1.0, tilt=18.0):
    prof = [(r * scale, y * scale) for r, y in BELL][::-1]
    m = g.lathe(prof, 16, crease=30).noised(0.0022, 14, 2, seed=5 + int(side > 0))
    lips = merge([g.torus(r * scale, 0.0058 * scale, 18, 4).translated(0, y * scale, 0) for r, y in ((0.138, -0.013), (0.162, -0.067), (0.183, -0.123))])
    return m, lips


def place(m, side, cx, cy, tilt, sx=1.12, sz=0.95):
    return m.scaled(sx, 1.0, sz).rotated(0, 0, side * -tilt).translated(cx, cy, 0.0)


def pauldrons(p: Piece):
    # left: huge and spiked, a stepped bell of layered spaulder skirts with rolled silver-trimmed lips
    m, lips = bell(+1, 0.84)
    p.add("pauldron_L", place(m, +1, 0.335, 1.285, 18), "RH_Obsidian", "arm_L")
    p.add("pauldron_L_lips", place(lips, +1, 0.335, 1.285, 18), "RH_Silver", "arm_L", lod1=None, tint=lambda P: np.full(len(P), 0.55))
    p.add("pauldron_L_frost", frost_layer(place(m, +1, 0.335, 1.285, 18), 0.009, min_ny=0.55, cover=0.3, seed=5), "RH_Frost", "arm_L", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    sp = []
    for k, (x, z, ln, tl) in enumerate(((0.36, 0.06, 0.19, 18), (0.40, -0.03, 0.22, 26), (0.30, -0.07, 0.15, 10), (0.43, 0.05, 0.12, 38), (0.27, 0.07, 0.13, 6), (0.37, 0.09, 0.10, 28))):
        sp.append(((x, 1.340, z), unit((math.sin(math.radians(tl)), 1.0, 0.05 * (k - 2))), ln, 0.032 - 0.003 * k))
    p.add("pauldron_L_spikes", spikes(sp, seed=21, flat=0.3, sides=5, tip=0.4), "RH_Ice", "arm_L")
    p.add("pauldron_L_side_spikes", spikes([((0.44 + 0.02 * i, 1.22 - 0.055 * i, 0.0), unit((1.0, -0.2, 0.0)), 0.07 - 0.008 * i, 0.019) for i in range(3)] +
                                           [((0.38 + 0.02 * i, 1.21 - 0.055 * i, 0.12), unit((0.7, -0.2, 0.7)), 0.06, 0.015) for i in range(2)], seed=24, flat=0.3, sides=5, tip=0.4), "RH_Ice", "arm_L", lod1=None)
    # right: smoother, smaller bell with a silver rune band (asymmetric), no spikes
    mr, lr = bell(-1, 0.76)
    p.add("pauldron_R", place(mr, -1, -0.325, 1.275, 12, 1.05, 1.0), "RH_Obsidian", "arm_R")
    p.add("pauldron_R_lips", place(lr, -1, -0.325, 1.275, 12, 1.05, 1.0), "RH_Silver", "arm_R", lod1=None, tint=lambda P: np.full(len(P), 0.55))
    p.add("pauldron_R_frost", frost_layer(place(mr, -1, -0.325, 1.275, 12, 1.05, 1.0), 0.009, min_ny=0.55, cover=0.3, seed=6), "RH_Frost", "arm_R", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    runes = []
    for k in range(7):
        a_ = math.radians(-70 + 23 * k)
        runes.append(g.extrude(g.rect_poly(0.0065, 0.030), 0.004, 0.001, 1).rotated(0, 0, 14 * (k % 3 - 1)).translated(0, 1.24, 0.14).rotated(0, math.degrees(a_), 0).translated(-0.325, 0, 0))
    p.add("pauldron_R_runes", merge(runes), "RH_Silver", "arm_R", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    p.add("pauldron_R_spikes", spikes([((-0.36, 1.33, 0.02), unit((-0.5, 1.0, 0.0)), 0.07, 0.020), ((-0.30, 1.34, -0.04), unit((-0.2, 1.0, -0.2)), 0.06, 0.018)], seed=27, flat=0.3, sides=5, tip=0.4), "RH_Ice", "arm_R", lod1=None)


def arms(p: Piece):
    for s, nm in ((+1, "L"), (-1, "R")):
        up = [(s * 0.32, 1.30, 0.0), (s * 0.325, 1.17, 0.02), (s * 0.33, 1.05, 0.04)]
        p.add(f"upper_arm_{nm}", g.tube(up, [0.064, 0.054, 0.048], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Armour", f"arm_{nm}", uv_scale=2)
        p.add(f"rerebrace_{nm}", rc.limb_lames(up, [0.064, 0.054, 0.048], [0.45, 0.80], h=0.075, sweep=250, grow=0.010, seg=8), "RH_Obsidian", f"arm_{nm}")
        p.add(f"elbow_spike_{nm}", spikes([((s * 0.375, 1.05, -0.03), (s * 1.0, 0.0, -0.4), 0.085, 0.024)], seed=30 + (s > 0), flat=0.3, sides=5, tip=0.4), "RH_Ice", f"hand_{nm}")
        fp = [(s * 0.33, 1.05, 0.04), (s * 0.35, 0.95, 0.11), (s * 0.35, 0.86, 0.15)]
        p.add(f"forearm_{nm}", g.tube(fp, [0.048, 0.044, 0.040], sides=8, samples=2, cap=None, up=(0, 0, 1)), "RH_Armour", f"hand_{nm}", uv_scale=2)
        p.add(f"vambrace_{nm}", rc.limb_lames(fp, [0.048, 0.044, 0.040], [0.30, 0.62], h=0.085, sweep=250, grow=0.010, seg=8), "RH_Obsidian", f"hand_{nm}")
        p.add(f"vambrace_wire_{nm}", merge([rc.helix(0.046, 0.93, 0.98, 2.0, r=0.0045, sides=3, per_turn=8, ax=s * 0.349, az=0.105)]), "RH_Silver", f"hand_{nm}", lod1=None)
        # gauntlet fist: block + 4 knuckle spikes + thumb; right fist larger with an ice crust
        sc = 1.12 if s < 0 else 1.0
        fist = g.superellipsoid((0.045 * sc, 0.040 * sc, 0.050 * sc), 0.4, 0.5, 4, 10).translated(s * 0.35, 0.835, 0.17)
        p.add(f"fist_{nm}", fist, "RH_Obsidian", f"hand_{nm}")
        kn = spikes([((s * (0.335 + 0.0225 * k), 0.84, 0.215), (0.0, 0.2, 1.0), 0.032, 0.008) for k in range(4)], seed=50 + (s > 0), flat=0.2, sides=4, tip=0.55) if True else None
        p.add(f"knuckles_{nm}", kn, "RH_Ice", f"hand_{nm}", lod1=None)
        th = g.tube([(s * 0.315, 0.845, 0.18), (s * 0.31, 0.83, 0.205)], [0.013, 0.010], sides=5, samples=1, cap="round", cap_steps=1, smooth=False)
        p.add(f"thumb_{nm}", th, "RH_Obsidian", f"hand_{nm}", lod1=None)
        p.add(f"shoulder_frost_{nm}", cluster((s * 0.37, 1.32, 0.04), (s * 0.4, 1.0, 0.0), 2, (0.03, 0.05), (0.008, 0.012), spread=0.02, tilt=25, seed=60 + (s > 0), flat=0.3, sides=4), "RH_Frost", f"arm_{nm}", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    p.add("fist_crust", cluster((-0.355, 0.88, 0.20), (-0.2, 0.8, 0.6), 5, (0.04, 0.09), (0.010, 0.016), spread=0.04, tilt=35, seed=71, flat=0.3), "RH_Ice", "hand_R")


# ======================================================================================= head
def head(p: Piece):
    prof = [(0.090, 1.345), (0.100, 1.40), (0.096, 1.46), (0.074, 1.50), (0.036, 1.52), (0.0, 1.525)]
    helm = g.lathe(prof, 8, crease=28)
    helm = helm.scaled(1.0, 1.0, 1.08).translated(0, 0, 0.012)
    p.add("helm", helm, "RH_Obsidian", "head", uv_scale=2)
    p.add("helm_frost", frost_layer(helm, 0.008, min_ny=0.6, cover=0.3, seed=9), "RH_Frost", "head", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    cheeks = []
    for s in (-1, 1):
        poly = np.array([(0.09, 1.37), (0.118, 1.40), (0.100, 1.445)])
        m = g.extrude_plane(np.array([(1.37, 0.015), (1.40, 0.095), (1.445, 0.05)]), 0.012, "YZ", bevel=0.003, bevel_segments=1)
        cheeks.append(m.translated(s * 0.105, 0, 0.012))
    p.add("cheek_flares", merge(cheeks), "RH_Obsidian", "head")
    face = g.superellipsoid((0.074, 0.048, 0.044), 0.45, 0.55, 5, 12).rotated(-6, 0, 0).translated(0, 1.425, 0.090)
    p.add("faceplate", face, "RH_Obsidian", "head")
    p.add("brow", g.superellipsoid((0.098, 0.013, 0.028), 0.4, 0.5, 3, 9).rotated(-10, 0, 0).translated(0, 1.470, 0.098), "RH_Obsidian", "head")
    p.add("nose_ridge", g.extrude(np.array([(-0.007, 1.38), (0.007, 1.38), (0.004, 1.455), (-0.004, 1.455)]), 0.012, 0.003, 1).translated(0, 0, 0.126), "RH_Obsidian", "head", lod1=None)
    # narrow cracked slit: a thin line of cold light recessed in the faceplate, two short hairline cracks (focal point 1)
    slit = g.extrude(np.array([(-0.040, -0.003), (0.0, -0.0045), (0.040, -0.003), (0.034, 0.0035), (0.0, 0.0045), (-0.034, 0.0035)]), 0.004, 0.0008, 1).translated(0, 1.436, 0.1282)
    p.add("visor_glow", slit, "RH_Glow", "head", bake=False, lod1="keep")
    cr = []
    for x, sgn in ((-0.022, 1), (0.026, -1)):
        pts = [(x, 1.436 + sgn * 0.004, 0.1285), (x + 0.006, 1.436 + sgn * 0.022, 0.1285), (x - 0.004, 1.436 + sgn * 0.040, 0.1285)]
        cr.append(g.tube(pts, 0.0024, sides=3, samples=1, cap=None, smooth=False))
    p.add("visor_cracks", merge(cr), "RH_Seam", "head", bake=False, lod1=None)
    fin = g.extrude_plane(np.array([(1.50, -0.05), (1.57, -0.015), (1.545, 0.04), (1.50, 0.07)]), 0.014, "YZ", bevel=0.004, bevel_segments=1)
    p.add("helm_crest", fin, "RH_Obsidian", "head", lod1=None)
    horns = [shard(0.10, 0.026, sides=6, flat=0.25, bend=0.15 * s, seed=3 + s).aimed((s * 1.0, 0.6, -0.2), (s * 0.095, 1.45, 0.0)) for s in (-1, 1)]
    p.add("helm_horns", merge(horns), "RH_Ice", "head")
    wires = []
    for k in range(4):
        a = -50 + 33 * k
        pts = []
        for t in np.linspace(0.12, 0.98, 8):
            ph = (a + 25 * (t - 0.5)) * 0.0
            yy = 1.405 + 0.115 * t
            rr = float(np.interp(yy, [p[1] for p in prof], [p[0] for p in prof])) * 1.0 + 0.006
            pts.append((rr * math.sin(math.radians(a)), yy, rr * math.cos(math.radians(a)) * 1.08 + 0.012))
        wires.append(g.tube(pts, 0.0036, sides=4, samples=1, cap=None, smooth=True))
    p.add("helm_wire", merge(wires), "RH_Silver", "head", lod1=None)


# ======================================================================================= prism ring (top bone)
def prism_ring(p: Piece):
    """Eight tall hex prisms hovering over the helm, gap 0.04, tips at 1.70: the Tyrant's crown."""
    pr, sub = [], []
    for k in range(8):
        a = math.radians(k * 45)
        h = 0.135 if k % 2 == 0 else 0.150
        pos = (0.115 * math.sin(a), 1.563, 0.115 * math.cos(a))
        d = unit((0.06 * math.sin(a), 1.0, 0.06 * math.cos(a)))
        s_ = shard(h, 0.027, sides=6, tip=0.30, flat=0.0, taper=0.9, jitter=0.0, seed=1, cap=True)
        pr.append(s_.aimed(d, pos))
        sub.append(((pos[0], 1.558, pos[2]), (0, -1, 0), 0.045 + 0.012 * (k % 2), 0.0095))
    p.add("prisms", merge(pr), "RH_Ice", "top")
    p.add("prism_subshards", spikes(sub, seed=17, flat=0.2, sides=4, tip=0.5), "RH_Ice", "top", lod1=None)
    p.add("prism_ring_glow", g.torus(0.115, 0.0042, 24, 4).translated(0, 1.566, 0), "RH_Seam", "top", bake=False, lod1="keep")
    p.add("prism_ring_band", g.torus(0.118, 0.0040, 24, 4).translated(0, 1.572, 0), "RH_Silver", "top", lod1=None, tint=lambda P: np.full(len(P), 0.55))
    # drifting shards orbiting the ring
    orb = [((0.17 * math.sin(math.radians(a)), 1.60 + 0.03 * (k % 3), 0.17 * math.cos(math.radians(a))), unit((0.2, 1, 0.1)), 0.05 + 0.02 * (k % 2), 0.010) for k, a in enumerate((20, 110, 200, 290))]
    p.add("ring_orbit_shards", spikes(orb, seed=19, flat=0.25, sides=5, tip=0.45), "RH_Ice", "top", lod1=None)


# ======================================================================================= clips
def make_clips() -> list[Clip]:
    idle = Clip("Idle", 4.0, loop=True)
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.4, (1.2, 0, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (1.4, (-1, 1.5, 0), "in_out_cubic"), (2.8, (0, -2, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "pos", [(0, (0, 0, 0)), (1.4, (0, 0.012, 0), "in_out_cubic"), (2.8, (0, -0.004, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.4, (0, 10, 0), "in_out_cubic"), (2.8, (0, 20, 0), "in_out_cubic"), (4.0, (0, 0, 0), "in_out_cubic")])

    mv = Clip("Move", 1.0, loop=True)
    mv.keys("body", "rot", [(0, (5, 0, 0)), (0.25, (5, 0, 3), "in_out_cubic"), (0.5, (5, 0, 0), "in_out_cubic"), (0.75, (5, 0, -3), "in_out_cubic"), (1.0, (5, 0, 0), "in_out_cubic")])
    mv.keys("body", "pos", [(0, (0, 0, 0)), (0.25, (0, 0.02, 0), "out_quad"), (0.5, (0, 0, 0), "in_quad"), (0.75, (0, 0.02, 0), "out_quad"), (1.0, (0, 0, 0), "in_quad")])
    mv.keys("head", "rot", [(0, (0, 0, 0)), (0.25, (0, 0, -2), "in_out_cubic"), (0.5, (0, 0, 0)), (1.0, (0, 0, 0))])
    mv.keys("top", "rot", [(0, (0, 0, 0)), (0.5, (-3, 15, 0), "in_out_cubic"), (1.0, (0, 0, 0), "in_out_cubic")])
    mv.keys("top", "pos", [(0, (0, 0.01, 0)), (0.5, (0, 0.0, 0), "in_out_cubic"), (1.0, (0, 0.01, 0), "in_out_cubic")])

    A = Clip("Attack", 2.4, fps=60)
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.55, (-105, 0, 0), "in_out_cubic"), (0.70, (-20, 0, 0), "in_cubic"), (1.07, (-78, 25, 0), "in_out_cubic"), (1.20, (-78, -30, 0), "in_cubic"), (1.40, (-78, -30, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.55, (-30, 0, 0), "in_out_cubic"), (0.70, (0, 0, 0), "in_cubic"), (1.07, (-30, 0, 0), "in_out_cubic"), (1.20, (-5, 0, 0), "in_cubic"), (1.40, (-5, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.55, (-8, 10, 0), "in_out_cubic"), (0.70, (22, 0, 0), "in_cubic"), (1.07, (0, 58, 0), "in_out_cubic"), (1.20, (0, -42, 0), "in_cubic"), (1.40, (0, -42, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.55, (-4, 0, 0), "in_out_cubic"), (0.70, (18, 0, 0), "in_cubic"), (1.07, (-4, 8, 0), "in_out_cubic"), (1.20, (0, -12, 0), "in_cubic"), (1.40, (0, -12, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.55, (0, 0.02, 0), "in_out_cubic"), (0.70, (0, 0, 0.16), "in_cubic"), (1.07, (0, 0, 0.0), "in_out_cubic"), (1.20, (0, 0, 0.24), "in_cubic"), (1.22, (0, -0.03, 0.24)), (1.40, (0, -0.03, 0.24)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.55, (-6, 0, 0), "in_out_cubic"), (0.70, (8, 0, 0), "in_cubic"), (1.07, (0, -10, 0), "in_out_cubic"), (1.20, (0, 6, 0), "in_cubic"), (1.40, (0, 6, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.55, (-10, 0, 0), "in_out_cubic"), (1.40, (-10, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "pos", [(0, (0, 0, 0)), (0.55, (0, 0.03, 0), "in_out_cubic"), (1.40, (0, 0.03, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (1.07, (0, -8, 0), "in_out_cubic"), (1.40, (0, -8, 0)), (2.4, (0, 20, 0), "in_out_cubic")])

    hit = Clip("HitReact", 0.5)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.10, (-8, 0, 0), "out_cubic"), (0.50, (-3, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.05), "out_cubic"), (0.50, (0, 0, -0.01), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-8, 0, 0), "out_cubic"), (0.50, (-3, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.10, (-13, 0, 4), "out_cubic"), (0.50, (-4, 0, 1), "in_out_cubic")])
    hit.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.10, (8, 0, 0), "out_cubic"), (0.50, (2, 0, 0), "in_out_cubic")])
    hit.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.10, (8, 0, 0), "out_cubic"), (0.50, (2, 0, 0), "in_out_cubic")])
    hit.keys("top", "pos", [(0, (0, 0, 0)), (0.10, (0, 0.02, 0), "out_cubic"), (0.50, (0, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (0, 18, 0), "out_cubic"), (0.50, (0, 0, 0), "in_out_cubic")])

    vic = Clip("Victory", 2.0)
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.7, (-150, 0, 0), "out_back"), (2.0, (-150, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.7, (-20, 0, 0), "out_cubic"), (2.0, (-20, 0, 0))])
    vic.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.7, (-20, 0, 0), "out_cubic"), (2.0, (-20, 0, 0))])
    vic.keys("spine", "rot", [(0, (0, 0, 0)), (0.7, (-8, 0, 0), "out_cubic"), (2.0, (-8, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.7, (-12, 0, 0), "out_cubic"), (2.0, (-12, 0, 0))])
    vic.keys("body", "pos", [(0, (0, 0, 0)), (0.7, (0, 0.02, 0), "out_cubic"), (2.0, (0, 0.02, 0))])
    vic.keys("top", "pos", [(0, (0, 0, 0)), (0.7, (0, 0.03, 0), "out_cubic"), (2.0, (0, 0.03, 0))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (0.7, (0, 60, 0), "out_cubic"), (2.0, (0, 120, 0))])
    T = Clip("Taunt", 1.6)           # the prism ring spins up, the right fist is raised in challenge
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.5, (0, 270, 0), "in_quad"), (1.1, (0, 720, 0), "in_cubic"), (1.6, (0, 720, 0))])
    T.keys("top", "pos", [(0, (0, 0, 0)), (0.6, (0, 0.05, 0), "out_cubic"), (1.2, (0, 0.04, 0), "in_out_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.55, (-150, 0, 8), "out_back"), (1.2, (-150, 0, 8)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.55, (-20, 0, 0), "out_cubic"), (1.2, (-20, 0, 0)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.55, (-14, 0, 0), "out_cubic"), (1.2, (-14, 0, 0)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("spine", "rot", [(0, (0, 0, 0)), (0.55, (-8, 0, 0), "out_cubic"), (1.2, (-8, 0, 0)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("head", "rot", [(0, (0, 0, 0)), (0.55, (-12, 0, 0), "out_cubic"), (1.2, (-12, 0, 0)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "pos", [(0, (0, 0, 0)), (0.55, (0, 0.02, 0), "out_cubic"), (1.2, (0, 0.02, 0)), (1.6, (0, 0, 0), "in_out_cubic")])
    S = Clip("Surrender", 2.4)       # kneels, head bowed; the prism ring sinks and dims, the fist opens (he is unarmed)
    S.keys("body", "pos", [(0, (0, 0, 0)), (0.20, (0, 0, 0), "in_out_cubic"), (0.95, (0, -0.25, 0.04), "in_out_cubic"), (2.4, (0, -0.25, 0.04))])
    S.keys("body", "rot", [(0, (0, 0, 0)), (0.95, (6, 0, 0), "in_out_cubic"), (2.4, (6, 0, 0))])
    S.keys("spine", "rot", [(0, (0, 0, 0)), (0.30, (-3, 0, 0), "in_out_cubic"), (1.00, (22, 0, 0), "in_out_cubic"), (2.4, (26, 0, 0), "in_out_cubic")])
    S.keys("head", "rot", [(0, (0, 0, 0)), (0.30, (-4, 0, 0), "in_out_cubic"), (1.05, (38, 0, 0), "in_out_cubic"), (2.4, (44, 0, 0), "in_out_cubic")])
    S.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.50, (-6, 0, 0), "in_out_cubic"), (1.20, (14, 0, 0), "in_out_cubic"), (2.4, (18, 0, 0), "in_out_cubic")])
    S.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.50, (0, 0, 0)), (1.20, (40, 0, 0), "in_out_cubic"), (2.4, (48, 0, 0), "in_out_cubic")])
    S.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.50, (-6, 0, 0)), (1.20, (14, 0, 0), "in_out_cubic"), (2.4, (18, 0, 0), "in_out_cubic")])
    S.keys("hand_L", "rot", [(0, (0, 0, 0)), (1.20, (40, 0, 0), "in_out_cubic"), (2.4, (48, 0, 0), "in_out_cubic")])
    S.keys("top", "pos", [(0, (0, 0, 0)), (0.5, (0, 0.04, 0), "out_cubic"), (1.6, (0, -0.13, 0.02), "in_out_cubic"), (2.4, (0, -0.15, 0.03))])
    S.keys("top", "scale", [(0, (1, 1, 1)), (0.5, (1.1, 1, 1.1), "out_cubic"), (1.6, (0.8, 0.7, 0.8), "in_out_cubic"), (2.4, (0.75, 0.65, 0.75))])
    S.keys("top", "rot", [(0, (0, 0, 0)), (1.0, (0, 40, 0), "in_out_cubic"), (2.4, (14, 60, 0), "out_cubic")])
    return [idle, mv, A, hit, vic, T, S]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "king", rig, make_clips(), impact_time=1.20, strike_range=0.60, attack_style="melee", seed=8)
    rc.pedestal_parts(p)
    lower_body(p)
    torso(p)
    cape(p)
    pauldrons(p)
    arms(p)
    head(p)
    prism_ring(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
