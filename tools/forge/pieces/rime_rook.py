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
LEAN = 2.0                           # degrees toward -X (rz +2); the crown (collar + merlons) sits level on top of the leaned shaft
PIV = (0.0, 0.22, 0.0)
SHARD_N = 5


def lean(m):
    return m.rotated(0, 0, LEAN, pivot=PIV)


def lp(v):
    """lean a point"""
    a = math.radians(LEAN)
    x, y, z = v[0] - PIV[0], v[1] - PIV[1], v[2]
    return np.array([x * math.cos(a) - y * math.sin(a) + PIV[0], x * math.sin(a) + y * math.cos(a) + PIV[1], z])


TOPC = lp((0, 1.0, 0))               # crown pivot (top bone) and the x offset of the whole level crown
SHARD_AZ = [36.0 + 72.0 * k for k in range(SHARD_N)]       # shards stand behind the merlons
SHARD_LEN = [0.150, 0.125, 0.140, 0.120, 0.135]
ORB_C = (float(TOPC[0]), 1.075, 0.0)


def _shard_geom(k):
    """-> (mesh, pivot): crown shard k in absolute rest coordinates (aimed outward 14 deg), pivot = its centroid."""
    az = math.radians(SHARD_AZ[k])
    t = math.radians(14.0 + 3 * (k % 2))
    d = unit((math.sin(t) * math.sin(az), math.cos(t), math.sin(t) * math.cos(az)))
    base = np.array([TOPC[0] + 0.105 * math.sin(az), 1.043, 0.105 * math.cos(az)])
    m = shard(SHARD_LEN[k], 0.030 + 0.003 * (k % 2), sides=5, tip=0.42, flat=0.2, bend=0.02 * (1 if k % 2 else -1), jitter=0.15, seed=70 + k * 5).aimed(d, base)
    return m, base + d * SHARD_LEN[k] * 0.38


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", PIV)
    r.add("runes", "body", PIV)
    r.add("top", "body", tuple(TOPC))
    r.add("orb", "top", ORB_C)
    for k in range(SHARD_N):
        r.add(f"shard_{k}", "top", tuple(float(v) for v in _shard_geom(k)[1]))
    r.socket("socket_weapon_R", "body", (0.0, 0.30, 0.34))
    r.socket("socket_cast", "top", (float(TOPC[0]), 1.12, 0.0))
    r.socket("socket_impact", "body", (0.0, 0.30, 0.40))
    r.socket("socket_head", "top", (float(TOPC[0]), 1.24, 0.0))
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
    (0.225, 0.462, 0.292, 0.264, 0.0, (0.0, 0.0), 11),
    (0.480, 0.672, 0.252, 0.230, 22.5, (0.0, 0.0), 12),
    (0.690, 0.852, 0.224, 0.202, -10.0, (-0.015, 0.015), 13),
    (0.870, 0.992, 0.196, 0.174, 30.0, (0.012, -0.015), 14),
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
        (28, 0.27, 0.46, 0.066, 12, 0), (100, 0.30, 0.40, 0.060, 15, 0), (172, 0.28, 0.50, 0.070, 11, 0),
        (240, 0.50, 0.40, 0.060, 14, 1), (310, 0.46, 0.46, 0.066, 12, 1), (350, 0.70, 0.24, 0.050, 16, 2), (200, 0.72, 0.22, 0.046, 18, 2),
    ]
    sp = []
    for a, by, ln, r, tl, ci in spec:
        base = surf(ci, by, a, -0.02)
        ar = math.radians(a)
        d = unit((math.sin(math.radians(tl)) * math.sin(ar), math.cos(math.radians(tl)), math.sin(math.radians(tl)) * math.cos(ar)))
        sp.append((lp(base), d, ln, r))
    mono = spikes(sp, seed=10, flat=0.42, sides=6, tip=0.26, bend=0.03, jitter=0.10)
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
    for j, a in enumerate((36, 108, 180, 252, 324)):
        ar = math.radians(a)
        base = (0.31 * math.sin(ar), 0.24, 0.31 * math.cos(ar))
        up = (0.55 * math.sin(ar), 1.0, 0.55 * math.cos(ar))
        cl.append(cluster(base, up, 3, (0.12, 0.24), (0.024, 0.036), spread=0.04, tilt=24, seed=40 + j, flat=0.25))
    p.add("buttress_shards", lean(merge(cl)), "RH_Ice", "body")


# ======================================================================================= collars, wire, runes
def build_bands(p: Piece):
    # silver-lashed obsidian collars in the seams between courses; a dim ring of seam light inside each seam
    seams = [(0.471, 0.272), (0.681, 0.240), (0.861, 0.212)]
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
    p.add("runes", lean(merge(runes)), "RH_Seam", "runes", bake=False, lod1=None)


_RINGS_ROT = [c[4] for c in COURSES]


# ======================================================================================= crown: flared collar + five ice merlons
R_PAR = 0.334                                    # parapet / merlon outer radius (0.67 wide)
MER_A = [36.0 + 72.0 * k for k in range(5)]      # merlon centres (a crenel is centred on the front)
CRE_A = [72.0 * k for k in range(5)]
MER_TOP = [1.18, 1.20, 1.16, 1.19, 1.17]
MER_BASE = 1.040
MER_SWEEP = 38.0


