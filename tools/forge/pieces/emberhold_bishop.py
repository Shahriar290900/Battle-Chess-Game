"""emberhold_bishop - Emberhold Cinder Oracle.

A forge-seer in a layered, sooted ember-red robe with an embroidered stole, crowned with a tall bronze MITRE that is cut by a deep
38 degree diagonal slit lined with oxblood cloth (the identity cue), leaning on a crook-staff from which a chained bronze censer swings,
its coals glowing through the cage.  Prayer beads hang at the left hip.
Built from docs/art/emberhold_bishop.md on the full humanoid skeleton: smooth-skinned sleeves / neck / robe / stole, skirt-compression
bones (the hem stays planted, the kneel gathers the robe), rigid metal, and a gravity-hung censer chain (top > cape_1 > cape_2) that
the animator keeps vertical in the world while the staff moves.  All clips are procedural IK / pendulum motion baked to dense tracks.
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
from rig import Rig                                # noqa: E402
from anim import Animator, Curve, Fn, Wave, Skin, humanoid_rig, limb_tube   # noqa: E402
from anim import motion as M                       # noqa: E402
from anim.curves import step_signal                # noqa: E402
from anim.xf import rot_between, slerp, quat_from_mat, mat_from_quat   # noqa: E402
import _emberhold_common as C                      # noqa: E402

ASSET_ID = "emberhold_bishop"
V = lambda *x: np.array(x, dtype=float)            # noqa: E731
nrm = lambda v: np.asarray(v, float) / np.linalg.norm(v)      # noqa: E731


def lerp3(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


# ======================================================================================= robe ellipse family
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
    return 1.0 + 0.045 * np.cos(th - 0.9) * float(smoothstep(0.80, 0.30, y))


def fold_amp(y):
    return 0.050 * float(smoothstep(0.72, 0.28, y)) + 0.007


def fold_f(th, y, ph=0.0):
    return 1 + fold_amp(y) * (0.55 * np.cos(10 * th + 0.4 + ph) + 0.30 * np.cos(17 * th + 2.1 + ph) + 0.15 * np.cos(5 * th + ph))


def ring(y, grow=0.0, K=80, fold=None, ph=0.0, yoff=None):
    th = np.linspace(0, TAU, K, endpoint=False)
    f = (fold_f(th, y, ph) if fold is None else (1 + fold * (0.55 * np.cos(10 * th + 0.4 + ph) + 0.30 * np.cos(17 * th + 2.1 + ph) + 0.15 * np.cos(5 * th + ph)))) * asym(th, y)
    x = (rx_(y) + grow) * f * np.sin(th)
    z = (rz_(y) + grow) * f * np.cos(th) + zc_(y)
    yy = np.full(K, y) if yoff is None else y + yoff(th)
    return np.stack([x, yy, z], 1)


def surf(y, ang_deg, lift=0.0):
    """Point (and outward direction) on the robe surface at height y, angle from +Z toward +X."""
    a = math.radians(ang_deg)
    k = float(asym(a, y)) * float(fold_f(a, y))
    p = np.array([(rx_(y) * k + lift) * math.sin(a), y, (rz_(y) * k + lift) * math.cos(a) + zc_(y)])
    n = np.array([math.sin(a) / max(rx_(y), 1e-3), 0, math.cos(a) / max(rz_(y), 1e-3)])
    return p, n / np.linalg.norm(n)


def conform_strip(y0, y1, w0, w1, lift=0.008, rows=14, cols=5, back=False, fold=0.0, seed=0, hem=0.0):
    """Open cloth strip hugging the robe front (or back), width tapering w0 (top) -> w1 (bottom)."""
    ys = np.linspace(y1, y0, rows)
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
            zf = rz_(y) * float(asym(math.pi if back else 0.0, y)) * float(fold_f(math.pi if back else 0.0, y))
            z = zf * math.sqrt(e) + lift + fold * math.sin(ui * 9 + ph[0]) * (0.3 + t) + zc_(y)
            row.append((x, y - hem * t ** 3 * math.sin(ui * 7 + ph[1]), -z if back else z))
        grid.append(row)
    G = np.array(grid)[::-1]
    return g.loft(G if not back else G[:, ::-1], closed=False, crease=60, v_tile=0.25, u_tile=0.25)


# ======================================================================================= rig
JOINTS = dict(pelvis=(0, 0.60, 0), spine=(0, 0.72, 0), chest=(0, 0.86, 0), neck=(0, 0.97, 0.01), head=(0, 1.00, 0.012), top=(-0.235, 1.385, 0.218),
              clavicle_L=(0.07, 0.95, 0), shoulder_L=(0.14, 0.98, 0), elbow_L=(0.18, 0.82, 0.05), wrist_L=(0.20, 0.72, 0.13),
              hip_L=(0.07, 0.62, 0), knee_L=(0.08, 0.42, 0.05), ankle_L=(0.075, 0.26, 0.05), toe_L=(0.075, 0.245, 0.13),
              elbow_R=(-0.205, 0.82, 0.06), wrist_R=(-0.2386, 0.90, 0.1443))
J_ = lambda k: np.array(JOINTS[k] if k in JOINTS else ((-JOINTS[k[:-1] + "L"][0],) + tuple(JOINTS[k[:-1] + "L"][1:])), dtype=float)   # noqa: E731

# the crook-staff: a straight shaft from the foot cap to the crook base, the grip at wrist_R
S_FOOT, S_TOP = V(-0.245, 0.22, 0.170), V(-0.235, 1.28, 0.130)
A_S = nrm(S_FOOT - S_TOP)                          # staff axis at rest: grip -> foot
WR0, WL0 = J_("wrist_R"), J_("wrist_L")
W0 = S_TOP + (S_FOOT - S_TOP) * ((1.28 - 0.80) / 1.06)        # `weapon` bone = staff centre (y 0.80)
PIV = V(-0.235, 1.385, 0.218)                      # censer pendulum pivot (over the crook)
CX, CZ = PIV[0], PIV[2]
CH1, CH2 = V(CX, 1.314, CZ), V(CX, 1.212, CZ)      # junction ring, lid ring
CEN_S = 0.82                                       # censer scale (about the lid ring)
CEN_C = CH2 + (V(CX, 1.125, CZ) - CH2) * CEN_S       # censer centre (coals)
PEND = float(np.linalg.norm(CEN_C - PIV))          # pivot -> censer centre (0.26)


def make_rig() -> Rig:
    base = humanoid_rig(JOINTS, weapon=tuple(W0), cape=[tuple(CH1), tuple(CH2)])
    r = Rig()
    for name, b in base.bones.items():                      # `top` (the censer pivot) rides the staff: re-parent it under `weapon`
        if name == "top":
            continue
        if name == "cape_1":
            r.add("top", "weapon", PIV)
        r.add(name, b.parent, b.pos)
    r.alias = dict(base.alias)
    r.add("skirt_1", "body", (0, 0.60, 0))                  # skirt compression bones: the hem stays planted, the kneel gathers the robe
    r.add("skirt_2", "body", (0, 0.40, 0))
    r.add("skirt_3", "body", (0, 0.26, 0))
    r.socket("socket_weapon_R", "wrist_R", tuple(WR0))
    r.socket("socket_cast", "cape_2", tuple(CEN_C))
    r.socket("socket_impact", "body", (0, 0.45, 1.45))
    r.socket("socket_head", "head", (0, 1.38, 0))
    return r


# ---- smooth-skin recipes
LEG_SKIN = {s: Skin.chain([f"thigh_{s}", f"shin_{s}", f"foot_{s}"], pre="body", tip=tuple(J_(f"toe_{s}")), zone=0.4) for s in "LR"}
ARM_SKIN = {s: Skin.chain([f"arm_{s}", f"hand_{s}"], pre=f"clavicle_{s}", tip=tuple(J_(f"wrist_{s}")), zone=0.42) for s in "LR"}
TORSO_SKIN = Skin.chain(["body", "spine", "chest"], tip=JOINTS["neck"], zone=0.45)
NECK_SKIN = Skin.chain(["neck", "head"], pre="chest", tip=(0, 1.08, 0.012), zone=0.45)
_SK_N = Skin.nearest([("body", J_("pelvis"), J_("spine")), ("skirt_1", (0, 0.60, 0), (0, 0.60, 0)), ("skirt_2", (0, 0.40, 0), (0, 0.40, 0)),
                      ("skirt_3", (0, 0.26, 0), (0, 0.26, 0)), ("thigh_L", J_("hip_L"), J_("knee_L")), ("thigh_R", J_("hip_R"), J_("knee_R"))],
                     tau=0.07, bias={"thigh_L": 0.40, "thigh_R": 0.40})
SKIRT_SKIN = Skin.gradient(_SK_N, Skin.rigid("skirt_3"), axis=1, v0=0.40, v1=0.27)             # the hem is planted on the plinth
ROBE_SKIN = Skin.gradient(TORSO_SKIN, SKIRT_SKIN, axis=1, v0=0.80, v1=0.68)                    # waist follows the torso, skirt follows the legs
CHAIN_SKIN = Skin.chain(["top", "cape_1", "cape_2"], pre="weapon", tip=tuple(CH2 + V(0, -0.012, 0)), zone=0.4)
LAP_SKIN = Skin.gradient(Skin.rigid("head"), Skin.rigid("chest"), axis=1, v0=1.06, v1=0.90)


def tint_robe(P):
    hem = (0.20 + 0.80 * smoothstep(0.22, 0.66, P[:, 1] + 0.05 * g.fbm3(P * 6.0, 3, 2, seed=4)))
    return hem[:, None] * np.array([1.10, 0.98, 0.9])


# ======================================================================================= robe & legs
def robe(p: Piece):
    ys = [0.222, 0.235, 0.255, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.69, 0.72, 0.75, 0.80, 0.84, 0.88, 0.92, 0.95, 0.968]
    rings = np.stack([ring(y, 0.0, 72) for y in ys])
    m = g.loft(rings, closed=True, crease=70, cap_start=False, cap_end=True).noised(0.0020, 14, 2, seed=3)
    p.add("robe", m, "EH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, tint=tint_robe)
    # surcoat: scalloped darker over-layer from the waist to mid-skirt, folds out of phase with the under-robe
    ysc = [0.745, 0.71, 0.66, 0.60, 0.54, 0.48, 0.43]
    scal = lambda th: -0.050 * (0.5 + 0.5 * np.cos(8 * th + 0.3))                    # noqa: E731
    rg = []
    for i, y in enumerate(ysc):
        last = i == len(ysc) - 1
        rg.append(ring(y, 0.012 + 0.003 * i, 64, fold=fold_amp(y) * 0.6 + 0.004, ph=0.9, yoff=scal if last else None))
    sur = g.loft(np.stack(rg[::-1]), closed=True, crease=60).noised(0.0018, 14, 2, seed=5)
    p.add("surcoat", sur, "EH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, tint=lambda P: (0.36 + 0.64 * smoothstep(0.42, 0.72, P[:, 1]))[:, None] * np.array([0.92, 0.82, 0.78]))
    edge = ring(0.43, 0.030, 64, fold=0.025, ph=0.9, yoff=scal)
    p.add("surcoat_edge", g.tube(edge, 0.0040, sides=4, samples=1, cap=None, closed=True, smooth=False, up=(0, 1, 0)), "EH_Bronze", None, skin=ROBE_SKIN, lod1=None)
    # rolled bronze hem rim (smooth, wraps the folds) studded with bronze bosses
    rows = [(0.226, 0.010), (0.238, 0.0185), (0.275, 0.0185), (0.296, 0.009)]
    band = g.loft(np.stack([ring(y, gr, 72, fold=0.0) for y, gr in rows]), closed=True, crease=40)
    p.add("hem_trim", band, "EH_Bronze", None, skin=ROBE_SKIN)
    pos, nr = [], []
    for i in range(24):
        a_ = i * 15.0 + 3
        pt, nn = surf(0.258, a_, 0.0)
        k = (rx_(0.258) + 0.0195) / max(rx_(0.258), 1e-3)
        th = math.radians(a_)
        kk = float(asym(th, 0.258))
        pt = np.array([(rx_(0.258) * kk + 0.0195) * math.sin(th), 0.258, (rz_(0.258) * kk + 0.0195) * math.cos(th) + zc_(0.258)])
        pos.append(pt)
        nr.append(nn)
    p.add("hem_studs", g.instances(g.dome(0.0085, 0.007, 6, 1), pos, nr), "EH_Bronze", None, skin=ROBE_SKIN, lod1=None)
    # vertical pleat ribs (inverted pleats), hem -> waist, darker than the robe
    ribs = []
    rng = np.random.default_rng(9)
    for i in range(16):
        a_ = 12 + i * (336 / 15) + rng.normal(0, 3)
        y0, y1 = 0.30 + 0.04 * rng.random(), 0.62 + 0.10 * rng.random()
        pts = [surf(y, a_, 0.0045 + 0.004 * float(smoothstep(0.7, 0.3, y)))[0] for y in np.linspace(y0, y1, 6)]
        ribs.append(g.tube(pts, [0.0100, 0.0088, 0.0074, 0.0058, 0.0040, 0.0012], sides=4, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 0, 1)))
    p.add("pleat_ribs", merge(ribs), "EH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, lod1=None,
          tint=lambda P: (0.30 + 0.62 * smoothstep(0.28, 0.62, P[:, 1]))[:, None] * np.array([0.9, 0.8, 0.74]))


def legs(p: Piece):
    for s, nm in ((1, "L"), (-1, "R")):
        hip, knee, ank = J_(f"hip_{nm}"), J_(f"knee_{nm}"), J_(f"ankle_{nm}")
        x = s * 0.075
        hose = limb_tube([hip + [0, 0.03, 0], lerp3(hip, knee, 0.5) + [0, 0, 0.004], knee, lerp3(knee, ank, 0.5), ank + [0, 0.01, 0]],
                         [0.052, 0.047, 0.040, 0.035, 0.032], joints=[knee], spacing=0.06, joint_spacing=0.03, joint_zone=0.05, sides=7, cap=None, up=(0, 0, 1))
        p.add(f"hose_{nm}", hose, "EH_Cloth", None, skin=LEG_SKIN[nm], uv_scale=2, tint=lambda P: np.full(len(P), 0.4), lod1=None)
        foot = g.superellipsoid((0.036, 0.025, 0.090), 0.5, 0.62, 4, 10).translated(x, 0.250, 0.190)
        shaft = g.tube([(x, 0.340, 0.050), (x, 0.275, 0.050)], [0.040, 0.043], sides=8, samples=1, cap=None, smooth=False)
        p.add(f"boot_{nm}", merge([foot, shaft]), "EH_Leather", f"foot_{nm}", uv_scale=2)
        kc = g.superellipsoid((0.040, 0.036, 0.030), 0.6, 0.6, 3, 8).translated(*(knee + [0, 0, 0.034]))
        p.add(f"knee_{nm}", kc, "EH_Cloth", f"shin_{nm}", lod1=None, tint=lambda P: np.full(len(P), 0.4))


# ======================================================================================= torso details
def torso_details(p: Piece):
    belt = g.loft(np.stack([ring(y, gr, 40) for y, gr in ((0.718, 0.004), (0.722, 0.016), (0.756, 0.016), (0.760, 0.004))]), closed=True, crease=50)
    p.add("belt", belt, "EH_Leather", None, skin=TORSO_SKIN, uv_scale=2)
    pt, n = surf(0.74, 0, 0.018)
    buckle = g.extrude(g.rect_poly(0.046, 0.036, 0.006, 1), 0.012, 0.004, 1).translated(0, 0.74, pt[2] + 0.004)
    p.add("belt_buckle", buckle, "EH_Bronze", None, skin=TORSO_SKIN)
    anvil = g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 0.45, 0.006, 0.0, 1)
    p.add("buckle_anvil", anvil.translated(0, 0.738, pt[2] + 0.012), "EH_Steel", None, skin=TORSO_SKIN, lod1=None)
    # prayer beads on a cord, asymmetric at the left hip
    pts = []
    for t in np.linspace(0, 1, 13):
        y = 0.745 - 0.255 * t
        pt, nn = surf(y, 38 + 14 * t, 0.014 + 0.004 * math.sin(t * math.pi))
        pts.append(pt)
    pts = np.array(pts)
    p.add("bead_cord", g.tube(pts, 0.0040, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "EH_Leather", None, skin=ROBE_SKIN, lod1=None)
    beads = [g.superellipsoid((0.0145, 0.0135, 0.0145), 0.7, 0.7, 3, 7).translated(*pt) for pt in pts[1:]]
    p.add("prayer_beads", merge(beads), "EH_Stone", None, skin=ROBE_SKIN, uv_scale=2)
    tas = g.tube([pts[-1], pts[-1] + [0.0, -0.05, 0.01], pts[-1] + [0.004, -0.09, 0.015]], [0.008, 0.007, 0.002], sides=5, samples=1, cap="round", cap_steps=1)
    p.add("bead_tassel", tas, "EH_Bronze", None, skin=ROBE_SKIN, lod1=None)
    # the long embroidered stole
    st = conform_strip(0.34, 0.965, 0.125, 0.165, lift=0.011, rows=22, cols=5, fold=0.004, seed=2, hem=0.008)
    p.add("stole", st, "EH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, tint=lambda P: (0.26 + 0.14 * smoothstep(0.42, 0.9, P[:, 1]))[:, None] * np.array([1.0, 0.72, 0.66]))
    for sgn, nm in ((-1, "R"), (1, "L")):
        yy = np.linspace(0.36, 0.965, 14)
        wv = 0.125 + (0.165 - 0.125) * (0.965 - yy) / (0.965 - 0.34)
        path = [(sgn * wv[i] / 2 * 0.98, yy[i], rz_(yy[i]) * float(asym(0.0, yy[i])) * float(fold_f(0.0, yy[i])) * math.sqrt(max(0.0, 1 - (wv[i] / 2 / rx_(yy[i])) ** 2)) + 0.0165 + zc_(yy[i]))
                for i in range(len(yy))]
        p.add(f"stole_edge_{nm}", g.tube(path, 0.0045, sides=4, samples=1, cap="round", cap_steps=1, smooth=False, ellipse=(1.0, 0.7)), "EH_Bronze", None, skin=ROBE_SKIN, lod1=None)
    glyphs = []
    for y in (0.46, 0.60, 0.74, 0.86):
        pt, _ = surf(y, 0, 0.0115)
        glyphs.append(g.extrude(g.teardrop(0.036, 0.020, 8), 0.004, 0.0, 1).translated(0, y - 0.014, pt[2] + 0.002))
        glyphs.append(g.torus(0.016, 0.0028, 12, 4).rotated(90, 0, 0).translated(0, y + 0.008, pt[2] + 0.004))
    p.add("stole_glyphs", merge(glyphs), "EH_Bronze", None, skin=ROBE_SKIN, lod1=None)
    pos, nr = [], []
    for x in np.linspace(-0.06, 0.06, 8):
        pt, _ = surf(0.34, 0, 0.012)
        pos.append((x * 1.4, 0.338, pt[2] + 0.004))
        nr.append((0, -1, 0.05))
    tuft = g.tube([(0, 0, 0), (0.002, 0.020, 0.002), (0.004, 0.040, 0.006)], [0.0055, 0.0045, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    p.add("stole_fringe", g.instances(tuft, pos, nr, 1.0), "EH_Bronze", None, skin=ROBE_SKIN, lod1=None)
    # anvil medallion on a chain over the stole
    pt, _ = surf(0.80, 0, 0.0135)
    med = g.lathe(np.array([(0, 0), (0.026, 0), (0.028, 0.004), (0.026, 0.008), (0, 0.009)]), 18, crease=40).rotated(90, 0, 0).translated(0, 0.80, pt[2])
    anv2 = g.extrude(np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)]) * 0.55, 0.005, 0.0, 1).translated(0, 0.796, pt[2] + 0.0125)
    p.add("medallion", merge([med, anv2]), "EH_Bronze", None, skin=TORSO_SKIN)
    c1 = [surf(y, ang, 0.012)[0] for y, ang in ((0.965, -38), (0.93, -22), (0.86, -9), (0.815, -3))] + [surf(0.815, 0, 0.0135)[0]]
    c2 = [surf(y, ang, 0.012)[0] for y, ang in ((0.965, 38), (0.93, 22), (0.86, 9), (0.815, 3))] + [surf(0.815, 0, 0.0135)[0]]
    p.add("medallion_chain", merge([g.tube(c1, 0.0036, sides=4, samples=2, cap="round", cap_steps=1), g.tube(c2, 0.0036, sides=4, samples=2, cap="round", cap_steps=1)]),
          "EH_Bronze", None, skin=TORSO_SKIN, lod1=None)
    # back drape under the mantle
    back = conform_strip(0.62, 0.965, 0.17, 0.26, lift=0.010, rows=11, cols=5, back=True, fold=0.008, seed=4, hem=0.012)
    p.add("back_drape", back, "EH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, tint=lambda P: (0.34 + 0.6 * smoothstep(0.62, 0.95, P[:, 1]))[:, None] * np.array([0.95, 0.86, 0.8]))


def mantle_and_collar(p: Piece):
    K = 52
    th = np.linspace(0, TAU, K, endpoint=False)
    path = np.stack([0.142 * np.sin(th), 0.966 - 0.030 * np.abs(np.sin(th)) ** 1.5, 0.104 * np.cos(th) + 0.006], 1)
    mant = g.tube(path, 0.026, sides=10, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.0025, 16, 2, seed=7)
    p.add("mantle", mant, "EH_Cloth", "chest", uv_scale=2)
    mant2 = g.tube(path * [1.14, 1, 1.14] - [0, 0.028, 0], 0.021, sides=6, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.004, 16, 2, seed=8)
    p.add("mantle_under", mant2, "EH_Cloth", "chest", uv_scale=2, tint=lambda P: np.full(len(P), 0.6), lod1=None)
    # cowl collar hugging the neck
    thc = np.linspace(0, TAU, 24, endpoint=False)
    cpath = np.stack([0.072 * np.sin(thc), np.full(24, 0.958), 0.066 * np.cos(thc) + 0.010], 1)
    p.add("cowl_collar", g.tube(cpath, 0.024, sides=7, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.006, 18, 2, seed=9), "EH_Cloth", "chest", uv_scale=2)
    for s, nm, drop in ((1, "L", 0.0), (-1, "R", -0.026)):
        cap = g.superellipsoid((0.058, 0.036, 0.066), 0.6, 0.7, 5, 12)
        cap = g.warp(cap, lambda P: np.column_stack([P[:, 0], np.where(P[:, 1] < 0, P[:, 1] * 0.35, P[:, 1]), P[:, 2]]), 60)
        cap = cap.rotated(0, 0, -s * 22).translated(s * 0.172, 0.975 + drop, 0.0).noised(0.0016, 36, 2, seed=11 + s)
        p.add(f"shoulder_cap_{nm}", cap, "EH_Bronze", f"arm_{nm}")
        lame = g.torus(0.050, 0.0070, 16, 4, arc=230).rotated(90, 0, 0).rotated(0, 90 if s > 0 else 270, 0).rotated(0, 0, -s * 22).translated(s * 0.178, 0.952 + drop, 0.0)
        p.add(f"shoulder_lame_{nm}", lame, "EH_Bronze", f"arm_{nm}", lod1=None)
    clasp = merge([g.torus(0.016, 0.0034, 12, 4).rotated(90, 0, 0), g.superellipsoid((0.010, 0.010, 0.006), 0.6, 0.6, 3, 6)]).translated(0, 0.945, 0.114)
    p.add("mantle_clasp", clasp, "EH_Bronze", "chest", lod1=None)


# ======================================================================================= arms & hands
def arms(p: Piece):
    for s, nm in ((1, "L"), (-1, "R")):
        sh, el, wr = J_(f"shoulder_{nm}"), J_(f"elbow_{nm}"), J_(f"wrist_{nm}")
        fd = C.unit(wr - el)
        sleeve = limb_tube([sh + [0, -0.01, 0], lerp3(sh, el, 0.5), el, lerp3(el, wr - fd * 0.02, 0.5), wr - fd * 0.02], [0.040, 0.045, 0.046, 0.054, 0.062],
                           joints=[el], spacing=0.045, joint_spacing=0.02, joint_zone=0.05, sides=9, cap=None, up=(0, 1, 0))
        p.add(f"sleeve_{nm}", sleeve.noised(0.003, 12, 2, seed=20 + s), "EH_Cloth", None, skin=ARM_SKIN[nm], uv_scale=2,
              tint=lambda P: (0.55 + 0.45 * smoothstep(0.66, 0.84, P[:, 1]))[:, None] * np.array([1.0, 0.9, 0.84]))
        p.add(f"cuff_{nm}", g.torus(0.0635, 0.0085, 16, 5).aimed(fd, wr - fd * 0.018), "EH_Bronze", f"hand_{nm}")
        inner = g.lathe(np.array([(0.030, 0.0), (0.056, 0.0), (0.056, 0.002), (0.030, 0.002)]), 14, crease=40).aimed(fd, wr - fd * 0.018)
        p.add(f"cuff_inner_{nm}", inner, "EH_Cloth", f"hand_{nm}", lod1=None, tint=lambda P: np.full(len(P), 0.18))
    # left hand: open, relaxed, hanging; fingers curl a little toward the palm (medial, -X for the left hand)
    wl = WL0
    palm = g.superellipsoid((0.013, 0.030, 0.026), 0.55, 0.6, 3, 8).translated(wl[0], wl[1] - 0.030, wl[2] + 0.004)
    fing = []
    for i, zz in enumerate((-0.0155, -0.0052, 0.0052, 0.0155)):
        L = 0.040 - 0.004 * abs(i - 1.5)
        y0 = wl[1] - 0.052
        fing.append(g.tube([(wl[0] - 0.002, y0, wl[2] + zz), (wl[0] - 0.006, y0 - L * 0.55, wl[2] + zz + 0.001), (wl[0] - 0.016, y0 - L * 0.95, wl[2] + zz + 0.004)],
                           [0.0068, 0.0060, 0.0048], sides=5, samples=1, cap="round", cap_steps=1))
    thumb = g.tube([(wl[0] - 0.004, wl[1] - 0.020, wl[2] + 0.028), (wl[0] - 0.012, wl[1] - 0.038, wl[2] + 0.034), (wl[0] - 0.020, wl[1] - 0.054, wl[2] + 0.034)],
                   [0.0085, 0.0075, 0.0055], sides=5, samples=1, cap="round", cap_steps=1)
    p.add("hand_L", merge([palm, thumb] + fing), "EH_Leather", "wrist_L", uv_scale=2)
    # right hand: fist around the staff (rings wrap the staff axis)
    wr = WR0
    ax = -A_S
    fist = g.superellipsoid((0.030, 0.026, 0.027), 0.6, 0.6, 4, 9).translated(wr[0] + 0.001, wr[1] + 0.001, wr[2] + 0.022)
    rings_ = [g.torus(0.0200, 0.0068, 9, 4).aimed(ax, wr + A_S * dy + [0, 0, 0.0]) for dy in (-0.020, -0.007, 0.006, 0.019)]
    thumb = g.tube([wr + [0.026, 0.018, 0.026], wr + [0.014, 0.034, 0.022], wr + [0.004, 0.034, 0.012]], [0.0092, 0.0080, 0.0062], sides=5, samples=1, cap="round", cap_steps=1)
    p.add("hand_R", merge([fist, thumb] + rings_), "EH_Leather", "wrist_R", uv_scale=2)


# ======================================================================================= head & mitre
def head(p: Piece):
    cx, cy, cz = 0.0, 1.044, 0.010
    skull = g.superellipsoid((0.051, 0.076, 0.057), 0.85, 0.95, 6, 12).translated(cx, cy, cz)
    skull = g.warp(skull, lambda P: np.column_stack([P[:, 0] * (1 - 0.34 * smoothstep(cy + 0.01, cy - 0.072, P[:, 1])), P[:, 1],
                                                     P[:, 2] + 0.006 * smoothstep(cy - 0.03, cy - 0.072, P[:, 1])]), 60)
    nose = g.superellipsoid((0.0085, 0.020, 0.012), 0.6, 0.6, 3, 7).rotated(-18, 0, 0).translated(0, cy - 0.004, cz + 0.054)
    brow = g.rounded_box((0.088, 0.014, 0.028), 0.0065, 1).translated(0, cy + 0.028, cz + 0.040)
    brow = g.warp(brow, lambda P: np.column_stack([P[:, 0], P[:, 1] - 0.006 * (np.abs(P[:, 0]) / 0.044) ** 2, P[:, 2] - 0.012 * (np.abs(P[:, 0]) / 0.044) ** 2]), 60)
    chin = g.superellipsoid((0.016, 0.013, 0.018), 0.6, 0.6, 3, 7).translated(0, cy - 0.064, cz + 0.038)
    lip = g.tube([(-0.016, cy - 0.042, cz + 0.046), (0, cy - 0.045, cz + 0.054), (0.016, cy - 0.042, cz + 0.046)], 0.0036, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
    ears = [g.superellipsoid((0.0065, 0.016, 0.012), 0.6, 0.6, 3, 6).translated(s * 0.046, cy + 0.002, cz - 0.004) for s in (-1, 1)]
    p.add("face", merge([skull, nose, brow, chin, lip] + ears), "EH_Skin", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.62))
    eyes = [g.superellipsoid((0.0100, 0.0048, 0.0052), 0.7, 0.7, 3, 6).rotated(0, 0, s * -8).translated(s * 0.0215, cy + 0.012, cz + 0.049) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "EH_EmberVein", "head", lod1="keep", bake=False)
    neck = limb_tube([(0, 0.925, 0.006), (0, 0.96, 0.010), (0, 0.995, 0.012), (0, 1.03, 0.012)], [0.034, 0.031, 0.030, 0.030], joints=[(0, 0.985, 0.011)], spacing=0.04,
                     joint_spacing=0.02, joint_zone=0.03, sides=8, cap=None, up=(0, 0, 1))
    p.add("neck", neck, "EH_Skin", None, skin=NECK_SKIN, uv_scale=2, lod1=None, tint=lambda P: np.full(len(P), 0.62))
    mitre(p)


# ---- mitre geometry: an ogive shell (oval section), a deep diagonal slit cut into the front
MIT_Y = np.array([1.066, 1.070, 1.100, 1.160, 1.220, 1.275, 1.315, 1.333, 1.3358])
MIT_R = np.array([0.090, 0.090, 0.092, 0.088, 0.074, 0.052, 0.026, 0.008, 0.0005])
MIT_ZS = 0.72                                      # depth / width
MIT_LIFT = 0.012                                   # the whole mitre sits this much above its nominal frame
SLIT_ANG = math.radians(38.0)
SLIT_C = (0.0, 1.204)
SLIT_HALF_LEN, SLIT_HALF_W, SLIT_DEPTH = 0.104, 0.0275, 0.036


def mit_r(y):
    from scipy.interpolate import PchipInterpolator
    return PchipInterpolator(MIT_Y, MIT_R)(np.clip(y, MIT_Y[0], MIT_Y[-1]))


def slit_depth(x, y, z):
    """Groove depth (0..SLIT_DEPTH) at a NOMINAL mitre-surface point: V-groove along the 38 degree centreline, round capped, running
    around the flank (~25 %) and fading toward the back."""
    x, y, z = np.asarray(x, float), np.asarray(y, float), np.asarray(z, float)
    dx, dy = x - SLIT_C[0], y - SLIT_C[1]
    d = np.abs(dx * math.sin(SLIT_ANG) + dy * math.cos(SLIT_ANG))
    s = dx * math.cos(SLIT_ANG) - dy * math.sin(SLIT_ANG)
    de = np.hypot(d, np.maximum(np.abs(s) - SLIT_HALF_LEN, 0.0))
    prof = np.clip((SLIT_HALF_W - de) / 0.0115, 0, 1)
    prof = prof * prof * (3 - 2 * prof)
    zn = z / MIT_ZS
    cth = zn / np.maximum(np.hypot(x, zn), 1e-6)
    front = smoothstep(-0.55, -0.05, cth)
    return SLIT_DEPTH * prof * front


MIT_YS = [1.066, 1.080, 1.098] + [round(1.108 + 0.0085 * i, 4) for i in range(24)] + [1.314, 1.326, 1.333, 1.3358]


def mitre_shell(K=64):
    # angles: dense across the front (+-70 deg), sparse behind
    th = np.radians(np.concatenate([np.linspace(-72, 72, 48, endpoint=False), np.linspace(72, 288, K - 48, endpoint=False)]))
    th = np.sort(np.mod(th, TAU))
    rings, deps = [], []
    for y in MIT_YS:
        r = float(mit_r(y))
        x0, z0 = r * np.sin(th), MIT_ZS * r * np.cos(th)
        dep = slit_depth(x0, y, z0)
        nx, nz = x0 / (r * r), z0 / ((MIT_ZS * r) ** 2)                     # push the groove in along the section's inward normal
        nn = np.maximum(np.hypot(nx, nz), 1e-9)
        rings.append(np.stack([x0 - dep * nx / nn, np.full(len(th), y), z0 - dep * nz / nn], 1))
        deps.append(dep)
    rings = np.stack(rings)
    dep = np.stack(deps)
    dep = np.concatenate([dep, dep[:, :1]], axis=1).reshape(-1)          # closed loft duplicates the seam column
    uv = np.stack([dep, np.zeros_like(dep)], 1)
    return g.loft(rings, closed=True, crease=62, shade=False, uv=uv)


def mitre(p: Piece):
    def add(name, mesh, *args, **kw):
        p.add(name, mesh.translated(0, MIT_LIFT, 0), *args, **kw)

    shell = mitre_shell()
    from scipy.spatial import cKDTree
    tree = cKDTree(shell.P)
    dep_v = shell.UV[:, 0].copy()
    shell_m = g.Mesh(shell.P, shell.F, shell.P[:, [0, 1]] / 0.25, crease=88).shade(88)
    RED = np.array([1.0, 0.27, 0.20])

    def mit_tint(Q):                                    # the groove floor is oxblood: tint the bronze by the groove depth (smooth, no ragged seam)
        _, ix = tree.query(np.asarray(Q) - [0, MIT_LIFT, 0])
        t = smoothstep(0.35, 0.80, dep_v[ix] / SLIT_DEPTH)[:, None]
        return 1.0 - t * (1.0 - RED)
    add("mitre_shell", shell_m, "EH_Bronze", "head", tint=mit_tint)
    # bronze lips along both groove edges
    lips = []
    for sgn in (-1, 1):
        pts = []
        for s in np.linspace(-SLIT_HALF_LEN - 0.012, SLIT_HALF_LEN + 0.012, 22):
            ex = max(abs(s) - SLIT_HALF_LEN, 0.0)
            off = SLIT_HALF_W * 1.02 * math.sqrt(max(0.0, 1 - (ex / (SLIT_HALF_W * 1.0)) ** 2)) if ex < SLIT_HALF_W else 0.0
            x = SLIT_C[0] + s * math.cos(SLIT_ANG) + sgn * off * math.sin(SLIT_ANG)
            y = SLIT_C[1] - s * math.sin(SLIT_ANG) + sgn * off * math.cos(SLIT_ANG)
            r = float(mit_r(y))
            if abs(x) > r * 0.985 or off == 0.0:
                if pts and len(pts) > 1:
                    lips.append(g.tube(pts, 0.0050, sides=4, samples=1, cap="round", cap_steps=1, smooth=True))
                pts = []
                continue
            z = MIT_ZS * r * math.sqrt(max(0.0, 1 - (x / r) ** 2))
            pts.append((x, y, z + 0.001))
        if len(pts) > 1:
            lips.append(g.tube(pts, 0.0050, sides=4, samples=1, cap="round", cap_steps=1, smooth=True))
    if lips:
        add("mitre_slit_lips", merge(lips), "EH_Bronze", "head", lod1=None)
    # base band with rivets, apex cap, side piping (bright edge that survives on dark squares)
    band = g.lathe(np.array([(0.0905, 1.062), (0.0955, 1.067), (0.0965, 1.090), (0.0925, 1.098), (0.0905, 1.094), (0.0905, 1.062)]), 40, crease=40).scaled(1, 1, MIT_ZS)
    add("mitre_band", band, "EH_Bronze", "head")
    rv = [math.radians(a) for a in np.linspace(-80, 80, 11)]
    rpos = [(0.0968 * math.sin(a), 1.0785, 0.0968 * MIT_ZS * math.cos(a)) for a in rv]
    rn = [(math.sin(a) / 1.0, 0, math.cos(a) / MIT_ZS) for a in rv]
    add("mitre_rivets", g.instances(g.dome(0.0060, 0.0050, 6, 1), rpos, rn), "EH_Bronze", "head", lod1=None)
    add("mitre_apex", g.superellipsoid((0.012, 0.014, 0.012), 0.9, 0.9, 4, 8).translated(0, 1.337, 0), "EH_Bronze", "head")
    for sgn in (-1, 1):
        seg, segs = [], []
        for y in np.linspace(1.100, 1.322, 34):
            r = float(mit_r(y))
            if float(slit_depth(sgn * r, y, 0.0)) > 0.0008:
                if len(seg) > 1:
                    segs.append(seg)
                seg = []
                continue
            seg.append((sgn * (r + 0.003), y, 0.0))
        if len(seg) > 1:
            segs.append(seg)
        for sg in segs:
            if len(sg) > 1:
                add(f"mitre_piping_{'R' if sgn < 0 else 'L'}{len(p.parts)}", g.tube(sg, 0.0048, sides=4, samples=1, cap="round", cap_steps=1, smooth=len(sg) > 2), "EH_Bronze", "head", lod1=None)
    # lappets hang behind the ears over the shoulders
    for sgn, nm in ((1, "L"), (-1, "R")):
        rows, cols = 9, 3
        grid = []
        for i in range(rows):
            t = i / (rows - 1)
            y = 1.082 - 0.20 * t
            w = 0.052 - 0.006 * t
            z = -0.062 - 0.060 * smoothstep(0.0, 1.0, t) - 0.01 * math.sin(t * 5 + sgn)
            xc = sgn * (0.054 + 0.004 * t)
            row = [(xc + u * w + sgn * 0.0 , y, z - 0.012 * abs(u)) for u in (-0.5, 0.0, 0.5)]
            grid.append(row)
        G = np.array(grid)[::-1]
        lap = g.loft(G[:, ::-1], closed=False, crease=70, v_tile=0.25, u_tile=0.25)
        add(f"lappet_{nm}", lap, "EH_Cloth", None, skin=LAP_SKIN, uv_scale=2, tint=lambda Q: (0.7 + 0.3 * smoothstep(0.9, 1.08, Q[:, 1]))[:, None] * np.array([1.18, 0.92, 0.8]))
        tip = g.tube([(sgn * 0.058, 0.883, -0.123), (sgn * 0.058, 0.872, -0.125), (sgn * 0.058, 0.864, -0.127)], [0.012, 0.010, 0.0], sides=5, samples=1, cap=None, smooth=False)
        add(f"lappet_tip_{nm}", tip, "EH_Bronze", None, skin=LAP_SKIN, lod1=None)


# ======================================================================================= staff, chain, censer
def on_staff(y):
    """Point on the staff axis at height y."""
    t = (S_TOP[1] - y) / (S_TOP[1] - S_FOOT[1])
    return S_TOP + (S_FOOT - S_TOP) * t


def staff(p: Piece):
    ys = [0.226, 0.45, 0.72, 1.0, 1.28]
    shaft = g.tube([on_staff(y) for y in ys], [0.0235, 0.0215, 0.0195, 0.0172, 0.0155], sides=8, samples=2, cap=None, up=(1, 0, 0))
    p.add("staff_shaft", shaft.noised(0.0016, 30, 2, seed=40), "EH_Bronze", "weapon", tint=lambda P: np.full(len(P), 0.62))
    x = S_TOP[0]
    crook = g.tube([S_TOP + V(0, -0.01, 0), (x, 1.335, 0.136), (x, 1.372, 0.158), (x, 1.396, 0.192), (x, 1.398, 0.232), (x, 1.378, 0.262), (x, 1.352, 0.270)],
                   [0.0155, 0.0160, 0.0165, 0.0158, 0.0138, 0.0118, 0.0085], sides=8, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("staff_crook", crook.noised(0.0014, 30, 2, seed=41), "EH_Bronze", "weapon")
    p.add("crook_tip", g.superellipsoid((0.011, 0.011, 0.011), 0.9, 0.9, 3, 7).translated(x, 1.348, 0.272), "EH_Bronze", "weapon", lod1=None)
    wraps = [g.torus(0.0215, 0.0042, 10, 4).aimed(-A_S, on_staff(0.865 + 0.0125 * i)) for i in range(7)]
    p.add("staff_wraps", merge(wraps), "EH_Leather", "weapon", uv_scale=2, lod1=None)
    foot = g.lathe(np.array([(0.0, 0.0), (0.026, 0.0), (0.029, 0.026), (0.024, 0.066), (0.0215, 0.096), (0.0, 0.096)]), 12, crease=45).aimed(-A_S, on_staff(0.222) + V(0, 0.0, 0.0))
    p.add("staff_foot", foot, "EH_Steel", "weapon")
    knops = [g.torus(0.0215 - 0.0003 * i, 0.0068, 12, 4).aimed(-A_S, on_staff(y)) for i, y in enumerate((0.45, 0.62, 1.04, 1.18))]
    knops.append(g.superellipsoid((0.025, 0.020, 0.025), 0.6, 0.6, 3, 8).translated(*on_staff(1.255)))
    p.add("staff_knops", merge(knops), "EH_Bronze", "weapon")


def censer(p: Piece):
    cx, cz = CX, CZ
    S = lambda m: m.translated(-CX, -CH2[1], -CZ).scaled(CEN_S).translated(CX, CH2[1], CZ)      # noqa: E731
    pivot = tuple(PIV)
    chain = g.tube([pivot, (cx, 1.35, cz), tuple(CH1)], 0.0058, sides=5, samples=4, cap="round", cap_steps=1, radius_fn=lambda t: 0.62 + 0.38 * abs(math.sin(t * 40)))
    junc = g.torus(0.014, 0.0035, 10, 4).rotated(90, 0, 0).translated(*CH1)
    hook = g.torus(0.013, 0.0032, 10, 4).rotated(0, 0, 90).translated(*pivot)
    p.add("chain", merge([chain, junc, hook]), "EH_Steel", None, skin=CHAIN_SKIN)
    ch3 = []
    for i in range(3):
        a_ = math.radians(i * 120 + 30)
        ch3.append(g.tube([tuple(CH1), (cx + 0.018 * math.sin(a_), 1.262, cz + 0.018 * math.cos(a_)), (cx + 0.034 * math.sin(a_), 1.208, cz + 0.034 * math.cos(a_))],
                          0.0046, sides=4, samples=3, cap="round", cap_steps=1, radius_fn=lambda t: 0.62 + 0.38 * abs(math.sin(t * 30))))
    p.add("chains3", merge(ch3), "EH_Steel", None, skin=CHAIN_SKIN, lod1=None)
    lidring = g.torus(0.042, 0.0050, 14, 4).translated(cx, 1.204, cz)
    lid = g.lathe(np.array([(0.0, 1.250), (0.010, 1.246), (0.024, 1.236), (0.046, 1.214), (0.062, 1.192), (0.066, 1.186), (0.0, 1.186)]), 18, crease=45).translated(cx, 0, cz)
    vents = g.instances(g.dome(0.0085, 0.004, 6, 1), [(cx + 0.040 * math.sin(a_), 1.222, cz + 0.040 * math.cos(a_)) for a_ in np.arange(6) * TAU / 6],
                        [(math.sin(a_), 1.1, math.cos(a_)) for a_ in np.arange(6) * TAU / 6])
    p.add("censer_lid", S(merge([lid.noised(0.0012, 40, 2, seed=50), lidring])), "EH_Bronze", "cape_2")
    p.add("censer_vents", S(vents), "EH_Steel", "cape_2", lod1=None)
    ribs = []
    for i in range(8):
        t = g.tube([(0.018, 1.066, 0), (0.052, 1.086, 0), (0.0685, 1.128, 0), (0.060, 1.166, 0), (0.046, 1.186, 0)], [0.0068, 0.0072, 0.0076, 0.0070, 0.0066],
                   sides=5, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 0, 1))
        ribs.append(t.rotated(0, i * 45, 0))
    p.add("censer_ribs", S(merge(ribs).translated(cx, 0, cz)), "EH_Bronze", "cape_2")
    rings = [g.torus(0.0690, 0.0058, 18, 4).translated(cx, 1.128, cz), g.torus(0.0545, 0.0050, 16, 4).translated(cx, 1.087, cz), g.torus(0.0625, 0.0050, 16, 4).translated(cx, 1.166, cz)]
    p.add("censer_rings", S(merge(rings)), "EH_Bronze", "cape_2")
    cup = g.lathe(np.array([(0.0, 1.046), (0.020, 1.050), (0.034, 1.062), (0.030, 1.072), (0.0, 1.072)]), 14, crease=45).translated(cx, 0, cz)
    drop = g.tube([(cx, 1.048, cz), (cx, 1.026, cz), (cx, 1.012, cz)], [0.008, 0.007, 0.0], sides=5, samples=1, cap=None, smooth=False)
    p.add("censer_base", S(merge([cup, drop])), "EH_Steel", "cape_2")
    studs = g.instances(g.dome(0.0058, 0.005, 6, 1), [(cx + 0.0695 * math.sin(a_), 1.128, cz + 0.0695 * math.cos(a_)) for a_ in np.arange(8) * TAU / 8],
                        [(math.sin(a_), 0, math.cos(a_)) for a_ in np.arange(8) * TAU / 8])
    p.add("censer_studs", S(studs), "EH_Steel", "cape_2", lod1=None)
    coals = g.superellipsoid((0.046, 0.042, 0.046), 0.8, 0.85, 4, 10).translated(cx, 1.124, cz).noised(0.006, 18, 2, seed=51)
    p.add("coals", S(coals), "EH_Ember", "cape_2", lod1="keep", bake=False)


# ======================================================================================= animation
class BAnim(Animator):
    """Animator + (a) skirt pins: skirt_* bones are blended toward their rest WORLD pose so the hem stays planted on the plinth while the
    body bobs / lunges / kneels, and (b) a gravity-hung censer: `hang(t)` is the world direction pivot -> censer; `top` is rotated so the
    chain follows it whatever the staff does (cape_1/cape_2 then lag it with the accel-driven spring)."""

    def __init__(self, rig):
        super().__init__(rig)
        self.hang = None
        self.pins = {"skirt_1": 0.10, "skirt_2": 0.55, "skirt_3": 1.0}

    def pose(self, t, overrides=True):
        ctx = super().pose(t, overrides)
        sk = self.sk
        for b, k in self.pins.items():
            if k <= 0:
                continue
            i = sk.ix[b]
            ip = sk.parent[i]
            Pw = ctx.Pw[i] + (sk.rest[i] - ctx.Pw[i]) * k
            qc = quat_from_mat(ctx.Rw[i])
            qi = np.array([0.0, 0.0, 0.0, 1.0])
            if np.dot(qc, qi) < 0:
                qi = -qi
            Rw = mat_from_quat(slerp(qc, qi, k))
            Rp, Pp = ctx.Rw[ip], ctx.Pw[ip]
            ctx.R[i] = Rp.T @ Rw
            ctx.T[i] = Rp.T @ (Pw - Pp) - sk.off[i]
        if self.hang is not None:
            it = sk.ix["top"]
            ip = sk.parent[it]
            d = nrm(np.asarray(self.hang(t), float))
            ctx.R[it] = ctx.Rw[ip].T @ rot_between(V(0, -1, 0), d)
        ctx.fk()
        return ctx


def _anim(rig):
    a = BAnim(rig)
    M.plant_feet(a)
    a.secondary(["cape_1", "cape_2"], driver="top", freq=2.3, zeta=0.34, follow=1.0, accel=0.045, max_deg=16, decay=0.85)
    return a


def _z():
    return V(0, 0, 0)


def swing(ax_deg, az_deg):
    """Chain direction for a hang angle toward +X (character's left) / +Z (forward), degrees."""
    ax, az = math.radians(ax_deg), math.radians(az_deg)
    return nrm(V(math.sin(ax), -math.cos(ax) * math.cos(az), math.sin(az)))


def cone(alpha_deg, phi_deg):
    """Chain direction on a cone of half angle alpha about the vertical; phi from +X toward +Z."""
    al, ph = math.radians(alpha_deg), math.radians(phi_deg)
    return V(math.sin(al) * math.cos(ph), -math.cos(al), math.sin(al) * math.sin(ph))


def _hand(a, pos, dirs, world=None, pole=(-0.5, -1.0, -0.25)):
    """Right hand on the staff: pos = absolute chest-space (or world, where `world` is 1) point of the grip; dirs = staff axis (grip -> foot)."""
    P = pos if callable(pos) else Curve(pos)
    D = dirs if callable(dirs) else Curve(dirs)
    wd = (lambda t: 0.0) if world is None else (world if callable(world) else step_signal(world))
    a.goal("ik_hand_R", ("arm_R", "hand_R", "wrist_R"),
           spaces=(("world", Fn(lambda t: wd(t))), ("chest", Fn(lambda t: 1.0 - wd(t)))), pole=pole)
    gr = next(g_ for g_ in a.goals if g_.name == "ik_hand_R")
    gr.pos = M.abs_pos(WR0, P)
    gr.rot = M.aim(A_S, D)
    return P, D


# ---------------------------------------------------------------------------------------------- Idle
def clip_idle(rig):
    a = _anim(rig)
    T = 3.6
    M.idle(a, period=T, breath=1.0, shift=0.9, sway=0.008, look=0.8, hands=False)
    _hand(a, [(0, WR0)], [(0, A_S)], world=[(0, 1.0)])
    a.rot("arm_L", Wave(V(-1.2, 0, 0.8), 1 / T, 0.4))
    a.rot("hand_L", Wave(V(-2.0, 0, 0), 1 / T, 0.5))
    a.rot("wrist_L", Wave(V(-3.0, 0, 0), 1 / T, 0.6))
    a.hang = Fn(lambda t: swing(5.5 * math.sin(TAU * 2 * t / T + 0.4), 4.0 * math.sin(TAU * t / T + 1.2) + 1.0 * math.sin(TAU * 3 * t / T)))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- Move
def clip_move(rig):
    a = _anim(rig)
    T = 1.0
    M.biped_gait(a, T, stride=0.035, lift=0.045, duty=0.6, bob=0.014, sway=0.010, roll=2.4, twist=3.5, lean=3.0, arm_swing=(6, 0), elbow=8,
                 toe_off=18, strike=-5, head_stab=0.5)

    def tap(t):                                                     # staff lifts and re-plants ahead on every step
        tt = t % 0.5
        if 0.10 < tt < 0.34:
            s = (tt - 0.10) / 0.24
            return math.sin(math.pi * s) ** 1.4
        return 0.0
    P = Fn(lambda t: WR0 + V(0.0, 0.03, 0.0) * tap(t) + V(0.0, 0.0, 0.012) * math.sin(TAU * t / T * 2) * 0.0 + V(0, 0, 0.022) * (smoothstep(0.10, 0.34, t % 0.5) - 0.5) * 0)
    _hand(a, P, [(0, A_S), (0.25, nrm(V(0.0, -1.0, 0.075)), "in_out_cubic"), (0.5, A_S, "in_out_cubic"), (0.75, nrm(V(0.0, -1.0, 0.075)), "in_out_cubic"), (1.0, A_S, "in_out_cubic")],
          world=lambda t: 0.8)
    a.rot("arm_L", Wave(V(0.0, 0, 0.6), 1 / T, 0.1))
    a.rot("wrist_L", Wave(V(5, 0, 0), 1 / T, 0.30))
    a.hang = Fn(lambda t: swing(6.0 * math.sin(TAU * t / T + 1.0), -9.0 * math.sin(TAU * 2 * t / T + 0.5) + 3.0))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- HitReact
def clip_hit(rig):
    a = _anim(rig)
    T = 0.5
    z = _z()
    a.pos("body", Curve([(0, z), (0.08, V(0, -0.026, -0.060), "out_cubic"), (0.20, V(0, -0.010, -0.022), "in_out_cubic"), (0.32, V(0, -0.012, 0.008), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.08, V(-8, 2, 3), "out_cubic"), (0.20, V(2, -1, -1), "in_out_cubic"), (0.32, V(-1, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.095, V(-8, 3, 2), "out_cubic"), (0.22, V(3, -2, 0), "in_out_cubic"), (0.34, V(-1.2, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.11, V(-10, 4, 3), "out_cubic"), (0.24, V(3, -3, -1), "in_out_cubic"), (0.36, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.12, V(-12, 6, 4), "out_cubic"), (0.26, V(4, -4, -1), "in_out_cubic"), (0.38, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.13, V(-14, 8, 5), "out_cubic"), (0.28, V(5, -4, -2), "in_out_cubic"), (0.40, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.10, V(0, 0, 5), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.10, V(0, 0, -5), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("arm_L", Curve([(0, z), (0.10, V(10, 0, 8), "out_cubic"), (0.26, V(-4, 0, 2), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.12, V(8, 0, 0), "out_cubic"), (0.28, V(-10, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    _hand(a, [(0, WR0), (0.09, WR0 + V(0.012, 0.018, -0.045), "out_cubic"), (0.22, WR0 + V(-0.004, -0.006, 0.012), "in_out_cubic"), (T, WR0, "in_out_cubic")],
          [(0, A_S), (0.09, nrm(V(0.0, -1.0, -0.12)), "out_cubic"), (0.22, nrm(V(0.0, -1.0, 0.09)), "in_out_cubic"), (T, A_S, "in_out_cubic")], world=[(0, 1.0)])
    a.hang = Curve([(0, V(0, -1, 0)), (0.10, swing(8, 34), "out_cubic"), (0.26, swing(-3, -16), "in_out_cubic"), (0.40, swing(0, 6), "in_out_cubic"), (T, V(0, -1, 0), "in_out_cubic")])
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.1, V(0, 0, -0.012), "out_cubic"), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.25)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Victory
def clip_victory(rig):
    a = _anim(rig)
    T = 2.0
    z = _z()
    a.pos("body", Curve([(0, z), (0.18, V(0, -0.016, 0), "in_out_cubic"), (0.62, V(0, 0.016, 0.008), ("spring", 0.2, 1.5)), (T, V(0, 0.012, 0.008), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.18, V(3, 0, 0)), (0.62, V(-3, -3, -1), "out_cubic"), (T, V(-2, -2, -1), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.18, V(4, 0, 0)), (0.66, V(-6, -3, 0), ("spring", 0.15, 1.5)), (T, V(-5, -2, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.18, V(5, 0, 0)), (0.68, V(-8, -4, 0), ("spring", 0.15, 1.5)), (T, V(-7, -3, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.7, V(-6, 4, 0), "out_cubic"), (T, V(-5, 3, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.72, V(-10, 6, 0), ("spring", 0.15, 1.5)), (T, V(-9, 5, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.20, V(0, 0, 2), "in_out_cubic"), (0.70, V(0, 0, -8), "out_cubic"), (T, V(0, 0, -8))]))
    a.rot("clavicle_L", Curve([(0, z), (0.70, V(0, 0, 6), "out_cubic"), (T, V(0, 0, 6))]))
    # the staff is hoisted overhead, planted taller: the grip rises and the crook leans over
    P_UP, D_UP = WR0 + V(0.02, 0.19, 0.10), nrm(V(0.0, -0.95, -0.30))
    _hand(a, [(0, WR0), (0.20, WR0 + V(0, -0.012, 0.0), "in_out_cubic"), (0.66, P_UP, ("spring", 0.10, 1.5)), (T, P_UP + V(0, 0.010, 0), "in_out_cubic")],
          [(0, A_S), (0.20, A_S, "in_out_cubic"), (0.66, D_UP, ("spring", 0.12, 1.5)), (T, D_UP, "in_out_cubic")])
    a.rot("arm_L", Curve([(0, z), (0.24, V(6, 0, 4), "in_out_cubic"), (0.80, V(-18, 0, 30), ("spring", 0.12, 1.5)), (T, V(-16, 0, 28), "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.80, V(-26, 0, 0), ("spring", 0.12, 1.5)), (T, V(-24, 0, 0), "in_out_cubic")]))
    a.rot("wrist_L", Curve([(0, z), (0.84, V(-28, 0, 0), "out_cubic"), (T, V(-26, 0, 0))]))
    # censer: spun in a wide circle over the head as the staff goes up, then damped
    def vic_hang(t):
        if t < 0.55:
            return swing(4.0 * math.sin(t * 6), 3.0)
        u = t - 0.55
        al = 6.0 + 58.0 * math.exp(-u / 0.70) * smoothstep(0.0, 0.22, u)
        phi = 90.0 + 360.0 * (0.42 * u + 0.5 * (1 - math.exp(-u / 0.55)) * 0.0) * 1.0 * 1.0
        return cone(al, phi)
    a.hang = Fn(vic_hang)
    for nm in ("foot_L", "foot_R"):
        M.set_foot(a, nm, rot=Curve([(0, z), (0.25, z), (0.6, V(5, 0, 0), "out_cubic"), (T, V(5, 0, 0))]),
                   pos=Curve([(0, z), (0.25, z), (0.6, V(0, 0.005, 0), "out_cubic"), (T, V(0, 0.005, 0))]))
    a.rot("chest", Wave(V(-0.6, 0, 0), 1.0, 0.0) * step_signal([(0.9, 0), (1.3, 1)]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Taunt
def clip_taunt(rig):
    """The staff tips forward so the censer whirls clear of the mitre, two fast circles, then it plants and the left hand points at the foe."""
    a = _anim(rig)
    T = 1.5
    z = _z()
    P_W, D_W = WR0 + V(0.03, 0.17, 0.10), nrm(V(0.0, -0.95, -0.30))
    _hand(a, [(0, WR0), (0.22, P_W, "out_cubic"), (0.80, P_W + V(0, 0.01, 0), "in_out_cubic"), (1.10, WR0 + V(0, 0.01, 0.02), "in_out_cubic"), (T, WR0, "in_out_cubic")],
          [(0, A_S), (0.22, D_W, "out_cubic"), (0.80, D_W, "in_out_cubic"), (1.10, nrm(V(0.0, -1.0, 0.05)), "in_out_cubic"), (T, A_S, "in_out_cubic")])

    def tn_hang(t):
        if t < 0.18:
            return swing(3.0, 3.0)
        u = (t - 0.18)
        al = 8.0 + 62.0 * smoothstep(0.0, 0.18, u) * (1.0 - 0.9 * smoothstep(0.62, 0.95, u))
        phi = 90.0 + 360.0 * 2.0 * (u / 0.75) ** 1.0 if u < 0.75 else 90.0 + 360.0 * 2.0
        # after the swirl the chain settles with a damped plane swing
        if u > 0.80:
            s = u - 0.80
            return swing(0.0, 24.0 * math.exp(-s / 0.30) * math.cos(TAU * s / 0.9))
        return cone(al, phi)
    a.hang = Fn(tn_hang)
    # body: leans into the swirl, then rocks back and bows (the slit points at the foe) while the left hand points
    a.pos("body", Curve([(0, z), (0.30, V(0.004, -0.008, 0.0), "in_out_cubic"), (0.90, V(-0.004, 0.012, 0.030), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.40, V(-2, 0, 3), "in_out_cubic"), (1.00, V(-2, 0, -3), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.22, V(-3, 0, 0), "out_cubic"), (0.86, V(-4, -5, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.22, V(-4, 0, 0), "out_cubic"), (0.86, V(-5, -6, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.30, V(-3, 0, 2), "out_cubic"), (0.80, V(6, -4, 0), "in_out_cubic"), (1.05, V(7, -4, 0)), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.30, V(-6, 0, 4), "out_cubic"), (0.80, V(10, -5, 0), "in_out_cubic"), (1.05, V(11, -5, 0)), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.9, V(0, 0, 5), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("arm_L", Curve([(0, z), (0.50, V(4, 0, 4), "in_out_cubic"), (0.92, V(-82, 0, -4), "out_cubic"), (1.12, V(-84, 0, -4), {"tan": "flat"}), (T, z, "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.50, V(0, 0, 0)), (0.92, V(-12, 0, 0), "out_cubic"), (1.12, V(-12, 0, 0)), (T, z, "in_out_cubic")]))
    a.rot("wrist_L", Curve([(0, z), (0.92, V(8, 0, 0), ("spring", 0.2, 1.5)), (1.12, V(6, 0, 0)), (T, z, "in_out_cubic")]))
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.30, V(0, 0, -0.030), "in_out_cubic"), (1.1, V(0, 0, -0.030)), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.0)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Surrender
def clip_surrender(rig):
    """Stagger, the staff slips from the grip (free fall, two bounces, lies on the plinth with the censer clattering beside it), a one-knee
    KNEEL (left foot planted, right knee on the plinth, shin and instep flat), the torso folds, the mitre bows, hands open on the thighs."""
    a = _anim(rig)
    T = 2.4
    z = _z()
    sk = a.sk
    L1 = float(np.linalg.norm(sk.rest[sk.ix["shin_R"]] - sk.rest[sk.ix["thigh_R"]]))
    L2 = float(np.linalg.norm(sk.rest[sk.ix["foot_R"]] - sk.rest[sk.ix["shin_R"]]))
    KNEE_Y = 0.268                                  # kneeling knee axis above world 0 (plinth top 0.22 + knee cap radius)
    DROP = JOINTS["hip_L"][1] - (KNEE_Y + L1)
    PZ = 0.04
    a.pos("body", Curve([(0, z), (0.30, V(0, -0.010, -0.035), "out_cubic"), (0.55, V(0, -0.018, -0.018), "in_out_cubic"), (1.38, V(0, -DROP, PZ), "in_out_cubic"),
                         (1.60, V(0, -DROP + 0.006, PZ), "out_cubic"), (1.95, V(0, -DROP, PZ), "in_out_cubic"), (T, V(0, -DROP - 0.004, PZ), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.30, V(-6, 0, 0), "out_cubic"), (0.55, z, "in_out_cubic"), (1.38, V(3, 0, -2), "in_out_cubic"), (T, V(4, 0, -2), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.30, V(-3, 0, 0), "out_cubic"), (0.9, V(3, 0, 0), "in_out_cubic"), (1.6, V(8, 0, 0), "in_out_cubic"), (T, V(9, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.30, V(-2, 0, 0), "out_cubic"), (0.9, V(2, 0, 0), "in_out_cubic"), (1.7, V(7, 0, 0), "in_out_cubic"), (T, V(8, 0, 0.0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.30, V(-4, 0, 0), "out_cubic"), (1.0, V(6, 0, 0), "in_out_cubic"), (1.75, V(14, 0, 0), "in_out_cubic"), (T, V(15, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.30, V(-10, 0, 0), "out_cubic"), (1.0, V(8, 0, 0), "in_out_cubic"), (1.75, V(22, 2, 3), "in_out_cubic"), (T, V(24, 2, 4), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (1.0, V(0, 0, 4), "in_out_cubic"), (T, V(0, 0, 6))]))
    a.rot("clavicle_L", Curve([(0, z), (1.0, V(0, 0, -4), "in_out_cubic"), (T, V(0, 0, -6))]))
    # right hand: loosens, opens (the staff leaves at 0.45), drops to the thigh
    HR = V(-0.15, 0.70, 0.17)
    _hand(a, [(0, WR0), (0.20, WR0 + V(0, -0.02, 0.01), "in_out_cubic"), (0.45, WR0 + V(0.0, -0.03, 0.02), "in_out_cubic"), (1.2, HR, "in_out_cubic"), (T, HR + V(0, -0.01, 0.0), "in_out_cubic")],
          [(0, A_S), (0.45, nrm(V(0.0, -1.0, 0.10)), "in_out_cubic"), (1.2, nrm(V(0.5, -0.6, 0.6)), "in_out_cubic"), (T, nrm(V(0.5, -0.6, 0.6)))])
    a.rot("arm_L", Curve([(0, z), (0.30, V(8, 0, 6), "out_cubic"), (1.2, V(-24, 0, 4), "in_out_cubic"), (1.8, V(-32, 0, 3), "in_out_cubic"), (T, V(-33, 0, 3), "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.30, V(6, 0, 0), "out_cubic"), (1.2, V(-46, 0, 0), "in_out_cubic"), (1.8, V(-56, 0, 0), "in_out_cubic"), (T, V(-57, 0, 0), "in_out_cubic")]))
    a.rot("wrist_L", Curve([(0, z), (0.5, V(10, 0, 0), "in_out_cubic"), (1.4, V(-34, 0, 0), "in_out_cubic"), (T, V(-40, 0, 0), "in_out_cubic")]))
    ankL = V(0.0, 0.0, PZ + 0.165 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.55, z), (0.85, ankL + V(0, 0.06, -0.06), "in_out_cubic"), (1.15, ankL, "in_out_cubic"), (T, ankL)]),
               rot=Curve([(0, z), (0.55, z), (0.70, V(18, 0, 0), "in_out_cubic"), (0.95, V(-10, 0, 0), "in_out_cubic"), (1.15, z, "in_out_cubic"), (T, z)]))
    ankR = V(0.0, KNEE_Y - JOINTS["ankle_L"][1], PZ - L2 - JOINTS["ankle_L"][2])
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.60, z), (1.00, ankR + V(0, 0.10, 0.10), "in_out_cubic"), (1.38, ankR, "in_out_cubic"), (T, ankR)]),
               rot=Curve([(0, z), (0.60, z), (1.00, V(95, 0, 0), "in_out_cubic"), (1.38, V(172, 0, 0), "in_out_cubic"), (T, V(172, 0, 0))]))
    # ---- the staff leaves the hand at 0.45: free fall, two bounces, lies tangent to the kneeling figure on the plinth's right-front, the crook end
    # at the rim so the censer chain drapes over the edge and the censer rests on the board
    pc = V(-0.27, 0.0, 0.21)                                       # crook end (hook) on the plinth top, near the rim
    u_in = -nrm(pc)
    tg = V(-u_in[2], 0.0, u_in[0])
    if tg[2] > 0:
        tg = -tg
    sphi = min(0.315 / float(np.linalg.norm(pc)), 0.98)
    head_dir = nrm(u_in * math.sqrt(1 - sphi * sphi) + tg * sphi)  # grip -> foot direction on the plinth
    c_xz = pc + head_dir * 0.585
    a.hang = Fn(lambda t: swing(0.0, 0.0))
    t_land = M.release_weapon(a, "weapon", 0.45, 0.22, 0.022, A_S, tuple(head_dir), land_xz=(float(c_xz[0]), float(c_xz[2])), up_local=(0, 0, 1))
    # the censer: swings wildly through the fall, then rests over the rim, rocking to a stop
    a.hang = None
    ctxT = a.pose(T)
    Pf = ctxT.Pw[sk.ix["top"]].copy()
    rh = nrm(V(Pf[0], 0.0, Pf[2]))                                  # outward from the plinth centre
    dy = float(np.clip((0.112 - Pf[1]) / PEND, -0.97, -0.05))
    d_lie = nrm(rh * math.sqrt(1 - dy * dy) + V(0, dy, 0))

    def sg_hang(t):
        if t < 0.45:
            return swing(3.0 * math.sin(t * 5), 4.0)
        u = t - 0.45
        w = smoothstep(0.0, max(t_land - 0.45, 0.2) + 0.25, u)
        wob = math.exp(-u / 0.55) * math.sin(TAU * u / 0.55)
        d0 = nrm(swing(34.0 * wob, 22.0 * math.exp(-u / 0.4) * math.cos(TAU * u / 0.5)))
        d = nrm(d0 * (1 - w) + d_lie * w)
        rock = math.exp(-max(u - (t_land - 0.45), 0.0) / 0.25) * math.sin(TAU * max(u - (t_land - 0.45), 0.0) / 0.4) * 0.10 * smoothstep(0.0, 0.2, u - (t_land - 0.45))
        return nrm(d + V(0.0, rock, 0.0) * 0 + V(-d[2], 0, d[0]) * rock)
    a.hang = Fn(sg_hang)
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Attack
IMPACT = 1.10
P_WIND, D_WIND = WR0 + V(0.05, 0.22, 0.13), nrm(V(0.0, -0.93, -0.36))      # staff hoisted, crook tipped forward over the head
P_HIT, D_HIT = WR0 + V(0.06, 0.12, 0.22), nrm(V(0.0, -0.50, -0.87))        # thrust: the crook points at the foe
P_FOL, D_FOL = WR0 + V(0.05, 0.06, 0.22), nrm(V(0.0, -0.60, -0.80))


def clip_attack(rig):
    a = _anim(rig)
    T, I = 2.4, IMPACT
    z = _z()
    TW0, TW1 = 0.30, I                                           # the censer circle runs 0.30 -> impact
    _hand(a, [(0, WR0), (0.14, WR0 + V(0.0, 0.02, -0.02), "in_out_cubic"), (0.50, P_WIND, "in_out_cubic"), (0.92, P_WIND + V(0, 0.015, -0.03), "in_out_cubic"),
              (I, P_HIT, "snap_in"), (1.28, P_FOL, "out_cubic"), (1.50, P_FOL, {"tan": "flat"}), (2.0, WR0 + V(0.02, 0.01, 0.05), "in_out_cubic"), (T, WR0, "in_out_cubic")],
          [(0, A_S), (0.14, A_S, "in_out_cubic"), (0.50, D_WIND, "in_out_cubic"), (0.92, D_WIND, "in_out_cubic"), (I, D_HIT, "snap_in"), (1.28, D_FOL, "out_cubic"),
           (1.50, D_FOL, {"tan": "flat"}), (2.0, nrm(V(0.0, -1.0, 0.05)), "in_out_cubic"), (T, A_S, "in_out_cubic")])
    N_REV, PW = 2.25, 1.9
    alpha = Curve([(0, 4.0), (0.30, 6.0), (0.62, 58.0, "in_out_cubic"), (0.92, 66.0), (I, 82.0, "in_cubic")])

    def hang(t):
        if t <= I:
            u = min(max((t - TW0) / (TW1 - TW0), 0.0), 1.0)
            phi = 90.0 - 360.0 * N_REV * (1.0 - u ** PW)
            return cone(float(alpha(t)[0] if np.ndim(alpha(t)) else alpha(t)), phi)
        s = t - I                                                 # released: damped plane pendulum starting from the forward whip
        az = 82.0 * math.exp(-s / 0.55) * math.cos(TAU * s / 1.05)
        ax = 6.0 * math.exp(-s / 0.5) * math.sin(TAU * s / 0.7)
        return swing(ax, az)
    a.hang = Fn(hang)
    # left hand: raised, palm out, a conjuring push at the release
    a.rot("arm_L", Curve([(0, z), (0.30, V(-30, 0, 6), "in_out_cubic"), (0.80, V(-80, 0, 10), "in_out_cubic"), (I, V(-90, 0, 6), "snap_in"), (1.40, V(-62, 0, 6), "out_cubic"), (2.0, V(-8, 0, 2), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.30, z), (0.80, V(-22, 0, 0), "in_out_cubic"), (I, V(-8, 0, 0), "snap_in"), (1.40, V(-20, 0, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("wrist_L", Curve([(0, z), (0.80, V(-14, 0, 0), "in_out_cubic"), (I + 0.02, V(-26, 0, 0), ("spring", 0.2, 1.5)), (1.5, V(-12, 0, 0)), (T, z, "in_out_cubic")]))
    # pelvis leads: coil back, rise through the circle, LUNGE into the release just ahead of the staff
    a.pos("body", Curve([(0, z), (0.20, V(0, -0.014, -0.022), "in_out_cubic"), (0.55, V(0, 0.010, -0.020), "in_out_cubic"), (0.92, V(0, -0.006, -0.034), "in_out_cubic"),
                         (I - 0.05, V(0, -0.030, 0.100), "snap_in"), (1.30, V(0, -0.042, 0.108), "out_cubic"), (1.56, V(0, -0.036, 0.104), {"tan": "flat"}), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.20, V(3, 0, 0), "in_out_cubic"), (0.62, V(-2, -3, 0), "in_out_cubic"), (0.92, V(-5, -5, 0), "in_out_cubic"), (I - 0.07, V(5, 2, 0), "snap_in"),
                         (1.34, V(4, 2, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.20, V(2, 0, 0), "in_out_cubic"), (0.62, V(-5, -2, 0), "in_out_cubic"), (0.92, V(-9, -6, -1), "in_out_cubic"), (I - 0.04, V(9, 3, 1), "snap_in"),
                          (1.34, V(7, 3, 1), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.20, V(1, 0, 0), "in_out_cubic"), (0.62, V(-5, -2, 0), "in_out_cubic"), (0.92, V(-9, -7, -2), "in_out_cubic"), (I - 0.02, V(9, 4, 2), "snap_in"),
                          (1.34, V(7, 4, 1), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.20, V(3, 0, 0), "in_out_cubic"), (0.92, V(-8, 6, 0), "in_out_cubic"), (I + 0.03, V(6, -3, 0), "snap_in"), (1.34, V(5, -3, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.20, V(3, 0, 0), "in_out_cubic"), (0.92, V(-10, 6, 0), "in_out_cubic"), (I + 0.05, V(5, -3, 0), "snap_in"), (1.38, V(4, -3, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.6, V(0, 0, -4), "in_out_cubic"), (0.92, V(0, 0, -7), "in_out_cubic"), (I, V(0, 0, 3), "snap_in"), (1.4, V(0, 0, 3)), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.6, V(0, 0, 5), "in_out_cubic"), (0.92, V(0, 0, 8), "in_out_cubic"), (I, V(0, 0, -2), "snap_in"), (1.4, V(0, 0, -2)), (T, z, "in_out_cubic")]))
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.82, z), (0.94, V(0, 0.05, 0.05), "in_out_cubic"), (1.06, V(0, 0, 0.115), "in_out_cubic"), (1.60, V(0, 0, 0.115)),
                                       (1.82, V(0, 0.04, 0.06), "in_out_cubic"), (2.05, z, "in_out_cubic")]),
               rot=Curve([(0, z), (0.82, z), (0.92, V(16, 0, 0), "in_out_cubic"), (1.04, V(-6, 0, 0), "in_out_cubic"), (1.12, z, "in_out_cubic"), (1.62, z), (1.76, V(10, 0, 0), "in_out_cubic"), (2.05, z, "in_out_cubic")]))
    M.set_foot(a, "foot_R", pos=Curve([(0, z), (0.9, z), (1.12, V(0, 0, -0.03), "in_out_cubic"), (1.6, V(0, 0, -0.03)), (2.08, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.35)
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
        out.append(a.bake(name, dur, loop=loop, fps=fps, keep_times=keep))
    if cache:
        with open(cache, "wb") as fh:
            pickle.dump(out, fh)
    return out


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("emberhold", "bishop", rig, make_clips(rig), impact_time=IMPACT, strike_range=1.50, attack_style="ranged", seed=7)
    C.pedestal_parts(p)
    robe(p)
    legs(p)
    torso_details(p)
    mantle_and_collar(p)
    arms(p)
    head(p)
    staff(p)
    censer(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
