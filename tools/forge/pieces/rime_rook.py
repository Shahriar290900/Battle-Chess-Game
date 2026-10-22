"""rime_rook - Rime Glacier Bastion: four uneven glacial ice monoliths lashed in silver wire around a faceted
obsidian core, a crack of cold light, a crown of tilted ice shards.  Built from docs/art/rime_rook.md.
The tower leans 3 degrees toward -X (baked into the geometry)."""
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

ASSET_ID = "rime_rook"
LEAN = 3.0                           # degrees toward -X (rz +3)
PIV = (0.0, 0.22, 0.0)


def lean(m):
    return m.rotated(0, 0, LEAN, pivot=PIV)


def lp(v):
    """lean a point"""
    a = math.radians(LEAN)
    x, y, z = v[0] - PIV[0], v[1] - PIV[1], v[2]
    return np.array([x * math.cos(a) - y * math.sin(a) + PIV[0], x * math.sin(a) + y * math.cos(a) + PIV[1], z])


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", PIV)
    top = lp((0, 1.0, 0))
    r.add("top", "body", tuple(top))
    r.socket("socket_weapon_R", "body", (0.0, 0.30, 0.34))
    r.socket("socket_cast", "top", tuple(lp((0, 1.12, 0))))
    r.socket("socket_impact", "body", (0.0, 0.30, 0.40))
    r.socket("socket_head", "top", tuple(lp((0, 1.22, 0))))
    return r


# ======================================================================================= obsidian courses + ice monoliths
def block_rings(y0, y1, r0, r1, K=8, rot=0.0, off=(0.0, 0.0), seed=0, jit=0.05, bulge=1.03, jag=0.012, notch=None):
    """Rings (levels x K x 3) of an irregular faceted block; shared by the mesh and the surface-point queries."""
    rng = np.random.default_rng(seed)
    th = (np.arange(K) + (rng.random(K) - 0.5) * 0.3) * TAU / K + math.radians(rot)
    rj = 1 + jit * (rng.random(K) - 0.5) * 2
    H = y1 - y0
    levels = [(0.0, 0.90), (0.05, 1.0), (0.28, 1.0), (0.5, bulge), (0.72, 1.0), (0.93, 0.97), (1.0, 0.86)]
    rings, fs = [], []
    for f, k in levels:
        r = (r0 + (r1 - r0) * f) * k * rj
        y = np.full(K, y0 + H * f)
        if f >= 0.99:
            y = y + (rng.random(K) - 0.35) * jag
        if notch is not None:
            a0, yc, depth, wid = notch
            da = np.abs(((np.degrees(th) - a0 + 180) % 360) - 180)
            w = np.clip(1 - da / wid, 0, 1) * np.clip(1 - np.abs(y0 + H * f - yc) / 0.07, 0, 1)
            r = r - depth * w
        rings.append(np.stack([off[0] + r * np.sin(th), y, off[1] + r * np.cos(th)], 1))
        fs.append(f)
    return np.stack(rings), th, fs


def block(rings):
    return g.loft(rings, closed=True, cap_start=True, cap_end=True, crease=34.0, v_tile=0.12)


COURSES = [  # y0, y1, r0, r1, rot, offset, seed
    (0.225, 0.462, 0.275, 0.248, 0.0, (0.0, 0.0), 11),
    (0.480, 0.672, 0.238, 0.216, 22.5, (0.0, 0.0), 12),
    (0.690, 0.852, 0.212, 0.192, -10.0, (-0.015, 0.015), 13),
    (0.870, 0.992, 0.184, 0.162, 30.0, (0.012, -0.015), 14),
]
_RINGS = [block_rings(c[0], c[1], c[2], c[3], 8, c[4], c[5], c[6], notch=((40.0, 0.56, 0.06, 26.0) if i == 1 else None)) for i, c in enumerate(COURSES)]


