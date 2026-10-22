"""emberhold_bishop - Emberhold Cinder Oracle.

A hooded forge-seer: a tall peaked hood over a gaunt ember-eyed face, a layered oxblood robe (folded under-robe, scalloped
surcoat, embroidered hem, long stole), prayer beads at the hip, bell sleeves, and a bronze crook-staff from which a chained
bronze censer-cage swings, glowing with coals.  Built from docs/art/emberhold_bishop.md.
Bones: root, body, spine, head, top (censer pendulum, rides the staff crook), arm_L/hand_L, arm_R/hand_R.
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

ASSET_ID = "emberhold_bishop"

# ---- robe ellipse family (one description keeps robe / belt / stole / beads nested)
RY = np.array([0.22, 0.245, 0.30, 0.40, 0.50, 0.60, 0.68, 0.74, 0.80, 0.86, 0.92, 0.97, 1.00])
RX = np.array([0.268, 0.272, 0.266, 0.243, 0.222, 0.195, 0.165, 0.128, 0.122, 0.130, 0.142, 0.148, 0.118])
RZ = np.array([0.262, 0.266, 0.260, 0.240, 0.215, 0.190, 0.150, 0.114, 0.098, 0.104, 0.108, 0.106, 0.085])


def rx_(y):
    return np.interp(y, RY, RX)


def rz_(y):
    return np.interp(y, RY, RZ)


def zc_(y):
    return 0.012 * smoothstep(0.70, 0.99, y)


def asym(th, y):
    """Lopsided bell: the skirt swings out toward the front-left and tucks in at the right (a seer in motion, not a gown)."""
    return 1.0 + 0.060 * np.cos(th - 0.9) * float(smoothstep(0.80, 0.30, y))


def ring(y, grow=0.0, K=64, fold=0.0, ph=0.0, yoff=None):
    th = np.linspace(0, TAU, K, endpoint=False)
    f = 1.0
    if fold:
        f = 1 + fold * (0.55 * np.cos(10 * th + 0.4 + ph) + 0.30 * np.cos(17 * th + 2.1 + ph) + 0.15 * np.cos(5 * th + ph))
    f = f * asym(th, y)
    x = (rx_(y) + grow) * f * np.sin(th)
    z = (rz_(y) + grow) * f * np.cos(th) + zc_(y)
    yy = np.full(K, y) if yoff is None else y + yoff(th)
    return np.stack([x, yy, z], 1)


def surf(y, ang_deg, lift=0.0):
    """Point (and outward direction) on the robe surface at height y, angle from +Z toward +X."""
    a = math.radians(ang_deg)
    k = float(asym(a, y))
    p = np.array([(rx_(y) * k + lift) * math.sin(a), y, (rz_(y) * k + lift) * math.cos(a) + zc_(y)])
    n = np.array([math.sin(a) / max(rx_(y), 1e-3), 0, math.cos(a) / max(rz_(y), 1e-3)])
    return p, n / np.linalg.norm(n)


def conform_strip(y0, y1, w0, w1, lift=0.008, rows=14, cols=5, back=False, fold=0.0, seed=0, hem=0.0):
    """Open cloth strip hugging the robe front (or back), width tapering w0 (top) -> w1 (bottom)."""
    ys = np.linspace(y1, y0, rows)            # top -> bottom
    u = np.linspace(-0.5, 0.5, cols)
    grid = []
    rng = np.random.default_rng(seed)
    ph = rng.random(3) * TAU
    for y in ys:
        t = (y1 - y) / (y1 - y0)
        w = w0 + (w1 - w0) * t
        row = []
        for ui in u:
            x = ui * w
            e = max(0.0, 1 - (x / rx_(y)) ** 2)
            z = rz_(y) * float(asym(math.pi if back else 0.0, y)) * math.sqrt(e) + lift + fold * math.sin(ui * 9 + ph[0]) * (0.3 + t) + zc_(y)
            row.append((x, y - hem * t ** 3 * math.sin(ui * 7 + ph[1]), -z if back else z))
        grid.append(row)
    G = np.array(grid)                        # (rows, cols, 3) rows top->bottom
    # loft wants rows progressing so that normal points outward: rows ascending, cols x-ascending (front)
    G = G[::-1]
    m = g.loft(G if not back else G[:, ::-1], closed=False, crease=60, v_tile=0.25, u_tile=0.25)
    return m


def make_rig() -> Rig:
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", (0, 0.60, 0))
    r.add("spine", "body", (0, 0.72, 0))
    r.add("head", "spine", (0, 1.00, 0.01))
    r.add("top", "spine", (-0.20, 1.386, 0.215))
    r.add("arm_L", "spine", (0.14, 0.98, 0))
    r.add("hand_L", "arm_L", (0.17, 0.84, 0.06))
    r.add("arm_R", "spine", (-0.14, 0.98, 0))
    r.add("hand_R", "arm_R", (-0.17, 0.84, 0.06))
    r.add("weapon", "hand_R", (-0.218, 0.80, 0.16))      # the crook staff (centre of mass): lets Surrender drop it
    r.socket("socket_weapon_R", "hand_R", (-0.20, 0.92, 0.10))
    r.socket("socket_cast", "top", (-0.20, 1.12, 0.215))
    r.socket("socket_impact", "body", (0, 0.45, 1.45))
    r.socket("socket_head", "head", (0, 1.30, 0))
    return r


# ======================================================================================= robe
def robe(p: Piece):
    ys = [0.22, 0.245, 0.30, 0.40, 0.50, 0.60, 0.68, 0.74, 0.80, 0.86, 0.92, 0.97, 1.00]
    rings = np.stack([ring(y, 0.0, 80, fold=(0.050 * float(smoothstep(0.72, 0.28, y)) + 0.007)) for y in ys])
    m = g.loft(rings, closed=True, crease=70, cap_start=False).noised(0.0022, 14, 2, seed=3)
    hem = lambda P: ((0.20 + 0.80 * smoothstep(0.22, 0.66, P[:, 1] + 0.05 * g.fbm3(P * 6.0, 3, 2, seed=4)))[:, None]) * np.array([1.10, 0.98, 0.9])
    p.add("robe", m, "EH_Cloth", "body", uv_scale=2, tint=hem)
    # upper body (spine): a second skin over the chest/shoulders so the robe splits cleanly at the waist
    # surcoat: scalloped, darker over-layer from the waist to mid-skirt, folds out of phase with the under-robe
    ysc = [0.745, 0.70, 0.64, 0.57, 0.50, 0.43]
    scal = lambda th: -0.050 * (0.5 + 0.5 * np.cos(8 * th + 0.3))
    rg = []
    for i, y in enumerate(ysc):
        last = i == len(ysc) - 1
        rg.append(ring(y, 0.012 + 0.004 * i, 64, fold=0.03 * (i / 5) + 0.005, ph=0.9, yoff=scal if last else None))
    sur = g.loft(np.stack(rg[::-1]), closed=True, crease=60).noised(0.002, 14, 2, seed=5)
    p.add("surcoat", sur, "EH_Cloth", "body", uv_scale=2, tint=lambda P: (0.40 + 0.6 * smoothstep(0.42, 0.7, P[:, 1]))[:, None] * np.array([0.98, 0.86, 0.80]))
    # hem trim + embroidered glyph band
    trim = g.lathe(np.array([(0.272, 0.250), (0.2775, 0.255), (0.2775, 0.286), (0.272, 0.291)]), 48, crease=40)
    p.add("hem_trim", trim, "EH_Bronze", "body")
    gly = []
    for i in range(16):
        a = i * 22.5
        m2 = g.extrude(g.teardrop(0.028, 0.017, 8), 0.004, 0.0, 1)
        gly.append(m2.translated(0, 0.2535, 0.2785).rotated(0, a, 0))
    p.add("hem_glyphs", merge(gly), "EH_Bronze", "body", lod1=None)
    # pleat ribs: raised creases running hem -> waist (varying length / amplitude)
    ribs = []
    rng = np.random.default_rng(9)
    for i in range(14):
        a = 20 + i * (320 / 13) + rng.normal(0, 3)
        y0 = 0.27 + 0.05 * rng.random()
        y1 = 0.62 + 0.10 * rng.random()
        pts = [surf(y, a, 0.0045 + 0.004 * float(smoothstep(0.7, 0.3, y)))[0] for y in np.linspace(y0, y1, 6)]
        ribs.append(g.tube(pts, [0.0100, 0.0085, 0.0070, 0.0055, 0.0040, 0.0010], sides=5, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 0, 1)))
    p.add("pleat_ribs", merge(ribs), "EH_Cloth", "body", uv_scale=2, lod1=None, tint=lambda P: (0.28 + 0.62 * smoothstep(0.26, 0.6, P[:, 1]))[:, None] * np.array([0.9, 0.8, 0.74]))
    # boots
    for s in (-1, 1):
        b = g.superellipsoid((0.046, 0.026, 0.078), 0.55, 0.6, 4, 10).rotated(-6, s * 6, 0).translated(s * 0.082, 0.245, 0.222)
        p.add(f"boot_{'L' if s > 0 else 'R'}", b, "EH_Leather", "body", uv_scale=2)
        cap = g.superellipsoid((0.034, 0.016, 0.034), 0.55, 0.6, 3, 8).translated(s * 0.082, 0.248, 0.286)
        p.add(f"boot_cap_{'L' if s > 0 else 'R'}", cap, "EH_Bronze", "body", lod1=None)


def torso_details(p: Piece):
    # belt (ellipse band) + buckle + side pouch
    belt = g.loft(np.stack([ring(y, gr, 40) for y, gr in ((0.718, 0.004), (0.722, 0.016), (0.756, 0.016), (0.760, 0.004))]), closed=True, crease=50)
    p.add("belt", belt, "EH_Leather", "body", uv_scale=2)
    pt, n = surf(0.74, 0, 0.018)
    buckle = g.extrude(g.rect_poly(0.046, 0.036, 0.006, 1), 0.012, 0.004, 1).translated(0, 0.74, pt[2] + 0.004)
    p.add("belt_buckle", buckle, "EH_Bronze", "body")
    anvil = g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 0.45, 0.006, 0.0, 1)
    p.add("buckle_anvil", anvil.translated(0, 0.738, pt[2] + 0.012), "EH_Steel", "body", lod1=None)
    # prayer beads, asymmetric on the left hip: cord + beads along a sagging arc on the robe surface
    pts = []
    for t in np.linspace(0, 1, 13):
        y = 0.745 - 0.255 * t
        ang = 36 + 14 * t
        pt, nn = surf(y, ang, 0.014 + 0.004 * math.sin(t * math.pi))
        pts.append(pt)
    pts = np.array(pts)
    cord = g.tube(pts, 0.0042, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
    p.add("bead_cord", cord, "EH_Leather", "body", lod1=None)
    beads = [g.superellipsoid((0.0145, 0.0135, 0.0145), 0.7, 0.7, 3, 7).translated(*pt) for pt in pts[1:]]
    tas = g.tube([pts[-1], pts[-1] + [0.0, -0.05, 0.01], pts[-1] + [0.004, -0.09, 0.015]], [0.008, 0.007, 0.002], sides=5, samples=1, cap="round", cap_steps=1)
    p.add("prayer_beads", merge(beads), "EH_Stone", "body", lod1="auto", uv_scale=2)
    p.add("bead_tassel", tas, "EH_Bronze", "body", lod1=None)
    # key ring pouch on the right
    pouch = g.superellipsoid((0.030, 0.034, 0.020), 0.5, 0.6, 4, 9).translated(*(surf(0.69, -48, 0.016)[0]))
    p.add("pouch", pouch.rotated(0, -40, 0), "EH_Leather", "body", uv_scale=2)
    # upper robe collar ring (underlay of the mantle) is the robe loft itself.  Stole:
    st = conform_strip(0.34, 0.985, 0.115, 0.150, lift=0.011, rows=22, cols=5, fold=0.004, seed=2, hem=0.008)
    p.add("stole", st, "EH_Cloth", "spine", bone2="body", blend=(0.78, 0.62), uv_scale=2,
          tint=lambda P: (0.62 + 0.38 * smoothstep(0.42, 0.9, P[:, 1]))[:, None] * np.array([1.16, 0.96, 0.82]))
    # stole borders (bronze trims running down both edges) and glyphs
    for sgn, nm in ((-1, "R"), (1, "L")):
        yy = np.linspace(0.36, 0.985, 14)
        wv = 0.115 + (0.150 - 0.115) * (0.985 - yy) / (0.985 - 0.34)
        path = [(sgn * wv[i] / 2 * 0.98, yy[i], rz_(yy[i]) * float(asym(0.0, yy[i])) * math.sqrt(max(0.0, 1 - (wv[i] / 2 / rx_(yy[i])) ** 2)) + 0.0165 + zc_(yy[i])) for i in range(len(yy))]
        tr = g.tube(path, 0.0045, sides=4, samples=1, cap="round", cap_steps=1, smooth=False, ellipse=(1.0, 0.7))
        p.add(f"stole_edge_{nm}", tr, "EH_Bronze", "spine", bone2="body", blend=(0.78, 0.62), lod1=None)
    glyphs = []
    for y in (0.46, 0.60, 0.74, 0.86):
        pt, _ = surf(y, 0, 0.0115)
        fl = g.extrude(g.teardrop(0.036, 0.020, 8), 0.004, 0.0, 1).translated(0, y - 0.014, pt[2] + 0.002)
        glyphs.append(fl)
        rng_ = g.torus(0.016, 0.0028, 12, 4).rotated(90, 0, 0).translated(0, y + 0.008, pt[2] + 0.004)
        glyphs.append(rng_)
    p.add("stole_glyphs", merge(glyphs), "EH_Bronze", "spine", bone2="body", blend=(0.78, 0.62), lod1=None)
    # fringe tassels at the stole's hem
    pos, nrm = [], []
    for i, x in enumerate(np.linspace(-0.06, 0.06, 8)):
        pt, _ = surf(0.34, 0, 0.012)
        pos.append((x * 1.4, 0.338, pt[2] + 0.004))
        nrm.append((0, -1, 0.05))
    tuft = g.tube([(0, 0, 0), (0.002, 0.020, 0.002), (0.004, 0.040, 0.006)], [0.0055, 0.0045, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    p.add("stole_fringe", g.instances(tuft, pos, nrm, 1.0), "EH_Bronze", "body", lod1=None)


def extras(p: Piece):
    # bronze anvil medallion on a chain over the stole, and a bronze edge tube on the scalloped surcoat hem
    pt, _ = surf(0.80, 0, 0.0135)
    med = g.lathe(np.array([(0, 0), (0.026, 0), (0.028, 0.004), (0.026, 0.008), (0, 0.009)]), 18, crease=40).rotated(90, 0, 0).translated(0, 0.80, pt[2])
    anv = g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 0.55, 0.005, 0.0, 1).translated(0, 0.796, pt[2] + 0.0125)
    p.add("medallion", merge([med, anv]), "EH_Bronze", "spine", lod1=None)
    ch = [(math.sin(math.radians(a)) * (rx_(0.99) + 0.018), 0.995 - 0.19 * (1 - math.cos(math.radians(a))) * 0.0 - 0.0, 0) for a in ()]
    pts = [surf(y, ang, 0.012)[0] for y, ang in ((0.99, -38), (0.93, -22), (0.86, -9), (0.815, -3))] + [surf(0.815, 0, 0.0135)[0]]
    pts2 = [surf(y, ang, 0.012)[0] for y, ang in ((0.99, 38), (0.93, 22), (0.86, 9), (0.815, 3))] + [surf(0.815, 0, 0.0135)[0]]
    p.add("medallion_chain", merge([g.tube(pts, 0.0038, sides=4, samples=2, cap="round", cap_steps=1), g.tube(pts2, 0.0038, sides=4, samples=2, cap="round", cap_steps=1)]), "EH_Bronze", "spine", lod1=None)
    scal = lambda th: -0.050 * (0.5 + 0.5 * np.cos(8 * th + 0.3))
    edge = ring(0.43, 0.034, 64, fold=0.035, ph=0.9, yoff=scal)
    p.add("surcoat_edge", g.tube(edge, 0.0042, sides=4, samples=1, cap=None, closed=True, smooth=False, up=(0, 1, 0)), "EH_Bronze", "body", lod1=None)


def mantle_and_collar(p: Piece):
    # shoulder mantle: rolled ring that droops to the shoulders (cloth), fur collar with tufts, back flare
    K = 40
    th = np.linspace(0, TAU, K, endpoint=False)
    path = np.stack([0.150 * np.sin(th), 0.985 - 0.030 * np.abs(np.sin(th)) ** 1.5, 0.108 * np.cos(th) + 0.006], 1)
    mant = g.tube(path, 0.027, sides=8, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.0045, 16, 2, seed=7)
    p.add("mantle", mant, "EH_Cloth", "spine", uv_scale=2)
    mant2 = g.tube(path * [1.14, 1, 1.14] - [0, 0.030, 0], 0.024, sides=7, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.004, 16, 2, seed=8)
    p.add("mantle_under", mant2, "EH_Cloth", "spine", uv_scale=2, tint=lambda P: np.full(len(P), 0.7))
    # bronze shoulder caps: right drooping lower (asymmetric)
    for s, nm, drop, bone in ((1, "L", 0.0, "arm_L"), (-1, "R", -0.026, "arm_R")):
        cap = g.superellipsoid((0.052, 0.026, 0.062), 0.55, 0.6, 5, 11).translated(0, 0, 0)
        cap = g.warp(cap, lambda P: np.column_stack([P[:, 0], np.where(P[:, 1] < 0, P[:, 1] * 0.35, P[:, 1]), P[:, 2]]), 60)
        cap = cap.rotated(0, 0, -s * 22).translated(s * 0.172, 0.985 + drop, 0.0)
        cap = cap.noised(0.0016, 36, 2, seed=11 + s)
        p.add(f"shoulder_cap_{nm}", cap, "EH_Bronze", bone)
        lame = g.torus(0.050, 0.0070, 18, 4, arc=230).rotated(0, 0, 0)
        lame = lame.rotated(90, 0, 0).rotated(0, 90 if s > 0 else 270, 0).rotated(0, 0, -s * 22).translated(s * 0.178, 0.962 + drop, 0.0)
        p.add(f"shoulder_lame_{nm}", lame, "EH_Bronze", bone, lod1=None)
    # fur collar: a ring of tufts around the hood base (uses the pawn's tuft idiom)
    tuft = g.tube([(0, 0, 0), (0.004, 0.020, 0.004), (0.010, 0.036, 0.014)], [0.0150, 0.0090, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    ring_ = g.tube(np.stack([0.100 * np.sin(th), np.full(K, 1.004), 0.084 * np.cos(th) + 0.006], 1), 0.022, sides=6, samples=1, cap=None, closed=True,
                   up=(0, 1, 0), smooth=False).noised(0.008, 18, 3, seed=12)
    p.add("fur_collar", ring_, "EH_Fur", "spine", uv_scale=2)
    outer = C.ring_instances(tuft, 20, 0.112, 1.000, normal_tilt=-0.5, scale=1.0, jitter=0.5, seed=4, z_scale=0.84)
    inner = C.ring_instances(tuft, 12, 0.086, 1.022, normal_tilt=0.55, scale=0.8, jitter=0.5, seed=5, start=0.2, z_scale=0.84)
    p.add("fur_tufts", merge([outer, inner]).translated(0, 0, 0.006), "EH_Fur", "spine", uv_scale=2)
    # clasp (bronze) at the throat
    clasp = merge([g.torus(0.016, 0.0034, 14, 4).rotated(90, 0, 0), g.superellipsoid((0.010, 0.010, 0.006), 0.6, 0.6, 3, 7)]).translated(0, 0.968, 0.118)
    p.add("mantle_clasp", clasp, "EH_Bronze", "spine", lod1=None)


# ======================================================================================= arms & hands
def hand(sign, pos, rot=(0, 0, 0), curled=True, open_=False):
    """Mitten with four finger tubes and a thumb. Local frame: fingers point +Z, palm down."""
    palm = g.superellipsoid((0.026, 0.0155, 0.030), 0.55, 0.6, 4, 10).translated(0, 0, 0.012)
    parts = [palm]
    for i, x in enumerate((-0.0165, -0.0055, 0.0055, 0.0165)):
        L = 0.034 - 0.003 * abs(i - 1.5)
        if open_:
            pts = [(x, 0.0, 0.034), (x, 0.002, 0.034 + L * 0.55), (x, 0.0, 0.034 + L)]
        else:
            pts = [(x, 0.0, 0.034), (x, -0.003, 0.034 + L * 0.55), (x, -0.020, 0.034 + L * 0.85)]
        parts.append(g.tube(pts, [0.0070, 0.0062, 0.0050], sides=5, samples=1, cap="round", cap_steps=1))
    th = g.tube([(sign * 0.020, 0.002, 0.014), (sign * 0.036, 0.002, 0.034), (sign * 0.034, 0.004, 0.056)], [0.0090, 0.0078, 0.0058], sides=5, samples=1, cap="round", cap_steps=1)
    parts.append(th)
    m = merge(parts)
    return m.rotated(*rot).translated(*pos)


def arms(p: Piece):
    # --- left arm (hanging open-palmed): upper sleeve on arm_L, bell forearm + hand on hand_L
    el_L = np.array([0.17, 0.84, 0.06])
    up_L = g.tube([(0.152, 0.975, 0.0), (0.164, 0.915, 0.03), tuple(el_L)], [0.043, 0.046, 0.046], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
    p.add("sleeve_up_L", up_L.noised(0.003, 14, 2, seed=21), "EH_Cloth", "arm_L", uv_scale=2)
    fo_L = g.tube([tuple(el_L), (0.182, 0.790, 0.100), (0.192, 0.742, 0.140)], [0.047, 0.058, 0.074], sides=9, samples=2, cap=None, up=(0, 0, 1))
    p.add("sleeve_bell_L", fo_L.noised(0.004, 12, 2, seed=22), "EH_Cloth", "hand_L", uv_scale=2)
    cuff_L = g.lathe(np.array([(0.074, 0.0), (0.081, 0.004), (0.081, 0.020), (0.074, 0.024), (0.066, 0.020), (0.066, 0.004), (0.074, 0.0)]), 20, crease=40)
    cuff_L = cuff_L.rotated(0, 0, 0).scaled(1, 1, 1)
    ax = C.unit([0.192 - 0.182, 0.742 - 0.790, 0.140 - 0.100])
    cuffL = cuff_L.rotated(-90, 0, 0).aimed(ax, (0.192, 0.742, 0.140)) if False else g.torus(0.073, 0.0085, 18, 5).aimed(ax, (0.193, 0.740, 0.142))
    p.add("cuff_L", cuffL, "EH_Bronze", "hand_L")
    inner = g.lathe(np.array([(0.0, 0.0), (0.066, 0.0), (0.066, 0.002), (0.0, 0.002)]), 16, crease=40).aimed(ax, (0.194, 0.738, 0.145))
    p.add("cuff_L_inner", inner, "EH_Cloth", "hand_L", lod1=None, tint=lambda P: np.full(len(P), 0.35))
    p.add("hand_L", hand(+1, (0.198, 0.712, 0.158), (62, 8, 0), curled=True, open_=True), "EH_Leather", "hand_L", uv_scale=2)
    # --- right arm: upper sleeve on arm_R; forearm/bell + hand gripping the staff on hand_R
    el_R = np.array([-0.17, 0.84, 0.06])
    up_R = g.tube([(-0.152, 0.975, 0.0), (-0.162, 0.915, 0.03), tuple(el_R)], [0.043, 0.046, 0.046], sides=8, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
    p.add("sleeve_up_R", up_R.noised(0.003, 14, 2, seed=23), "EH_Cloth", "arm_R", uv_scale=2)
    fo_R = g.tube([tuple(el_R), (-0.186, 0.872, 0.086), (-0.204, 0.912, 0.106)], [0.047, 0.056, 0.068], sides=9, samples=2, cap=None, up=(0, 0, 1))
    p.add("sleeve_bell_R", fo_R.noised(0.004, 12, 2, seed=24), "EH_Cloth", "hand_R", uv_scale=2)
    axr = C.unit([-0.204 + 0.186, 0.912 - 0.872, 0.106 - 0.086])
    cuffR = g.torus(0.067, 0.0085, 18, 5).aimed(axr, (-0.206, 0.916, 0.108))
    p.add("cuff_R", cuffR, "EH_Bronze", "hand_R")
    # right hand: fist around the staff (fingers wrap +Z around the shaft at x=-0.20, z=0.10)
    fist = g.superellipsoid((0.030, 0.027, 0.028), 0.6, 0.6, 4, 9).translated(-0.200, 0.918, 0.123)
    fing = [g.torus(0.020, 0.0066, 8, 4).rotated(90, 0, 0).translated(-0.200, 0.918 + dy, 0.100) for dy in (-0.018, -0.006, 0.006, 0.018)]
    thumb = g.tube([(-0.178, 0.938, 0.128), (-0.188, 0.948, 0.108), (-0.196, 0.946, 0.088)], [0.0092, 0.0080, 0.0062], sides=5, samples=1, cap="round", cap_steps=1)
    p.add("hand_R", merge([fist, thumb]), "EH_Leather", "hand_R", uv_scale=2)
    p.add("hand_R_fingers", merge(fing), "EH_Leather", "hand_R", lod1=None, uv_scale=2)


# ======================================================================================= head, hood
def head(p: Piece):
    cx, cy, cz = 0.0, 1.075, 0.022
    skull = g.superellipsoid((0.050, 0.074, 0.056), 0.85, 0.95, 7, 14).translated(cx, cy, cz)
    # gaunt: narrow the jaw, push the chin forward a little
    skull = g.warp(skull, lambda P: np.column_stack([P[:, 0] * (1 - 0.34 * smoothstep(cy + 0.01, cy - 0.074, P[:, 1])), P[:, 1],
                                                     P[:, 2] + 0.006 * smoothstep(cy - 0.03, cy - 0.074, P[:, 1])]), 60)
    nose = g.superellipsoid((0.0085, 0.020, 0.012), 0.6, 0.6, 4, 8).rotated(-18, 0, 0).translated(0, cy - 0.004, cz + 0.058)
    brow = g.rounded_box((0.092, 0.014, 0.030), 0.0065, 1).translated(0, cy + 0.030, cz + 0.044)
    brow = g.warp(brow, lambda P: np.column_stack([P[:, 0], P[:, 1] - 0.006 * (np.abs(P[:, 0]) / 0.046) ** 2, P[:, 2] - 0.012 * (np.abs(P[:, 0]) / 0.046) ** 2]), 60)
    chin = g.superellipsoid((0.016, 0.013, 0.018), 0.6, 0.6, 3, 8).translated(0, cy - 0.066, cz + 0.042)
    lip = g.tube([(-0.016, cy - 0.044, cz + 0.050), (0, cy - 0.047, cz + 0.058), (0.016, cy - 0.044, cz + 0.050)], 0.0036, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
    ears = [g.superellipsoid((0.0065, 0.016, 0.012), 0.6, 0.6, 3, 6).translated(s * 0.048, cy + 0.002, cz - 0.002) for s in (-1, 1)]
    p.add("face", merge([skull, nose, brow, chin, lip] + ears), "EH_Skin", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.62))
    eyes = [g.superellipsoid((0.0105, 0.0050, 0.0055), 0.7, 0.7, 3, 6).rotated(0, 0, s * -8).translated(s * 0.0225, cy + 0.016, cz + 0.051) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "EH_EmberVein", "head", lod1="keep", bake=False)
    neck = g.tube([(0, 0.985, 0.006), (0, 1.030, 0.010)], [0.034, 0.030], sides=8, samples=1, cap=None, smooth=False)
    p.add("neck", neck, "EH_Skin", "head", uv_scale=2, lod1=None)
    # --- hood: open shell, window narrows to an arch; leans back slightly, peak 1.274
    hy = [0.98, 1.01, 1.045, 1.08, 1.115, 1.15, 1.185, 1.215, 1.24, 1.258, 1.268, 1.274]
    hr = [0.112, 0.116, 0.118, 0.113, 0.106, 0.096, 0.082, 0.066, 0.048, 0.030, 0.014, 0.0]
    gap = lambda y: 70.0 * float(smoothstep(1.20, 1.05, y))
    K = 34
    rows = []
    edgeL, edgeR = [], []
    for y, r in zip(hy, hr):
        a = gap(y)
        th = np.radians(np.linspace(a, 360 - a, K))
        fold_ = 1 + 0.045 * np.cos(7 * th + 0.5) * float(smoothstep(1.24, 1.0, y))
        lean = -0.036 * ((y - 1.06) / 0.214) ** 2 if y > 1.06 else 0.0
        rows.append(np.stack([r * fold_ * np.sin(th) * 1.0, np.full(K, y), r * fold_ * np.cos(th) * 1.04 + 0.004 + lean], 1))
        edgeR.append(rows[-1][0])
        edgeL.append(rows[-1][-1])
    hood = g.loft(np.stack(rows), closed=False, crease=65, v_tile=0.25, u_tile=0.25).noised(0.0022, 16, 2, seed=14)
    p.add("hood", hood, "EH_Cloth", "head", uv_scale=2, tint=lambda P: (0.58 + 0.42 * smoothstep(0.98, 1.22, P[:, 1]))[:, None] * np.array([1.0, 0.95, 0.9]))
    inner = g.loft(np.stack(rows)[:, :, :] * [0.955, 1.0, 0.955] + [0, 0, 0.002], closed=False, crease=65, v_tile=0.25, u_tile=0.25).flipped()
    p.add("hood_lining", inner, "EH_Cloth", "head", lod1=None, tint=lambda P: np.full(len(P), 0.22))
    # face-opening rim (bronze embroidery) following the arch of the window
    path = [tuple(q) for q in edgeL[:-1]] + [tuple(q) for q in edgeR[:-1][::-1]]
    path = [(x * 1.02, y, z + 0.004) for (x, y, z) in path]
    rim = g.tube(path, 0.0105, sides=6, samples=2, cap="round", cap_steps=1, smooth=True)
    p.add("hood_rim", rim, "EH_Bronze", "head")
    # fur lining peeking out along the rim
    fur = g.tube([(x * 0.99, y, z - 0.004) for (x, y, z) in path], 0.0105, sides=5, samples=1, cap="round", cap_steps=1, smooth=True).noised(0.005, 24, 2, seed=30)
    p.add("hood_fur_lining", fur, "EH_Fur", "head", uv_scale=2, lod1=None)
    # peak cap + a short hanging tassel of the peak
    cap = g.superellipsoid((0.016, 0.018, 0.016), 0.7, 0.7, 4, 8).translated(0, 1.268, 0.004 - 0.036 * ((1.268 - 1.06) / 0.214) ** 2)
    p.add("hood_cap", cap, "EH_Bronze", "head")
    # ridge seams on the hood's back (stitched bronze thread)
    seam = g.tube([(0, 0.99, -0.114), (0, 1.07, -0.118), (0, 1.15, -0.098 - 0.002), (0, 1.22, -0.065)], 0.0042, sides=4, samples=2, cap="round", cap_steps=1)
    p.add("hood_seam", seam, "EH_Bronze", "head", lod1=None)
    # back drape: hood tail falling over the back (soft: head -> spine)
    back = conform_strip(0.64, 1.02, 0.17, 0.25, lift=0.010, rows=11, cols=5, back=True, fold=0.008, seed=4, hem=0.012)
    p.add("hood_drape", back, "EH_Cloth", "head", bone2="spine", blend=(0.99, 0.80), uv_scale=2,
          tint=lambda P: (0.40 + 0.6 * smoothstep(0.64, 0.95, P[:, 1]))[:, None] * np.array([0.95, 0.9, 0.86]))
    # soot hem on the sleeves is carried by the tint of cloth parts


# ======================================================================================= staff, chain, censer
def staff(p: Piece):
    path = [(-0.235, 0.226, 0.200), (-0.232, 0.40, 0.190), (-0.222, 0.62, 0.150), (-0.205, 0.80, 0.108), (-0.20, 0.92, 0.100), (-0.20, 1.10, 0.108), (-0.20, 1.28, 0.125)]
    shaft = g.tube(path, [0.0235, 0.0220, 0.0205, 0.0190, 0.0180, 0.0165, 0.0150], sides=8, samples=2, cap=None, up=(1, 0, 0))
    p.add("staff_shaft", shaft.noised(0.0016, 30, 2, seed=40), "EH_Bronze", "weapon", tint=lambda P: np.full(len(P), 0.62))
    crook = g.tube([(-0.20, 1.27, 0.122), (-0.20, 1.335, 0.140), (-0.20, 1.372, 0.178), (-0.20, 1.390, 0.214), (-0.20, 1.372, 0.246), (-0.20, 1.340, 0.252)],
                   [0.0150, 0.0160, 0.0165, 0.0150, 0.0120, 0.0090], sides=8, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("staff_crook", crook.noised(0.0014, 30, 2, seed=41), "EH_Bronze", "weapon")
    # grip wraps
    wraps = [g.torus(0.0228, 0.0042, 10, 4).translated(-0.20, 0.86 + 0.0125 * i, 0.10 + 0.0003 * i) for i in range(7)]
    p.add("staff_wraps", merge(wraps), "EH_Leather", "weapon", uv_scale=2, lod1=None)
    wraps2 = [g.torus(0.0226, 0.0045, 10, 4).translated(-0.20, 0.958 + 0.0125 * i, 0.10 + 0.0004 * i) for i in range(3)]
    p.add("staff_wraps2", merge(wraps2), "EH_Leather", "weapon", uv_scale=2, lod1=None)
    # foot cap (steel), knop rings (bronze)
    foot = g.lathe(np.array([(0.0, 0.222), (0.026, 0.224), (0.029, 0.250), (0.024, 0.290), (0.0215, 0.320), (0.0, 0.320)]), 12, crease=45).translated(-0.235, 0, 0.200)
    p.add("staff_foot", foot, "EH_Steel", "weapon")
    ypts = [0.226, 0.40, 0.62, 0.80, 0.92, 1.10, 1.28]; xs = [-0.235, -0.232, -0.222, -0.205, -0.20, -0.20, -0.20]; zs = [0.200, 0.190, 0.150, 0.108, 0.100, 0.108, 0.125]
    knops = [g.torus(0.0225 - 0.0003 * i, 0.0070, 12, 4).translated(float(np.interp(y, ypts, xs)), y, float(np.interp(y, ypts, zs))) for i, y in enumerate((0.45, 0.62, 1.04, 1.18))]
    knops.append(g.superellipsoid((0.026, 0.020, 0.026), 0.6, 0.6, 4, 9).translated(-0.20, 1.255, 0.119))
    p.add("staff_knops", merge(knops), "EH_Bronze", "weapon")
    # flame-tine finial ring around the crook neck
    tines = []
    for i in range(5):
        a = i * 72
        t = g.tube([(0, 0, 0), (0.008, 0.020, 0), (0.002, 0.046, 0)], [0.0070, 0.0058, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
        tines.append(t.rotated(0, a, 0).rotated(0, 0, 0).translated(-0.20 + 0.0 * math.sin(a), 0, 0))
    tm = merge(tines)
    p.add("staff_tines", tm.rotated(18, 0, 0).translated(0, 1.283, 0.128), "EH_Bronze", "weapon", lod1=None)


def censer(p: Piece):
    cx, cz = -0.20, 0.215
    pivot = (cx, 1.386, cz)
    # one chain from the crook apex to a junction ring, then three chains to the lid ring (a classic hanging thurible)
    chain = g.tube([pivot, (cx, 1.35, cz), (cx, 1.318, cz)], 0.0058, sides=5, samples=4, cap="round", cap_steps=1,
                   radius_fn=lambda t: 0.62 + 0.38 * abs(math.sin(t * 40)))
    junc = g.torus(0.014, 0.0035, 10, 4).rotated(90, 0, 0).translated(cx, 1.314, cz)
    hook = g.torus(0.013, 0.0032, 10, 4).rotated(0, 0, 90).translated(*pivot)
    p.add("chain", merge([chain, junc, hook]), "EH_Steel", "top")
    ch3 = []
    for i in range(3):
        a_ = math.radians(i * 120 + 30)
        ch3.append(g.tube([(cx, 1.312, cz), (cx + 0.018 * math.sin(a_), 1.262, cz + 0.018 * math.cos(a_)), (cx + 0.040 * math.sin(a_), 1.214, cz + 0.040 * math.cos(a_))],
                          0.0046, sides=4, samples=3, cap="round", cap_steps=1, radius_fn=lambda t: 0.62 + 0.38 * abs(math.sin(t * 30))))
    p.add("chains3", merge(ch3), "EH_Steel", "top", lod1=None)
    lidring = g.torus(0.042, 0.0050, 14, 4).translated(cx, 1.204, cz)
    lid = g.lathe(np.array([(0.0, 1.250), (0.010, 1.246), (0.024, 1.236), (0.046, 1.214), (0.062, 1.192), (0.066, 1.186), (0.0, 1.186)]), 18, crease=45).translated(cx, 0, cz)
    # vent holes on the lid read as dark studs
    vents = g.instances(g.dome(0.0085, 0.004, 6, 1), [(cx + 0.040 * math.sin(a_), 1.222, cz + 0.040 * math.cos(a_)) for a_ in np.arange(6) * TAU / 6],
                        [(math.sin(a_), 1.1, math.cos(a_)) for a_ in np.arange(6) * TAU / 6])
    p.add("censer_lid", merge([lid.noised(0.0012, 40, 2, seed=50), lidring]), "EH_Bronze", "top")
    p.add("censer_vents", vents, "EH_Steel", "top", lod1=None)
    # spherical filigree cage: 10 meridian ribs + three latitude rings, hinged at the lid
    ribs = []
    for i in range(10):
        a_ = i * 36
        t = g.tube([(0.018, 1.066, 0), (0.052, 1.086, 0), (0.0685, 1.128, 0), (0.060, 1.166, 0), (0.046, 1.186, 0)], [0.0068, 0.0072, 0.0076, 0.0070, 0.0066],
                   sides=5, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 0, 1))
        ribs.append(t.rotated(0, a_, 0))
    p.add("censer_ribs", merge(ribs).translated(cx, 0, cz), "EH_Bronze", "top")
    rings = [g.torus(0.0690, 0.0058, 18, 4).translated(cx, 1.128, cz), g.torus(0.0545, 0.0050, 16, 4).translated(cx, 1.087, cz), g.torus(0.0625, 0.0050, 16, 4).translated(cx, 1.166, cz)]
    p.add("censer_rings", merge(rings), "EH_Bronze", "top")
    cup = g.lathe(np.array([(0.0, 1.046), (0.020, 1.050), (0.034, 1.062), (0.030, 1.072), (0.0, 1.072)]), 14, crease=45).translated(cx, 0, cz)
    drop = g.tube([(cx, 1.048, cz), (cx, 1.026, cz), (cx, 1.012, cz)], [0.008, 0.007, 0.0], sides=5, samples=1, cap=None, smooth=False)
    p.add("censer_base", merge([cup, drop]), "EH_Steel", "top")
    studs = g.instances(g.dome(0.0058, 0.005, 6, 1), [(cx + 0.0695 * math.sin(a_), 1.128, cz + 0.0695 * math.cos(a_)) for a_ in np.arange(10) * TAU / 10],
                        [(math.sin(a_), 0, math.cos(a_)) for a_ in np.arange(10) * TAU / 10])
    p.add("censer_studs", studs, "EH_Steel", "top", lod1=None)
    # glowing coals visible through the cage (the focal point)
    coals = g.superellipsoid((0.046, 0.042, 0.046), 0.8, 0.85, 4, 10).translated(cx, 1.124, cz).noised(0.006, 18, 2, seed=51)
    p.add("coals", coals, "EH_Ember", "top", lod1="keep", bake=False)
    # smoke: dark soot ribbons curling off the lid (swings with the censer)
    wisps = []
    for i, (ox, oz, h) in enumerate(((0.016, 0.010, 0.110), (-0.020, -0.006, 0.090), (0.004, -0.022, 0.075))):
        pts = [(cx + ox, 1.246, cz + oz), (cx + ox * 2.4, 1.246 + h * 0.4, cz + oz * 2.4), (cx + ox * 0.2, 1.246 + h * 0.72, cz + oz * 0.2 + 0.014), (cx + ox * 3.0, 1.246 + h, cz + oz * 3.0)]
        wisps.append(g.tube(pts, [0.0100, 0.0085, 0.0055, 0.0015], sides=5, samples=2, cap="round", cap_steps=1, ellipse=(1.0, 0.6)))
    p.add("censer_smoke", merge(wisps), "EH_Stone", "top", lod1=None, uv_scale=2, tint=lambda P: np.full(len(P), 0.5))


# ======================================================================================= clips
def make_clips(rig) -> list[Clip]:
    idle = Clip("Idle", 3.6, loop=True)
    idle.keys("top", "rot", [(0, (0, 0, 0)), (0.9, (6, 0, -4), "in_out_cubic"), (1.8, (-4, 0, 5), "in_out_cubic"), (2.7, (4, 0, -3), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.8, (1.5, 0, 0), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    idle.keys("head", "rot", [(0, (0, 0, 0)), (1.8, (-1.5, 1.0, 0), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    idle.keys("hand_R", "rot", [(0, (0, 0, 0)), (2.7, (0, 0, 1), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    idle.keys("body", "pos", [(0, (0, 0, 0)), (1.8, (0, 0.003, 0), "in_out_cubic"), (3.6, (0, 0, 0), "in_out_cubic")])
    C.follow(idle, rig, "top", "weapon")

    move = Clip("Move", 1.0, loop=True)
    move.keys("body", "rot", [(0, (4, 0, 0)), (0.25, (5, 0, 2), "in_out_cubic"), (0.5, (6, 0, 0), "in_out_cubic"), (0.75, (5, 0, -2), "in_out_cubic"), (1.0, (4, 0, 0), "in_out_cubic")])
    move.keys("body", "pos", [(0, (0, 0, 0)), (0.25, (0, 0.02, 0), "out_quad"), (0.5, (0, 0, 0), "in_quad"), (0.75, (0, 0.02, 0), "out_quad"), (1.0, (0, 0, 0), "in_quad")])
    move.keys("top", "rot", [(0, (12, 0, 0)), (0.5, (-14, 0, 0), "in_out_cubic"), (1.0, (12, 0, 0), "in_out_cubic")])
    move.keys("spine", "rot", [(0, (2, 0, 0)), (0.5, (3, 0, 0), "in_out_cubic"), (1.0, (2, 0, 0), "in_out_cubic")])
    move.keys("head", "rot", [(0, (-2, 0, 0)), (0.5, (-3, 0, 0), "in_out_cubic"), (1.0, (-2, 0, 0), "in_out_cubic")])
    C.follow(move, rig, "top", "weapon")

    A = Clip("Attack", 2.4, fps=60)
    # staff is carried on hand_R (elbow pivot): arm and elbow counter-rotate so the crook leads and the foot stays planted until the thrust
    A.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.30, (-10, 0, 0), "in_out_cubic"), (0.95, (-20, 0, 0), "in_out_cubic"), (1.10, (-50, 0, 0), "in_cubic"), (1.30, (-48, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.30, (10, 0, 0), "in_out_cubic"), (0.95, (30, 0, 0), "in_out_cubic"), (1.10, (95, 0, 0), "in_cubic"), (1.30, (90, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.30, (-30, 0, 0), "in_out_cubic"), (0.95, (-80, 0, 0), "in_out_cubic"), (1.30, (-80, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("hand_L", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.95, (-25, 0, 0), "in_out_cubic"), (1.30, (-25, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("spine", "rot", [(0, (0, 0, 0)), (0.30, (-5, 0, 0), "in_out_cubic"), (0.95, (-8, 0, 0), "in_out_cubic"), (1.10, (12, 0, 0), "in_cubic"), (1.30, (10, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("head", "rot", [(0, (0, 0, 0)), (0.30, (0, 0, 0)), (0.95, (-8, 0, 0), "in_out_cubic"), (1.10, (4, 0, 0), "in_cubic"), (1.30, (4, 0, 0)), (2.4, (0, 0, 0), "in_out_cubic")])
    A.keys("body", "pos", [(0, (0, 0, 0)), (0.95, (0, 0, 0), "in_out_cubic"), (1.10, (0, 0, 0.10), "in_cubic"), (1.45, (0, 0, 0.10)), (2.4, (0, 0, 0), "in_out_cubic")])
    # censer: a widening circular swing, then the whip forward at the strike (forward = -rx for a hanging weight)
    A.keys("top", "rot", [(0, (0, 0, 0)), (0.30, (-35, 0, 0), "in_out_cubic"), (0.50, (0, 0, 50), "in_out_cubic"), (0.70, (45, 0, 0), "in_out_cubic"),
                          (0.90, (0, 0, -55), "in_out_cubic"), (0.95, (-60, 0, 0), "in_out_cubic"), (1.10, (-85, 0, 0), "in_cubic"), (1.30, (-60, 0, 0), "out_quad"),
                          (1.60, (10, 0, 0), "in_out_cubic"), (1.90, (-6, 0, 0), "in_out_cubic"), (2.15, (3, 0, 0), "in_out_cubic"), (2.4, (0, 0, 0), "in_out_cubic")])
    C.follow(A, rig, "top", "weapon")

    hit = Clip("HitReact", 0.45)
    hit.keys("body", "rot", [(0, (0, 0, 0)), (0.10, (-11, 0, 0), "out_cubic"), (0.45, (-4, 0, 0), "in_out_cubic")])
    hit.keys("body", "pos", [(0, (0, 0, 0)), (0.10, (0, 0, -0.07), "out_cubic"), (0.45, (0, 0, -0.02), "in_out_cubic")])
    hit.keys("spine", "rot", [(0, (0, 0, 0)), (0.10, (-9, 0, 0), "out_cubic"), (0.45, (-3, 0, 0), "in_out_cubic")])
    hit.keys("head", "rot", [(0, (0, 0, 0)), (0.10, (-14, 0, 0), "out_cubic"), (0.45, (-5, 0, 0), "in_out_cubic")])
    hit.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.10, (6, 0, 0), "out_cubic"), (0.45, (1, 0, 0), "in_out_cubic")])
    hit.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.10, (-6, 0, 0), "out_cubic"), (0.45, (-1, 0, 0), "in_out_cubic")])
    hit.keys("top", "rot", [(0, (0, 0, 0)), (0.10, (30, 0, 0), "out_cubic"), (0.28, (-12, 0, 0), "in_out_cubic"), (0.45, (8, 0, 0), "in_out_cubic")])
    C.follow(hit, rig, "top", "weapon")

    vic = Clip("Victory", 1.8)
    vic.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.6, (-30, 0, 0), "out_back"), (1.8, (-30, 0, 0))])
    vic.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.6, (45, 0, 0), "out_back"), (1.8, (45, 0, 0))])
    vic.keys("head", "rot", [(0, (0, 0, 0)), (0.6, (-10, 0, 0), "out_cubic"), (1.8, (-10, 0, 0))])
    vic.keys("spine", "rot", [(0, (0, 0, 0)), (0.6, (-6, 0, 0), "out_cubic"), (1.8, (-6, 0, 0))])
    vic.keys("arm_L", "rot", [(0, (0, 0, 0)), (1.0, (-25, 0, 0), "out_cubic"), (1.8, (-25, 0, 0))])
    vic.keys("top", "rot", [(0, (0, 0, 0)), (0.6, (-30, 0, 0), "out_cubic"), (0.8, (30, 0, 0), "in_out_cubic"), (1.0, (-20, 0, 0), "in_out_cubic"), (1.3, (10, 0, 0), "in_out_cubic"), (1.8, (3, 0, 0), "in_out_cubic")])
    C.follow(vic, rig, "top", "weapon")

    # ---- Taunt (1.5 s): the censer is whirled in a wide horizontal circle above the hood, then the left hand points at the enemy king
    T = Clip("Taunt", 1.5)
    T.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.20, (-10, 0, 0), "in_out_cubic"), (1.15, (-14, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("hand_R", "rot", [(0, (0, 0, 0)), (0.20, (10, 0, 0), "in_out_cubic"), (1.15, (16, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("top", "rot", [(0, (0, 0, 0)), (0.18, (-40, 0, 0), "in_out_cubic"), (0.32, (-90, 0, 0), "in_out_cubic"), (0.46, (-10, 0, 90), "in_out_cubic"), (0.60, (90, 0, 0), "in_out_cubic"),
                          (0.74, (10, 0, -90), "in_out_cubic"), (0.88, (-90, 0, 0), "in_out_cubic"), (1.02, (-30, 0, 40), "in_out_cubic"), (1.25, (8, 0, -6), "in_out_cubic"), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.78, (-8, 0, 0), "in_out_cubic"), (1.0, (-92, 0, -6), "out_cubic"), (1.28, (-92, 0, -6)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("hand_L", "rot", [(0, (0, 0, 0)), (1.0, (-10, 0, 0), "out_cubic"), (1.28, (-10, 0, 0)), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("spine", "rot", [(0, (0, 0, 0)), (0.5, (-4, 0, 6), "in_out_cubic"), (1.0, (-6, 0, 0), "in_out_cubic"), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("head", "rot", [(0, (0, 0, 0)), (0.5, (-8, 0, 0), "in_out_cubic"), (1.0, (-10, 4, 0), "in_out_cubic"), (1.5, (0, 0, 0), "in_out_cubic")])
    T.keys("body", "pos", [(0, (0, 0, 0)), (1.0, (0, 0.012, 0.03), "out_cubic"), (1.5, (0, 0, 0), "in_out_cubic")])
    C.follow(T, rig, "top", "weapon")

    # ---- Surrender (2.2 s, holds): bows his hooded head, the staff slips and clatters on the plinth, the censer sags and lies still
    S = Clip("Surrender", 2.2)
    S.keys("spine", "rot", [(0, (0, 0, 0)), (0.9, (16, 0, 0), "in_out_cubic"), (2.2, (20, 0, 0), "in_out_cubic")])
    S.keys("head", "rot", [(0, (0, 0, 0)), (0.9, (26, 0, 0), "in_out_cubic"), (2.2, (32, 0, 0), "in_out_cubic")])
    S.keys("body", "pos", [(0, (0, 0, 0)), (0.9, (0, -0.025, 0.02), "in_out_cubic"), (2.2, (0, -0.03, 0.02))])
    S.keys("body", "rot", [(0, (0, 0, 0)), (0.9, (5, 0, 0), "in_out_cubic"), (2.2, (6, 0, 0))])
    S.keys("arm_R", "rot", [(0, (0, 0, 0)), (0.35, (-6, 0, 0), "in_out_cubic"), (1.0, (12, 0, 0), "in_out_cubic"), (2.2, (16, 0, 0))])
    S.keys("hand_R", "rot", [(0, (0, 0, 0)), (1.0, (8, 0, 0), "in_out_cubic"), (2.2, (10, 0, 0))])
    S.keys("arm_L", "rot", [(0, (0, 0, 0)), (0.6, (10, 0, 0), "in_out_cubic"), (2.2, (14, 0, 0))])
    S.keys("top", "rot", [(0, (0, 0, 0)), (0.30, (-14, 0, 0), "in_out_cubic"), (0.62, (22, 0, 8), "in_out_cubic"), (0.95, (-12, 0, 40), "in_out_cubic"), (1.3, (0, 0, 74), "in_out_cubic"), (2.2, (0, 0, 78))])
    C.drop_weapon(S, rig, "weapon", 0.50, (0.03, 1.0, 0.012), 0.22, 0.022, (0.82, 0.0, 0.55), land_xz=(-0.04, 0.22), roll_deg=60.0)
    C.follow(S, rig, "top", "weapon")
    return [idle, move, A, hit, vic, T, S]


# ======================================================================================= forward lean
def lean(y):
    """The whole figure above the hem leans a few degrees forward (z shift grows with height)."""
    return 0.052 * smoothstep(0.30, 1.35, y)


def lean_rig(rig):
    for b in rig.bones.values():
        b.pos = b.pos + np.array([0.0, 0.0, float(lean(b.pos[1]))])
    for k, (bone, pos) in list(rig.sockets.items()):
        if not k.startswith("socket_impact"):
            rig.sockets[k] = (bone, pos + np.array([0.0, 0.0, float(lean(pos[1]))]))


def lean_parts(p):
    for q in p.parts:
        m = q.mesh.copy()
        m.P[:, 2] += lean(m.P[:, 1])
        q.mesh = m


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    lean_rig(rig)
    p = Piece("emberhold", "bishop", rig, make_clips(rig), impact_time=1.10, strike_range=1.50, attack_style="ranged", seed=7)
    C.pedestal_parts(p)
    robe(p)
    torso_details(p)
    mantle_and_collar(p)
    extras(p)
    arms(p)
    head(p)
    staff(p)
    censer(p)
    lean_parts(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
