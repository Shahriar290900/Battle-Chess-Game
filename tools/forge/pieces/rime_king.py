"""rime_king - Rime Glacier Tyrant: a colossal armoured revenant lord in faceted obsidian plate, the glacier he was
buried in breaking out through his back as a ridge of ice (kept below the crown), a CLOSED crown of eight hovering ice
prisms caged by four silver arches around a tall ice-crystal CROSS, a frozen cape swept back, a cracked visor glowing.
Unarmed: fist and backhand.  Built from docs/art/rime_king.md on the full humanoid skeleton (smooth-skinned limbs, torso,
neck and cape; rigid plates; extra `ring` bone spins the prism ring while the cross stays facing front)."""
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
from anim import Animator, Curve, Fn, Wave, Skin, humanoid_rig, limb_tube   # noqa: E402
from anim import motion as M          # noqa: E402
from anim.curves import step_signal   # noqa: E402
import _rime_common as rc             # noqa: E402
from _rime_common import unit, shard, spikes, cluster, frost_layer  # noqa: E402

ASSET_ID = "rime_king"
V = lambda *x: np.array(x, dtype=float)       # noqa: E731

# ======================================================================================= rig
JOINTS = dict(pelvis=(0, 0.76, 0), spine=(0, 0.92, 0), chest=(0, 1.10, 0), neck=(0, 1.25, 0.01), head=(0, 1.30, 0.02), top=(0, 1.56, 0),
              clavicle_L=(0.10, 1.28, 0), shoulder_L=(0.32, 1.30, 0), elbow_L=(0.33, 1.05, 0.04), wrist_L=(0.35, 0.88, 0.15),
              hip_L=(0.12, 0.78, 0), knee_L=(0.145, 0.54, 0.05), ankle_L=(0.14, 0.27, 0.05), toe_L=(0.14, 0.245, 0.17))
J_ = lambda k: np.array(JOINTS[k] if k in JOINTS else tuple(V(-1, 1, 1) * JOINTS[k[:-1] + "L"]), dtype=float)   # noqa: E731
CAPE = [(0, 1.10, -0.20), (0.06, 0.78, -0.26), (0.12, 0.50, -0.28)]


def make_rig() -> Rig:
    r = humanoid_rig(JOINTS, cape=CAPE)
    # the cape hangs from the chest (not the floating crown, which spins independently)
    r.bones["cape_1"].parent = "chest"
    r.add("ring", "top", (0, 1.56, 0))                 # prism ring + arches: spins around the (static) cross
    r.socket("socket_weapon_R", "wrist_R", (-0.35, 0.88, 0.17))
    r.socket("socket_cast", "wrist_R", (-0.35, 0.86, 0.19))
    r.socket("socket_impact", "body", (-0.15, 1.00, 0.60))
    r.socket("socket_head", "top", (0, 1.74, 0))
    return r


LEG_SKIN = {s: Skin.chain([f"thigh_{s}", f"shin_{s}", f"foot_{s}"], pre="body", tip=J_(f"toe_{s}"), zone=0.4) for s in "LR"}
ARM_SKIN = {s: Skin.chain([f"arm_{s}", f"hand_{s}"], pre=f"clavicle_{s}", tip=J_(f"wrist_{s}"), zone=0.42) for s in "LR"}
TORSO_SKIN = Skin.chain(["body", "spine", "chest"], tip=JOINTS["neck"], zone=0.45)
NECK_SKIN = Skin.chain(["neck", "head"], pre="chest", tip=(0, 1.37, 0.03), zone=0.4)
CAPE_SKIN = Skin.chain(["cape_1", "cape_2", "cape_3"], pre="chest", tip=(0.14, 0.36, -0.29), zone=0.4)
_HANG = Skin.nearest([("body", J_("pelvis"), J_("spine")), ("thigh_L", J_("hip_L"), J_("knee_L")), ("thigh_R", J_("hip_R"), J_("knee_R"))], tau=0.035, bias={"body": 1.6})
KILT_SKIN = Skin.gradient(Skin.rigid("body"), _HANG, axis=1, v0=0.82, v1=0.60)
DARK = lambda v: (lambda P: np.full(len(P), v))       # noqa: E731

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