def surf(i, y, phi_deg, out=0.004):
    """Point on the surface of course i at height y in direction phi (0 = +Z, toward +X), pushed out by `out`."""
    rings, th, fs = _RINGS[i]
    c = COURSES[i]
    f = float(np.clip((y - c[0]) / (c[1] - c[0]), 0, 1))
    k = int(np.clip(np.searchsorted(fs, f) - 1, 0, len(fs) - 2))
    u = (f - fs[k]) / (fs[k + 1] - fs[k])
    ring = rings[k] * (1 - u) + rings[k + 1] * u
    off = np.array([c[5][0], 0, c[5][1]])
    phi = math.radians(phi_deg)
    d = np.array([math.sin(phi), math.cos(phi)])
    K = len(ring)
    best = None
    for j in range(K):
        a = ring[j][[0, 2]] - off[[0, 2]]
        b = ring[(j + 1) % K][[0, 2]] - off[[0, 2]]
        # solve t*d = a + s*(b-a)
        M = np.array([[d[0], -(b[0] - a[0])], [d[1], -(b[1] - a[1])]])
        try:
            t, s_ = np.linalg.solve(M, a)
        except np.linalg.LinAlgError:
            continue
        if t > 0 and -1e-6 <= s_ <= 1 + 1e-6:
            best = t
            break
    t = best if best is not None else 0.2
    return np.array([off[0] + (t + out) * d[0], y, off[2] + (t + out) * d[1]])


