"""emberhold_rook - Emberhold Forge Bastion.

A squat siege-tower of soot-black masonry (pillowed blocks, offset courses, ledged batter) held by bronze hoops and
riveted straps, a corbelled machicolation ring and merlons, a working brazier for a crown with a fan of ember flame
tongues, and a bronze ram-head battering beam on chains across its face.  Built from docs/art/emberhold_rook.md.
Bones: root (plinth), body (tower, merlons, brazier bowl), weapon (the ram, hinged on its cradle), top (coals + flames) with three
flame_* children.  Five big merlons on a flared 0.67 parapet; the fire burns up through the crenels.
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


RAM_PIV = (0.0, 0.565, 0.30)          # hinge of the ram beam (on its cradle)
FL_BASE = 1.050
MER_A = [36.0 + 72.0 * k for k in range(5)]       # merlon centres (a crenel is centred on the front, a merlon on the back)
CRE_A = [72.0 * k for k in range(5)]              # crenel centres
R_PAR = 0.336                                     # parapet / merlon outer radius (0.67 wide)


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.22, 0))
    r.add("top", "body", (0, 1.00, 0))
    r.add("weapon", "body", RAM_PIV)
    r.add("flame_a", "top", (0, FL_BASE, 0))
    r.add("flame_b", "top", (0, FL_BASE, 0))
    r.add("flame_c", "top", (0, FL_BASE, 0))
    r.socket("socket_weapon_R", "weapon", (0, 0.56, 0.54))
    r.socket("socket_cast", "top", (0, 1.12, 0))
    r.socket("socket_impact", "body", (0, 0.30, 0.46))
    r.socket("socket_head", "top", (0, 1.22, 0))
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
    prof = [(0.272, 0.860), (0.286, 0.866), (0.296, 0.880), (0.300, 0.888), (0.320, 0.900), (0.324, 0.912), (0.338, 0.926),
            (0.342, 0.946), (0.341, 0.972), (0.334, 0.984), (0.300, 0.986)]
    ring = g.lathe(np.array(prof), 32, crease=48).noised(0.0024, 24, 2, seed=6)
    return ring


def corbel_brackets():
    # stepped bracket profile in the (radial, y) plane, extruded tangentially; two big stone corbels under every merlon
    poly = np.array([(0.296, 0.880), (0.346, 0.930), (0.346, 0.986), (0.300, 0.986), (0.296, 0.940)])
    base = g.extrude(poly - [0.325, 0.0], 0.050, 0.005, 1)
    out = []
    for a in MER_A:
        for s in (-1, 1):
            out.append(base.rotated(0, 90, 0).translated(0.0, 0, 0.325).rotated(0, a + s * 13.5, 0))
    return merge(out)


def sector_solid(loop, sweep_deg, ang_deg, segs, crease=50.0, subdiv=0.0):
    """A closed ring-sector solid: `loop` = (r, y) outline listed counter-clockwise (outer wall bottom->top, then back in), revolved
    over `sweep_deg` centred on ang_deg (0 = +Z, toward +X), with flat end caps."""
    loop = np.asarray(loop, dtype=np.float64)
    prof = np.vstack([loop, loop[:1]])
    body = g.lathe(prof, segs, sweep=sweep_deg, start=-sweep_deg / 2, crease=crease)
    parts = [body]
    tris = g.triangulate_polygon(loop)
    cy = loop[:, 1].mean()
    cr = loop[:, 0].mean()
    for sgn in (-1, 1):
        th = math.radians(sgn * sweep_deg / 2)
        P = np.column_stack([loop[:, 0] * math.sin(th), loop[:, 1], loop[:, 0] * math.cos(th)])
        F = np.asarray(tris)
        n = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]]).sum(axis=0)
        tang = np.array([math.cos(th), 0.0, -math.sin(th)]) * sgn          # outward tangent direction at this end
        if np.dot(n, tang) < 0:
            F = F[:, ::-1]
        parts.append(g.Mesh(P, F, np.column_stack([loop[:, 0], loop[:, 1]]) / 0.25))
    m = merge(parts).shade(crease)
    if subdiv > 0:
        m = m.subdivided_to(subdiv)
    return m.rotated(0, ang_deg, 0)


def parapet():
    wall = g.lathe(np.array([(0.300, 0.985), (R_PAR, 0.986), (R_PAR - 0.002, 1.034), (0.328, 1.040), (0.300, 1.040)]), 40, crease=45)
    stones, caps, plates = [], [], []
    ro, ri, y0, h = R_PAR, 0.262, 1.040, 0.130
    for a in MER_A:
        # chunky tooth: slight batter, chamfered crown
        loop = [(ro, y0), (ro - 0.003, y0 + h * 0.80), (ro - 0.012, y0 + h), (ri + 0.012, y0 + h), (ri + 0.002, y0 + h * 0.80), (ri, y0)]
        stones.append(sector_solid(loop, 41.0, a, 6, subdiv=0.085))
        cl = [(ro + 0.006, y0 + h - 0.004), (ro + 0.006, y0 + h + 0.010), (ro - 0.003, y0 + h + 0.016), (ri + 0.003, y0 + h + 0.016),
              (ri - 0.003, y0 + h + 0.010), (ri - 0.003, y0 + h - 0.004)]
        caps.append(sector_solid(cl, 42.5, a, 6, crease=40))
        pl = [(ro + 0.0, y0 + 0.012), (ro + 0.009, y0 + 0.016), (ro + 0.009, y0 + 0.100), (ro + 0.0, y0 + 0.108), (ro - 0.004, y0 + 0.108), (ro - 0.004, y0 + 0.012)]
        plates.append(sector_solid(pl, 8.0, a, 2, crease=40))
    return wall, merge(stones).noised(0.0018, 30, 2, seed=8), merge(caps), merge(plates)


def crenel_glow():
    """Ember-lit floors of the five crenels: the fire is seen burning in the notches."""
    out = []
    for a in CRE_A:
        m = g.lathe(np.array([(0.325, 1.0415), (0.262, 1.0415)]), 6, sweep=26.0, start=-13.0, crease=60)
        out.append(m.rotated(0, a, 0))
    return merge(out)


def parapet_collar():
    return g.torus(R_PAR + 0.004, 0.0085, 40, 5).translated(0, 0.988, 0)


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
    beam = g.tube([along(0.185), along(0.300), along(0.405)], [0.066, 0.071, 0.080], sides=12, samples=2, cap=None, up=(1, 0, 0))
    beam = beam.noised(0.0035, 26, 3, seed=14)
    p.add("ram_beam", beam, "EH_Bronze", "weapon")
    hoops = [g.torus(0.0785 + 0.0035 * i + 0.0075, 0.0085, 14, 4).rotated(90, 0, 0).translated(*along(z)) for i, z in enumerate((0.300, 0.345, 0.385))]
    p.add("ram_hoops", merge(hoops), "EH_Steel", "weapon")
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
    p.add("ram_head", merge([skull, muzzle, brow, nose, chin] + ears).noised(0.0022, 34, 2, seed=15), "EH_Bronze", "weapon")
    nostril = g.instances(g.dome(0.010, 0.006, 6, 1).rotated(90, 0, 0), [(s * 0.020, cy - 0.012, cz + 0.152) for s in (-1, 1)], [(0, 0, 1)] * 2)
    p.add("ram_nostrils", nostril, "EH_Steel", "body", lod1=None)
    collar = g.torus(0.082, 0.012, 16, 5).rotated(90, 0, 0).translated(cx, cy, cz - 0.075)
    p.add("ram_collar", collar, "EH_Steel", "weapon")
    horns = []
    for s in (-1, 1):
        path = [(s * 0.050, cy + 0.052, cz - 0.006), (s * 0.098, cy + 0.066, cz - 0.060), (s * 0.150, cy + 0.030, cz - 0.100),
                (s * 0.168, cy - 0.040, cz - 0.070), (s * 0.156, cy - 0.078, cz + 0.002), (s * 0.130, cy - 0.060, cz + 0.058),
                (s * 0.108, cy - 0.020, cz + 0.078)]
        rad = [0.038, 0.037, 0.034, 0.028, 0.021, 0.013, 0.004]
        horn = g.tube(path, rad, sides=7, samples=3, cap="round", cap_steps=1, up=(0, 1, 0),
                      radius_fn=lambda t: 1.0 + 0.07 * math.cos(t * TAU * 5) * (1 - t))
        horns.append(horn.noised(0.0018, 36, 2, seed=16))
    p.add("ram_horns", merge(horns), "EH_Bronze", "weapon")
    # forged forehead boss: a flat-faced striking plate between the horns
    plate = g.extrude(np.array([(-0.040, -0.030), (0.040, -0.030), (0.050, 0.0), (0.038, 0.040), (-0.038, 0.040), (-0.050, 0.0)]), 0.016, 0.005, 1)
    plate = plate.rotated(-58, 0, 0).translated(cx, cy + 0.050, cz + 0.052)
    p.add("ram_forehead_plate", plate, "EH_Steel", "weapon")
    eyes = g.instances(g.superellipsoid((0.0075, 0.0045, 0.0045), 0.7, 0.7, 3, 6).rotated(0, 0, 0), [(s * 0.062, cy + 0.016, cz + 0.060) for s in (-1, 1)],
                       [(s * 0.3, 0.2, 1) for s in (-1, 1)])
    p.add("ram_eyes", eyes, "EH_EmberVein", "weapon", lod1="keep", bake=False)


# ======================================================================================= brazier crown (bone: top)
def brazier(p: Piece):
    prof = np.array([(0.0, 1.000), (0.075, 1.000), (0.150, 1.020), (0.205, 1.062), (0.230, 1.100), (0.224, 1.108), (0.212, 1.104),
                     (0.196, 1.078), (0.140, 1.040), (0.070, 1.024), (0.0, 1.022)])
    bowl = g.lathe(prof, 24, crease=50).noised(0.0025, 24, 2, seed=21)
    p.add("brazier_bowl", bowl, "EH_Bronze", "body")
    rim = g.torus(0.2185, 0.0072, 28, 5).translated(0, 1.1065, 0)
    hoop = g.torus(0.178, 0.0065, 24, 4).translated(0, 1.050, 0)
    lugs = []
    for a in MER_A:                       # one lug under every merlon angle
        l = g.extrude(g.rect_poly(0.040, 0.034), 0.046, 0.008, 1).rotated(90, 0, 0).translated(0, 1.072, 0.236)
        lugs.append(l.rotated(0, a, 0))
    p.add("brazier_rim_lugs", merge([rim, hoop] + lugs), "EH_Bronze", "body")
    feet = []
    for i in range(4):
        f = g.tube([(0.060, 1.014, 0), (0.110, 1.006, 0), (0.150, 0.992, 0)], [0.018, 0.016, 0.014], sides=5, samples=1, cap="round",
                   cap_steps=1, smooth=True)
        feet.append(f.rotated(0, i * 90 + 45, 0))
    p.add("brazier_feet", merge(feet), "EH_Steel", "body", lod1=None)
    coals = g.superellipsoid((0.190, 0.020, 0.190), 0.5, 0.7, 4, 14).translated(0, 1.050, 0).noised(0.009, 14, 2, seed=22)
    p.add("coals", coals, "EH_Coal", "top", lod1="keep", bake=False)
    # flame fan: five outer tongues leaning out INTO the crenels, six inner tongues, a tall centre tongue
    cfg = [(0.0, 0.0, 1.198, 0.058, "flame_c")]
    for i in range(6):
        cfg.append((0.098, math.radians(30 + 60 * i), [1.168, 1.180, 1.160, 1.174, 1.156, 1.176][i], 0.046, "flame_c"))
    for i, a in enumerate(CRE_A):
        cfg.append((0.200, math.radians(a), [1.150, 1.144, 1.156, 1.142, 1.148][i], 0.038, "flame_a" if math.sin(math.radians(a)) > 0.1 else "flame_b" if math.sin(math.radians(a)) < -0.1 else "flame_c"))
    groups = {"flame_a": [], "flame_b": [], "flame_c": []}
    lean = math.radians(3)
    y0 = FL_BASE
    for k, (rr, ang, top_y, wid, bone) in enumerate(cfg):
        bx, bz = rr * math.sin(ang), rr * math.cos(ang)
        h = top_y - y0
        side = (-1) ** k * (0.014 if rr < 0.15 else 0.008)
        tx, tz = math.cos(ang) * side, -math.sin(ang) * side
        ox, oz = math.sin(ang), math.cos(ang)
        grow = 0.030 if rr > 0.15 else (0.012 if rr else 0.0)
        pts = [(bx, y0, bz), (bx + ox * grow * 0.5 + tx, y0 + h * 0.36, bz + oz * grow * 0.5 + tz),
               (bx + ox * grow * 0.85 - tx * 0.9, y0 + h * 0.70, bz + oz * grow * 0.85 - tz * 0.9),
               (bx + ox * grow + tx * 0.7, top_y, bz + oz * grow + tz * 0.7)]
        pts = [(x, y, z + (y - y0) * math.tan(lean)) for x, y, z in pts]
        radial = (ox, 0, oz) if rr else (0, 0, 1)
        t = g.tube(pts, [wid, wid * 0.90, wid * 0.55, 0.004], sides=6, samples=2, cap="round", cap_steps=1, ellipse=(0.55, 1.45), up=radial)
        groups[bone].append(t)
    for b, ms in groups.items():
        p.add("flames_" + b[-1], merge(ms), "EH_Flame", b, lod1="keep", bake=False)
    sp = g.instances(g.superellipsoid((0.007, 0.010, 0.007), 0.7, 0.7, 3, 6), [(0.05, 1.200, 0.03), (-0.07, 1.190, -0.02), (0.01, 1.194, -0.08)],
                     [(0, 1, 0)] * 3)
    p.add("sparks", sp, "EH_Flame", "flame_c", lod1=None, bake=False)


# ======================================================================================= clips
# ======================================================================================= clips
# The tower is rigid masonry: it never bends, it SQUASHES / STRETCHES (volume-preserving scale on `body`, pivot on the plinth top), LEANS
# (rocking about the base edge it tips onto, so it never sinks through the plinth) and HOPS.  The ram hinges on its cradle (`weapon`), the
# fire (`top` + three `flame_*` bones) lags behind and flickers.  Everything is authored as eased Curves, sampled densely and written as
# LINEAR keys (60 fps on the Attack, with a key exactly on the impact frame).
from anim.curves import Curve, spring_follow      # noqa: E402
from geom import rot_matrix                       # noqa: E402
from anim import xf                               # noqa: E402

IMPACT = 0.75
R_BASE = 0.30                     # base radius the tower rocks on
VOL = 0.85                        # how much of a volume-preserving bulge the squash makes
BODY_REST = np.array([0.0, 0.22, 0.0])
WEAPON_LOCAL = np.array(RAM_PIV) - BODY_REST      # weapon bone rest, relative to `body`


class Rec:
    """Dense clip recorder: every channel is an (n, 3) array on the frame grid; scale channels are built from scalar squash curves."""

    def __init__(self, name, T, fps=30, loop=False):
        self.name, self.T, self.fps, self.loop = name, float(T), fps, loop
        self.n = int(round(T * fps)) + 1
        self.t = np.linspace(0.0, T, self.n)
        self.ch = {}
        self.extras = {}

    # ---- sampling
    def s(self, keys, loop=None):
        c = Curve(keys, loop=loop)
        return np.array([np.atleast_1d(c(t)) for t in self.t])

    def sc(self, keys, loop=None):
        return self.s(keys, loop)[:, 0]

    def z3(self):
        return np.zeros((self.n, 3))

    def sine(self, f, amp, ph=0.0):
        return amp * np.sin(TAU * f * self.t + ph)

    # ---- channels
    def add(self, bone, path, arr):
        arr = np.asarray(arr, dtype=np.float64)
        if arr.ndim == 1:
            arr = np.column_stack([arr, np.zeros(self.n), np.zeros(self.n)])
        self.ch[(bone, path)] = self.ch.get((bone, path), 0.0) + arr

    def squash(self, bone, sy, sx=None):
        """volume-preserving scale from the vertical factor (sx = sz = sy^(-VOL/2) unless given)."""
        sy = np.asarray(sy, dtype=np.float64)
        sxz = sy ** (-0.5 * VOL) if sx is None else np.asarray(sx)
        self.ch[(bone, "scale")] = np.column_stack([sxz, sy, sxz])

    def follow(self, x, freq, zeta):
        """second-order lag of an (n,d) signal (loops are solved periodically by running 3 cycles)."""
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x[:, None]
        if self.loop:
            m = self.n - 1
            x3 = np.concatenate([x[:-1]] * 3 + [x[-1:]])
            y = spring_follow(x3, 1.0 / self.fps, freq, zeta, y0=x3[0])
            return y[2 * m:2 * m + self.n]
        return spring_follow(x, 1.0 / self.fps, freq, zeta, y0=x[0])

    def emit(self):
        c = Clip(self.name, self.T, loop=self.loop, fps=self.fps)
        for (bone, path), arr in self.ch.items():
            for t, v in zip(self.t, arr):
                c.key(bone, path, float(t), v, "linear")
        c.extras.update(self.extras)
        return c


def rock_pos(rot):
    """Rocking about the base edge the tower tips onto: translation that keeps that edge on the plinth.  rot: (n,3) Euler deg."""
    out = np.zeros((len(rot), 3))
    for i, e in enumerate(rot):
        R = rot_matrix(*e)
        d = R @ np.array([0.0, 1.0, 0.0])
        h = np.array([d[0], 0.0, d[2]])
        L = np.linalg.norm(h)
        if L < 1e-6:
            continue
        edge = R_BASE * h / L
        out[i] = edge - R @ edge
    return out


def body_channels(r, rot, pos, sy, rock=0.9):
    """Write body rot / pos / squash; the lean also gets the base-edge rocking translation."""
    r.add("body", "rot", rot)
    r.add("body", "pos", np.asarray(pos) + rock * rock_pos(rot))
    r.squash("body", sy)


def flicker_set(r, intensity, loop_T=None, spread=None, a_amp=2.4, vig=1.0):
    """Fire: top squash + per-group flicker (rz/rx sway and scale) on flame_a/b/c.  `intensity` multiplies the flicker amplitude;
    `spread` (deg, >=0) opens the tongues outward into the crenels."""
    t = r.t
    k = 1.0 if loop_T is None else 1.0 / loop_T

    def fl(freqs, amps, ph):
        v = np.zeros(r.n)
        for f, a, p in zip(freqs, amps, ph):
            ff = round(f * loop_T) * k if loop_T else f
            v = v + a * np.sin(TAU * ff * t + p)
        return v
    inten = np.asarray(intensity) * np.ones(r.n)
    spread = np.zeros(r.n) if spread is None else np.asarray(spread)
    for bone, ph, sgn in (("flame_a", 0.0, -1.0), ("flame_b", 2.1, 1.0), ("flame_c", 4.0, 0.0)):
        sway = fl([1.3, 2.9, 4.7], [1.0, 0.55, 0.30], [ph, ph + 1.3, ph + 2.2]) * a_amp * inten
        lean = fl([1.7, 3.3], [1.0, 0.5], [ph + 0.7, ph + 2.9]) * a_amp * 0.7 * inten
        r.add(bone, "rot", np.column_stack([lean, np.zeros(r.n), sway + sgn * spread]))
        sy = 1.0 + fl([2.3, 3.9, 6.1], [0.060, 0.045, 0.022], [ph + 0.3, ph + 1.1, ph + 2.7]) * inten * vig
        r.squash(bone, sy, sx=1.0 + (sy - 1.0) * -0.35)


# ---------------------------------------------------------------------------------------------- Idle
def clip_idle():
    T = 2.4
    r = Rec("Idle", T, 30, loop=True)
    w = 1.0 / T
    sy = 1.0 + r.sine(w, 0.0075, -math.pi / 2 + 0.4)                      # slow breath: the whole tower swells a hair
    rot = np.column_stack([r.sine(w, 0.40, 0.7), np.zeros(r.n), r.sine(w, 0.30, 2.4)])
    body_channels(r, rot, r.z3(), sy, rock=0.9)
    # fire: top breathes with a layered flicker; lags the tower
    top_sy = 1.0 + r.sine(3 * w, 0.065, 0.2) + r.sine(5 * w, 0.040, 1.3) + r.sine(9 * w, 0.020, 2.2)
    r.squash("top", top_sy, sx=1.0 + (top_sy - 1.0) * -0.3)
    lag = r.follow(rot, 3.0, 0.3)
    r.add("top", "rot", 0.9 * (lag - rot))
    # ram nods very slightly on its cradle
    r.add("weapon", "rot", np.column_stack([r.sine(w, 0.9, 1.9) + 0.6 * (r.follow(rot, 2.2, 0.25)[:, 0] - rot[:, 0]), np.zeros(r.n), np.zeros(r.n)]))
    flicker_set(r, 1.0, loop_T=T)
    return r.emit()


# ---------------------------------------------------------------------------------------------- Move
def clip_move():
    T = 0.7
    r = Rec("Move", T, 60, loop=True)
    # heavy hop: coil -> spring -> hang -> slam down -> squash -> rebound -> settle
    sy = r.sc([(0, 1.0), (0.12, 0.87, "in_out_cubic"), (0.22, 1.09, "out_cubic"), (0.32, 1.04, "in_out_quad"), (0.47, 1.07, "in_quad"),
               (0.505, 0.85, "out_quad"), (0.60, 1.045, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    y = r.sc([(0, 0.0), (0.12, 0.0), (0.22, 0.030, "out_cubic"), (0.33, 0.062, "out_quad"), (0.505, 0.0, "in_quad"), (T, 0.0)])
    z = r.sc([(0, -0.004), (0.12, -0.012, "in_out_cubic"), (0.33, 0.014, "out_cubic"), (0.505, 0.018, "in_quad"), (T, -0.004, "in_out_cubic")])
    rx = r.sc([(0, 0.0), (0.12, -3.0, "in_out_cubic"), (0.30, 4.5, "out_cubic"), (0.47, 3.0, "in_out_cubic"), (0.505, -1.6, "out_quad"), (0.60, 1.2, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    rz = r.sc([(0, 0.0), (0.22, 1.2, "in_out_cubic"), (0.47, -0.8, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), y, z]), sy, rock=0.9)
    # fire stretches up as the tower coils, whips on the landing
    top_sy = r.sc([(0, 1.0), (0.12, 1.22, "in_out_cubic"), (0.30, 0.88, "in_out_cubic"), (0.50, 0.95, "in_out_cubic"), (0.56, 1.38, "out_cubic"), (T, 1.0, "in_out_cubic")])
    r.squash("top", top_sy, sx=1.0 + (top_sy - 1.0) * -0.3)
    lag = r.follow(rot, 3.0, 0.3)
    r.add("top", "rot", 1.0 * (lag - rot))
    # ram: left behind on the take-off, nods hard on the landing
    wrx = r.sc([(0, 0.0), (0.12, -3.0, "in_out_cubic"), (0.30, -9.0, "out_cubic"), (0.50, -4.0, "in_out_cubic"), (0.53, 9.0, "out_quad"), (0.64, -2.5, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    wz = r.sc([(0, 0.0), (0.12, -0.012, "in_out_cubic"), (0.30, 0.008, "out_cubic"), (0.505, 0.024, "in_quad"), (0.60, -0.006, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    r.add("weapon", "rot", np.column_stack([wrx, np.zeros(r.n), np.zeros(r.n)]))
    r.add("weapon", "pos", np.column_stack([np.zeros(r.n), np.zeros(r.n), wz]))
    flicker_set(r, 1.3, loop_T=T)
    r.extras["footContacts"] = {"body": [[0.495, 0.60]]}
    return r.emit()


# ---------------------------------------------------------------------------------------------- Attack
def ram_follow(r, rot, k=0.5):
    """ram hangs behind the tower's lean: relative pitch = k * (lagged - actual)."""
    lag = r.follow(rot, 2.4, 0.28)
    return k * (lag[:, 0] - rot[:, 0])


