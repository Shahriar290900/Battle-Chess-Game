"""rime_bishop - Rime Frost Chanter: a gaunt drowned caster in layered frozen robes, a frost-white beard, a crooked
obsidian staff with a lantern of trapped blue light, five ice runes orbiting the lantern.  docs/art/rime_bishop.md."""
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

ASSET_ID = "rime_bishop"
LANT = np.array([-0.15, 1.22, 0.19])          # lantern centre = rune orbit centre (the `top` bone)
GRIP = np.array([-0.19, 0.88, 0.12])


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.58, 0))
    r.add("spine", "body", (0, 0.70, 0))
    r.add("head", "spine", (0, 0.98, 0.02))
    r.add("top", "spine", tuple(LANT))
    r.add("arm_L", "spine", (0.13, 0.96, 0))
    r.add("hand_L", "arm_L", (0.16, 0.82, 0.07))
    r.add("arm_R", "spine", (-0.13, 0.96, 0))
    r.add("hand_R", "arm_R", (-0.17, 0.82, 0.07))
    r.add("weapon", "hand_R", (-0.19, 0.80, 0.12))        # the lantern staff (centre of mass): lets Surrender drop it
    r.socket("socket_weapon_R", "hand_R", tuple(GRIP))
    r.socket("socket_cast", "top", tuple(LANT))
    r.socket("socket_impact", "body", (0, 0.70, 1.45))
    r.socket("socket_head", "head", (0, 1.24, 0.02))
    return r