# ======================================================================================= legs, kilt
def lower_body(p: Piece):
    for s, nm in ((+1, "L"), (-1, "R")):
        hip, knee, ank, toe = J_(f"hip_{nm}"), J_(f"knee_{nm}"), J_(f"ankle_{nm}"), J_(f"toe_{nm}")
        # continuous dark leg core, dense rings at the knee (smooth skin bends it)
        core = limb_tube([hip + [0, 0.02, 0], (hip + knee) / 2 + [0.0, 0, 0.0], knee, (knee + ank) / 2, ank + [0, 0.02, 0]],
                         [0.080, 0.078, 0.066, 0.058, 0.054], joints=[knee], spacing=0.05, joint_spacing=0.024, joint_zone=0.06, sides=8, cap=None, up=(0, 0, 1))
        p.add(f"leg_{nm}", core, "RH_Armour", None, skin=LEG_SKIN[nm], uv_scale=2, tint=DARK(0.7))
        boot = g.superellipsoid((0.066, 0.036, 0.122), 0.4, 0.5, 4, 10).translated(s * 0.14, 0.258, 0.05)
        toec = g.superellipsoid((0.058, 0.026, 0.040), 0.4, 0.5, 3, 8).translated(s * 0.14, 0.270, 0.150)
        p.add(f"boot_{nm}", merge([boot, toec]), "RH_Obsidian", f"foot_{nm}")
        p.add(f"boot_spike_{nm}", spikes([((s * 0.14, 0.262, 0.185), (0.0, 0.1, 1.0), 0.065, 0.016)], seed=3 + (s > 0), flat=0.3, sides=5), "RH_Ice", f"foot_{nm}")
        gp = [(s * 0.14, 0.29, 0.05), (s * 0.145, 0.41, 0.06), (s * 0.15, 0.52, 0.05)]
        ridge_sec = lambda th, t: 1 + 0.30 * np.exp(-(np.arctan2(np.sin(th), np.cos(th)) / 0.55) ** 2) * (0.5 + 0.5 * np.sin(math.pi * t))
        greave = g.tube(gp, [0.056, 0.066, 0.074], sides=8, samples=2, cap=None, up=(0, 0, 1), section=ridge_sec).noised(0.0015, 20, 2, seed=4)
        p.add(f"greave_{nm}", greave, "RH_Obsidian", f"shin_{nm}")
        p.add(f"greave_lames_{nm}", rc.limb_lames(gp, [0.056, 0.066, 0.074], [0.12, 0.88], h=0.050, sweep=250, grow=0.012, seg=8), "RH_Armour", f"shin_{nm}")
        bands = merge([g.torus(0.064 + 0.012 * k, 0.0052, 14, 4).translated(s * (0.142 + 0.004 * k), y, 0.054) for k, y in enumerate((0.34, 0.455))])
        p.add(f"greave_bands_{nm}", bands, "RH_Silver", f"shin_{nm}", lod1=None, tint=DARK(0.6))
        pol = g.superellipsoid((0.066, 0.056, 0.052), 0.4, 0.5, 5, 12).translated(s * 0.15, 0.555, 0.088)
        pol2 = g.superellipsoid((0.016, 0.052, 0.040), 0.4, 0.5, 3, 8).translated(s * 0.15, 0.560, 0.126)
        p.add(f"knee_{nm}", merge([pol, pol2]), "RH_Obsidian", f"shin_{nm}")
        p.add(f"knee_fins_{nm}", merge([g.extrude(np.array([(0, 0), (0.05, 0.016), (0.0, 0.034)]), 0.010, 0.002, 1).rotated(0, s * 90, 0).translated(s * (0.150 + 0.058), 0.560 + 0.012 * q, 0.09) for q in (-1, 1)]), "RH_Obsidian", f"shin_{nm}", lod1=None)
        p.add(f"knee_spike_{nm}", spikes([((s * 0.15, 0.560, 0.135), (0.3 * s, 0.3, 1.0), 0.09, 0.030)], seed=6 + (s > 0), flat=0.3, sides=5, tip=0.4), "RH_Ice", f"shin_{nm}")
        p.add(f"knee_frost_{nm}", cluster((s * 0.15, 0.605, 0.075), (0, 1, 0.2), 3, (0.03, 0.06), (0.008, 0.012), spread=0.03, tilt=30, seed=7 + (s > 0), flat=0.3, sides=4), "RH_Frost", f"thigh_{nm}", lod1=None, tint=DARK(0.6))
        tp = [(s * 0.145, 0.55, 0.045), (s * 0.135, 0.68, 0.02), (s * 0.120, 0.80, 0.0)]
        thigh = g.tube(tp, [0.074, 0.088, 0.094], sides=8, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"thigh_{nm}", thigh, "RH_Armour", f"thigh_{nm}", uv_scale=2)
        p.add(f"thigh_lames_{nm}", rc.limb_lames(tp, [0.074, 0.088, 0.094], [0.25, 0.5, 0.75], h=0.075, sweep=215, grow=0.008, seg=8), "RH_Obsidian", f"thigh_{nm}")
    pelvis = g.superellipsoid((0.15, 0.065, 0.11), 0.4, 0.5, 4, 12).translated(0, 0.82, 0)
    p.add("pelvis", pelvis, "RH_Armour", "body", uv_scale=2)
    # frozen mail kilt: 14 stiff jagged strips (hang from the pelvis, hem follows the thighs), frost on the upper face
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
    p.add("kilt", merge(strips), "RH_Cloth", None, skin=KILT_SKIN, uv_scale=2)
    p.add("kilt_frost", spikes([(f, (math.sin(math.atan2(f[0], f[2])), 0.7, math.cos(math.atan2(f[0], f[2]))), 0.035, 0.010) for f in frost], seed=5, flat=0.3, sides=4, tip=0.5), "RH_Frost", "body", lod1=None, tint=DARK(0.6))
    tas = []
    for row, (y0, ww) in enumerate(((0.80, 0.105), (0.745, 0.095))):
        for k, a in enumerate(np.arange(-60, 61, 30) + (15 if row else 0)):
            if abs(a) > 61:
                continue
            pl = g.plate(ww, 0.13, 0.012, 0.005, bend_r=0.20, inner_x=2, taper=lambda t: 1 - 0.22 * (t + 1) / 2, drop_back=True)
            tas.append(pl.rotated(-12 - 3 * row, 0, 0).translated(0, y0 - 0.05, 0.205 + 0.012 * row).rotated(0, float(a), 0))
    p.add("tassets", merge(tas), "RH_Obsidian", None, skin=KILT_SKIN)
    p.add("tasset_studs", g.instances(g.dome(0.008, 0.007, 6, 1), [(0.205 * math.sin(math.radians(a)), 0.80 - 0.003, 0.205 * math.cos(math.radians(a)) + 0.012) for a in range(-60, 61, 30)],
                                      [(math.sin(math.radians(a)), 0.1, math.cos(math.radians(a))) for a in range(-60, 61, 30)]), "RH_Silver", "body", lod1=None, tint=DARK(0.6))
    belt = g.lathe([(0.150, 0.86), (0.162, 0.865), (0.162, 0.905), (0.150, 0.91)], 16, crease=35)
    p.add("belt", belt, "RH_Obsidian", "body")
    plate = g.extrude(g.rect_poly(0.11, 0.09, 0.008, 1), 0.016, 0.004, 1).translated(0, 0.882, 0.168)
    p.add("belt_plate", plate, "RH_Obsidian", "body")
    bars = [g.extrude(g.rect_poly(0.058, 0.0075), 0.005, 0.001, 1).rotated(0, 0, a).translated(0, 0.882, 0.178) for a in (0, 60, 120)]
    p.add("belt_glyph", merge(bars), "RH_Silver", "body")
    chain = rc.zigzag((0.0, 0.84, 0.17), (0.07, 0.64, 0.17), 7, 0.007, r=0.0045, side=(1, 0, 0))
    p.add("belt_chain", chain, "RH_Silver", "body", lod1=None, tint=DARK(0.55))
    p.add("belt_shards", spikes([((0.07, 0.645, 0.17), (0.1, -1, 0.1), 0.08, 0.012), ((0.02, 0.68, 0.17), (0, -1, 0.1), 0.06, 0.010), ((0.1, 0.70, 0.16), (0.2, -1, 0.1), 0.05, 0.009)], seed=8, flat=0.3, sides=4, tip=0.5), "RH_Ice", "body")


