"""rime_queen - Rime Pale Tide Queen: a tall spectral queen in obsidian gown-armour whose hem frays into drifting ice,
a translucent ice veil, silver wire lacing, a dim crescent halo floating BEHIND the head, one crystal wing shoulder, frost
trailing across the floor.  She is crowned with an OPEN coronet of nine bright ice-crystal tines (five tall, four short) and a
small glowing orb in the centre: no cross, no arches, no cage, so she can never be mistaken for the Rime king.
Her great crystal glaive is pulled out of the air in Attack (`weapon_summon`, scale 0 everywhere else).
Built from docs/art/rime_queen.md on the full humanoid skeleton: smooth-skinned limbs/torso/neck/cape/hair, a gown skinned onto
pelvis + two skirt compression bones + thighs (the kneel gathers it instead of sinking it into the plinth), rigid armour plates,
procedural IK / glide / strike animation baked to dense tracks."""
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

ASSET_ID = "rime_queen"
V = lambda *x: np.array(x, dtype=float)       # noqa: E731
DARK = lambda v: (lambda P: np.full(len(P), v))       # noqa: E731

# ======================================================================================= rig
JOINTS = dict(pelvis=(0, 0.78, 0), spine=(0, 0.90, 0), chest=(0, 1.02, 0), neck=(0, 1.15, 0.005), head=(0, 1.19, 0.01), top=(0, 1.40, -0.14),
              clavicle_L=(0.07, 1.13, 0), shoulder_L=(0.19, 1.12, 0), elbow_L=(0.23, 0.93, 0.04), wrist_L=(0.24, 0.80, 0.17),
              hip_L=(0.06, 0.80, 0), knee_L=(0.07, 0.56, 0.07), ankle_L=(0.065, 0.27, 0.04), toe_L=(0.065, 0.245, 0.12))
J_ = lambda k: np.array(JOINTS[k] if k in JOINTS else ((-JOINTS[k[:-1] + "L"][0],) + tuple(JOINTS[k[:-1] + "L"][1:])), dtype=float)   # noqa: E731
CAPE = [(0, 1.10, -0.16), (0, 0.78, -0.22), (0, 0.50, -0.28)]
HAIR = [(0.0, 1.30, -0.070), (0.0, 1.16, -0.140), (0.0, 1.02, -0.190)]
WR0, WL0 = J_("wrist_R"), J_("wrist_L")
GRIP = WR0.copy()                                   # weapon_summon origin = the right palm on the shaft
A_S = V(0.0, -1.0, 0.0)                             # shaft axis at rest: hand -> blade (straight down)
E_S = V(0.0, 0.0, 1.0)                              # cutting-edge normal at rest (blade hooks toward +Z)


def make_rig() -> Rig:
    r = humanoid_rig(JOINTS, cape=CAPE)
    r.bones["cape_1"].parent = "chest"              # the mist cloak hangs from the shoulders; `top` is only the floating halo
    prev = "head"
    for i, pp in enumerate(HAIR, 1):
        r.add(f"hair_{i}", prev, pp)
        prev = f"hair_{i}"
    r.add("skirt_1", "body", (0, 0.58, 0))          # gown compression bones: the kneel gathers the skirt instead of sinking it
    r.add("skirt_2", "body", (0, 0.34, 0))
    r.node("weapon_summon", "wrist_R", tuple(GRIP))
    r.socket("socket_weapon_R", "wrist_R", tuple(GRIP))
    r.socket("socket_cast", "top", (0, 1.28, -0.14))
    r.socket("socket_impact", "body", (0, 0.70, 0.70))
    r.socket("socket_head", "head", (0, 1.58, 0))
    return r


LEG_SKIN = {s: Skin.chain([f"thigh_{s}", f"shin_{s}", f"foot_{s}"], pre="body", tip=tuple(J_(f"toe_{s}")), zone=0.4) for s in "LR"}
ARM_SKIN = {s: Skin.chain([f"arm_{s}", f"hand_{s}"], pre=f"clavicle_{s}", tip=tuple(J_(f"wrist_{s}")), zone=0.42) for s in "LR"}
TORSO_SKIN = Skin.chain(["body", "spine", "chest"], tip=JOINTS["neck"], zone=0.45)
NECK_SKIN = Skin.chain(["neck", "head"], pre="chest", tip=(0, 1.28, 0.02), zone=0.4)
CAPE_SKIN = Skin.chain(["cape_1", "cape_2", "cape_3"], pre="chest", tip=(0.0, 0.30, -0.30), zone=0.4)
HAIR_SKIN = Skin.gradient(Skin.rigid("head"), Skin.chain(["hair_1", "hair_2", "hair_3"], pre="head", tip=(0.0, 0.90, -0.215), zone=0.45), axis=1, v0=1.36, v1=1.25)
SKIRT_SKIN = Skin.nearest([("body", J_("pelvis"), J_("spine")), ("skirt_1", (0, 0.58, 0), (0, 0.58, 0)), ("skirt_2", (0, 0.34, 0), (0, 0.34, 0)),
                           ("thigh_L", J_("hip_L"), J_("knee_L")), ("thigh_R", J_("hip_R"), J_("knee_R"))], tau=0.07, bias={"thigh_L": 0.55, "thigh_R": 0.55})
WAIST_SKIN = Skin.gradient(Skin.rigid("body"), SKIRT_SKIN, axis=1, v0=0.86, v1=0.80)


