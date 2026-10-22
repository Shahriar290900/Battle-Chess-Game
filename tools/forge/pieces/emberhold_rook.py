"""emberhold_rook - Emberhold Forge Bastion.

A squat siege-tower of soot-black masonry (pillowed blocks, offset courses, ledged batter) held by bronze hoops and
riveted straps, a corbelled machicolation ring and merlons, a working brazier for a crown with a fan of ember flame
tongues, and a bronze ram-head battering beam on chains across its face.  Built from docs/art/emberhold_rook.md.
Bones: root (plinth), body (whole tower + ram), top (brazier + flames).
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

ASSET_ID = "emberhold_rook"

# ---- masonry: 8 courses of 0.08 (the first is the footing), each stepped in a little from the one below
Y0, COURSE_H, NC = 0.22, 0.08, 8
R_COURSE = [0.316, 0.309, 0.302, 0.295, 0.288, 0.282, 0.2765, 0.272]
Y_TOP = Y0 + COURSE_H * NC          # 0.86
BLOCKS = 16


def tower_r(y):
    """Outer radius of the shaft at height y (centre of the blocks)."""
    k = int(np.clip((y - Y0) // COURSE_H, 0, NC - 1))
    return R_COURSE[k]


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.22, 0))
    r.add("top", "body", (0, 1.00, 0))
    r.socket("socket_weapon_R", "body", (0, 0.56, 0.54))
    r.socket("socket_cast", "top", (0, 1.12, 0))
    r.socket("socket_impact", "body", (0, 0.30, 0.46))
    r.socket("socket_head", "top", (0, 1.14, 0))
    return r


# ======================================================================================= masonry shaft
def shaft() -> g.Mesh:
    rng = np.random.default_rng(11)
    block_off = rng.normal(0, 0.0032, (NC, BLOCKS))
    prof = [(0.0, Y0)]
    for k in range(NC):
        y0 = Y0 + k * COURSE_H
        R = R_COURSE[k]
        prof += [(R * 0.972, y0 + 0.0015), (R * 1.0, y0 + COURSE_H * 0.5), (R * 0.972, y0 + COURSE_H - 0.0015)]
    prof.append((0.0, Y_TOP))
    prof = np.array(prof)
    nrow = len(prof)

    def shape_v(th, v):
        ri = np.round(v * (nrow - 1)).astype(int)
        out = np.ones((nrow, len(th)))
        for i in range(nrow):
            k = int(np.clip((i - 1) // 3, 0, NC - 1))
            if i == 0 or i == nrow - 1:
                continue
            f = (th / TAU * BLOCKS + 0.5 * (k % 2)) % 1.0
            bi = (np.floor(th / TAU * BLOCKS + 0.5 * (k % 2)).astype(int)) % BLOCKS
            groove = 1.0 - np.abs(np.sin(np.pi * f)) ** 0.55
            out[i] = 1.0 - 0.026 * groove + block_off[k, bi] / max(prof[i, 0], 0.1)
        return out
    m = g.lathe(prof, 64, shape_v=shape_v, crease=62)
    m = m.noised(0.0032, 22, 3, seed=5)
    return m


def corbel_ring():
    # out-stepped, rolled machicolation courses between the shaft top and the parapet floor
    prof = [(0.272, 0.860), (0.286, 0.866), (0.296, 0.880), (0.300, 0.888), (0.326, 0.900), (0.330, 0.912), (0.348, 0.926),
            (0.352, 0.946), (0.350, 0.972), (0.338, 0.984), (0.300, 0.986)]
    ring = g.lathe(np.array(prof), 32, crease=48).noised(0.0024, 24, 2, seed=6)
    return ring


def corbel_brackets():
    # stepped bracket profile in the (radial, y) plane, extruded tangentially; 12 big stone corbels
    poly = np.array([(0.298, 0.884), (0.352, 0.934), (0.352, 0.986), (0.304, 0.986), (0.298, 0.940)])
    base = g.extrude(poly - [0.325, 0.0], 0.052, 0.005, 1)
    out = []
    for i in range(12):
        th = i * 30 + 15
        out.append(base.rotated(0, 90, 0).translated(0.0, 0, 0.325).rotated(0, th, 0))
    return merge(out)


def parapet():
    wall = g.lathe(np.array([(0.300, 0.985), (0.334, 0.986), (0.332, 1.034), (0.326, 1.038), (0.300, 1.038)]), 32, crease=45)
    caps, stones = [], []
    for k in range(8):
        a = k * 45.0 + 22.5
        m = g.extrude(g.rect_poly(0.124, 0.066), 0.056, 0.009, 1)               # XY: x tangent, y up
        m = m.translated(0, 1.038 + 0.033, 0.0).translated(0, 0, 0.318)
        stones.append(m.rotated(0, a, 0))
        cap = g.extrude(g.rect_poly(0.134, 0.014), 0.066, 0.004, 1).translated(0, 1.038 + 0.066 + 0.006, 0.318)
        caps.append(cap.rotated(0, a, 0))
    return wall, merge(stones).noised(0.0016, 30, 2, seed=8), merge(caps)


# ======================================================================================= bronze strapwork
def tower_ribbon(theta_deg, y0, y1, w0, w1, lift=0.009, t=0.011, rows=7):
    """A bevelled strap hugging the (batter) tower at angle theta (0 = +Z, toward +X), tapering from w0 to w1."""
    th0 = math.radians(theta_deg)
    rings = []
    for y in np.linspace(y0, y1, rows):
        u = (y - y0) / (y1 - y0)
        w = w0 + (w1 - w0) * u
        R = tower_r(y) * 1.0 + lift - 0.003 * np.sin(u * math.pi * 3)
        ang = w / R
        pts = []
        # cross-section: bevelled rectangle around the surface (8 pts), in the horizontal plane
        sec = [(-0.5, 0.0), (-0.5, 0.55), (-0.44, 1.0), (0.44, 1.0), (0.5, 0.55), (0.5, 0.0)]
        for sx, sr in sec:
            a = th0 + sx * ang
            r = R - 0.004 + sr * t
            pts.append((r * math.sin(a), y, r * math.cos(a)))
        rings.append(pts)
    return g.loft(np.array(rings)[:, ::-1], closed=True, crease=50)


def bands():
    specs = [(0.395, 0.445, 0.008, 0.318, 0.014), (0.640, 0.688, 0.0075, 0.2895, 0.012), (0.818, 0.858, 0.007, 0.279, 0.011)]
    out = []
    for ya, yb, lip, r, h in specs:
        c = 0.5 * (ya + yb)
        rr = r + 0.007
        prof = np.array([(rr - 0.012, ya), (rr, ya + 0.004), (rr + 0.004, ya + 0.012), (rr + 0.005, c), (rr + 0.004, yb - 0.012),
                         (rr, yb - 0.004), (rr - 0.012, yb)])
        out.append(g.lathe(prof, 32, crease=48))
    return out


def band_rivets():
    pos, nrm = [], []
    for (ya, yb, r) in ((0.395, 0.445, 0.318), (0.640, 0.688, 0.2895), (0.818, 0.858, 0.279)):
        c = 0.5 * (ya + yb)
        rr = r + 0.007 + 0.005
        for i in range(10):
            a = i * TAU / 10 + 0.1
            pos.append((rr * math.sin(a), c, rr * math.cos(a)))
            nrm.append((math.sin(a), 0, math.cos(a)))
    return g.instances(g.dome(0.0078, 0.0045, 6, 2), pos, nrm)


def straps_and_rivets():
    straps, rivets_pos, rivets_n = [], [], []
    for k in range(8):
        a = k * 45 + 22.5
        straps.append(tower_ribbon(a, 0.43, 0.835, 0.040, 0.034, lift=0.010))
        for y in np.linspace(0.48, 0.80, 3):
            R = tower_r(y) + 0.0205
            rivets_pos.append((R * math.sin(math.radians(a)), y, R * math.cos(math.radians(a))))
            rivets_n.append((math.sin(math.radians(a)), 0, math.cos(math.radians(a))))
    riv = g.instances(g.dome(0.0090, 0.0050, 6, 2), rivets_pos, rivets_n)
    return merge(straps), riv


def banner():
    wid, hgt = 0.135, 0.255
    R = 0.2905
    curve = math.degrees(wid / R)
    cl = g.cloth_panel(wid, hgt, cols=7, rows=7, fold_amp=0.008, folds=2.4, flare=0.12, curve=curve, seed=3, hem_wave=0.012,
                       thickness=0.006)
    cl = cl.translated(0, 0.975, R + 0.020)
    cl = cl.rotated(0, 40, 0)
    rod = g.tube([(-0.080, 0.982, R + 0.022), (0.080, 0.982, R + 0.022)], 0.0065, sides=6, samples=1, cap="round", cap_steps=1,
                 smooth=False)
    rod = rod.rotated(0, 40, 0)
    fin = [g.superellipsoid((0.011, 0.011, 0.011), 0.7, 0.7, 3, 7).translated(s * 0.088, 0.982, R + 0.022).rotated(0, 40, 0) for s in (-1, 1)]
    return cl, merge([rod] + fin)


def chains():
    out = []
    for s in (-1, 1):
        a = math.radians(33 * s + (0))
        r0 = 0.3340
        start = (r0 * math.sin(a), 0.944, r0 * math.cos(a))
        end = (0.060 * s, 0.645, 0.370)
        mid = ((start[0] + end[0]) / 2 + 0.016 * s, 0.80, (start[2] + end[2]) / 2 + 0.01)
        out.append(g.tube([start, mid, end], 0.0068, sides=5, samples=3, cap="round", cap_steps=1,
                          radius_fn=lambda t: 0.62 + 0.38 * abs(math.sin(t * 38))))
    return merge(out)


def swag_chains():
    out = []
    for a0, a1 in ((-100, -145), (115, 160)):
        pts = []
        for i in range(9):
            t = i / 8
            a = math.radians(a0 + (a1 - a0) * t)
            sag = 0.050 * math.sin(math.pi * t)
            pts.append((0.3375 * math.sin(a), 0.935 - sag, 0.3375 * math.cos(a)))
        out.append(g.tube(pts, 0.0085, sides=5, samples=1, cap="round", cap_steps=1, smooth=True,
                          radius_fn=lambda t: 0.7 + 0.3 * abs(math.sin(t * 30))))
    return merge(out)


# ======================================================================================= door, slits, rubble
def door(p: Piece):
    zw = 0.3195          # wall radius at the door height (base course) + a little
    arch = np.array([(-0.062, 0.222), (0.062, 0.222), (0.062, 0.335), (0.052, 0.375), (0.030, 0.404), (0.0, 0.414),
                     (-0.030, 0.404), (-0.052, 0.375), (-0.062, 0.335)])
    leaf = g.extrude(arch, 0.012, 0.004, 1).translated(0, 0, zw + 0.006)
    p.add("door_leaf", leaf, "EH_Steel", "body", uv_scale=2)
    # arch moulding (voussoir ring) as a bevelled tube following the arch, plus jambs
    path = [(-0.078, 0.222, 0), (-0.078, 0.340, 0), (-0.064, 0.392, 0), (-0.034, 0.426, 0), (0.0, 0.438, 0), (0.034, 0.426, 0),
            (0.064, 0.392, 0), (0.078, 0.340, 0), (0.078, 0.222, 0)]
    frame = g.tube([(x, y, zw + 0.012) for x, y, _ in path], 0.0185, sides=6, samples=2, cap="flat", ellipse=(0.7, 1.0), up=(0, 0, 1))
    p.add("door_frame", frame.noised(0.0018, 30, 2, seed=2), "EH_Stone", "body")
    keystone = g.extrude(np.array([(-0.020, 0.414), (0.020, 0.414), (0.016, 0.452), (-0.016, 0.452)]), 0.030, 0.005, 1).translated(0, 0, zw + 0.012)
    p.add("door_keystone", keystone, "EH_Stone", "body", uv_scale=2)
    hinge = []
    for y in (0.262, 0.322, 0.378):
        hinge.append(g.extrude(np.array([(-0.062, y - 0.010), (0.040, y - 0.006), (0.046, y), (0.040, y + 0.006), (-0.062, y + 0.010)]),
                               0.006, 0.0015, 1).translated(0, 0, zw + 0.0145))
    p.add("door_hinges", merge(hinge), "EH_Bronze", "body")
    studs = g.instances(g.dome(0.0070, 0.006, 6, 1), [(x, y, zw + 0.0125) for x in (-0.040, -0.014, 0.014, 0.040) for y in (0.246, 0.296, 0.346)],
                        [(0, 0, 1)] * 12)
    p.add("door_studs", studs, "EH_Bronze", "body", lod1=None)
    ring = g.torus(0.016, 0.0034, 12, 4).rotated(90, 0, 0).translated(0.032, 0.318, zw + 0.0175)
    p.add("door_ring", ring, "EH_Steel", "body")


def slits(p: Piece):
    frames, dark, glow = [], [], []
    for a, y in ((42, 0.640), (-64, 0.586), (150, 0.632)):
        R = tower_r(y) + 0.003
        ar = math.radians(a)
        pos = (R * math.sin(ar), y, R * math.cos(ar))

        def place(m, dz=0.0):
            return m.translated(0, 0, dz).rotated(0, a, 0).translated(0, 0, 0) if False else m.translated(0, y, R + dz).rotated(0, a, 0)
        fr = g.extrude(np.array([(-0.022, -0.062), (0.022, -0.062), (0.026, -0.04), (0.026, 0.04), (0.022, 0.062), (0.0, 0.074),
                                 (-0.022, 0.062), (-0.026, 0.04), (-0.026, -0.04)]), 0.014, 0.004, 1)
        frames.append(place(fr, 0.004))
        dk = g.extrude(g.rect_poly(0.0155, 0.108, 0.003, 1), 0.006, 0.0015, 1)
        dark.append(place(dk, 0.0105))
        gl = g.extrude(g.rect_poly(0.0085, 0.100, 0.002, 1), 0.004, 0.001, 1)
        glow.append(place(gl, 0.0135))
    return merge(frames), merge(dark), merge(glow)


def rubble(p: Piece):
    blocks = []
    for (x, z, ry, s) in ((0.262, 0.215, 28, (0.075, 0.052, 0.062)), (-0.285, 0.130, -15, (0.062, 0.042, 0.056)),
                          (0.118, -0.300, 40, (0.058, 0.040, 0.052)), (-0.185, -0.268, 8, (0.070, 0.046, 0.058)),
                          (0.300, -0.088, 55, (0.040, 0.030, 0.040))):
        b = g.superellipsoid((s[0] / 2, s[1] / 2, s[2] / 2), 0.42, 0.42, 4, 8).noised(0.004, 22, 2, seed=int(abs(x) * 100))
        blocks.append(b.rotated(5, ry, -4).translated(x, 0.222 + s[1] * 0.38, z))
    p.add("rubble", merge(blocks), "EH_Stone", "body", uv_scale=2, tint=lambda P: np.full(len(P), 0.82))


# ======================================================================================= ram
def ram(p: Piece):
    zc = 0.0
    # cradle plate on the wall (curved to the tower)
    R = tower_r(0.56) + 0.004
    cr = g.extrude(np.array([(-0.12, 0.46), (0.12, 0.46), (0.145, 0.58), (0.12, 0.68), (-0.12, 0.68), (-0.145, 0.58)]), 0.020, 0.008, 1)
    cr = g.warp(cr.translated(0, 0, R + 0.009), lambda P: np.column_stack([P[:, 0], P[:, 1], P[:, 2] - (P[:, 0] ** 2) / (2 * R)]), 45)
    p.add("ram_cradle", cr, "EH_Bronze", "body")
    rv = g.instances(g.dome(0.0075, 0.007, 6, 1), [(x * 0.108, y, R + 0.019 - (x * 0.108) ** 2 / (2 * R)) for x, y in
                                                     ((-1, 0.486), (1, 0.486), (-1.15, 0.58), (1.15, 0.58), (-1, 0.654), (1, 0.654))], [(0, 0, 1)] * 6)
    p.add("ram_cradle_rivets", rv, "EH_Bronze", "body", lod1=None)
    # saddle brackets cradling the beam
    # beam: tapering log with iron hoops, tilted a hair downward
    tilt = math.radians(-4)

    def along(z):
        return (0.0, 0.565 + math.tan(tilt) * (z - 0.27), z)
    beam = g.tube([along(0.275), along(0.340), along(0.405)], [0.068, 0.073, 0.080], sides=12, samples=2, cap=None, up=(1, 0, 0))
    beam = beam.noised(0.0035, 26, 3, seed=14)
    p.add("ram_beam", beam, "EH_Bronze", "body")
    hoops = [g.torus(0.0785 + 0.0035 * i + 0.0075, 0.0085, 14, 4).rotated(90, 0, 0).translated(*along(z)) for i, z in enumerate((0.300, 0.345, 0.385))]
    p.add("ram_hoops", merge(hoops), "EH_Steel", "body")
    # --- head: skull, muzzle, brow, ears, curled horns
    cx, cy, cz = along(0.435)
    skull = g.superellipsoid((0.086, 0.074, 0.092), 0.62, 0.62, 6, 14).translated(cx, cy + 0.004, cz)
    muzzle = g.superellipsoid((0.050, 0.046, 0.078), 0.55, 0.6, 5, 12).translated(cx, cy - 0.022, cz + 0.078)
    brow = g.tube([(cx - 0.080, cy + 0.036, cz + 0.020), (cx - 0.040, cy + 0.056, cz + 0.046), (cx + 0.040, cy + 0.056, cz + 0.046),
                   (cx + 0.080, cy + 0.036, cz + 0.020)], [0.012, 0.016, 0.016, 0.012], sides=6, samples=2, cap="round", cap_steps=1)
    nose = g.tube([(cx, cy + 0.040, cz + 0.060), (cx, cy + 0.020, cz + 0.115), (cx, cy - 0.006, cz + 0.150)], [0.014, 0.017, 0.020],
                  sides=6, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    chin = g.superellipsoid((0.034, 0.020, 0.040), 0.6, 0.6, 3, 8).translated(cx, cy - 0.060, cz + 0.100)
    ears = [g.superellipsoid((0.036, 0.010, 0.020), 0.6, 0.6, 3, 7).rotated(0, 0, -s * 14).translated(cx + s * 0.092, cy - 0.006, cz - 0.020) for s in (-1, 1)]
    p.add("ram_head", merge([skull, muzzle, brow, nose, chin] + ears).noised(0.0022, 34, 2, seed=15), "EH_Bronze", "body")
    nostril = g.instances(g.dome(0.010, 0.006, 6, 1).rotated(90, 0, 0), [(s * 0.020, cy - 0.012, cz + 0.152) for s in (-1, 1)], [(0, 0, 1)] * 2)
    p.add("ram_nostrils", nostril, "EH_Steel", "body", lod1=None)
    collar = g.torus(0.082, 0.012, 16, 5).rotated(90, 0, 0).translated(cx, cy, cz - 0.075)
    p.add("ram_collar", collar, "EH_Steel", "body")
    horns = []
    for s in (-1, 1):
        path = [(s * 0.050, cy + 0.052, cz - 0.006), (s * 0.098, cy + 0.066, cz - 0.060), (s * 0.150, cy + 0.030, cz - 0.100),
                (s * 0.168, cy - 0.040, cz - 0.070), (s * 0.156, cy - 0.078, cz + 0.002), (s * 0.130, cy - 0.060, cz + 0.058),
                (s * 0.108, cy - 0.020, cz + 0.078)]
        rad = [0.038, 0.037, 0.034, 0.028, 0.021, 0.013, 0.004]
        horn = g.tube(path, rad, sides=7, samples=3, cap="round", cap_steps=1, up=(0, 1, 0),
                      radius_fn=lambda t: 1.0 + 0.07 * math.cos(t * TAU * 5) * (1 - t))
        horns.append(horn.noised(0.0018, 36, 2, seed=16))
    p.add("ram_horns", merge(horns), "EH_Bronze", "body")
    # forged forehead boss: a flat-faced striking plate between the horns
    plate = g.extrude(np.array([(-0.040, -0.030), (0.040, -0.030), (0.050, 0.0), (0.038, 0.040), (-0.038, 0.040), (-0.050, 0.0)]), 0.016, 0.005, 1)
    plate = plate.rotated(-58, 0, 0).translated(cx, cy + 0.050, cz + 0.052)
    p.add("ram_forehead_plate", plate, "EH_Steel", "body")
    eyes = g.instances(g.superellipsoid((0.0075, 0.0045, 0.0045), 0.7, 0.7, 3, 6).rotated(0, 0, 0), [(s * 0.062, cy + 0.016, cz + 0.060) for s in (-1, 1)],
                       [(s * 0.3, 0.2, 1) for s in (-1, 1)])
    p.add("ram_eyes", eyes, "EH_EmberVein", "body", lod1="keep", bake=False)


# ======================================================================================= brazier crown (bone: top)
def brazier(p: Piece):
    prof = np.array([(0.0, 1.000), (0.075, 1.000), (0.150, 1.020), (0.205, 1.062), (0.230, 1.100), (0.224, 1.108), (0.212, 1.104),
                     (0.196, 1.078), (0.140, 1.040), (0.070, 1.024), (0.0, 1.022)])
    bowl = g.lathe(prof, 24, crease=50).noised(0.0025, 24, 2, seed=21)
    p.add("brazier_bowl", bowl, "EH_Bronze", "top")
    rim = g.torus(0.2185, 0.0072, 28, 5).translated(0, 1.1065, 0)
    hoop = g.torus(0.178, 0.0065, 24, 4).translated(0, 1.050, 0)
    lugs = []
    for i in range(6):
        a = i * 60 + 30
        l = g.extrude(g.rect_poly(0.040, 0.034), 0.046, 0.008, 1).rotated(90, 0, 0).translated(0, 1.072, 0.236)
        lugs.append(l.rotated(0, a, 0))
    p.add("brazier_rim_lugs", merge([rim, hoop] + lugs), "EH_Bronze", "top")
    # iron legs/feet: the bowl is a stand-alone bronze brazier on the parapet floor
    feet = []
    for i in range(4):
        a = i * 90 + 45
        f = g.tube([(0.060, 1.014, 0), (0.110, 1.006, 0), (0.150, 0.992, 0)], [0.018, 0.016, 0.014], sides=5, samples=1, cap="round",
                   cap_steps=1, smooth=True)
        feet.append(f.rotated(0, a, 0))
    p.add("brazier_feet", merge(feet), "EH_Steel", "top", lod1=None)
    # coal bed + burning flame fan
    coals = g.superellipsoid((0.190, 0.020, 0.190), 0.5, 0.7, 4, 14).translated(0, 1.050, 0).noised(0.009, 14, 2, seed=22)
    p.add("coals", coals, "EH_Coal", "top", lod1="keep", bake=False)
    tongues = []
    lean = math.radians(3)
    cfg = [  # (ring radius, angle, tip height, base width)  - a fan of separate tongues, tall in the middle
        (0.0, 0.0, 1.196, 0.060)]
    for i in range(7):
        cfg.append((0.118, 0.25 + i * TAU / 7, [1.168, 1.182, 1.160, 1.176, 1.152, 1.178, 1.164][i], 0.050))
    for i in range(7):
        cfg.append((0.178, 0.25 + (i + 0.5) * TAU / 7, [1.112, 1.124, 1.108, 1.120, 1.104, 1.126, 1.114][i], 0.032))
    y0 = 1.050
    for k, (rr, ang, top_y, wid) in enumerate(cfg):
        bx, bz = rr * math.sin(ang), rr * math.cos(ang)
        h = top_y - y0
        side = (-1) ** k * (0.016 if rr < 0.15 else 0.010)
        tx, tz = math.cos(ang) * side, -math.sin(ang) * side
        ox, oz = math.sin(ang), math.cos(ang)
        grow = 0.012 if rr else 0.0
        pts = [(bx, y0, bz), (bx + ox * grow + tx, y0 + h * 0.36, bz + oz * grow + tz), (bx + ox * grow * 0.6 - tx * 0.9, y0 + h * 0.70, bz + oz * grow * 0.6 - tz * 0.9),
               (bx * 0.86 + tx * 0.7, top_y, bz * 0.86 + tz * 0.7)]
        pts = [(x, y, z + (y - y0) * math.tan(lean)) for x, y, z in pts]
        radial = (ox, 0, oz) if rr else (0, 0, 1)
        t = g.tube(pts, [wid, wid * 0.90, wid * 0.55, 0.004], sides=6, samples=2, cap="round", cap_steps=1, ellipse=(0.55, 1.45), up=radial)
        tongues.append(t)
    p.add("flames", merge(tongues), "EH_Flame", "top", lod1="keep", bake=False)
    # a few drifting sparks above the flame tips (tiny, part of the silhouette)
    sp = g.instances(g.superellipsoid((0.007, 0.010, 0.007), 0.7, 0.7, 3, 6), [(0.05, 1.196, 0.03), (-0.07, 1.186, -0.02), (0.01, 1.19, -0.08)],
                     [(0, 1, 0)] * 3)
    p.add("sparks", sp, "EH_Flame", "top", lod1=None, bake=False)


# ======================================================================================= clips
def make_clips() -> list[Clip]:
    idle = Clip("Idle", 2.4, loop=True)
    idle.keys("top", "scale", [(0, (1, 1, 1)), (0.6, (1.04, 1.12, 1.04), "in_out_cubic"), (1.2, (1, 0.96, 1), "in_out_cubic"),
                               (1.8, (1.03, 1.08, 1.03), "in_out_cubic"), (2.4, (1, 1, 1), "in_out_cubic")])
    idle.keys("top", "rot", [(0, (0, 0, 0)), (0.6, (0, 0, 2), "in_out_cubic"), (1.2, (1, 0, -1.5), "in_out_cubic"), (1.8, (0, 0, 1), "in_out_cubic"),
                             (2.4, (0, 0, 0), "in_out_cubic")])
    idle.keys("body", "scale", [(0, (1, 1, 1)), (1.2, (1, 1.003, 1), "in_out_cubic"), (2.4, (1, 1, 1), "in_out_cubic")])

    move = Clip("Move", 0.7, loop=True)
    move.keys("body", "scale", [(0, (1, 1, 1)), (0.1, (1.03, 0.94, 1.03), "out_quad"), (0.3, (0.98, 1.06, 0.98), "out_quad"),
                                (0.5, (1.02, 0.96, 1.02), "in_quad"), (0.7, (1, 1, 1), "out_quad")])
    move.keys("body", "pos", [(0, (0, 0, 0)), (0.1, (0, -0.015, 0), "out_quad"), (0.3, (0, 0.04, 0), "out_quad"), (0.5, (0, 0, 0), "in_quad"),
                              (0.7, (0, 0, 0))])
    move.keys("body", "rot", [(0, (0, 0, 0)), (0.1, (0, 0, 0)), (0.3, (5, 0, 0), "in_out_cubic"), (0.5, (-1, 0, 0), "in_cubic"), (0.7, (0, 0, 0), "out_quad")])
    move.keys("top", "scale", [(0, (1, 1, 1)), (0.1, (1, 1.2, 1), "out_quad"), (0.3, (1, 0.9, 1), "in_out_cubic"), (0.5, (1, 1.3, 1), "out_quad"), (0.7, (1, 1, 1), "in_out_cubic")])

    A = Clip("Attack", 1.7, fps=60)
    A.keys("body", "scale", [(0, (1, 1, 1)), (0.40, (1.05, 0.92, 1.05), "in_out_cubic"), (0.62, (0.97, 1.10, 0.97), "in_out_cubic"),
                             (0.75, (1.06, 0.90, 1.06), "in_cubic"), (0.90, (1.08, 0.88, 1.08), "out_quad"), (1.2, (0.98, 1.03, 0.98), "in_out_cubic"), (1.7, (1, 1, 1), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.40, (0, -0.03, 0), "in_out_cubic"), (0.62, (0, 0, -0.10), "in_out_cubic"), (0.75, (0, 0, 0.22), "in_cubic"),
                           (0.90, (0, -0.04, 0.22), "out_quad"), (1.7, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.40, (0, 0, 0), "in_out_cubic"), (0.62, (-8, 0, 0), "in_out_cubic"), (0.75, (20, 0, 0), "in_cubic"),
                           (0.90, (20, 0, 0)), (1.7, (0, 0, 0), "in_out_cubic")])
    A.keys("top", "scale", [(0, (1, 1, 1)), (0.40, (1.10, 1.4, 1.10), "in_out_cubic"), (0.62, (0.95, 0.85, 0.95), "in_out_cubic"), (0.75, (1, 0.85, 1), "in_cubic"),
                            (0.90, (1.08, 0.70, 1.08), "out_quad"), (1.2, (1, 1.12, 1), "in_out_cubic"), (1.7, (1, 1, 1), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.40, (0, 0, 0)), (0.62, (-10, 0, 0), "in_out_cubic"), (0.75, (25, 0, 0), "in_cubic"), (0.90, (25, 0, 0)),
                          (1.2, (-6, 0, 0), "in_out_cubic"), (1.7, (0, 0, 0), "in_out_cubic")])

    hit = Clip("HitReact", 0.4)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.08, (-7, 0, 0), "out_cubic"), (0.40, (-2, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.08, (0, 0, -0.07), "out_cubic"), (0.40, (0, 0, -0.02), "in_out_cubic")])
    hit.keys("body", "scale", [(0, (1, 1, 1)), (0.08, (1.02, 0.96, 1.02), "out_cubic"), (0.40, (1, 1, 1), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.08, (14, 0, 0), "out_cubic"), (0.40, (0, 0, 0), "in_out_cubic")])
    hit.keys("top", "scale", [(0, (1, 1, 1)), (0.08, (1, 0.8, 1), "out_cubic"), (0.40, (1, 1, 1), "in_out_cubic")])

    vic = Clip("Victory", 1.4)
    vic.keys("body", "scale", [(0, (1, 1, 1)), (0.4, (1.02, 1.05, 1.02), "out_back"), (1.4, (1, 1, 1), "in_out_cubic")])
    vic.keys("body", "pos", [(0, (0, 0, 0)), (0.4, (0, 0.03, 0), "out_back"), (1.4, (0, 0, 0), "in_out_cubic")])
    vic.keys("top", "scale", [(0, (1, 1, 1)), (0.4, (1.1, 1.5, 1.1), "out_cubic"), (0.9, (1.05, 1.25, 1.05), "in_out_cubic"), (1.4, (1.05, 1.25, 1.05))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (0.9, (0, 0, 3), "in_out_cubic"), (1.4, (0, 0, 3))])

    # ---- Taunt (1.2 s): the brazier roars up and the whole tower lurches at the enemy
    T = Clip("Taunt", 1.2)
    T.keys("top", "scale", [(0, (1, 1, 1)), (0.22, (1.05, 0.8, 1.05), "in_out_cubic"), (0.42, (1.30, 1.85, 1.30), "out_cubic"), (0.80, (1.18, 1.55, 1.18), "in_out_cubic"), (1.2, (1, 1, 1), "in_out_cubic")])
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.42, (-8, 0, 0), "out_cubic"), (0.80, (6, 0, 2), "in_out_cubic"), (1.2, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "scale", [(0, (1, 1, 1)), (0.22, (1.04, 0.94, 1.04), "in_out_cubic"), (0.42, (0.97, 1.06, 0.97), "out_cubic"), (0.55, (1.03, 0.96, 1.03), "in_cubic"), (1.2, (1, 1, 1), "in_out_cubic")])
    T.keys("body", "pos", [(0, (0, 0, 0)), (0.22, (0, -0.02, -0.04), "in_out_cubic"), (0.46, (0, 0, 0.12), "out_cubic"), (0.58, (0, -0.02, 0.12), "in_cubic"), (0.9, (0, 0, 0.05), "in_out_cubic"), (1.2, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "rot", [(0, (0, 0, 0)), (0.22, (-3, 0, 0), "in_out_cubic"), (0.46, (9, 0, 0), "out_cubic"), (0.58, (7, 0, 0)), (1.2, (0, 0, 0), "in_out_cubic")])

    # ---- Surrender (2.0 s, holds): the brazier fire dies down to embers and the tower sags and settles
    S = Clip("Surrender", 2.0)
    S.keys("top", "scale", [(0, (1, 1, 1)), (0.30, (1.12, 1.35, 1.12), "out_cubic"), (1.2, (1.0, 0.14, 1.0), "in_out_cubic"), (2.0, (0.96, 0.08, 0.96), "in_out_cubic")])
    S.keys("top", "rot", [(0, (0, 0, 0)), (1.2, (4, 0, 2), "in_out_cubic"), (2.0, (5, 0, 3))])
    S.keys("body", "scale", [(0, (1, 1, 1)), (0.5, (1.03, 0.97, 1.03), "in_out_cubic"), (1.3, (1.05, 0.90, 1.05), "in_out_cubic"), (2.0, (1.06, 0.88, 1.06), "in_out_cubic")])
    S.keys("body", "pos", [(0, (0, 0, 0)), (1.3, (0, -0.03, 0.02), "in_out_cubic"), (2.0, (0, -0.035, 0.02))])
    S.keys("body", "rot", [(0, (0, 0, 0)), (1.3, (5, 0, 1.5), "in_out_cubic"), (2.0, (6, 0, 2))])
    return [idle, move, A, hit, vic, T, S]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("emberhold", "rook", rig, make_clips(), impact_time=0.75, strike_range=0.10, attack_style="slam", seed=5)
    C.pedestal_parts(p)
    def soot(P):
        k = 0.62 + 0.38 * smoothstep(0.22, 0.52, P[:, 1]) - 0.10 * smoothstep(0.92, 1.0, P[:, 1])
        return k[:, None] * np.array([1.16, 0.97, 0.80])
    p.add("shaft", shaft(), "EH_Stone", "body", tint=soot)
    p.add("corbel_ring", corbel_ring(), "EH_Stone", "body")
    p.add("corbel_brackets", corbel_brackets(), "EH_Stone", "body", uv_scale=2)
    wall, mer, caps = parapet()
    p.add("parapet", wall, "EH_Stone", "body")
    p.add("merlons", mer, "EH_Stone", "body", uv_scale=2)
    p.add("merlon_caps", caps, "EH_Bronze", "body")
    for i, b in enumerate(bands()):
        p.add(f"band_{i}", b, "EH_Bronze", "body")
    p.add("band_rivets", band_rivets(), "EH_Bronze", "body", lod1=None)
    st, rv = straps_and_rivets()
    p.add("straps", st, "EH_Bronze", "body")
    p.add("strap_rivets", rv, "EH_Bronze", "body", lod1=None)
    cl, rod = banner()
    p.add("banner", cl, "EH_Cloth", "body", uv_scale=2, tint=lambda P: np.clip(0.42 + 0.58 * smoothstep(0.70, 0.95, P[:, 1]), 0, 1))
    p.add("banner_rod", rod, "EH_Bronze", "body")
    p.add("swag_chains", swag_chains(), "EH_Steel", "body", lod1=None)
    door(p)
    fr, dk, gl = slits(p)
    p.add("slit_frames", fr, "EH_Bronze", "body")
    p.add("slit_recess", dk, "EH_Steel", "body", lod1=None)
    p.add("slit_glow", gl, "EH_EmberVein", "body", lod1="keep", bake=False)
    rubble(p)
    ram(p)
    brazier(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