# ======================================================================================= torso
def torso(p: Piece):
    barrel = limb_tube([(0, 0.90, 0), (0, 1.08, 0), (0, 1.25, 0)], [0.130, 0.170, 0.205], joints=[(0, 0.92, 0), (0, 1.10, 0)], spacing=0.04, joint_spacing=0.022,
                       joint_zone=0.07, sides=12, cap="round", cap_steps=1, ellipse=(0.62, 1.0), up=(0, 0, 1))
    p.add("barrel", barrel, "RH_Armour", None, skin=TORSO_SKIN, uv_scale=2, tint=DARK(0.7))
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
    pec = [g.superellipsoid((0.100, 0.082, 0.050), 0.45, 0.6, 5, 12).rotated(0, sx * 12, 0).translated(sx * 0.095, 1.17, 0.095) for sx in (-1, 1)]
    p.add("pectorals", merge(pec), "RH_Obsidian", "chest")
    keel = g.extrude(np.array([(-0.012, 1.02), (0.012, 1.02), (0.018, 1.17), (0.0, 1.27), (-0.018, 1.17)]), 0.040, 0.012, 1).translated(0, 0, 0.123)
    p.add("keel_ridge", keel, "RH_Obsidian", "chest", lod1=None)
    col = [g.superellipsoid((0.100, 0.020, 0.050), 0.45, 0.6, 3, 9).rotated(0, 0, sx * -14).translated(sx * 0.115, 1.285, 0.045) for sx in (-1, 1)]
    p.add("collar_plates", merge(col), "RH_Obsidian", "chest")
    trap = [g.superellipsoid((0.110, 0.034, 0.085), 0.5, 0.65, 4, 10).rotated(0, 0, sx * -24).translated(sx * 0.185, 1.305, -0.005) for sx in (-1, 1)]
    p.add("trapezius", merge(trap), "RH_Obsidian", "chest")
    ridge = lambda y: 0.020 * smoothstep(1.04, 1.12, y) * (1 - smoothstep(1.22, 1.30, y))
    ys = [1.100, 1.108, 1.14, 1.18, 1.22, 1.26, 1.295]
    gr = [0.002, 0.012, 0.016, 0.018, 0.018, 0.014, 0.0]
    cuirass = g.loft(np.stack([tring(y, a, 14, ridge(y)) for y, a in zip(ys, gr)]), closed=True, crease=32)
    cuirass = cuirass.dented(5, 0.04, 0.003, seed=11)
    p.add("cuirass", cuirass, "RH_Obsidian", "chest")
    p.add("cuirass_lip", g.tube(tring(1.102, 0.0105, 20), 0.0075, sides=4, samples=1, cap=None, smooth=False, closed=True, up=(0, 1, 0)), "RH_Silver", "chest", lod1=None)
    p.add("cuirass_frost", frost_layer(cuirass, 0.008, min_ny=0.5, cover=0.3, seed=3), "RH_Frost", "chest", lod1=None, tint=DARK(0.5))
    glyphs = []
    for k, (x, y) in enumerate(((-0.07, 1.20), (0.07, 1.20), (0.0, 1.13))):
        def bar(x0, y0, x1, y1, w=0.0055):
            L = math.hypot(x1 - x0, y1 - y0)
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) - 90
            return g.extrude(g.rect_poly(w, L), 0.005, 0.001, 1).rotated(0, 0, ang).translated((x0 + x1) / 2, (y0 + y1) / 2, 0)
        parts = [bar(0, -0.035, 0, 0.035), bar(0, 0.035, 0.022, 0.012), bar(0, 0.008, 0.022, -0.016)] if k != 1 else [bar(-0.018, 0.035, 0.008, 0.004), bar(0.008, 0.004, -0.012, -0.008), bar(-0.012, -0.008, 0.016, -0.035)]
        z = float(np.interp(y, Y_LV, ZF)) + 0.020 + float(ridge(y)) * math.exp(-(x / 0.035) ** 2)
        glyphs.append(merge(parts).translated(x, y, z))
    p.add("chest_glyphs", merge(glyphs), "RH_Silver", "chest", lod1=None, tint=DARK(0.7))
    # one glowing rune stroke (accent)
    z1 = float(np.interp(1.13, Y_LV, ZF)) + 0.020 + float(ridge(1.13))
    p.add("chest_rune_glow", g.extrude(g.rect_poly(0.0042, 0.060), 0.0042, 0.0008, 1).translated(0, 1.13, z1 + 0.002), "RH_Glow", "chest", bake=False, lod1="keep")
    p.add("chest_ice", cluster((-0.13, 1.10, 0.125), (-0.3, 0.5, 1.0), 4, (0.06, 0.11), (0.015, 0.026), spread=0.05, tilt=30, seed=13, flat=0.3), "RH_Ice", "chest")
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
    p.add("backplate", g.warp(back, warp_back, 40), "RH_Obsidian", "chest")
    # the back ridge: seven crystals breaking out along the spine; every tip stays below 1.42 (the crown is the tallest thing)
    ys_ = [0.98, 1.05, 1.12, 1.19, 1.25, 1.30, 1.34]
    ln_ = [0.12, 0.17, 0.22, 0.24, 0.16, 0.11, 0.07]
    rr_ = [0.030, 0.036, 0.044, 0.050, 0.046, 0.038, 0.030]
    specs = []
    rng = np.random.default_rng(14)
    for i, (y, ln, r) in enumerate(zip(ys_, ln_, rr_)):
        z = -float(np.interp(min(y, 1.30), Y_LV, ZB)) - 0.01 - 0.01 * i * 0.3
        d = unit((0.14 * (rng.random() - 0.5), 1.0, -0.36 - 0.05 * (i % 2)))
        ln = min(ln, (1.415 - y) / d[1])
        specs.append(((0.0, y, z), d, ln, r))
    p.add("back_ridge", spikes(specs, seed=70, bend=0.05, flat=0.26, sides=6, tip=0.42, jitter=0.15), "RH_Ice", "chest")
    sub = []
    for i, (y, ln, r) in enumerate(zip(ys_, ln_, rr_)):
        for sx in (-1, 1):
            sub.append(((sx * 0.055, y - 0.02, -float(np.interp(min(y, 1.30), Y_LV, ZB)) - 0.005), unit((sx * 0.6, 0.8, -0.5)), min(0.07 + 0.03 * (i % 3), 1.40 - y), 0.014))
    p.add("back_ridge_sub", spikes(sub, seed=90, flat=0.3, sides=5, tip=0.45), "RH_Ice", "chest", lod1=None)
    seam = [g.torus(0.040 + 0.004 * (i % 2), 0.0034, 12, 3).rotated(80, 0, 0).translated(0, y - 0.005, -float(np.interp(min(y, 1.30), Y_LV, ZB)) - 0.004) for i, y in enumerate(ys_)]
    p.add("ridge_seams", merge(seam), "RH_Seam", "chest", bake=False, lod1=None)
    neck = limb_tube([(0, 1.24, 0), (0, 1.30, 0.02), (0, 1.36, 0.03)], [0.064, 0.060, 0.056], joints=[(0, 1.30, 0.02)], spacing=0.04, joint_spacing=0.02, joint_zone=0.05,
                     sides=8, cap=None, up=(0, 0, 1))
    p.add("neck", neck, "RH_Armour", None, skin=NECK_SKIN, uv_scale=2, tint=DARK(0.7))
    gor = g.lathe([(0.095, 1.27), (0.114, 1.28), (0.118, 1.33), (0.098, 1.355), (0.076, 1.355)], 8, crease=30)
    p.add("gorget", gor, "RH_Obsidian", "chest")
    p.add("gorget_wire", g.torus(0.118, 0.0055, 16, 4).translated(0, 1.31, 0), "RH_Silver", "chest", lod1=None)


# ======================================================================================= cape (chain skinned)
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
    p.add("cape", cm, "RH_Cloth", None, skin=CAPE_SKIN, uv_scale=2)
    sheath = []
    for r in range(R):
        row = []
        for k in range(K - 3, K):
            x, y, z = rings[r][k]
            row.append((x, y, z - 0.014))
        sheath.append(row)
    sh = g.loft(np.array(sheath)[::-1], closed=False, crease=40, v_tile=0.25, u_tile=0.25)
    p.add("cape_sheath", sh, "RH_Ice", None, skin=CAPE_SKIN)
    caps = []
    rng = np.random.default_rng(3)
    for k in range(14):
        r = 1 + int(rng.random() * (R - 3))
        kk = int(rng.random() * K)
        x, y, z = rings[r][kk]
        caps.append(((x, y + 0.012, z - 0.004), unit((0.0, 0.5, -1.0)), 0.025 + 0.03 * rng.random(), 0.010))
    p.add("cape_frost", spikes(caps, seed=40, flat=0.3, sides=4, tip=0.5), "RH_Frost", None, skin=CAPE_SKIN, lod1=None, tint=DARK(0.6))
    p.add("cape_hem_ice", spikes([((x, y + 0.01, z), (0.2, -1, -0.2), 0.06, 0.012) for x, y, z in tips], seed=44, flat=0.3, sides=4, tip=0.5), "RH_Ice", None, skin=CAPE_SKIN, lod1=None)
    for s in (-1, 1):
        d = g.lathe([(0, 0), (0.026, 0), (0.026, 0.008), (0, 0.010)], 12).rotated(90, 0, 0)
        bars = [g.extrude(g.rect_poly(0.040, 0.005), 0.004, 0.001, 1).rotated(0, 0, a).translated(0, 0, 0) for a in (0, 60, 120)]
        pos = (s * 0.115, 1.27, 0.115)
        p.add(f"fastener_{'L' if s > 0 else 'R'}", merge([d.translated(*pos), merge(bars).translated(pos[0], pos[1], pos[2] + 0.012)]), "RH_Silver", "chest", lod1=None)


