"""rime_knight - Rime Gravewind Rider: a skeletal rider in wired obsidian plate on a gaunt ice ram whose rib cage is
hollow and lit by a cold inner glow, spiral crystal horns, a hooked glaive standing upright at his side.
Mount faces +Z.  Built from docs/art/rime_knight.md."""
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

ASSET_ID = "rime_knight"


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("mount_body", "root", (0, 0.58, 0))
    r.add("mount_head", "mount_body", (0, 0.72, 0.16))
    r.add("body", "mount_body", (0, 0.75, -0.05))
    r.add("spine", "body", (0, 0.80, -0.05))
    r.add("head", "spine", (0, 1.00, -0.04))
    r.add("top", "body", (0, 0.78, -0.10))
    r.add("arm_L", "spine", (0.095, 0.98, -0.05))
    r.add("hand_L", "arm_L", (0.105, 0.90, -0.01))
    r.add("arm_R", "spine", (-0.095, 0.98, -0.05))
    r.add("hand_R", "arm_R", (-0.11, 0.90, 0.0))
    r.add("weapon", "hand_R", (-0.17, 0.95, 0.02))        # the glaive (centre of mass): lets Surrender drop it
    r.socket("socket_weapon_R", "hand_R", (-0.17, 1.28, 0.20))
    r.socket("socket_cast", "mount_body", (0, 0.60, 0.0))
    r.socket("socket_impact", "body", (-0.08, 0.72, 0.60))
    r.socket("socket_head", "head", (0, 1.12, -0.03))
    return r


def mpts(pts, s):
    return [(s * x, y, z) for x, y, z in pts]


def helix_path(centers, radius, turns, n=20, phase=0.0):
    """Points spiralling around a polyline (a twin crystal spiral)."""
    cl = g.spline(np.asarray(centers, float), 4)
    idx = np.linspace(0, len(cl) - 1, n).astype(int)
    pts = []
    for q, i in enumerate(idx):
        t = q / (n - 1)
        T = unit(cl[min(i + 1, len(cl) - 1)] - cl[max(i - 1, 0)])
        a = unit(np.cross(T, [0, 0, 1.0] if abs(T[2]) < 0.9 else [1.0, 0, 0]))
        b = np.cross(T, a)
        ang = phase + t * turns * TAU
        pts.append(cl[i] + (a * math.cos(ang) + b * math.sin(ang)) * radius * (1 - 0.35 * t))
    return pts