def build_core(p: Piece):
    for i, c in enumerate(COURSES):
        m = lean(block(_RINGS[i][0]))
        m = m.noised(0.004, 14, 2, seed=3 + i) if False else m
        p.add(f"course_{i + 1}", m, "RH_Obsidian", "body", uv_scale=2)
        p.add(f"frost_cap_{i + 1}", frost_layer(m, 0.010, min_ny=0.5, cover=0.4, seed=20 + i), "RH_Frost", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
        # silver rivets round the lower lip + dark arrow slits / chipped facets add detail
        rv = [surf(i, c[0] + 0.03, k * 45 + 22.5 + c[4], 0.0) for k in range(8)]
        nrm = [(math.sin(math.radians(k * 45 + 22.5 + c[4])), 0.0, math.cos(math.radians(k * 45 + 22.5 + c[4]))) for k in range(8)]
        p.add(f"rivets_{i + 1}", lean(g.instances(g.dome(0.0085, 0.007, 6, 1), rv, nrm)), "RH_Silver", "body", lod1=None)
    # obsidian spurs growing out of the back-left of course 3
    sp = cluster(lp(surf(2, 0.74, 215.0, -0.01)), (-0.7, 0.35, -0.7), 3, (0.07, 0.11), (0.013, 0.019), tilt=22, seed=5, flat=0.2, sides=4)
    p.add("obsidian_spurs", sp, "RH_Obsidian", "body")
    # the fissure: a zig-zag crack of cold light crossing courses 1 and 2 (focal point 1)
    pts = []
    n = 12
    for q in range(n + 1):
        y = 0.28 + 0.52 * q / n
        ci = 0 if y < 0.462 else (1 if y < 0.672 else 2)
        y = float(np.clip(y, COURSES[ci][0] + 0.01, COURSES[ci][1] - 0.01))
        phi = 18 + 11 * ((q % 2) - 0.5) * 2 + 2.2 * q
        pts.append(lp(surf(ci, y, phi, 0.0015)))
    p.add("fissure_glow", g.tube(pts, 0.0042, sides=4, samples=1, cap=None, smooth=False), "RH_Glow", "body", bake=False, lod1="keep")
    # arrow slit
    slit = g.extrude(g.rect_poly(0.030, 0.090), 0.012, 0.003, 1).rotated(0, 0, 0).translated(*surf(0, 0.34, 330.0, 0.0))
    p.add("arrow_slit", lean(slit.rotated(0, -30, 0, pivot=tuple(surf(0, 0.34, 330.0, 0.0)))), "RH_Armour", "body", lod1=None)


def build_blocks(p: Piece):
    # five uneven glacial monoliths lashed to the core: long faceted ice crystals at different heights and tilts
    spec = [  # angle, base y, length, radius, tilt (deg outward), base course
        (28, 0.27, 0.50, 0.062, 14, 0), (100, 0.34, 0.40, 0.056, 18, 0), (172, 0.30, 0.56, 0.068, 12, 0),
        (240, 0.52, 0.44, 0.058, 16, 1), (310, 0.46, 0.50, 0.064, 13, 1), (350, 0.74, 0.34, 0.048, 20, 2), (200, 0.76, 0.30, 0.044, 22, 2),
    ]
    sp = []
    for a, by, ln, r, tl, ci in spec:
        base = surf(ci, by, a, -0.02)
        ar = math.radians(a)
        d = unit((math.sin(math.radians(tl)) * math.sin(ar), math.cos(math.radians(tl)), math.sin(math.radians(tl)) * math.cos(ar)))
        sp.append((lp(base), d, ln, r))
    mono = spikes(sp, seed=10, flat=0.30, sides=6, tip=0.34, bend=0.04, jitter=0.12)
    p.add("ice_monoliths", mono, "RH_Ice", "body")
    p.add("ice_monolith_frost", frost_layer(mono, 0.008, min_ny=0.6, cover=0.25, seed=7), "RH_Frost", "body", lod1=None, tint=lambda P: np.full(len(P), 0.6))
    # secondary shards riding on the monoliths
    sec = []
    rng = np.random.default_rng(2)
    for k, (a, by, ln, r, tl, ci) in enumerate(spec):
        for q in range(2):
            ar = math.radians(a + (-30 if q else 30))
            base = surf(ci, by + 0.18 + 0.1 * q, a + (-26 if q else 26), -0.01)
            d = unit((0.6 * math.sin(ar), 0.7, 0.6 * math.cos(ar)))
            sec.append((lp(base), d, 0.10 + 0.07 * rng.random(), 0.018 + 0.006 * rng.random()))
    p.add("ice_secondary", spikes(sec, seed=33, flat=0.28, sides=5, tip=0.4), "RH_Ice", "body")
    # chunky buttress shards around the foot
    cl = []
    for j, a in enumerate((60, 135, 205, 275, 335)):
        ar = math.radians(a)
        base = (0.31 * math.sin(ar), 0.24, 0.31 * math.cos(ar))
        up = (0.55 * math.sin(ar), 1.0, 0.55 * math.cos(ar))
        cl.append(cluster(base, up, 3, (0.12, 0.24), (0.024, 0.036), spread=0.04, tilt=24, seed=40 + j, flat=0.25))
    p.add("buttress_shards", lean(merge(cl)), "RH_Ice", "body")


# ======================================================================================= collars, wire, runes
def build_bands(p: Piece):
    # silver-lashed obsidian collars in the seams between courses; a dim ring of seam light inside each seam
    seams = [(0.471, 0.254), (0.681, 0.224), (0.861, 0.198)]
    col, wires, glow = [], [], []
    for k, (y, r) in enumerate(seams):
        prof = [(r - 0.012, y - 0.016), (r, y - 0.014), (r + 0.010, y), (r, y + 0.014), (r - 0.012, y + 0.016)]
        col.append(g.lathe(prof, 16, crease=30).rotated(0, 12 * k, 0))
        wires.append(rc.helix(r + 0.010, y - 0.016, y + 0.016, 3.0, r=0.0045, sides=4, per_turn=14))
        glow.append(g.torus(r - 0.002, 0.0028, 20, 3).translated(0, y + 0.0, 0))
    p.add("collars", lean(merge(col)), "RH_Armour", "body")
    p.add("collar_wire", lean(merge(wires)), "RH_Silver", "body", tint=lambda P: np.full(len(P), 0.6))
    p.add("seam_light", lean(merge(glow)), "RH_Seam", "body", bake=False, lod1=None)
    # silver tie rods bridging the courses
    rods = []
    for k in range(6):
        a = 15 + k * 60
        pts = [surf(0, 0.40, a, 0.007), surf(1, 0.58, a, 0.007), surf(2, 0.77, a, 0.007), surf(3, 0.93, a, 0.007)]
        rods.append(g.tube(pts, 0.0050, sides=4, samples=1, cap="round", cap_steps=1))
    p.add("tie_rods", lean(merge(rods)), "RH_Silver", "body", lod1=None, tint=lambda P: np.full(len(P), 0.7))
    # silver rune glyphs on the obsidian faces (dim seam light)
    runes = []
    for ci, y in ((0, 0.40), (1, 0.58), (2, 0.77), (3, 0.93)):
        for k in range(8):
            a = _RINGS_ROT[ci] + k * 45 + 22.5
            c = surf(ci, y, a, 0.003)
            def bar(x0, y0, x1, y1, w=0.0065):
                L = math.hypot(x1 - x0, y1 - y0)
                ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) - 90
                return g.extrude(g.rect_poly(w, L), 0.0042, 0.0008, 1).rotated(0, 0, ang).translated((x0 + x1) / 2, (y0 + y1) / 2, 0)
            v = (k * 3 + ci) % 3
            if v == 0:      # fehu-like: stem + two upward ticks
                glyph = [bar(-0.008, -0.02, -0.008, 0.022), bar(-0.008, 0.022, 0.014, 0.004), bar(-0.008, 0.006, 0.012, -0.012)]
            elif v == 1:    # sowilo-like: angular lightning
                glyph = [bar(-0.012, 0.022, 0.006, 0.004), bar(0.006, 0.004, -0.008, -0.004), bar(-0.008, -0.004, 0.012, -0.022)]
            else:           # thurisaz-like: stem + triangle
                glyph = [bar(-0.006, -0.022, -0.006, 0.022), bar(-0.006, 0.012, 0.014, 0.0), bar(0.014, 0.0, -0.006, -0.012)]
            runes.append(merge(glyph).rotated(0, a, 0).translated(*c))
    p.add("runes", lean(merge(runes)), "RH_Seam", "body", bake=False, lod1=None)