# ======================================================================================= pauldrons, arms
BELL = [(0.0, 0.070), (0.060, 0.068), (0.105, 0.046), (0.128, 0.0), (0.120, -0.007), (0.136, -0.013), (0.153, -0.052), (0.144, -0.059), (0.160, -0.066),
        (0.178, -0.108), (0.168, -0.115), (0.180, -0.122), (0.192, -0.152), (0.0, -0.152)]


def bell(side, scale=1.0):
    prof = [(r * scale, y * scale) for r, y in BELL][::-1]
    m = g.lathe(prof, 16, crease=30).noised(0.0022, 14, 2, seed=5 + int(side > 0))
    lips = merge([g.torus(r * scale, 0.0058 * scale, 18, 4).translated(0, y * scale, 0) for r, y in ((0.138, -0.013), (0.162, -0.067), (0.183, -0.123))])
    return m, lips


def place(m, side, cx, cy, tilt, sx=1.12, sz=0.95):
    return m.scaled(sx, 1.0, sz).rotated(0, 0, side * -tilt).translated(cx, cy, 0.0)


def pauldrons(p: Piece):
    m, lips = bell(+1, 0.84)
    p.add("pauldron_L", place(m, +1, 0.335, 1.285, 18), "RH_Obsidian", "clavicle_L")
    p.add("pauldron_L_lips", place(lips, +1, 0.335, 1.285, 18), "RH_Silver", "clavicle_L", lod1=None, tint=DARK(0.55))
    p.add("pauldron_L_frost", frost_layer(place(m, +1, 0.335, 1.285, 18), 0.009, min_ny=0.6, cover=0.16, seed=5), "RH_Frost", "clavicle_L", lod1=None, tint=DARK(0.5))
    sp = []
    for k, (x, z, ln, tl) in enumerate(((0.36, 0.06, 0.085, 18), (0.40, -0.03, 0.095, 26), (0.30, -0.07, 0.07, 10), (0.43, 0.05, 0.06, 38), (0.27, 0.07, 0.06, 6), (0.37, 0.09, 0.05, 28))):
        sp.append(((x, 1.335, z), unit((math.sin(math.radians(tl)), 1.0, 0.05 * (k - 2))), ln, 0.030 - 0.003 * k))
    p.add("pauldron_L_spikes", spikes(sp, seed=21, flat=0.3, sides=5, tip=0.4), "RH_Ice", "clavicle_L")
    p.add("pauldron_L_side_spikes", spikes([((0.44 + 0.02 * i, 1.22 - 0.055 * i, 0.0), unit((1.0, -0.2, 0.0)), 0.07 - 0.008 * i, 0.019) for i in range(3)] +
                                           [((0.38 + 0.02 * i, 1.21 - 0.055 * i, 0.12), unit((0.7, -0.2, 0.7)), 0.06, 0.015) for i in range(2)], seed=24, flat=0.3, sides=5, tip=0.4), "RH_Ice", "clavicle_L", lod1=None)
    mr, lr = bell(-1, 0.76)
    p.add("pauldron_R", place(mr, -1, -0.325, 1.275, 12, 1.05, 1.0), "RH_Obsidian", "clavicle_R")
    p.add("pauldron_R_lips", place(lr, -1, -0.325, 1.275, 12, 1.05, 1.0), "RH_Silver", "clavicle_R", lod1=None, tint=DARK(0.55))
    p.add("pauldron_R_frost", frost_layer(place(mr, -1, -0.325, 1.275, 12, 1.05, 1.0), 0.009, min_ny=0.6, cover=0.16, seed=6), "RH_Frost", "clavicle_R", lod1=None, tint=DARK(0.5))
    runes = []
    for k in range(7):
        a_ = math.radians(-70 + 23 * k)
        runes.append(g.extrude(g.rect_poly(0.0065, 0.030), 0.004, 0.001, 1).rotated(0, 0, 14 * (k % 3 - 1)).translated(0, 1.24, 0.14).rotated(0, math.degrees(a_), 0).translated(-0.325, 0, 0))
    p.add("pauldron_R_runes", merge(runes), "RH_Silver", "clavicle_R", lod1=None, tint=DARK(0.6))
    p.add("pauldron_R_spikes", spikes([((-0.36, 1.33, 0.02), unit((-0.5, 1.0, 0.0)), 0.07, 0.020), ((-0.30, 1.34, -0.04), unit((-0.2, 1.0, -0.2)), 0.06, 0.018)], seed=27, flat=0.3, sides=5, tip=0.4), "RH_Ice", "clavicle_R", lod1=None)


def arms(p: Piece):
    for s, nm in ((+1, "L"), (-1, "R")):
        sh, el, wr = J_(f"shoulder_{nm}"), J_(f"elbow_{nm}"), J_(f"wrist_{nm}")
        sleeve = limb_tube([sh + [0, -0.01, 0], (sh + el) / 2, el, (el + wr) / 2, wr + [0, 0.02, -0.01]], [0.064, 0.056, 0.050, 0.045, 0.040], joints=[el],
                           spacing=0.04, joint_spacing=0.02, joint_zone=0.055, sides=8, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"sleeve_{nm}", sleeve, "RH_Armour", None, skin=ARM_SKIN[nm], uv_scale=2, tint=DARK(0.7))
        up_ = [(s * 0.32, 1.28, 0.0), (s * 0.325, 1.17, 0.02), (s * 0.33, 1.06, 0.04)]
        p.add(f"rerebrace_{nm}", rc.limb_lames(up_, [0.068, 0.058, 0.052], [0.25, 0.65], h=0.075, sweep=250, grow=0.010, seg=8), "RH_Obsidian", f"arm_{nm}")
        p.add(f"elbow_spike_{nm}", spikes([((s * 0.375, 1.05, -0.03), (s * 1.0, 0.0, -0.4), 0.08, 0.024)], seed=30 + (s > 0), flat=0.3, sides=5, tip=0.4), "RH_Ice", f"hand_{nm}")
        fp = [(s * 0.33, 1.05, 0.04), (s * 0.35, 0.95, 0.11), (s * 0.35, 0.88, 0.15)]
        p.add(f"vambrace_{nm}", rc.limb_lames(fp, [0.052, 0.048, 0.044], [0.34, 0.66], h=0.085, sweep=250, grow=0.010, seg=8), "RH_Obsidian", f"hand_{nm}")
        p.add(f"vambrace_wire_{nm}", rc.helix(0.050, 0.93, 0.98, 2.0, r=0.0045, sides=3, per_turn=8, ax=s * 0.349, az=0.105), "RH_Silver", f"hand_{nm}", lod1=None)
        cop = g.superellipsoid((0.042, 0.046, 0.040), 0.45, 0.55, 4, 10).translated(s * 0.352, 1.048, -0.004)
        p.add(f"elbow_cop_{nm}", cop, "RH_Obsidian", f"hand_{nm}")
        p.add(f"elbow_ring_{nm}", g.torus(0.050, 0.0045, 14, 4).rotated(0, 0, 90).translated(s * 0.33, 1.05, 0.04), "RH_Silver", f"hand_{nm}", lod1=None, tint=DARK(0.6))
        sc = 1.12 if s < 0 else 1.0
        fist = g.superellipsoid((0.045 * sc, 0.040 * sc, 0.050 * sc), 0.4, 0.5, 4, 10).translated(s * 0.35, 0.835, 0.17)
        p.add(f"fist_{nm}", fist, "RH_Obsidian", f"wrist_{nm}")
        kn = spikes([((s * (0.335 + 0.0225 * k), 0.84, 0.215), (0.0, 0.2, 1.0), 0.032, 0.008) for k in range(4)], seed=50 + (s > 0), flat=0.2, sides=4, tip=0.55)
        p.add(f"knuckles_{nm}", kn, "RH_Ice", f"wrist_{nm}", lod1=None)
        th = g.tube([(s * 0.315, 0.845, 0.18), (s * 0.31, 0.83, 0.205)], [0.013, 0.010], sides=5, samples=1, cap="round", cap_steps=1, smooth=False)
        p.add(f"thumb_{nm}", th, "RH_Obsidian", f"wrist_{nm}", lod1=None)
        p.add(f"shoulder_frost_{nm}", cluster((s * 0.37, 1.32, 0.04), (s * 0.4, 1.0, 0.0), 2, (0.02, 0.04), (0.008, 0.012), spread=0.02, tilt=25, seed=60 + (s > 0), flat=0.3, sides=4), "RH_Frost", f"clavicle_{nm}", lod1=None, tint=DARK(0.6))
    p.add("fist_crust", cluster((-0.355, 0.88, 0.20), (-0.2, 0.8, 0.6), 5, (0.04, 0.09), (0.010, 0.016), spread=0.04, tilt=35, seed=71, flat=0.3), "RH_Ice", "wrist_R")