# ======================================================================================= ram body
def mount_body(p: Piece):
    # spine ridge with vertebra knobs
    spine_pts = [(0, 0.69, -0.28), (0, 0.72, -0.10), (0, 0.72, 0.14)]
    ridge = g.tube(spine_pts, [0.026, 0.028, 0.030], sides=6, samples=3, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("m_spine", ridge, "RH_Armour", "mount_body", uv_scale=2)
    knobs = [g.superellipsoid((0.034, 0.030, 0.030), 0.6, 0.7, 3, 7).translated(0, 0.735 + 0.002 * (k % 2), -0.27 + 0.0525 * k) for k in range(9)]
    p.add("m_vertebrae", merge(knobs), "RH_Armour", "mount_body")
    p.add("m_vertebra_spikes", spikes([((0, 0.755, -0.27 + 0.0525 * k), (0, 1, -0.3), 0.04 + 0.015 * (k % 3), 0.009) for k in range(9)], seed=3, flat=0.3, sides=4, tip=0.5), "RH_Ice", "mount_body", lod1=None)
    # nine pairs of ribs (hollow cage), frost-lit from inside
    ribs = []
    for k in range(9):
        z = -0.24 + 0.046 * k
        sc = 1.0 - 0.18 * abs(k - 4) / 4
        for s in (-1, 1):
            pts = [(0, 0.70, z), (0.09 * sc, 0.72, z), (0.15 * sc, 0.62, z + 0.01), (0.12 * sc, 0.50, z + 0.02)]
            ribs.append(g.tube(mpts(pts, s), [0.012, 0.012, 0.011, 0.007], sides=5, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)))
    p.add("m_ribs", merge(ribs), "RH_Armour", "mount_body")
    p.add("m_sternum", g.tube([(0, 0.47, -0.20), (0, 0.46, -0.03), (0, 0.46, 0.14)], 0.013, sides=5, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)), "RH_Armour", "mount_body")
    p.add("m_rib_frost", frost_layer(merge(ribs[:8]), 0.004, min_ny=0.8, cover=0.3, seed=3), "RH_Frost", "mount_body", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    # frost-light core seen through the ribs (focal point 2)
    core = g.superellipsoid((0.075, 0.050, 0.17), 0.9, 0.9, 5, 10).noised(0.008, 14, 2, seed=2).translated(0, 0.60, -0.04)
    p.add("m_core_light", core, "RH_Seam", "mount_body", bake=False, lod1="keep")
    embers = merge([g.superellipsoid((0.028, 0.026, 0.030), 0.9, 0.9, 4, 8).translated(0, 0.60 + 0.01 * k, z) for k, z in enumerate((-0.14, -0.02, 0.06))])
    p.add("m_core_embers", embers, "RH_Glow", "mount_body", bake=False, lod1="keep")
    # dark barding over the withers and haunch + spine plates: keeps the mount a dark mass with ice accents
    plates = []
    for k in range(7):
        plates.append(g.superellipsoid((0.050, 0.014, 0.034), 0.5, 0.6, 3, 8).rotated(-6, 0, 0).translated(0, 0.766 + 0.002 * (k % 2), -0.255 + 0.062 * k))
    p.add("m_spine_plates", merge(plates), "RH_Obsidian", "mount_body")
    for sd, nmm in ((+1, "L"), (-1, "R")):
        sh = [g.superellipsoid((0.030 - 0.004 * i, 0.044 - 0.005 * i, 0.058 - 0.006 * i), 0.5, 0.6, 3, 9).rotated(0, 0, sd * (-14 - 6 * i)).translated(sd * (0.118 + 0.008 * i), 0.585 - 0.034 * i, 0.135) for i in range(2)]
        p.add(f"m_shoulder_plates_{nmm}", merge(sh), "RH_Obsidian", "mount_body")
        hp = [g.superellipsoid((0.034 - 0.004 * i, 0.048 - 0.005 * i, 0.062 - 0.006 * i), 0.5, 0.6, 3, 9).rotated(0, 0, sd * (-14 - 6 * i)).translated(sd * (0.130 + 0.008 * i), 0.60 - 0.034 * i, -0.215) for i in range(2)]
        p.add(f"m_haunch_plates_{nmm}", merge(hp), "RH_Obsidian", "mount_body")
        mus = [g.superellipsoid((0.044, 0.070, 0.056), 0.6, 0.7, 4, 9).translated(sd * 0.098, 0.565, 0.12), g.superellipsoid((0.052, 0.080, 0.066), 0.6, 0.7, 4, 9).translated(sd * 0.108, 0.565, -0.22)]
        p.add(f"m_leg_mass_{nmm}", merge(mus), "RH_Armour", "mount_body", uv_scale=2)
    # cloudy pelvis + torn pelt scraps
    pel = g.superellipsoid((0.11, 0.07, 0.07), 0.5, 0.6, 4, 10).translated(0, 0.64, -0.25)
    p.add("m_pelvis", pel, "RH_Obsidian", "mount_body")
    scraps = []
    for k, (x, ln) in enumerate(((0.10, 0.22), (-0.11, 0.18), (0.13, 0.12))):
        poly = np.array([(0.0, 0.0), (0.07, -0.02), (0.065, -ln * 0.6), (0.03, -ln), (0.0, -ln * 0.55), (-0.01, -0.03)])
        sg = 1 if x > 0 else -1
        scraps.append(g.extrude(poly, 0.006, 0.0012, 1).rotated(0, 90 * sg, 0).translated(x, 0.70 - 0.02 * k, -0.20 + 0.06 * k))
    p.add("m_pelt", merge(scraps), "RH_Cloth", "mount_body", uv_scale=2)
    # legs: gaunt, with joint spurs and cloven obsidian hooves
    for s, nm in ((+1, "L"), (-1, "R")):
        fl = mpts([(0.095, 0.60, 0.11), (0.100, 0.47, 0.175), (0.105, 0.34, 0.150), (0.105, 0.25, 0.185)], s)
        p.add(f"m_foreleg_{nm}", g.tube(fl, [0.040, 0.027, 0.020, 0.024], sides=6, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Armour", "mount_body", uv_scale=2)
        hl = mpts([(0.10, 0.62, -0.22), (0.120, 0.48, -0.11), (0.105, 0.35, -0.275), (0.105, 0.25, -0.225)], s)
        p.add(f"m_hindleg_{nm}", g.tube(hl, [0.048, 0.033, 0.022, 0.024], sides=6, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Armour", "mount_body", uv_scale=2)
        p.add(f"m_leg_lames_{nm}", merge([rc.limb_lames(fl, [0.036, 0.024, 0.018, 0.022], [0.20, 0.45], h=0.040, sweep=230, grow=0.006, seg=6),
                                           rc.limb_lames(hl, [0.042, 0.030, 0.020, 0.022], [0.22, 0.52], h=0.044, sweep=230, grow=0.006, seg=6)]), "RH_Obsidian", "mount_body")
        hv = []
        for (hx, hz) in ((s * 0.105, 0.18), (s * 0.105, -0.23)):
            for o in (-0.014, 0.014):
                hv.append(shard(0.045, 0.016, sides=5, tip=0.3, flat=0.2, seed=3).rotated(90, 0, 0).translated(hx + o * 0.0, 0.245, hz + o + 0.02) if False else
                          g.superellipsoid((0.015, 0.020, 0.024), 0.5, 0.6, 3, 7).translated(hx + o, 0.235, hz + 0.01))
        p.add(f"m_hooves_{nm}", merge(hv), "RH_Obsidian", "mount_body")
        sp = [((s * 0.115, 0.46, 0.13), (s * 0.3, 0.0, -1.0), 0.05, 0.011), ((s * 0.12, 0.47, -0.19), (s * 0.3, 0.0, -1.0), 0.06, 0.012), ((s * 0.11, 0.35, -0.27), (s * 0.2, 0.0, -1.0), 0.045, 0.010)]
        p.add(f"m_joint_spurs_{nm}", spikes(sp, seed=9 + (s > 0), flat=0.3, sides=4, tip=0.5), "RH_Ice", "mount_body", lod1=None)
        p.add(f"m_hoof_frost_{nm}", g.torus(0.026, 0.005, 10, 3).translated(s * 0.105, 0.262, 0.18), "RH_Frost", "mount_body", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    # bony tail with ice shards
    tail = g.tube([(0, 0.66, -0.30), (0, 0.56, -0.40), (0, 0.42, -0.42)], [0.018, 0.014, 0.004], sides=5, samples=3, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("m_tail", tail, "RH_Armour", "mount_body")
    p.add("m_tail_shards", spikes([((0, 0.60, -0.37), (0.3, -0.2, -1.0), 0.07, 0.012), ((0, 0.50, -0.41), (-0.3, -0.5, -1.0), 0.06, 0.011), ((0, 0.43, -0.42), (0.2, -1, -0.3), 0.06, 0.010)], seed=5, flat=0.3, sides=4, tip=0.5), "RH_Ice", "mount_body")
    # saddle + tattered blanket (soft)
    sad = g.superellipsoid((0.085, 0.020, 0.100), 0.5, 0.6, 4, 10).translated(0, 0.745, -0.05)
    p.add("m_saddle", sad, "RH_Armour", "mount_body", uv_scale=2)
    p.add("m_saddle_wire", g.torus(0.086, 0.004, 14, 3).scaled(1.0, 1.0, 1.15).translated(0, 0.752, -0.05), "RH_Silver", "mount_body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    R, K = 6, 7
    rings = []
    for r_ in range(R):
        v = r_ / (R - 1)
        row = []
        for k in range(K):
            u = k / (K - 1)
            ang = math.radians(-60 + 120 * u)
            rr = 0.17 + 0.03 * v
            y = 0.755 - 0.20 * v - (0.05 * (k % 2) if r_ == R - 1 else 0)
            row.append((-0.0 + rr * math.sin(ang) * 1.0 + (0.0), y - 0.0, -0.17 + 0.10 * (1 - math.cos(ang)) * 0.0 - 0.0 + 0.0))
        rings.append(row)
    # blanket draped over the haunch: a curved patch from the saddle down the right (-X) side
    rows = []
    for r_ in range(R):
        v = r_ / (R - 1)
        row = []
        for k in range(K):
            u = k / (K - 1)
            z = -0.28 + 0.26 * u
            x = -(0.085 + 0.080 * v ** 0.8) + 0.004 * math.sin(u * 9)
            y = 0.748 - 0.24 * v - (0.045 * (k % 2) if r_ == R - 1 else 0)
            row.append((x, y, z))
        rows.append(row)
    bl = g.loft(np.array(rows)[::-1], closed=False, crease=60, v_tile=0.25, u_tile=0.25)
    p.add("m_blanket", bl, "RH_Cloth", "mount_body", uv_scale=2)


# ======================================================================================= ram head
def mount_head(p: Piece):
    neck = g.tube([(0, 0.69, 0.14), (0, 0.76, 0.25), (0, 0.80, 0.34)], [0.060, 0.046, 0.040], sides=7, samples=3, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("m_neck", neck, "RH_Armour", "mount_head", uv_scale=2)
    p.add("m_neck_spikes", spikes([((0, 0.74 + 0.02 * k, 0.17 + 0.045 * k), (0, 1.0, -0.4), 0.04 + 0.02 * (k % 3), 0.010) for k in range(5)], seed=7, flat=0.3, sides=4, tip=0.5), "RH_Ice", "mount_head")
    p.add("m_neck_lames", rc.limb_lames([(0, 0.69, 0.14), (0, 0.76, 0.25), (0, 0.80, 0.34)], [0.060, 0.046, 0.040], [0.25, 0.5, 0.75], h=0.050, sweep=300, grow=0.007, seg=8, spin=180), "RH_Obsidian", "mount_head")
    skull = g.tube([(0, 0.82, 0.34), (0, 0.80, 0.43), (0, 0.76, 0.52)], [0.050, 0.043, 0.028], sides=7, samples=3, cap="round", cap_steps=1, ellipse=(1.0, 0.9), up=(1, 0, 0))
    p.add("m_skull", skull.noised(0.003, 22, 2, seed=3), "RH_Armour", "mount_head", uv_scale=2)
    plates = []
    for s in (-1, 1):
        pl = g.extrude_plane(np.array([(0.84, 0.36), (0.86, 0.44), (0.80, 0.50), (0.78, 0.40)]), 0.012, "YZ", bevel=0.003, bevel_segments=1).translated(s * 0.045, 0, 0)
        plates.append(pl)
    p.add("m_brow_plates", merge(plates), "RH_Obsidian", "mount_head")
    eyes = [g.extrude(np.array([(-0.008, -0.004), (0.008, 0.0), (0.007, 0.005), (-0.008, 0.002)]) * [s, 1], 0.006, 0.0014, 1).rotated(0, s * 18, 0).translated(s * 0.044, 0.836, 0.425) for s in (-1, 1)]
    p.add("m_eyes", merge(eyes), "RH_Glow", "mount_head", bake=False, lod1="keep")
    jaw = g.tube([(0, 0.74, 0.40), (0, 0.71, 0.50)], [0.020, 0.014], sides=6, samples=1, cap="round", cap_steps=1, smooth=False)
    p.add("m_jaw", jaw, "RH_Armour", "mount_head")
    teeth = spikes([((s * 0.012, 0.745, 0.45 + 0.02 * k), (0, 1, 0.1), 0.02, 0.005) for s in (-1, 1) for k in range(3)], seed=3, flat=0.2, sides=4, tip=0.6)
    p.add("m_teeth", teeth, "RH_Frost", "mount_head", lod1=None, tint=lambda P: np.full(len(P), 0.55))
    # curled horns (two turns of twist), frost ridges, glowing inclusions; rising twin crystal spirals
    for s, nm in ((+1, "L"), (-1, "R")):
        hp = mpts([(0.045, 0.86, 0.33), (0.125, 0.90, 0.28), (0.200, 0.84, 0.30), (0.215, 0.74, 0.38), (0.165, 0.69, 0.46), (0.100, 0.72, 0.47)], s)
        horn = g.tube(hp, [0.034, 0.032, 0.028, 0.022, 0.014, 0.006], sides=6, samples=4, cap="round", cap_steps=1, twist=720, up=(0, 1, 0))
        p.add(f"m_horn_{nm}", horn, "RH_Ice", "mount_head", uv_scale=2)
        rib = g.tube(hp, 0.0072, sides=3, samples=3, cap=None, smooth=True, twist=1800, radius_fn=lambda t: 1.0 - 0.7 * t, ellipse=(1, 1)) if False else None
        ridge_pts = helix_path(hp, 0.030, 5, 30)
        p.add(f"m_horn_ridge_{nm}", g.tube(ridge_pts, lambda t: 0.0070 * (1 - 0.6 * t), sides=3, samples=1, cap=None, smooth=False), "RH_Frost", "mount_head", lod1=None, tint=lambda P: np.full(len(P), 0.55))
        cores = [g.superellipsoid((0.012, 0.016, 0.012), 0.8, 0.8, 3, 6).translated(*hp[i]) for i in (1, 2, 3)]
        p.add(f"m_horn_glow_{nm}", merge(cores), "RH_Seam", "mount_head", bake=False, lod1=None)
        sp = mpts([(0.04, 0.89, 0.32), (0.075, 0.95, 0.31), (0.060, 1.01, 0.30), (0.095, 1.07, 0.30)], s)
        spiral = g.tube(helix_path(sp, 0.025, 2, 22), lambda t: 0.020 * (1 - 0.7 * t ** 1.5), sides=6, samples=1, cap="round", cap_steps=1, smooth=False, up=(0, 0, 1))
        p.add(f"m_crystal_spiral_{nm}", spiral, "RH_Ice", "mount_head", uv_scale=2)
        p.add(f"m_spiral_tip_{nm}", spikes([(sp[-1], (s * 0.1, 1, 0), 0.025, 0.010)], seed=3, flat=0.2, sides=5), "RH_Ice", "mount_head", lod1=None)
    # frost mane of icicles along the neck crest + bridle with chains
    p.add("m_mane", spikes([((0, 0.745 + 0.0225 * k, 0.17 + 0.035 * k), (0.0, 0.6, -1.0), 0.05 + 0.02 * (k % 3), 0.0085) for k in range(8)], seed=11, flat=0.3, sides=4, tip=0.5), "RH_Frost", "mount_head", tint=lambda P: np.full(len(P), 0.55))
    for s, nm in ((+1, "L"), (-1, "R")):
        ch = rc.zigzag((s * 0.045, 0.80, 0.44), (s * 0.04, 0.84, 0.22), 6, 0.005, r=0.0035, side=(1, 0, 0), sides=3)
        p.add(f"m_bridle_{nm}", ch, "RH_Silver", "mount_head", lod1=None, tint=lambda P: np.full(len(P), 0.55))
    p.add("m_noseband", g.torus(0.034, 0.0045, 12, 3).rotated(90, 0, 0).scaled(1, 1, 0.9).translated(0, 0.775, 0.47), "RH_Silver", "mount_head", lod1=None, tint=lambda P: np.full(len(P), 0.55))


# ======================================================================================= rider
def rider(p: Piece):
    for s, nm in ((+1, "L"), (-1, "R")):
        lg = mpts([(0.085, 0.76, -0.05), (0.14, 0.66, 0.04), (0.155, 0.56, 0.02)], s)
        p.add(f"r_leg_{nm}", g.tube(lg, [0.022, 0.018, 0.014], sides=6, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Bone", "body", uv_scale=2)
        p.add(f"r_leg_wire_{nm}", merge([rc.helix(0.021, 0.64, 0.69, 2.0, r=0.0030, sides=3, per_turn=7, ax=s * 0.138, az=0.035)]), "RH_Silver", "body", lod1=None)
        greave = g.extrude_plane(np.array([(0.58, 0.01), (0.66, 0.05), (0.67, 0.08), (0.59, 0.05)]), 0.015, "YZ", bevel=0.004, bevel_segments=1).translated(s * 0.157, 0, 0)
        p.add(f"r_greave_{nm}", greave, "RH_Obsidian", "body")
        p.add(f"r_leg_lames_{nm}", rc.limb_lames(lg, [0.022, 0.018, 0.014], [0.30, 0.62, 0.85], h=0.032, sweep=230, grow=0.005, seg=6), "RH_Obsidian", "body")
        p.add(f"r_knee_{nm}", g.superellipsoid((0.028, 0.028, 0.024), 0.5, 0.6, 3, 8).translated(s * 0.145, 0.665, 0.065), "RH_Obsidian", "body")
        p.add(f"r_boot_{nm}", g.superellipsoid((0.028, 0.034, 0.055), 0.5, 0.6, 3, 8).translated(s * 0.16, 0.52, 0.045), "RH_Obsidian", "body")
        p.add(f"r_stirrup_{nm}", g.torus(0.022, 0.0034, 12, 3).rotated(0, 90, 0).translated(s * 0.16, 0.47, 0.045), "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
        p.add(f"r_stirrup_leather_{nm}", g.tube([(s * 0.16, 0.495, 0.045), (s * 0.15, 0.62, 0.0), (s * 0.12, 0.745, -0.04)], 0.0035, sides=3, samples=1, cap=None, smooth=True), "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    p.add("r_pelvis", g.superellipsoid((0.075, 0.038, 0.050), 0.5, 0.6, 4, 10).translated(0, 0.77, -0.05), "RH_Obsidian", "body")
    # spine, five rib pairs, half breastplate (broken), silver binding
    p.add("r_spine", g.tube([(0, 0.80, -0.07), (0, 0.90, -0.065), (0, 1.00, -0.06)], 0.013, sides=5, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)), "RH_Bone", "spine")
    ribs = []
    for k in range(5):
        y = 0.84 + 0.03 * k
        r = 0.075 - 0.004 * abs(k - 2)
        pts = []
        for a in np.linspace(-110, 110, 9):
            pts.append((r * math.sin(math.radians(a)), y, -0.06 + r * 0.85 * math.cos(math.radians(a))))
        ribs.append(g.tube(pts, 0.0065, sides=4, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 1, 0)))
    p.add("r_ribs", merge(ribs), "RH_Ice", "spine")
    bp = g.extrude(np.array([(-0.07, 0.88), (0.09, 0.86), (0.10, 0.97), (0.04, 1.00), (-0.04, 0.96), (-0.075, 0.94)]), 0.016, 0.004, 1)
    bp = bp.subdivided_to(0.05, max_levels=1)

    def curve(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        return np.column_stack([x, y, 0.056 - 0.9 * x * x * 0.6 + z - 0.0 - 0.06 * 0.0 + 0.0 - 0.06])
    p.add("r_breastplate", g.warp(bp, lambda P: np.column_stack([P[:, 0], P[:, 1], 0.058 - 3.0 * P[:, 0] ** 2 + P[:, 2] - 0.05]), 40), "RH_Obsidian", "spine")
    p.add("r_breast_wire", rc.poly_wire([(-0.07, 0.88, 0.0), (0.09, 0.86, 0.0), (0.10, 0.97, 0.0), (0.04, 1.00, 0.0), (-0.04, 0.96, 0.0)], 0.0028, 3, True), "RH_Silver", "spine", lod1=None) if False else None
    p.add("r_collar_ice", cluster((0.0, 1.00, -0.03), (0, 1, 0), 3, (0.03, 0.05), (0.007, 0.010), spread=0.04, tilt=30, seed=2, flat=0.3, sides=4), "RH_Ice", "spine", lod1=None)
    # pauldrons: left large and spiked, right bare bone knob
    pl = g.superellipsoid((0.055, 0.026, 0.055), 0.5, 0.65, 4, 10).translated(0.145, 1.00, -0.04)
    pl2 = g.superellipsoid((0.048, 0.020, 0.048), 0.5, 0.65, 4, 9).rotated(0, 0, -18).translated(0.158, 0.975, -0.04)
    p.add("r_pauldron_L", merge([pl, pl2]), "RH_Obsidian", "arm_L")
    p.add("r_pauldron_L_frost", frost_layer(pl, 0.006, min_ny=0.4, cover=0.3, seed=2), "RH_Frost", "arm_L", lod1=None, tint=lambda P: np.full(len(P), 0.5))
    p.add("r_pauldron_L_spikes", spikes([((0.15 + 0.012 * k, 1.02, -0.05 + 0.03 * k), unit((0.4 + 0.1 * k, 1.0, 0.0)), 0.06 + 0.02 * (k % 2), 0.011) for k in range(3)], seed=4, flat=0.3, sides=5, tip=0.4), "RH_Ice", "arm_L")
    p.add("r_shoulder_R", g.superellipsoid((0.026, 0.020, 0.026), 0.7, 0.7, 3, 8).translated(-0.095, 0.99, -0.05), "RH_Bone", "arm_R")
    # arms: bare bone with silver wire and obsidian vambraces; claws
    for s, nm in ((+1, "L"), (-1, "R")):
        up = mpts([(0.095, 0.98, -0.05), (0.102, 0.94, -0.03), (0.105, 0.90, -0.01)], s)
        if s < 0:
            up = [(-0.095, 0.98, -0.05), (-0.102, 0.94, -0.03), (-0.11, 0.90, 0.0)]
        p.add(f"r_arm_{nm}", g.tube(up, [0.016, 0.014, 0.014], sides=5, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Bone", f"arm_{nm}", uv_scale=2)
        fore = mpts([(0.105, 0.90, -0.01), (0.108, 0.87, 0.04), (0.105, 0.84, 0.07)], s)
        if s < 0:
            fore = [(-0.11, 0.90, 0.0), (-0.145, 0.87, 0.025), (-0.17, 0.84, 0.035)]
        p.add(f"r_forearm_{nm}", g.tube(fore, [0.014, 0.013, 0.012], sides=5, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)), "RH_Bone", f"hand_{nm}", uv_scale=2)
        p.add(f"r_vambrace_{nm}", rc.limb_lames(fore, [0.014, 0.013, 0.012], [0.4, 0.7], h=0.026, sweep=240, grow=0.004, seg=6), "RH_Obsidian", f"hand_{nm}")
        p.add(f"r_arm_wire_{nm}", merge([rc.helix(0.017, 0.90, 0.95, 1.6, r=0.0026, sides=3, per_turn=6, ax=up[1][0], az=up[1][2])]), "RH_Silver", f"arm_{nm}", lod1=None)
    p.add("r_hand_L", rc.claw_hand(+1, np.array([0.105, 0.825, 0.085]), (0.0, -0.5, 1.0), 0.8, 0.8, 1.2), "RH_Bone", "hand_L", uv_scale=2)
    p.add("r_hand_R", rc.claw_hand(-1, np.array([-0.17, 0.835, 0.04]), (0.0, 0.2, 1.0), 0.2, 0.8, 1.0), "RH_Bone", "hand_R", uv_scale=2)
    # skull (bone-white), glowing eyes (focal point 1), crown spikes, cowl + cloak scraps (soft)
    sk = g.superellipsoid((0.041, 0.047, 0.047), 0.8, 0.85, 5, 12).noised(0.002, 30, 2, seed=2).translated(0, 1.040, -0.03)
    jaw = g.superellipsoid((0.024, 0.016, 0.030), 0.6, 0.6, 3, 8).translated(0, 1.005, -0.005)
    p.add("r_skull", merge([sk, jaw]), "RH_Frost", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.6))
    p.add("r_neck", g.tube([(0, 0.99, -0.045), (0, 1.015, -0.035)], 0.014, sides=5, samples=1, cap=None, smooth=False), "RH_Bone", "head")
    eyes = [g.extrude(np.array([(-0.006, -0.002), (0.006, 0.001), (0.0055, 0.0045), (-0.006, 0.002)]) * [s, 1], 0.004, 0.001, 1).translated(s * 0.0215, 1.056, 0.0175) for s in (-1, 1)]
    p.add("r_eyes", merge(eyes), "RH_Glow", "head", bake=False, lod1="keep")
    p.add("r_crown", spikes([((0.040 * math.sin(math.radians(a)), 1.100, -0.03 + 0.036 * math.cos(math.radians(a))), (0.2 * math.sin(math.radians(a)), 1.0, 0.2 * math.cos(math.radians(a))), 0.04 + 0.025 * (k % 3) / 2, 0.0075)
                            for k, a in enumerate((20, 92, 164, 236, 308))], seed=6, flat=0.25, sides=4, tip=0.5), "RH_Ice", "head")
    p.add("r_diadem", g.torus(0.043, 0.0034, 14, 3).translated(0, 1.075, -0.03), "RH_Silver", "head", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    R, K = 8, 8
    rows = []
    for r in range(R):
        v = r / (R - 1)
        row = []
        for k in range(K):
            u = k / (K - 1)
            y = 1.02 - 0.40 * v - ((0.05 if r == R - 1 else 0.012) * (k % 2) if r >= R - 2 else 0)
            xw = 0.075 + 0.085 * v ** 0.8
            z = -0.072 - 0.06 * v ** 1.2 + 0.007 * math.sin(u * TAU * 2.2)
            row.append((-xw + 2 * xw * u, y, z))
        rows.append(row)
    cm = g.loft(np.array(rows)[::-1], closed=False, crease=50, v_tile=0.25, u_tile=0.25)
    p.add("r_cloak", cm, "RH_Cloth", "head", bone2="top", blend=(0.95, 0.70), uv_scale=2)
    # half-helm over the skull with cheek plates and a nasal bar; the crown spikes grow through it
    prof = [(0.046, 1.030), (0.050, 1.050), (0.046, 1.078), (0.030, 1.098), (0.0, 1.106)]
    helm = g.lathe(prof, 8, crease=30).scaled(1.0, 1.0, 1.05).translated(0, 0, -0.03)
    p.add("r_helm", helm, "RH_Obsidian", "head")
    nasal = g.extrude(np.array([(-0.005, 1.0), (0.005, 1.0), (0.0042, 1.066), (-0.0042, 1.066)]), 0.005, 0.001, 1).translated(0, 0, 0.0185)
    p.add("r_nasal", nasal, "RH_Obsidian", "head", lod1=None)
    for sx in (-1, 1):
        ck = g.extrude_plane(np.array([(1.012, -0.02), (1.020, 0.02), (1.050, 0.015), (1.056, -0.025)]), 0.006, "YZ", bevel=0.0015, bevel_segments=1).translated(sx * 0.046, 0, -0.015)
        p.add(f"r_cheek_{'L' if sx > 0 else 'R'}", ck, "RH_Obsidian", "head", lod1=None)
    # faulds + hip lames + tattered tassets
    for sx in (-1, 1):
        fl = [g.superellipsoid((0.032 - 0.004 * i, 0.030, 0.050 - 0.005 * i), 0.5, 0.6, 3, 8).rotated(0, 0, sx * (-20 - 8 * i)).translated(sx * (0.105 + 0.010 * i), 0.775 - 0.030 * i, -0.04) for i in range(3)]
        p.add(f"r_faulds_{'L' if sx > 0 else 'R'}", merge(fl), "RH_Obsidian", "body")
    # rib-cage lames: obsidian bands half-covering the ribs in front
    bands = []
    for y in (0.855, 0.905, 0.955):
        pts = [(0.078 * math.sin(math.radians(a)), y, -0.06 + 0.078 * 0.85 * math.cos(math.radians(a)) + 0.008) for a in np.linspace(-70, 70, 7)]
        bands.append(g.tube(pts, 0.0105, sides=4, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 1, 0)))
    p.add("r_rib_bands", merge(bands), "RH_Obsidian", "spine")
    p.add("r_cloak_frost", cluster((0.04, 0.70, -0.105), (0, -1, -0.3), 3, (0.025, 0.045), (0.007, 0.010), spread=0.05, tilt=30, seed=3, flat=0.3, sides=4), "RH_Frost", "head", bone2="top", blend=(0.95, 0.70), lod1=None)
    # hooked glaive standing at the rider's right: haft with silver wraps, ice blade with a back spike
    haft = g.tube([(-0.17, 0.60, 0.01), (-0.17, 0.95, 0.02), (-0.17, 1.20, 0.02)], [0.015, 0.013, 0.012], sides=6, samples=3, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("r_glaive_haft", haft, "RH_Obsidian", "weapon", uv_scale=2)
    p.add("r_glaive_wraps", merge([g.torus(0.0165, 0.0034, 8, 3).translated(-0.17, y, 0.012 + 0.01 * (y - 0.6)) for y in (0.70, 0.78, 0.92, 0.98, 1.08)]), "RH_Silver", "weapon", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    blade = g.extrude_plane(np.array([(1.15, 0.015), (1.20, 0.06), (1.26, 0.16), (1.30, 0.24), (1.27, 0.20), (1.22, 0.12), (1.18, 0.08), (1.17, 0.02)]), 0.020, "YZ", bevel=0.004, bevel_segments=1).translated(-0.17, 0, 0)
    p.add("r_glaive_blade", blade, "RH_Ice", "weapon", occluder=False)
    p.add("r_glaive_spike", spikes([((-0.17, 1.19, 0.0), (0, 0.5, -1.0), 0.07, 0.011)], seed=3, flat=0.3, sides=5), "RH_Ice", "weapon")
    p.add("r_glaive_collar", g.lathe([(0.013, 1.12), (0.022, 1.13), (0.022, 1.15), (0.013, 1.16)], 8, crease=35).translated(-0.17, 0, 0.02), "RH_Silver", "weapon", tint=lambda P: np.full(len(P), 0.7))
    p.add("r_glaive_butt", spikes([((-0.17, 0.605, 0.01), (0, -1, 0), 0.06, 0.012)], seed=2, flat=0.1, sides=5), "RH_Ice", "weapon")


# ======================================================================================= clips
def make_clips(rig) -> list[Clip]:
    idle = Clip("Idle", 3.4, loop=True)
    idle.keys("mount_head", "rot", [(0, (0, 0, 0)), (1.1, (4, -5, 0), "in_out_cubic"), (2.3, (-1, 3, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.1, (6, 0, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("hand_R", "rot", [(0, (0, 0, 0)), (1.1, (0, 0, 1.5), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("mount_body", "rot", [(0, (0, 0, 0)), (2.3, (-1, 0, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (2.3, (1.2, 0, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (2.3, (0, 4, 0), "in_out_cubic"), (3.4, (0, 0, 0), "in_out_cubic")])

    mv = Clip("Move", 0.8, loop=True)
    mv.keys("mount_body", "rot", [(0, (4, 0, 0)), (0.2, (4, 0, -2), "in_out_cubic"), (0.4, (6, 0, -3), "in_out_cubic"), (0.6, (4, 0, 3), "in_out_cubic"), (0.8, (4, 0, 0), "in_out_cubic")])
    mv.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.1, (0, 0.02, 0), "out_quad"), (0.25, (0, 0, 0), "in_quad"), (0.5, (0, 0.02, 0), "out_quad"), (0.65, (0, 0, 0), "in_quad"), (0.8, (0, 0, 0))])
    mv.keys("mount_head", "rot", [(0, (6, 0, 0)), (0.4, (3, 0, 0), "in_out_cubic"), (0.8, (6, 0, 0), "in_out_cubic")])
    mv.keys("top", "rot", [(0, (0, 0, 0)), (0.4, (-8, 0, 0), "in_out_cubic"), (0.8, (0, 0, 0), "in_out_cubic")])

    A = Clip("Attack", 2.1, fps=60)
    A.keys("mount_body", "rot", [(0, (0, 0, 0)), (0.40, (-22, 0, 0), "in_out_cubic"), (0.55, (-22, 0, 0)), (0.85, (10, 0, 0), "in_out_cubic"), (0.93, (18, 0, 0), "in_cubic"), (1.15, (18, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.40, (0, 0.05, 0), "in_out_cubic"), (0.55, (0, 0.05, 0)), (0.85, (0, 0, 0), "in_out_cubic"), (0.93, (0, 0, 0.10), "in_cubic"), (1.00, (0, 0, 0.10)),
                           (1.05, (0, -0.03, 0.10), "out_quad"), (1.15, (0, -0.03, 0.10)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("mount_head", "rot", [(0, (0, 0, 0)), (0.40, (-24, 0, 0), "in_out_cubic"), (0.55, (-30, 0, 0), "in_out_cubic"), (0.85, (-5, 0, 0), "in_out_cubic"), (0.93, (42, 0, 0), "in_cubic"), (1.15, (42, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.40, (8, 0, 0), "in_out_cubic"), (0.85, (8, 0, 0)), (0.93, (8, 0, 0)), (1.15, (8, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.93, (0, 0, 0)), (1.00, (0, 0, 0.12), "in_cubic"), (1.15, (0, 0, 0.12)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.40, (0, 0, 0)), (0.85, (5, 0, 0), "in_out_cubic"), (1.00, (18, 0, 0), "in_cubic"), (1.15, (18, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.40, (0, 0, 0)), (0.55, (-8, 0, 0), "in_out_cubic"), (0.93, (-8, 0, 0)), (1.00, (6, 0, 0), "in_cubic"), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.40, (-45, 0, 0), "in_out_cubic"), (0.55, (-45, 0, 0)), (0.85, (-55, 0, 0), "in_out_cubic"), (0.93, (-55, 0, 0)), (1.00, (-30, 0, 0), "in_cubic"), (1.15, (-30, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.40, (-45, 0, 0), "in_out_cubic"), (0.93, (-45, 0, 0)), (1.00, (75, 0, 0), "in_cubic"), (1.15, (75, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.40, (-10, 0, 0), "in_out_cubic"), (1.15, (-10, 0, 0)), (2.1, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.40, (16, 0, 0), "in_out_cubic"), (0.93, (16, 0, 0)), (1.05, (-8, 0, 0), "out_quad"), (2.1, (0, 0, 0), "in_out_cubic")])

    hit = Clip("HitReact", 0.45)
    hit.keys("mount_body", "rot", [(0, (0, 0, 0)), (0.10, (-10, 0, 0), "out_cubic"), (0.45, (-3, 0, 0), "in_out_cubic")])
    hit.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.07), "out_cubic"), (0.45, (0, 0, -0.02), "in_out_cubic")])
    hit.keys("mount_head", "rot", [(0, (0, 0, 0)), (0.10, (-22, 0, 0), "out_cubic"), (0.45, (-8, 0, 0), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-10, 0, 0), "out_cubic"), (0.45, (-3, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.10, (-14, 0, 0), "out_cubic"), (0.45, (-4, 0, 0), "in_out_cubic")])
    hit.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.10, (10, 0, 0), "out_cubic"), (0.45, (3, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (14, 0, 0), "out_cubic"), (0.45, (3, 0, 0), "in_out_cubic")])

    vic = Clip("Victory", 1.6)
    vic.keys("mount_body", "rot", [(0, (0, 0, 0)), (0.6, (-20, 0, 0), "out_back"), (1.6, (-20, 0, 0))])
    vic.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.6, (0, 0.05, 0), "out_back"), (1.6, (0, 0.05, 0))])
    vic.keys("mount_head", "rot", [(0, (0, 0, 0)), (0.6, (-22, 0, 0), "out_cubic"), (1.6, (-22, 0, 0))])
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.6, (-150, 0, 0), "out_cubic"), (1.6, (-150, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.6, (10, 0, 0), "out_cubic"), (1.6, (10, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.6, (-10, 0, 0), "out_cubic"), (1.6, (-10, 0, 0))])
    T = Clip("Taunt", 1.6)           # the ram rears, then lowers its crystal horns at the target; rider shakes the glaive
    T.keys("mount_body", "rot", [(0, (0, 0, 0)), (0.45, (-26, 0, 0), "out_cubic"), (0.70, (-26, 0, 0)), (1.0, (6, 0, 0), "in_cubic"), (1.2, (6, 0, 0)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.45, (0, 0.05, 0), "out_cubic"), (0.70, (0, 0.05, 0)), (1.0, (0, -0.01, 0.04), "in_cubic"), (1.2, (0, -0.01, 0.04)), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("mount_head", "rot", [(0, (0, 0, 0)), (0.45, (-30, 0, 0), "out_cubic"), (0.70, (-34, 0, 0)), (1.0, (44, 0, 0), "in_cubic"), (1.1, (40, -6, 0), "in_out_quad"), (1.2, (44, 6, 0), "in_out_quad"), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "rot", [(0, (0, 0, 0)), (0.45, (8, 0, 0), "out_cubic"), (1.0, (-4, 0, 0), "in_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("spine", "rot", [(0, (0, 0, 0)), (0.70, (0, 0, 0)), (1.0, (12, 0, 0), "in_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.45, (-35, 0, 0), "out_cubic"), (0.70, (-70, 0, 0), "in_out_cubic"), (1.0, (-30, 0, 0), "in_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.70, (-20, 0, 0), "in_out_cubic"), (1.0, (30, 0, 0), "in_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("head", "rot", [(0, (0, 0, 0)), (0.45, (-8, 0, 0), "out_cubic"), (1.0, (8, 12, 0), "in_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.45, (14, 0, 0), "out_cubic"), (1.0, (-8, 0, 0), "in_cubic"), (1.6, (0, 0, 0), "in_out_cubic")])
    S = Clip("Surrender", 2.2)       # the ram lowers its horns, the rider slumps; the glaive falls, bounces and settles beside the ram
    S.keys("mount_body", "rot", [(0, (0, 0, 0)), (0.8, (4, 0, 0), "in_out_cubic"), (2.2, (5, 0, 0))])
    S.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.8, (0, -0.02, 0.0), "in_out_cubic"), (2.2, (0, -0.025, 0))])
    S.keys("mount_head", "rot", [(0, (0, 0, 0)), (0.9, (34, 0, 0), "in_out_cubic"), (2.2, (40, 0, 0))])
    S.keys("spine", "rot", [(0, (0, 0, 0)), (0.9, (18, 0, 0), "in_out_cubic"), (2.2, (22, 0, 0))])
    S.keys("head", "rot", [(0, (0, 0, 0)), (0.9, (30, 0, 0), "in_out_cubic"), (2.2, (36, 0, 0))])
    S.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.5, (-8, 0, 0), "in_out_cubic"), (1.1, (14, 0, 0), "in_out_cubic"), (2.2, (18, 0, 0))])
    S.keys("hand_R", "rot", [(0, (0, 0, 0)), (1.1, (8, 0, 0), "in_out_cubic"), (2.2, (10, 0, 0))])
    S.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.9, (14, 0, 0), "in_out_cubic"), (2.2, (18, 0, 0))])
    S.keys("top", "rot", [(0, (0, 0, 0)), (0.9, (16, 0, 0), "in_out_cubic"), (2.2, (12, 0, 0))])
    rc.drop_weapon(S, rig, "weapon", 0.45, (0, 1, 0), 0.22, 0.02, (0.1, 0.0, 1.0), land_xz=(-0.23, 0.0))
    return [idle, mv, A, hit, vic, T, S]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "knight", rig, make_clips(rig), impact_time=1.00, strike_range=0.50, attack_style="leap", seed=10)
    rc.pedestal_parts(p)
    mount_body(p)
    mount_head(p)
    rider(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