# ======================================================================================= robes
def robe(p: Piece):
    K = 28
    ys = [0.225, 0.34, 0.40, 0.47, 0.55, 0.62, 0.68, 0.705]
    rad = [0.232, 0.232, 0.214, 0.192, 0.164, 0.138, 0.116, 0.104]
    rng = np.random.default_rng(3)
    th = np.arange(K) * TAU / K
    tooth = np.where(np.arange(K) % 2 == 0, 0.0, 0.035 + 0.055 * rng.random(K))
    tooth[::4] *= 0.5
    rings = []
    for i, (y, r) in enumerate(zip(ys, rad)):
        fold = 1 + (0.05 + 0.03 * (1 - i / 7)) * np.cos(7 * th + 0.3 * i) * smoothstep(0.7, 0.2, y)
        yy = np.full(K, y) + (tooth if i == 0 else 0.0)
        rings.append(np.stack([r * fold * np.sin(th), yy, r * fold * np.cos(th)], 1))
    outer = g.loft(np.stack(rings), closed=True, crease=40.0, cap_end=True)
    fade = lambda P: 0.55 + 0.45 * smoothstep(0.2, 0.6, P[:, 1])
    p.add("robe_outer", outer, "RH_Cloth", "body", tint=fade)
    under = g.lathe([(0.205, 0.245), (0.200, 0.32), (0.170, 0.46), (0.135, 0.60), (0.0, 0.62)], 12, crease=35).rotated(0, 12, 0)
    p.add("robe_under", under, "RH_Armour", "body", uv_scale=2)
    wrap = rc.helix(0.146, 0.64, 0.76, 3.0, r=0.012, sides=5, per_turn=11, R1=0.130)
    p.add("waist_wrap", wrap, "RH_Cloth", "body", uv_scale=2)
    # frost build-up along the hem: alternating ice and frost shards
    hem = []
    hem_f = []
    for k in range(18):
        a = k * TAU / 18 + 0.1
        r = 0.236
        tip = (r * math.sin(a), 0.232 + (0.0 if k % 2 else 0.01), r * math.cos(a))
        d = (math.sin(a) * 0.9, 0.5, math.cos(a) * 0.9)
        (hem if k % 3 else hem_f).append((tip, d, 0.03 + 0.04 * rng.random(), 0.0065 + 0.0045 * rng.random()))
    p.add("hem_ice", spikes(hem, seed=11, flat=0.25, sides=4, tip=0.5), "RH_Ice", "body")
    p.add("hem_frost", spikes(hem_f, seed=12, flat=0.2, sides=4, tip=0.5), "RH_Frost", "body", tint=lambda P: np.full(len(P), 0.6))
    # barely visible boots
    for s in (-1, 1):
        b = g.superellipsoid((0.036, 0.022, 0.066), 0.5, 0.6, 3, 9).translated(s * 0.07, 0.246, 0.20)
        p.add(f"boot_{'L' if s > 0 else 'R'}", b, "RH_Obsidian", "body")
    # frayed rope-cloth belt + hanging chain of ice beads
    belt = rc.helix(0.139, 0.745, 0.765, 1.0, r=0.008, sides=4, per_turn=14)
    p.add("belt_cord", belt, "RH_Silver", "body", lod1=None)
    cm = [rc.zigzag((0.0, 0.76, 0.14), (0.05, 0.58, 0.19), 5, 0.006, r=0.0035, side=(1, 0, 0))]
    p.add("belt_chain", merge(cm), "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.45))
    p.add("belt_shards", spikes([((0.05, 0.585, 0.19), (0.1, -1, 0.1), 0.06, 0.010), ((0.02, 0.62, 0.17), (0.0, -1, 0.15), 0.045, 0.008)], seed=14, flat=0.25, sides=4, tip=0.5), "RH_Ice", "body", lod1=None)


def torso(p: Piece):
    path = [(0, 0.70, -0.01), (0, 0.80, 0.0), (0, 0.90, 0.015)]
    t = g.tube(path, [0.100, 0.104, 0.112], sides=10, samples=3, cap=None, ellipse=(0.76, 1.0), up=(0, 0, 1))
    p.add("chest_robe", t.noised(0.003, 14, 2, seed=2), "RH_Cloth", "spine")
    yoke = g.superellipsoid((0.150, 0.040, 0.085), 0.55, 0.7, 5, 12).translated(0, 0.915, 0.012)
    p.add("shoulder_yoke", yoke, "RH_Cloth", "spine")
    # front tabard: a long armoured strip down the robe, jagged hem, silver edge trim
    rr = lambda y: float(np.interp(y, [0.225, 0.34, 0.40, 0.47, 0.55, 0.62, 0.68, 0.705], [0.232, 0.232, 0.214, 0.192, 0.164, 0.138, 0.116, 0.104]))
    tab = g.cloth_panel(0.075, 0.52, cols=6, rows=9, fold_amp=0.004, folds=2, flare=0.55, curve=0, seed=2, thickness=0.006)
    tab = tab.translated(0, 0.74, 0)

    def drape(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        r = np.array([rr(max(v, 0.225)) for v in y]) + 0.012
        zz = np.sqrt(np.clip(1 - (x / (r * 1.02)) ** 2, 0.05, 1)) * r
        yy = y + np.where(y < 0.30, -0.035 * np.clip(np.sin(x * 120), 0, 1), 0)
        return np.column_stack([x, np.maximum(yy, 0.228), zz + z * 0.5])
    tab = g.warp(tab, drape, 50)
    p.add("tabard", tab, "RH_Armour", "body", uv_scale=2)
    for sx in (-1, 1):
        edge = [(sx * 0.0375 * (1 + 0.55 * f), 0.74 - 0.52 * f, rr(0.74 - 0.52 * f) * math.sqrt(1 - (0.0375 * (1 + 0.55 * f) / (rr(0.74 - 0.52 * f) * 1.02)) ** 2) + 0.018) for f in np.linspace(0.0, 0.93, 9)]
        p.add(f"tabard_trim_{'L' if sx > 0 else 'R'}", g.tube(edge, 0.0048, sides=4, samples=1, cap="round", cap_steps=1), "RH_Silver", "body", lod1=None)
    zf = lambda y: np.interp(y, [0.70, 0.84, 0.96], [0.075, 0.09, 0.105])
    # left-only chest plate shards (asymmetric)
    tris = [[(0.02, 0.90), (0.12, 0.92), (0.07, 0.80)], [(0.02, 0.84), (0.10, 0.82), (0.05, 0.72)], [(0.02, 0.78), (0.09, 0.74), (0.05, 0.66)]]
    pl = []
    for i, t3 in enumerate(tris):
        m = g.extrude(np.array(t3), 0.012, 0.0035, 1)
        pl.append(m.rotated(-4 + 3 * i, 0, 0).translated(0, 0, float(zf(np.mean([q[1] for q in t3]))) + 0.004 + 0.003 * i))
    p.add("chest_shards", merge(pl), "RH_Obsidian", "spine")
    # silver lacing zig-zag across the robe front: 8 loops
    lace = rc.zigzag((0.0, 0.64, 0.074), (0.0, 0.93, 0.108), 16, 0.070, r=0.0038, side=(1, 0, 0))
    p.add("lacing", lace, "RH_Silver", "spine", lod1=None)
    # back frost ridge
    rid = cluster((0.0, 0.92, -0.085), (0.0, 0.6, -1.0), 3, (0.06, 0.10), (0.012, 0.018), spread=0.05, tilt=20, seed=4, flat=0.25)
    p.add("back_ridge", rid, "RH_Ice", "spine")
    # gorget: a fan of seven obsidian plates rising behind the neck (high collar)
    pls = []
    for k in range(7):
        a = 180 + (k - 3) * 28
        h = 0.12 - 0.012 * abs(k - 3) + (0.02 if k % 2 else 0.0)
        poly = np.array([(-0.014, 0), (0.014, 0), (0.019, h * 0.75), (0.0, h), (-0.019, h * 0.78)])
        m = g.extrude(poly, 0.008, 0.002, 1).rotated(-14 - 5 * (k % 2), 0, 0).translated(0, 0.955, 0.075).rotated(0, a, 0)
        pls.append(m.translated(0.0, 0.0, 0.0))
    p.add("gorget", merge(pls), "RH_Obsidian", "spine")
    p.add("gorget_wire", g.torus(0.082, 0.0045, 16, 4).translated(0, 0.97, -0.002), "RH_Silver", "spine", lod1=None)
    # frost drips from robe/sleeve edges
    drips = spikes([((0.07, 0.72, 0.10), (0, -1, 0.1), 0.05, 0.009), ((-0.06, 0.70, 0.10), (0, -1, 0.1), 0.04, 0.008), ((0.10, 0.74, 0.075), (0.2, -1, 0), 0.06, 0.009)],
                   seed=22, flat=0.25, sides=4, tip=0.5)
    p.add("robe_drips", drips, "RH_Frost", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.6))


def mantle(p: Piece):
    # layered shoulder mantle: two jagged tiers of tattered cloth over the chest and back, frost on top
    for tier, (y0, y1, r0, r1, seed) in enumerate(((0.99, 0.80, 0.105, 0.205, 3), (0.94, 0.72, 0.100, 0.185, 4))):
        K = 24
        th = np.arange(K) * TAU / K
        rng = np.random.default_rng(seed)
        rows = []
        for i, f in enumerate((0.0, 0.35, 0.7, 1.0)):
            r = r0 + (r1 - r0) * f ** 0.8
            y = y0 + (y1 - y0) * f
            yy = np.full(K, y)
            if i == 3:
                yy = yy - (np.where(np.arange(K) % 2 == 0, 0.0, 0.03 + 0.05 * rng.random(K)))
            fold = 1 + 0.04 * np.cos(6 * th + tier)
            rows.append(np.stack([r * fold * np.sin(th) * 1.0, yy, r * fold * np.cos(th) * 0.9 - 0.005], 1))
        m = g.loft(np.stack(rows), closed=True, crease=45.0)
        p.add(f"mantle_{tier}", m, "RH_Cloth", "spine", uv_scale=2, tint=(lambda P: 0.55 + 0.45 * smoothstep(0.7, 0.95, P[:, 1])))
        if tier == 0:
            p.add("mantle_frost", frost_layer(m, 0.008, min_ny=0.55, cover=0.35, seed=3), "RH_Frost", "spine", lod1=None, tint=lambda P: np.full(len(P), 0.5))
            p.add("mantle_ice", spikes([((0.16 * math.sin(a), 0.78 + 0.02, 0.15 * math.cos(a)), (math.sin(a), -0.7, math.cos(a)), 0.05 + 0.025 * (k % 2), 0.007) for k, a in enumerate(np.linspace(0, TAU, 12, endpoint=False))], seed=5, flat=0.25, sides=4, tip=0.5), "RH_Ice", "spine", lod1=None)
    # tattered back cloak hanging from the shoulders to the hem
    R, K = 9, 9
    rows = []
    for r in range(R):
        v = r / (R - 1)
        row = []
        for k in range(K):
            u = k / (K - 1)
            y = 0.97 - 0.70 * v - ((0.06 if r == R - 1 else 0.015) * (k % 2) if r >= R - 2 else 0)
            xw = 0.10 + 0.11 * v ** 0.9
            z = -0.115 - 0.08 * v ** 1.2 + 0.008 * math.sin(u * TAU * 2.5)
            row.append((-xw + 2 * xw * u, y, z))
        rows.append(row)
    p.add("back_cloak", g.loft(np.array(rows)[::-1], closed=False, crease=50, v_tile=0.25, u_tile=0.25), "RH_Cloth", "spine", bone2="body", blend=(0.85, 0.55), uv_scale=2)


def embroidery(p: Piece):
    rr = lambda y: float(np.interp(y, [0.225, 0.34, 0.40, 0.47, 0.55, 0.62, 0.68, 0.705], [0.232, 0.232, 0.214, 0.192, 0.164, 0.138, 0.116, 0.104]))
    gl = []
    for k, y in enumerate((0.64, 0.545, 0.45, 0.36)):
        z = rr(y) + 0.022
        gm = merge(glyph_bars(k + 1, 0.0050)).scaled(1.5).translated(0, y, z).rotated(-14, 0, 0, pivot=(0, y, z))
        gl.append(gm)
    p.add("tabard_glyphs", merge(gl), "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    # snow-crystal brooch pinning the yoke
    bars = [g.extrude(g.rect_poly(0.040, 0.0075), 0.006, 0.0012, 1).rotated(0, 0, a) for a in (0, 60, 120)]
    br = merge(bars).translated(0, 0.885, 0.122)
    p.add("brooch", br, "RH_Silver", "spine")
    # tattered ribbons hanging from the belt, frosted tips
    rib = []
    for k, (x, ln, ang) in enumerate(((0.075, 0.20, 12), (0.105, 0.28, 8), (-0.085, 0.24, -10), (-0.12, 0.17, -14))):
        poly = np.array([(-0.014, 0), (0.014, 0), (0.011, -ln * 0.8), (0.0, -ln), (-0.010, -ln * 0.75)])
        rib.append(g.extrude(poly, 0.006, 0.0012, 1).rotated(-6, 0, ang).translated(x, 0.74, 0.115 + 0.02 * (k % 2)))
    p.add("ribbons", merge(rib), "RH_Cloth", "body", uv_scale=2)


# ======================================================================================= arms
def arms(p: Piece):
    # left arm: open hand at the hip, shoulder plate (obsidian + frost)
    upL = [(0.13, 0.96, 0.0), (0.150, 0.89, 0.04), (0.16, 0.82, 0.07)]
    foreL = [(0.16, 0.82, 0.07), (0.17, 0.77, 0.10), (0.18, 0.735, 0.125)]
    p.add("arm_L", g.tube(upL, [0.032, 0.034, 0.036], sides=7, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Cloth", "arm_L", uv_scale=2)
    p.add("forearm_L", g.tube(foreL, [0.040, 0.046, 0.052], sides=7, samples=2, cap=None, up=(0, 0, 1)), "RH_Cloth", "hand_L", uv_scale=2)
    sh = g.superellipsoid((0.058, 0.026, 0.056), 0.5, 0.65, 4, 10).noised(0.0016, 36, 2, seed=2).rotated(0, 0, -14).translated(0.152, 0.985, 0.0)
    sh2 = g.superellipsoid((0.050, 0.020, 0.050), 0.5, 0.65, 4, 9).rotated(0, 0, -22).translated(0.162, 0.958, 0.0)
    p.add("shoulder_L", merge([sh, sh2]), "RH_Obsidian", "arm_L")
    p.add("shoulder_L_frost", frost_layer(sh, 0.007, min_ny=0.4, cover=0.3, seed=2), "RH_Frost", "arm_L", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    p.add("cuff_L_lames", rc.limb_lames(foreL, [0.040, 0.046, 0.052], [0.55, 0.85], h=0.030, sweep=250, grow=0.006, seg=7), "RH_Armour", "hand_L")
    p.add("cuff_L_ice", cluster((0.18, 0.735, 0.125), (0.1, -1.0, 0.2), 4, (0.04, 0.07), (0.007, 0.011), spread=0.04, tilt=30, seed=9, flat=0.3, sides=4), "RH_Ice", "hand_L")
    p.add("hand_L", rc.claw_hand(+1, np.array([0.185, 0.705, 0.135]), (0.15, -0.5, 1.0), 0.6, 1.0, 1.7), "RH_Bone", "hand_L", uv_scale=2)
    # right arm: bare cloth drape (no shoulder plate), holds the staff
    upR = [(-0.13, 0.96, 0.0), (-0.150, 0.89, 0.04), (-0.17, 0.82, 0.07)]
    foreR = [(-0.17, 0.82, 0.07), (-0.178, 0.85, 0.10), (-0.19, 0.88, 0.12)]
    p.add("arm_R", g.tube(upR, [0.032, 0.034, 0.036], sides=7, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Cloth", "arm_R", uv_scale=2)
    p.add("forearm_R", g.tube(foreR, [0.040, 0.034, 0.030], sides=7, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Cloth", "hand_R", uv_scale=2)
    drape = []
    for k, (dx, ln) in enumerate(((-0.145, 0.16), (-0.12, 0.20), (-0.165, 0.13))):
        poly = np.array([(-0.016, 0), (0.016, 0), (0.012, -ln * 0.8), (0.0, -ln), (-0.012, -ln * 0.7)])
        drape.append(g.extrude(poly, 0.007, 0.0015, 1).rotated(0, 90, 0).rotated(0, 0, 8 * (k - 1)).translated(dx - 0.03, 0.97, 0.01 - 0.03 * (k - 1)))
    p.add("drape_R", merge(drape), "RH_Cloth", "arm_R", uv_scale=2)
    p.add("hand_R", rc.claw_hand(-1, np.array([-0.19, 0.885, 0.125]), (0.0, 0.2, 1.0), 0.2, 0.95, 1.0), "RH_Bone", "hand_R", uv_scale=2)
    p.add("cuff_R_icicles", cluster((-0.18, 0.84, 0.10), (-0.4, -1.0, 0.1), 3, (0.03, 0.05), (0.006, 0.009), spread=0.03, tilt=25, seed=19, flat=0.3, sides=4), "RH_Ice", "hand_R", lod1=None)
    p.add("sleeve_R_wire", merge([rc.helix(0.034, 0.835, 0.865, 1.5, r=0.0034, sides=3, per_turn=7, ax=-0.176, az=0.095)]), "RH_Silver", "hand_R", lod1=None)


# ======================================================================================= head
def head(p: Piece):
    neck = g.tube([(0, 0.93, 0.0), (0, 0.99, 0.02)], [0.036, 0.030], sides=7, samples=1, cap=None, smooth=False)
    p.add("neck", neck, "RH_Bone", "head", uv_scale=2)
    cx, cy, cz = 0.0, 1.05, 0.015
    skull = g.superellipsoid((0.047, 0.070, 0.052), 0.8, 0.85, 6, 12).noised(0.003, 28, 2, seed=3)
    cheek = [g.superellipsoid((0.014, 0.014, 0.014), 0.6, 0.6, 3, 6).translated(s * 0.030, -0.012, 0.040) for s in (-1, 1)]
    brow = g.superellipsoid((0.044, 0.010, 0.026), 0.6, 0.6, 3, 8).translated(0, 0.018, 0.036)
    nose = g.superellipsoid((0.008, 0.014, 0.012), 0.6, 0.6, 3, 6).translated(0, -0.005, 0.052)
    p.add("head", merge([skull, brow, nose] + cheek).rotated(0, 6, 0).translated(cx, cy, cz), "RH_Bone", "head", uv_scale=2)
    sock = [g.superellipsoid((0.0175, 0.0125, 0.010), 0.7, 0.7, 3, 8).rotated(0, s * 14, s * 8).translated(s * 0.0225, 1.066, 0.0585) for s in (-1, 1)]
    p.add("eye_sockets", merge(sock), "RH_Obsidian", "head", lod1=None)
    cb = [g.superellipsoid((0.016, 0.009, 0.016), 0.6, 0.6, 3, 7).rotated(0, s * 20, 0).translated(s * 0.036, 1.036, 0.040) for s in (-1, 1)]
    ear = [g.superellipsoid((0.006, 0.016, 0.011), 0.6, 0.6, 3, 7).translated(s * 0.050, 1.045, 0.005) for s in (-1, 1)]
    p.add("cheekbones", merge(cb + ear), "RH_Bone", "head", lod1=None, uv_scale=2)
    eyes = [g.extrude(np.array([(-0.008, -0.003), (0.008, 0.0), (0.007, 0.0045), (-0.008, 0.0015)]) * [s, 1], 0.005, 0.0012, 1).translated(s * 0.0225, 1.068, 0.0625) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "RH_Glow", "head", bake=False, lod1="keep")
    # frozen beard: flowing locks of frost with ice tips, plus a mass at the chin
    locks = []
    ice_t = []
    rng = np.random.default_rng(8)
    for k in range(9):
        x = (k - 4) * 0.0105
        mid = 1 - abs(k - 4) / 4
        L = 0.10 + 0.07 * rng.random() + 0.07 * mid
        pts = [(x * 0.7, 1.005, 0.050 + 0.012 * mid), (x * 1.2, 0.97 - L * 0.4, 0.068 + 0.01 * mid), (x * 1.5 + 0.01 * (k % 3 - 1), 1.00 - L, 0.078)]
        locks.append(g.tube(pts, [0.0105, 0.0095, 0.0028], sides=5, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)))
        ice_t.append(((x * 1.5, 1.00 - L + 0.006, 0.078), (0.08 * (k - 4), -1, 0.1), 0.03 + 0.045 * rng.random(), 0.0070))
    p.add("beard", merge(locks), "RH_Frost", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.5))
    p.add("beard_ice", spikes(ice_t, seed=3, flat=0.25, sides=4, tip=0.5), "RH_Ice", "head")
    # moustache + brow shadow plates
    for sx in (-1, 1):
        mo = g.tube([(0.0, 1.012, 0.058), (sx * 0.022, 1.004, 0.062), (sx * 0.045, 0.985, 0.052)], [0.008, 0.008, 0.002], sides=5, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"moustache_{'L' if sx > 0 else 'R'}", mo, "RH_Frost", "head", uv_scale=2, lod1=None, tint=lambda P: np.full(len(P), 0.5))
    # ice crown (uneven, one broken) + silver diadem + cowl scrap
    cr = []
    for k in range(5):
        a = math.radians(k * 72 + 20)
        ln = (0.075, 0.10, 0.06, 0.09, 0.035)[k]
        cr.append(((0.052 * math.sin(a), 1.115, 0.052 * math.cos(a) + 0.015), (0.45 * math.sin(a), 1.0, 0.45 * math.cos(a)), ln, 0.0095))
    p.add("ice_crown", spikes(cr, seed=5, flat=0.25, sides=5, tip=0.45), "RH_Ice", "head")
    p.add("diadem", g.torus(0.056, 0.0050, 18, 4).translated(0, 1.10, 0.015), "RH_Silver", "head")
    p.add("diadem_gem", g.superellipsoid((0.008, 0.011, 0.006), 0.6, 0.6, 3, 6).translated(0, 1.10, 0.072), "RH_Ice", "head", lod1=None)
    cowl = np.array([(0.0, 1.12), (0.07, 1.08), (0.09, 0.92), (0.0, 0.86), (-0.08, 0.94), (-0.06, 1.08)])
    cm = g.extrude(cowl, 0.006, 0.0015, 1).translated(0, 0, -0.063)
    p.add("cowl_scrap", cm, "RH_Cloth", "head", uv_scale=2)


# ======================================================================================= staff + lantern
STAFF = [(-0.19, 0.22, 0.12), (-0.19, 0.60, 0.12), (-0.20, 0.95, 0.11), (-0.21, 1.15, 0.12), (-0.20, 1.30, 0.14), (-0.17, 1.37, 0.17), (-0.13, 1.36, 0.19)]


def staff(p: Piece):
    shaft = g.tube(STAFF, [0.020, 0.016, 0.015, 0.016, 0.014, 0.011, 0.008], sides=7, samples=3, cap="round", cap_steps=1, up=(1, 0, 0))
    shaft = shaft.noised(0.004, 12, 2, seed=6)
    p.add("staff_shaft", shaft, "RH_Obsidian", "weapon", uv_scale=2)
    bands = []
    for y, r in ((0.50, 0.021), (0.80, 0.0185), (1.05, 0.0175), (1.28, 0.0170)):
        x = float(np.interp(y, [p[1] for p in STAFF], [p[0] for p in STAFF]))
        z = float(np.interp(y, [p[1] for p in STAFF], [p[2] for p in STAFF]))
        bands.append(g.lathe([(r + 0.002, y - 0.010), (r + 0.006, y - 0.006), (r + 0.006, y + 0.006), (r + 0.002, y + 0.010)], 10, crease=35).translated(x, 0, z))
    p.add("staff_bands", merge(bands), "RH_Silver", "weapon")
    p.add("staff_foot", spikes([((-0.19, 0.235, 0.12), (0, -1, 0), 0.06, 0.014)], seed=2, flat=0.1, sides=5, tip=0.5), "RH_Ice", "weapon")
    p.add("staff_ice", cluster((-0.208, 0.98, 0.115), (-0.5, 0.8, 0.2), 4, (0.05, 0.11), (0.008, 0.014), spread=0.02, tilt=30, seed=12, flat=0.3), "RH_Ice", "weapon")
    p.add("staff_ice_low", cluster((-0.19, 0.42, 0.135), (0.0, 0.6, 1.0), 3, (0.04, 0.08), (0.008, 0.013), spread=0.02, tilt=30, seed=15, flat=0.3), "RH_Ice", "weapon", lod1=None)
    # lantern (hangs from the hook): chain, cap, cage bars, glass, light core, base
    hook = np.array([-0.13, 1.355, 0.19])
    chain = rc.zigzag(hook, (LANT[0], 1.305, LANT[2]), 5, 0.004, r=0.0034, side=(1, 0, 0), sides=3)
    p.add("lantern_chain", chain, "RH_Silver", "weapon", lod1=None)
    cap = g.lathe([(0.0, 1.30), (0.030, 1.285), (0.045, 1.272), (0.0, 1.272)], 8, crease=35).translated(LANT[0], 0, LANT[2])
    base = g.lathe([(0.0, 1.14), (0.035, 1.15), (0.02, 1.165), (0.0, 1.165)], 8, crease=35).translated(LANT[0], 0, LANT[2])
    p.add("lantern_cap_base", merge([cap, base]), "RH_Silver", "weapon")
    bars = []
    for k in range(4):
        a = math.radians(45 + k * 90)
        bars.append(g.tube([(LANT[0] + 0.040 * math.sin(a), 1.16, LANT[2] + 0.040 * math.cos(a)), (LANT[0] + 0.020 * math.sin(a), 1.285, LANT[2] + 0.020 * math.cos(a))],
                           0.0055, sides=4, samples=1, cap="round", cap_steps=1, smooth=False))
    rings_ = [g.torus(0.040, 0.0042, 10, 3).translated(LANT[0], 1.162, LANT[2]), g.torus(0.030, 0.0042, 10, 3).translated(LANT[0], 1.275, LANT[2])]
    p.add("lantern_cage", merge(bars + rings_), "RH_Silver", "weapon")
    glass = g.superellipsoid((0.036, 0.062, 0.036), 0.6, 0.7, 4, 10).translated(*LANT)
    p.add("lantern_glass", glass, "RH_Ice", "weapon", occluder=False, lod1="keep")
    core = g.superellipsoid((0.020, 0.035, 0.020), 0.9, 0.9, 4, 9).translated(*LANT)
    p.add("lantern_core", core, "RH_Glow", "weapon", bake=False, lod1="keep")


# ======================================================================================= orbit runes (top bone)
def glyph_bars(kind, w=0.0042):
    def bar(x0, y0, x1, y1):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) - 90
        return g.extrude(g.rect_poly(w, L), 0.003, 0.0006, 1).rotated(0, 0, ang).translated((x0 + x1) / 2, (y0 + y1) / 2, 0)
    if kind == 0:
        return [bar(-0.006, -0.022, -0.006, 0.022), bar(-0.006, 0.022, 0.012, 0.006), bar(-0.006, 0.004, 0.012, -0.012)]
    if kind == 1:
        return [bar(-0.010, 0.022, 0.006, 0.004), bar(0.006, 0.004, -0.008, -0.004), bar(-0.008, -0.004, 0.010, -0.022)]
    if kind == 2:
        return [bar(0.0, -0.022, 0.0, 0.022), bar(-0.012, 0.010, 0.012, 0.010), bar(-0.010, -0.008, 0.010, -0.008)]
    if kind == 3:
        return [bar(-0.010, -0.022, 0.0, 0.022), bar(0.0, 0.022, 0.010, -0.022), bar(-0.006, 0.0, 0.006, 0.0)]
    return [bar(-0.010, -0.020, 0.010, 0.020), bar(0.010, -0.020, -0.010, 0.020)]


def runes(p: Piece):
    tab_poly = np.array([(-0.025, -0.035), (0.025, -0.035), (0.030, 0.0), (0.025, 0.035), (-0.025, 0.035), (-0.030, 0.0)])
    tabs, gly = [], []
    ys = (1.20, 1.30, 1.24, 1.34, 1.28)
    for k in range(5):
        a = k * 72.0
        tilt = 15 + 4 * k
        t = g.extrude(tab_poly, 0.014, 0.004, 1).rotated(tilt, 0, 4 * (k - 2))
        gl = merge(glyph_bars(k)).translated(0, 0, 0.0085).rotated(tilt, 0, 4 * (k - 2))
        pos = LANT + np.array([0.14 * math.sin(math.radians(a)), ys[k] - LANT[1] + 0.02, 0.14 * math.cos(math.radians(a))])
        tabs.append(t.rotated(0, a, 0).translated(*pos))
        gly.append(gl.rotated(0, a, 0).translated(*pos))
    p.add("rune_tablets", merge(tabs), "RH_Ice", "top")
    p.add("rune_glyphs", merge(gly), "RH_Seam", "top", bake=False, lod1=None)
    motes = []
    for k in range(3):
        a = math.radians(36 + k * 120)
        motes.append(g.superellipsoid((0.008, 0.012, 0.008), 0.6, 0.6, 3, 6).translated(LANT[0] + 0.13 * math.sin(a), LANT[1] + 0.02 + 0.04 * k, LANT[2] + 0.13 * math.cos(a)))
    p.add("rune_motes", merge(motes), "RH_Ice", "top", lod1=None)


# ======================================================================================= clips
def make_clips(rig) -> list[Clip]:
    idle = Clip("Idle", 3.4, loop=True)
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.0, (1.4, 0, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (1.0, (-1.5, 2, 0), "in_out_cubic"), (2.2, (0, 0, -2), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("hand_R", "rot", [(0, (0, 0, 0)), (2.2, (0, 0, 1.2), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.7, (0, 180, 0)), (3.4, (0, 360, 0))])

    mv = Clip("Move", 1.0, loop=True)
    mv.keys("body", "rot", [(0, (5, 0, 0)), (0.25, (5, 0, -2), "in_out_cubic"), (0.5, (7, 0, 0), "in_out_cubic"), (0.75, (5, 0, 2), "in_out_cubic"), (1.0, (5, 0, 0), "in_out_cubic")])
    mv.keys("body", "pos", [(0, (0, 0, 0)), (0.25, (0, 0.02, 0), "out_quad"), (0.5, (0, 0, 0), "in_quad"), (0.75, (0, 0.02, 0), "out_quad"), (1.0, (0, 0, 0), "in_quad")])
    mv.keys("head", "rot", [(0, (0, 0, 0)), (0.5, (4, 0, 0), "in_out_cubic"), (1.0, (0, 0, 0), "in_out_cubic")])
    mv.keys("top", "rot", [(0, (0, 0, 0)), (0.5, (0, 180, 0)), (1.0, (0, 360, 0))])

    A = Clip("Attack", 2.4, fps=60)
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.30, (-20, 0, 0), "in_out_cubic"), (0.95, (-20, 0, 0), "in_out_cubic"), (1.10, (-70, 0, 0), "in_cubic"), (1.30, (-70, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.95, (-10, 0, 0), "in_out_cubic"), (1.10, (-10, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.30, (-5, 0, 0), "in_out_cubic"), (0.95, (-8, 0, 0), "in_out_cubic"), (1.10, (10, 0, 0), "in_cubic"), (1.30, (10, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.30, (-6, 0, 0), "in_out_cubic"), (0.95, (-8, 0, 0), "in_out_cubic"), (1.10, (4, 0, 0), "in_cubic"), (1.30, (4, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0), "in_out_cubic"), (0.95, (-85, 0, 0), "in_out_cubic"), (1.30, (-85, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_L", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.95, (-15, 0, 0), "in_out_cubic"), (1.30, (-15, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.95, (0, 0, 0), "in_out_cubic"), (1.10, (0, 0, 0.10), "in_cubic"), (1.30, (0, 0, 0.10)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.95, (0, 900, 0), "in_quad"), (1.10, (0, 1080, 0), "out_quad"), (1.30, (0, 1080, 0)), (2.4, (0, 1440, 0), "in_out_cubic")])
    A.keys("top", "scale", [(0, (1, 1, 1)), (0.30, (1, 1, 1)), (0.95, (1.15, 1, 1.15), "in_out_cubic"), (1.10, (0.3, 1, 0.3), "in_expo"), (1.30, (0.6, 1, 0.6), "out_quad"), (2.0, (1, 1, 1), "in_out_cubic")])

    hit = Clip("HitReact", 0.45)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.10, (-12, 0, 0), "out_cubic"), (0.45, (-5, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.07), "out_cubic"), (0.45, (0, 0, -0.02), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-10, 0, 0), "out_cubic"), (0.45, (-4, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.10, (-16, 0, 0), "out_cubic"), (0.45, (-6, 0, 0), "in_out_cubic")])
    hit.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.10, (10, 0, 0), "out_cubic"), (0.45, (3, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (0, 40, 0), "out_cubic"), (0.45, (0, 20, 0), "in_out_cubic")])

    vic = Clip("Victory", 1.8)
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.6, (-45, 0, 0), "out_back"), (1.8, (-45, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.6, (-15, 0, 0), "out_cubic"), (1.8, (-15, 0, 0))])
    vic.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.6, (-50, 0, 0), "out_cubic"), (1.8, (-50, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.6, (-12, 0, 0), "out_cubic"), (1.8, (-12, 0, 0))])
    vic.keys("spine", "rot", [(0, (0, 0, 0)), (0.6, (-6, 0, 0), "out_cubic"), (1.8, (-6, 0, 0))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (1.0, (0, 720, 0), "in_out_cubic"), (1.8, (0, 720, 0))])
    vic.keys("top", "scale", [(0, (1, 1, 1)), (1.0, (1.2, 1, 1.2), "in_out_cubic"), (1.8, (1, 1, 1), "in_out_cubic")])
    T = Clip("Taunt", 1.5)           # runes spin up fast around the lantern, then a pointing gesture with the free hand
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.35, (0, 360, 0), "in_quad"), (0.80, (0, 1440, 0), "in_cubic"), (1.1, (0, 1500, 0), "out_cubic"), (1.5, (0, 1440, 0))])
    T.keys("top", "scale", [(0, (1, 1, 1)), (0.8, (1.25, 1, 1.25), "in_out_cubic"), (1.1, (1.0, 1, 1.0), "out_quad"), (1.5, (1, 1, 1))])
    T.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.7, (0, 0, 0)), (0.95, (-88, 0, -12), "out_back"), (1.25, (-88, 0, -12)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("hand_L", "rot", [(0, (0, 0, 0)), (0.95, (-8, 0, 0), "out_cubic"), (1.25, (-8, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("spine", "rot", [(0, (0, 0, 0)), (0.35, (-6, 0, 0), "in_out_cubic"), (0.95, (8, -8, 0), "in_cubic"), (1.25, (8, -8, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("head", "rot", [(0, (0, 0, 0)), (0.35, (-8, 0, 0), "in_out_cubic"), (0.95, (6, -10, 0), "in_cubic"), (1.25, (6, -10, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "pos", [(0, (0, 0, 0)), (0.95, (0, 0, 0.05), "in_out_cubic"), (1.25, (0, 0, 0.05)), (1.5, (0, 0, 0), "in_out_cubic")])
    S = Clip("Surrender", 2.2)       # the caster bows; the staff slips away and clatters down, the runes drop with the lantern and dim
    S.keys("spine", "rot", [(0, (0, 0, 0)), (0.9, (20, 0, 0), "in_out_cubic"), (2.2, (24, 0, 0))])
    S.keys("head", "rot", [(0, (0, 0, 0)), (0.9, (30, 0, 0), "in_out_cubic"), (2.2, (36, 0, 0))])
    S.keys("body", "rot", [(0, (0, 0, 0)), (0.9, (6, 0, 0), "in_out_cubic"), (2.2, (7, 0, 0))])
    S.keys("body", "pos", [(0, (0, 0, 0)), (0.9, (0, -0.02, 0.02), "in_out_cubic"), (2.2, (0, -0.025, 0.02))])
    S.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.5, (-8, 0, 0), "in_out_cubic"), (1.1, (10, 0, 0), "in_out_cubic"), (2.2, (14, 0, 0))])
    S.keys("hand_R", "rot", [(0, (0, 0, 0)), (1.1, (8, 0, 0), "in_out_cubic"), (2.2, (10, 0, 0))])
    S.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.9, (14, 0, 0), "in_out_cubic"), (2.2, (18, 0, 0))])
    S.keys("top", "scale", [(0, (1, 1, 1)), (0.7, (1, 1, 1)), (1.4, (0.55, 0.55, 0.55), "in_out_cubic"), (2.2, (0.45, 0.45, 0.45))])
    S.keys("top", "rot", [(0, (0, 0, 0)), (0.45, (0, 90, 0), "in_quad"), (2.2, (0, 200, 0), "out_cubic")])
    rc.drop_weapon(S, rig, "weapon", 0.45, (0, 1, 0), 0.22, 0.03, (1.0, 0.0, -0.35), land_xz=(-0.02, 0.05))
    clips = [idle, mv, A, hit, vic, T, S]
    # the rune ring (bone `top`, child of the spine) must follow the lantern that the right arm carries
    for c in clips:
        ts = sorted(set(np.round(np.linspace(0, c.duration, int(c.duration * 30) + 1), 3)) | {k[0] for tr in c.tracks.values() for k in tr.keys if tr.bone in ("arm_R", "hand_R", "spine", "body", "weapon")})
        rc.follow_keys(rig, c, "top", "spine", lambda W: rc.fk_point(rig, W, "weapon", LANT), [t for t in ts if 0 <= t <= c.duration])
    return clips


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "bishop", rig, make_clips(rig), impact_time=1.10, strike_range=1.50, attack_style="ranged", seed=7)
    rc.pedestal_parts(p)
    robe(p)
    torso(p)
    mantle(p)
    embroidery(p)
    arms(p)
    head(p)
    staff(p)
    runes(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