# ======================================================================================= head (helm top at 1.475)
HELM = [(0.090, 1.300), (0.100, 1.355), (0.096, 1.410), (0.074, 1.450), (0.036, 1.470), (0.0, 1.475)]
FC = 1.378            # visor / faceplate centre height


def head(p: Piece):
    helm = g.lathe(HELM, 8, crease=28)
    helm = helm.scaled(1.0, 1.0, 1.08).translated(0, 0, 0.012)
    p.add("helm", helm, "RH_Obsidian", "head", uv_scale=2)
    p.add("helm_frost", frost_layer(helm, 0.006, min_ny=0.6, cover=0.25, seed=9), "RH_Frost", "head", lod1=None, tint=DARK(0.5))
    cheeks = []
    for s in (-1, 1):
        m = g.extrude_plane(np.array([(1.32, 0.015), (1.35, 0.095), (1.395, 0.05)]), 0.012, "YZ", bevel=0.003, bevel_segments=1)
        cheeks.append(m.translated(s * 0.105, 0, 0.012))
    p.add("cheek_flares", merge(cheeks), "RH_Obsidian", "head")
    mask = np.array([(-0.058, -0.052), (0.058, -0.052), (0.072, -0.012), (0.066, 0.036), (0.030, 0.050), (-0.030, 0.050), (-0.066, 0.036), (-0.072, -0.012)])
    face = g.extrude(mask, 0.036, 0.007, 1).rotated(-4, 0, 0).translated(0, FC - 0.004, 0.106)
    p.add("faceplate", face, "RH_Obsidian", "head")
    p.add("brow", g.superellipsoid((0.098, 0.013, 0.028), 0.4, 0.5, 3, 9).rotated(-10, 0, 0).translated(0, 1.418, 0.098), "RH_Obsidian", "head")
    p.add("nose_ridge", g.extrude(np.array([(-0.007, FC - 0.045), (0.007, FC - 0.045), (0.004, FC - 0.004), (-0.004, FC - 0.004)]), 0.012, 0.003, 1).translated(0, 0, 0.138), "RH_Obsidian", "head", lod1=None)
    slit = g.extrude(np.array([(-0.040, -0.003), (0.0, -0.0045), (0.040, -0.003), (0.034, 0.0035), (0.0, 0.0045), (-0.034, 0.0035)]), 0.004, 0.0008, 1).translated(0, FC + 0.006, 0.1455)
    p.add("visor_glow", slit, "RH_Glow", "head", bake=False, lod1="keep")
    cr = []
    for x, sgn in ((-0.022, 1), (0.026, -1)):
        pts = [(x, FC + 0.006 + sgn * 0.004, 0.1465), (x + 0.006, FC + 0.006 + sgn * 0.022, 0.1465), (x - 0.004, FC + 0.006 + sgn * 0.040, 0.1465)]
        cr.append(g.tube(pts, 0.0024, sides=3, samples=1, cap=None, smooth=False))
    p.add("visor_cracks", merge(cr), "RH_Seam", "head", bake=False, lod1=None)
    horns = [shard(0.08, 0.026, sides=6, flat=0.25, bend=0.15 * s, seed=3 + s).aimed((s * 1.0, 0.4, -0.2), (s * 0.095, 1.40, 0.0)) for s in (-1, 1)]
    p.add("helm_horns", merge(horns), "RH_Ice", "head")
    wires = []
    for k in range(4):
        a = -50 + 33 * k
        pts = []
        for t in np.linspace(0.10, 0.98, 8):
            yy = 1.36 + 0.11 * t
            rr = float(np.interp(yy, [q[1] for q in HELM], [q[0] for q in HELM])) + 0.006
            pts.append((rr * math.sin(math.radians(a)), yy, rr * math.cos(math.radians(a)) * 1.08 + 0.012))
        wires.append(g.tube(pts, 0.0036, sides=4, samples=1, cap=None, smooth=True))
    p.add("helm_wire", merge(wires), "RH_Silver", "head", lod1=None, tint=DARK(0.6))