def sector_solid(loop, sweep_deg, segs, crease=50.0):
    """Closed ring-sector solid centred on +Z: `loop` = (r, y) outline counter-clockwise (outer wall bottom->top, then back in),
    revolved over `sweep_deg`, flat end caps."""
    loop = np.asarray(loop, dtype=np.float64)
    prof = np.vstack([loop, loop[:1]])
    body = g.lathe(prof, segs, sweep=sweep_deg, start=-sweep_deg / 2, crease=crease)
    parts = [body]
    tris = g.triangulate_polygon(loop)
    for sgn in (-1, 1):
        th = math.radians(sgn * sweep_deg / 2)
        P = np.column_stack([loop[:, 0] * math.sin(th), loop[:, 1], loop[:, 0] * math.cos(th)])
        F = np.asarray(tris)
        n = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]]).sum(axis=0)
        tang = np.array([math.cos(th), 0.0, -math.sin(th)]) * sgn
        if np.dot(n, tang) < 0:
            F = F[:, ::-1]
        parts.append(g.Mesh(P, F, np.column_stack([loop[:, 0], loop[:, 1]]) / 0.25))
    return merge(parts).shade(crease)


def _chip(m, top, sgn, depth=0.034):
    """hand-cut diagonal chip off one top corner (acts on vertices within 4 cm of the top)."""
    def fn(P):
        P = P.copy()
        r = np.hypot(P[:, 0], P[:, 2])
        xn = P[:, 0] / (0.30 * math.sin(math.radians(MER_SWEEP / 2)))
        rn = (r - 0.26) / (R_PAR - 0.26)
        d = depth * smoothstep(0.35, 1.15, sgn * xn + (rn - 0.5) * 0.9) * smoothstep(top - 0.045, top - 0.004, P[:, 1])
        P[:, 1] -= d
        return P
    return g.warp(m, fn)


def merlons():
    ro, ri, y0 = R_PAR, 0.262, MER_BASE
    rng = np.random.default_rng(21)
    stones, caps = [], []
    for k, (a, top) in enumerate(zip(MER_A, MER_TOP)):
        loop = [(ro, y0), (ro - 0.004, top - 0.03), (ro - 0.012, top), (ri + 0.012, top), (ri + 0.002, top - 0.03), (ri, y0)]
        st = sector_solid(loop, MER_SWEEP, 6)
        cl = [(ro + 0.006, top - 0.004), (ro + 0.006, top + 0.010), (ro - 0.003, top + 0.016), (ri + 0.003, top + 0.016), (ri - 0.003, top + 0.010), (ri - 0.003, top - 0.004)]
        cp = sector_solid(cl, MER_SWEEP + 3.0, 6, crease=40)
        sgn = 1 if k % 2 == 0 else -1
        st, cp = _chip(st, top, sgn), _chip(cp, top, sgn)
        yaw = float(rng.uniform(-6, 6))
        for lst, mm in ((stones, st), (caps, cp)):
            mm = mm.rotated(4.0, 0, 0, pivot=(0, y0, 0.30)).rotated(0, yaw + a, 0)
            lst.append(mm)
    stones = merge(stones).noised(0.0016, 30, 2, seed=8)
    return stones.translated(TOPC[0], 0, 0), merge(caps).translated(TOPC[0], 0, 0)


def crown_collar():
    prof = [(0.0, 0.960), (0.150, 0.960), (0.230, 0.985), (0.300, 1.005), (0.334, 1.030), (0.334, 1.045), (0.290, 1.048), (0.150, 1.045), (0.0, 1.045)]
    m = g.lathe(np.array(prof), 20, crease=40).noised(0.0022, 24, 2, seed=6)
    return m.translated(TOPC[0], 0, 0)


def crown_icicles():
    specs = []
    for a in MER_A:
        ar = math.radians(a)
        specs.append((np.array([TOPC[0] + 0.316 * math.sin(ar), 1.020, 0.316 * math.cos(ar)]), unit((0.18 * math.sin(ar), -1.0, 0.18 * math.cos(ar))), 0.070, 0.016))
    return spikes(specs, seed=60, flat=0.15, sides=4, tip=0.5, bend=0.01)


def crenel_glow():
    out = []
    for a in CRE_A:
        m = g.lathe(np.array([(0.325, 1.0485), (0.262, 1.0485)]), 6, sweep=26.0, start=-13.0, crease=60)
        out.append(m.rotated(0, a, 0))
    return merge(out).translated(TOPC[0], 0, 0)


def build_crown(p: Piece):
    p.add("crown_collar", crown_collar(), "RH_Obsidian", "top")
    st, cp = merlons()
    p.add("merlons", st, "RH_Frost", "top", uv_scale=2, tint=lambda P: np.full(len(P), 0.72))
    p.add("merlon_caps", cp, "RH_Frost", "top", tint=lambda P: np.full(len(P), 0.9))
    p.add("crown_icicles", crown_icicles(), "RH_Ice", "top", lod1=None)
    p.add("crown_band", g.torus(R_PAR + 0.003, 0.0065, 40, 5).translated(TOPC[0], 1.034, 0), "RH_Silver", "top")
    p.add("crenel_glow", crenel_glow(), "RH_Seam", "top", lod1="keep", bake=False)
    for k in range(SHARD_N):
        m, _ = _shard_geom(k)
        p.add(f"crown_shard_{k}", m, "RH_Ice", f"shard_{k}")
    orb = g.superellipsoid((0.050, 0.050, 0.050), 0.9, 0.9, 6, 12).translated(*ORB_C)
    p.add("crown_orb", orb, "RH_Glow", "orb", bake=False, lod1="keep")


