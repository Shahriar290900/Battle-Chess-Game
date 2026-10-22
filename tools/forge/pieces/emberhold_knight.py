"""emberhold_knight - Emberhold Ashmane Rider.

An armoured rider on a heavy barded highland war-elk.  The elk is built from swept, tapered limbs (shoulder / elbow / knee /
fetlock with split hooves and bronze greaves), a deep barrel under an oxblood saddle blanket, layered bronze barding (peytral
with lames, flank plates, segmented crinet, chanfron), a long neck with an ember mane, and broad forward-swept palmate antlers
with tines, bronze tip caps and ridged horn rings.  The rider sits upright in a stitched saddle: cuirass, asymmetric fur mantle,
big/small pauldrons, helm with crest, and a pennoned lance couched on the right.  Built from docs/art/emberhold_knight.md.
Bones: root, mount_body (elk), mount_head (neck/head/antlers), body/spine/head/arms (rider), top (mane, soft with mount_head).
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

ASSET_ID = "emberhold_knight"
COAT = lambda P: np.full(len(P), 0.72)             # ash-coat tint for the elk's fur


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("mount_body", "root", (0, 0.60, 0))
    r.add("mount_head", "mount_body", (0, 0.76, 0.20))
    r.add("body", "mount_body", (0, 0.78, -0.04))
    r.add("spine", "body", (0, 0.84, -0.04))
    r.add("head", "spine", (0, 1.07, -0.02))
    r.add("top", "body", (0, 0.82, 0.12))
    r.add("arm_L", "spine", (0.105, 1.04, -0.03))
    r.add("hand_L", "arm_L", (0.115, 0.95, 0.03))
    r.add("arm_R", "spine", (-0.105, 1.04, -0.03))
    r.add("hand_R", "arm_R", (-0.12, 0.95, 0.04))
    r.socket("socket_weapon_R", "hand_R", (-0.16, 1.30, 0.44))
    r.socket("socket_cast", "mount_head", (0, 1.00, 0.36))
    r.socket("socket_impact", "body", (-0.10, 0.75, 0.58))
    r.socket("socket_head", "head", (0, 1.20, 0))
    return r


# ---- elk barrel: centreline (z, y) and half-size so plates / blanket can follow it
BZ = np.array([-0.30, -0.20, -0.05, 0.10, 0.19])
BY = np.array([0.640, 0.630, 0.620, 0.600, 0.598])
BR = np.array([0.118, 0.140, 0.142, 0.150, 0.146])
ELL = (1.18, 0.84)                                  # (vertical, horizontal) scale of the barrel section


def b_y(z):
    return float(np.interp(z, BZ, BY))


def b_r(z):
    return float(np.interp(z, BZ, BR))


def barrel_pt(z, theta_deg, grow=0.0):
    """Point on the barrel surface: theta 0 = top, +90 = +X side."""
    t = math.radians(theta_deg)
    r = b_r(z) + grow
    return np.array([r * ELL[1] * math.sin(t), b_y(z) + r * ELL[0] * math.cos(t), z])


def barrel_arc(zs, grows, a0, a1, K=18):
    rings = []
    for z, gr in zip(zs, np.broadcast_to(np.asarray(grows, float), (len(zs),))):
        rings.append([barrel_pt(z, a, gr) for a in np.linspace(a0, a1, K)])
    m = g.loft(np.array(rings), closed=False, crease=55, v_tile=0.25, u_tile=0.25)
    return fix_out(m)


def fix_out(m, axis=2):
    """Flip an open shell if its normals mostly point toward the barrel axis."""
    c = m.P.copy()
    c[:, 0] = 0.0
    c[:, 1] = np.array([b_y(z) for z in m.P[:, 2]])
    fn = m.face_normals()
    cen = m.P[m.F].mean(1)
    cc = cen.copy()
    cc[:, 0] = 0.0
    cc[:, 1] = np.array([b_y(z) for z in cen[:, 2]])
    if np.mean(np.einsum("ij,ij->i", fn, cen - cc)) < 0:
        return m.flipped()
    return m


# ======================================================================================= elk body
def limb(p, name, pts, radii, bone, mat="EH_Fur", sides=10, tint=COAT, ellipse=(1, 1), up=(1, 0, 0), samples=3, cap="round", uv=2, noise=0.0035):
    m = g.tube(pts, radii, sides=sides, samples=samples, cap=cap, cap_steps=1, up=up, ellipse=ellipse)
    if noise:
        m = m.noised(noise, 24, 2, seed=abs(hash(name)) % 97)
    p.add(name, m, mat, bone, uv_scale=uv, tint=tint if mat == "EH_Fur" else None)


def elk_body(p: Piece):
    path = [(0, b_y(z), z) for z in (-0.30, -0.20, -0.05, 0.045)]
    barrel = g.tube(path, [b_r(z) for z in (-0.30, -0.20, -0.05, 0.045)], sides=14, samples=3, cap="round", cap_steps=2, up=(0, 1, 0), ellipse=ELL).noised(0.003, 18, 3, seed=2)
    p.add("m_barrel", barrel, "EH_Fur", "mount_body", uv_scale=2, tint=COAT)
    # haunches and shoulders: big muscle masses that make the legs grow out of the body
    for s in (-1, 1):
        n = "L" if s > 0 else "R"
        ha = g.superellipsoid((0.070, 0.116, 0.115), 0.85, 0.9, 6, 12).rotated(-8, 0, 0).translated(s * 0.112, 0.605, -0.200).noised(0.004, 16, 2, seed=3 + s)
        sh = g.superellipsoid((0.060, 0.105, 0.092), 0.85, 0.9, 6, 12).rotated(10, 0, 0).translated(s * 0.112, 0.610, 0.150).noised(0.004, 16, 2, seed=5 + s)
        p.add(f"m_haunch_{n}", ha, "EH_Fur", "mount_body", uv_scale=2, tint=COAT)
        p.add(f"m_shoulder_{n}", sh, "EH_Fur", "mount_body", uv_scale=2, tint=COAT)
    hump = g.superellipsoid((0.075, 0.060, 0.115), 0.8, 0.9, 5, 11).translated(0, 0.752, 0.105).noised(0.005, 14, 3, seed=7)
    p.add("m_withers", hump, "EH_Fur", "mount_body", uv_scale=2, tint=COAT)
    rump = g.superellipsoid((0.120, 0.135, 0.100), 0.8, 0.85, 6, 14).translated(0, 0.640, -0.250).noised(0.005, 14, 3, seed=9)
    p.add("m_rump", rump, "EH_Fur", "mount_body", uv_scale=2, tint=COAT)
    # legs: shoulder -> elbow -> knee -> cannon -> fetlock -> hoof, tapered, with joint swellings, greaves and split hooves
    for s in (-1, 1):
        n = "L" if s > 0 else "R"
        x = s * 0.115
        # foreleg (weight on the left foreleg: right knee a little bent)
        bend = 0.02 if s < 0 else 0.0
        pf = [(x, 0.600, 0.150), (x, 0.470, 0.170 + bend), (x, 0.350, 0.190 + bend * 1.5), (x + s * 0.002, 0.300, 0.197), (x, 0.262, 0.202)]
        limb(p, f"m_foreleg_{n}", pf, [0.056, 0.040, 0.027, 0.0225, 0.027], "mount_body", up=(0, 0, 1))
        knee = g.superellipsoid((0.030, 0.034, 0.030), 0.7, 0.7, 4, 9).translated(x, 0.355, 0.193 + bend * 1.5)
        pastern = g.superellipsoid((0.026, 0.026, 0.030), 0.7, 0.7, 3, 8).translated(x, 0.272, 0.203)
        p.add(f"m_foreknee_{n}", merge([knee, pastern]), "EH_Fur", "mount_body", uv_scale=2, tint=COAT)
        hoof = g.superellipsoid((0.034, 0.020, 0.040), 0.45, 0.55, 3, 9).translated(x, 0.238, 0.208)
        dew = [g.superellipsoid((0.007, 0.007, 0.010), 0.6, 0.6, 3, 6).translated(x + k * 0.022, 0.275, 0.186) for k in (-1, 1)]
        p.add(f"m_forehoof_{n}", merge([hoof] + dew), "EH_Steel", "mount_body", uv_scale=2)
        gr = g.tube([(x, 0.328, 0.192 + bend * 1.5), (x, 0.292, 0.198), (x, 0.262, 0.202)], [0.0275, 0.0262, 0.0305], sides=9, samples=1, cap=None, smooth=False)
        p.add(f"m_foregreave_{n}", gr, "EH_Bronze", "mount_body")
        # hind leg with a hock
        ph = [(x + s * 0.005, 0.620, -0.200), (x + s * 0.016, 0.470, -0.130), (x, 0.360, -0.228), (x, 0.290, -0.215), (x, 0.262, -0.200)]
        limb(p, f"m_hindleg_{n}", ph, [0.066, 0.046, 0.030, 0.024, 0.028], "mount_body", up=(0, 0, 1))
        hock = g.superellipsoid((0.030, 0.040, 0.040), 0.7, 0.7, 4, 9).translated(x, 0.360, -0.240)
        pst = g.superellipsoid((0.026, 0.026, 0.030), 0.7, 0.7, 3, 8).translated(x, 0.272, -0.205)
        p.add(f"m_hock_{n}", merge([hock, pst]), "EH_Fur", "mount_body", uv_scale=2, tint=COAT)
        hh = g.superellipsoid((0.034, 0.020, 0.040), 0.45, 0.55, 3, 9).translated(x, 0.238, -0.198)
        p.add(f"m_hindhoof_{n}", hh, "EH_Steel", "mount_body", uv_scale=2)
        gh = g.tube([(x, 0.332, -0.222), (x, 0.292, -0.213), (x, 0.262, -0.201)], [0.0285, 0.0262, 0.0305], sides=9, samples=1, cap=None, smooth=False)
        p.add(f"m_hindgreave_{n}", gh, "EH_Bronze", "mount_body")
        # greave rolled lips
        for q, (y, zz) in enumerate(((0.328, 0.192 + bend * 1.5), (0.262, 0.202))):
            p.add(f"m_forelip_{n}{q}", g.torus(0.0312, 0.0040, 12, 4).translated(x, y, zz), "EH_Bronze", "mount_body", lod1=None)
        for q, (y, zz) in enumerate(((0.332, -0.222), (0.262, -0.201))):
            p.add(f"m_hindlip_{n}{q}", g.torus(0.0318, 0.0040, 12, 4).translated(x, y, zz), "EH_Bronze", "mount_body", lod1=None)
    # tail: heavy fur tail with an ember tuft
    tail = g.tube([(0, 0.650, -0.292), (0, 0.610, -0.322), (0.006, 0.545, -0.343), (0.016, 0.465, -0.350)], [0.030, 0.040, 0.026, 0.012], sides=7, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("m_tail", tail.noised(0.008, 16, 3, seed=9), "EH_Fur", "mount_body", uv_scale=2, tint=COAT)
    tuft = g.tube([(0.016, 0.476, -0.350), (0.020, 0.428, -0.356), (0.022, 0.392, -0.358)], [0.016, 0.012, 0.0], sides=5, samples=1, cap=None, smooth=False)
    p.add("m_tail_ember", tuft, "EH_Flame", "mount_body", bake=False, lod1="keep")


def barding(p: Piece):
    # --- peytral: chest plate hanging below the neck with three overlapping lames
    pey = g.plate(0.250, 0.250, 0.017, 0.008, bend_r=0.155, inner_x=1, taper=lambda t: 1 - 0.34 * (t + 1) / 2, drop_back=True)
    pey = pey.rotated(-14, 0, 0).translated(0, 0.605, 0.178)
    p.add("m_peytral", pey, "EH_Bronze", "mount_body")
    lames = []
    for i in range(3):
        l = g.plate(0.210 - 0.045 * i, 0.058, 0.012, 0.005, bend_r=0.14, inner_x=1, drop_back=True)
        lames.append(l.rotated(-10 - 5 * i, 0, 0).translated(0, 0.462 - 0.046 * i, 0.172 + 0.006 * i))
    p.add("m_peytral_lames", merge(lames), "EH_Bronze", "mount_body")
    # peytral boss with the Emberhold anvil
    boss = g.lathe(np.array([(0, 0), (0.030, 0), (0.033, 0.005), (0.026, 0.014), (0, 0.016)]), 18, crease=45).rotated(78, 0, 0).translated(0, 0.585, 0.222)
    anv = g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 0.55, 0.005, 0.0, 1).rotated(-14, 0, 0).translated(0, 0.585, 0.240)
    p.add("m_peytral_boss", merge([boss, anv]), "EH_Steel", "mount_body", lod1=None)
    rv = [(x, 0.62 + dy, 0.2175) for x in (-0.085, 0.085) for dy in (0.06, -0.01, -0.08)]
    p.add("m_peytral_rivets", g.instances(g.dome(0.0072, 0.005, 6, 1), rv, [(0, 0.2, 1)] * len(rv)), "EH_Bronze", "mount_body", lod1=None)
    # --- flank plates: four overlapping, per side
    for s, n in ((1, "L"), (-1, "R")):
        pls = []
        for k in range(4):
            z = 0.060 - k * 0.095
            pl = g.plate(0.105, 0.150, 0.012, 0.006, bend_r=0.16, inner_x=1, drop_back=True)
            pl = pl.rotated(0, 90 * s, 0).translated(s * (b_r(z) * ELL[1] + 0.015), b_y(z) - 0.020, z)
            pls.append(pl)
        p.add(f"m_flank_{n}", merge(pls), "EH_Bronze", "mount_body")
        rim = g.tube([(s * (b_r(z) * ELL[1] + 0.028), b_y(z) - 0.095, z) for z in (0.08, 0.0, -0.1, -0.2, -0.29)], 0.0070, sides=5, samples=2, cap="round", cap_steps=1)
        p.add(f"m_flank_rim_{n}", rim, "EH_Bronze", "mount_body", lod1=None)
    # --- blanket: oxblood saddle cloth over the barrel with a scalloped, stitched hem
    zs = np.linspace(0.06, -0.24, 9)
    rings = []
    for z in zs:
        row = []
        for a in np.linspace(-98, 98, 17):
            t = abs(a) / 98
            pt = barrel_pt(z, a, 0.011 + 0.006 * t)
            row.append(pt)
        rings.append(row)
    bl = fix_out(g.loft(np.array(rings), closed=False, crease=60, v_tile=0.25, u_tile=0.25))
    p.add("m_blanket", bl.noised(0.003, 14, 2, seed=11), "EH_Cloth", "mount_body", uv_scale=2, tint=lambda P: (0.45 + 0.55 * smoothstep(0.50, 0.74, P[:, 1]))[:, None] * np.array([1.1, 0.98, 0.88]))
    for s, n in ((1, "L"), (-1, "R")):
        trim = g.tube([barrel_pt(z, 98 * s, 0.017) for z in zs], 0.0060, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
        p.add(f"m_blanket_trim_{n}", trim, "EH_Bronze", "mount_body", lod1=None)
    # --- saddle with cantle, pommel, stitched edge and girth
    sad = g.superellipsoid((0.100, 0.026, 0.118), 0.55, 0.6, 5, 12).translated(0, 0.800, -0.040)
    cant = g.superellipsoid((0.092, 0.040, 0.016), 0.5, 0.6, 4, 10).translated(0, 0.822, -0.158)
    pom = g.superellipsoid((0.032, 0.034, 0.022), 0.55, 0.6, 4, 10).translated(0, 0.822, 0.082)
    p.add("m_saddle", merge([sad, cant, pom]), "EH_Leather", "body", uv_scale=2)
    stitch = [g.tube([(s * 0.098 * math.cos(t), 0.806, -0.040 + 0.112 * math.sin(t)) for t in np.linspace(-1.2, 1.2, 8)], 0.0030, sides=4, samples=1, cap="round", cap_steps=1) for s in (-1, 1)]
    p.add("m_saddle_stitch", merge(stitch), "EH_Bronze", "body", lod1=None)
    for s, n in ((1, "L"), (-1, "R")):
        girth = g.tube([(s * 0.150, 0.690, -0.020), (s * 0.166, 0.610, -0.020), (s * 0.172, 0.520, -0.008)], 0.0085, sides=5, samples=2, cap="round", cap_steps=1, ellipse=(1.0, 0.45), up=(0, 0, 1))
        p.add(f"m_stirrup_strap_{n}", girth, "EH_Leather", "mount_body", uv_scale=2)
        ring = g.torus(0.026, 0.0045, 14, 4).rotated(0, 90, 0).translated(s * 0.172, 0.494, -0.004)
        p.add(f"m_stirrup_{n}", ring, "EH_Steel", "mount_body", lod1=None)


def elk_neck_head(p: Piece):
    neck_path = [(0, 0.725, 0.165), (0, 0.800, 0.220), (0, 0.870, 0.282), (0, 0.925, 0.340)]
    neck = g.tube(neck_path, [0.100, 0.088, 0.075, 0.064], sides=12, samples=3, cap=None, up=(1, 0, 0), ellipse=(1.0, 0.85)).noised(0.005, 16, 3, seed=13)
    p.add("m_neck", neck, "EH_Fur", "mount_head", uv_scale=2, tint=COAT, bone2="mount_body", blend=(0.74, 0.86))
    # crinet: segmented bronze collar rings that follow the neck (each a little proud of the last)
    ring = np.array(neck_path)
    segs = []
    for i, (u, rr) in enumerate(((0.12, 0.112), (0.30, 0.100), (0.48, 0.089), (0.66, 0.079), (0.84, 0.070))):
        k = np.array(g.spline(ring, 12)[int(u * 35)])
        k2 = np.array(g.spline(ring, 12)[min(int(u * 35) + 3, 35)])
        d = C.unit(k2 - k)
        seg = g.tube([k - d * 0.020, k + d * 0.020], rr, sides=12, samples=1, cap=None, smooth=False, ellipse=(1.0, 0.85), up=(1, 0, 0))
        segs.append(seg)
    p.add("m_crinet", merge(segs).noised(0.0012, 30, 2, seed=15), "EH_Bronze", "mount_head")
    ribs = [g.tube([np.array(g.spline(ring, 12)[int(u * 35)]) + [0, 0.002, 0] - C.unit(np.array(g.spline(ring, 12)[min(int(u * 35) + 3, 35)]) - np.array(g.spline(ring, 12)[int(u * 35)])) * 0.022 * 1.0,
                    np.array(g.spline(ring, 12)[int(u * 35)]) + C.unit(np.array(g.spline(ring, 12)[min(int(u * 35) + 3, 35)]) - np.array(g.spline(ring, 12)[int(u * 35)])) * 0.022], rr + 0.004,
                   sides=12, samples=1, cap=None, smooth=False, ellipse=(1.0, 0.85), up=(1, 0, 0)) for u, rr in ((0.12, 0.112), (0.48, 0.089), (0.84, 0.070))]
    p.add("m_crinet_lips", merge([r_.scaled(1.0, 1.0, 1.0) for r_ in ribs]), "EH_Steel", "mount_head", lod1=None)
    # skull, jaw, muzzle
    skull = g.tube([(0, 0.930, 0.335), (0, 0.892, 0.430), (0, 0.845, 0.505)], [0.064, 0.052, 0.038], sides=11, samples=3, cap="round", cap_steps=2, up=(1, 0, 0), ellipse=(1.0, 0.90))
    p.add("m_skull", skull.noised(0.0035, 22, 2, seed=16), "EH_Fur", "mount_head", uv_scale=2, tint=COAT)
    muzzle = g.superellipsoid((0.036, 0.034, 0.046), 0.65, 0.7, 5, 10).translated(0, 0.822, 0.528)
    jaw = g.tube([(0, 0.870, 0.370), (0, 0.832, 0.455), (0, 0.806, 0.520)], [0.040, 0.030, 0.026], sides=8, samples=2, cap="round", cap_steps=1, up=(1, 0, 0), ellipse=(0.8, 1.0))
    nos = g.instances(g.dome(0.0082, 0.006, 6, 1).rotated(90, 0, 0), [(s * 0.016, 0.826, 0.573) for s in (-1, 1)], [(0, 0, 1)] * 2)
    p.add("m_muzzle", merge([muzzle, jaw]).noised(0.002, 26, 2, seed=17), "EH_Fur", "mount_head", uv_scale=2, tint=COAT)
    p.add("m_nostrils", nos, "EH_Steel", "mount_head", lod1=None)
    for s, n in ((1, "L"), (-1, "R")):
        ear = g.superellipsoid((0.034, 0.010, 0.018), 0.6, 0.7, 3, 8).rotated(0, 0, -s * 24).rotated(-18, 0, 0).translated(s * 0.074, 0.947, 0.312)
        p.add(f"m_ear_{n}", ear, "EH_Fur", "mount_head", uv_scale=2, tint=COAT)
    # chanfron: bronze face plate with a ridge and rivets, rolled eye guards
    fp = g.extrude_plane(np.array([(0.945, 0.360), (0.935, 0.455), (0.885, 0.530), (0.832, 0.548), (0.872, 0.452), (0.918, 0.368)]), 0.066, "YZ", bevel=0.010, bevel_segments=2)
    fp = g.warp(fp, lambda P: np.column_stack([P[:, 0], P[:, 1] + 0.006 - 0.5 * (P[:, 0] / 0.04) ** 2 * 0.0, P[:, 2]]), 50)
    p.add("m_chanfron", fp.noised(0.0010, 34, 2, seed=18), "EH_Bronze", "mount_head")
    ridge = g.tube([(0, 0.958, 0.352), (0, 0.918, 0.455), (0, 0.874, 0.532)], [0.0075, 0.0085, 0.0075], sides=5, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("m_chanfron_ridge", ridge, "EH_Steel", "mount_head", lod1=None)
    eg = [g.torus(0.0255, 0.0050, 12, 4).rotated(0, 0, 90).rotated(0, 18 * s, 0).translated(s * 0.059, 0.914, 0.432) for s in (-1, 1)]
    p.add("m_eyeguards", merge(eg), "EH_Bronze", "mount_head", lod1=None)
    eyes = [g.superellipsoid((0.0095, 0.0125, 0.0160), 0.7, 0.7, 3, 7).translated(s * 0.0555, 0.914, 0.432) for s in (-1, 1)]
    p.add("m_eyes", merge(eyes), "EH_Gem", "mount_head", lod1="keep", bake=False)
    rv = g.instances(g.dome(0.0065, 0.0045, 6, 1), [(s * 0.030, 0.915 - 0.0 * s, 0.440) for s in (-1, 1)] + [(0, 0.895, 0.470)], [(s * 0.6, 1, 0.2) for s in (-1, 1)] + [(0, 1, 0.3)])
    p.add("m_chanfron_rivets", rv, "EH_Bronze", "mount_head", lod1=None)


def palm_mesh(s, centre, tilt_deg):
    """A cupped, lobed palm: a flattened superellipsoid whose plan outline grows finger lobes toward the outer/forward edge."""
    m = g.superellipsoid((0.056, 0.012, 0.066), 0.7, 0.7, 6, 20)
    lobes = (-0.45, 0.45, 1.35, 2.25)

    def f(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        th = np.arctan2(z, x)
        k = 1.0 + sum(0.62 * np.exp(-(((th - a + math.pi) % TAU - math.pi) / 0.20) ** 2) for a in lobes)
        x2, z2 = x * k, z * k
        y2 = y + 0.85 * (x2 * x2 + z2 * z2) - 0.0
        return np.column_stack([x2, y2, z2])
    m = g.warp(m, f, 50)
    m = m.rotated(0, 0, -s * tilt_deg)
    if s < 0:
        m = m.mirrored("x")
    return m.translated(*centre)


def antlers(p: Piece):
    for s, n in ((1, "L"), (-1, "R")):
        pc = np.array([s * 0.150, 1.052, 0.424])
        beam_path = [(s * 0.050, 0.978, 0.338), (s * 0.090, 1.010, 0.360), (s * 0.126, 1.036, 0.392), tuple(pc + [-s * 0.01, -0.004, -0.012])]
        beam = g.tube(beam_path, [0.026, 0.0245, 0.0225, 0.0200], sides=9, samples=4, cap="round", cap_steps=1, up=(0, 1, 0))
        p.add(f"m_antler_beam_{n}", beam.noised(0.0018, 34, 2, seed=20 + s), "EH_Leather", "mount_head", uv_scale=2)
        palm = palm_mesh(s, pc, 22).noised(0.0007, 30, 2, seed=22 + s)
        p.add(f"m_antler_palm_{n}", palm, "EH_Leather", "mount_head", uv_scale=2)
        # fan of tines: from the lobe tips outward / forward / up, curved, with bronze caps
        tines, caps = [], []
        for k, (ang, ext, up_, ln) in enumerate(((-0.45, 0.092, 0.55, 0.095), (0.45, 0.100, 0.70, 0.105), (1.35, 0.104, 0.85, 0.100), (2.25, 0.090, 0.95, 0.088))):
            dx, dz = math.cos(ang), math.sin(ang)
            base = pc + np.array([s * dx * ext * 0.80, 0.020 + 0.5 * (ext * 0.8) ** 2 * 0.85 * 6, dz * ext * 0.80])
            d = C.unit(np.array([s * dx, up_, dz * 0.9]))
            p1 = base + d * ln * 0.45 + np.array([0, 0.004, 0])
            p2 = base + d * ln * 0.85 + np.array([0, 0.012, 0.012])
            tines.append(g.tube([base, p1, p2], [0.0125, 0.0100, 0.0030], sides=6, samples=2, cap=None, smooth=True))
            dd = C.unit(p2 - p1)
            caps.append(g.cone(0.0105, 0.022, 6).aimed(dd, p2 - dd * 0.016))
        p.add(f"m_antler_tines_{n}", merge(tines), "EH_Leather", "mount_head", uv_scale=2)
        p.add(f"m_antler_tipcaps_{n}", merge(caps), "EH_Bronze", "mount_head", lod1=None)
        # brow tine + a rear tine (back of the beam)
        brow = g.tube([(s * 0.068, 0.990, 0.352), (s * 0.080, 1.000, 0.404), (s * 0.082, 1.020, 0.454)], [0.017, 0.012, 0.003], sides=6, samples=2, cap=None, smooth=True)
        rear = g.tube([(s * 0.088, 1.020, 0.350), (s * 0.130, 1.052, 0.316), (s * 0.168, 1.090, 0.290)], [0.016, 0.011, 0.003], sides=6, samples=2, cap=None, smooth=True)
        p.add(f"m_antler_brow_{n}", merge([brow, rear]), "EH_Leather", "mount_head", lod1=None, uv_scale=2)
        rings = []
        for u, rr in ((0.20, 0.0295), (0.50, 0.0270), (0.80, 0.0250)):
            q = g.spline(np.array(beam_path), 5)
            i = int(u * (len(q) - 1))
            d = q[min(i + 1, len(q) - 1)] - q[i]
            rings.append(g.torus(rr, 0.0052, 12, 4).aimed(d, q[i]))
        p.add(f"m_antler_rings_{n}", merge(rings), "EH_Bronze", "mount_head", lod1=None)
        cuff = g.tube([(s * 0.044, 0.972, 0.334), (s * 0.064, 0.990, 0.348)], [0.038, 0.033], sides=10, samples=1, cap=None, smooth=False, up=(0, 1, 0))
        p.add(f"m_antler_cuff_{n}", cuff, "EH_Bronze", "mount_head")
        # bronze inlay band across the palm
        inl = g.torus(0.050, 0.0045, 16, 4, arc=200).rotated(90, 0, 0)
        inl = inl.rotated(0, 0, -s * 22).translated(*(pc + [0, 0.010, 0]))
        p.add(f"m_antler_inlay_{n}", inl, "EH_Bronze", "mount_head", lod1=None)


def mane(p: Piece):
    """Ember mane: two staggered rows of long tapering clumps streaming back along the neck crest, fur at the root burning to
    ember at the tips (separate EH_Flame tips so the glow stays restrained)."""
    rng = np.random.default_rng(31)
    neck = np.array(g.spline(np.array([(0, 0.735, 0.140), (0, 0.800, 0.200), (0, 0.880, 0.270), (0, 0.968, 0.322)]), 6))
    fur, ember = [], []
    n = 22
    for i in range(n):
        u = i / (n - 1)
        base = neck[int(u * (len(neck) - 1))] + [0.012 * (-1) ** i, 0.022, 0]
        L = 0.150 + 0.100 * rng.random() * (0.6 + 0.8 * (1 - u))
        d = C.unit(np.array([(rng.random() - 0.5) * 0.9 + 0.35 * (-1) ** i, 0.55 - 0.25 * u, -1.0]))
        side = np.array([1.0 if (i % 2) else -1.0, 0, 0]) * 0.016
        p1 = base + d * L * 0.36 + side
        p2 = base + d * L * 0.68 - side * 0.5 + [0, -0.020, 0]
        p3 = base + d * L + side * 0.8 + [0, -0.055, 0]
        fur.append(g.tube([base, p1, p2], [0.020, 0.017, 0.012], sides=5, samples=2, cap="round", cap_steps=1, smooth=True, up=(1, 0, 0)))
        ember.append(g.tube([p2, p3], [0.012, 0.0018], sides=5, samples=2, cap="round", cap_steps=1, smooth=True, up=(1, 0, 0)))
    p.add("m_mane", merge(fur).noised(0.0028, 26, 2, seed=32), "EH_Fur", "top", bone2="mount_head", blend=(0.74, 0.86), uv_scale=2, tint=lambda P: np.full(len(P), 0.8))
    p.add("m_mane_ember", merge(ember), "EH_Flame", "top", bone2="mount_head", blend=(0.74, 0.86), lod1="keep", bake=False)
    # a ridge of smaller embers along the barrel's back (withers)
    back = []
    for i in range(5):
        z = 0.085 - i * 0.045
        base = np.array([0, 0.790 - 0.012 * i, z])
        L = 0.075 + 0.03 * rng.random()
        back.append(g.tube([base, base + [0.008 * (-1) ** i, L * 0.6, -L * 0.3], base + [0.0, L, -L * 0.7]], [0.014, 0.010, 0.002], sides=5, samples=1, cap="round", cap_steps=1, smooth=True, up=(1, 0, 0)))
    p.add("m_back_embers", merge(back), "EH_Flame", "top", bake=False, lod1=None)


# ======================================================================================= rider
RB = C.Body(Y=[0.78, 0.84, 0.90, 0.96, 1.02, 1.06, 1.09], RX=[0.105, 0.100, 0.108, 0.122, 0.132, 0.120, 0.075],
            RZ=[0.082, 0.078, 0.084, 0.092, 0.094, 0.086, 0.062], ZC=[-0.04] * 7)


def rider(p: Piece):
    # legs: thigh along the elk's flank, knee forward, greave to the stirrup
    for s, n in ((1, "L"), (-1, "R")):
        thigh = g.tube([(s * 0.095, 0.800, -0.045), (s * 0.150, 0.730, 0.050), (s * 0.188, 0.652, 0.085)], [0.050, 0.046, 0.040], sides=9, samples=2, cap="round", cap_steps=1, up=(0, 1, 0))
        p.add(f"r_thigh_{n}", thigh, "EH_Cloth", "body", uv_scale=2)
        calf = g.tube([(s * 0.188, 0.652, 0.085), (s * 0.196, 0.575, 0.062), (s * 0.192, 0.512, 0.040)], [0.040, 0.034, 0.030], sides=9, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"r_calf_{n}", calf, "EH_Cloth", "body", uv_scale=2)
        greave = g.tube([(s * 0.194, 0.622, 0.078), (s * 0.198, 0.560, 0.060), (s * 0.194, 0.510, 0.040)], [0.046, 0.040, 0.034], sides=9, samples=2, cap=None, up=(0, 0, 1))
        p.add(f"r_greave_{n}", greave.noised(0.0016, 32, 2, seed=40 + s), "EH_Bronze", "body")
        cop = g.superellipsoid((0.038, 0.034, 0.032), 0.65, 0.65, 4, 9).translated(s * 0.190, 0.652, 0.112)
        fin = g.extrude_plane(np.array([(0.630, 0.080), (0.630, 0.126), (0.670, 0.118), (0.678, 0.090)]), 0.008, "YZ", bevel=0.003, bevel_segments=1).translated(s * 0.226, 0, 0)
        p.add(f"r_kneecop_{n}", merge([cop, fin]), "EH_Bronze", "body")
        boot = g.superellipsoid((0.040, 0.034, 0.075), 0.55, 0.62, 4, 9).rotated(14, 0, 0).translated(s * 0.192, 0.498, 0.075)
        p.add(f"r_boot_{n}", boot, "EH_Leather", "body", uv_scale=2)
    # torso: gambeson, cuirass with ridge, backplate, belt
    gam = RB.loft([0.80, 0.86, 0.92, 0.98, 1.04, 1.08], [-0.004] * 6, K=26, crease=60)
    p.add("r_torso", gam, "EH_Cloth", "spine", uv_scale=2)
    ys = [0.835, 0.865, 0.90, 0.94, 0.98, 1.02, 1.05]
    gr = [0.008, 0.012, 0.015, 0.016, 0.016, 0.014, 0.008]
    rg = [0.0, 0.003, 0.007, 0.010, 0.010, 0.006, 0.0]
    rings = np.stack([RB.ring(y, a, 22, -96, 96, ridge=r_, ridge_w=0.016) for y, a, r_ in zip(ys, gr, rg)])
    p.add("r_cuirass", g.loft(rings, closed=False, crease=50).dented(3, 0.026, 0.003, seed=44), "EH_Bronze", "spine")
    for a, nm in ((-96, "R"), (96, "L")):
        p.add(f"r_cuirass_edge_{nm}", RB.edge(ys[1:-1], [x + 0.003 for x in gr[1:-1]], a, 0.0040, 4), "EH_Bronze", "spine", lod1=None)
    rb = np.stack([RB.ring(y, a, 18, 120, 240) for y, a in zip([0.84, 0.90, 0.96, 1.02, 1.05], [0.008, 0.012, 0.013, 0.012, 0.008])])
    p.add("r_backplate", g.loft(rb, closed=False, crease=50), "EH_Bronze", "spine")
    bl = RB.loft([0.800, 0.804, 0.832, 0.836], [0.004, 0.012, 0.012, 0.004], K=26, crease=50)
    p.add("r_belt", bl, "EH_Leather", "body", uv_scale=2)
    lame = [RB.loft([y - 0.010, y - 0.007, y + 0.007, y + 0.010], [0.016 - 0.004, 0.020, 0.020, 0.016 - 0.003], K=20, a0=-95, a1=95, crease=45) for y in (0.80,)]
    p.add("r_waist_lames", merge(lame), "EH_Bronze", "spine", lod1=None)
    # fur mantle (asymmetric: heavy on the left)
    K = 28
    th = np.linspace(0, TAU, K, endpoint=False)
    path = np.stack([0.122 * np.sin(th), 1.046 - 0.020 * np.abs(np.sin(th)) ** 1.5, 0.092 * np.cos(th) - 0.036], 1)
    ring_ = g.tube(path, 0.030, sides=7, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.008, 18, 3, seed=45)
    flap = g.superellipsoid((0.065, 0.034, 0.072), 0.7, 0.8, 4, 10).noised(0.008, 14, 3, seed=46).translated(0.155, 1.030, -0.030)
    p.add("r_mantle", merge([ring_, flap]), "EH_Fur", "spine", uv_scale=2)
    tuft = g.tube([(0, 0, 0), (0.003, 0.012, 0.003), (0.008, 0.022, 0.009)], [0.016, 0.010, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    rng = np.random.default_rng(48)
    pos = [(0.138 * math.sin(a), 1.040 - 0.020 * abs(math.sin(a)) ** 1.5, 0.104 * math.cos(a) - 0.036) for a in np.arange(18) * TAU / 18]
    nrm = [(math.sin(a), -0.7, math.cos(a)) for a in np.arange(18) * TAU / 18]
    p.add("r_mantle_tufts", g.instances(tuft, pos, nrm, 1.0, spins=rng.random(18) * 360), "EH_Fur", "spine", uv_scale=2)
    # pauldrons (large left / small right) as layered domes
    L = C.pauldron(+1, (0.172, 1.050, -0.030), 0.92, lames=3, seed=1, tilt_deg=16, flare=0.009)
    R = C.pauldron(-1, (-0.160, 1.046, -0.030), 0.74, lames=2, dent=True, seed=2, tilt_deg=16, flare=0.009)
    p.add("r_pauldron_L", L, "EH_Bronze", "arm_L")
    p.add("r_pauldron_R", R, "EH_Bronze", "arm_R")
    # arms
    for s, nm in ((1, "L"), (-1, "R")):
        sh = (s * 0.105, 1.04, -0.03)
        el = (s * 0.115 if s > 0 else -0.12, 0.95, 0.03 if s > 0 else 0.04)
        up = g.tube([sh, (s * 0.112, 0.995, -0.010), el], [0.034, 0.031, 0.028], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"r_upper_arm_{nm}", up, "EH_Cloth", f"arm_{nm}", uv_scale=2)
        wr = (s * 0.118 if s > 0 else -0.140, 0.895, 0.100 if s > 0 else 0.105)
        fore = g.tube([el, (s * 0.120 if s > 0 else -0.134, 0.925, 0.068), wr], [0.028, 0.025, 0.022], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 1, 0))
        p.add(f"r_forearm_{nm}", fore, "EH_Cloth", f"hand_{nm}", uv_scale=2)
        vam = g.tube([el, (s * 0.120 if s > 0 else -0.134, 0.925, 0.068), wr], [0.031, 0.028, 0.025], sides=8, samples=2, cap="flat", up=(0, 1, 0))
        p.add(f"r_vambrace_{nm}", vam.noised(0.0012, 36, 2, seed=50 + s), "EH_Bronze", f"hand_{nm}")
        hand = g.superellipsoid((0.022, 0.020, 0.026), 0.55, 0.6, 4, 9).translated(wr[0], wr[1] - 0.016, wr[2] + 0.014)
        fing = g.instances(g.dome(0.0052, 0.0045, 6, 1), [(wr[0] + dx, wr[1] - 0.024, wr[2] + 0.036) for dx in (-0.011, -0.004, 0.004, 0.011)], [(0, -0.2, 1)] * 4)
        p.add(f"r_hand_{nm}", merge([hand, fing]), "EH_Leather", f"hand_{nm}", uv_scale=2)
        cuff = g.torus(0.026, 0.0055, 12, 4).aimed(C.unit(np.array(wr) - np.array([s * 0.120 if s > 0 else -0.134, 0.925, 0.068])), np.array(wr))
        p.add(f"r_cuff_{nm}", cuff, "EH_Bronze", f"hand_{nm}", lod1=None)
    # head, helm
    cy, cz = 1.105, -0.020
    skull = g.superellipsoid((0.041, 0.048, 0.046), 0.92, 0.95, 5, 11).translated(0, cy, cz)
    nose = g.superellipsoid((0.006, 0.012, 0.010), 0.6, 0.6, 3, 6).translated(0, cy - 0.004, cz + 0.045)
    p.add("r_face", merge([skull, nose]), "EH_Skin", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.7))
    helm = g.lathe(g.spline(np.array([(0.052, 1.070), (0.056, 1.105), (0.050, 1.140), (0.030, 1.166), (0.0, 1.184)]), 3), 18, crease=55).translated(0, 0, cz).noised(0.0012, 40, 2, seed=52)
    p.add("r_helm", helm, "EH_Bronze", "head")
    visor = g.extrude(np.array([(-0.030, -0.006), (0.030, -0.006), (0.034, 0.006), (-0.034, 0.006)]), 0.012, 0.003, 1).translated(0, 1.108, cz + 0.052)
    nasal = g.extrude(np.array([(-0.0065, 1.070), (0.0065, 1.070), (0.0055, 1.150), (-0.0055, 1.150)]), 0.006, 0.0015, 1).translated(0, 0, cz + 0.052)
    p.add("r_visor", merge([visor, nasal]), "EH_Steel", "head")
    band = g.torus(0.052, 0.0050, 18, 4).translated(0, 1.128, cz)
    p.add("r_helm_band", band, "EH_Bronze", "head", lod1=None)
    crest = g.extrude_plane(np.array([(1.150, -0.050), (1.205, -0.034), (1.224, -0.004), (1.200, 0.030), (1.150, 0.042)]), 0.014, "YZ", bevel=0.004, bevel_segments=1).translated(0, 0, cz)
    p.add("r_helm_crest", crest, "EH_Bronze", "head", lod1="keep")
    cheek = [g.extrude_plane(np.array([(1.072, -0.025), (1.070, 0.028), (1.100, 0.036), (1.120, 0.020), (1.116, -0.022)]), 0.007, "YZ", bevel=0.0015, bevel_segments=1).translated(s * 0.050, 0, cz) for s in (-1, 1)]
    p.add("r_cheek_guards", merge(cheek), "EH_Steel", "head", lod1=None)


def lance(p: Piece):
    base = np.array([-0.16, 0.78, -0.16])
    mid = np.array([-0.16, 0.95, 0.04])
    tip = np.array([-0.16, 1.24, 0.38])
    shaft = g.tube([base, mid, tip], [0.015, 0.0135, 0.0105], sides=8, samples=3, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("r_lance_shaft", shaft.noised(0.0012, 30, 2, seed=60), "EH_Leather", "hand_R", uv_scale=2)
    d = C.unit(tip - mid)
    rings = [g.torus(0.0165 - 0.002 * i, 0.0050, 10, 4).aimed(d, mid + (tip - mid) * u) for i, u in enumerate((0.28, 0.55, 0.82))]
    rings.append(g.torus(0.0170, 0.0055, 10, 4).aimed(C.unit(mid - base), base + (mid - base) * 0.18))
    p.add("r_lance_rings", merge(rings), "EH_Bronze", "hand_R")
    head = g.blade(0.105, 0.040, 0.011, tip=0.45, taper=0.9, fuller=0.0015, rows=3).aimed(d, tip - d * 0.005)
    collar = g.lathe(np.array([(0.0125, 0.0), (0.021, 0.006), (0.021, 0.022), (0.014, 0.030), (0.0105, 0.032)]), 10, crease=45).aimed(d, tip - d * 0.020)
    p.add("r_lance_head", head, "EH_Steel", "hand_R", occluder=False)
    p.add("r_lance_collar", collar, "EH_Bronze", "hand_R")
    # pennon: swallow-tail cloth streaming back (soft: rides the shaft, flutters at the free end)
    pen = np.array([(0, 0.014), (-0.150, 0.046), (-0.115, 0.0), (-0.150, -0.046), (0, -0.014)])
    cloth = g.extrude(pen, 0.004, 0.0008, 1)
    cloth = g.warp(cloth, lambda P: np.column_stack([P[:, 0], P[:, 1], P[:, 2] + 0.010 * np.sin(P[:, 0] * 38) * np.abs(P[:, 0]) * 6]), 70)
    pos = mid + (tip - mid) * 0.80
    cloth = cloth.rotated(0, 90, 0).translated(*(pos + [0.0, 0.0, 0.0]))
    cloth = g.warp(cloth, lambda P: P - np.column_stack([np.zeros(len(P)), 0.04 * np.clip(-(P[:, 2] - pos[2]), 0, None) ** 1.3, np.zeros(len(P))]), 60)
    p.add("r_pennon", cloth, "EH_Cloth", "hand_R", uv_scale=2, lod1=None)
    # reins: from the left hand to the elk's bit
    reins = g.tube([(0.115, 0.915, 0.075), (0.070, 0.935, 0.200), (0.030, 0.915, 0.350), (0.0, 0.870, 0.470)], 0.0042, sides=4, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
    p.add("r_reins", reins, "EH_Leather", "hand_L", uv_scale=2, lod1=None)


def extras(p: Piece):
    rng = np.random.default_rng(77)
    tuft = g.tube([(0, 0, 0), (0.002, -0.020, 0.004), (0.004, -0.040, 0.012)], [0.016, 0.011, 0.0], sides=5, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    # throat ruff / chest fur: hanging tufts under the neck and on the chest
    pos, nrm = [], []
    for i in range(10):
        u = i / 9
        pos.append((rng.normal(0, 0.05) * (0.4 + u), 0.700 - 0.02 * u + rng.normal(0, 0.012), 0.205 + 0.03 * (1 - u) + rng.normal(0, 0.01)))
        nrm.append((rng.normal(0, 0.2), -1, 0.4))
    p.add("m_chest_tufts", g.instances(tuft, pos, nrm, 1.3, spins=rng.random(10) * 360), "EH_Fur", "mount_head", bone2="mount_body", blend=(0.78, 0.70), uv_scale=2, tint=COAT)
    # fetlock feathering on all four legs
    ft = []
    for z, hz in ((0.200, 0.205), (-0.205, -0.200)):
        for s_ in (-1, 1):
            for k in range(5):
                a = k * TAU / 5
                ft.append(((s_ * 0.115 + 0.020 * math.sin(a), 0.278, z + 0.020 * math.cos(a)), (math.sin(a) * 0.7, -1, math.cos(a) * 0.7)))
    p.add("m_fetlock_tufts", g.instances(tuft, [q[0] for q in ft], [q[1] for q in ft], 0.6, spins=rng.random(len(ft)) * 360), "EH_Fur", "mount_body", uv_scale=2, tint=COAT, lod1=None)
    # croupiere: overlapping bronze plates over the rump, with a rolled edge
    cr = []
    for i, (y, w, z) in enumerate(((0.700, 0.250, -0.300), (0.660, 0.270, -0.322), (0.620, 0.280, -0.340))):
        pl = g.plate(w, 0.070, 0.012, 0.005, bend_r=0.16, inner_x=1, taper=lambda t: 1 - 0.1 * t, drop_back=True)
        cr.append(pl.rotated(0, 180, 0).rotated(-8 + 4 * i, 0, 0).translated(0, y, z - 0.0))
    p.add("m_croupiere", merge(cr), "EH_Bronze", "mount_body")
    # crinet studs
    stud_pos, stud_n = [], []
    q = np.array(g.spline(np.array([(0, 0.725, 0.165), (0, 0.800, 0.220), (0, 0.870, 0.282), (0, 0.925, 0.340)]), 12))
    for u in np.linspace(0.08, 0.9, 7):
        i = int(u * (len(q) - 1))
        for sx in (-1, 1):
            r = 0.104 - 0.03 * u
            stud_pos.append(q[i] + [sx * r * 0.82, r * 0.52, 0])
            stud_n.append((sx, 0.6, 0))
    p.add("m_crinet_studs", g.instances(g.dome(0.0080, 0.0055, 6, 1), stud_pos, stud_n), "EH_Steel", "mount_head", lod1=None)
    # blanket tassels along the lower hem
    tas = g.tube([(0, 0, 0), (0, -0.020, 0), (0, -0.040, 0)], [0.0085, 0.0075, 0.0], sides=5, samples=1, cap=None, smooth=False)
    tp, tn = [], []
    for s_ in (-1, 1):
        for z in np.linspace(0.05, -0.23, 8):
            tp.append(barrel_pt(z, 98 * s_, 0.017))
            tn.append((0, -1, 0))
    p.add("m_blanket_tassels", g.instances(tas, tp, tn, 1.0), "EH_Bronze", "mount_body", lod1=None)
    # shoulder (spaulder) plates, blanket badges, muscle swellings, cheek tufts
    for s_, n in ((1, "L"), (-1, "R")):
        pls = []
        for k in range(2):
            pl = g.plate(0.105 - 0.015 * k, 0.095, 0.012, 0.006, bend_r=0.12, inner_x=1, drop_back=True)
            pls.append(pl.rotated(0, 90 * s_, 0).rotated(0, 0, -s_ * (12 + 8 * k)).translated(s_ * (0.146 - 0.004 * k), 0.655 - 0.060 * k, 0.150 + 0.012 * k))
        p.add(f"m_spaulder_{n}", merge(pls), "EH_Bronze", "mount_body")
        badge = g.lathe(np.array([(0, 0), (0.038, 0), (0.040, 0.004), (0.036, 0.008), (0, 0.009)]), 18, crease=40).rotated(0, 0, -90 * s_).translated(s_ * (b_r(-0.10) * ELL[1] + 0.030), b_y(-0.10) + 0.055, -0.115)
        anv = g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 0.62, 0.005, 0.0, 1).rotated(0, 90 * s_, 0).translated(s_ * (b_r(-0.10) * ELL[1] + 0.042), b_y(-0.10) + 0.052, -0.115)
        p.add(f"m_blanket_badge_{n}", merge([badge, anv]), "EH_Bronze", "mount_body", lod1=None)
        fore_b = g.superellipsoid((0.034, 0.060, 0.036), 0.8, 0.8, 4, 9).translated(s_ * 0.118, 0.455, 0.172)
        gask = g.superellipsoid((0.040, 0.070, 0.042), 0.8, 0.8, 4, 9).translated(s_ * 0.120, 0.470, -0.150)
        p.add(f"m_muscles_{n}", merge([fore_b, gask]).noised(0.003, 18, 2, seed=90 + s_), "EH_Fur", "mount_body", uv_scale=2, tint=COAT, lod1=None)
        ct = []
        for k in range(5):
            ct.append(((s_ * (0.038 + 0.004 * k), 0.880 - 0.012 * k, 0.430 - 0.020 * k), (s_ * 0.5, -1, -0.3)))
        p.add(f"m_cheek_tufts_{n}", g.instances(tuft, [c[0] for c in ct], [c[1] for c in ct], 0.8, spins=rng.random(5) * 360), "EH_Fur", "mount_head", uv_scale=2, tint=COAT, lod1=None)
    # rider: short sword on the left hip (scabbard + hilt)
    sc = g.tube([(0.150, 0.815, -0.090), (0.205, 0.760, -0.150), (0.250, 0.700, -0.215)], [0.016, 0.017, 0.012], sides=7, samples=2, cap="round", cap_steps=1, ellipse=(1, 0.7), up=(0, 1, 0))
    hilt = g.tube([(0.150, 0.815, -0.090), (0.128, 0.848, -0.062)], 0.0105, sides=6, samples=1, cap="flat", smooth=False)
    guard = g.extrude(g.rect_poly(0.050, 0.010, 0.003, 1), 0.012, 0.003, 1).rotated(0, 0, 0).translated(0.152, 0.812, -0.092)
    p.add("r_sword_scabbard", sc, "EH_Leather", "body", uv_scale=2)
    p.add("r_sword_hilt", merge([hilt, guard, g.superellipsoid((0.013, 0.011, 0.013), 0.7, 0.7, 3, 7).translated(0.126, 0.852, -0.058)]), "EH_Bronze", "body", lod1=None)


# ======================================================================================= clips
def make_clips(rig) -> list[Clip]:
    idle = Clip("Idle", 3.2, loop=True)
    idle.keys("mount_head", "rot", [(0, (0, 0, 0)), (1.0, (3, 4, 0), "in_out_cubic"), (2.2, (-2, -3, 0), "in_out_cubic"), (3.2, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.0, (-4, 0, 0), "in_out_cubic"), (2.2, (2, 0, 0), "in_out_cubic"), (3.2, (0, 0, 0), "in_out_cubic")])
    idle.keys("mount_body", "pos", [(0, (0, 0, 0)), (1.6, (0, 0.004, 0), "in_out_cubic"), (3.2, (0, 0, 0), "in_out_cubic")])
    idle.keys("mount_body", "rot", [(0, (0, 0, 0)), (1.6, (-0.8, 0, 0), "in_out_cubic"), (3.2, (0, 0, 0), "in_out_cubic")])
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.6, (1, 0, 0), "in_out_cubic"), (3.2, (0, 0, 0), "in_out_cubic")])
    idle.keys("hand_R", "rot", [(0, (0, 0, 0)), (2.2, (0, 0, 1), "in_out_cubic"), (3.2, (0, 0, 0), "in_out_cubic")])

    move = Clip("Move", 0.9, loop=True)
    move.keys("mount_body", "rot", [(0, (3, 0, 0)), (0.15, (3, 0, 0)), (0.45, (5, 0, -2), "in_out_cubic"), (0.6, (4, 0, 2), "in_out_cubic"), (0.9, (3, 0, 0), "in_out_cubic")])
    move.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.15, (0, 0.02, 0), "out_quad"), (0.3, (0, 0, 0), "in_quad"), (0.6, (0, 0.02, 0), "out_quad"), (0.75, (0, 0, 0), "in_quad"), (0.9, (0, 0, 0))])
    move.keys("mount_head", "rot", [(0, (4, 0, 0)), (0.45, (-4, 0, 0), "in_out_cubic"), (0.9, (4, 0, 0), "in_out_cubic")])
    move.keys("spine", "rot", [(0, (0, 0, 0)), (0.45, (-2, 0, 0), "in_out_cubic"), (0.9, (0, 0, 0), "in_out_cubic")])
    move.keys("top", "rot", [(0, (0, 0, 0)), (0.45, (-10, 0, 0), "in_out_cubic"), (0.9, (0, 0, 0), "in_out_cubic")])

    A = Clip("Attack", 2.0, fps=60)
    A.keys("mount_body", "rot", [(0, (0, 0, 0)), (0.40, (-26, 0, 0), "in_out_cubic"), (0.55, (-58, 0, 0), "out_cubic"), (0.70, (-30, 0, 0), "in_out_cubic"), (0.88, (14, 0, 0), "in_out_cubic"),
                                 (1.00, (22, 0, 0), "in_cubic"), (1.15, (22, 0, 0)), (1.5, (-4, 0, 0), "in_out_cubic"), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.40, (0, 0.06, 0), "in_out_cubic"), (0.55, (0, 0.08, 0), "out_cubic"), (0.88, (0, 0.04, 0.10), "in_out_cubic"), (0.97, (0, 0, 0.15), "in_cubic"),
                                 (1.00, (0, -0.04, 0.15), "out_quad"), (1.15, (0, -0.04, 0.15)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("mount_head", "rot", [(0, (0, 0, 0)), (0.40, (-12, 0, 0), "in_out_cubic"), (0.55, (-22, 0, 0), "out_cubic"), (0.88, (8, 0, 0), "in_out_cubic"), (1.15, (10, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.40, (10, 0, 0), "in_out_cubic"), (0.55, (26, 0, 0)), (0.88, (6, 0, 0), "in_out_cubic"), (1.15, (2, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.40, (8, 0, 0), "in_out_cubic"), (0.88, (8, 0, 0), "in_out_cubic"), (1.00, (10, 0, 0), "in_cubic"), (1.15, (10, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.40, (-6, 0, 0), "in_out_cubic"), (0.55, (-8, 0, 0)), (1.0, (4, 0, 0), "in_cubic"), (2.0, (0, 0, 0), "in_out_cubic")])
    # lance elevation = 41 deg - (sum of pitches down the chain): rear it lifts, in the leap it levels, on landing it points down at the target
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.40, (-14, 0, 0), "in_out_cubic"), (0.55, (-5, 0, 0)), (0.88, (-30, 0, 0), "in_out_cubic"), (1.00, (-20, 0, 0), "in_cubic"), (1.15, (-20, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.40, (-7, 0, 0), "in_out_cubic"), (0.55, (7, 0, 0)), (0.88, (36, 0, 0), "in_out_cubic"), (1.00, (46, 0, 0), "in_cubic"), (1.15, (46, 0, 0)), (2.0, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.40, (-22, 0, 0), "in_out_cubic"), (0.55, (-30, 0, 0)), (0.88, (-4, 0, 0), "in_out_cubic"), (1.15, (20, 0, 0), "out_quad"), (2.0, (0, 0, 0), "in_out_cubic")])
    C.solve_hold(A, rig, "body", "arm_L", "hand_L", (0.115, 0.915, 0.075), axes=(0,)) if False else None

    hit = Clip("HitReact", 0.45)
    hit.keys("mount_body", "rot", [(0, (0, 0, 0)), (0.10, (-9, 0, 0), "out_cubic"), (0.45, (-3, 0, 0), "in_out_cubic")])
    hit.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.07), "out_cubic"), (0.45, (0, 0, -0.02), "in_out_cubic")])
    hit.keys("mount_head", "rot", [(0, (0, 0, 0)), (0.10, (-16, 0, 0), "out_cubic"), (0.45, (-6, 0, 0), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-10, 0, 0), "out_cubic"), (0.45, (-4, 0, 0), "in_out_cubic")])
    hit.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.10, (12, 0, 0), "out_cubic"), (0.45, (0, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (16, 0, 0), "out_cubic"), (0.45, (0, 0, 0), "in_out_cubic")])

    vic = Clip("Victory", 1.8)
    vic.keys("mount_body", "rot", [(0, (0, 0, 0)), (0.6, (-22, 0, 0), "out_back"), (1.8, (-14, 0, 0), "in_out_cubic")])
    vic.keys("mount_body", "pos", [(0, (0, 0, 0)), (0.6, (0, 0.05, 0), "out_back"), (1.8, (0, 0.03, 0), "in_out_cubic")])
    vic.keys("mount_head", "rot", [(0, (0, 0, 0)), (0.6, (-14, 0, 0), "out_cubic"), (1.8, (-14, 0, 0))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (0.6, (-25, 0, 0), "out_cubic"), (1.8, (-25, 0, 0))])
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.6, (-150, 0, 0), "out_back"), (1.8, (-150, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.6, (-25, 0, 0), "out_back"), (1.8, (-25, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.6, (-8, 0, 0), "out_cubic"), (1.8, (-8, 0, 0))])
    return [idle, move, A, hit, vic]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("emberhold", "knight", rig, make_clips(rig), impact_time=1.00, strike_range=0.50, attack_style="leap", seed=13)
    C.pedestal_parts(p)
    elk_body(p)
    barding(p)
    elk_neck_head(p)
    antlers(p)
    mane(p)
    rider(p)
    lance(p)
    extras(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