_RINGS_ROT = [c[4] for c in COURSES]


# ======================================================================================= crown
def build_crown(p: Piece):
    ring = g.lathe([(0.100, 0.995), (0.150, 1.000), (0.150, 1.030), (0.110, 1.040)], 12, crease=30)
    p.add("crown_ring", lean(ring), "RH_Silver", "top")
    band = g.torus(0.12, 0.0075, 18, 4).translated(0, 1.012, 0)
    p.add("crown_band", lean(band), "RH_Silver", "top", lod1=None)
    specs = [(lp((0, 1.03, 0)), unit((0.02, 1.0, 0.0)), 0.17, 0.036)]
    lens = [0.14, 0.17, 0.19, 0.16]
    for k, a in enumerate((0, 72, 144, 216, 288)):
        ar = math.radians(a)
        ln = (0.14, 0.17, 0.19, 0.20, 0.16)[k]
        t = math.radians(18 + 12 * (k % 3) / 2 + 4)
        d = unit((math.sin(t) * math.sin(ar), math.cos(t), math.sin(t) * math.cos(ar)))
        specs.append((lp((0.09 * math.sin(ar), 1.025, 0.09 * math.cos(ar))), d, ln, 0.030 + 0.006 * (k % 2)))
    # stretch so the central tip hits 1.20
    tall = spikes(specs, seed=80, flat=0.22, sides=6, tip=0.42, bend=0.05)
    p.add("crown_shards", tall, "RH_Ice", "top")
    short = []
    for k in range(4):
        ar = math.radians(36 + k * 90 + 8)
        t = math.radians(35)
        d = unit((math.sin(t) * math.sin(ar), math.cos(t), math.sin(t) * math.cos(ar)))
        short.append((lp((0.15 * math.sin(ar), 1.02, 0.15 * math.cos(ar))), d, 0.08 + 0.03 * (k % 3) / 2, 0.020 + 0.003 * (k % 2)))
    p.add("crown_short", spikes(short, seed=90, flat=0.25, sides=5, tip=0.45), "RH_Ice", "top")
    orb = g.superellipsoid((0.030, 0.030, 0.030), 0.9, 0.9, 5, 9).translated(*lp((0, 1.075, 0)))
    p.add("crown_orb", orb, "RH_Glow", "top", bake=False, lod1="keep")