# ======================================================================================= clips
# The bastion is rigid masonry: it never bends, it SQUASHES / STRETCHES (volume-preserving scale on `body`, pivot on the plinth top),
# LEANS (rocking about the base edge it tips onto, so it never sinks through the plinth) and HOPS.  The crown (`top`: collar + merlons)
# is rigid, lags a few frames behind and never deforms.  Five loose crown shards (`shard_0..4`) hover around the glow `orb`; they fire
# in the Attack and fall out of the crenels onto the plinth in the Surrender (world-space paths converted to bone-local keys).
# `runes` scales radially a hair so the raised glyphs sink into / pop out of the obsidian (pulse); `orb` scales (glow pulse / dim).
from anim.curves import Curve, spring_follow      # noqa: E402
from geom import rot_matrix, rot_between, axis_angle   # noqa: E402
from anim import xf                               # noqa: E402

IMPACT = 0.75
R_BASE = 0.30                     # base radius the tower rocks on
VOL = 0.85
PLINTH_Y, PLINTH_R = 0.22, 0.352
SHARDS = [f"shard_{k}" for k in range(SHARD_N)]
_V = {}                           # shard bone -> vertices relative to its pivot (filled by build_crown)


def smooth(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


class Rec:
    """Dense clip recorder: every channel is an (n,3) array on the frame grid."""

    def __init__(self, name, T, fps=30, loop=False):
        self.name, self.T, self.fps, self.loop = name, float(T), fps, loop
        self.n = int(round(T * fps)) + 1
        self.t = np.linspace(0.0, T, self.n)
        self.ch = {}
        self.extras = {}
        self.over = {}                              # shard bone -> (pos(n,3), quat(n,4))

    def s(self, keys, loop=None):
        c = Curve(keys, loop=loop)
        return np.array([np.atleast_1d(c(t)) for t in self.t])

    def sc(self, keys, loop=None):
        return self.s(keys, loop)[:, 0]

    def z3(self):
        return np.zeros((self.n, 3))

    def sine(self, f, amp, ph=0.0):
        return amp * np.sin(TAU * f * self.t + ph)

    def add(self, bone, path, arr):
        arr = np.asarray(arr, dtype=np.float64)
        if arr.ndim == 1:
            arr = np.column_stack([arr, np.zeros(self.n), np.zeros(self.n)])
        self.ch[(bone, path)] = self.ch.get((bone, path), 0.0) + arr

    def squash(self, bone, sy, sx=None):
        sy = np.asarray(sy, dtype=np.float64) * np.ones(self.n)
        sxz = sy ** (-0.5 * VOL) if sx is None else np.asarray(sx) * np.ones(self.n)
        self.ch[(bone, "scale")] = np.column_stack([sxz, sy, sxz])

    def uni(self, bone, s):
        s = np.asarray(s, dtype=np.float64) * np.ones(self.n)
        self.ch[(bone, "scale")] = np.column_stack([s, s, s])

    def follow(self, x, freq, zeta):
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
            if path in ("rot", "pos") and bone in self.over:
                continue
            for t, v in zip(self.t, arr):
                c.key(bone, path, float(t), v, "linear")
        for bone, (pos, quat) in self.over.items():
            c.set_dense(bone, "pos", self.t, pos)
            c.set_dense(bone, "rot", self.t, quat)
        c.extras.update(self.extras)
        return c


def rock_pos(rot):
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
    r.add("body", "rot", rot)
    r.add("body", "pos", np.asarray(pos) + rock * rock_pos(rot))
    r.squash("body", sy)


def crown(r, rot, gain=1.0, freq=3.0, zeta=0.3):
    """the rigid crown lags the tower's lean (overlap) -> `top` rot is the difference."""
    lag = r.follow(rot, freq, zeta)
    r.add("top", "rot", gain * (lag - rot))
    return lag


def pulse_runes(r, p, lo=0.978, hi=1.018):
    s = lo + (hi - lo) * np.asarray(p) * np.ones(r.n)
    r.ch[("runes", "scale")] = np.column_stack([s, np.ones(r.n), s])


def shards(r, rot, ybody, flare=0.0, lift=0.0, scl=1.0, jig=1.0, bob=0.0, freq=None, extra_rot=None):
    """Author the five hovering shards: flare (deg outward tilt), lift (m), scale, plus lag-jiggle from the tower motion and an optional idle bob."""
    flare = np.asarray(flare, dtype=np.float64) * np.ones(r.n)
    lift = np.asarray(lift, dtype=np.float64) * np.ones(r.n)
    scl = np.asarray(scl, dtype=np.float64) * np.ones(r.n)
    for k, bone in enumerate(SHARDS):
        az = math.radians(SHARD_AZ[k])
        lagr = r.follow(rot, 3.2 + 0.4 * k, 0.22)
        lagy = r.follow(np.asarray(ybody), 3.6 + 0.3 * k, 0.25)[:, 0]
        jr = jig * 0.6 * (lagr - rot)
        rx = flare * math.cos(az) + jr[:, 0]
        rz = -flare * math.sin(az) + jr[:, 2]
        py = lift + jig * 0.8 * (lagy - np.asarray(ybody)) + 0.0
        if bob:
            f = freq or 1.0 / r.T
            ph = 1.3 * k
            py = py + bob * np.sin(TAU * f * r.t + ph)
            rx = rx + 2.2 * np.sin(TAU * f * r.t + ph + 0.8)
            rz = rz + 2.2 * np.sin(TAU * f * r.t + ph + 2.1)
        e = np.column_stack([rx, np.zeros(r.n), rz])
        if extra_rot is not None:
            e = e + extra_rot[k]
        r.add(bone, "rot", e)
        r.add(bone, "pos", np.column_stack([np.zeros(r.n), py, np.zeros(r.n)]))
        r.uni(bone, scl)


# ---- world-space chain (for shard paths) -------------------------------------------------------------------------------------
def _local_M(rig, r, bone, i):
    loc = rig.local(bone).copy()
    if (bone, "pos") in r.ch:
        loc = loc + r.ch[(bone, "pos")][i]
    R = rot_matrix(*r.ch[(bone, "rot")][i]) if (bone, "rot") in r.ch else np.eye(3)
    S = r.ch[(bone, "scale")][i] if (bone, "scale") in r.ch else np.ones(3)
    M = np.eye(4)
    M[:3, :3] = R * S[None, :]
    M[:3, 3] = loc
    return M


def top_world(rig, r):
    """per-frame world matrices of the shard parent (`top`), through root > body > top."""
    return [_local_M(rig, r, "body", i) @ _local_M(rig, r, "top", i) for i in range(r.n)]


def _polar(M3):
    U, _, Vt = np.linalg.svd(M3)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    return R


def finalize_shards(r, rig, drives):
    """Convert every shard's authored channels to dense pos/quat; `drives[k] = (i0, i1, P(n,3), R(n,3,3))` overrides frames i0..i1 with a
    WORLD pose (expressed back in the `top` frame).  Call after body/top channels are final."""
    Wt = top_world(rig, r)
    for k, bone in enumerate(SHARDS):
        pos = r.ch[(bone, "pos")].copy()
        quat = np.array([xf.quat_from_mat(rot_matrix(*e)) for e in r.ch[(bone, "rot")]])
        if k in drives:
            i0, i1, P, R = drives[k]
            rest = rig.local(bone)
            for i in range(i0, i1 + 1):
                W = np.eye(4)
                W[:3, :3], W[:3, 3] = R[i], P[i]
                L = np.linalg.inv(Wt[i]) @ W
                quat[i] = xf.quat_from_mat(_polar(L[:3, :3]))
                pos[i] = L[:3, 3] - rest
        for i in range(1, r.n):
            if np.dot(quat[i], quat[i - 1]) < 0:
                quat[i] = -quat[i]
        r.over[bone] = (pos, quat)


def authored_world(rig, r, Wt, k, i):
    """world pose of shard k at frame i from its authored channels (before any override)."""
    bone = SHARDS[k]
    L = np.eye(4)
    L[:3, :3] = rot_matrix(*r.ch[(bone, "rot")][i])
    L[:3, 3] = rig.local(bone) + r.ch[(bone, "pos")][i]
    W = Wt[i] @ L
    return W[:3, 3].copy(), _polar(W[:3, :3])


def bezier(p0, p1, p2, p3, u):
    v = 1 - u
    return v ** 3 * p0 + 3 * v * v * u * p1 + 3 * v * u * u * p2 + u ** 3 * p3


def dbezier(p0, p1, p2, p3, u):
    v = 1 - u
    return 3 * v * v * (p1 - p0) + 6 * v * u * (p2 - p1) + 3 * u * u * (p3 - p2)


# ---------------------------------------------------------------------------------------------- Idle
def clip_idle(rig):
    T = 3.0
    r = Rec("Idle", T, 30, loop=True)
    w = 1.0 / T
    sy = 1.0 + r.sine(w, 0.007, -math.pi / 2 + 0.4)
    rot = np.column_stack([r.sine(w, 0.35, 0.7), np.zeros(r.n), r.sine(w, 0.30, 2.4) + r.sine(3 * w, 0.10, 1.0)])   # slow sway + a small creak
    body_channels(r, rot, r.z3(), sy)
    crown(r, rot)
    p = (0.5 + 0.5 * np.sin(TAU * 2 * w * r.t - math.pi / 2)) ** 2           # two cold pulses per loop
    pulse_runes(r, p)
    r.uni("orb", 1.0 + 0.16 * p)
    shards(r, rot, r.z3()[:, 1], bob=0.004, jig=1.0)
    finalize_shards(r, rig, {})
    return r.emit()


# ---------------------------------------------------------------------------------------------- Move
def clip_move(rig):
    T = 0.7
    r = Rec("Move", T, 60, loop=True)
    sy = r.sc([(0, 1.0), (0.12, 0.87, "in_out_cubic"), (0.22, 1.09, "out_cubic"), (0.32, 1.04, "in_out_quad"), (0.47, 1.07, "in_quad"),
               (0.505, 0.85, "out_quad"), (0.60, 1.045, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    y = r.sc([(0, 0.0), (0.12, 0.0), (0.22, 0.030, "out_cubic"), (0.33, 0.062, "out_quad"), (0.505, 0.0, "in_quad"), (T, 0.0)])
    z = r.sc([(0, -0.004), (0.12, -0.012, "in_out_cubic"), (0.33, 0.014, "out_cubic"), (0.505, 0.018, "in_quad"), (T, -0.004, "in_out_cubic")])
    rx = r.sc([(0, 0.0), (0.12, -3.0, "in_out_cubic"), (0.30, 4.5, "out_cubic"), (0.47, 3.0, "in_out_cubic"), (0.505, -1.6, "out_quad"), (0.60, 1.2, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    rz = r.sc([(0, 0.0), (0.22, 1.2, "in_out_cubic"), (0.47, -0.8, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), y, z]), sy)
    crown(r, rot, 1.0, 3.4, 0.28)
    p = r.sc([(0, 0.0), (0.40, 0.1, "in_out_cubic"), (0.505, 1.0, "out_cubic"), (0.62, 0.2, "in_out_cubic"), (T, 0.0, "in_out_cubic")])   # flash on landing
    pulse_runes(r, p)
    r.uni("orb", 1.0 + 0.3 * p)
    shards(r, rot, y, flare=r.sc([(0, 0.0), (0.30, 3.0, "in_out_cubic"), (0.505, 9.0, "out_quad"), (0.62, 0.0, "in_out_cubic"), (T, 0.0)]), jig=1.4)
    finalize_shards(r, rig, {})
    r.extras["footContacts"] = {"body": [[0.495, 0.60]]}
    return r.emit()


# ---------------------------------------------------------------------------------------------- Attack
def clip_attack(rig):
    T, I = 1.8, IMPACT
    r = Rec("Attack", T, 60)
    # coil -> rise and rear back (hang) -> TOPPLE (accelerating) -> slam squash on the impact frame -> hold -> rise with one overshoot
    sy = r.sc([(0, 1.0), (0.22, 0.92, "in_out_cubic"), (0.50, 1.07, "in_out_cubic"), (0.58, 1.08, "in_out_cubic"), (0.68, 1.04, "in_cubic"), (I, 0.88, "in_cubic"),
               (0.84, 0.84, "out_quad"), (0.96, 0.86, "in_out_cubic"), (1.28, 1.045, "in_out_cubic"), (1.50, 0.985, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    rx = r.sc([(0, 0.0), (0.22, -3.5, "in_out_cubic"), (0.50, -8.0, "in_out_cubic"), (0.58, -11.0, "in_out_cubic"), (I, 46.0, "in_cubic"),
               (0.84, 44.0, "out_quad"), (0.96, 45.0, "in_out_cubic"), (1.30, -4.0, "in_out_cubic"), (1.50, 1.5, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    rz = r.sc([(0, 0.0), (0.40, 0.8, "in_out_cubic"), (0.58, -1.0, "in_out_cubic"), (I, 0.0, "in_cubic"), (1.1, 0.6, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    z = r.sc([(0, 0.0), (0.22, -0.02, "in_out_cubic"), (0.58, -0.07, "in_out_cubic"), (I, 0.18, "in_cubic"), (0.96, 0.17, "out_quad"), (1.45, -0.004, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    y = r.sc([(0, 0.0), (0.22, 0.0), (0.50, 0.03, "in_out_cubic"), (0.58, 0.045, "in_out_cubic"), (I, -0.01, "in_cubic"), (0.90, -0.008, "out_quad"), (T, 0.0, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), y, z]), sy)
    # crown: nods back with the rear-up, leads the strike (+12), rattles after the blow, then lags on the rise
    trx = r.sc([(0, 0.0), (0.22, -2.0, "in_out_cubic"), (0.58, -6.0, "in_out_cubic"), (I, 12.0, "in_cubic"), (0.98, 0.0, ("spring", 0.35, 2.0)),
                (1.30, -4.0, "in_out_cubic"), (1.50, 1.0, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    r.add("top", "rot", np.column_stack([trx, np.zeros(r.n), np.zeros(r.n)]))
    tsy = r.sc([(0, 1.0), (0.58, 1.02, "in_out_cubic"), (I, 0.97, "in_cubic"), (0.9, 1.0, "in_out_cubic"), (T, 1.0)])
    r.squash("top", tsy, sx=1.0 + (tsy - 1.0) * -0.3)
    # runes + orb: charge on the coil, white-hot on the blow, die back
    p = r.sc([(0, 0.0), (0.30, 0.7, "in_out_cubic"), (0.50, 1.0, "in_out_cubic"), (I, 1.0), (1.0, 0.3, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    pulse_runes(r, p)
    r.uni("orb", r.sc([(0, 1.0), (0.30, 1.35, "in_out_cubic"), (0.50, 1.55, "in_out_cubic"), (0.56, 0.5, "in_expo"), (0.9, 0.5), (1.30, 1.2, "out_back"), (T, 1.0, "in_out_cubic")]))
    # shards: lift and flare on the charge, FIRE from the crown over the merlons at 0.50, strike the target ~impact, vanish, re-form late
    flare = r.sc([(0, 0.0), (0.30, 18.0, "in_out_cubic"), (0.50, 28.0, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    lift = r.sc([(0, 0.0), (0.30, 0.020, "in_out_cubic"), (0.50, 0.040, "in_out_cubic"), (1.05, 0.0), (T, 0.0)])
    scl = np.zeros((5, r.n))
    for k in range(SHARD_N):
        t_hit = I - 0.018 + 0.006 * k
        scl[k] = r.sc([(0, 1.0), (0.30, 1.15, "in_out_cubic"), (0.50, 1.30, "in_out_cubic"), (t_hit, 1.0, "in_cubic"), (t_hit + 0.014, 0.0, "in_expo"),
                       (1.10 + 0.03 * k, 0.0), (1.36 + 0.03 * k, 1.0, "out_back"), (T, 1.0)])
    shards(r, rot, y, flare=flare, lift=lift, jig=1.0)
    for k, bone in enumerate(SHARDS):
        r.uni(bone, scl[k])                          # per-shard scale (fire / vanish / re-form staggered)
    # world-driven flight windows
    Wt = top_world(rig, r)
    drives = {}
    for k in range(SHARD_N):
        i0 = int(round((0.50 + 0.012 * k) * r.fps))
        i1 = int(round((I - 0.014 + 0.006 * k) * r.fps))
        P0, R0 = authored_world(rig, r, Wt, k, i0)
        tgt = np.array([(k - 2) * 0.065, 0.55 + 0.02 * ((k * 3) % 5), 1.02])
        c1 = P0 + np.array([0.0, 0.20, 0.05])
        c2 = tgt + np.array([0.0, 0.30, -0.50])
        P = np.zeros((r.n, 3))
        R = np.tile(np.eye(3), (r.n, 1, 1))
        t0, t1 = r.t[i0], r.t[i1]
        q0 = xf.quat_from_mat(R0)
        for i in range(i0, i1 + 1):
            u = ((r.t[i] - t0) / (t1 - t0)) ** 1.5
            P[i] = bezier(P0, c1, c2, tgt, u)
            tan = dbezier(P0, c1, c2, tgt, max(u, 0.02))
            Ra = rot_between(np.array([0.0, 1.0, 0.0]), tan / np.linalg.norm(tan))
            wq = float(smooth((r.t[i] - t0) / 0.07))
            R[i] = xf.mat_from_quat(xf.slerp(q0, xf.quat_from_mat(Ra), wq))
        drives[k] = (i0, i1, P, R)
    finalize_shards(r, rig, drives)
    r.extras["shardStrike"] = {"impact": I}
    return r.emit()


# ---------------------------------------------------------------------------------------------- HitReact
def clip_hit(rig):
    T = 0.5
    r = Rec("HitReact", T, 60)
    rx = r.sc([(0, 0.0), (0.06, -8.0, "out_cubic"), (T, 0.0, ("spring", 0.42, 2.5))])
    rz = r.sc([(0, 0.0), (0.06, 3.0, "out_cubic"), (T, 0.0, ("spring", 0.5, 3.0))])
    z = r.sc([(0, 0.0), (0.06, -0.06, "out_cubic"), (T, 0.0, ("spring", 0.35, 2.0))])
    sy = r.sc([(0, 1.0), (0.06, 0.90, "out_cubic"), (0.18, 1.05, "in_out_cubic"), (0.32, 0.985, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), np.zeros(r.n), z]), sy)
    crown(r, rot, 1.0, 3.2, 0.3)
    p = r.sc([(0, 0.0), (0.06, 1.0, "out_cubic"), (0.30, 0.0, "in_out_cubic"), (T, 0.0)])
    pulse_runes(r, p)
    r.uni("orb", 1.0 + 0.5 * p)
    shards(r, rot, r.z3()[:, 1], flare=r.sc([(0, 0.0), (0.08, 16.0, "out_cubic"), (T, 0.0, ("spring", 0.4, 2.0))]), jig=2.0)
    finalize_shards(r, rig, {})
    return r.emit()


# ---------------------------------------------------------------------------------------------- Victory
def clip_victory(rig):
    T = 1.6
    r = Rec("Victory", T, 30)
    sy = r.sc([(0, 1.0), (0.22, 0.92, "in_out_cubic"), (0.42, 1.09, "out_cubic"), (0.58, 0.97, "in_out_cubic"), (0.80, 1.025, "in_out_cubic"), (T, 1.015, "in_out_cubic")])
    y = r.sc([(0, 0.0), (0.22, 0.0), (0.40, 0.05, "out_cubic"), (0.56, 0.0, "in_quad"), (T, 0.0)])
    rx = r.sc([(0, 0.0), (0.22, 3.0, "in_out_cubic"), (0.45, -5.0, "out_cubic"), (0.64, -2.0, "in_out_cubic"), (T, -3.0, "in_out_cubic")])
    rz = r.sc([(0, 0.0), (0.45, 0.6, "in_out_cubic"), (1.0, -0.8, "in_out_cubic"), (T, 0.3, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), y, np.zeros(r.n)]), sy)
    crown(r, rot, 1.0, 3.0, 0.3)
    ry = r.sc([(0, 0.0), (0.5, 0.0), (1.1, 14.0, "in_out_cubic"), (T, 14.0, "in_out_cubic")])      # the crown slowly turns on its seat
    r.add("top", "rot", np.column_stack([np.zeros(r.n), ry, np.zeros(r.n)]))
    p = r.sc([(0, 0.0), (0.22, 0.2, "in_out_cubic"), (0.45, 1.0, "out_cubic"), (T, 0.9, "in_out_cubic")])
    pulse_runes(r, p)
    r.uni("orb", r.sc([(0, 1.0), (0.22, 0.9, "in_out_cubic"), (0.45, 1.7, "out_cubic"), (0.8, 1.45, "in_out_cubic"), (T, 1.5, "in_out_cubic")]))
    shards(r, rot, y, flare=r.sc([(0, 0.0), (0.22, -4.0, "in_out_cubic"), (0.45, 30.0, "out_back"), (T, 24.0, "in_out_cubic")]),
           lift=r.sc([(0, 0.0), (0.22, -0.01, "in_out_cubic"), (0.45, 0.045, "out_cubic"), (T, 0.035, "in_out_cubic")]),
           scl=r.sc([(0, 1.0), (0.22, 0.95, "in_out_cubic"), (0.45, 1.40, "out_cubic"), (T, 1.30, "in_out_cubic")]), jig=1.0)
    finalize_shards(r, rig, {})
    return r.emit()


# ---------------------------------------------------------------------------------------------- Taunt
def clip_taunt(rig):
    T = 1.4
    r = Rec("Taunt", T, 60)
    sy = r.sc([(0, 1.0), (0.28, 0.90, "in_out_cubic"), (0.36, 1.09, "out_cubic"), (0.46, 0.98, "in_out_cubic"), (0.62, 0.955, "in_out_cubic"),
               (0.72, 1.07, "out_cubic"), (0.86, 0.985, "in_out_cubic"), (1.05, 1.02, "in_out_cubic"), (T, 1.0, "in_out_cubic")])
    rx = r.sc([(0, 0.0), (0.28, -6.0, "in_out_cubic"), (0.36, 9.0, "out_quad"), (0.50, 2.0, "in_out_cubic"), (0.62, -4.0, "in_out_cubic"),
               (0.72, 9.0, "out_quad"), (0.95, 0.5, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    z = r.sc([(0, 0.0), (0.28, -0.03, "in_out_cubic"), (0.36, 0.07, "out_quad"), (0.50, 0.02, "in_out_cubic"), (0.62, -0.02, "in_out_cubic"),
              (0.72, 0.07, "out_quad"), (1.0, 0.004, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), np.zeros(r.n)])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), np.zeros(r.n), z]), sy)
    crown(r, rot, 1.0, 3.0, 0.3)
    p = r.sc([(0, 0.0), (0.28, 0.1, "in_out_cubic"), (0.36, 1.0, "out_cubic"), (0.52, 0.5, "in_out_cubic"), (0.62, 0.1, "in_cubic"), (0.72, 1.0, "out_cubic"), (1.05, 0.3, "in_out_cubic"), (T, 0.0, "in_out_cubic")])
    pulse_runes(r, p)
    r.uni("orb", 1.0 + 1.0 * p)
    # the shards flare outward and snap back, twice
    shards(r, rot, r.z3()[:, 1],
           flare=r.sc([(0, 0.0), (0.28, -4.0, "in_out_cubic"), (0.36, 40.0, "out_cubic"), (0.52, 36.0, "in_out_cubic"), (0.62, -8.0, "in_cubic"), (0.72, 40.0, "out_cubic"),
                       (0.90, -2.0, "in_cubic"), (T, 0.0, ("spring", 0.3, 2.0))]),
           lift=r.sc([(0, 0.0), (0.28, -0.012, "in_out_cubic"), (0.36, 0.05, "out_cubic"), (0.52, 0.04, "in_out_cubic"), (0.62, -0.01, "in_cubic"), (0.72, 0.05, "out_cubic"), (0.9, 0.0, "in_cubic"), (T, 0.0)]),
           scl=r.sc([(0, 1.0), (0.28, 0.92, "in_out_cubic"), (0.36, 1.38, "out_cubic"), (0.52, 1.3, "in_out_cubic"), (0.62, 0.9, "in_cubic"), (0.72, 1.38, "out_cubic"), (0.9, 0.95, "in_cubic"), (T, 1.0, ("spring", 0.3, 2.0))]),
           jig=1.0)
    finalize_shards(r, rig, {})
    return r.emit()


# ---------------------------------------------------------------------------------------------- Surrender
EDGE_R = 0.375


def ground(X, Z):
    return np.where(np.hypot(X, Z) < PLINTH_R, PLINTH_Y, 0.19)


def rest_lift(W, cx, cz):
    return float(np.max(ground(W[:, 0] + cx, W[:, 2] + cz) - W[:, 1]))


def clip_surrender(rig):
    T, fps = 2.0, 60
    r = Rec("Surrender", T, fps)
    sy = r.sc([(0, 1.0), (0.28, 0.95, "out_cubic"), (0.55, 0.97, "in_out_cubic"), (1.25, 0.90, "in_out_cubic"), (T, 0.885, "in_out_cubic")])
    rx = r.sc([(0, 0.0), (0.28, -4.0, "out_cubic"), (0.55, -1.0, "in_out_cubic"), (1.30, 9.0, "in_out_cubic"), (T, 10.0, "in_out_cubic")])
    rz = r.sc([(0, 0.0), (0.30, -1.5, "out_cubic"), (0.60, -0.4, "in_out_cubic"), (1.30, 3.5, "in_out_cubic"), (T, 4.2, "in_out_cubic")])
    z = r.sc([(0, 0.0), (0.28, -0.03, "out_cubic"), (0.55, -0.01, "in_out_cubic"), (1.30, 0.03, "in_out_cubic"), (T, 0.03, "in_out_cubic")])
    rot = np.column_stack([rx, np.zeros(r.n), rz])
    body_channels(r, rot, np.column_stack([np.zeros(r.n), np.zeros(r.n), z]), sy)
    # the merlon ring slumps forward and to one side, lagging the tower
    lag = r.follow(rot, 3.0, 0.3)
    trx = r.sc([(0, 0.0), (0.30, 1.0, "out_cubic"), (1.30, 6.0, "in_out_cubic"), (T, 6.5, "in_out_cubic")])
    trz = r.sc([(0, 0.0), (0.30, 2.5, "out_cubic"), (1.30, 4.0, "in_out_cubic"), (T, 4.5, "in_out_cubic")])
    r.add("top", "rot", 1.0 * (lag - rot) + np.column_stack([trx, np.zeros(r.n), trz]))
    tsy = r.sc([(0, 1.0), (1.3, 0.97, "in_out_cubic"), (T, 0.96, "in_out_cubic")])
    r.squash("top", tsy, sx=1.0 + (tsy - 1.0) * -0.3)
    # the light dies: orb shrinks, runes sink flush into the obsidian
    r.uni("orb", r.sc([(0, 1.0), (0.28, 0.85, "out_cubic"), (0.55, 1.0, "in_out_cubic"), (1.30, 0.22, "in_out_cubic"), (T, 0.16, "in_out_cubic")]))
    pulse_runes(r, r.sc([(0, 0.5), (0.4, 0.55, "in_out_cubic"), (1.3, 0.0, "in_out_cubic"), (T, 0.0)]))
    # shards: droop on the stagger, then slip out of the crenels and fall to the plinth
    shards(r, rot, r.z3()[:, 1], flare=r.sc([(0, 0.0), (0.28, 8.0, "out_cubic"), (T, 8.0)]),
           lift=r.sc([(0, 0.0), (0.28, 0.012, "out_cubic"), (T, 0.012)]), jig=1.0)
    Wt = top_world(rig, r)
    drives = {}
    contacts = []
    Y = np.array([0.0, 1.0, 0.0])
    for k in range(SHARD_N):
        bone = SHARDS[k]
        V = _V[bone]
        Vs = V[::3]
        t0 = 0.32 + 0.045 * k
        i0 = int(round(t0 * fps))
        P0, R0 = authored_world(rig, r, Wt, k, i0)
        az = math.radians(SHARD_AZ[k] + 36.0 if True else 0.0)            # exit through the crenel next to the shard
        radial = np.array([math.sin(az), 0.0, math.cos(az)])
        heading = np.array([math.cos(az), 0.0, -math.sin(az)])
        Rf = axis_angle(heading, 25.0 + 47.0 * k) @ rot_between(Y, heading)
        r_land, r_exit = 0.335, 0.45
        cxz_f = r_land * np.array([radial[0], radial[2]])
        yf = rest_lift(Vs @ Rf.T, cxz_f[0], cxz_f[1])
        X = np.array([r_exit * radial[0], 1.20 + 0.012 * k, r_exit * radial[2]])
        dA = 0.26
        launch_d = np.array([0.77 * radial[0], 0.64, 0.77 * radial[2]])
        RA = rot_between(Y, launch_d / np.linalg.norm(launch_d))
        q0, qA, qf = xf.quat_from_mat(R0), xf.quat_from_mat(RA), xf.quat_from_mat(Rf)
        G, E = 6.5, 0.34
        vy0 = 0.25
        tf = (vy0 + math.sqrt(vy0 ** 2 + 2 * G * (X[1] - yf))) / G
        v_imp = G * tf - vy0
        arcs, tc = [], dA + tf
        impacts = [tc]
        for b in range(3):
            vb = v_imp * E ** (b + 1)
            arcs.append((impacts[-1], impacts[-1] + 2 * vb / G, vb))
            impacts.append(impacts[-1] + 2 * vb / G)
        contacts.append(round(t0 + impacts[0], 3))
        P = np.zeros((r.n, 3))
        R = np.tile(np.eye(3), (r.n, 1, 1))
        for i in range(i0, r.n):
            tau = r.t[i] - t0
            if tau < dA:
                u = tau / dA
                e = 1 - (1 - u) ** 2
                pos = P0 + (X - P0) * e + np.array([0.0, 0.08 * math.sin(math.pi * u), 0.0])
                q = xf.slerp(q0, qA, float(smooth(u * 1.3)))
            else:
                s = tau - dA
                if s < tf:
                    uu = s / tf
                    y = X[1] + vy0 * s - 0.5 * G * s * s
                    rr = r_exit + (r_land - r_exit) * uu ** 2.5
                    q = xf.slerp(qA, qf, float(smooth(uu ** 0.8)))
                    wob = 0.0
                else:
                    y, rr, q, wob = yf, r_land, qf, 0.0
                    for j, (ta, tb, vb) in enumerate(arcs):
                        if dA + ta - dA <= tau < tb:
                            tt = tau - ta
                            y = yf + vb * tt - 0.5 * G * tt * tt
                            break
                    last = max([ti for ti in impacts if ti <= tau], default=None)
                    if last is not None and last > 0:
                        sa = tau - last
                        wob = 5.0 * (E ** impacts.index(last)) * math.exp(-sa / 0.25) * math.sin(TAU * sa / 0.30)
                pos = np.array([rr * radial[0], y, rr * radial[2]])
                if tau >= dA + tf:
                    pos = np.array([rr * radial[0], y, rr * radial[2]])
            Rm = xf.mat_from_quat(q)
            if tau >= dA + tf and wob:
                Rm = axis_angle(heading, wob) @ Rm
            P[i], R[i] = pos, Rm
        drives[k] = (i0, r.n - 1, P, R)
    finalize_shards(r, rig, drives)
    c = r.emit()
    c.extras["shardRest"] = {"azimuths": [round(float((a + 36.0) % 360), 1) for a in SHARD_AZ], "dist": 0.335, "contacts": contacts}
    return c


def make_clips(rig):
    return [clip_idle(rig), clip_move(rig), clip_attack(rig), clip_hit(rig), clip_victory(rig), clip_taunt(rig), clip_surrender(rig)]


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "rook", rig, [], impact_time=IMPACT, strike_range=0.10, attack_style="slam", seed=6)
    rc.pedestal_parts(p)
    build_core(p)
    build_blocks(p)
    build_bands(p)
    build_crown(p)
    for k in range(SHARD_N):
        m, piv = _shard_geom(k)
        _V[f"shard_{k}"] = m.P - piv
    p.clips = make_clips(rig)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
