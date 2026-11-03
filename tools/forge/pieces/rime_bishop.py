"""rime_bishop - Rime Frost Chanter.

A gaunt drowned caster in very dark, frost-stiff layered robes with a frozen white beard, crowned with a tall translucent ICE MITRE cut by
a deep 38 degree diagonal slit that glows cyan (the identity cue; the old spiky crown is gone).  A crooked obsidian staff carries a cage
lantern of trapped blue light on a chain; five ice rune tablets orbit the lantern.
Built from docs/art/rime_bishop.md on the full humanoid skeleton: smooth-skinned sleeves / neck / robe / tabard, skirt-compression bones
(the torn hem stays planted, the kneel gathers the robe), rigid ice + silver, a gravity-hung lantern chain (top > cape_1 > cape_2) and a
`runes` bone riding the lantern that spins / expands / converges.  All clips are procedural IK / pendulum motion baked to dense tracks.
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
import _rime_common as rc                          # noqa: E402
from _rime_common import spikes, cluster, frost_layer   # noqa: E402

ASSET_ID = "rime_bishop"
V = lambda *x: np.array(x, dtype=float)            # noqa: E731
nrm = lambda v: np.asarray(v, float) / np.linalg.norm(v)      # noqa: E731
DARK = lambda v: (lambda P: np.full(len(P), v))    # noqa: E731


def lerp3(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


# ======================================================================================= robe ellipse family
RY = np.array([0.22, 0.245, 0.30, 0.40, 0.50, 0.60, 0.68, 0.74, 0.80, 0.86, 0.92, 0.97, 1.00])
RX = np.array([0.250, 0.252, 0.246, 0.222, 0.196, 0.168, 0.140, 0.112, 0.104, 0.110, 0.122, 0.128, 0.100])
RZ = np.array([0.244, 0.246, 0.240, 0.216, 0.190, 0.162, 0.126, 0.098, 0.086, 0.090, 0.094, 0.094, 0.074])
HEM_Y = 0.226
N_TONGUE = 13


def rx_(y):
    return np.interp(y, RY, RX)


def rz_(y):
    return np.interp(y, RY, RZ)


def zc_(y):
    return 0.010 * smoothstep(0.70, 0.99, y)


def asym(th, y):
    """Lopsided bell: the skirt drags out toward the back-left and tucks in at the front-right (a caster drifting, not a gown)."""
    return 1.0 + 0.04 * np.cos(th - 2.3) * float(smoothstep(0.80, 0.30, y))


def fold_amp(y):
    return 0.045 * float(smoothstep(0.72, 0.28, y)) + 0.006


def fold_f(th, y, ph=0.0, amp=None):
    a = fold_amp(y) if amp is None else amp
    return 1 + a * (0.55 * np.cos(9 * th + 0.4 + ph) + 0.30 * np.cos(15 * th + 2.1 + ph) + 0.15 * np.cos(5 * th + ph))


_TH = np.random.default_rng(31)
_HB = 0.035 + 0.060 * _TH.random(N_TONGUE)          # notch heights between the tongues (shared: the hem is one torn edge)
_TIP = 0.004 * _TH.random(N_TONGUE)


def tooth(th, hscale=1.0, ph=0.0):
    """Torn hem: N_TONGUE downward tongues, continuous, each of its own length."""
    u = (np.asarray(th) * N_TONGUE / TAU + ph) % N_TONGUE
    k = np.floor(u).astype(int) % N_TONGUE
    f = u - np.floor(u)
    hb = _HB[k] * (1 - f) + _HB[(k + 1) % N_TONGUE] * f
    a = np.abs(2 * f - 1)
    return (_TIP[k] + (hb * hscale - _TIP[k]) * a ** 1.15)


def ring(y, grow=0.0, K=78, fold=None, ph=0.0, hscale=1.0, tph=0.0):
    th = np.linspace(0, TAU, K, endpoint=False)
    f = fold_f(th, y, ph, fold) * asym(th, y)
    x = (rx_(y) + grow) * f * np.sin(th)
    z = (rz_(y) + grow) * f * np.cos(th) + zc_(y)
    fall = max(0.0, 1.0 - (y - HEM_Y) / 0.26)
    yy = y + tooth(th, hscale, tph) * fall
    return np.stack([x, yy, z], 1)


def surf(y, ang_deg, lift=0.0):
    """Point (and outward direction) on the robe surface at height y, angle from +Z toward +X."""
    a = math.radians(ang_deg)
    k = float(asym(a, y)) * float(fold_f(a, y))
    p = np.array([(rx_(y) * k + lift) * math.sin(a), y, (rz_(y) * k + lift) * math.cos(a) + zc_(y)])
    n = np.array([math.sin(a) / max(rx_(y), 1e-3), 0, math.cos(a) / max(rz_(y), 1e-3)])
    return p, n / np.linalg.norm(n)


def zfront(x, y, lift=0.0):
    e = max(0.0, 1 - (x / rx_(y)) ** 2)
    return rz_(y) * float(asym(0.0, y)) * float(fold_f(0.0, y)) * math.sqrt(e) + lift + zc_(y)


def conform_strip(y0, y1, w0, w1, lift=0.008, rows=14, cols=5, back=False, fold=0.0, seed=0, hem=0.0, tatter=0.0):
    """Open cloth strip hugging the robe front (or back), width tapering w0 (top) -> w1 (bottom); `tatter` shreds the lower edge."""
    ys = np.linspace(y1, y0, rows)
    u = np.linspace(-0.5, 0.5, cols)
    grid = []
    rng = np.random.default_rng(seed)
    ph = rng.random(3) * TAU
    cut = rng.random(cols) * tatter
    for y in ys:
        t = (y1 - y) / (y1 - y0)
        w = w0 + (w1 - w0) * t
        row = []
        for ci, ui in enumerate(u):
            x = ui * w
            e = max(0.0, 1 - (x / rx_(y)) ** 2)
            zf = rz_(y) * float(asym(math.pi if back else 0.0, y)) * float(fold_f(math.pi if back else 0.0, y))
            z = zf * math.sqrt(e) + lift + fold * math.sin(ui * 9 + ph[0]) * (0.3 + t) + zc_(y)
            row.append((x, y - hem * t ** 3 * math.sin(ui * 7 + ph[1]) + cut[ci] * smoothstep(0.82, 1.0, t), -z if back else z))
        grid.append(row)
    G = np.array(grid)[::-1]
    return g.loft(G if not back else G[:, ::-1], closed=False, crease=60, v_tile=0.25, u_tile=0.25)


# ======================================================================================= rig
# the crook-staff: a straight shaft from the foot cap to the crook base, the grip at wrist_R (same proven geometry as the Emberhold bishop)
JOINTS = dict(pelvis=(0, 0.60, 0), spine=(0, 0.72, 0), chest=(0, 0.85, 0), neck=(0, 0.955, 0.012), head=(0, 0.985, 0.015), top=(-0.235, 1.384, 0.250),
              clavicle_L=(0.06, 0.945, 0), shoulder_L=(0.13, 0.955, 0), elbow_L=(0.165, 0.82, 0.055), wrist_L=(0.185, 0.725, 0.125),
              hip_L=(0.065, 0.62, 0), knee_L=(0.075, 0.42, 0.045), ankle_L=(0.07, 0.26, 0.05), toe_L=(0.07, 0.245, 0.13),
              elbow_R=(-0.195, 0.82, 0.062), wrist_R=(-0.2386, 0.90, 0.1443))
J_ = lambda k: np.array(JOINTS[k] if k in JOINTS else ((-JOINTS[k[:-1] + "L"][0],) + tuple(JOINTS[k[:-1] + "L"][1:])), dtype=float)   # noqa: E731

S_FOOT, S_TOP = V(-0.245, 0.22, 0.170), V(-0.235, 1.28, 0.130)
A_S = nrm(S_FOOT - S_TOP)                          # staff axis at rest: grip -> foot
WR0, WL0 = J_("wrist_R"), J_("wrist_L")
W0 = S_TOP + (S_FOOT - S_TOP) * ((1.28 - 0.80) / 1.06)        # `weapon` bone = staff centre (y 0.80)
PIV = V(-0.235, 1.384, 0.250)                      # lantern pendulum pivot (under the crook apex)
CX, CZ = PIV[0], PIV[2]
CH1, CH2 = V(CX, 1.342, CZ), V(CX, 1.300, CZ)      # mid chain, lantern cap ring
LAN_C = V(CX, 1.222, CZ)                           # lantern centre = rune orbit centre
PEND = float(np.linalg.norm(LAN_C - PIV))


def make_rig() -> Rig:
    base = humanoid_rig(JOINTS, weapon=tuple(W0), cape=[tuple(CH1), tuple(CH2)])
    r = Rig()
    for name, b in base.bones.items():                      # `top` (the lantern pivot) rides the staff: re-parent it under `weapon`
        if name == "top":
            continue
        if name == "cape_1":
            r.add("top", "weapon", PIV)
        r.add(name, b.parent, b.pos)
    r.alias = dict(base.alias)
    r.add("runes", "cape_2", tuple(LAN_C))                  # the orbit ring rides the lantern
    r.add("skirt_1", "body", (0, 0.60, 0))                  # skirt compression bones: the hem stays planted, the kneel gathers the robe
    r.add("skirt_2", "body", (0, 0.40, 0))
    r.add("skirt_3", "body", (0, 0.26, 0))
    r.socket("socket_weapon_R", "wrist_R", tuple(WR0))
    r.socket("socket_cast", "cape_2", tuple(LAN_C))
    r.socket("socket_impact", "body", (0, 0.45, 1.45))
    r.socket("socket_head", "head", (0, 1.36, 0))
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
BEARD_SKIN = Skin.gradient(Skin.rigid("head"), Skin.rigid("chest"), axis=1, v0=0.975, v1=0.895)


def tint_robe(P):
    hem = (0.07 + 0.19 * smoothstep(0.22, 0.66, P[:, 1] + 0.05 * g.fbm3(P * 6.0, 3, 2, seed=4)))
    return hem[:, None] * np.array([0.8, 0.95, 1.2])


# ======================================================================================= robe & boots
def robe(p: Piece):
    ys = [0.222, 0.235, 0.255, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.69, 0.72, 0.75, 0.80, 0.84, 0.88, 0.92, 0.95, 0.968]
    rings = np.stack([ring(y, 0.0, 78) for y in ys])
    m = g.loft(rings, closed=True, crease=70, cap_start=False, cap_end=True).noised(0.0020, 14, 2, seed=3)
    p.add("robe", m, "RH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, tint=tint_robe)
    # under-robe: a darker quilted layer a little shorter and tighter; shows through the torn notches of the outer robe
    yu = [0.234, 0.255, 0.30, 0.36, 0.42, 0.50, 0.58, 0.66, 0.72]
    under = g.loft(np.stack([ring(y, -0.013, 52, fold=0.03, ph=1.7, hscale=0.55, tph=0.5) for y in yu]), closed=True, crease=60, cap_start=False, cap_end=True)
    p.add("robe_under", under.noised(0.0016, 14, 2, seed=5), "RH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, tint=lambda P: np.tile([0.16, 0.20, 0.30], (len(P), 1)))
    # frost-stiff hem: a pale rime edge following the torn line on the outer robe's lower faces (value accent)
    th = np.linspace(0, TAU, 78, endpoint=False)
    edge = np.stack([(rx_(0.222) + 0.003) * fold_f(th, 0.222) * asym(th, 0.222) * np.sin(th), 0.222 + tooth(th),
                     (rz_(0.222) + 0.003) * fold_f(th, 0.222) * asym(th, 0.222) * np.cos(th) + zc_(0.222)], 1)
    p.add("hem_rime", g.tube(edge, 0.0040, sides=4, samples=1, cap=None, closed=True, smooth=False, up=(0, 1, 0)), "RH_Frost", None, skin=ROBE_SKIN,
          tint=DARK(0.40))
    # ice daggers growing from the tongue tips + short frost tufts between them
    ice, fro = [], []
    rng = np.random.default_rng(12)
    for k in range(N_TONGUE):
        a = (k + 0.5) * TAU / N_TONGUE
        pt = edge[int(round((k + 0.5) * 78 / N_TONGUE)) % 78]
        d = V(math.sin(a) * 0.6, -1.0, math.cos(a) * 0.6)
        ice.append((pt + V(0, 0.012, 0), d, 0.035 + 0.045 * rng.random(), 0.0085 + 0.004 * rng.random()))
        pn = edge[int(round(k * 78 / N_TONGUE)) % 78]
        fro.append((pn + V(0, -0.002, 0), V(math.sin(a - 0.24) * 0.9, 0.7, math.cos(a - 0.24) * 0.9), 0.020 + 0.020 * rng.random(), 0.0065))
    p.add("hem_ice", spikes(ice, seed=11, flat=0.25, sides=4, tip=0.5), "RH_Ice", None, skin=ROBE_SKIN)
    p.add("hem_frost", spikes(fro, seed=12, flat=0.2, sides=4, tip=0.5), "RH_Frost", None, skin=ROBE_SKIN, lod1=None, tint=DARK(0.6))
    # vertical frozen pleat ribs (stiff folds), hem -> waist
    ribs = []
    rng = np.random.default_rng(9)
    for i in range(14):
        a_ = 12 + i * (336 / 13) + rng.normal(0, 3)
        y0, y1 = 0.32 + 0.04 * rng.random(), 0.60 + 0.10 * rng.random()
        pts = [surf(y, a_, 0.0045 + 0.004 * float(smoothstep(0.7, 0.3, y)))[0] for y in np.linspace(y0, y1, 5)]
        ribs.append(g.tube(pts, [0.0095, 0.0085, 0.0070, 0.0050, 0.0012], sides=4, samples=1, cap="round", cap_steps=1, smooth=True, up=(0, 0, 1)))
    p.add("pleat_ribs", merge(ribs), "RH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, lod1=None,
          tint=lambda P: (0.30 + 0.60 * smoothstep(0.28, 0.62, P[:, 1]))[:, None] * np.array([0.9, 1.0, 1.2]))
    # boots barely peeking out under the hem
    for s, nm in ((1, "L"), (-1, "R")):
        foot = g.superellipsoid((0.034, 0.022, 0.082), 0.5, 0.62, 3, 9).translated(s * 0.070, 0.246, 0.188)
        p.add(f"boot_{nm}", foot, "RH_Obsidian", f"foot_{nm}")
        p.add(f"boot_ice_{nm}", spikes([((s * 0.070, 0.248, 0.262), (0.0, 0.1, 1.0), 0.035, 0.010)], seed=3 + (s > 0), flat=0.3, sides=4), "RH_Ice", f"foot_{nm}", lod1=None)


# ======================================================================================= torso details
def torso_details(p: Piece):
    # front tabard: a long dark armoured strip with silver edge wire and embroidered glyphs, torn at the hem
    tab = conform_strip(0.34, 0.905, 0.075, 0.118, lift=0.010, rows=20, cols=5, fold=0.003, seed=2, hem=0.012, tatter=0.05)
    p.add("tabard", tab, "RH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, tint=lambda P: np.tile([0.30, 0.38, 0.58], (len(P), 1)))
    for sgn, nm in ((-1, "R"), (1, "L")):
        yy = np.linspace(0.36, 0.90, 13)
        wv = 0.075 + (0.118 - 0.075) * (0.905 - yy) / (0.905 - 0.34)
        path = [(sgn * wv[i] / 2 * 0.99, yy[i], zfront(sgn * wv[i] / 2 * 0.99, yy[i], 0.0145)) for i in range(len(yy))]
        p.add(f"tabard_trim_{nm}", g.tube(path, 0.0036, sides=4, samples=1, cap="round", cap_steps=1, smooth=False, ellipse=(1.0, 0.8)), "RH_Silver", None, skin=ROBE_SKIN,
              lod1=None, tint=DARK(0.75))
    gl = []
    for k, y in enumerate((0.47, 0.57, 0.68, 0.80)):
        z = zfront(0.0, y, 0.0125)
        gl.append(merge(glyph_bars(k, 0.0044)).scaled(1.25).translated(0, y, z + 0.002).rotated(-5, 0, 0, pivot=(0, y, z)))
    p.add("tabard_glyphs", merge(gl), "RH_Silver", None, skin=ROBE_SKIN, lod1=None, tint=DARK(0.7))
    # back cloak: a tattered cloth hanging from the shoulders (smooth-skinned)
    back = conform_strip(0.40, 0.955, 0.14, 0.26, lift=0.012, rows=14, cols=7, back=True, fold=0.010, seed=4, hem=0.02, tatter=0.07)
    p.add("back_cloak", back, "RH_Cloth", None, skin=ROBE_SKIN, uv_scale=2, tint=lambda P: (0.06 + 0.12 * smoothstep(0.40, 0.95, P[:, 1]))[:, None] * np.array([0.9, 1.0, 1.15]))
    # waist: a wrapped cloth band, silver cord, hanging ice shards on a chain at the left hip (asymmetry)
    wrap = rc.helix(0.114, 0.668, 0.766, 2.4, r=0.0125, sides=5, per_turn=11, R1=0.104, az=0.008)
    p.add("waist_wrap", wrap, "RH_Cloth", None, skin=TORSO_SKIN, uv_scale=2, tint=DARK(0.6))
    cord = rc.helix(0.1215, 0.757, 0.771, 1.0, r=0.0052, sides=4, per_turn=14, az=0.008)
    p.add("belt_cord", cord, "RH_Silver", None, skin=TORSO_SKIN, lod1=None, tint=DARK(0.75))
    pts = [surf(0.745 - 0.10 * t, 40 + 12 * t, 0.016)[0] for t in np.linspace(0, 1, 6)]
    p.add("hip_chain", g.tube(pts, 0.0030, sides=4, samples=1, cap="round", cap_steps=1, smooth=True), "RH_Silver", None, skin=ROBE_SKIN, lod1=None, tint=DARK(0.75))
    p.add("hip_shards", spikes([(pts[-1], (0.1, -1, 0.15), 0.065, 0.011), (pts[-1] + V(0.012, 0.01, -0.004), (0.35, -1, 0.0), 0.040, 0.008)], seed=14, flat=0.25, sides=4, tip=0.5),
          "RH_Ice", None, skin=ROBE_SKIN)
    # left-only obsidian chest plate shards (3 overlapping triangles) + silver wire lacing across the front
    tris = [[(0.02, 0.90), (0.12, 0.92), (0.07, 0.80)], [(0.02, 0.84), (0.10, 0.82), (0.05, 0.72)], [(0.02, 0.78), (0.09, 0.74), (0.05, 0.66)]]
    pl = []
    for i, t3 in enumerate(tris):
        m = g.extrude(np.array(t3), 0.010, 0.003, 1)
        yc = float(np.mean([q[1] for q in t3]))
        zc = zfront(float(np.mean([q[0] for q in t3])), yc, 0.016 + 0.004 * i)
        pl.append(m.rotated(-6 + 3 * i, 0, 0).translated(0, 0, zc))
    p.add("chest_shards", merge(pl), "RH_Obsidian", None, skin=TORSO_SKIN)
    lace = []
    for i in range(17):
        y = 0.64 + 0.27 * i / 16
        x = 0.060 * (1 if i % 2 else -1)
        lace.append((x, y, zfront(x, y, 0.0225)))
    p.add("lacing", g.tube(lace, 0.0038, sides=4, samples=1, cap=None, smooth=False), "RH_Silver", None, skin=ROBE_SKIN, lod1=None, tint=DARK(0.75))
    rid = cluster((0.0, 0.92, -0.075), (0.0, 0.5, -1.0), 3, (0.06, 0.10), (0.012, 0.018), spread=0.05, tilt=20, seed=4, flat=0.25)
    p.add("back_ridge", rid, "RH_Ice", "chest")


def mantle_and_collar(p: Piece):
    K = 48
    th = np.linspace(0, TAU, K, endpoint=False)
    path = np.stack([0.128 * np.sin(th), 0.944 - 0.030 * np.abs(np.sin(th)) ** 1.5, 0.088 * np.cos(th) + 0.004], 1)
    mant = g.tube(path, 0.0205, sides=9, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.0025, 16, 2, seed=7)
    p.add("mantle", mant, "RH_Cloth", "chest", uv_scale=2, tint=DARK(0.38))
    p.add("mantle_frost", frost_layer(mant, 0.006, min_ny=0.6, cover=0.26, seed=3), "RH_Frost", "chest", lod1=None, tint=DARK(0.5))
    mant2 = g.tube(path * [1.20, 1, 1.20] - [0, 0.030, 0], 0.016, sides=6, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.004, 16, 2, seed=8)
    p.add("mantle_under", mant2, "RH_Cloth", "chest", uv_scale=2, tint=DARK(0.28), lod1=None)
    # tattered ice-tipped fringe under the mantle
    fr = []
    for k, a in enumerate(np.linspace(0.3, TAU + 0.3, 11, endpoint=False)):
        fr.append(((0.158 * math.sin(a), 0.905, 0.118 * math.cos(a)), (math.sin(a) * 0.5, -1, math.cos(a) * 0.5), 0.040 + 0.025 * (k % 2), 0.0075))
    p.add("mantle_ice", spikes(fr, seed=5, flat=0.25, sides=4, tip=0.5), "RH_Ice", "chest", lod1=None)
    # gorget: a fan of seven obsidian plates rising behind the neck (high collar)
    pls = []
    for k in range(7):
        a = 180 + (k - 3) * 27
        h = 0.115 - 0.012 * abs(k - 3) + (0.02 if k % 2 else 0.0)
        poly = np.array([(-0.014, 0), (0.014, 0), (0.019, h * 0.75), (0.0, h), (-0.019, h * 0.78)])
        m = g.extrude(poly, 0.008, 0.002, 1).rotated(-14 - 5 * (k % 2), 0, 0).translated(0, 0.955, 0.070).rotated(0, a, 0)
        pls.append(m)
    p.add("gorget", merge(pls), "RH_Obsidian", "neck")
    p.add("gorget_wire", g.torus(0.079, 0.0045, 16, 4).translated(0, 0.968, 0.002), "RH_Silver", "neck", lod1=None, tint=DARK(0.8))
    # left shoulder: an obsidian pauldron + frost; the right shoulder is bare cloth (asymmetry)
    sh = g.superellipsoid((0.058, 0.026, 0.056), 0.5, 0.65, 4, 10).noised(0.0016, 36, 2, seed=2).rotated(0, 0, -14).translated(0.150, 0.990, 0.0)
    sh2 = g.superellipsoid((0.050, 0.020, 0.050), 0.5, 0.65, 4, 9).rotated(0, 0, -22).translated(0.160, 0.962, 0.0)
    p.add("shoulder_L", merge([sh, sh2]), "RH_Obsidian", "arm_L")
    p.add("shoulder_L_frost", frost_layer(sh, 0.007, min_ny=0.4, cover=0.3, seed=2), "RH_Frost", "arm_L", lod1=None, tint=DARK(0.55))
    drape = []
    for k, (dx, ln) in enumerate(((-0.130, 0.16), (-0.108, 0.21), (-0.150, 0.13))):
        poly = np.array([(-0.016, 0), (0.016, 0), (0.012, -ln * 0.8), (0.0, -ln), (-0.012, -ln * 0.7)])
        drape.append(g.extrude(poly, 0.007, 0.0015, 1).rotated(0, 90, 0).rotated(0, 0, 8 * (k - 1)).translated(dx - 0.02, 0.975, 0.01 - 0.03 * (k - 1)))
    p.add("drape_R", merge(drape), "RH_Cloth", "arm_R", uv_scale=2, tint=DARK(0.38))
    clasp = merge([g.extrude(g.rect_poly(0.040, 0.0075), 0.006, 0.0012, 1).rotated(0, 0, a) for a in (0, 60, 120)]).translated(0, 0.915, 0.104)
    p.add("brooch", clasp, "RH_Silver", "chest")


# ======================================================================================= arms & hands
def arms(p: Piece):
    for s, nm in ((1, "L"), (-1, "R")):
        sh, el, wr = J_(f"shoulder_{nm}"), J_(f"elbow_{nm}"), J_(f"wrist_{nm}")
        fd = nrm(wr - el)
        sleeve = limb_tube([sh + [0, -0.01, 0], lerp3(sh, el, 0.5), el, lerp3(el, wr - fd * 0.02, 0.5), wr - fd * 0.02], [0.034, 0.040, 0.042, 0.052, 0.062],
                           joints=[el], spacing=0.045, joint_spacing=0.02, joint_zone=0.05, sides=8, cap=None, up=(0, 1, 0))
        p.add(f"sleeve_{nm}", sleeve.noised(0.003, 12, 2, seed=20 + s), "RH_Cloth", None, skin=ARM_SKIN[nm], uv_scale=2,
              tint=lambda P: (0.20 + 0.28 * smoothstep(0.66, 0.84, P[:, 1]))[:, None] * np.array([0.95, 1.0, 1.1]))
        p.add(f"cuff_{nm}", g.torus(0.060, 0.0050, 16, 4).aimed(fd, wr - fd * 0.016), "RH_Silver", f"hand_{nm}", lod1=None, tint=DARK(0.75))
        inner = g.lathe(np.array([(0.0, -0.085), (0.030, -0.083), (0.050, -0.055), (0.055, -0.026), (0.0, -0.026)]), 14, crease=40).aimed(fd, wr - fd * 0.016)
        p.add(f"cuff_inner_{nm}", inner, "RH_Obsidian", f"hand_{nm}", lod1=None, tint=DARK(0.25))
    # ragged tatters hanging from both cuffs
    for s_, nm in ((1, "L"), (-1, "R")):
        wr = J_(f"wrist_{nm}")
        el = J_(f"elbow_{nm}")
        fd = nrm(wr - el)
        tats = []
        for k, (ang, ln) in enumerate(((0, 0.075), (72, 0.105), (144, 0.060), (216, 0.095), (288, 0.070))):
            poly = np.array([(-0.014, 0), (0.014, 0), (0.011, ln * 0.7), (0.0, ln), (-0.009, ln * 0.6)])
            m = g.extrude(poly, 0.004, 0.0008, 1).translated(0, 0, 0.056).rotated(0, ang + 14 * s_, 0)
            tats.append(m.translated(0, -0.004, 0))
        tm = merge(tats).aimed(fd, wr - fd * 0.016)
        p.add(f"cuff_tatters_{nm}", tm, "RH_Cloth", f"hand_{nm}", uv_scale=2, lod1=None, tint=DARK(0.30))
    # left cuff: icicles
    p.add("cuff_L_ice", cluster((0.185, 0.69, 0.122), (0.1, -1.0, 0.2), 4, (0.04, 0.07), (0.007, 0.011), spread=0.04, tilt=30, seed=9, flat=0.3, sides=4), "RH_Ice", "hand_L")
    p.add("cuff_R_icicles", cluster((-0.215, 0.86, 0.10), (-0.4, -1.0, 0.1), 3, (0.03, 0.05), (0.006, 0.009), spread=0.03, tilt=25, seed=19, flat=0.3, sides=4), "RH_Ice", "hand_R", lod1=None)
    # left hand: bony, open, fingers spread, hanging at the hip
    p.add("hand_L", rc.claw_hand(+1, WL0 + V(0.0, -0.012, 0.002), (0.08, -0.9, 0.42), 0.35, 0.95, 1.7), "RH_Bone", "wrist_L", uv_scale=2, tint=DARK(0.85))
    # right hand: bony fist wrapped round the staff (rings wrap the staff axis)
    wrr = WR0
    ax = -A_S
    fist = g.superellipsoid((0.028, 0.026, 0.026), 0.6, 0.6, 3, 8).translated(wrr[0] + 0.001, wrr[1] + 0.001, wrr[2] + 0.021)
    rings_ = [g.torus(0.0195, 0.0062, 8, 4).aimed(ax, wrr + A_S * dy) for dy in (-0.020, -0.007, 0.006, 0.019)]
    thumb = g.tube([wrr + [0.026, 0.018, 0.026], wrr + [0.014, 0.034, 0.022], wrr + [0.004, 0.034, 0.012]], [0.0086, 0.0074, 0.0058], sides=5, samples=1, cap="round", cap_steps=1)
    p.add("hand_R", merge([fist, thumb] + rings_), "RH_Bone", "wrist_R", uv_scale=2, tint=DARK(0.85))
    p.add("sleeve_R_wire", merge([rc.helix(0.040, 0.838, 0.872, 1.5, r=0.0032, sides=3, per_turn=7, ax=-0.200, az=0.082)]), "RH_Silver", "hand_R", lod1=None, tint=DARK(0.75))


# ======================================================================================= head & mitre
def head(p: Piece):
    cx, cy, cz = 0.0, 1.034, 0.012
    skull = g.superellipsoid((0.047, 0.074, 0.054), 0.85, 0.95, 5, 11).translated(cx, cy, cz)
    skull = g.warp(skull, lambda P: np.column_stack([P[:, 0] * (1 - 0.40 * smoothstep(cy + 0.01, cy - 0.074, P[:, 1])), P[:, 1],
                                                     P[:, 2] + 0.004 * smoothstep(cy - 0.03, cy - 0.074, P[:, 1])]), 60)
    nose = g.superellipsoid((0.0075, 0.019, 0.011), 0.6, 0.6, 3, 6).rotated(-18, 0, 0).translated(0, cy - 0.006, cz + 0.050)
    brow = g.rounded_box((0.082, 0.012, 0.026), 0.0055, 1).translated(0, cy + 0.028, cz + 0.036)
    brow = g.warp(brow, lambda P: np.column_stack([P[:, 0], P[:, 1] - 0.006 * (np.abs(P[:, 0]) / 0.041) ** 2, P[:, 2] - 0.012 * (np.abs(P[:, 0]) / 0.041) ** 2]), 60)
    cheek = [g.superellipsoid((0.012, 0.014, 0.012), 0.6, 0.6, 3, 6).translated(s * 0.030, cy - 0.016, cz + 0.038) for s in (-1, 1)]
    chin = g.superellipsoid((0.014, 0.012, 0.016), 0.6, 0.6, 3, 6).translated(0, cy - 0.066, cz + 0.034)
    ears = [g.superellipsoid((0.006, 0.015, 0.011), 0.6, 0.6, 3, 6).translated(s * 0.045, cy + 0.002, cz - 0.004) for s in (-1, 1)]
    p.add("face", merge([skull, nose, brow, chin] + cheek + ears).rotated(0, 5, 0, pivot=(0, cy, cz)), "RH_Bone", "head", uv_scale=2, tint=DARK(0.85))
    sock = [g.superellipsoid((0.0155, 0.0115, 0.009), 0.7, 0.7, 3, 7).rotated(0, s * 14, s * 8).translated(s * 0.0215, cy + 0.016, cz + 0.044) for s in (-1, 1)]
    p.add("eye_sockets", merge(sock), "RH_Obsidian", "head", lod1=None)
    eyes = [g.superellipsoid((0.0085, 0.0040, 0.0045), 0.7, 0.7, 3, 6).rotated(0, 0, s * -8).translated(s * 0.0215, cy + 0.015, cz + 0.0485) for s in (-1, 1)]
    p.add("eyes", merge(eyes), "RH_Glow", "head", lod1="keep", bake=False)
    neck = limb_tube([(0, 0.915, 0.006), (0, 0.95, 0.010), (0, 0.985, 0.012), (0, 1.02, 0.012)], [0.032, 0.028, 0.027, 0.027], joints=[(0, 0.97, 0.011)], spacing=0.04,
                     joint_spacing=0.02, joint_zone=0.03, sides=7, cap=None, up=(0, 0, 1))
    p.add("neck", neck, "RH_Bone", None, skin=NECK_SKIN, uv_scale=2, lod1=None, tint=DARK(0.7))
    # frozen beard: nine flowing locks of rime with ice tips, laid over the mantle and chest, plus a mass at the chin
    locks, ice_t = [], []
    rng = np.random.default_rng(8)
    for k in range(9):
        x = (k - 4) * 0.0095
        mid = 1 - abs(k - 4) / 4
        L = 0.085 + 0.045 * rng.random() + 0.060 * mid
        pts = [(x * 0.55, cy - 0.034, cz + 0.040 + 0.008 * mid), (x * 0.95, 0.958, 0.098 + 0.012 * mid), (x * 1.20, 0.935 - 0.20 * L, 0.124 + 0.010 * mid),
               (x * 1.55 + 0.007 * (k % 3 - 1), 0.985 - L, 0.128 + 0.008 * mid)]
        locks.append(g.tube(pts, [0.0098, 0.0100, 0.0085, 0.0028], sides=5, samples=2, cap="round", cap_steps=1, up=(0, 0, 1)))
        ice_t.append(((x * 1.55, 0.985 - L + 0.006, 0.128 + 0.008 * mid), (0.10 * (k - 4), -1, 0.08), 0.030 + 0.040 * rng.random(), 0.0068))
    p.add("beard", merge(locks), "RH_Frost", None, skin=BEARD_SKIN, uv_scale=2, tint=DARK(0.62))
    p.add("beard_ice", spikes(ice_t, seed=3, flat=0.25, sides=4, tip=0.5), "RH_Ice", None, skin=BEARD_SKIN)
    mass = g.superellipsoid((0.036, 0.040, 0.030), 0.7, 0.8, 3, 8).translated(0, cy - 0.060, cz + 0.040)
    p.add("beard_mass", mass, "RH_Frost", "head", tint=DARK(0.62))
    for sx in (-1, 1):
        mo = g.tube([(0.0, cy - 0.026, cz + 0.048), (sx * 0.020, cy - 0.034, cz + 0.050), (sx * 0.042, cy - 0.060, cz + 0.040)], [0.007, 0.0075, 0.002], sides=5, samples=2, cap="round", cap_steps=1, up=(0, 0, 1))
        p.add(f"moustache_{'L' if sx > 0 else 'R'}", mo, "RH_Frost", "head", uv_scale=2, lod1=None, tint=DARK(0.62))
    mitre(p)


# ---- mitre geometry: a faceted (8-sided) ogive ice shell, a deep diagonal slit cut into the front, a cyan glow floor inside it
MIT_Y = np.array([1.062, 1.070, 1.100, 1.150, 1.205, 1.255, 1.295, 1.318, 1.3235])
MIT_R = np.array([0.086, 0.088, 0.093, 0.090, 0.075, 0.052, 0.027, 0.0085, 0.0005])
MIT_ZS = 0.74                                      # depth / width
SLIT_ANG = math.radians(38.0)
SLIT_C = (0.0, 1.190)
SLIT_HALF_LEN, SLIT_HALF_W, SLIT_DEPTH = 0.094, 0.0200, 0.046
SLIT_RAMP = 0.0105
CHIP = (0.044, 1.262)                              # the chipped notch on the upper character-left edge


def mit_r(y):
    from scipy.interpolate import PchipInterpolator
    return PchipInterpolator(MIT_Y, MIT_R)(np.clip(y, MIT_Y[0], MIT_Y[-1]))


def facet(th):
    """Octagonal section factor (front facet centred on +Z): 1 at the 8 edges, cos(pi/8) at facet centres."""
    ph = np.mod(th + math.pi / 8, math.pi / 4) - math.pi / 8
    return math.cos(math.pi / 8) / np.cos(ph)


def slit_prof(x, y, z):
    """Groove profile 0..1 at a nominal mitre-surface point: V-groove along the 38 degree centreline, round capped, running around the
    flank and fading toward the back."""
    x, y, z = np.asarray(x, float), np.asarray(y, float), np.asarray(z, float)
    dx, dy = x - SLIT_C[0], y - SLIT_C[1]
    d = np.abs(dx * math.sin(SLIT_ANG) + dy * math.cos(SLIT_ANG))
    s = dx * math.cos(SLIT_ANG) - dy * math.sin(SLIT_ANG)
    de = np.hypot(d, np.maximum(np.abs(s) - SLIT_HALF_LEN, 0.0))
    prof = np.clip((SLIT_HALF_W - de) / SLIT_RAMP, 0, 1)
    prof = prof * prof * (3 - 2 * prof)
    zn = z / MIT_ZS
    cth = zn / np.maximum(np.hypot(x, zn), 1e-6)
    return prof * smoothstep(-0.55, -0.05, cth)


MIT_YS = [1.062, 1.070, 1.084, 1.098] + [round(1.108 + 0.0095 * i, 4) for i in range(22)] + [1.3185, 1.3235]
TH_EDGES = [math.radians(a) for a in (-157.5, -112.5, -67.5, -22.5, 22.5, 67.5, 112.5, 157.5)]


def mit_point(th, y):
    """Deformed (groove-carved) mitre surface point + groove profile for angles `th` at height y."""
    th = np.asarray(th, float)
    r = float(mit_r(y))
    f = facet(th)
    x0, z0 = r * f * np.sin(th), MIT_ZS * r * f * np.cos(th)
    pr = slit_prof(x0, y, z0)
    nx, nz = x0 / (r * r), z0 / ((MIT_ZS * r) ** 2)
    nn = np.maximum(np.hypot(nx, nz), 1e-9)
    dep = np.minimum(SLIT_DEPTH * pr, 0.60 * np.hypot(x0, z0))              # never cut past the axis where the mitre narrows
    chip = 0.0105 * np.exp(-(((x0 - CHIP[0]) ** 2 + (y - CHIP[1]) ** 2) / (2 * 0.011 ** 2))) * (np.abs(z0) < 0.03)
    P = np.stack([x0 - (dep + chip) * nx / nn, np.full(len(th), y), z0 - (dep + chip) * nz / nn], 1)
    return P, pr, np.stack([nx / nn, np.zeros_like(nx), nz / nn], 1)


def mitre_shell():
    # angles: dense across the front (+-72 deg) and the facet edges, sparse behind
    th = np.radians(np.concatenate([np.linspace(-76, 76, 38, endpoint=False), np.linspace(76, 284, 14, endpoint=False)]))
    th = np.sort(np.unique(np.round(np.mod(np.concatenate([th, TH_EDGES]), TAU), 6)))
    rings, profs = [], []
    for y in MIT_YS:
        P, pr, _ = mit_point(th, y)
        rings.append(P)
        profs.append(pr)
    rings = np.stack(rings)
    pr = np.stack(profs)
    pr = np.concatenate([pr, pr[:, :1]], axis=1).reshape(-1)          # closed loft duplicates the seam column
    uv = np.stack([pr, np.zeros_like(pr)], 1)
    return g.loft(rings, closed=True, crease=40, shade=False, uv=uv)


def glow_ribbon(half_w=0.0085, n_s=44, cols=5, lift=0.0016):
    """The cyan glow strip lying on the groove floor: a smooth ribbon along the 38 degree centreline (nominal slit coordinates mapped
    through the same carving as the shell), tapered to round caps, ending where the groove wraps onto the flank."""
    rows = []
    for s in np.linspace(-SLIT_HALF_LEN - 0.006, SLIT_HALF_LEN + 0.006, n_s):
        ex = max(abs(s) - SLIT_HALF_LEN, 0.0)
        wf = math.sqrt(max(0.0, 1 - (ex / 0.007) ** 2)) if ex > 0 else 1.0
        row, ok = [], True
        for u in np.linspace(-half_w, half_w, cols):
            u = u * max(wf, 0.12)
            x = SLIT_C[0] + s * math.cos(SLIT_ANG) + u * math.sin(SLIT_ANG)
            y = SLIT_C[1] - s * math.sin(SLIT_ANG) + u * math.cos(SLIT_ANG)
            r = float(mit_r(y))
            if abs(x) > 0.95 * r:
                ok = False
                break
            th = 0.0
            for _ in range(6):
                th = math.asin(max(-0.999, min(0.999, x / (r * float(facet(th))))))
            P, pr, N = mit_point(np.array([th]), y)
            row.append(P[0] - N[0] * (-lift))             # N points inward: subtract -> move outward by `lift`
        if ok:
            rows.append(row)
    G = np.array(rows)
    return g.loft(G[:, ::-1], closed=False, crease=88)


def mitre(p: Piece):
    shell = mitre_shell()
    prof = shell.UV[:, 0].copy()
    uvp = shell.P[:, [0, 1]] / 0.25
    F = shell.F
    wall = prof[F].mean(1) > 0.06                                       # faces of the carved groove -> opaque dark walls under the glow
    shell_m = g.Mesh(shell.P, F[~wall], uvp, crease=44).shade(44)
    walls_m = g.Mesh(shell.P, F[wall], uvp, crease=70).cleaned().shade(70)
    glow_m = glow_ribbon()
    p.add("mitre_slit_walls", walls_m, "RH_Obsidian", "head", tint=DARK(0.55))
    from scipy.spatial import cKDTree
    tree = cKDTree(shell.P)

    def mit_tint(Q):                                # the groove walls fall into deep blue-black; the shell stays pale ice
        _, ix = tree.query(np.asarray(Q))
        t = smoothstep(0.05, 0.75, prof[ix])[:, None]
        return 1.0 - t * (1.0 - np.array([0.10, 0.16, 0.30]))
    p.add("mitre_shell", shell_m, "RH_Ice", "head", tint=mit_tint)
    p.add("mitre_slit_glow", glow_m, "RH_Glow", "head", bake=False, lod1="keep", occluder=False)
    # silver lips along both groove edges (bright line, survives on dark squares)
    lips = []
    for sgn in (-1, 1):
        pts = []
        for s in np.linspace(-SLIT_HALF_LEN - 0.010, SLIT_HALF_LEN + 0.010, 22):
            ex = max(abs(s) - SLIT_HALF_LEN, 0.0)
            off = SLIT_HALF_W * math.sqrt(max(0.0, 1 - (ex / SLIT_HALF_W) ** 2)) if ex < SLIT_HALF_W else 0.0
            x = SLIT_C[0] + s * math.cos(SLIT_ANG) + sgn * off * math.sin(SLIT_ANG)
            y = SLIT_C[1] - s * math.sin(SLIT_ANG) + sgn * off * math.cos(SLIT_ANG)
            r = float(mit_r(y))
            if abs(x) > r * 0.90 or off == 0.0:
                if len(pts) > 1:
                    lips.append(g.tube(pts, 0.0036, sides=4, samples=1, cap="round", cap_steps=1, smooth=True))
                pts = []
                continue
            z = MIT_ZS * r * float(facet(math.asin(min(0.999, abs(x) / r)) * (1 if x > 0 else -1))) * math.sqrt(max(0.0, 1 - (x / r) ** 2))
            pts.append((x, y, z + 0.001))
        if len(pts) > 1:
            lips.append(g.tube(pts, 0.0036, sides=4, samples=1, cap="round", cap_steps=1, smooth=True))
    if lips:
        p.add("mitre_slit_lips", merge(lips), "RH_Silver", "head", lod1=None, tint=DARK(0.85))
    # base band, apex finial, a faint silver piping on the side ridges
    band = g.lathe(np.array([(0.0885, 1.058), (0.0935, 1.063), (0.0945, 1.086), (0.0905, 1.094), (0.0885, 1.090), (0.0885, 1.058)]), 40, crease=40).scaled(1, 1, MIT_ZS)
    p.add("mitre_band", band, "RH_Silver", "head", tint=DARK(0.8))
    rv = [math.radians(a) for a in np.linspace(-80, 80, 9)]
    rpos = [(0.0948 * math.sin(a), 1.0745, 0.0948 * MIT_ZS * math.cos(a)) for a in rv]
    rn = [(math.sin(a), 0, math.cos(a) / MIT_ZS) for a in rv]
    p.add("mitre_studs", g.instances(g.dome(0.0055, 0.0045, 6, 1), rpos, rn), "RH_Silver", "head", lod1=None, tint=DARK(0.8))
    p.add("mitre_apex", spikes([((0, 1.318, 0), (0, 1, 0), 0.026, 0.0085)], seed=2, flat=0.0, sides=4, tip=0.55), "RH_Silver", "head", tint=DARK(0.85))
    # lappets hang behind the ears over the shoulders
    for sgn, nm in ((1, "L"), (-1, "R")):
        rows, cols = 9, 3
        grid = []
        for i in range(rows):
            t = i / (rows - 1)
            y = 1.074 - 0.19 * t
            w = 0.046 - 0.008 * t
            z = -0.058 - 0.060 * smoothstep(0.0, 1.0, t) - 0.01 * math.sin(t * 5 + sgn)
            xc = sgn * (0.058 + 0.004 * t)
            grid.append([(xc + u * w, y - (0.012 * (1 + u) if i == rows - 1 else 0.0), z - 0.012 * abs(u)) for u in (-0.5, 0.0, 0.5)])
        G = np.array(grid)[::-1]
        lap = g.loft(G[:, ::-1], closed=False, crease=70, v_tile=0.25, u_tile=0.25)
        p.add(f"lappet_{nm}", lap, "RH_Cloth", None, skin=LAP_SKIN, uv_scale=2, tint=lambda Q: (0.26 + 0.30 * smoothstep(0.9, 1.08, Q[:, 1]))[:, None] * np.array([0.95, 1.0, 1.1]))
        tip = g.tube([(sgn * 0.062, 0.894, -0.128), (sgn * 0.062, 0.883, -0.130), (sgn * 0.062, 0.874, -0.132)], [0.011, 0.009, 0.0], sides=5, samples=1, cap=None, smooth=False)
        p.add(f"lappet_tip_{nm}", tip, "RH_Silver", None, skin=LAP_SKIN, lod1=None, tint=DARK(0.8))


# ======================================================================================= staff, chain, lantern, runes
def on_staff(y):
    """Point on the staff axis at height y."""
    t = (S_TOP[1] - y) / (S_TOP[1] - S_FOOT[1])
    return S_TOP + (S_FOOT - S_TOP) * t


def glyph_bars(kind, w=0.0042):
    def bar(x0, y0, x1, y1):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) - 90
        return g.extrude(g.rect_poly(w, L), 0.003, 0.0006, 1).rotated(0, 0, ang).translated((x0 + x1) / 2, (y0 + y1) / 2, 0)
    if kind == 0:
        return [bar(-0.006, -0.022, -0.006, 0.022), bar(-0.006, 0.022, 0.012, 0.006), bar(-0.006, 0.004, 0.012, -0.012)]
    if kind == 1:
        return [bar(-0.010, 0.022, 0.006, 0.004), bar(0.006, 0.004, -0.008, -0.004), bar(-0.008, -0.004, 0.010, -0.022)]
    if kind == 2:
        return [bar(0.0, -0.022, 0.0, 0.022), bar(-0.012, 0.010, 0.012, 0.010), bar(-0.010, -0.008, 0.010, -0.008)]
    if kind == 3:
        return [bar(-0.010, -0.022, 0.0, 0.022), bar(0.0, 0.022, 0.010, -0.022), bar(-0.006, 0.0, 0.006, 0.0)]
    return [bar(-0.010, -0.020, 0.010, 0.020), bar(0.010, -0.020, -0.010, 0.020)]


def staff(p: Piece):
    ys = [0.226, 0.45, 0.72, 1.0, 1.28]
    shaft = g.tube([on_staff(y) for y in ys], [0.0215, 0.0185, 0.0165, 0.0150, 0.0140], sides=7, samples=3, cap=None, up=(1, 0, 0))
    p.add("staff_shaft", shaft.noised(0.0042, 12, 2, seed=6), "RH_Obsidian", "weapon", uv_scale=2)
    x = S_TOP[0]
    crook = g.tube([S_TOP + V(0, -0.01, 0), (x, 1.322, 0.134), (x, 1.356, 0.152), (x, 1.382, 0.186), (x, 1.396, 0.226), (x, 1.399, 0.258), (x, 1.390, 0.288), (x, 1.366, 0.304), (x, 1.340, 0.298)],
                   [0.0140, 0.0148, 0.0152, 0.0148, 0.0138, 0.0124, 0.0108, 0.0088, 0.0058], sides=7, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("staff_crook", crook.noised(0.0036, 12, 2, seed=7), "RH_Obsidian", "weapon", uv_scale=2)
    bands = []
    for y, r in ((0.50, 0.0225), (0.80, 0.0195), (1.05, 0.0178), (1.24, 0.0170)):
        c = on_staff(y)
        bands.append(g.lathe([(r + 0.002, -0.010), (r + 0.005, -0.006), (r + 0.005, 0.006), (r + 0.002, 0.010)], 10, crease=35).aimed(-A_S, c))
    p.add("staff_bands", merge(bands), "RH_Silver", "weapon", tint=DARK(0.85))
    p.add("staff_foot", spikes([(on_staff(0.232), (0, -1, 0.1), 0.06, 0.014)], seed=2, flat=0.1, sides=5, tip=0.5), "RH_Ice", "weapon")
    p.add("staff_ice", cluster(on_staff(0.98) + V(-0.012, 0, -0.004), (-0.5, 0.8, 0.2), 4, (0.05, 0.11), (0.008, 0.014), spread=0.02, tilt=30, seed=12, flat=0.3), "RH_Ice", "weapon")
    p.add("staff_ice_low", cluster(on_staff(0.42) + V(0.0, 0, 0.012), (0.0, 0.6, 1.0), 3, (0.04, 0.08), (0.008, 0.013), spread=0.02, tilt=30, seed=15, flat=0.3), "RH_Ice", "weapon", lod1=None)
    # p.add("crook_ice", cluster(V(x, 1.405, 0.200), (0.0, 0.85, 0.35), 3, (0.015, 0.030), (0.006, 0.009), spread=0.012, tilt=30, seed=17, flat=0.3), "RH_Ice", "weapon", lod1=None)
    wraps = [g.torus(0.0178, 0.0036, 8, 4).aimed(-A_S, on_staff(0.865 + 0.0115 * i)) for i in range(7)]
    p.add("staff_wraps", merge(wraps), "RH_Cloth", "weapon", uv_scale=2, lod1=None, tint=DARK(0.5))


def lantern(p: Piece):
    cx, cz = CX, CZ
    pivot = tuple(PIV)
    chain = g.tube([pivot, (cx, 1.364, cz), tuple(CH1), (cx, 1.320, cz), tuple(CH2 + V(0, 0.004, 0))], 0.0050, sides=5, samples=3, cap="round", cap_steps=1,
                   radius_fn=lambda t: 0.62 + 0.38 * abs(math.sin(t * 34)))
    hook = g.torus(0.0120, 0.0030, 10, 4).rotated(0, 0, 90).translated(*pivot)
    p.add("chain", merge([chain, hook]), "RH_Silver", None, skin=CHAIN_SKIN, tint=DARK(0.85))
    cap = g.lathe([(0.0, 1.304), (0.014, 1.299), (0.030, 1.289), (0.046, 1.274), (0.0, 1.274)], 10, crease=35).translated(cx, 0, cz)
    base = g.lathe([(0.0, 1.138), (0.026, 1.141), (0.040, 1.152), (0.030, 1.168), (0.0, 1.168)], 10, crease=35).translated(cx, 0, cz)
    drop = g.tube([(cx, 1.140, cz), (cx, 1.124, cz), (cx, 1.112, cz)], [0.008, 0.007, 0.0], sides=5, samples=1, cap=None, smooth=False)
    p.add("lantern_cap_base", merge([cap, base, drop]), "RH_Silver", "cape_2", tint=DARK(0.9))
    bars = []
    for k in range(4):
        a = math.radians(45 + k * 90)
        bars.append(g.tube([(cx + 0.040 * math.sin(a), 1.160, cz + 0.040 * math.cos(a)), (cx + 0.022 * math.sin(a), 1.280, cz + 0.022 * math.cos(a))],
                           0.0050, sides=4, samples=1, cap="round", cap_steps=1, smooth=False))
    rings_ = [g.torus(0.040, 0.0040, 10, 3).translated(cx, 1.162, cz), g.torus(0.0245, 0.0040, 10, 3).translated(cx, 1.275, cz), g.torus(0.040, 0.0036, 10, 3).translated(cx, 1.222, cz)]
    p.add("lantern_cage", merge(bars + rings_), "RH_Silver", "cape_2", tint=DARK(0.9))
    glass = g.superellipsoid((0.034, 0.060, 0.034), 0.6, 0.7, 4, 10).translated(*LAN_C)
    p.add("lantern_glass", glass, "RH_Ice", "cape_2", occluder=False, lod1="keep")
    core = g.superellipsoid((0.020, 0.036, 0.020), 0.9, 0.9, 4, 9).translated(*LAN_C)
    p.add("lantern_core", core, "RH_Glow", "cape_2", bake=False, lod1="keep")


R_RING = 0.105


def runes(p: Piece):
    tab_poly = np.array([(-0.024, -0.034), (0.024, -0.034), (0.029, 0.0), (0.024, 0.034), (-0.024, 0.034), (-0.029, 0.0)])
    tabs, gly = [], []
    dys = (-0.030, 0.050, 0.010, 0.056, 0.020)
    for k in range(5):
        a = k * 72.0 + 10
        tilt = 12 + 4 * k
        t = g.extrude(tab_poly, 0.013, 0.004, 1).rotated(tilt, 0, 4 * (k - 2))
        glf = merge(glyph_bars(k)).translated(0, 0, 0.0085).rotated(tilt, 0, 4 * (k - 2))
        pos = LAN_C + np.array([R_RING * math.sin(math.radians(a)), dys[k], R_RING * math.cos(math.radians(a))])
        tabs.append(t.rotated(0, a, 0).translated(*pos))
        gly.append(glf.rotated(0, a, 0).translated(*pos))
    p.add("rune_tablets", merge(tabs), "RH_Ice", "runes")
    p.add("rune_glyphs", merge(gly), "RH_Glow", "runes", bake=False, lod1=None)
    motes = []
    for k in range(3):
        a = math.radians(40 + k * 120)
        motes.append(g.superellipsoid((0.007, 0.011, 0.007), 0.6, 0.6, 3, 6).translated(CX + 0.100 * math.sin(a), LAN_C[1] + 0.005 + 0.035 * k, CZ + 0.100 * math.cos(a)))
    p.add("rune_motes", merge(motes), "RH_Ice", "runes", lod1=None)


# ======================================================================================= animation
class BAnim(Animator):
    """Animator + (a) skirt pins: skirt_* bones are blended toward their rest WORLD pose so the hem stays planted on the plinth while the
    body bobs / lunges / kneels, and (b) a gravity-hung lantern: `hang(t)` is the world direction pivot -> lantern; `top` is rotated so the
    chain follows it whatever the staff does (cape_1/cape_2 then lag it with the accel-driven spring; the `runes` ring rides cape_2)."""

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
    a.secondary(["cape_1", "cape_2"], driver="top", freq=2.3, zeta=0.34, follow=1.0, accel=0.040, max_deg=14, decay=0.85)
    return a


def _z():
    return V(0, 0, 0)


def swing(ax_deg, az_deg):
    """Chain direction for a hang angle toward +X (character's left) / +Z (forward), degrees."""
    ax, az = math.radians(ax_deg), math.radians(az_deg)
    return nrm(V(math.sin(ax), -math.cos(ax) * math.cos(az), math.sin(az)))


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


def _runes(a, spin, wob=(2.4, 0.0, 1.8), wob_f=0.8, wob_ph=0.3):
    """Rune ring: `spin` = degrees about the lantern's vertical axis (Curve keys or Fn), plus a small gimbal wobble."""
    sp = spin if callable(spin) else Curve(spin)
    a.rot("runes", Fn(lambda t: V(0, float(np.asarray(sp(t)).reshape(-1)[0]), 0)))
    a.rot("runes", Wave(V(*wob), wob_f, wob_ph))


RUNE_SCALE = {}


# ---------------------------------------------------------------------------------------------- Idle
def clip_idle(rig):
    a = _anim(rig)
    T = 3.4
    M.idle(a, period=T, breath=1.0, shift=0.9, sway=0.008, look=0.8, hands=False)
    _hand(a, [(0, WR0)], [(0, A_S)], world=[(0, 1.0)])
    a.rot("arm_L", Wave(V(-1.2, 0, 0.8), 1 / T, 0.4))
    a.rot("hand_L", Wave(V(-2.0, 0, 0), 1 / T, 0.5))
    a.rot("wrist_L", Wave(V(-3.0, 0, 0), 1 / T, 0.6))
    a.hang = Fn(lambda t: swing(5.0 * math.sin(TAU * 2 * t / T + 0.4), 3.5 * math.sin(TAU * t / T + 1.2) + 1.0 * math.sin(TAU * 3 * t / T)))
    a.rot("runes", Fn(lambda t: V(0, 360.0 * t / T, 0)))
    a.rot("runes", Wave(V(2.6, 0, 1.8), 1 / T, 0.3))
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
    P = Fn(lambda t: WR0 + V(0.0, 0.03, 0.0) * tap(t))
    _hand(a, P, [(0, A_S), (0.25, nrm(V(0.0, -1.0, 0.075)), "in_out_cubic"), (0.5, A_S, "in_out_cubic"), (0.75, nrm(V(0.0, -1.0, 0.075)), "in_out_cubic"), (1.0, A_S, "in_out_cubic")],
          world=lambda t: 0.8)
    a.rot("arm_L", Wave(V(0.0, 0, 0.6), 1 / T, 0.1))
    a.rot("wrist_L", Wave(V(5, 0, 0), 1 / T, 0.30))
    a.hang = Fn(lambda t: swing(6.0 * math.sin(TAU * t / T + 1.0), -9.0 * math.sin(TAU * 2 * t / T + 0.5) + 3.0))
    a.rot("runes", Fn(lambda t: V(0, 360.0 * t / T, 0)))
    a.rot("runes", Wave(V(3.0, 0, 2.2), 1 / T, 0.2))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- HitReact
def clip_hit(rig):
    a = _anim(rig)
    T = 0.45
    z = _z()
    a.pos("body", Curve([(0, z), (0.08, V(0, -0.026, -0.060), "out_cubic"), (0.19, V(0, -0.010, -0.022), "in_out_cubic"), (0.30, V(0, -0.012, 0.008), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.08, V(-8, 2, 3), "out_cubic"), (0.19, V(2, -1, -1), "in_out_cubic"), (0.30, V(-1, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.095, V(-8, 3, 2), "out_cubic"), (0.21, V(3, -2, 0), "in_out_cubic"), (0.32, V(-1.2, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.11, V(-10, 4, 3), "out_cubic"), (0.23, V(3, -3, -1), "in_out_cubic"), (0.34, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.12, V(-12, 6, 4), "out_cubic"), (0.25, V(4, -4, -1), "in_out_cubic"), (0.36, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.13, V(-14, 8, 5), "out_cubic"), (0.27, V(5, -4, -2), "in_out_cubic"), (0.38, V(-1.5, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_L", Curve([(0, z), (0.10, V(0, 0, 5), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.10, V(0, 0, -5), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("arm_L", Curve([(0, z), (0.10, V(10, 0, 8), "out_cubic"), (0.25, V(-4, 0, 2), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.12, V(8, 0, 0), "out_cubic"), (0.27, V(-10, 0, 0), "in_out_cubic"), (T, z, "in_out_cubic")]))
    _hand(a, [(0, WR0), (0.09, WR0 + V(0.012, 0.018, -0.045), "out_cubic"), (0.21, WR0 + V(-0.004, -0.006, 0.012), "in_out_cubic"), (T, WR0, "in_out_cubic")],
          [(0, A_S), (0.09, nrm(V(0.0, -1.0, -0.12)), "out_cubic"), (0.21, nrm(V(0.0, -1.0, 0.09)), "in_out_cubic"), (T, A_S, "in_out_cubic")], world=[(0, 1.0)])
    a.hang = Curve([(0, V(0, -1, 0)), (0.10, swing(8, 34), "out_cubic"), (0.25, swing(-3, -16), "in_out_cubic"), (0.37, swing(0, 6), "in_out_cubic"), (T, V(0, -1, 0), "in_out_cubic")])
    M.set_foot(a, "foot_L", pos=Curve([(0, z), (0.1, V(0, 0, -0.012), "out_cubic"), (T, z, "in_out_cubic")]))
    M.stabilize(a, "head", 0.25)
    a.rot("runes", Curve([(0, z), (0.10, V(0, 55, 0), "out_cubic"), (T, V(0, 70, 0), "in_out_cubic")]))
    a.rot("runes", Curve([(0, z), (0.10, V(8, 0, -6), "out_cubic"), (0.25, V(-4, 0, 3), "in_out_cubic"), (T, z, "in_out_cubic")]))
    RUNE_SCALE["HitReact"] = [(0, (1, 1, 1)), (0.08, (0.80, 0.9, 0.80), "out_cubic"), (0.2, (1.08, 1, 1.08), "in_out_cubic"), (T, (1, 1, 1), "in_out_cubic")]
    return a, T, False, 60, ()


# ---------------------------------------------------------------------------------------------- Victory
def clip_victory(rig):
    a = _anim(rig)
    T = 1.8
    z = _z()
    a.pos("body", Curve([(0, z), (0.16, V(0, -0.016, 0), "in_out_cubic"), (0.58, V(0, 0.016, 0.008), ("spring", 0.2, 1.5)), (T, V(0, 0.012, 0.008), "in_out_cubic")]))
    a.rot("body", Curve([(0, z), (0.16, V(3, 0, 0)), (0.58, V(-3, -3, -1), "out_cubic"), (T, V(-2, -2, -1), "in_out_cubic")]))
    a.rot("spine", Curve([(0, z), (0.16, V(4, 0, 0)), (0.62, V(-6, -3, 0), ("spring", 0.15, 1.5)), (T, V(-5, -2, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, z), (0.16, V(5, 0, 0)), (0.64, V(-8, -4, 0), ("spring", 0.15, 1.5)), (T, V(-7, -3, 0), "in_out_cubic")]))
    a.rot("neck", Curve([(0, z), (0.66, V(-6, 4, 0), "out_cubic"), (T, V(-5, 3, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, z), (0.68, V(-10, 6, 0), ("spring", 0.15, 1.5)), (T, V(-9, 5, 0), "in_out_cubic")]))
    a.rot("clavicle_R", Curve([(0, z), (0.18, V(0, 0, 2), "in_out_cubic"), (0.66, V(0, 0, -8), "out_cubic"), (T, V(0, 0, -8))]))
    a.rot("clavicle_L", Curve([(0, z), (0.66, V(0, 0, 6), "out_cubic"), (T, V(0, 0, 6))]))
    # the staff is hoisted overhead, planted taller: the grip rises and the crook leans over
    P_UP, D_UP = WR0 + V(0.02, 0.19, 0.10), nrm(V(0.0, -0.95, -0.30))
    _hand(a, [(0, WR0), (0.18, WR0 + V(0, -0.012, 0.0), "in_out_cubic"), (0.62, P_UP, ("spring", 0.10, 1.5)), (T, P_UP + V(0, 0.010, 0), "in_out_cubic")],
          [(0, A_S), (0.18, A_S, "in_out_cubic"), (0.62, D_UP, ("spring", 0.12, 1.5)), (T, D_UP, "in_out_cubic")])
    a.rot("arm_L", Curve([(0, z), (0.22, V(6, 0, 4), "in_out_cubic"), (0.74, V(-18, 0, 30), ("spring", 0.12, 1.5)), (T, V(-16, 0, 28), "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.74, V(-26, 0, 0), ("spring", 0.12, 1.5)), (T, V(-24, 0, 0), "in_out_cubic")]))
    a.rot("wrist_L", Curve([(0, z), (0.78, V(-28, 0, 0), "out_cubic"), (T, V(-26, 0, 0))]))

    def vic_hang(t):                                  # the lantern swings wide as the staff goes up, then damps
        if t < 0.5:
            return swing(4.0 * math.sin(t * 6), 3.0)
        u = t - 0.5
        return swing(30.0 * math.exp(-u / 0.55) * math.sin(TAU * u / 0.75), 16.0 * math.exp(-u / 0.5) * math.cos(TAU * u / 0.9))
    a.hang = Fn(vic_hang)
    for nm in ("foot_L", "foot_R"):
        M.set_foot(a, nm, rot=Curve([(0, z), (0.22, z), (0.56, V(5, 0, 0), "out_cubic"), (T, V(5, 0, 0))]),
                   pos=Curve([(0, z), (0.22, z), (0.56, V(0, 0.005, 0), "out_cubic"), (T, V(0, 0.005, 0))]))
    M.stabilize(a, "head", 0.0)
    _runes(a, [(0, 0.0), (0.25, 0.0), (1.15, 560.0, "in_out_cubic"), (T, 720.0, "in_out_cubic")])
    RUNE_SCALE["Victory"] = [(0, (1, 1, 1)), (0.3, (1, 1, 1)), (1.0, (1.25, 1.1, 1.25), "in_out_cubic"), (T, (1, 1, 1), "in_out_cubic")]
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Taunt
def clip_taunt(rig):
    """The staff tips forward so the lantern clears the mitre, the runes spin up fast, then it plants and the free hand points at the foe."""
    a = _anim(rig)
    T = 1.5
    z = _z()
    P_W, D_W = WR0 + V(0.03, 0.17, 0.10), nrm(V(0.0, -0.95, -0.30))
    _hand(a, [(0, WR0), (0.22, P_W, "out_cubic"), (0.80, P_W + V(0, 0.01, 0), "in_out_cubic"), (1.10, WR0 + V(0, 0.01, 0.02), "in_out_cubic"), (T, WR0, "in_out_cubic")],
          [(0, A_S), (0.22, D_W, "out_cubic"), (0.80, D_W, "in_out_cubic"), (1.10, nrm(V(0.0, -1.0, 0.05)), "in_out_cubic"), (T, A_S, "in_out_cubic")])

    def tn_hang(t):
        if t < 0.18:
            return swing(3.0, 3.0)
        u = t - 0.18
        if u < 0.72:
            return swing(9.0 * math.sin(TAU * u / 0.5) * smoothstep(0.0, 0.2, u), 8.0 + 6.0 * math.sin(TAU * u / 0.36))
        s = u - 0.72
        return swing(0.0, 8.0 * math.exp(-s / 0.30) * math.cos(TAU * s / 0.9))
    a.hang = Fn(tn_hang)
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
    _runes(a, [(0, 0.0), (0.30, 100.0, "in_out_cubic"), (0.85, 820.0, "in_out_cubic"), (1.15, 1000.0, "out_cubic"), (T, 1080.0, "in_out_cubic")], wob=(3.5, 0.0, 2.6), wob_f=2.0)
    RUNE_SCALE["Taunt"] = [(0, (1, 1, 1)), (0.30, (1.05, 1, 1.05), "in_out_cubic"), (0.85, (1.35, 1.1, 1.35), "in_out_cubic"), (1.15, (1.2, 1.05, 1.2), "out_cubic"), (T, (1, 1, 1), "in_out_cubic")]
    return a, T, False, 60, ()


# ---------------------------------------------------------------------------------------------- Surrender
def clip_surrender(rig):
    """Stagger, the staff slips from the grip (free fall, two bounces, lies on the plinth with the lantern clattering beside it), a one-knee
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
    # ---- the staff leaves the hand at 0.45: free fall, two bounces, lies along the plinth's right side (tangent to the kneeling figure) with
    # the crook curled UP over the front rim; the lantern hangs from the crook outside the plinth wall and swings to rest
    head_dir = V(0.0, 0.0, -1.0)                                    # grip -> foot
    TGT = V(-0.30, 0.0, 0.335)                                      # where the chain pivot ends up (xz): beyond the rim, outside the plinth tiers
    a.hang = Fn(lambda t: swing(0.0, 0.0))
    kw = dict(up_local=None, roll_deg=180.0)
    M.release_weapon(a, "weapon", 0.45, 0.22, 0.022, A_S, tuple(head_dir), land_xz=(0.0, 0.0), **kw)
    fn0 = a.overrides[-1].fn
    R0_, p0_ = fn0(99.0)
    piv0 = R0_ @ (PIV - W0) + p0_
    a.overrides.pop()
    land = (float(TGT[0] - piv0[0]), float(TGT[2] - piv0[2]))
    t_land = M.release_weapon(a, "weapon", 0.45, 0.22, 0.022, A_S, tuple(head_dir), land_xz=land, **kw)
    a.hang = None
    d_lie = nrm(V(-0.10, -0.99, 0.07))

    def sg_hang(t):
        if t < 0.45:
            return swing(3.0 * math.sin(t * 5), 4.0)
        u = t - 0.45
        w = smoothstep(0.0, max(t_land - 0.45, 0.2) + 0.30, u)
        wob = math.exp(-u / 0.60) * math.sin(TAU * u / 0.60)
        d0 = nrm(swing(30.0 * wob, 20.0 * math.exp(-u / 0.45) * math.cos(TAU * u / 0.55)))
        return nrm(d0 * (1 - w) + d_lie * w + V(-d0[2], 0, d0[0]) * 0.0)
    a.hang = Fn(sg_hang)
    _runes(a, [(0, 0.0), (0.30, 40.0, "out_cubic"), (1.2, 90.0, "out_cubic"), (T, 100.0, "out_cubic")], wob=(1.2, 0.0, 1.0), wob_f=1.0)
    RUNE_SCALE["Surrender"] = [(0, (1, 1, 1)), (0.45, (1, 1, 1)), (0.75, (0.80, 0.55, 0.80), "out_cubic"), (1.5, (0.52, 0.42, 0.52), "in_out_cubic"), (T, (0.45, 0.40, 0.45), "in_out_cubic")]
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
    _hand(a, [(0, WR0), (0.14, WR0 + V(0.0, 0.02, -0.02), "in_out_cubic"), (0.50, P_WIND, "in_out_cubic"), (0.92, P_WIND + V(0, 0.015, -0.03), "in_out_cubic"),
              (I, P_HIT, "snap_in"), (1.28, P_FOL, "out_cubic"), (1.50, P_FOL, {"tan": "flat"}), (2.0, WR0 + V(0.02, 0.01, 0.05), "in_out_cubic"), (T, WR0, "in_out_cubic")],
          [(0, A_S), (0.14, A_S, "in_out_cubic"), (0.50, D_WIND, "in_out_cubic"), (0.92, D_WIND, "in_out_cubic"), (I, D_HIT, "snap_in"), (1.28, D_FOL, "out_cubic"),
           (1.50, D_FOL, {"tan": "flat"}), (2.0, nrm(V(0.0, -1.0, 0.05)), "in_out_cubic"), (T, A_S, "in_out_cubic")])

    def hang(t):                                      # the lantern sways back as the staff rises, then whips forward at the thrust and damps
        if t < 0.92:
            return swing(3.0 * math.sin(6.0 * t) * smoothstep(0.1, 0.4, t), -6.0 * smoothstep(0.35, 0.92, t) + 3.0)
        if t <= I:
            u = (t - 0.92) / (I - 0.92)
            return swing(0.0, -6.0 + 56.0 * u * u)
        s = t - I
        return swing(5.0 * math.exp(-s / 0.5) * math.sin(TAU * s / 0.7), 50.0 * math.exp(-s / 0.50) * math.cos(TAU * s / 1.05))
    a.hang = Fn(hang)
    # left hand: raised, palm out, a conjuring push at the release
    a.rot("arm_L", Curve([(0, z), (0.30, V(-30, 0, 6), "in_out_cubic"), (0.80, V(-80, 0, 10), "in_out_cubic"), (I, V(-90, 0, 6), "snap_in"), (1.40, V(-62, 0, 6), "out_cubic"), (2.0, V(-8, 0, 2), "in_out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("hand_L", Curve([(0, z), (0.30, z), (0.80, V(-22, 0, 0), "in_out_cubic"), (I, V(-8, 0, 0), "snap_in"), (1.40, V(-20, 0, 0), "out_cubic"), (T, z, "in_out_cubic")]))
    a.rot("wrist_L", Curve([(0, z), (0.80, V(-14, 0, 0), "in_out_cubic"), (I + 0.02, V(-26, 0, 0), ("spring", 0.2, 1.5)), (1.5, V(-12, 0, 0)), (T, z, "in_out_cubic")]))
    # pelvis leads: coil back, rise, LUNGE into the release just ahead of the staff
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
    # the runes whirl up (accelerating), then converge on the lantern at the thrust: the beam leaves socket_cast at IMPACT
    _runes(a, [(0, 0.0), (0.25, 0.0), (0.95, 720.0, "in_quad"), (I, 870.0, "out_quad"), (1.30, 900.0, "out_quad"), (T, 1080.0, "in_out_cubic")], wob=(2.0, 0.0, 1.5), wob_f=1.0)
    RUNE_SCALE["Attack"] = [(0, (1, 1, 1)), (0.30, (1, 1, 1)), (0.95, (1.18, 1.05, 1.18), "in_out_cubic"), (I, (0.26, 0.70, 0.26), "in_expo"), (1.30, (0.55, 0.9, 0.55), "out_quad"),
                            (2.0, (1, 1, 1), "in_out_cubic"), (T, (1, 1, 1))]
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
        clip = a.bake(name, dur, loop=loop, fps=fps, keep_times=keep)
        if name in RUNE_SCALE:
            clip.keys("runes", "scale", RUNE_SCALE[name])
        out.append(clip)
    if cache:
        with open(cache, "wb") as fh:
            pickle.dump(out, fh)
    return out


# ======================================================================================= build
def build(log=print):
    rig = make_rig()
    p = Piece("rime", "bishop", rig, make_clips(rig), impact_time=1.10, strike_range=1.50, attack_style="ranged", seed=7)
    rc.pedestal_parts(p)
    robe(p)
    torso_details(p)
    mantle_and_collar(p)
    arms(p)
    head(p)
    staff(p)
    lantern(p)
    runes(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