def lerp3(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


# ======================================================================================= gown
SK_Y0 = [0.26, 0.34, 0.50, 0.66, 0.80, 0.88]
SK_R0 = [0.215, 0.222, 0.200, 0.160, 0.120, 0.100]
SK_YS = [0.26, 0.30, 0.36, 0.44, 0.54, 0.64, 0.74, 0.82, 0.88]


def sk_r(y):
    return float(np.interp(y, SK_Y0, SK_R0))


def legs(p: Piece):
    for s, nm in ((+1, "L"), (-1, "R")):
        hip, knee, ank, toe = J_(f"hip_{nm}"), J_(f"knee_{nm}"), J_(f"ankle_{nm}"), J_(f"toe_{nm}")
        core = limb_tube([hip + [0, 0.02, 0], lerp3(hip, knee, 0.5), knee, lerp3(knee, ank, 0.5), ank + [0, 0.02, 0]],
                         [0.058, 0.052, 0.044, 0.038, 0.034], joints=[knee], spacing=0.06, joint_spacing=0.026, joint_zone=0.06, sides=7, cap=None, up=(0, 0, 1))
        p.add(f"leg_{nm}", core, "RH_Armour", None, skin=LEG_SKIN[nm], uv_scale=2, tint=DARK(0.7))
        boot = g.superellipsoid((0.034, 0.028, 0.105), 0.4, 0.5, 4, 9).translated(s * 0.065, 0.258, 0.115)
        p.add(f"boot_{nm}", boot, "RH_Obsidian", f"foot_{nm}")
        p.add(f"boot_spike_{nm}", spikes([((s * 0.065, 0.262, 0.205), (0.0, 0.08, 1.0), 0.06, 0.013)], seed=3 + (s > 0), flat=0.3, sides=5), "RH_Ice", f"foot_{nm}", lod1=None)
        gp = [lerp3(knee, ank, 0.9) + [0, 0, 0.004], lerp3(knee, ank, 0.5) + [0, 0, 0.006], lerp3(knee, ank, 0.12) + [0, 0, 0.004]]
        p.add(f"greave_{nm}", g.tube(gp, [0.040, 0.044, 0.046], sides=7, samples=2, cap=None, up=(0, 0, 1)), "RH_Obsidian", f"shin_{nm}")
        cop = g.superellipsoid((0.040, 0.036, 0.034), 0.5, 0.6, 3, 8).translated(*(knee + [0, 0.0, 0.040]))
        p.add(f"knee_{nm}", cop, "RH_Obsidian", f"shin_{nm}")


def gown(p: Piece):
    K = 36
    th = np.arange(K) * TAU / K
    rings = []
    for i, y in enumerate(SK_YS):
        r = sk_r(y)
        fold = 1 + 0.030 * np.cos(8 * th + 0.5 * i) * (1 - i / 8.0)
        rings.append(np.stack([r * fold * np.sin(th), np.full(K, y), r * fold * np.cos(th)], 1))
    inner = g.loft(np.stack(rings), closed=True, crease=38.0, cap_start=True, cap_end=True)
    p.add("gown_inner", inner, "RH_Armour", None, skin=SKIRT_SKIN, uv_scale=2, tint=lambda P: 0.5 + 0.5 * smoothstep(0.26, 0.8, P[:, 1]))
    # eight tall obsidian panels, V-pointed lower edge, alternating lengths, flaring
    panels, wire = [], []
    for k in range(8):
        a0 = k * 45.0 + 8
        half = 0.19 if k % 2 == 0 else 0.17
        bot = 0.265 if k % 2 == 0 else 0.34
        rows, cols = 11, 6
        grid = []
        for ci in range(cols):
            u = ci / (cols - 1)
            ang = math.radians(a0) + (u - 0.5) * 2 * half
            ybot = bot + 0.12 * abs(2 * u - 1) ** 1.2
            col = []
            for ri in range(rows):
                v = ri / (rows - 1)
                y = 0.88 - (0.88 - ybot) * v
                r = sk_r(max(y, 0.26)) + 0.014 + 0.022 * v ** 1.5
                col.append((r * math.sin(ang), y, r * math.cos(ang)))
            grid.append(col)
        grid = np.array(grid)
        panels.append(g.loft(grid[:, ::-1], closed=False, crease=40, v_tile=0.25, u_tile=0.25).flipped())
        edge = [tuple(grid[ci, -1]) for ci in range(cols)]
        wire.append(g.tube([(e[0] * 1.004, e[1] + 0.003, e[2] * 1.004) for e in edge], 0.0042, sides=4, samples=1, cap="round", cap_steps=1, smooth=False))
    p.add("gown_panels", merge(panels), "RH_Obsidian", None, skin=SKIRT_SKIN, uv_scale=2)
    p.add("gown_panel_wire", merge(wire), "RH_Silver", None, skin=SKIRT_SKIN, lod1=None, tint=DARK(0.6))
    # tide-wave trim: scalloped silver arcs in three rows
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
    p.add("tide_trim", merge(waves), "RH_Silver", None, skin=SKIRT_SKIN, lod1=None, tint=DARK(0.6))
    # fraying hem tongues (translucent ice) tilted out so they lie across the plinth; a second shorter row between them
    rng = np.random.default_rng(4)
    tg = []
    for k in range(16):
        a = k * TAU / 16 + 0.1
        ln = 0.09 + 0.07 * rng.random()
        poly = np.array([(-0.03, 0), (0.03, 0), (0.02, -ln * 0.6), (0.0, -ln), (-0.02, -ln * 0.6)])
        tg.append(g.extrude(poly, 0.005, 0.0012, 1).rotated(-38, 0, 0).translated(0, 0.345, 0.205 + 0.01 * (k % 2)).rotated(0, math.degrees(a), 0))
    p.add("hem_tongues", merge(tg), "RH_Ice", None, skin=SKIRT_SKIN)
    tg2 = []
    for k in range(12):
        a = (k + 0.5) * TAU / 12 + 0.4
        ln = 0.05 + 0.04 * rng.random()
        poly = np.array([(-0.018, 0), (0.018, 0), (0.0, -ln)])
        tg2.append(g.extrude(poly, 0.004, 0.001, 1).rotated(-55, 0, 0).translated(0, 0.30, 0.215).rotated(0, math.degrees(a), 0))
    p.add("hem_tongues_2", merge(tg2), "RH_Ice", None, skin=SKIRT_SKIN, lod1=None)
    # trailing ice train dragging behind (rear)
    train = cluster((0.0, 0.265, -0.19), (0.0, 0.35, -1.0), 7, (0.10, 0.22), (0.020, 0.040), spread=0.10, tilt=20, seed=7, flat=0.3)
    p.add("ice_train", train, "RH_Ice", None, skin=SKIRT_SKIN)
    # floor frost trail: ragged fan + fringe of tiny crystals (a decal on the plinth: stays on root)
    fan = g.extrude_plane(np.array([(0.0, -0.10), (0.20, -0.25), (0.15, -0.34), (0.05, -0.30), (-0.02, -0.36), (-0.12, -0.31), (-0.21, -0.27)]), 0.006, "XZ", bevel=0.002, bevel_segments=1)
    p.add("floor_frost", fan.translated(0, 0.2255, 0), "RH_Frost", "root", lod1=None, tint=DARK(0.5))
    fr = spikes([((0.2 * math.sin(a), 0.226, -0.30 + 0.04 * abs(math.sin(2 * a)) - 0.1 * (1 - math.cos(a))), (0, 1, 0), 0.025 + 0.015 * (k % 2), 0.007)
                 for k, a in enumerate(np.linspace(-1.2, 1.2, 14))], seed=19, flat=0.2, sides=4, tip=0.5)
    p.add("floor_frost_crystals", fr, "RH_Ice", "root", lod1=None)
    # belt of linked plates
    belt = g.lathe([(0.098, 0.84), (0.106, 0.845), (0.106, 0.880), (0.098, 0.885)], 14, crease=30)
    p.add("belt", belt, "RH_Obsidian", "body")
    diamonds = [g.extrude(np.array([(0, -0.028), (0.020, 0), (0, 0.028), (-0.020, 0)]), 0.012, 0.003, 1).translated(0, 0.862, 0.108).rotated(0, k * 72, 0) for k in range(5)]
    p.add("belt_diamonds", merge(diamonds), "RH_Silver", "body", tint=DARK(0.7))
    # silver front lacing from the belt down the gown, a hanging chain with ice shards, ice clusters at the panel points
    lace = []
    for k, y in enumerate(np.linspace(0.80, 0.46, 11)):
        r = sk_r(y) + 0.040 + 0.022 * ((0.88 - y) / 0.62) ** 1.5
        w = 0.030 * (1.0 + 0.5 * (0.88 - y))
        lace.append(g.tube([(-w, y + 0.012, r), (0.0, y, r + 0.003), (w, y + 0.012, r)], 0.0022, sides=3, samples=1, cap="round", cap_steps=1, smooth=True))
        lace.append(g.tube([(-w, y - 0.012, r), (0.0, y, r + 0.003), (w, y - 0.012, r)], 0.0028, sides=3, samples=1, cap="round", cap_steps=1, smooth=True))
    lace.append(g.tube([(-0.030, 0.82, sk_r(0.82) + 0.036), (-0.036, 0.62, sk_r(0.62) + 0.062), (-0.040, 0.44, sk_r(0.44) + 0.078)], 0.0032, sides=3, samples=2, cap="round", cap_steps=1, smooth=True))
    lace.append(g.tube([(0.030, 0.82, sk_r(0.82) + 0.036), (0.036, 0.62, sk_r(0.62) + 0.062), (0.040, 0.44, sk_r(0.44) + 0.078)], 0.0032, sides=3, samples=2, cap="round", cap_steps=1, smooth=True))
    p.add("gown_lacing", merge(lace), "RH_Silver", None, skin=SKIRT_SKIN, lod1=None, tint=DARK(0.28))
    ang = math.radians(-38)
    cp = lambda y, rr: (rr * math.sin(ang), y, rr * math.cos(ang))                       # noqa: E731
    chain = rc.zigzag(cp(0.835, 0.150), cp(0.56, sk_r(0.56) + 0.050), 8, 0.008, r=0.0040, side=(math.cos(ang), 0, -math.sin(ang)))
    p.add("gown_chain", chain, "RH_Silver", None, skin=SKIRT_SKIN, lod1=None, tint=DARK(0.55))
    p.add("gown_chain_shards", spikes([(cp(0.57, sk_r(0.57) + 0.050), (math.sin(ang) * 0.3, -1.0, math.cos(ang) * 0.3), 0.085, 0.012), (cp(0.64, sk_r(0.64) + 0.048), (math.sin(ang) * 0.3, -1.0, math.cos(ang) * 0.3), 0.06, 0.010),
                                       (cp(0.72, sk_r(0.72) + 0.044), (math.sin(ang) * 0.3, -1.0, math.cos(ang) * 0.3), 0.045, 0.009)], seed=8, flat=0.3, sides=4, tip=0.5), "RH_Ice", None, skin=SKIRT_SKIN, lod1=None)
    pts = []
    for k in range(8):
        a0 = math.radians(k * 45.0 + 8)
        bot = 0.265 if k % 2 == 0 else 0.34
        rr = sk_r(max(bot, 0.26)) + 0.030
        base = ((rr + 0.01) * math.sin(a0), bot + 0.03, (rr + 0.01) * math.cos(a0))
        pts.append(cluster(base, (math.sin(a0) * 0.8, -0.35, math.cos(a0) * 0.8), 3, (0.05, 0.10), (0.010, 0.016), spread=0.02, tilt=30, seed=40 + k, flat=0.3, sides=4))
    p.add("hem_points", merge(pts), "RH_Ice", None, skin=SKIRT_SKIN, lod1=None)
    # knee-bone spikes pushing through the cloth
    for s in (-1, 1):
        p.add(f"knee_spikes_{'L' if s > 0 else 'R'}", cluster((s * 0.08, 0.50, 0.20), (s * 0.3, 0.4, 1.0), 2, (0.05, 0.08), (0.011, 0.015), spread=0.02, tilt=22, seed=3 + (s > 0), flat=0.3, sides=4),
              "RH_Ice", None, skin=SKIRT_SKIN)


# ======================================================================================= bodice, shoulders, arms
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


def bodice(p: Piece):
    t = limb_tube([(0, 0.84, 0), (0, 0.98, 0), (0, 1.12, 0)], [0.092, 0.108, 0.128], joints=[(0, 0.90, 0), (0, 1.02, 0)], spacing=0.04, joint_spacing=0.02,
                  joint_zone=0.06, sides=12, cap="round", cap_steps=1, ellipse=(0.62, 1.0), up=(0, 0, 1))
    p.add("torso", t, "RH_Armour", None, skin=TORSO_SKIN, uv_scale=2, tint=DARK(0.7))
    yoke = g.superellipsoid((0.165, 0.040, 0.085), 0.55, 0.7, 5, 12).translated(0, 1.125, 0.0)
    p.add("yoke", yoke, "RH_Armour", "chest", uv_scale=2)

    def qshell(specs, K=14):
        return g.loft(np.stack([qring(y, gr, K, rd) for y, gr, rd in specs]), closed=True, crease=34)
    for i, y0 in enumerate((0.855, 0.885, 0.915)):
        gr = 0.004 + 0.003 * (2 - i)
        p.add(f"rib_lame_{i}", qshell([(y0, gr - 0.004, 0), (y0 + 0.006, gr + 0.004, 0), (y0 + 0.030, gr + 0.005, 0), (y0 + 0.036, gr - 0.003, 0)]), "RH_Obsidian", None, skin=TORSO_SKIN)
    ridge = lambda y: 0.014 * smoothstep(0.95, 1.02, y) * (1 - smoothstep(1.08, 1.14, y))      # noqa: E731
    ys = [0.935, 0.942, 0.99, 1.04, 1.09, 1.125, 1.148]
    gs = [0.002, 0.009, 0.013, 0.014, 0.013, 0.009, 0.0]
    cu = g.loft(np.stack([qring(y, a_, 14, ridge(y)) for y, a_ in zip(ys, gs)]), closed=True, crease=30)
    cu = cu.dented(3, 0.03, 0.002, seed=5)
    p.add("bodice_plate", cu, "RH_Obsidian", None, skin=TORSO_SKIN)
    p.add("bodice_lip", g.tube(qring(0.938, 0.0075, 18), 0.0055, sides=4, samples=1, cap=None, smooth=False, closed=True, up=(0, 1, 0)), "RH_Silver", None, skin=TORSO_SKIN, lod1=None, tint=DARK(0.45))
    p.add("bodice_frost", frost_layer(cu, 0.006, min_ny=0.5, cover=0.28, seed=4), "RH_Frost", None, skin=TORSO_SKIN, lod1=None, tint=DARK(0.5))
    cw = [(0.0, y, float(np.interp(y, QY, QF)) + 0.016 + float(ridge(y))) for y in np.linspace(0.945, 1.12, 8)]
    p.add("bodice_center_wire", g.tube(cw, 0.0032, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "RH_Silver", None, skin=TORSO_SKIN, lod1=None, tint=DARK(0.45))
    studs = []
    for y in (0.985, 1.035, 1.085):
        z = float(np.interp(y, QY, QF)) + 0.020 + float(ridge(y))
        for a_ in (0, 60, 120):
            studs.append(g.extrude(g.rect_poly(0.024, 0.0050), 0.004, 0.001, 1).rotated(0, 0, a_).translated(0, y, z))
    p.add("bodice_studs", merge(studs), "RH_Silver", None, skin=TORSO_SKIN, lod1=None, tint=DARK(0.55))
    lace = []
    for k in range(5):
        y = 0.955 + 0.030 * k
        z = float(np.interp(y, QY, QF)) + 0.016 + float(ridge(y))
        w = 0.070 * (0.7 + 0.3 * (k % 2))
        lace.append(g.tube([(-w, y - 0.010, z - 0.01), (0.0, y + 0.004, z + 0.002), (w, y - 0.010, z - 0.01)], 0.0026, sides=3, samples=1, cap="round", cap_steps=1, smooth=True))
    p.add("lacing", merge(lace), "RH_Silver", None, skin=TORSO_SKIN, lod1=None, tint=DARK(0.4))
    # gorget crystals around the neck: sides and back only (the veil hangs in front)
    col = []
    for k, a in enumerate(np.linspace(math.radians(65), math.radians(295), 6)):
        col.append((((0.078 * math.sin(a)), 1.135, 0.078 * math.cos(a)), (math.sin(a) * 0.45, 1.0, math.cos(a) * 0.45), 0.05 + 0.06 * ((k * 3) % 4) / 3, 0.0100))
    p.add("collar_crystals", spikes(col, seed=3, flat=0.28, sides=5, tip=0.42), "RH_Ice", "chest")
    # crystal wing on the left shoulder: five fanned shards, tallest tip 1.30
    wing = []
    for k, (ln, rd, fan) in enumerate(((0.10, 0.020, -34), (0.15, 0.026, -14), (0.19, 0.032, 6), (0.15, 0.026, 26), (0.095, 0.020, 44))):
        d = unit((0.5 + math.sin(math.radians(fan)) * 0.9, 1.0, -0.2))
        wing.append(((0.20, 1.14, -0.03 * (k - 2) * 0.4), d, ln, rd))
    p.add("wing_L", spikes(wing, seed=33, flat=0.3, sides=6, tip=0.38, bend=0.06), "RH_Ice", "clavicle_L")
    p.add("wing_L_secondary", spikes([((0.24, 1.135, -0.04), unit((0.9, 0.8, -0.4)), 0.09, 0.016), ((0.16, 1.14, -0.05), unit((0.2, 1.0, -0.5)), 0.11, 0.016),
                                      ((0.27, 1.12, 0.03), unit((1.0, 0.5, 0.1)), 0.08, 0.014)], seed=41, flat=0.3, sides=5, tip=0.42), "RH_Ice", "clavicle_L", lod1=None)
    pl_L = g.superellipsoid((0.065, 0.026, 0.066), 0.5, 0.7, 4, 10).translated(0.19, 1.12, 0.0)
    pl_L2 = g.superellipsoid((0.058, 0.020, 0.058), 0.5, 0.7, 4, 10).rotated(0, 0, -20).translated(0.21, 1.09, 0.0)
    p.add("pauldron_L", merge([pl_L, pl_L2]), "RH_Obsidian", "clavicle_L")
    pr = g.superellipsoid((0.058, 0.025, 0.058), 0.5, 0.7, 4, 10).rotated(0, 0, 8).translated(-0.19, 1.14, 0.0)
    p.add("shoulder_R", pr, "RH_Obsidian", "clavicle_R")
    p.add("shoulder_R_frost", frost_layer(pr, 0.006, min_ny=0.5, cover=0.22, seed=2), "RH_Frost", "clavicle_R", lod1=None, tint=DARK(0.30))
    neck = limb_tube([(0, 1.13, 0.0), (0, 1.18, 0.008), (0, 1.235, 0.012)], [0.032, 0.029, 0.026], joints=[(0, 1.17, 0.006)], spacing=0.04, joint_spacing=0.02, joint_zone=0.04,
                     sides=7, cap=None, up=(0, 0, 1))
    p.add("neck", neck, "RH_Bone", None, skin=NECK_SKIN, uv_scale=2)


def arms(p: Piece):
    for s, nm in ((+1, "L"), (-1, "R")):
        sh, el, wr = J_(f"shoulder_{nm}"), J_(f"elbow_{nm}"), J_(f"wrist_{nm}")
        core = limb_tube([sh + [0, -0.005, 0], (s * 0.215, 1.03, 0.02), el, (s * 0.24, 0.865, 0.115), wr + [0, 0.005, -0.005]], [0.034, 0.029, 0.025, 0.021, 0.016], joints=[el],
                         spacing=0.04, joint_spacing=0.018, joint_zone=0.05, sides=7, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"arm_core_{nm}", core, "RH_Armour", None, skin=ARM_SKIN[nm], uv_scale=2, tint=DARK(0.7))
        up_ = [(s * 0.19, 1.12, 0), (s * 0.22, 0.98, 0.02), (s * 0.23, 0.93, 0.04)]
        fore = [(s * 0.23, 0.93, 0.04), (s * 0.24, 0.86, 0.12), (s * 0.24, 0.80, 0.17)]
        p.add(f"arm_lames_{nm}", rc.limb_lames(up_, [0.034, 0.027, 0.024], [0.28, 0.58], h=0.034, sweep=240, grow=0.005, seg=7), "RH_Obsidian", f"arm_{nm}")
        p.add(f"vambrace_{nm}", rc.limb_lames(fore, [0.026, 0.021, 0.016], [0.25, 0.55, 0.8], h=0.036, sweep=250, grow=0.005, seg=7), "RH_Obsidian", f"hand_{nm}")
        slv = g.tube([(s * 0.19, 1.10, 0.0), (s * 0.21, 1.00, 0.02), (s * 0.235, 0.90, 0.05)], [0.040, 0.044, 0.058], sides=8, samples=2, cap=None, up=(0, 0, 1))
        hem = [(s * 0.235 + 0.050 * math.sin(a), 0.90 - 0.03 * (k % 2) - 0.01, 0.05 + 0.050 * math.cos(a)) for k, a in enumerate(np.linspace(0, TAU, 12, endpoint=False))]
        p.add(f"sleeve_{nm}", slv.noised(0.003, 14, 2, seed=3 + (s > 0)), "RH_Cloth", None, skin=ARM_SKIN[nm], uv_scale=2)
        p.add(f"sleeve_ice_{nm}", spikes([((h[0], h[1], h[2]), (h[0] - s * 0.235, -1.0, h[2] - 0.05), 0.045 + 0.02 * (k % 2), 0.006) for k, h in enumerate(hem[::2])],
                                         seed=70 + (s > 0), flat=0.25, sides=4, tip=0.5), "RH_Ice", None, skin=ARM_SKIN[nm], lod1=None)
        fins = g.extrude_plane(np.array([(0.90, 0.06), (0.84, 0.14), (0.86, 0.17), (0.91, 0.10)]), 0.006, "YZ", bevel=0.002, bevel_segments=1).translated(s * 0.262, 0, 0)
        p.add(f"vambrace_fins_{nm}", fins, "RH_Silver", f"hand_{nm}", tint=DARK(0.7))
        p.add(f"arm_wire_{nm}", rc.helix(0.0275, 0.84, 0.88, 1.6, r=0.0030, sides=3, per_turn=7, ax=s * 0.241, az=0.12), "RH_Silver", f"hand_{nm}", lod1=None)
        wrist = np.array([s * 0.245, 0.785, 0.18])
        p.add(f"hand_{nm}", rc.claw_hand(s, wrist, (0.0, -0.55, 1.0), 0.9, 1.05, 1.6), "RH_Bone", f"wrist_{nm}", uv_scale=2)
        claws = spikes([((s * 0.245 + o, 0.745, 0.215), (0, -0.7, 1.0), 0.032, 0.0042) for o in (-0.0135, -0.0045, 0.0045, 0.0135)], seed=60 + (s > 0), flat=0.2, sides=4, tip=0.6)
        p.add(f"claws_{nm}", claws, "RH_Ice", f"wrist_{nm}", lod1=None)


# ======================================================================================= head, veil, coronet, hair
def head(p: Piece):
    skull = g.superellipsoid((0.057, 0.088, 0.061), 0.8, 0.85, 6, 12).noised(0.002, 24, 2, seed=3).rotated(0, 0, 3)
    cheek = [g.superellipsoid((0.011, 0.014, 0.011), 0.6, 0.6, 3, 6).translated(s * 0.030, -0.020, 0.042) for s in (-1, 1)]
    nose = g.superellipsoid((0.007, 0.014, 0.011), 0.6, 0.6, 3, 6).translated(0, -0.005, 0.054)
    p.add("head", merge([skull, nose] + cheek).translated(0, 1.305, 0.01), "RH_Bone", "head", uv_scale=2)
    # dark hair cap over the skull (the face stays open in front) and two locks framing the cheeks
    cap = g.superellipsoid((0.061, 0.090, 0.066), 0.8, 0.85, 5, 12).translated(0, 1.322, -0.014).noised(0.0025, 22, 2, seed=7)
    locks = [g.tube([(s * 0.054, 1.345, 0.016), (s * 0.060, 1.285, 0.022), (s * 0.070, 1.215, 0.010), (s * 0.074, 1.150, -0.012)], [0.010, 0.0095, 0.007, 0.002], sides=5, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
             for s in (-1, 1)]
    p.add("hair_cap", merge([cap] + locks), "RH_Cloth", "head", uv_scale=2, tint=DARK(0.5))
    eyes = [g.extrude(np.array([(-0.009, -0.003), (0.009, 0.001), (0.007, 0.005), (-0.009, 0.002)]) * [s, 1], 0.005, 0.0012, 1).translated(s * 0.027, 1.318, 0.0645) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "RH_Glow", "head", bake=False, lod1="keep")
    vp = np.array([(-0.065, 1.285), (-0.020, 1.290), (0.020, 1.290), (0.065, 1.285), (0.078, 1.20), (0.045, 1.185), (0.030, 1.150), (0.0, 1.175), (-0.030, 1.150), (-0.048, 1.190), (-0.078, 1.20)])
    veil = g.extrude(vp, 0.004, 0.001, 1).subdivided_to(0.04, max_levels=1)

    def vf(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        return np.column_stack([x, y, 0.066 - 0.55 * x * x + z + 0.006 * np.sin(x * 90 + y * 40)])
    p.add("veil", g.warp(veil, vf, 40), "RH_Ice", "head", occluder=False)
    # tresses of dark frosted hair streaming back (chain skin: they trail the head), ice beads at the tips
    strands, beads = [], []
    for k in range(9):
        sx = (k - 4) * 0.0155
        fall = 0.97 - 0.06 * ((k * 5) % 4)
        pts = [(sx * 0.9, 1.352, -0.034), (sx * 1.5, 1.28, -0.098 - 0.010 * (k % 3)), (sx * 2.1 + 0.014 * math.sin(k * 1.7), 1.15 - 0.03 * (k % 3), -0.148 - 0.006 * k),
               (sx * 2.4 + 0.020 * math.sin(k * 2.3), 1.04 - 0.03 * (k % 3), -0.178), (sx * 2.5, fall, -0.192)]
        strands.append(g.tube(pts, [0.0115, 0.0105, 0.0085, 0.0055, 0.0015], sides=5, samples=3, cap="round", cap_steps=1, up=(1, 0, 0)))
        beads.append(((sx * 2.5, fall + 0.004, -0.192), (0.0, -1.0, -0.1), 0.030 + 0.012 * (k % 3), 0.0065))
    p.add("hair", merge(strands), "RH_Cloth", None, skin=HAIR_SKIN, uv_scale=2, tint=DARK(0.55))
    p.add("hair_ice", spikes(beads, seed=8, flat=0.2, sides=4, tip=0.5), "RH_Ice", None, skin=HAIR_SKIN, lod1=None)
    coronet(p)


# the open nine-tine coronet: silver band 1.350-1.405, hex-prism ice tines on it up to 1.550 (5 tall) / 1.515 (4 short), glow orb on a stalk in the centre
TINE_R = 0.090
TINE_Y = 1.405


def coronet(p: Piece):
    band = g.lathe([(0.082, 1.350), (0.088, 1.354), (0.094, 1.364), (0.094, 1.400), (0.088, 1.405), (0.082, 1.400), (0.082, 1.350)], 18, crease=45)
    p.add("crown_band", band, "RH_Silver", "head", tint=DARK(0.30))
    p.add("crown_rims", merge([g.torus(0.0925, 0.0042, 24, 4).translated(0, 1.402, 0), g.torus(0.0865, 0.0038, 24, 4).translated(0, 1.352, 0)]), "RH_Silver", "head", tint=DARK(0.85))
    rva = [math.radians(10 + 20 * k) for k in range(18)]
    p.add("crown_studs", g.instances(g.dome(0.0050, 0.0045, 5, 1), [(0.0945 * math.sin(a), 1.378, 0.0945 * math.cos(a)) for a in rva], [(math.sin(a), 0, math.cos(a)) for a in rva]),
          "RH_Silver", "head", lod1=None, tint=DARK(0.6))
    tall, short = [], []
    for k in range(9):
        a = math.radians(k * 40.0)
        h = 0.145 if k in (0, 2, 4, 5, 7) else 0.110
        pos = (TINE_R * math.sin(a), TINE_Y - 0.002, TINE_R * math.cos(a))
        d = unit((math.sin(math.radians(10)) * math.sin(a), math.cos(math.radians(10)), math.sin(math.radians(10)) * math.cos(a)))
        m = shard(h + 0.002, 0.0225, sides=6, tip=0.46, flat=0.0, taper=0.80, jitter=0.0, seed=1, cap=True).aimed(d, pos)
        (tall if h > 0.12 else short).append(m)
    p.add("crown_tines", merge(tall + short), "RH_Ice", "head", lod1="keep")
    # bright cores inside the translucent prisms: faint cyan on the tall five, frost white on the short four (they read on a dark piece at 60 px)
    cores_t, cores_s = [], []
    for k in range(9):
        a = math.radians(k * 40.0)
        h = 0.145 if k in (0, 2, 4, 5, 7) else 0.110
        pos = (TINE_R * math.sin(a), TINE_Y, TINE_R * math.cos(a))
        d = unit((math.sin(math.radians(10)) * math.sin(a), math.cos(math.radians(10)), math.sin(math.radians(10)) * math.cos(a)))
        m = shard(h * 0.90, 0.0105, sides=6, tip=0.55, flat=0.0, taper=0.7, jitter=0.0, seed=2, cap=False).aimed(d, pos)
        (cores_t if h > 0.12 else cores_s).append(m)
    p.add("crown_cores", merge(cores_t), "RH_Seam", "head", bake=False, lod1="keep")
    p.add("crown_cores_short", merge(cores_s), "RH_Frost", "head", bake=False, lod1="keep", tint=DARK(0.85))
    # dark lining inside the band (the bright tines read against it) + the small cap the orb stands on
    p.add("crown_lining", g.lathe([(0, 1.396), (0.080, 1.396), (0.082, 1.402), (0.0, 1.404)], 18, crease=60), "RH_Armour", "head", uv_scale=2, lod1=None)
    p.add("crown_stalk", g.tube([(0, 1.404, 0), (0, 1.456, 0), (0, 1.508, 0)], [0.0070, 0.0058, 0.0058], sides=6, samples=1, cap=None, smooth=False), "RH_Silver", "head", tint=DARK(0.7))
    p.add("crown_orb_bezel", g.torus(0.0215, 0.0030, 14, 4).translated(0, 1.510, 0), "RH_Silver", "head", lod1=None, tint=DARK(0.7))
    p.add("crown_orb", g.superellipsoid((0.020, 0.020, 0.020), 1.0, 1.0, 5, 12).translated(0, 1.528, 0), "RH_Glow", "head", bake=False, lod1="keep")


# ======================================================================================= halo (dim crescent behind the head)
HALO_C = (0.0, 1.28)
HALO_Z = -0.14


def halo(p: Piece):
    cx, cy = HALO_C
    ts = np.linspace(15, 165, 17)
    ro = 0.23
    outer = [(cx + ro * math.cos(math.radians(t)), cy + ro * math.sin(math.radians(t))) for t in ts]
    inner = []
    for t in ts[::-1]:
        w = 0.018 + 0.034 * (math.sin(math.radians((t - 15) / 150 * 180)) ** 0.7)
        inner.append((cx + (ro - w) * math.cos(math.radians(t)), cy + (ro - w) * math.sin(math.radians(t))))
    cr = g.extrude(np.array(outer + inner), 0.026, 0.005, 1).translated(0, 0, HALO_Z)
    p.add("halo", cr, "RH_Obsidian", "top", uv_scale=2)
    p.add("halo_frost", frost_layer(cr, 0.005, min_ny=0.6, cover=0.2, seed=3), "RH_Frost", "top", lod1=None, tint=DARK(0.22))
    edge = g.tube([(cx + (ro + 0.002) * math.cos(math.radians(t)), cy + (ro + 0.002) * math.sin(math.radians(t)), HALO_Z + 0.008) for t in np.linspace(17, 163, 14)], 0.0035, sides=4, samples=1,
                  cap="round", cap_steps=1, smooth=True)
    p.add("halo_edge_wire", edge, "RH_Silver", "top", lod1=None, tint=DARK(0.22))
    th = []
    for k in range(9):
        t = 24 + k * 16.5
        pos = (cx + (ro - 0.004) * math.cos(math.radians(t)), cy + (ro - 0.004) * math.sin(math.radians(t)), HALO_Z)
        th.append((pos, (math.cos(math.radians(t)), math.sin(math.radians(t)), 0.0), 0.030 + 0.034 * ((k * 5) % 3) / 2, 0.0095))
    p.add("halo_thorns", spikes(th, seed=12, flat=0.2, sides=4, tip=0.5), "RH_Ice", "top", tint=DARK(0.30))
    arc = g.tube([(cx + 0.208 * math.cos(math.radians(t)), cy + 0.208 * math.sin(math.radians(t)), HALO_Z + 0.014) for t in np.linspace(40, 140, 12)], 0.0036, sides=4, samples=1,
                 cap="round", cap_steps=1, smooth=True)
    p.add("halo_glow", arc, "RH_Seam", "top", bake=False, lod1="keep")
    orb = spikes([((cx + 0.245 * math.cos(math.radians(t)), cy + 0.17 * math.sin(math.radians(t)) - 0.03, HALO_Z), unit((math.cos(math.radians(t)), 0.3, 0.1)), 0.05, 0.010) for t in (4, 176, 96)],
                 seed=15, flat=0.2, sides=4, tip=0.5)
    p.add("halo_orbit_shards", orb, "RH_Ice", "top", lod1=None, tint=DARK(0.30))


def cape(p: Piece):
    R, K = 11, 13
    rings, tips = [], []
    for r in range(R):
        v = r / (R - 1)
        row = []
        for k in range(K):
            u = k / (K - 1)
            y = 1.14 - 0.78 * v
            if r >= R - 2:
                y -= (0.05 if r == R - 1 else 0.015) * (k % 2) * (0.7 + 0.3 * ((k * 5) % 3) / 2)
            xw = 0.14 + 0.08 * v ** 0.8
            x = -xw + 2 * xw * u
            z = -0.118 - 0.07 * v ** 1.3 + 0.016 * math.sin(u * TAU * 3.0 + 0.6) * (0.35 + v)
            z = min(z, -(sk_r(max(y, 0.26)) * (1 - 0.5 * (x / (xw + 1e-9)) ** 2) + 0.045)) if y < 0.86 else z
            row.append((x, y, z))
        rings.append(row)
        if r == R - 1:
            tips = [row[k] for k in range(1, K, 2)]
    edge = []
    for kk in (0, K - 1):
        edge.append(g.tube([(rings[r][kk][0], rings[r][kk][1], rings[r][kk][2] - 0.004) for r in range(0, R - 1)], 0.0034, sides=4, samples=1, cap="round", cap_steps=1, smooth=True))
    p.add("cape_edge_wire", merge(edge), "RH_Silver", None, skin=CAPE_SKIN, lod1=None, tint=DARK(0.40))
    cm = g.loft(np.array(rings)[::-1], closed=False, crease=60, v_tile=0.25, u_tile=0.25)
    p.add("cape", cm, "RH_Cloth", None, skin=CAPE_SKIN, uv_scale=2, tint=DARK(0.55))
    caps = []
    rng = np.random.default_rng(2)
    for k in range(12):
        r = int(rng.random() * (R - 2))
        kk = int(rng.random() * K)
        x, y, z = rings[r][kk]
        caps.append(((x, y + 0.01, z - 0.004), (0, 0.4, -1.0), 0.02 + 0.03 * rng.random(), 0.008))
    p.add("cape_frost", spikes(caps, seed=5, flat=0.3, sides=4, tip=0.5), "RH_Frost", None, skin=CAPE_SKIN, lod1=None, tint=DARK(0.55))
    p.add("cape_hem_ice", spikes([((x, y + 0.01, z), (0.1, -1, -0.3), 0.035, 0.009) for x, y, z in tips], seed=6, flat=0.3, sides=4, tip=0.5), "RH_Ice", None, skin=CAPE_SKIN, lod1=None)


# ======================================================================================= weapon_summon glaive (grip-local frame placed at GRIP; blade toward -Y)
def glaive(p: Piece):
    def W(m):                               # the hands hold the shaft 0.12 further up than the old origin: the blade is nearer the grip
        return m.translated(*(GRIP + np.array([0.0, 0.12, 0.0])))
    shaft = g.tube([(0, 0.22, 0), (0, 0.0, 0), (0, -0.25, 0), (0, -0.48, 0)], [0.015, 0.017, 0.0145, 0.015], sides=7, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)).noised(0.0015, 20, 2, seed=3)
    p.add("glaive_shaft", W(shaft), "RH_Obsidian", "weapon_summon", uv_scale=2)
    wraps = merge([g.torus(0.0195, 0.0036, 8, 3).translated(0, 0.06 - 0.016 * i, 0) for i in range(6)])
    p.add("glaive_wraps", W(wraps), "RH_Silver", "weapon_summon", tint=DARK(0.6))
    collar = g.lathe([(0.019, -0.44), (0.029, -0.455), (0.029, -0.52), (0.019, -0.535)], 10, crease=35)
    p.add("glaive_collar", W(collar), "RH_Silver", "weapon_summon", tint=DARK(0.7))
    collar2 = g.lathe([(0.019, 0.12), (0.025, 0.13), (0.025, 0.15), (0.019, 0.16)], 10, crease=35)
    p.add("glaive_collar2", W(collar2), "RH_Silver", "weapon_summon", lod1=None, tint=DARK(0.7))
    butt = spikes([((0, 0.22, 0), (0, 1, 0), 0.07, 0.016)], seed=3, flat=0.1, sides=5, tip=0.5)
    p.add("glaive_butt", W(butt), "RH_Ice", "weapon_summon")
    poly = np.array([(-0.50, -0.026), (-0.58, -0.050), (-0.70, -0.056), (-0.82, -0.030), (-0.92, 0.050), (-0.97, 0.150),
                     (-0.86, 0.108), (-0.76, 0.078), (-0.66, 0.056), (-0.58, 0.040), (-0.50, 0.026)])
    blade = g.extrude_plane(poly, 0.030, "YZ", bevel=0.007, bevel_segments=1)
    p.add("glaive_blade", W(blade), "RH_Ice", "weapon_summon", occluder=False)
    core = g.extrude_plane(np.array([(-0.54, -0.010), (-0.66, -0.020), (-0.78, 0.0), (-0.88, 0.060), (-0.76, 0.045), (-0.62, 0.030)]), 0.011, "YZ", bevel=0.003, bevel_segments=1)
    p.add("glaive_core", W(core), "RH_Frost", "weapon_summon", occluder=False, bake=False, tint=DARK(0.55))
    hook = spikes([((0.0, -0.50, -0.020), unit((0.0, -0.1, -1.0)), 0.085, 0.014)], seed=3, flat=0.3, sides=5, tip=0.5)
    p.add("glaive_hook", W(hook), "RH_Ice", "weapon_summon")
    gr = []
    for k, (yy, ln, rr) in enumerate(((-0.56, 0.07, 0.012), (-0.66, 0.10, 0.015), (-0.76, 0.12, 0.016), (-0.84, 0.09, 0.013), (-0.62, 0.06, 0.011), (-0.72, 0.08, 0.012))):
        gr.append((np.array([0.0, yy + 0.12, -0.055]) + GRIP, unit((0.25 * (k % 2 - 0.5), -0.3, -1.0)), ln, rr))
    p.add("glaive_growths", spikes(gr, seed=20, flat=0.3, sides=5, tip=0.42), "RH_Ice", "weapon_summon")


# ======================================================================================= clips
def _anim(rig):
    """Common rig of every clip: planted feet (leg IK + pelvis reach clamp), cape / hair / skirt springs."""
    a = Animator(rig)
    M.plant_feet(a)
    a.secondary(["cape_1", "cape_2", "cape_3"], driver="body", freq=2.0, zeta=0.35, follow=1.0, accel=0.07, max_deg=24, decay=0.85)
    a.secondary(["hair_1", "hair_2", "hair_3"], driver="body", freq=2.7, zeta=0.30, follow=1.0, accel=0.07, max_deg=26)
    a.secondary(["skirt_1"], driver="body", freq=2.3, zeta=0.40, follow=0.9, accel=0.05, max_deg=8)
    a.secondary(["skirt_2"], driver="body", freq=1.9, zeta=0.35, follow=1.0, accel=0.07, max_deg=10)
    return a


def _goal(a, name):
    return next(g_ for g_ in a.goals if g_.name == name)


def feet_follow(a, sig, k=(1.0, 1.0, 1.0)):
    """She floats: both feet ride along with the pelvis (hem and legs keep their shape) instead of staying planted."""
    kk = V(*k)
    for nm in ("foot_L", "foot_R"):
        M.set_foot(a, nm, pos=Fn(lambda t: np.asarray(sig(t), float) * kk))


def _z():
    return V(0, 0, 0)


# ---------------------------------------------------------------------------------------------- Idle
def clip_idle(rig):
    a = _anim(rig)
    T = 3.8
    M.idle(a, period=T, breath=1.2, shift=0.5, sway=0.0, look=0.9, hands=True)
    bp = Wave(V(0, 0.011, 0), 1 / T, 0.0) + Wave(V(0, 0.003, 0), 2 / T, 0.2)
    a.pos("body", bp)
    feet_follow(a, bp)
    a.rot("body", Wave(V(1.0, 0, 1.6), 1 / T, 0.15))                       # the float tips her a little
    a.rot("wrist_L", Wave(V(-3.5, 0, 0), 1 / T, 0.50))                      # fingers curl and uncurl
    a.rot("wrist_R", Wave(V(-3.0, 0, 0), 1 / T, 0.62))
    a.rot("top", Wave(V(1.5, 6.0, 2.5), 1 / T, 0.30))                       # halo drifts, lags the head
    a.pos("top", Wave(V(0, 0.008, 0), 1 / T, 0.45))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- Move
def clip_move(rig):
    a = _anim(rig)
    T = 1.0
    M.biped_gait(a, T, stride=0.08, lift=0.045, duty=0.60, bob=0.014, sway=0.012, roll=3.2, twist=5.0, lean=6.5, arm_swing=(7, 7), elbow=9,
                 toe_off=16, strike=-5, head_stab=0.6)
    a.rot("top", Wave(V(-3.0, 5.0, 0), 1 / T, 0.20))
    a.pos("top", Wave(V(0, 0.010, 0), 2 / T, 0.1))
    a.rot("wrist_L", Wave(V(4, 0, 0), 1 / T, 0.30))
    a.rot("wrist_R", Wave(V(-4, 0, 0), 1 / T, 0.30))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- HitReact
def clip_hit(rig):
    a = _anim(rig)
    T = 0.5
    z = _z()
    bp = Curve([(0, z), (0.09, V(0, 0.014, -0.075), "out_cubic"), (0.22, V(0, 0.018, -0.030), "in_out_cubic"), (0.34, V(0, 0.004, -0.010), "in_out_cubic"), (T, z, "in_out_cubic")])
    a.pos("body", bp)
    feet_follow(a, bp, (1, 0.6, 1))
    a.rot("body", Curve([(0, z), (0.09, V(-9, 2, 3), "out_cubic"), (0.22, V(2, -1, -1), "in_out_cubic"), (0.34, V(-1, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.10, V(-9, 3, 2), "out_cubic"), (0.24, V(3, -2, 0), "in_out_cubic"), (0.36, V(-1.2, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.11, V(-10, 4, 3), "out_cubic"), (0.26, V(3, -3, -1), "in_out_cubic"), (0.38, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.12, V(-12, 6, 4), "out_cubic"), (0.28, V(4, -4, -1), "in_out_cubic"), (0.40, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.13, V(-14, 8, 6), "out_cubic"), (0.30, V(5, -4, -2), "in_out_cubic"), (0.42, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.10, V(0, 0, 5), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.10, V(0, 0, -5), "out_cubic"), (T, z, "in_out_cubic")]))
    for s, sg in (("L", 1), ("R", -1)):
        a.rot(f"arm_{s}", Curve([(0, z), (0.10, V(12, 0, sg * 8), "out_cubic"), (0.24, V(-4, 0, sg * 2), "in_out_cubic"), (T, z, "in_out_cubic")]))
        a.rot(f"hand_{s}", Curve([(0, z), (0.12, V(8, 0, 0), "out_cubic"), (0.26, V(-12, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
        a.rot(f"wrist_{s}", Curve([(0, z), (0.14, V(14, 0, 0), "out_cubic"), (0.28, V(-10, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("top", Curve([(0, z), (0.10, V(14, 12, 0), "out_cubic"), (0.30, V(-4, -4, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.pos("top", Curve([(0, z), (0.10, V(0, 0.02, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.25)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Victory
def clip_victory(rig):
    """She rises, the free hand presents palm-up, the halo pulses and then floats on."""
    a = _anim(rig)
    T = 2.0
    z = _z()
    bp = Curve([(0, z), (0.18, V(0, -0.012, 0), "in_out_cubic"), (0.62, V(0, 0.034, 0.008), ("spring", 0.2, 1.5)), (T, V(0, 0.030, 0.008), "in_out_cubic")]) + Wave(V(0, 0.005, 0), 0.5, 0.0) * step_signal([(0.9, 0), (1.3, 1)])
    a.pos("body", bp)
    feet_follow(a, bp)
    a.rot("body", Curve([(0, z), (0.18, V(3, 0, 0)), (0.62, V(-3, -4, -1), "out_cubic"), (T, V(-2, -3, -1), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.18, V(4, 0, 0)), (0.66, V(-6, -3, 0), ("spring", 0.15, 1.5)), (T, V(-5, -2, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.18, V(5, 0, 0)), (0.68, V(-8, -5, 0), ("spring", 0.15, 1.5)), (T, V(-7, -3, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.7, V(-6, 4, 0), "out_cubic"), (T, V(-5, 3, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.72, V(-10, 6, 0), ("spring", 0.15, 1.5)), (T, V(-9, 5, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.20, V(0, 0, 2), "in_out_cubic"), (0.70, V(0, 0, -8), "out_cubic"), (T, V(0, 0, -8))]))
    a.rot("clavicle_L", Curve([(0, z), (0.70, V(0, 0, 4), "out_cubic"), (T, V(0, 0, 4))]))
    a.rot("arm_R", Curve([(0, z), (0.20, V(10, 0, -4), "in_out_cubic"), (0.66, V(-72, 0, -10), ("spring", 0.10, 1.5)), (T, V(-70, 0, -10), "in_out_cubic")]))
    a.rot("hand_R", Curve([(0, z), (0.20, V(8, 0, 0), "in_out_cubic"), (0.70, V(-34, 0, 0), ("spring", 0.18, 1.5)), (T, V(-32, 0, 0), "in_out_cubic")]))
    a.rot("wrist_R", Curve([(0, z), (0.72, V(-24, 0, 0), ("spring", 0.2, 1.5)), (T, V(-22, 0, 0), "in_out_cubic")]))
    a.rot("arm_L", Curve([(0, z), (0.24, V(6, 0, 4), "in_out_cubic"), (0.80, V(-34, 0, 12), ("spring", 0.12, 1.5)), (T, V(-32, 0, 12), "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.80, V(-30, 0, 0), ("spring", 0.12, 1.5)), (T, V(-28, 0, 0), "in_out_cubic")]))
    a.rot("wrist_L", Curve([(0, z), (0.82, V(-14, 0, 0), ("spring", 0.2, 1.5)), (T, V(-12, 0, 0), "in_out_cubic")]))
    a.rot("top", Curve([(0, z), (0.9, V(-4, 24, 0), "in_out_cubic"), (T, V(-3, 32, 0), "in_out_cubic")]))
    a.pos("top", Curve([(0, z), (0.7, V(0, 0.035, 0), "out_cubic"), (T, V(0, 0.03, 0), "in_out_cubic")]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Taunt
def clip_taunt(rig):
    """The halo flares (scale pulse added after the bake), then the free left hand beckons: palm up, fingers ripple twice."""
    a = _anim(rig)
    T = 1.6
    z = _z()
    bp = Curve([(0, z), (0.40, V(0, 0.026, 0.0), "out_cubic"), (1.1, V(0.004, 0.022, 0.02), "in_out_cubic"), (T, z, "in_out_cubic")])
    a.pos("body", bp)
    feet_follow(a, bp, (1, 1, 0.7))
    a.rot("body", Curve([(0, z), (0.45, V(-2, 0, 3), "in_out_cubic"), (1.1, V(-2, 0, -3), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.22, V(-3, 0, 0), "out_cubic"), (0.85, V(-3, -8, 0), "in_out_cubic"), (1.3, V(-3, -8, 0)), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.22, V(-4, 0, 0), "out_cubic"), (0.85, V(-4, -8, 0), "in_out_cubic"), (1.3, V(-4, -8, 0)), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.30, V(-3, 0, 4), "out_cubic"), (0.85, V(-4, -5, 6), "in_out_cubic"), (1.3, V(-4, -5, 6)), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.30, V(-5, 0, -6), "out_cubic"), (0.80, V(-4, -6, 7), "in_out_cubic"), (1.3, V(-4, -6, 7)), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.80, V(0, 0, 4), "out_cubic"), (1.3, V(0, 0, 4)), (T, z, "in_out_cubic")]))
    bk = Curve([(0, WL0), (0.45, WL0 + V(0.0, 0.02, 0.02), "in_out_cubic"), (0.85, V(0.17, 1.02, 0.40), "out_cubic"), (1.30, V(0.17, 1.02, 0.40), {"tan": "flat"}), (T, WL0, "in_out_cubic")])
    gg = a.goal("ik_beckon", ("arm_L", "hand_L", "wrist_L"), spaces=(("chest", 1.0),), rot=None, pole=(0.6, -1, -0.2))
    gg.pos = M.abs_pos(WL0, bk)
    gg.weight = step_signal([(0.40, 0.0), (0.80, 1.0), (1.30, 1.0), (T, 0.0)])
    a.rot("wrist_L", Curve([(0, z), (0.80, V(-30, 0, 0), "out_cubic"), (0.95, V(-72, 0, 0), "in_out_quad"), (1.10, V(-6, 0, 0), "in_out_quad"), (1.24, V(-72, 0, 0), "in_out_quad"), (1.38, V(-20, 0, 0), "in_out_quad"), (T, z, "in_out_cubic")]))
    a.rot("arm_R", Curve([(0, z), (0.4, V(4, 0, -6), "out_cubic"), (1.1, V(5, 0, -8), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("top", Curve([(0, z), (0.40, V(-6, 22, 0), "out_cubic"), (1.0, V(-2, -6, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.pos("top", Curve([(0, z), (0.40, V(0, 0.05, 0), "out_cubic"), (1.1, V(0, 0.03, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Surrender
SURR_SK = (0.8, 1.15)          # skirt compression fractions, tuned below


def clip_surrender(rig):
    """Stagger, then a one-knee KNEEL (left foot planted, right knee on the plinth, shin and instep flat); the gown gathers on its
    skirt bones instead of sinking into the plinth.  Torso folds, head bows, empty palms turn up onto the thighs; the halo dims
    (shrinks) and drops over the bowed head."""
    a = _anim(rig)
    T = 2.4
    z = _z()
    sk = a.sk
    L1 = float(np.linalg.norm(sk.rest[sk.ix["shin_R"]] - sk.rest[sk.ix["thigh_R"]]))
    L2 = float(np.linalg.norm(sk.rest[sk.ix["foot_R"]] - sk.rest[sk.ix["shin_R"]]))
    KNEE_Y = 0.290
    DROP = JOINTS["hip_L"][1] - (KNEE_Y + L1)
    PZ = 0.05
    a.pos("body", Curve([(0, z), (0.30, V(0, -0.012, -0.040), "out_cubic"), (0.55, V(0, -0.020, -0.020), "in_out_cubic"), (1.38, V(0, -DROP, PZ), "in_out_cubic"),
                         (1.60, V(0, -DROP + 0.007, PZ), "out_cubic"), (1.95, V(0, -DROP, PZ), "in_out_cubic"), (T, V(0, -DROP - 0.004, PZ), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.30, V(-6, 0, 0), "out_cubic"), (0.55, z, "in_out_cubic"), (1.38, V(3, 0, -2), "in_out_cubic"), (T, V(4, 0, -2), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.30, V(-3, 0, 0), "out_cubic"), (0.9, V(4, 0, 0), "in_out_cubic"), (1.6, V(7, 0, 0), "in_out_cubic"), (T, V(8, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.30, V(-2, 0, 0), "out_cubic"), (0.9, V(3, 0, 0), "in_out_cubic"), (1.7, V(5, 0, 0), "in_out_cubic"), (T, V(6, 0, 0.0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.30, V(-4, 0, 0), "out_cubic"), (1.0, V(6, 0, 0), "in_out_cubic"), (1.75, V(11, 0, 0), "in_out_cubic"), (T, V(12, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.30, V(-10, 0, 0), "out_cubic"), (1.0, V(8, 0, 0), "in_out_cubic"), (1.75, V(16, 2, 3), "in_out_cubic"), (T, V(18, 2, 4), "in_out_cubic")]))
    comp = Curve([(0, z), (0.55, z, "in_out_cubic"), (1.38, V(0, 1, 0), "in_out_cubic"), (T, V(0, 1, 0))])         # the gown gathers as she sinks
    a.pos("skirt_1", Fn(lambda t: comp(t) * (DROP * SURR_SK[0])))
    a.pos("skirt_2", Fn(lambda t: comp(t) * (DROP * SURR_SK[1])))
    a.pos("cape_2", Fn(lambda t: comp(t) * (DROP * 0.45)))                                  # the mist cloak gathers on the plinth too
    a.pos("cape_3", Fn(lambda t: comp(t) * (DROP * 0.60)))
    a.rot("clavicle_R", Curve([(0, z), (1.0, V(0, 0, 4), "in_out_cubic"), (T, V(0, 0, 6))]))
    a.rot("clavicle_L", Curve([(0, z), (1.0, V(0, 0, -4), "in_out_cubic"), (T, V(0, 0, -6))]))
    wl_t, wr_t = V(0.105, 0.665, 0.215), V(-0.115, 0.640, 0.185)                       # empty palms rest in her lap on the thighs
    for s, sg, tgt, w0 in (("L", 1, wl_t, WL0), ("R", -1, wr_t, WR0)):
        gg = a.goal(f"ik_lap_{s}", (f"arm_{s}", f"hand_{s}", f"wrist_{s}"), spaces=(("world", 1.0),), rot=None, pole=(sg * 0.5, -1, -0.3))
        gg.pos = M.abs_pos(w0, Curve([(0, w0), (0.9, w0 + V(0, -0.02, 0.05), "in_out_cubic"), (1.55, tgt, "in_out_cubic"), (T, tgt + V(0, -0.004, 0.0), "in_out_cubic")]))
        gg.weight = step_signal([(0.80, 0.0), (1.45, 1.0)])
    for s, sg in (("L", 1), ("R", -1)):
        a.rot(f"arm_{s}", Curve([(0, z), (0.30, V(8, 0, sg * 6), "out_cubic"), (1.2, V(-22, 0, sg * 3), "in_out_cubic"), (1.8, V(-30, 0, sg * 2), "in_out_cubic"), (T, V(-31, 0, sg * 2), "in_out_cubic")]))
        a.rot(f"hand_{s}", Curve([(0, z), (0.30, V(6, 0, 0), "out_cubic"), (1.2, V(-48, 0, 0), "in_out_cubic"), (1.8, V(-56, 0, 0), "in_out_cubic"), (T, V(-57, 0, 0), "in_out_cubic")]))
        a.rot(f"wrist_{s}", Curve([(0, z), (0.5, V(10, 0, 0), "in_out_cubic"), (1.4, V(-34, 0, 0), "in_out_cubic"), (T, V(-40, 0, 0), "in_out_cubic")]))
    a.rot("top", Curve([(0, z), (0.30, V(10, 12, 0), "out_cubic"), (0.9, V(18, 0, 0), "in_out_cubic"), (1.4, V(12, 0, 0), "in_out_cubic"), (T, V(15, 0, 0))]))
    a.pos("top", Curve([(0, z), (0.30, V(0, 0.04, 0), "out_cubic"), (1.5, V(0, -0.04, 0.02), "in_out_cubic"), (T, V(0, -0.06, 0.03), "in_out_cubic")]))
    ankL = V(0.0, 0.0, PZ + 0.165 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.55, z), (0.85, ankL + V(0, 0.06, -0.06), "in_out_cubic"), (1.15, ankL, "in_out_cubic"), (T, ankL)]),
               rot=Curve([(0, z), (0.55, z), (0.70, V(18, 0, 0), "in_out_cubic"), (0.95, V(-10, 0, 0), "in_out_cubic"), (1.15, z, "in_out_cubic"), (T, z)]))
    ankR = V(0.0, KNEE_Y - JOINTS["ankle_L"][1], PZ - L2 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.60, z), (1.00, ankR + V(0, 0.10, 0.10), "in_out_cubic"), (1.38, ankR, "in_out_cubic"), (T, ankR)]),
               rot=Curve([(0, z), (0.60, z), (1.00, V(95, 0, 0), "in_out_cubic"), (1.38, V(172, 0, 0), "in_out_cubic"), (T, V(172, 0, 0))]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Attack
IMPACT = 1.30
TW = 1.05                                  # wind-up peak, held to TH, then the cut
TH = 1.10
nrm = lambda v: np.asarray(v, float) / np.linalg.norm(v)                 # noqa: E731
B0 = np.column_stack([np.cross(A_S, E_S), A_S, E_S])                    # rest frame of the glaive: (side, shaft, edge)


def glaive_frame(Dsig, Esig):
    """Goal.rot signal: the rotation taking the rest glaive (shaft A_S, edge E_S) to shaft direction D(t) with the cutting edge facing E(t)."""
    def f(t):
        D = nrm(Dsig(t))
        E = np.asarray(Esig(t), float)
        E = nrm(E - (E @ D) * D)
        B1 = np.column_stack([np.cross(D, E), D, E])
        return B1 @ B0.T
    return Fn(f)


def edge_for(D):
    """Edge normal: the cutting edge leads the sweep (the head circles about +Y, so its velocity is Y x D); a hanging blade keeps its rest edge."""
    D = nrm(D)
    h = np.array([D[2], 0.0, -D[0]])
    w = float(smoothstep(0.15, 0.45, float(np.linalg.norm(h))))
    e = h / max(float(np.linalg.norm(h)), 1e-9) * w + E_S * (1 - w)
    return nrm(e - (e @ D) * D)


GS = -0.17                                  # left hand sits this far from the right along the shaft (negative: toward the butt)
P_SUM, D_SUM = V(-0.15, 1.02, 0.29), nrm((-0.20, -0.25, 0.95))             # glaive drawn from the air ahead of her
P_WIND, D_WIND = V(-0.20, 1.10, 0.22), nrm((-0.585, 0.474, 0.659))            # head high, behind the right shoulder
P_HIT, D_HIT = V(-0.10, 1.00, 0.14), nrm((-0.68, -0.30, 0.67))
P_FOL, D_FOL = V(-0.08, 0.97, 0.20), nrm((-0.52, -0.40, 0.76))


def clip_attack(rig):
    a = _anim(rig)
    gr = a.goal("ik_hand_R", ("arm_R", "hand_R", "wrist_R"), spaces=(("chest", 1.0),), rot=(0, 0, 0), pole=(-0.5, -1, -0.2))
    gl = a.goal("ik_hand_L", ("arm_L", "hand_L", "wrist_L"), spaces=(("chest", 1.0),), rot=(0, 0, 0), pole=(0.5, -1, -0.2))
    T, I = 2.4, IMPACT
    z = _z()
    Pc = Curve([(0, WR0), (0.14, V(-0.20, 0.92, 0.24), "in_out_cubic"), (0.30, P_SUM, "out_cubic"), (0.50, P_SUM + V(0, 0, 0.0), "in_out_cubic"), (TW, P_WIND, "in_out_cubic"),
                (TH, P_WIND + V(0.01, 0.0, -0.01), {"tan": "flat"}), (I, P_HIT, "snap_in"), (1.44, P_FOL, "out_cubic"), (1.62, P_FOL, {"tan": "flat"}), (2.12, WR0, "in_out_cubic"), (T, WR0)])
    Dc = Curve([(0, A_S), (0.14, nrm((0, -0.6, 0.8)), "in_out_cubic"), (0.30, D_SUM, "out_cubic"), (0.50, D_SUM, "in_out_cubic"), (TW, D_WIND, "in_out_cubic"), (TH, D_WIND, {"tan": "flat"}),
                (I, D_HIT, "snap_in"), (1.44, D_FOL, "out_cubic"), (1.62, D_FOL, {"tan": "flat"}), (2.12, A_S, "in_out_cubic"), (T, A_S)])
    Sc = Curve([(0, 0.0), (0.4, 0.0), (0.55, GS, "in_out_cubic"), (T, GS)])
    Wl = Curve([(0, 0.0), (0.36, 0.0), (0.58, 1.0, "in_out_cubic"), (1.78, 1.0), (2.12, 0.0, "in_out_cubic"), (T, 0.0)])
    Ec = Fn(lambda t: edge_for(Dc(t)))
    Rf = glaive_frame(Dc, Ec)
    gr.pos = M.abs_pos(WR0, Pc)
    gr.rot = Rf
    gl.pos = Fn(lambda t: Pc(t) + (Rf(t) @ A_S) * float(Sc(t)[0]) - WL0)
    gl.rot = Rf
    gl.weight = Wl
    # ---- yaw: the whole torso winds up to the right, then unwinds through the cut (pelvis leads by ~0.06 s, spine ~0.03 s)
    ya = lambda w, h, f=0.0: Curve([(0, 0), (0.35, 0.18 * w, "in_out_cubic"), (TW, w, "in_out_cubic"), (TH, w, {"tan": "flat"}), (I - f, h, "snap_in"), (1.46, h * 0.8, "out_cubic"), (1.62, h * 0.8, {"tan": "flat"}), (2.2, 0, "in_out_cubic"), (T, 0)])   # noqa: E731
    yawb, yaws, yawc = ya(-10, 12, 0.06), ya(-26, 16, 0.03), ya(-30, 18, 0.0)
    a.rot("body", Fn(lambda t: V(0, float(yawb(t)[0]) if hasattr(yawb(t), "__len__") else float(yawb(t)), 0)))
    a.rot("spine", Fn(lambda t: V(0, float(np.ravel(yaws(t))[0]), 0)))
    a.rot("chest", Fn(lambda t: V(0, float(np.ravel(yawc(t))[0]), 0)))
    a.rot("body", Curve([(0, z), (0.35, V(-2, 0, 0), "in_out_cubic"), (TW, V(-6, 0, 0), "in_out_cubic"), (TH, V(-6, 0, 0), {"tan": "flat"}), (I - 0.05, V(8, 0, 0), "snap_in"), (1.46, V(6, 0, 0), "out_cubic"), (2.2, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.35, V(-3, 0, 0), "in_out_cubic"), (TW, V(-5, 0, 0), "in_out_cubic"), (TH, V(-5, 0, 0), {"tan": "flat"}), (I - 0.03, V(8, 0, 0), "snap_in"), (1.46, V(6, 0, 0), "out_cubic"), (2.2, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.35, V(-2, 0, 0), "in_out_cubic"), (TW, V(-3, 0, 2), "in_out_cubic"), (TH, V(-3, 0, 2), {"tan": "flat"}), (I, V(6, 0, -2), "snap_in"), (1.46, V(5, 0, -1), "out_cubic"), (2.2, z, "in_out_cubic")]))
    hy = lambda w, h: Curve([(0, 0), (0.35, 0.15 * w, "in_out_cubic"), (TW, w, "in_out_cubic"), (TH, w, {"tan": "flat"}), (I + 0.04, h, "snap_in"), (1.5, h, "out_cubic"), (1.62, h), (2.2, 0, "in_out_cubic"), (T, 0)])   # noqa: E731
    ny, hyc = hy(22, -12), hy(26, -14)
    a.rot("neck", Fn(lambda t: V(0, float(np.ravel(ny(t))[0]), 0)))
    a.rot("head", Fn(lambda t: V(0, float(np.ravel(hyc(t))[0]), 0)))
    a.rot("head", Curve([(0, z), (0.35, V(-4, 0, 0), "out_cubic"), (TW, V(-5, 0, 0), "in_out_cubic"), (TH, V(-5, 0, 0)), (I + 0.04, V(6, 0, 0), "snap_in"), (1.5, V(5, 0, 0), "out_cubic"), (2.2, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (TW, V(0, 0, -6), "in_out_cubic"), (I, V(0, 0, 3), "snap_in"), (1.5, V(0, 0, 3)), (2.2, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (TW, V(0, 0, 5), "in_out_cubic"), (I, V(0, 0, -3), "snap_in"), (1.5, V(0, 0, -3)), (2.2, z, "in_out_cubic")]))
    # ---- glide: lean back and rise through the wind-up, shoot forward into the cut, settle
    bp = Curve([(0, z), (0.30, V(0, 0.012, -0.020), "in_out_cubic"), (TW, V(0, 0.032, -0.100), "in_out_cubic"), (TH, V(0, 0.034, -0.105), {"tan": "flat"}),
                (I - 0.05, V(0, 0.030, 0.040), "snap_in"), (1.40, V(0, 0.026, 0.048), "out_cubic"), (1.62, V(0, 0.002, 0.044), {"tan": "flat"}), (2.2, z, "in_out_cubic"), (T, z)])
    a.pos("body", bp)
    feet_follow(a, bp, (1, 1, 1.0))
    a.rot("top", Curve([(0, z), (0.45, V(-4, 18, 0), "out_cubic"), (TH, V(-6, 22, 0), "in_out_cubic"), (I + 0.03, V(-4, -26, 0), "snap_in"), (1.6, V(-4, -10, 0), "out_cubic"), (2.2, z, "in_out_cubic")]))
    a.pos("top", Curve([(0, z), (0.45, V(0, 0.03, 0), "out_cubic"), (1.4, V(0, 0.01, 0), "in_out_cubic"), (2.2, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 60, (I,)


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
        c = a.bake(name, dur, loop=loop, fps=fps, keep_times=keep)
        if name == "Attack":                                           # drawn from the air, held, dissolved again
            c.keys("weapon_summon", "scale", [(0, 0.0), (0.04, 0.0), (0.30, 1.15, "out_cubic"), (0.45, 1.0, "in_out_cubic"), (2.10, 1.0), (dur, 0.0, "in_quad")])
        else:
            c.keys("weapon_summon", "scale", [(0, 0.0), (dur, 0.0)])
        if name == "Taunt":                                            # the halo flares, then settles
            c.keys("top", "scale", [(0, (1, 1, 1)), (0.30, (1.55, 1.55, 1.55), "out_back"), (0.80, (1.25, 1.25, 1.25), "in_out_cubic"), (dur, (1, 1, 1), "in_out_cubic")])
        elif name == "Surrender":                                      # the halo dims (shrinks) and sinks over the bowed head
            c.keys("top", "scale", [(0, (1, 1, 1)), (0.35, (1.10, 1.10, 1.10), "out_cubic"), (1.5, (0.62, 0.62, 0.62), "in_out_cubic"), (dur, (0.55, 0.55, 0.55))])
        elif name == "Victory":                                        # halo pulse
            c.keys("top", "scale", [(0, (1, 1, 1)), (0.7, (1.28, 1.28, 1.28), "out_cubic"), (1.2, (1.08, 1.08, 1.08), "in_out_cubic"), (dur, (1.12, 1.12, 1.12), "in_out_cubic")])
        out.append(c)
    if cache:
        with open(cache, "wb") as fh:
            pickle.dump(out, fh)
    return out


# ======================================================================================= build
def impact_socket(rig):
    """Place socket_impact (under body) where the glaive blade meets the board at impactTime."""
    a, dur, loop, fps, keep = clip_attack(rig)
    ix = a.sk.ix
    c = a.pose(keep[0])
    R = c.Rw[ix["wrist_R"]]
    ph = c.Pw[ix["wrist_R"]] + R @ V(0, -0.63, 0.04)
    pc = V(ph[0], max(ph[1], 0.30), ph[2])
    Rb, Pb = c.Rw[ix["body"]], c.Pw[ix["body"]]
    return rig.pos("body") + Rb.T @ (pc - Pb)


def build(log=print):
    rig = make_rig()
    rig.socket("socket_impact", "body", tuple(impact_socket(rig)))
    p = Piece("rime", "queen", rig, make_clips(rig), impact_time=IMPACT, strike_range=0.70, attack_style="summon", seed=9)
    rc.pedestal_parts(p)
    legs(p)
    gown(p)
    bodice(p)
    arms(p)
    head(p)
    halo(p)
    cape(p)
    glaive(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris (+{p.node_tri_count()} on weapon_summon) before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