# ======================================================================================= crown: prism ring + 4 arches + ice cross
def crown(p: Piece):
    pr, sub = [], []
    for k in range(8):
        a = math.radians(k * 45)
        h = 0.105 if k % 2 == 0 else 0.095
        pos = (0.115 * math.sin(a), 1.515, 0.115 * math.cos(a))
        d = unit((0.05 * math.sin(a), 1.0, 0.05 * math.cos(a)))
        pr.append(shard(h, 0.026, sides=6, tip=0.30, flat=0.0, taper=0.9, jitter=0.0, seed=1, cap=True).aimed(d, pos))
        sub.append(((pos[0], 1.512, pos[2]), (0, -1, 0), 0.028 + 0.004 * (k % 2), 0.008))
    p.add("prisms", merge(pr), "RH_Ice", "ring")
    p.add("prism_subshards", spikes(sub, seed=17, flat=0.2, sides=4, tip=0.5), "RH_Ice", "ring", lod1=None)
    p.add("prism_ring_band", g.torus(0.115, 0.005, 24, 4).translated(0, 1.522, 0), "RH_Silver", "ring", lod1=None, tint=DARK(0.6))
    p.add("prism_ring_glow", g.torus(0.115, 0.0035, 24, 4).translated(0, 1.531, 0), "RH_Seam", "ring", bake=False, lod1="keep")
    # four silver arches from the tallest prism tips (0/90/180/270) up over to the cross shaft: the closed cage
    arch = []
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        s_, c_ = math.sin(a), math.cos(a)
        pts = [(0.115 * s_, 1.62, 0.115 * c_), (0.103 * s_, 1.652, 0.103 * c_), (0.066 * s_, 1.678, 0.066 * c_), (0.0, 1.684, 0.0)]
        arch.append(g.tube(pts, 0.0055, sides=4, samples=2, cap=None, smooth=True))
    p.add("crown_arches", merge(arch), "RH_Silver", "ring", tint=DARK(0.9))
    sheath = [g.tube([(0.115 * math.sin(math.radians(a)), 1.625, 0.115 * math.cos(math.radians(a))), (0.103 * math.sin(math.radians(a)), 1.652, 0.103 * math.cos(math.radians(a))),
                      (0.066 * math.sin(math.radians(a)), 1.678, 0.066 * math.cos(math.radians(a)))], 0.008, sides=4, samples=2, cap=None, smooth=True) for a in (0, 180)]
    p.add("crown_arch_ice", merge(sheath), "RH_Ice", "ring", lod1=None)
    # crystal cross (static; faces front): hex-prism shaft with pointed ends, crossbar along X, a short bar along Z so it reads as a cross from every side
    shaft = g.lathe([(0.0, 1.548), (0.023, 1.575), (0.023, 1.672), (0.0, 1.700)], 6, crease=25)
    bar_x = g.lathe([(0.0, -0.056), (0.019, -0.036), (0.019, 0.036), (0.0, 0.056)], 6, crease=25).rotated(0, 0, 90).translated(0, 1.648, 0)
    bar_z = g.lathe([(0.0, -0.040), (0.015, -0.026), (0.015, 0.026), (0.0, 0.040)], 6, crease=25).rotated(90, 0, 0).translated(0, 1.648, 0)
    p.add("cross", merge([shaft, bar_x, bar_z]), "RH_Ice", "top", lod1="keep")
    core_v = g.tube([(0, 1.565, 0), (0, 1.690, 0)], 0.0085, sides=4, samples=1, cap="flat", smooth=False)
    core_h = g.tube([(-0.050, 1.648, 0), (0.050, 1.648, 0)], 0.0085, sides=4, samples=1, cap="flat", smooth=False)
    core_z = g.tube([(0, 1.648, -0.036), (0, 1.648, 0.036)], 0.0065, sides=4, samples=1, cap="flat", smooth=False)
    p.add("cross_core", merge([core_v, core_h, core_z]), "RH_Glow", "top", bake=False, lod1="keep")


# ======================================================================================= clips
def _anim(rig, cape_on=True):
    a = Animator(rig)
    M.plant_feet(a)
    if cape_on:
        a.secondary(["cape_1", "cape_2", "cape_3"], driver="chest", freq=2.0, zeta=0.32, follow=1.1, accel=0.08, max_deg=26, decay=0.85)
    a.secondary(["top"], driver="chest", freq=1.6, zeta=0.45, follow=0.9, accel=0.03, max_deg=5)
    return a


def _rest_both(a):
    pass


def clip_idle(rig):
    a = _anim(rig)
    T = 4.0
    M.idle(a, period=T, breath=1.5, shift=0.7, sway=0.008, look=0.8)
    a.rot("ring", Fn(lambda t: V(0, 90.0 * t / T, 0)))                       # 4-fold symmetric: one quarter turn per loop = seamless slow spin
    a.pos("top", Wave(V(0, 0.010, 0), 1 / T, 0.1))
    a.rot("hand_R", Wave(V(-2.5, 0, 0), 1 / T, 0.6))                         # knuckles flex
    return a, T, True, 30, ()


def clip_move(rig):
    a = _anim(rig)
    T = 1.0
    M.biped_gait(a, T, stride=0.05, lift=0.06, duty=0.62, bob=0.016, sway=0.014, roll=3.0, twist=5.0, lean=3.0, arm_swing=(9, 9), elbow=12,
                 toe_off=20, strike=-8, head_stab=0.5)
    a.rot("spine", Wave(V(1.6, 0, 0), 2 / T, 0.1))                           # heavy chest drop on every footfall
    a.rot("ring", Wave(V(0, 14, 0), 1 / T, 0.2))
    a.pos("top", Wave(V(0, 0.008, 0), 2 / T, 0.15))
    return a, T, True, 30, ()