# ======================================================================================= clips
def make_clips() -> list[Clip]:
    idle = Clip("Idle", 3.0, loop=True)
    idle.keys("top", "rot", [(0, (0, 0, 0)), (1.0, (0, 4, 1.5), "in_out_cubic"), (2.0, (0, -3, -1.0), "in_out_cubic"), (3.0, (0, 0, 0), "in_out_cubic")])
    idle.keys("top", "scale", [(0, (1, 1, 1)), (1.0, (1, 1.03, 1), "in_out_cubic"), (2.0, (1, 1.0, 1), "in_out_cubic"), (3.0, (1, 1, 1), "in_out_cubic")])
    idle.keys("body", "rot", [(0, (0, 0, 0)), (1.5, (0, 0, -0.6), "in_out_cubic"), (3.0, (0, 0, 0), "in_out_cubic")])

    mv = Clip("Move", 0.8, loop=True)
    mv.keys("body", "rot", [(0, (3, 0, 0)), (0.2, (3, 0, -2), "in_out_cubic"), (0.4, (5, 0, 0), "in_out_cubic"), (0.6, (3, 0, 2), "in_out_cubic"), (0.8, (3, 0, 0), "in_out_cubic")])
    mv.keys("body", "pos", [(0, (0, 0, 0)), (0.2, (0, 0.02, 0), "out_quad"), (0.4, (0, 0, 0), "in_quad"), (0.6, (0, 0.02, 0), "out_quad"), (0.8, (0, 0, 0), "in_quad")])
    mv.keys("top", "rot", [(0, (0, 0, 0)), (0.2, (-5, 0, 0), "in_out_cubic"), (0.4, (0, 0, 0), "in_out_cubic"), (0.6, (-5, 0, 0), "in_out_cubic"), (0.8, (0, 0, 0), "in_out_cubic")])

    A = Clip("Attack", 1.8, fps=60)
    A.keys("body", "rot", [(0, (0, 0, 0)), (0.30, (-4, 0, 0), "in_out_cubic"), (0.50, (-6, 0, 0), "in_out_cubic"), (0.62, (-10, 0, 0), "in_out_cubic"), (0.75, (48, 0, 0), "in_cubic"),
                           (0.95, (46, 0, 0)), (1.5, (-3, 0, 0), "in_out_cubic"), (1.8, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.30, (0, 0, 0), "in_out_cubic"), (0.50, (0, 0.02, 0), "in_out_cubic"), (0.62, (0, 0.04, 0), "in_out_cubic"), (0.75, (0, 0, 0.18), "in_cubic"),
                           (0.95, (0, 0, 0.18)), (1.8, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "scale", [(0, (1, 1, 1)), (0.30, (1, 0.96, 1), "in_out_cubic"), (0.62, (1, 1, 1), "in_out_cubic"), (0.75, (1, 1, 1)), (0.95, (1, 0.96, 1), "out_quad"), (1.8, (1, 1, 1), "in_out_cubic")])
    A.keys("top", "scale", [(0, (1, 1, 1)), (0.30, (1, 1.2, 1), "in_out_cubic"), (0.50, (1, 1.35, 1), "in_out_cubic"), (0.56, (1, 0.4, 1), "in_expo"), (0.62, (1, 0.4, 1)),
                            (0.75, (1, 0.8, 1), "out_quad"), (0.95, (1, 0.8, 1)), (1.8, (1, 1, 1), "in_out_cubic")])
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 4), "in_out_cubic"), (0.50, (-10, 0, 4), "in_out_cubic"), (0.62, (0, 0, 0), "in_out_cubic"), (0.75, (30, 0, 0), "in_cubic"),
                          (0.95, (30, 0, 0)), (1.8, (0, 0, 0), "in_out_cubic")])

    hit = Clip("HitReact", 0.4)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.08, (-9, 0, 4), "out_cubic"), (0.40, (-3, 0, 1), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.08, (0, 0, -0.06), "out_cubic"), (0.40, (0, 0, -0.01), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.08, (16, 0, 0), "out_cubic"), (0.40, (0, 0, 0), "in_out_cubic")])
    hit.keys("top", "scale", [(0, (1, 1, 1)), (0.08, (1, 0.9, 1), "out_cubic"), (0.40, (1, 1, 1), "in_out_cubic")])

    vic = Clip("Victory", 1.5)
    vic.keys("top", "scale", [(0, (1, 1, 1)), (0.5, (1, 1.5, 1), "out_back"), (1.5, (1, 1.3, 1), "in_out_cubic")])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (0.5, (0, 0, 0), "out_cubic"), (1.0, (0, 20, 0), "in_out_cubic"), (1.5, (0, 20, 0))])
    vic.keys("body", "pos", [(0, (0, 0, 0)), (0.5, (0, 0.03, 0), "out_back"), (1.5, (0, 0.03, 0))])
    T = Clip("Taunt", 1.3)           # crown shards flare outward and snap back, a defiant hop
    T.keys("top", "scale", [(0, (1, 1, 1)), (0.35, (1.35, 1.30, 1.35), "out_cubic"), (0.55, (1.35, 1.30, 1.35)), (0.64, (0.85, 0.80, 0.85), "in_expo"), (0.90, (1.08, 1.05, 1.08), "out_back"), (1.3, (1, 1, 1), "in_out_cubic")])
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.35, (0, 18, 0), "out_cubic"), (0.64, (0, -10, 0), "in_expo"), (1.3, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "pos", [(0, (0, 0, 0)), (0.25, (0, 0.05, 0), "out_quad"), (0.40, (0, 0.0, 0), "in_quad"), (0.64, (0, 0.02, 0), "out_quad"), (0.80, (0, 0, 0), "in_quad"), (1.3, (0, 0, 0))])
    T.keys("body", "rot", [(0, (0, 0, 0)), (0.25, (-5, 0, 0), "out_cubic"), (0.40, (3, 0, 0), "in_quad"), (0.64, (-3, 0, 2), "out_quad"), (1.3, (0, 0, 0), "in_out_cubic")])
    return [idle, mv, A, hit, vic, T]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "rook", rig, make_clips(), impact_time=0.75, strike_range=0.10, attack_style="slam", seed=6)
    rc.pedestal_parts(p)
    build_core(p)
    build_blocks(p)
    build_bands(p)
    build_crown(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