def clip_attack():
    T, I = 1.7, IMPACT
    r = Rec("Attack", T, 60)
    # coil -> rise and rear back (hang) -> SLAM (stretch, then squash on the impact frame) -> hold -> rebound with one overshoot
    sy = r.sc([(0, 1.0), (0.38, 0.89, "in_out_cubic"), (0.62, 1.11, "in_out_cubic"), (I, 0.88, "in_cubic"), (0.84, 0.85, "out_quad"),
               (1.08, 1.05, "in_out_cubic"), (1.30, 0.985, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    rx = r.sc([(0, 0.0), (0.38, -4.5, "in_out_cubic"), (0.62, -10.0, "in_out_cubic"), (I + 0.02, 15.0, "in_cubic"), (0.88, 13.0, "out_quad"),
               (1.10, -2.5, "in_out_cubic"), (1.34, 1.0, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    rz = r.sc([(0, 0.0), (0.38, 0.8, "in_out_cubic"), (0.62, -0.8, "in_out_cubic"), (I, 0.0, "in_cubic"), (1.1, 0.7, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    z = r.sc([(0, 0.0), (0.38, -0.025, "in_out_cubic"), (0.62, -0.07, "in_out_cubic"), (I + 0.02, 0.13, "in_cubic"), (0.92, 0.12, "out_quad"), (1.38, -0.004, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    y = r.sc([(0, 0.0), (0.38, 0.0), (0.62, 0.02, "in_out_cubic"), (I, -0.012, "in_cubic"), (0.9, -0.008, "out_quad"), (T, 0.0, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), y, z]), sy, rock=0.9)
    # fire flares through the crenels on the coil, is squashed flat by the blow, then balloons back
    top_sy = r.sc([(0, 1.0), (0.38, 1.40, "in_out_cubic"), (0.62, 0.88, "in_out_cubic"), (I, 1.0, "in_cubic"), (0.88, 0.70, "out_quad"),
                   (1.12, 1.28, "out_cubic"), (1.42, 0.97, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    r.squash("top", top_sy, sx=1.0 + (top_sy - 1.0) * -0.3)
    spread = r.sc([(0, 0.0), (0.38, 14.0, "in_out_cubic"), (0.62, 3.0, "in_out_cubic"), (I, 18.0, "in_cubic"), (0.98, 22.0, "out_quad"), (1.4, 0.0, "in_out_cubic")])
    lag = r.follow(rot, 3.0, 0.3)
    r.add("top", "rot", 1.0 * (lag - rot))
    # ram: cocked up on the draw-back, thrust forward and down so its nose lands on the impact frame (leads the tower), then recoils
    wrx = r.sc([(0, 0.0), (0.38, -6.0, "in_out_cubic"), (0.62, -13.0, "in_out_cubic"), (I, 7.0, "snap_in"), (0.90, 5.0, "out_quad"),
                (1.22, -1.5, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    wz = r.sc([(0, 0.0), (0.38, -0.040, "in_out_cubic"), (0.62, -0.085, "in_out_cubic"), (I, 0.125, "snap_in"), (0.96, 0.10, "out_quad"),
               (1.30, -0.006, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    r.add("weapon", "rot", np.column_stack([wrx + ram_follow(r, rot, 0.45), np.zeros(r.n), np.zeros(r.n)]))
    r.add("weapon", "pos", np.column_stack([np.zeros(r.n), np.zeros(r.n), wz]))
    flicker_set(r, 1.4, spread=spread)
    return r.emit()


# ---------------------------------------------------------------------------------------------- HitReact
def clip_hit():
    T = 0.5
    r = Rec("HitReact", T, 60)
    sp = ("spring", 0.42, 2.5)
    rx = r.sc([(0, 0.0), (0.06, -8.0, "out_cubic"), (T, 0.0, sp)])
    rz = r.sc([(0, 0.0), (0.06, 3.0, "out_cubic"), (T, 0.0, ("spring", 0.5, 3.0))])
    z = r.sc([(0, 0.0), (0.06, -0.06, "out_cubic"), (T, 0.0, ("spring", 0.35, 2.0))])
    sy = r.sc([(0, 1.0), (0.06, 0.90, "out_cubic"), (0.18, 1.05, "in_out_cubic"), (0.32, 0.985, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), np.zeros(r.n), z]), sy, rock=0.9)
    top_sy = r.sc([(0, 1.0), (0.06, 0.78, "out_cubic"), (0.18, 1.30, "out_cubic"), (T, 1.0, ("spring", 0.3, 2.0))])
    r.squash("top", top_sy, sx=1.0 + (top_sy - 1.0) * -0.3)
    spread = r.sc([(0, 0.0), (0.06, 0.0), (0.18, 16.0, "out_cubic"), (T, 0.0, "in_out_cubic")])
    lag = r.follow(rot, 3.0, 0.3)
    r.add("top", "rot", 1.0 * (lag - rot))
    wrx = r.sc([(0, 0.0), (0.08, -9.0, "out_cubic"), (T, 0.0, ("spring", 0.5, 3.0))])
    wz = r.sc([(0, 0.0), (0.08, -0.025, "out_cubic"), (T, 0.0, ("spring", 0.4, 2.5))])
    r.add("weapon", "rot", np.column_stack([wrx + ram_follow(r, rot, 0.8), np.zeros(r.n), np.zeros(r.n)]))
    r.add("weapon", "pos", np.column_stack([np.zeros(r.n), np.zeros(r.n), wz]))
    flicker_set(r, 1.5, spread=spread)
    return r.emit()


# ---------------------------------------------------------------------------------------------- Victory
def clip_victory():
    T = 1.6
    r = Rec("Victory", T, 30)
    sy = r.sc([(0, 1.0), (0.22, 0.92, "in_out_cubic"), (0.42, 1.09, "out_cubic"), (0.58, 0.97, "in_out_cubic"), (0.80, 1.025, "in_out_cubic"), (T, 1.015, "in_out_cubic")])
    y = r.sc([(0, 0.0), (0.22, 0.0), (0.40, 0.05, "out_cubic"), (0.56, 0.0, "in_quad"), (T, 0.0)])
    rx = r.sc([(0, 0.0), (0.22, 3.0, "in_out_cubic"), (0.45, -5.0, "out_cubic"), (0.64, -2.0, "in_out_cubic"), (T, -3.0, "in_out_cubic")])
    rz = r.sc([(0, 0.0), (0.45, 0.6, "in_out_cubic"), (1.0, -0.8, "in_out_cubic"), (T, 0.3, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), y, np.zeros(r.n)]), sy, rock=0.9)
    top_sy = r.sc([(0, 1.0), (0.22, 0.82, "in_out_cubic"), (0.45, 1.65, "out_cubic"), (0.70, 1.30, "in_out_cubic"), (T, 1.36, "in_out_cubic")])
    r.squash("top", top_sy, sx=1.0 + (top_sy - 1.0) * -0.3)
    spread = r.sc([(0, 0.0), (0.22, 0.0), (0.45, 22.0, "out_cubic"), (T, 16.0, "in_out_cubic")])
    lag = r.follow(rot, 3.0, 0.3)
    r.add("top", "rot", 1.0 * (lag - rot))
    wrx = r.sc([(0, 0.0), (0.22, 3.0, "in_out_cubic"), (0.45, -11.0, "out_cubic"), (0.64, -6.0, "in_out_cubic"), (T, -8.0, "in_out_cubic")])
    wz = r.sc([(0, 0.0), (0.22, -0.01, "in_out_cubic"), (0.45, 0.05, "out_cubic"), (0.7, 0.03, "in_out_cubic"), (T, 0.03, "in_out_cubic")])
    r.add("weapon", "rot", np.column_stack([wrx + ram_follow(r, rot, 0.6), np.zeros(r.n), np.zeros(r.n)]))
    r.add("weapon", "pos", np.column_stack([np.zeros(r.n), np.zeros(r.n), wz]))
    inten = r.sc([(0, 1.0), (0.3, 1.5, "in_out_cubic"), (T, 2.0, "in_out_cubic")])
    flicker_set(r, inten, spread=spread, a_amp=2.6)
    return r.emit()


# ---------------------------------------------------------------------------------------------- Taunt
def clip_taunt():
    T = 1.4
    r = Rec("Taunt", T, 60)
    sy = r.sc([(0, 1.0), (0.28, 0.90, "in_out_cubic"), (0.36, 1.09, "out_cubic"), (0.46, 0.98, "in_out_cubic"), (0.62, 0.955, "in_out_cubic"),
               (0.72, 1.07, "out_cubic"), (0.86, 0.985, "in_out_cubic"), (1.05, 1.02, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    rx = r.sc([(0, 0.0), (0.28, -6.0, "in_out_cubic"), (0.36, 9.0, "out_quad"), (0.50, 2.0, "in_out_cubic"), (0.62, -4.0, "in_out_cubic"),
               (0.72, 9.0, "out_quad"), (0.95, 0.5, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    z = r.sc([(0, 0.0), (0.28, -0.03, "in_out_cubic"), (0.36, 0.07, "out_quad"), (0.50, 0.02, "in_out_cubic"), (0.62, -0.02, "in_out_cubic"),
              (0.72, 0.07, "out_quad"), (1.0, 0.004, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), np.zeros(r.n)])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), np.zeros(r.n), z]), sy, rock=0.9)
    top_sy = r.sc([(0, 1.0), (0.28, 0.80, "in_out_cubic"), (0.36, 1.80, "out_cubic"), (0.50, 1.10, "in_out_cubic"), (0.62, 0.85, "in_out_cubic"),
                   (0.72, 1.62, "out_cubic"), (1.0, 1.30, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    r.squash("top", top_sy, sx=1.0 + (top_sy - 1.0) * -0.3)
    spread = r.sc([(0, 0.0), (0.28, 0.0), (0.36, 24.0, "out_cubic"), (0.50, 6.0, "in_out_cubic"), (0.62, 3.0, "in_out_cubic"), (0.72, 24.0, "out_cubic"),
                   (1.0, 10.0, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    lag = r.follow(rot, 3.0, 0.3)
    r.add("top", "rot", 1.0 * (lag - rot))
    wrx = r.sc([(0, 0.0), (0.28, -6.0, "in_out_cubic"), (0.36, 6.0, "out_cubic"), (0.50, -2.0, "in_out_cubic"), (0.62, -6.0, "in_out_cubic"),
                (0.72, 6.0, "out_cubic"), (1.0, -1.0, "in_out_cubic"), (T, 0.0, ("spring", 0.3, 2.0))])
    wz = r.sc([(0, 0.0), (0.28, -0.04, "in_out_cubic"), (0.36, 0.09, "out_cubic"), (0.50, 0.0, "in_out_cubic"), (0.62, -0.03, "in_out_cubic"),
               (0.72, 0.09, "out_cubic"), (1.0, 0.0, "in_out_cubic"), (T, 0.0)])
    r.add("weapon", "rot", np.column_stack([wrx + ram_follow(r, rot, 0.5), np.zeros(r.n), np.zeros(r.n)]))
    r.add("weapon", "pos", np.column_stack([np.zeros(r.n), np.zeros(r.n), wz]))
    inten = r.sc([(0, 1.0), (0.3, 1.0), (0.4, 2.0, "out_cubic"), (1.0, 1.6, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    flicker_set(r, inten, spread=spread, a_amp=2.6)
    return r.emit()


# ---------------------------------------------------------------------------------------------- Surrender
PLINTH_Y, TOWER_R, EDGE_R = 0.22, 0.322, 0.375


def _polar(M3):
    U, _, Vt = np.linalg.svd(M3)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    return R


def ground(X, Z):
    """Support height under a point: the plinth top inside its ring, the board outside."""
    return np.where(np.hypot(X, Z) < EDGE_R, PLINTH_Y, 0.0)


def rest_lift(W, cx, cz):
    """Pivot height that puts the lowest contact of the rotated vertices W (pivot-relative) on the ground at pivot xz (cx, cz)."""
    return float(np.max(ground(W[:, 0] + cx, W[:, 2] + cz) - W[:, 1]))


RAM_LIES = dict(pitch=0.0, roll=0.0, yaw=-100.0, az=-42.0, dist=0.41)   # found with a pose search (rests on the plinth, beside the door)


def ram_rest_pose(V):
    """Where the unshipped ram lies: upright on the plinth front-right, beside the door, its head toward the rim."""
    Vs = V[::4]
    k = RAM_LIES
    R = rot_matrix(0, k["yaw"], 0) @ rot_matrix(k["pitch"], 0, 0) @ rot_matrix(0, 0, k["roll"])
    cx, cz = k["dist"] * math.sin(math.radians(k["az"])), k["dist"] * math.cos(math.radians(k["az"]))
    return R, np.array([cx, rest_lift(Vs @ R.T, cx, cz), cz]), k["pitch"], k["roll"], k["yaw"], k["az"], k["dist"]


def clip_surrender(V):
    T, fps = 2.4, 60
    r = Rec("Surrender", T, fps)
    t0 = 0.45
    sy = r.sc([(0, 1.0), (0.28, 0.95, "out_cubic"), (0.55, 0.97, "in_out_cubic"), (1.35, 0.90, "in_out_cubic"), (T, 0.885, "in_out_cubic")])
    rx = r.sc([(0, 0.0), (0.28, -5.0, "out_cubic"), (0.55, -1.0, "in_out_cubic"), (1.40, 9.0, "in_out_cubic"), (T, 10.0, "in_out_cubic")])
    rz = r.sc([(0, 0.0), (0.30, -1.5, "out_cubic"), (0.60, -0.4, "in_out_cubic"), (1.40, 3.5, "in_out_cubic"), (T, 4.2, "in_out_cubic")])
    z = r.sc([(0, 0.0), (0.28, -0.03, "out_cubic"), (0.55, -0.01, "in_out_cubic"), (1.40, 0.03, "in_out_cubic"), (T, 0.03, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    pos = np.column_stack([np.zeros(r.n), np.zeros(r.n), z])
    # ---- the ram: sags on its cradle (authored), is unshipped at t0 and drops under physics onto the plinth
    wrx = r.sc([(0, 0.0), (0.28, -4.0, "out_cubic"), (0.40, 9.0, "in_out_cubic"), (T, 9.0)])

    def body_world(rot_, pos_, sy_):
        out = []
        for e, p, s in zip(rot_, pos_, sy_):
            sxz = s ** (-0.5 * VOL)
            M = np.eye(4)
            M[:3, :3] = rot_matrix(*e) @ np.diag([sxz, s, sxz])
            M[:3, 3] = BODY_REST + p + rock_pos(e[None])[0] * 0.9
            out.append(M)
        return out
    B = body_world(rot, pos, sy)
    i0 = int(round(t0 * fps))

    def weapon_follow(i):
        M = B[i] @ np.block([[rot_matrix(wrx[i], 0, 0), WEAPON_LOCAL[:, None]], [np.zeros((1, 3)), np.ones((1, 1))]])
        return M[:3, 3], _polar(M[:3, :3])
    P0, R0 = weapon_follow(i0)
    Pm, _ = weapon_follow(i0 - 1)
    v0 = (P0 - Pm) * fps + np.array([0.0, 0.0, 0.35])
    Rf, Pf, pitch, roll, yaw, al, d = ram_rest_pose(V)
    q0, qf = xf.quat_from_mat(R0), xf.quat_from_mat(Rf)
    Vs = V[::4]
    G, E, TR = 6.5, 0.34, 0.60
    dt = 1.0 / 240
    steps = int((T - t0) / dt) + 1
    traj_p, traj_R, contacts = [], [], []
    y, vy, tau = P0[1], v0[1], 0.0
    last_c = None
    for k in range(steps):
        tau = k * dt
        u = min(tau / TR, 1.0)
        e = u * u * (3 - 2 * u)
        q = xf.slerp(q0, qf, e)
        R = xf.mat_from_quat(q)
        if last_c is not None:                                  # rocking wobble about the beam axis after each thud
            s = tau - last_c[0]
            R = R @ rot_matrix(0, 0, 5.0 * last_c[1] * math.exp(-s / 0.28) * math.sin(TAU * s / 0.34))
        wh0 = min(tau / (TR * 1.25), 1.0)
        wh0 = wh0 * wh0 * (3 - 2 * wh0)
        cxz = (P0[[0, 2]] + v0[[0, 2]] * tau * math.exp(-tau / 0.3)) * (1 - wh0) + Pf[[0, 2]] * wh0
        floor = rest_lift(Vs @ R.T, cxz[0], cxz[1])
        vy -= G * dt
        y += vy * dt
        if y < floor and tau > 0.01:
            y = floor
            if vy < -0.3:
                contacts.append((t0 + tau, min(1.0, -vy / 1.5)))
                last_c = (tau, min(1.0, -vy / 1.5))
            vy = -E * vy if vy < -0.3 else 0.0
        wh = min(tau / (TR * 1.25), 1.0)
        wh = wh * wh * (3 - 2 * wh)
        xz = (P0[[0, 2]] + v0[[0, 2]] * tau * math.exp(-tau / 0.3)) * (1 - wh) + Pf[[0, 2]] * wh
        traj_p.append(np.array([xz[0], y, xz[1]]))
        traj_R.append(R)
    # ---- tower: the dropped ram thuds through the stone (squash dip + a shiver)
    def bump(tc, A, tau_=0.08):
        s = np.clip(r.t - tc, 0, None)
        return A * (s / tau_) * np.exp(1.0 - s / tau_) * (r.t >= tc)
    sy2, rx2 = sy.copy(), rx.copy()
    for tc, vi in contacts:
        sy2 = sy2 - bump(tc, 0.020 * vi)
        rx2 = rx2 + bump(tc + 0.02, -0.8 * vi) * np.sin(TAU * (r.t - tc) / 0.22)
    rot2 = np.column_stack([rx2, np.zeros(r.n), rz])
    body_channels(r, rot2, pos, sy2, rock=0.9)
    # fire: shrinks into the bowl (embers/smoke only at the end)
    top_sy = r.sc([(0, 1.0), (0.28, 0.78, "out_cubic"), (0.50, 0.95, "in_out_cubic"), (1.25, 0.30, "in_out_cubic"), (T, 0.10, "in_out_cubic")])
    r.squash("top", top_sy, sx=1.0 + (top_sy - 1.0) * -0.25)
    lag = r.follow(rot2, 3.0, 0.3)
    r.add("top", "rot", 1.0 * (lag - rot2))
    inten = r.sc([(0, 1.0), (0.5, 1.0), (1.4, 0.35, "in_out_cubic"), (T, 0.2)])
    flicker_set(r, inten, spread=r.sc([(0, 0.0), (0.28, 0.0), (0.5, 6.0, "out_cubic"), (1.2, 0.0, "in_out_cubic"), (T, 0.0)]), vig=0.5)
    c = r.emit()
    # ---- weapon: dense (world path converted to the body's local frame, ignoring the tower's squash shear)
    B2 = body_world(rot2, pos, sy2)
    quats, dpos = [], []
    for i in range(r.n):
        if i < i0:
            R = rot_matrix(wrx[i], 0, 0)
            quats.append(xf.quat_from_mat(R))
            dpos.append(np.zeros(3))
            continue
        j = min(i - i0, len(traj_p) - 1)
        W = np.eye(4)
        W[:3, :3], W[:3, 3] = traj_R[j], traj_p[j]
        M = np.linalg.inv(B2[i]) @ W
        quats.append(xf.quat_from_mat(_polar(M[:3, :3])))
        dpos.append(M[:3, 3] - WEAPON_LOCAL)
    quats = np.array(quats)
    for i in range(1, len(quats)):
        if np.dot(quats[i], quats[i - 1]) < 0:
            quats[i] = -quats[i]
    c.set_dense("weapon", "rot", r.t, quats)
    c.set_dense("weapon", "pos", r.t, np.array(dpos))
    c.extras["ramRest"] = {"pitch": pitch, "yaw": yaw, "roll": roll, "azimuth": al, "dist": round(float(d), 3), "contacts": [round(float(t), 3) for t, _ in contacts]}
    return c


def make_clips(rig, ram_V=None) -> list[Clip]:
    out = [clip_idle(), clip_move(), clip_attack(), clip_hit(), clip_victory(), clip_taunt()]
    out.append(clip_surrender(ram_V))
    return out


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("emberhold", "rook", rig, [], impact_time=IMPACT, strike_range=0.10, attack_style="slam", seed=5)
    C.pedestal_parts(p)
    def soot(P):
        k = 0.62 + 0.38 * smoothstep(0.22, 0.52, P[:, 1]) - 0.10 * smoothstep(0.92, 1.0, P[:, 1])
        return k[:, None] * np.array([1.16, 0.97, 0.80])
    p.add("shaft", shaft(), "EH_Stone", "body", tint=soot)
    p.add("corbel_ring", corbel_ring(), "EH_Stone", "body")
    p.add("corbel_brackets", corbel_brackets(), "EH_Stone", "body", uv_scale=2)
    wall, mer, caps, plates = parapet()
    p.add("parapet", wall, "EH_Stone", "body")
    p.add("parapet_collar", parapet_collar(), "EH_Bronze", "body")
    p.add("merlons", mer, "EH_Stone", "body", uv_scale=2)
    p.add("merlon_caps", caps, "EH_Bronze", "body")
    p.add("merlon_plates", plates, "EH_Bronze", "body")
    p.add("crenel_glow", crenel_glow(), "EH_Coal", "body", lod1="keep", bake=False)
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
    ram_V = np.vstack([q.mesh.P for q in p.parts if q.bone == "weapon"]) - np.array(RAM_PIV)
    p.clips = make_clips(rig, ram_V)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