def clip_hit(rig):
    a = _anim(rig)
    T = 0.5
    z = V(0, 0, 0)
    a.pos("body", Curve([(0, z), (0.10, V(0, -0.02, -0.05), "out_cubic"), (0.26, V(0, -0.008, -0.012), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.10, V(-8, 2, 1), "out_cubic"), (0.26, V(1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.11, V(-8, 3, 1), "out_cubic"), (0.28, V(2, -1, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.12, V(-8, 4, 2), "out_cubic"), (0.30, V(2, -2, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.13, V(-8, 4, 2), "out_cubic"), (0.32, V(2, -2, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.14, V(-8, 5, 4), "out_cubic"), (0.34, V(2, -2, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    for s, sg in (("L", 1), ("R", -1)):
        a.rot(f"arm_{s}", Curve([(0, z), (0.10, V(8, 0, sg * -5), "out_cubic"), (0.26, V(-2, 0, sg * 1), "in_out_cubic"), (T, z, "in_out_cubic")]))
        a.rot(f"clavicle_{s}", Curve([(0, z), (0.10, V(0, 0, sg * -3), "out_cubic"), (T, z, "in_out_cubic")]))
    a.pos("top", Curve([(0, z), (0.10, V(0, 0.02, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("ring", Curve([(0, z), (0.10, V(0, 18, 0), "out_cubic"), (T, V(0, 90, 0), "in_out_cubic")]))
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.1, V(0, 0, -0.012), "out_cubic"), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.25)
    return a, T, False, 30, ()


IMPACT = 1.20


def clip_attack(rig):
    a = _anim(rig)
    T, I = 2.4, IMPACT
    z = V(0, 0, 0)
    W, S = 0.55, 0.70                       # wind-up peak, slam
    # right arm: raise the fist overhead, slam it down (spikes erupt at 0.70), coil across the chest, whip out as a backhand
    a.rot("arm_R", Curve([(0, z), (0.30, V(-60, 0, 0), "ease_in_out"), (W, V(-125, -4, 0), "ease_in_out"), (W + 0.04, V(-127, -4, 0), {"tan": "flat"}), (S, V(-20, 0, 0), "snap_in"), (0.78, V(-16, 0, 0), "out_quad"),
                          (0.92, V(-70, -4, 0), "ease_in_out"), (1.07, V(-72, -14, 0), "ease_in_out"), (I, V(-62, 22, 0), "snap_in"), (1.40, V(-58, 10, 0), "out_cubic"), (1.52, V(-58, 10, 0), {"tan": "flat"}),
                          (T, z, "in_out_cubic")]))
    a.rot("hand_R", Curve([(0, z), (W, V(-40, 0, 0), "ease_in_out"), (S, V(0, 0, 0), "snap_in"), (1.07, V(-30, 0, 0), "ease_in_out"), (I, V(-5, 0, 0), "snap_in"), (1.40, V(-5, 0, 0)), (T, z, "in_out_cubic")]))
    a.rot("wrist_R", Curve([(0, z), (W, V(-12, 0, 0), "ease_in_out"), (S, V(14, 0, 0), "snap_in"), (1.07, V(0, 0, 0), "ease_in_out"), (I, V(10, 0, 0), "snap_in"), (T, z, "in_out_cubic")]))
    a.rot("arm_L", Curve([(0, z), (W, V(-12, 0, 6), "ease_in_out"), (S, V(8, 0, 4), "snap_in"), (I, V(12, 0, 2), "snap_in"), (1.5, V(10, 0, 2)), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (W, V(0, 0, -8), "ease_in_out"), (S, V(0, 0, 5), "snap_in"), (1.07, V(0, 0, -6), "ease_in_out"), (I, V(0, 0, 4), "snap_in"), (1.5, V(0, 0, 3)), (T, z, "in_out_cubic")]))
    # pelvis leads: weight back, lunge into the slam, coil, lunge into the backhand (impact), settle
    a.pos("body", Curve([(0, z), (W, V(0, 0.02, -0.04), "ease_in_out"), (S - 0.04, V(0, -0.02, 0.16), "snap_in"), (0.90, V(0, -0.02, 0.10), "ease_in_out"), (1.07, V(0, 0.0, 0.0), "ease_in_out"),
                         (I - 0.05, V(0, -0.03, 0.24), "snap_in"), (1.40, V(0, -0.03, 0.24), "out_cubic"), (1.55, V(0, -0.03, 0.24), {"tan": "flat"}), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (W, V(-4, 0, 0), "ease_in_out"), (S - 0.04, V(18, 0, 0), "snap_in"), (1.07, V(-3, 8, 0), "ease_in_out"), (I - 0.05, V(0, -4, 0), "snap_in"), (1.42, V(0, -8, 0)), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (W, V(-8, 10, 0), "ease_in_out"), (S, V(22, 0, 0), "snap_in"), (1.07, V(0, 50, 0), "ease_in_out"), (I - 0.03, V(0, -8, 0), "snap_in"), (1.42, V(0, -14, 0)), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (W, V(-4, 6, 0), "ease_in_out"), (S, V(10, 0, 0), "snap_in"), (1.07, V(0, 18, 0), "ease_in_out"), (I, V(0, -4, 0), "snap_in"), (1.42, V(0, -6, 0)), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (W, V(-4, 0, 0), "ease_in_out"), (S, V(8, 0, 0), "snap_in"), (1.07, V(0, -14, 0), "ease_in_out"), (I + 0.03, V(0, 8, 0), "snap_in"), (1.45, V(0, 8, 0)), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (W, V(-6, 0, 0), "ease_in_out"), (S, V(8, 0, 0), "snap_in"), (1.07, V(0, -20, 0), "ease_in_out"), (I + 0.04, V(0, 12, 0), "snap_in"), (1.45, V(0, 12, 0)), (T, z, "in_out_cubic")]))
    a.pos("top", Curve([(0, z), (W, V(0, 0.03, 0), "ease_in_out"), (S, V(0, 0.01, 0), "snap_in"), (1.42, V(0, 0.01, 0)), (T, z, "in_out_cubic")]))
    a.rot("ring", Curve([(0, z), (W, V(0, 30, 0), "ease_in_out"), (S, V(0, 90, 0), "snap_in"), (I, V(0, 180, 0), "ease_in_out"), (T, V(0, 360, 0), "in_out_cubic")]))
    # feet: left foot strides into the lunge during the wind-up and holds; right drags back, then both recover
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.30, z), (0.46, V(0, 0.06, 0.08), "ease_in_out"), (0.66, V(0, 0, 0.15), "ease_in_out"), (1.60, V(0, 0, 0.15)), (1.78, V(0, 0.05, 0.08), "ease_in_out"), (2.05, z, "ease_in_out")]),
               rot=Curve([(0, z), (0.30, z), (0.40, V(20, 0, 0), "ease_in_out"), (0.56, V(-8, 0, 0), "ease_in_out"), (0.66, z, "ease_in_out"), (1.60, z), (1.70, V(14, 0, 0), "ease_in_out"), (1.90, V(-5, 0, 0), "ease_in_out"), (2.05, z, "ease_in_out")]))
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.5, z), (1.0, V(0, 0, -0.05), "in_out_cubic"), (1.6, V(0, 0, -0.05)), (2.1, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.3)
    return a, T, False, 60, (I,)


def clip_victory(rig):
    a = _anim(rig)
    T = 2.0
    z = V(0, 0, 0)
    a.rot("arm_R", Curve([(0, z), (0.25, V(-60, 0, -4), "ease_in_out"), (0.70, V(-150, 0, -6), ("spring", 0.10, 1.5)), (T, V(-150, 0, -6), "in_out_cubic")]))
    a.rot("hand_R", Curve([(0, z), (0.70, V(-20, 0, 0), ("spring", 0.10, 1.5)), (T, V(-20, 0, 0))]))
    a.rot("arm_L", Curve([(0, z), (0.70, V(-20, 0, 4), "out_cubic"), (T, V(-20, 0, 4))]))
    a.pos("body", Curve([(0, z), (0.18, V(0, -0.02, 0), "ease_in_out"), (0.62, V(0, 0.02, 0.01), ("spring", 0.2, 1.5)), (T, V(0, 0.016, 0.01), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.18, V(3, 0, 0)), (0.62, V(-3, 0, 0), "out_cubic"), (T, V(-2, 0, 0), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.18, V(4, 0, 0)), (0.66, V(-8, 0, 0), ("spring", 0.15, 1.5)), (T, V(-7, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.18, V(4, 0, 0)), (0.68, V(-8, 0, 0), ("spring", 0.15, 1.5)), (T, V(-7, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.72, V(-12, 0, 0), ("spring", 0.15, 1.5)), (T, V(-10, 0, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.7, V(0, 0, -8), "out_cubic"), (T, V(0, 0, -8))]))
    a.pos("top", Curve([(0, z), (0.7, V(0, 0.03, 0), "out_cubic"), (T, V(0, 0.03, 0), "in_out_cubic")]))
    a.rot("ring", Curve([(0, z), (0.7, V(0, 180, 0), "out_cubic"), (T, V(0, 450, 0), "in_out_cubic")]))
    return a, T, False, 30, ()


def clip_taunt(rig):
    a = _anim(rig)
    T = 1.5
    z = V(0, 0, 0)
    a.rot("arm_R", Curve([(0, z), (0.35, V(-125, 0, -8), "out_cubic"), (1.05, V(-128, 0, -8)), (T, z, "in_out_cubic")]))
    a.rot("hand_R", Curve([(0, z), (0.35, V(-45, 0, 0), "out_cubic"), (1.05, V(-45, 0, 0)), (T, z, "in_out_cubic")]))
    a.rot("wrist_R", Curve([(0, z), (0.50, V(-14, 0, 0), "in_out_cubic"), (0.65, V(10, 0, 0), "in_out_cubic"), (0.80, V(-14, 0, 0), "in_out_cubic"), (0.95, V(10, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("arm_L", Curve([(0, z), (0.35, V(-8, 0, 3), "out_cubic"), (1.05, V(-8, 0, 3)), (1.2, V(-16, 0, 2), "snap_in"), (T, z, "in_out_cubic")]))
    a.rot("wrist_L", Curve([(0, z), (1.05, z), (1.12, V(12, 0, 0), "snap_in"), (1.3, z, "in_out_cubic")]))
    a.pos("body", Curve([(0, z), (0.35, V(0, -0.012, 0.01), "ease_in_out"), (1.05, V(0, -0.012, 0.01)), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.35, V(-3, 0, 0), "ease_in_out"), (1.05, V(-3, 0, 0)), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.35, V(-5, 0, 0), "ease_in_out"), (1.05, V(-5, 0, 0)), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.35, V(-3, 0, 0), "ease_in_out"), (1.05, V(-3, 0, 0)), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.35, V(-4, 0, -6), "out_cubic"), (0.65, V(-4, 4, -6), "in_out_cubic"), (1.05, V(-4, 0, -6)), (T, z, "in_out_cubic")]))
    a.pos("top", Curve([(0, z), (0.6, V(0, 0.05, 0), "out_cubic"), (1.1, V(0, 0.04, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("ring", Curve([(0, z), (0.5, V(0, 270, 0), "in_quad"), (1.1, V(0, 720, 0), "in_out_cubic"), (T, V(0, 720, 0))]))
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.30, V(0, 0, -0.03), "in_out_cubic"), (1.0, V(0, 0, -0.03)), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


def clip_surrender(rig):
    """Stagger, a one-knee KNEEL (left foot planted, right knee down), torso folds, head bowed, fists open onto the plinth;
    the prism ring sinks and dims (shrinks) over the lowered head."""
    a = _anim(rig)
    T = 2.4
    z = V(0, 0, 0)
    sk = a.sk
    L1 = float(np.linalg.norm(sk.rest[sk.ix["shin_R"]] - sk.rest[sk.ix["thigh_R"]]))
    L2 = float(np.linalg.norm(sk.rest[sk.ix["foot_R"]] - sk.rest[sk.ix["shin_R"]]))
    KNEE_Y = 0.295
    DROP = JOINTS["hip_L"][1] - (KNEE_Y + L1)
    PZ = 0.05
    a.pos("body", Curve([(0, z), (0.30, V(0, -0.012, -0.040), "out_cubic"), (0.55, V(0, -0.020, -0.020), "in_out_cubic"), (1.38, V(0, -DROP, PZ), "in_out_cubic"),
                         (1.60, V(0, -DROP + 0.007, PZ), "out_cubic"), (1.95, V(0, -DROP, PZ), "in_out_cubic"), (T, V(0, -DROP - 0.004, PZ), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.30, V(-6, 0, 0), "out_cubic"), (0.55, z, "in_out_cubic"), (1.38, V(3, 0, -2), "in_out_cubic"), (T, V(4, 0, -2), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.30, V(-3, 0, 0), "out_cubic"), (0.9, V(5, 0, 0), "in_out_cubic"), (1.6, V(10, 0, 0), "in_out_cubic"), (T, V(12, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.30, V(-2, 0, 0), "out_cubic"), (0.9, V(5, 0, 0), "in_out_cubic"), (1.7, V(8, 0, 0), "in_out_cubic"), (T, V(9, 0, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.30, V(-4, 0, 0), "out_cubic"), (1.0, V(8, 0, 0), "in_out_cubic"), (1.75, V(14, 0, 0), "in_out_cubic"), (T, V(15, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.30, V(-10, 0, 0), "out_cubic"), (1.0, V(10, 0, 0), "in_out_cubic"), (1.75, V(20, 2, 3), "in_out_cubic"), (T, V(22, 2, 4), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (1.0, V(0, 0, 4), "in_out_cubic"), (T, V(0, 0, 6))]))
    a.rot("clavicle_L", Curve([(0, z), (1.0, V(0, 0, -4), "in_out_cubic"), (T, V(0, 0, -6))]))
    # arms: stagger, then both forearms reach down and forward, fists open (wrists flatten) onto the plinth / thigh
    for s, sg in (("L", 1), ("R", -1)):
        a.rot(f"arm_{s}", Curve([(0, z), (0.30, V(6, 0, sg * -3), "out_cubic"), (0.85, V(-10, 0, sg * -4), "in_out_cubic"), (1.7, V(-26, 0, sg * -3), "in_out_cubic"), (T, V(-28, 0, sg * -3), "in_out_cubic")]))
        a.rot(f"hand_{s}", Curve([(0, z), (0.85, V(-16, 0, 0), "in_out_cubic"), (1.7, V(-34, 0, 0), "in_out_cubic"), (T, V(-36, 0, 0), "in_out_cubic")]))
        a.rot(f"wrist_{s}", Curve([(0, z), (0.30, V(25, 0, 0), "out_cubic"), (1.7, V(34, 0, 0), "in_out_cubic"), (T, V(36, 0, 0), "in_out_cubic")]))
    # legs: left foot steps forward and plants, right foot slides back to lie flat behind the right knee, instep down
    ankL = V(0.0, 0.0, PZ + 0.165 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.55, z), (0.85, ankL + V(0, 0.06, -0.06), "in_out_cubic"), (1.15, ankL, "in_out_cubic"), (T, ankL)]),
               rot=Curve([(0, z), (0.55, z), (0.70, V(18, 0, 0), "in_out_cubic"), (0.95, V(-10, 0, 0), "in_out_cubic"), (1.15, z, "in_out_cubic"), (T, z)]))
    ankR = V(0.0, KNEE_Y - JOINTS["ankle_L"][1], PZ - L2 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.60, z), (1.00, ankR + V(0, 0.10, 0.10), "in_out_cubic"), (1.38, ankR, "in_out_cubic"), (T, ankR)]),
               rot=Curve([(0, z), (0.60, z), (1.00, V(95, 0, 0), "in_out_cubic"), (1.38, V(172, 0, 0), "in_out_cubic"), (T, V(172, 0, 0))]))
    # crown: jolts, sinks toward the bowed helm, ring slows and shrinks (dims)
    a.pos("top", Curve([(0, z), (0.30, V(0, 0.03, 0), "out_cubic"), (1.6, V(0, 0.02, 0.12), "in_out_cubic"), (T, V(0, 0.015, 0.13), "in_out_cubic")]))
    a.rot("top", Curve([(0, z), (1.6, V(36, 0, 0), "in_out_cubic"), (T, V(40, 0, 0), "in_out_cubic")]))
    a.rot("ring", Curve([(0, z), (0.30, V(0, 25, 0), "out_cubic"), (1.6, V(0, 70, 0), "out_cubic"), (T, V(0, 90, 0), "out_cubic")]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


def make_clips(rig):
    import pickle
    cache = os.environ.get("FORGE_CLIPCACHE")
    if cache and os.path.exists(cache):
        with open(cache, "rb") as fh:
            return pickle.load(fh)
    out = []
    for name, fn in (("Idle", clip_idle), ("Move", clip_move), ("Attack", clip_attack), ("HitReact", clip_hit), ("Victory", clip_victory),
                     ("Taunt", clip_taunt), ("Surrender", clip_surrender)):
        a, dur, loop, fps, keep = fn(rig)
        out.append(a.bake(name, dur, loop=loop, fps=fps, keep_times=keep))
    if cache:
        with open(cache, "wb") as fh:
            pickle.dump(out, fh)
    return out


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "king", rig, make_clips(rig), impact_time=1.20, strike_range=0.60, attack_style="melee", seed=8)
    rc.pedestal_parts(p)
    lower_body(p)
    torso(p)
    cape(p)
    pauldrons(p)
    arms(p)
    head(p)
    crown(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
