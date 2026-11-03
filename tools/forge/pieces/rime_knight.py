"""rime_knight - Rime Gravewind Rider.

A SKELETAL FROST WAR-HORSE carrying a crouched skeletal rider in wired obsidian plate.  The horse is the identity cue: a tall arched
neck of dark sinew with bone vertebrae and a crystal-shard mane, a bone-white skull with glowing cyan eyes and a black half-chanfron,
ice-shard ears, a hollow rib cage lit from inside, obsidian barding plates, a crystal-shard tail.  Everything above y 1.10 is horse; the
rider tops out at 1.08, the ears at 1.29 and the mane tips at 1.30.  The rider carries a reversed hooked glaive trailing over the croup.

Rig: quadruped_rig (spine chain body > mount_body > mount_chest, neck_1/2, mount_head, jaw, 4 legs x upper/lower/hoof, tail_1..3, three
mane bones) + the humanoid rider (rider_pelvis under the saddle bone `top`).  Smooth chain skins on legs / neck / barrel / tail / mane,
rigid barding plates.  Procedural IK clips: canter, rear, leap, headbutt + glaive strike, kneel.  Built from docs/art/rime_knight.md.
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
from anim import Animator, Curve, Fn, Wave, Skin, humanoid_rig, quadruped_rig, limb_tube   # noqa: E402
from anim.skin import Chain, _ss                   # noqa: E402
from anim import motion as M                       # noqa: E402
import _emberhold_common as C                      # noqa: E402  (pauldron lames only)
import _rime_common as rc                          # noqa: E402
from _rime_common import shard, spikes, cluster, frost_layer    # noqa: E402

ASSET_ID = "rime_knight"
V = lambda *x: np.array(x, dtype=float)            # noqa: E731
DK = lambda v: (lambda P: np.full(len(P), v))      # noqa: E731

# ======================================================================================= joints (rest pose, world coordinates)
HEAD_PITCH = 55.0                                   # head hangs this many degrees below horizontal
_HP = (0.0, 1.19, 0.315)
_a = math.radians(HEAD_PITCH)
_JAW_PIV_LOCAL = (0.0, -0.05, 0.05)
_JAW = (0.0, _HP[1] + _JAW_PIV_LOCAL[1] * math.cos(_a) - _JAW_PIV_LOCAL[2] * math.sin(_a), _HP[2] + _JAW_PIV_LOCAL[1] * math.sin(_a) + _JAW_PIV_LOCAL[2] * math.cos(_a))
JQ = dict(rump=(0, 0.66, -0.22), barrel=(0, 0.64, -0.04), withers=(0, 0.78, 0.12), neck_1=(0, 0.85, 0.17), neck_2=(0, 1.03, 0.245),
          head=_HP, jaw=_JAW, seat=(0, 0.80, -0.06),
          hip_L=(0.10, 0.64, -0.22), hock_L=(0.115, 0.435, -0.33), fetlock_L=(0.115, 0.29, -0.27), hoof_L=(0.115, 0.22, -0.235),
          shoulder_L=(0.10, 0.70, 0.10), elbow_L=(0.11, 0.45, 0.185), fetlock_F_L=(0.11, 0.30, 0.155), hoof_F_L=(0.11, 0.22, 0.185),
          tail_1=(0, 0.71, -0.30), tail_2=(0, 0.60, -0.365), tail_3=(0, 0.47, -0.385))
JR = dict(pelvis=(0, 0.835, -0.10), spine=(0, 0.875, -0.075), chest=(0, 0.935, -0.03), neck=(0, 0.985, 0.025), head=(0, 1.005, 0.055),
          top=(0, 0.80, -0.06),
          clavicle_L=(0.055, 0.955, -0.005), shoulder_L=(0.155, 0.945, 0.0), elbow_L=(0.185, 0.885, 0.065), wrist_L=(0.10, 0.875, 0.15),
          hip_L=(0.095, 0.82, -0.10), knee_L=(0.20, 0.74, 0.04), ankle_L=(0.20, 0.54, 0.01), toe_L=(0.20, 0.51, 0.09),
          elbow_R=(-0.19, 0.875, 0.03), wrist_R=(-0.20, 0.857, 0.11))
# reversed glaive: butt forward-down in the rider's right fist, hooked blade trailing up and back over the croup
GD = V(0.10, 0.50, -0.86)
GD = GD / np.linalg.norm(GD)
G_LEN, G_GRIP = 0.66, 0.20                          # axis length, butt -> grip distance
GLAIVE_B = V(*JR["wrist_R"]) - GD * G_GRIP
GLAIVE_T = GLAIVE_B + GD * G_LEN
GLAIVE_C = (GLAIVE_B + GLAIVE_T) / 2
MANE_ROOTS = [(0, 1.19, 0.275), (0, 0.99, 0.205), (0, 0.84, 0.13)]    # mane_1..3 pivots (crest)


def make_rig() -> Rig:
    r = quadruped_rig(JQ)
    hr = humanoid_rig(JR, weapon=tuple(GLAIVE_C), pelvis_name="rider_pelvis")
    for name in hr.order:
        if name in ("root", "top"):
            continue
        b = hr.bones[name]
        r.add(name, "top" if name == "rider_pelvis" else b.parent, b.pos)
    for a_, b_ in hr.alias.items():
        r.add_alias(a_, b_)
    r.add("mane_1", "neck_2", MANE_ROOTS[0])
    r.add("mane_2", "neck_1", MANE_ROOTS[1])
    r.add("mane_3", "mount_chest", MANE_ROOTS[2])
    r.socket("socket_weapon_R", "weapon", tuple(GLAIVE_T))
    r.socket("socket_cast", "mount_body", (0, 0.60, 0.0))
    r.socket("socket_impact", "mount_body", (-0.10, 0.78, 0.62))
    r.socket("socket_head", "mount_head", (0, 1.36, 0.30))
    return r


# ======================================================================================= geometry helpers
def spow(x, p):
    return np.sign(x) * np.abs(x) ** p


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


def orient_out(m, centres):
    """Flip a shell whose normals point toward the nearest reference centre instead of away from it."""
    fn = m.face_normals()
    cen = m.P[m.F].mean(1)
    Cc = np.asarray(centres, float)
    j = np.linalg.norm(cen[:, None, :] - Cc[None, :, :], axis=2).argmin(1)
    return m.flipped() if np.einsum("ij,ij->i", fn, cen - Cc[j]).mean() < 0 else m


class Stn:
    """A swept super-ellipse body: stations along a spline with half-width hw (along X) and half-depth hd, frame T/X/N.
    N = X x T (front for a rising path, DOWN for a path along +Z).  th=0 -> +X side, th=90 -> +N, 270 -> -N."""

    def __init__(self, path, hw, hd, e=2.3, samples=3, up=(1, 0, 0)):
        ctrl = np.asarray(path, float)
        pts = np.asarray(g.spline(ctrl, samples), float)
        ds = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(ds)])
        self.L = s[-1]
        self.s = s / self.L
        cs = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(ctrl, axis=0), axis=1))])
        cs = cs / cs[-1]
        self.c = pts
        self.hw = np.interp(self.s, cs, hw)
        self.hd = np.interp(self.s, cs, hd)
        T = np.gradient(pts, axis=0)
        T = T / np.linalg.norm(T, axis=1, keepdims=True)
        upv = np.asarray(up, float)
        X = upv[None, :] - (T @ upv)[:, None] * T
        X = X / np.linalg.norm(X, axis=1, keepdims=True)
        self.T, self.X, self.N = T, X, np.cross(X, T)
        self.e = e

    def at(self, u):
        f = lambda A: np.array([np.interp(u, self.s, A[:, k]) for k in range(3)])    # noqa: E731
        return f(self.c), unit(f(self.X)), unit(f(self.N)), float(np.interp(u, self.s, self.hw)), float(np.interp(u, self.s, self.hd)), unit(f(self.T))

    def pt(self, u, th, grow=0.0, off=0.0):
        c, X, N, hw, hd, _ = self.at(u)
        th = np.radians(np.asarray(th, float))
        pw = 2.0 / self.e
        a = (hw + grow) * spow(np.cos(th), pw)
        b = (hd + grow) * spow(np.sin(th), pw)
        return c + off * N + a[..., None] * X + b[..., None] * N

    def ring_i(self, i, K=16, grow=0.0):
        th = np.linspace(0, TAU, K, endpoint=False)
        pw = 2.0 / self.e
        a = (self.hw[i] + grow) * spow(np.cos(th), pw)
        b = (self.hd[i] + grow) * spow(np.sin(th), pw)
        return self.c[i] + a[:, None] * self.X[i] + b[:, None] * self.N[i]

    def mesh(self, K=16, grow=0.0, cap0=True, cap1=True, crease=55.0, stride=1):
        idx = list(range(0, len(self.c), stride))
        if idx[-1] != len(self.c) - 1:
            idx.append(len(self.c) - 1)
        rings = np.stack([self.ring_i(i, K, grow) for i in idx])
        m = g.loft(rings, closed=True, cap_start=cap0, cap_end=cap1, crease=crease)
        vol = np.einsum("ij,ij->i", m.P[m.F[:, 0]], np.cross(m.P[m.F[:, 1]], m.P[m.F[:, 2]])).sum()
        if vol < 0:
            m = g.loft(rings[:, ::-1], closed=True, cap_start=cap0, cap_end=cap1, crease=crease)
        return m

    def shell(self, us, th0, th1, nth=9, grow=0.012, crease=50.0):
        """Open band over the stations at `us`, angles th0..th1 (scalars or one per u), pushed out by `grow` (scalar or per u)."""
        us = np.asarray(us, float)
        th0 = np.broadcast_to(np.asarray(th0, float), us.shape)
        th1 = np.broadcast_to(np.asarray(th1, float), us.shape)
        gr = np.broadcast_to(np.asarray(grow, float), us.shape)
        rings = np.stack([self.pt(u, np.linspace(a, b, nth), gg) for u, a, b, gg in zip(us, th0, th1, gr)])
        m = g.loft(rings, closed=False, crease=crease)
        return orient_out(m, [self.at(u)[0] for u in us])

    def edge(self, us, th, grow=0.012, r=0.005, sides=4):
        pts = [self.pt(u, th, grow) for u in us]
        return g.tube(pts, r, sides=sides, samples=1, cap="round", cap_steps=1, smooth=len(pts) > 2)


def tube_(p, name, pts, radii, mat, bone=None, skin=None, sides=7, samples=2, cap="round", up=(1, 0, 0), ellipse=(1, 1), uv=2, tint=None, noise=0.0, seed=1, **kw):
    m = g.tube(pts, radii, sides=sides, samples=samples, cap=cap, cap_steps=1, up=up, ellipse=ellipse)
    if noise:
        m = m.noised(noise, 26, 2, seed=seed)
    p.add(name, m, mat, bone, skin=skin, uv_scale=uv, tint=tint, **kw)


# ======================================================================================= skins
BARREL_SKIN = Skin.chain(["body", "mount_body", "mount_chest"], tip=(0, 0.62, 0.30), zone=0.45)
NECK_SKIN = Skin.chain(["mount_chest", "neck_1", "neck_2", "mount_head"], tip=(0, 1.26, 0.34), zone=0.40)
TAIL_SKIN = Skin.chain(["tail_1", "tail_2", "tail_3"], pre="body", tip=(0, 0.33, -0.375), zone=0.45)


def hind_skin(s):
    return Skin.chain([f"hind_upper_{s}", f"hind_lower_{s}", f"hind_hoof_{s}"], pre="body", tip=(JQ["hoof_L"][0] * (1 if s == "L" else -1), 0.22, -0.20), zone=0.42)


def fore_skin(s):
    return Skin.chain([f"fore_upper_{s}", f"fore_lower_{s}", f"fore_hoof_{s}"], pre="mount_chest", tip=(JQ["hoof_F_L"][0] * (1 if s == "L" else -1), 0.22, 0.215), zone=0.42)


class Fringe(Skin):
    """Mane skin: base follows the neck chain; the free flame tips (distance from the crest line) follow the three mane bones."""

    def __init__(self, base, crest_pts, bones=("mane_1", "mane_2", "mane_3"), reach=0.075, sig=0.075):
        self.base, self.crest, self.bones, self.reach, self.sig = base, np.asarray(crest_pts, float), bones, reach, sig

    def primary(self, rig):
        return rig.resolve("neck_1")

    def dense(self, P, rig):
        W = self.base.dense(P, rig)
        a = np.full(len(P), np.inf)
        for q0, q1 in zip(self.crest[:-1], self.crest[1:]):
            d = q1 - q0
            t = np.clip(((P - q0) @ d) / max(float(d @ d), 1e-12), 0, 1)
            a = np.minimum(a, np.linalg.norm(P - (q0 + t[:, None] * d), axis=1))
        a = _ss(0.010, self.reach, a)[:, None]
        ys = np.array([rig.pos(b)[1] for b in self.bones])
        bw = np.exp(-(((P[:, 1][:, None] - ys[None, :]) / self.sig) ** 2))
        bw = bw / bw.sum(1, keepdims=True)
        out = W * (1 - a)
        for k, b in enumerate(self.bones):
            out[:, rig.index(b)] += a[:, 0] * bw[:, k]
        return out




# ======================================================================================= the horse: body, legs, tail
BONE = "RH_Bone"
BARREL = Stn([(0, .655, -.335), (0, .66, -.30), (0, .655, -.24), (0, .645, -.14), (0, .645, -.04), (0, .65, .06), (0, .655, .14), (0, .635, .21), (0, .615, .26), (0, .60, .29)],
             [.04, .115, .14, .135, .145, .15, .14, .115, .075, .03], [.05, .125, .135, .14, .135, .15, .145, .14, .10, .04], e=2.3, samples=3)
NECK = Stn([(0, .745, .095), (0, .85, .17), (0, .95, .215), (0, 1.04, .25), (0, 1.12, .285), (0, 1.19, .315)],
           [.094, .086, .071, .060, .050, .043], [.124, .110, .094, .078, .064, .052], e=2.4, samples=4)


def barrel_z(z, th, grow=0.0):
    u = float(np.interp(z, BARREL.c[:, 2], BARREL.s))
    return BARREL.pt(u, th, grow)


def barrel_u(z):
    return float(np.interp(z, BARREL.c[:, 2], BARREL.s))


def horse_body(p: Piece):
    # ---- dark inner body (so the steed reads as a solid mass from afar), glowing frost-light panels seen between the ribs
    p.add("m_barrel", BARREL.mesh(K=16, grow=-0.024).noised(0.0022, 16, 3, seed=2), "RH_Armour", None, skin=BARREL_SKIN, uv_scale=2, tint=DK(0.8))
    zs = [-0.215, -0.16, -0.10, -0.04, 0.02, 0.075]
    us = [barrel_u(z) for z in zs]
    for th0, th1, nm in ((-52, 52, "L"), (128, 232, "R")):
        pan = BARREL.shell(us, th0, th1, nth=7, grow=-0.0095, crease=60)
        p.add(f"m_ribglow_{nm}", pan, "RH_Seam", None, skin=BARREL_SKIN, bake=False, lod1="keep")
    # ---- rib cage: eight bone-white hoops, spine ridge with vertebra knobs and spinous spikes, sternum
    ribs = []
    for k in range(8):
        z = -0.225 + 0.043 * k
        u = barrel_u(z)
        rr = 0.0105 + 0.0012 * math.sin(math.pi * k / 7)
        pts = [BARREL.pt(u, th, 0.004) for th in np.linspace(0, 360, 18, endpoint=False)]
        ribs.append(g.tube(pts, rr, sides=4, samples=1, cap=None, closed=True, smooth=True))
    p.add("m_ribs", merge(ribs), "RH_Frost", None, skin=BARREL_SKIN, uv_scale=2, tint=DK(0.86))
    spine_pts = [barrel_z(z, 270, 0.0) for z in np.linspace(-0.30, 0.10, 6)]
    p.add("m_spine", g.tube(spine_pts, 0.015, sides=5, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)), BONE, None, skin=BARREL_SKIN, uv_scale=2)
    kn = [g.superellipsoid((0.030, 0.026, 0.026), 0.6, 0.7, 3, 7).translated(*(barrel_z(-0.30 + 0.047 * k, 270, 0.004))) for k in range(9)]
    p.add("m_vertebrae", merge(kn), "RH_Frost", None, skin=BARREL_SKIN, tint=DK(0.8))
    sp = [(barrel_z(-0.28 + 0.052 * k, 270, 0.012), (0, 1, -0.35), 0.04 + 0.014 * (k % 3), 0.0085) for k in range(8)]
    p.add("m_vertebra_spikes", spikes(sp, seed=3, flat=0.3, sides=4, tip=0.5), "RH_Ice", None, skin=BARREL_SKIN, lod1=None)
    p.add("m_sternum", g.tube([barrel_z(z, 90, 0.002) for z in (-0.22, -0.10, 0.04, 0.14)], 0.013, sides=5, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)), BONE, None, skin=BARREL_SKIN, uv_scale=2)
    # ---- haunch and shoulder masses (dark), pelvis
    for s, n in ((1, "L"), (-1, "R")):
        hx = s * 0.118
        ha = g.superellipsoid((0.044, 0.084, 0.088), 0.85, 0.9, 6, 12).rotated(-6, 0, 0).translated(hx - s * 0.006, 0.620, -0.215).noised(0.0022, 16, 2, seed=3 + s)
        p.add(f"m_haunch_{n}", ha, "RH_Armour", None, skin=Skin.nearest([("body", JQ["rump"], (0, 0.64, -0.08)), (f"hind_upper_{n}", (s * 0.10, 0.64, -0.22), (s * 0.115, 0.435, -0.33))], tau=0.05, bias={"body": 1.6}), uv_scale=2, tint=DK(0.8))
        sh = g.superellipsoid((0.040, 0.084, 0.078), 0.85, 0.9, 6, 12).rotated(8, 0, 0).translated(s * 0.110, 0.645, 0.115).noised(0.0022, 16, 2, seed=5 + s)
        p.add(f"m_shoulder_{n}", sh, "RH_Armour", None, skin=Skin.nearest([("mount_chest", (0, 0.72, 0.10), (0, 0.66, 0.22)), (f"fore_upper_{n}", (s * 0.10, 0.70, 0.10), (s * 0.11, 0.45, 0.185))], tau=0.05, bias={"mount_chest": 1.6}), uv_scale=2, tint=DK(0.8))
    pel = g.superellipsoid((0.105, 0.065, 0.075), 0.5, 0.6, 4, 10).translated(0, 0.668, -0.265)
    p.add("m_pelvis", pel, BONE, "body", uv_scale=2)
    wi = g.superellipsoid((0.065, 0.050, 0.11), 0.8, 0.9, 5, 11).translated(0, 0.770, 0.095).noised(0.004, 14, 3, seed=7)
    p.add("m_withers", wi, "RH_Armour", None, skin=BARREL_SKIN, uv_scale=2, tint=DK(0.8))
    # ---- legs: gaunt continuous limb tubes with dense rings at the joints, smooth chain skin
    for s, n in ((1, "L"), (-1, "R")):
        X = lambda v: (s * v[0], v[1], v[2])        # noqa: E731
        hip, hock, fet, hoof = (np.array(X(JQ[k])) for k in ("hip_L", "hock_L", "fetlock_L", "hoof_L"))
        hind = limb_tube([hip + [0, 0.05, 0.0], (hip + hock) / 2 + [0, 0.0, 0.01], hock, (hock + fet) / 2 + [0, 0, 0.004], fet, (fet + hoof) / 2 + [0, 0.012, 0], hoof + [0, 0.035, 0.0]],
                         [0.054, 0.042, 0.027, 0.020, 0.019, 0.023, 0.022], joints=[hock, fet], spacing=0.034, joint_spacing=0.017, joint_zone=0.045, sides=7, cap=None, up=(1, 0, 0), ellipse=(0.92, 1.1))
        p.add(f"m_hindleg_{n}", hind.noised(0.0016, 24, 2, seed=11 + s), BONE, None, skin=hind_skin(n), uv_scale=2)
        pt_ = g.superellipsoid((0.024, 0.036, 0.028), 0.7, 0.7, 4, 8).translated(*(hock + [0, 0.0, -0.016]))
        p.add(f"m_hock_{n}", pt_, "RH_Frost", None, skin=hind_skin(n), tint=DK(0.7))
        sho, car, ffet, fhoof = (np.array(X(JQ[k])) for k in ("shoulder_L", "elbow_L", "fetlock_F_L", "hoof_F_L"))
        fore = limb_tube([sho + [0, 0.05, 0.0], (sho + car) / 2 + [0, 0, 0.012], car, (car + ffet) / 2 + [0, 0, 0.002], ffet, (ffet + fhoof) / 2 + [0, 0.012, 0.004], fhoof + [0, 0.035, 0.0]],
                         [0.044, 0.035, 0.024, 0.019, 0.018, 0.022, 0.021], joints=[car, ffet], spacing=0.034, joint_spacing=0.017, joint_zone=0.045, sides=7, cap=None, up=(1, 0, 0), ellipse=(0.95, 1.05))
        p.add(f"m_foreleg_{n}", fore.noised(0.0016, 24, 2, seed=15 + s), BONE, None, skin=fore_skin(n), uv_scale=2)
        kn_ = g.superellipsoid((0.026, 0.028, 0.028), 0.7, 0.7, 4, 8).translated(*(car + [0, 0.0, 0.006]))
        p.add(f"m_knee_{n}", kn_, "RH_Frost", None, skin=fore_skin(n), tint=DK(0.7))
        for key, hb, hfp in (("hind", f"hind_hoof_{n}", hoof), ("fore", f"fore_hoof_{n}", fhoof)):
            xx, zc = hfp[0], hfp[2] - 0.005
            prof = np.array([(0.0, 0.2205), (0.036, 0.2205), (0.0375, 0.226), (0.034, 0.246), (0.030, 0.257), (0.026, 0.259), (0.0, 0.259)])
            p.add(f"m_{key}hoof_{n}", g.lathe(prof, 12, crease=50).scaled(1.0, 1.0, 1.18).translated(xx, 0, zc), "RH_Obsidian", hb)
            p.add(f"m_{key}coronet_{n}", g.torus(0.030, 0.0042, 12, 3).scaled(1.0, 1.0, 1.18).translated(xx, 0.2585, zc), "RH_Frost", hb, lod1=None, tint=DK(0.5))
        # obsidian cannon-bone lames (open hoops) + ice spurs at hock / carpus
        for key, a_, b_, lb in (("hind", hock + [0, -0.03, 0.01], fet + [0, 0.02, 0.0], f"hind_lower_{n}"), ("fore", car + [0, -0.03, 0.004], ffet + [0, 0.02, 0.0], f"fore_lower_{n}")):
            lm = rc.limb_lames([a_, (a_ + b_) / 2, b_], [0.025, 0.020, 0.019], [0.2, 0.55], h=0.040, sweep=230, grow=0.007, seg=6, spin=180)
            p.add(f"m_{key}lames_{n}", lm, "RH_Obsidian", lb)
        p.add(f"m_hockspur_{n}", spikes([((hock[0], hock[1] + 0.01, hock[2] - 0.022), (s * 0.15, 0.25, -1.0), 0.07, 0.012)], seed=9 + (s > 0), flat=0.3, sides=4, tip=0.5), "RH_Ice", f"hind_lower_{n}", lod1=None)
        p.add(f"m_carpspur_{n}", spikes([((car[0], car[1] + 0.01, car[2] - 0.02), (s * 0.15, 0.2, -1.0), 0.05, 0.010)], seed=12 + (s > 0), flat=0.3, sides=4, tip=0.5), "RH_Ice", f"fore_lower_{n}", lod1=None)
    # ---- tail: bone chain with crystal shards streaming off it
    tp = [(0, 0.71, -0.30), (0, 0.62, -0.355), (0, 0.50, -0.385), (0, 0.40, -0.385), (0, 0.34, -0.37)]
    p.add("m_tail", g.tube(tp, [0.018, 0.020, 0.018, 0.013, 0.006], sides=6, samples=3, cap="round", cap_steps=1, up=(1, 0, 0)), BONE, None, skin=TAIL_SKIN, uv_scale=2)
    ts = []
    for k, (dx, y0, ln) in enumerate(((0.0, 0.68, 0.22), (0.02, 0.60, 0.24), (-0.02, 0.55, 0.26), (0.025, 0.47, 0.24), (-0.022, 0.42, 0.22), (0.0, 0.36, 0.18), (0.0, 0.33, 0.12))):
        ts.append(((dx * 0.4, y0, -0.335 - 0.05 * (0.5 - abs(0.5 - k / 6)) - 0.02 * k), (dx * 3.0, -1.0, -0.22 - 0.05 * k), ln, 0.0125 - 0.0008 * k))
    p.add("m_tail_shards", spikes(ts, seed=5, flat=0.3, sides=4, tip=0.5), "RH_Ice", None, skin=TAIL_SKIN)


# ======================================================================================= neck, vertebrae, head, mane
HPIV = np.array(JQ["head"])


def to_head(m):
    return m.rotated(HEAD_PITCH, 0, 0).translated(*HPIV)


def hpt(v):
    a = math.radians(HEAD_PITCH)
    x, y, z = v
    return np.array([x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)]) + HPIV


def hdir(v):
    return unit(hpt(v) - hpt((0, 0, 0)))


def _head_stn(zs, top, bot, hw, e=2.5, samples=3):
    top, bot = np.asarray(top, float), np.asarray(bot, float)
    path = [(0, (t + b) / 2, z) for z, t, b in zip(zs, top, bot)]
    return Stn(path, hw, (top - bot) / 2, e=e, samples=samples)


HZ = [-0.02, 0.03, 0.08, 0.13, 0.18, 0.24, 0.29, 0.325, 0.343]
H_TOP = [0.042, 0.048, 0.046, 0.038, 0.028, 0.017, 0.009, 0.001, -0.008]
H_BOT = [-0.072, -0.084, -0.074, -0.052, -0.038, -0.028, -0.026, -0.022, -0.018]
H_HW = [0.044, 0.054, 0.060, 0.056, 0.047, 0.041, 0.040, 0.036, 0.025]
HEAD = _head_stn(HZ, H_TOP, H_BOT, H_HW)
JZ = [0.04, 0.08, 0.13, 0.18, 0.24, 0.29, 0.325, 0.343]
J_TOP = [-0.060, -0.058, -0.034, -0.020, -0.010, -0.008, -0.006, -0.004]
J_BOT = [-0.094, -0.094, -0.082, -0.062, -0.048, -0.045, -0.038, -0.033]
J_HW = [0.046, 0.050, 0.046, 0.038, 0.032, 0.029, 0.027, 0.019]
JAW = _head_stn(JZ, J_TOP, J_BOT, J_HW, e=2.3)
JAW_PIV = _JAW_PIV_LOCAL
JAW_OPEN = 9.0                                      # the jaw hangs open at rest


def neck_and_crinet(p: Piece):
    p.add("m_neck", NECK.mesh(K=14, cap0=False, cap1=False).noised(0.004, 16, 3, seed=10), "RH_Armour", None, skin=NECK_SKIN, uv_scale=2, tint=DK(0.85))
    # obsidian crinet lames over the crest and flanks of the neck
    for i, uc in enumerate([0.12, 0.28, 0.44, 0.60, 0.76]):
        du = 0.085
        bn = "neck_1" if uc < 0.50 else "neck_2"
        us = [uc - du, uc - du * 0.15, uc + du * 0.9]
        gr = [0.014 + 0.0012 * i, 0.019 + 0.0012 * i, 0.012 + 0.0012 * i]
        sh = NECK.shell(us, 205, 335, nth=7, grow=gr, crease=40)
        shn = sh.noised(0.0009, 34, 2, seed=30 + i)
        p.add(f"m_crinet_{i}", shn, "RH_Obsidian", bn)
        p.add(f"m_crinet_frost_{i}", frost_layer(shn, 0.005, min_ny=0.35, cover=0.3, seed=10 + i), "RH_Frost", bn, lod1=None, tint=DK(0.5))
        lip = g.tube([NECK.pt(us[0], th, gr[0] + 0.002) for th in np.linspace(205, 335, 8)], 0.0042, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
        p.add(f"m_crinet_lip_{i}", lip, "RH_Silver", bn, lod1=None, tint=DK(0.7))
    # exposed bone vertebrae riding the crest, each with a short spinous spike
    for i, u in enumerate(np.linspace(0.08, 0.93, 7)):
        bn = "neck_1" if u < 0.50 else "neck_2"
        c0 = NECK.pt(u, 270, 0.024)
        out = unit(c0 - NECK.at(u)[0])
        disc = g.superellipsoid((0.034 - 0.0016 * i, 0.012, 0.026), 0.6, 0.7, 3, 7)
        T = NECK.at(u)[5]
        p.add(f"m_vert_{i}", disc.aimed(out, c0).rotated(0, 0, 0), "RH_Frost", bn, tint=DK(0.85))


def head_parts(p: Piece):
    skull = to_head(HEAD.mesh(K=16, cap0=True, cap1=True, crease=55).noised(0.0030, 24, 2, seed=16))
    p.add("m_skull", skull, "RH_Frost", "mount_head", uv_scale=2)
    jaw = JAW.mesh(K=12, cap0=True, cap1=True, crease=55).noised(0.002, 22, 2, seed=17).rotated(JAW_OPEN, 0, 0, pivot=JAW_PIV)
    p.add("m_jaw", to_head(jaw), "RH_Frost", "jaw", uv_scale=2)
    # nostril cavities, dark sockets, zygomatic arches, brow ridges
    nos = [to_head(g.superellipsoid((0.0095, 0.0050, 0.013), 0.7, 0.7, 3, 7).rotated(0, s * 12, 0).translated(s * 0.017, -0.003, 0.333)) for s in (-1, 1)]
    p.add("m_nostrils", merge(nos), "RH_Obsidian", "mount_head", lod1=None)
    for s in (-1, 1):
        n = "L" if s > 0 else "R"
        arch = g.tube([hpt(np.array([s * 0.050, 0.004, 0.128])), hpt(np.array([s * 0.062, -0.014, 0.100])), hpt(np.array([s * 0.062, -0.034, 0.062])), hpt(np.array([s * 0.052, -0.048, 0.030]))], 0.0075, sides=5, samples=2, cap="round", cap_steps=1)
        p.add(f"m_zygoma_{n}", arch, "RH_Frost", "mount_head", lod1=None)
        brow = g.tube([hpt(np.array([s * 0.036, 0.034, 0.128])), hpt(np.array([s * 0.058, 0.028, 0.100])), hpt(np.array([s * 0.062, 0.016, 0.060]))], 0.0085, sides=5, samples=2, cap="round", cap_steps=1)
        p.add(f"m_brow_{n}", brow, "RH_Frost", "mount_head")
    # half-chanfron (black plate across the forehead and the brow) with silver wire edges: the hard value edge on the bone skull
    us = np.linspace(0.04, 0.60, 7)
    gr = 0.008 + 0.003 * np.sin(np.linspace(0, math.pi, 7))
    chan = to_head(HEAD.shell(us, -150, -30, nth=9, grow=gr, crease=40).noised(0.0010, 34, 2, seed=18))
    p.add("m_chanfron", chan, "RH_Obsidian", "mount_head")
    ed = []
    for th in (-150, -30):
        ed.append(g.tube([np.array(hpt(HEAD.pt(u, th, g_ + 0.001))) for u, g_ in zip(us, gr)], 0.0042, sides=4, samples=2, cap="round", cap_steps=1))
    ed.append(g.tube([np.array(hpt(HEAD.pt(us[-1], th, gr[-1] + 0.001))) for th in np.linspace(-150, -30, 8)], 0.0042, sides=4, samples=1, cap="round", cap_steps=1))
    p.add("m_chanfron_edges", merge(ed), "RH_Silver", "mount_head", lod1=None, tint=DK(0.75))
    p.add("m_chanfron_ridge", g.tube([np.array(hpt(HEAD.pt(u, -90, 0.0115))) for u in np.linspace(0.05, 0.60, 6)], [0.0075, 0.0085, 0.0085, 0.0080, 0.0070, 0.0050], sides=5, samples=2, cap="round", cap_steps=1), "RH_Obsidian", "mount_head")
    # eyes: dark socket rings with a cyan glow set in them (focal point 1)
    ey, rd = [], []
    for s in (-1, 1):
        c = np.array([s * 0.0545, 0.010, 0.088])
        rd.append(g.torus(0.0225, 0.0062, 12, 4).rotated(0, 0, 90).rotated(0, s * 14, 0).translated(*c))
        ey.append(g.superellipsoid((0.0095, 0.0150, 0.0150), 0.7, 0.7, 3, 7).translated(s * 0.0535, 0.0095, 0.090))
    p.add("m_eye_sockets", to_head(merge(rd)), "RH_Obsidian", "mount_head")
    p.add("m_eyes", to_head(merge(ey)), "RH_Glow", "mount_head", bake=False, lod1="keep")
    # teeth
    up_t = [(hpt(np.array([s * 0.027, -0.017, z])), hdir((0, -1, 0.1)), 0.020, 0.0060) for s in (-1, 1) for z in (0.20, 0.235, 0.27, 0.30)]
    p.add("m_teeth_up", spikes(up_t, seed=3, flat=0.2, sides=4, tip=0.6), "RH_Frost", "mount_head", lod1=None, tint=DK(0.8))
    #rj = lambda v: to_head(g.Mesh(np.array([v], float), np.zeros((0, 3), dtype=np.int64))).P[0] if False else None  # noqa: E731
    lo_t = []
    for s in (-1, 1):
        for z in (0.20, 0.235, 0.27, 0.30):
            base = np.array([s * 0.024, -0.012 + (-0.03 if z < 0.15 else 0.0) - 0.021, z])
            q = np.array([base[0], base[1], base[2]])
            # rotate with the open jaw (about JAW_PIV)
            a = math.radians(JAW_OPEN)
            rel = q - np.array(JAW_PIV)
            q2 = np.array([rel[0], rel[1] * math.cos(a) - rel[2] * math.sin(a), rel[1] * math.sin(a) + rel[2] * math.cos(a)]) + np.array(JAW_PIV)
            d = np.array([0, math.cos(a), math.sin(a)]) * 1.0
            lo_t.append((hpt(q2 + [0, 0.012, 0]), hdir(tuple(d)), 0.016, 0.0055))
    p.add("m_teeth_lo", spikes(lo_t, seed=8, flat=0.2, sides=4, tip=0.6), "RH_Frost", "jaw", lod1=None, tint=DK(0.8))
    # bridle: noseband, cheek chain, reins to the rider's left hand
    nb = [hpt(HEAD.pt(0.74, th, 0.014)) for th in np.linspace(0, 360, 12, endpoint=False)]
    p.add("m_noseband", g.tube(nb, 0.0045, sides=4, samples=1, cap=None, closed=True, smooth=True), "RH_Silver", "mount_head", lod1=None, tint=DK(0.65))
    bit = hpt(np.array([0.047, -0.027, 0.262]))
    wr = np.array(JR["wrist_L"])
    reins = g.tube([bit, bit + (wr - bit) * 0.35 + [0.012, -0.015, 0.0], bit + (wr - bit) * 0.72 + [0.008, -0.018, 0], wr + [0.0, 0.005, 0.0]], 0.0034, sides=4, samples=3, cap="round", cap_steps=1)
    p.add("m_reins", reins, "RH_Silver", None, skin=Skin.nearest([("mount_head", bit, bit + [0, 0, 0.01]), ("wrist_L", wr, wr + [0, 0, 0.01])], tau=0.09), lod1=None, tint=DK(0.6))
    # ears: ice shards standing from the poll (tips y 1.29)
    for s, n in ((1, "L"), (-1, "R")):
        sp = spikes([((s * 0.038, 1.200, 0.298), unit((s * 0.12, 1.0, 0.12)), 0.092, 0.0165)], seed=21 + (s > 0), flat=0.25, sides=5, tip=0.5, bend=0.03)
        p.add(f"m_ear_{n}", sp, "RH_Ice", "mount_head")


def mane(p: Piece):
    rng = np.random.default_rng(31)
    crest = [NECK.pt(u, 270, -0.004) for u in np.linspace(0.05, 1.0, 14)]
    fskin = Fringe(NECK_SKIN, np.array(crest), reach=0.07, sig=0.07)
    specs, sub = [], []
    n = 12
    for i in range(n):
        u = 0.97 - 0.88 * i / (n - 1)
        base = NECK.pt(u, 270, 0.010)
        L = (0.075 + 0.060 * smoothstep(0.05, 1.0, u)) * (0.9 + 0.2 * rng.random())
        sgn = 1 if i % 2 else -1
        d = unit(V(sgn * 0.10, 0.78, -0.62))
        specs.append((base, d, L, 0.021 - 0.004 * (1 - u)))
        sub.append((base + V(sgn * 0.014, 0.0, 0.01), unit(V(sgn * 0.55, 0.62, -0.55)), L * 0.70, 0.0135))
    p.add("m_mane", spikes(specs, seed=40, flat=0.30, sides=5, tip=0.45, bend=0.05), "RH_Frost", None, skin=fskin, tint=DK(0.95))
    p.add("m_mane_sub", spikes(sub, seed=60, flat=0.3, sides=4, tip=0.5), "RH_Ice", None, skin=fskin, lod1=None)
    # forelock shards between the ears + mane glints
    p.add("m_forelock", spikes([((s * 0.012, 1.215, 0.325), unit((s * 0.25, 0.55, 0.9)), 0.045, 0.0085) for s in (-1, 1)], seed=77, flat=0.3, sides=4, tip=0.5), "RH_Ice", "mount_head", lod1=None)


# ======================================================================================= barding, saddle
def barding(p: Piece):
    # ---- peytral: three obsidian lames across the chest (ribs visible behind), silver lips
    zr = [(0.10, 0.17), (0.145, 0.215), (0.19, 0.262)]
    pey, cru = [], []
    for k, (z0, z1) in enumerate(zr):
        us = [barrel_u(z0), barrel_u((z0 + z1) / 2), barrel_u(z1)]
        gr = [0.012 + 0.0035 * k, 0.017 + 0.0035 * k, 0.011 + 0.0035 * k]
        sh = BARREL.shell(us, -32, 212, nth=15, grow=gr, crease=40)
        shn = sh.noised(0.0010, 30, 2, seed=40 + k)
        pey.append(shn)
        p.add(f"m_peytral_{k}", shn, "RH_Obsidian", "mount_chest")
        lip = g.tube([BARREL.pt(us[-1], th, gr[-1] + 0.0015) for th in np.linspace(-32, 212, 12)], 0.0045, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
        p.add(f"m_peytral_lip_{k}", lip, "RH_Silver", "mount_chest", lod1=None, tint=DK(0.7))
    p.add("m_peytral_frost", frost_layer(merge(pey), 0.006, min_ny=0.45, cover=0.35, seed=3), "RH_Frost", "mount_chest", lod1=None, tint=DK(0.5))
    p.add("m_chest_ice", cluster(barrel_z(0.275, 90, 0.02) + V(0, 0.02, 0.0), (0, 0.15, 1.0), 4, (0.045, 0.085), (0.010, 0.016), spread=0.03, tilt=34, seed=5, flat=0.3), "RH_Ice", "mount_chest")
    # ---- shoulder and haunch plates (two overlapping lames each)
    for s, n in ((1, "L"), (-1, "R")):
        sh = [g.superellipsoid((0.011, 0.040 - 0.004 * i, 0.056 - 0.006 * i), 0.5, 0.6, 3, 9).rotated(0, 0, s * (-8 - 6 * i)).translated(s * (0.150 + 0.006 * i), 0.690 - 0.040 * i, 0.112) for i in range(2)]
        p.add(f"m_shoulder_plates_{n}", merge(sh), "RH_Obsidian", "mount_chest")
        hp = [g.superellipsoid((0.011, 0.046 - 0.004 * i, 0.060 - 0.006 * i), 0.5, 0.6, 3, 9).rotated(0, 0, s * (-8 - 6 * i)).translated(s * (0.158 + 0.006 * i), 0.668 - 0.040 * i, -0.215) for i in range(2)]
        p.add(f"m_haunch_plates_{n}", merge(hp), "RH_Obsidian", "body")
        p.add(f"m_haunch_ice_{n}", cluster((s * 0.166, 0.700, -0.215), (s * 0.7, 0.7, -0.25), 3, (0.04, 0.075), (0.009, 0.014), spread=0.02, tilt=30, seed=21 + (s > 0), flat=0.3, sides=4), "RH_Ice", "body")
        p.add(f"m_shoulder_ice_{n}", cluster((s * 0.158, 0.725, 0.115), (s * 0.7, 0.7, 0.1), 3, (0.04, 0.07), (0.009, 0.013), spread=0.02, tilt=30, seed=27 + (s > 0), flat=0.3, sides=4), "RH_Ice", "mount_chest")
        p.add(f"m_hip_bone_{n}", g.superellipsoid((0.012, 0.030, 0.038), 0.6, 0.7, 3, 7).translated(s * 0.085, 0.725, -0.215), BONE, "body", tint=DK(0.9))
    # ---- crupper: three obsidian plates over the rump
    for k, (z0, z1) in enumerate(((-0.205, -0.255), (-0.240, -0.290), (-0.272, -0.322))):
        us = [barrel_u(z0), barrel_u((z0 + z1) / 2), barrel_u(z1)]
        gr = [0.011 + 0.003 * k, 0.015 + 0.003 * k, 0.010 + 0.003 * k]
        sh = BARREL.shell(us, 205, 335, nth=11, grow=gr, crease=40)
        shn = sh.noised(0.0010, 30, 2, seed=50 + k)
        cru.append(shn)
        p.add(f"m_crupper_{k}", shn, "RH_Obsidian", "body")
    p.add("m_crupper_frost", frost_layer(merge(cru), 0.006, min_ny=0.40, cover=0.4, seed=4), "RH_Frost", "body", lod1=None, tint=DK(0.5))
    sp = [barrel_z(z, 270, 0.020) for z in (-0.235, -0.275, -0.315)]
    p.add("m_crupper_spikes", spikes([(q, (0, 1, -0.55), 0.045, 0.011) for q in sp], seed=14, flat=0.3, sides=4, tip=0.5), "RH_Ice", "body", lod1=None)
    # ---- torn saddle blanket over the back (cloth, ragged hem) + rotted saddle
    zs = np.linspace(0.05, -0.21, 9)
    wob = 14 * np.sin(zs * 60 + 0.6)
    th0 = 215 + wob * 0.6
    th1 = 325 - wob * 0.6
    us = [barrel_u(z) for z in zs]
    cap = BARREL.shell(us, th0, th1, nth=13, grow=0.014, crease=60)
    p.add("m_blanket", cap.noised(0.0028, 14, 2, seed=11), "RH_Cloth", None, skin=BARREL_SKIN, uv_scale=2, tint=DK(0.9))
    sad = g.superellipsoid((0.092, 0.022, 0.115), 0.55, 0.6, 5, 12).translated(0, 0.808, -0.060)
    cant = g.superellipsoid((0.086, 0.036, 0.015), 0.5, 0.6, 4, 10).translated(0, 0.826, -0.172)
    pom = g.superellipsoid((0.030, 0.032, 0.020), 0.55, 0.6, 4, 10).translated(0, 0.826, 0.046)
    p.add("m_saddle", merge([sad, cant, pom]), "RH_Obsidian", "mount_body")
    p.add("m_saddle_wire", g.torus(0.090, 0.0034, 14, 3).scaled(1.0, 1.0, 1.22).translated(0, 0.824, -0.060), "RH_Silver", "mount_body", lod1=None, tint=DK(0.6))
    for s, n in ((1, "L"), (-1, "R")):
        strap = g.tube([(s * 0.150, 0.790, -0.040), (s * 0.188, 0.690, -0.010), (s * 0.204, 0.560, 0.012)], 0.0050, sides=4, samples=2, cap="round", cap_steps=1, ellipse=(1.0, 0.45), up=(0, 0, 1))
        p.add(f"m_stirrup_strap_{n}", strap, "RH_Silver", "mount_body", lod1=None, tint=DK(0.5))
        ring = g.torus(0.026, 0.0042, 12, 4).rotated(0, 0, 90).translated(s * 0.204, 0.512, 0.020)
        p.add(f"m_stirrup_{n}", ring, "RH_Silver", "mount_body", lod1=None, tint=DK(0.65))


# ======================================================================================= the rider (crouched, secondary)
RJ = {k: np.array(v, float) for k, v in JR.items()}
for k_ in list(RJ):
    if k_.endswith("_L") and k_[:-1] + "R" not in RJ:
        RJ[k_[:-1] + "R"] = V(-RJ[k_][0], RJ[k_][1], RJ[k_][2])
LEG_SKIN = {s: Skin.chain([f"thigh_{s}", f"shin_{s}", f"foot_{s}"], pre="rider_pelvis", tip=tuple(RJ[f"toe_{s}"]), zone=0.40) for s in "LR"}
ARM_SKIN = {s: Skin.chain([f"arm_{s}", f"hand_{s}"], pre=f"clavicle_{s}", tip=tuple(RJ[f"wrist_{s}"]), zone=0.42) for s in "LR"}
RT_SKIN = Skin.chain(["rider_pelvis", "spine", "chest"], tip=tuple(RJ["neck"]), zone=0.45)
TORSO = Stn([(0, .825, -.112), (0, .875, -.085), (0, .935, -.045), (0, .990, .008)], [.090, .094, .108, .112], [.070, .072, .078, .068], e=2.4, samples=4)


def lerp3(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


def rider(p: Piece):
    for s, nm in ((1, "L"), (-1, "R")):
        hip, knee, ank, toe = (RJ[f"{k}_{nm}"] for k in ("hip", "knee", "ankle", "toe"))
        hose = limb_tube([hip + [0, 0.02, 0], lerp3(hip, knee, 0.5) + [0, 0, 0.004], knee, lerp3(knee, ank, 0.5), ank + [0, 0.01, 0]], [0.034, 0.031, 0.028, 0.025, 0.022],
                         joints=[knee], spacing=0.05, joint_spacing=0.024, joint_zone=0.05, sides=6, cap=None, up=(0, 0, 1))
        p.add(f"r_leg_{nm}", hose, BONE, None, skin=LEG_SKIN[nm], uv_scale=2, tint=DK(0.75))
        thigh = g.tube([lerp3(hip, knee, 0.12), lerp3(hip, knee, 0.4), lerp3(hip, knee, 0.72)], [0.044, 0.046, 0.040], sides=7, samples=1, cap=None, up=(0, 0, 1)).noised(0.0014, 34, 2, seed=40 + s)
        p.add(f"r_cuisse_{nm}", thigh, "RH_Obsidian", f"thigh_{nm}")
        boot = g.superellipsoid((0.036, 0.038, 0.068), 0.55, 0.62, 4, 9).rotated(10, 0, 0).translated(s * 0.200, 0.516, 0.038)
        p.add(f"r_boot_{nm}", boot, "RH_Obsidian", f"foot_{nm}")
        g0, g1 = lerp3(knee, ank, 0.88) + [0, 0, 0.008], lerp3(knee, ank, 0.22) + [0, 0, 0.008]
        greave = g.tube([g0, (g0 + g1) / 2, g1], [0.036, 0.039, 0.042], sides=8, samples=2, cap=None, up=(0, 0, 1)).noised(0.0014, 34, 2, seed=44 + s)
        p.add(f"r_greave_{nm}", greave, "RH_Obsidian", f"shin_{nm}")
        cop = g.superellipsoid((0.038, 0.034, 0.032), 0.65, 0.65, 4, 9).translated(*(knee + [s * 0.004, 0.0, 0.036]))
        p.add(f"r_kneecop_{nm}", cop, "RH_Obsidian", f"shin_{nm}")
        p.add(f"r_kneespike_{nm}", spikes([(knee + V(s * 0.004, 0.0, 0.058), (s * 0.25, 0.25, 1.0), 0.06, 0.016)], seed=6 + (s > 0), flat=0.3, sides=5, tip=0.4), "RH_Ice", f"shin_{nm}", lod1=None)
        p.add(f"r_stirrup_{nm}", g.torus(0.021, 0.0034, 10, 3).rotated(0, 90, 0).translated(s * 0.200, 0.468, 0.045), "RH_Silver", f"foot_{nm}", lod1=None, tint=DK(0.6))
    # torso: dark core with bone ribs arcing over the front, a half cuirass, backplate, spine
    p.add("r_torso", TORSO.mesh(K=12, grow=-0.006, cap0=True, cap1=True).noised(0.0012, 20, 2, seed=3), "RH_Armour", None, skin=RT_SKIN, uv_scale=2, tint=DK(0.8))
    rb = []
    for u in (0.12, 0.26, 0.40, 0.54):
        rb.append(g.tube([TORSO.pt(u, th, 0.004) for th in np.linspace(-20, 200, 9)], 0.0070, sides=4, samples=1, cap="round", cap_steps=1, smooth=True))
    p.add("r_ribs", merge(rb), "RH_Frost", None, skin=RT_SKIN, tint=DK(0.65))
    p.add("r_spine", g.tube([TORSO.pt(u, 270, 0.004) for u in np.linspace(0.04, 0.96, 5)], 0.011, sides=5, samples=2, cap="round", cap_steps=1), BONE, None, skin=RT_SKIN)
    cu = TORSO.shell([0.50, 0.64, 0.80, 0.93], -8, 188, nth=13, grow=[0.008, 0.013, 0.014, 0.008], crease=45)
    cud = cu.dented(3, 0.026, 0.003, seed=44)
    p.add("r_cuirass", cud, "RH_Obsidian", "chest")
    p.add("r_cuirass_frost", frost_layer(cud, 0.005, min_ny=0.4, cover=0.3, seed=6), "RH_Frost", "chest", lod1=None, tint=DK(0.5))
    p.add("r_cuirass_wire", TORSO.edge(np.linspace(0.52, 0.92, 4), 188, 0.015, 0.0035, 4), "RH_Silver", "chest", lod1=None, tint=DK(0.65))
    bk = TORSO.shell([0.15, 0.40, 0.65, 0.92], 200, 340, nth=9, grow=[0.008, 0.012, 0.012, 0.008], crease=45)
    p.add("r_backplate", bk, "RH_Obsidian", "chest")
    belt = TORSO.shell([0.02, 0.07, 0.13], 0, 360 - 360 / 12, nth=12, grow=[0.006, 0.010, 0.006], crease=50)
    p.add("r_belt", g.loft(np.stack([TORSO.pt(u, np.linspace(0, 360, 12, endpoint=False), gg) for u, gg in zip([0.02, 0.05, 0.10, 0.13], [0.006, 0.012, 0.012, 0.006])]), closed=True, crease=50), "RH_Obsidian", "spine", lod1=None)
    gor = g.lathe(np.array([(0.056, 0.972), (0.062, 0.980), (0.064, 1.000), (0.056, 1.016), (0.050, 1.014), (0.054, 0.998), (0.052, 0.980)]), 12, crease=45).translated(0, 0, 0.034)
    p.add("r_gorget", gor, "RH_Obsidian", "chest", lod1=None)
    # pauldrons: left large and spiked, right bare bone
    pld = merge([g.superellipsoid((0.066 - 0.006 * i, 0.013, 0.058 - 0.004 * i), 0.5, 0.65, 4, 10).rotated(0, 0, -16 - 10 * i).translated(0.172 + 0.010 * i, 0.990 - 0.026 * i, 0.0) for i in range(3)])
    p.add("r_pauldron_L", pld, "RH_Obsidian", "arm_L")
    p.add("r_pauldron_frost", frost_layer(pld, 0.005, min_ny=0.4, cover=0.35, seed=8), "RH_Frost", "arm_L", lod1=None, tint=DK(0.5))
    p.add("r_pauldron_L_spikes", spikes([((0.17 + 0.014 * k, 1.000, -0.02 + 0.026 * k), unit((0.5 + 0.1 * k, 1.0, 0.0)), 0.05 + 0.015 * (k % 2), 0.011) for k in range(3)], seed=4, flat=0.3, sides=5, tip=0.4), "RH_Ice", "arm_L")
    p.add("r_shoulder_R", g.superellipsoid((0.028, 0.024, 0.028), 0.7, 0.7, 3, 8).translated(-0.160, 0.962, 0.0), BONE, "arm_R")
    # arms: bone sleeves, vambraces, claw / gripping hands
    for s, nm in ((1, "L"), (-1, "R")):
        sh, el, wr = RJ[f"shoulder_{nm}"], RJ[f"elbow_{nm}"], RJ[f"wrist_{nm}"]
        fd = unit(wr - el)
        sleeve = limb_tube([sh + [0, -0.006, 0], lerp3(sh, el, 0.5), el, lerp3(el, wr - fd * 0.03, 0.5), wr - fd * 0.03], [0.022, 0.020, 0.018, 0.016, 0.014],
                           joints=[el], spacing=0.045, joint_spacing=0.022, joint_zone=0.045, sides=6, cap="round", cap_steps=1, up=(0, 1, 0))
        p.add(f"r_arm_{nm}", sleeve, BONE, None, skin=ARM_SKIN[nm], uv_scale=2, tint=DK(0.75))
        v0, v1 = lerp3(el, wr, 0.15), lerp3(el, wr, 0.75)
        vam = g.tube([v0, (v0 + v1) / 2, v1], [0.028, 0.026, 0.024], sides=7, samples=1, cap="flat", up=(0, 1, 0))
        p.add(f"r_vambrace_{nm}", vam.noised(0.0012, 34, 2, seed=24 + s), "RH_Obsidian", f"hand_{nm}")
    wl = RJ["wrist_L"]
    p.add("r_hand_L", rc.claw_hand(+1, wl + V(0, -0.004, 0.012), (0.0, -0.3, 1.0), 0.8, 0.8, 1.1), BONE, "wrist_L", uv_scale=2)
    wr_ = RJ["wrist_R"]
    ld = unit(GLAIVE_T - GLAIVE_B)
    fing = [g.torus(0.0165, 0.0062, 8, 4).aimed(ld, wr_ + ld * dz) for dz in (-0.020, -0.004, 0.012)]
    back = g.superellipsoid((0.026, 0.022, 0.026), 0.5, 0.6, 3, 8).translated(*(wr_ + [0.0, 0.020, -0.004]))
    p.add("r_hand_R", merge(fing + [back]), BONE, "wrist_R", uv_scale=2)
    # head: bone skull (dimmer than the steed's), obsidian half-helm with nasal bar and cheeks (top 1.08), dim eye lights
    hc = np.array([0.0, 1.030, 0.062])
    skull = g.superellipsoid((0.041, 0.044, 0.045), 0.9, 0.95, 5, 10).translated(*hc)
    jaw = g.superellipsoid((0.024, 0.016, 0.028), 0.6, 0.6, 3, 7).translated(hc[0], hc[1] - 0.034, hc[2] + 0.012)
    p.add("r_skull", merge([skull, jaw]), "RH_Frost", "head", uv_scale=2, tint=DK(0.58))
    helm = g.lathe(g.spline(np.array([(0.050, 0.998), (0.055, 1.026), (0.050, 1.056), (0.031, 1.076), (0.0, 1.083)]), 3), 14, crease=55).translated(0, 0, hc[2] - 0.004).noised(0.0010, 40, 2, seed=52)
    p.add("r_helm", helm, "RH_Obsidian", "head")
    nasal = g.extrude(np.array([(-0.0055, 0.995), (0.0055, 0.995), (0.0046, 1.060), (-0.0046, 1.060)]), 0.006, 0.0015, 1).translated(0, 0, hc[2] + 0.044)
    p.add("r_nasal", nasal, "RH_Silver", "head", lod1=None, tint=DK(0.7))
    cheek = [g.extrude_plane(np.array([(0.998, hc[2] - 0.026), (0.996, hc[2] + 0.022), (1.020, hc[2] + 0.030), (1.038, hc[2] + 0.014), (1.034, hc[2] - 0.024)]), 0.006, "YZ", bevel=0.0015, bevel_segments=1).translated(s * 0.044, 0, 0) for s in (-1, 1)]
    p.add("r_cheek_guards", merge(cheek), "RH_Obsidian", "head", lod1=None)
    eyes = [g.superellipsoid((0.006, 0.006, 0.006), 0.7, 0.7, 3, 6).translated(s * 0.019, 1.036, hc[2] + 0.040) for s in (-1, 1)]
    p.add("r_eyes", merge(eyes), "RH_Glow", "head", bake=False, lod1="keep")
    p.add("r_neck", g.tube([(0, 0.975, 0.020), (0, 1.010, 0.050)], [0.028, 0.026], sides=6, samples=1, cap=None, smooth=False), BONE, "neck", uv_scale=2)
    # tattered cloak behind the rider (cloth, ragged hem)
    R_, K_ = 7, 8
    rows = []
    for r in range(R_):
        v = r / (R_ - 1)
        row = []
        for k in range(K_):
            u = k / (K_ - 1)
            y = 0.99 - 0.30 * v - ((0.05 if r == R_ - 1 else 0.012) * (k % 2) if r >= R_ - 2 else 0)
            xw = 0.070 + 0.075 * v ** 0.8
            z = -0.085 - 0.055 * v ** 1.2 + 0.007 * math.sin(u * TAU * 2.2)
            row.append((-xw + 2 * xw * u, y, z))
        rows.append(row)
    cm = g.loft(np.array(rows)[::-1], closed=False, crease=50, v_tile=0.25, u_tile=0.25)
    p.add("r_cloak", cm, "RH_Cloth", "chest", bone2="top", blend=(0.93, 0.74), uv_scale=2)


# ---- the glaive: haft with silver wraps, hooked ice blade with a back spur (axis along local +Y from the butt)
def glaive(p: Piece):
    L = G_LEN
    haft = g.tube([(0, 0.0, 0), (0, L * 0.45, 0), (0, L * 0.80, 0)], [0.013, 0.011, 0.010], sides=6, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
    wraps = merge([g.torus(0.0135, 0.0030, 8, 3).rotated(90, 0, 0).translated(0, y, 0) for y in (0.06, 0.12, 0.30, 0.36)])
    collar = g.lathe([(0.011, 0.50), (0.020, 0.51), (0.020, 0.53), (0.011, 0.54)], 8, crease=35)
    poly = np.array([(0.50, 0.0), (0.54, -0.032), (0.60, -0.052), (0.665, -0.034), (0.690, 0.006),     # leading edge up to the tip
                     (0.635, 0.002), (0.59, 0.010), (0.575, 0.045), (0.555, 0.090), (0.540, 0.045), (0.52, 0.016)])
    blade = g.extrude_plane(poly, 0.016, "YZ", bevel=0.0035, bevel_segments=1)
    butt = spikes([((0, 0.0, 0), (0, -1, 0), 0.05, 0.011)], seed=2, flat=0.1, sides=5)
    def place(m):
        return m.aimed(GD, GLAIVE_B)
    p.add("r_glaive_haft", place(haft), "RH_Obsidian", "weapon", uv_scale=2)
    p.add("r_glaive_wraps", place(wraps), "RH_Silver", "weapon", lod1=None, tint=DK(0.6))
    p.add("r_glaive_collar", place(collar), "RH_Silver", "weapon", tint=DK(0.7))
    p.add("r_glaive_blade", place(blade), "RH_Ice", "weapon", occluder=False)
    p.add("r_glaive_butt", place(butt), "RH_Ice", "weapon", lod1=None)



# ======================================================================================= animation (IK quadruped + rider)
from anim.curves import Sig                         # noqa: E402

FEET = {"hoof_hind_L": (("hind_upper_L", "hind_lower_L", "hind_hoof_L"), (0, 0, -1)), "hoof_hind_R": (("hind_upper_R", "hind_lower_R", "hind_hoof_R"), (0, 0, -1)),
        "hoof_fore_L": (("fore_upper_L", "fore_lower_L", "fore_hoof_L"), (0, 0, 1)), "hoof_fore_R": (("fore_upper_R", "fore_lower_R", "fore_hoof_R"), (0, 0, 1))}
A_L = unit(GLAIVE_T - GLAIVE_B)                       # lance axis (butt -> tip) at rest
WR0, WL0 = RJ["wrist_R"], RJ["wrist_L"]
Z3 = V(0, 0, 0)


def goal_(a, n):
    return next(x for x in a.goals if x.name == n)


def _anim(rig):
    a = Animator(rig)
    for nm, (chain, pole) in FEET.items():
        a.goal(nm, chain, rot=(0, 0, 0), pole=pole, contact=True)
    a.keep_legs_reachable(list(FEET))
    a.goal("ik_hand_R", ("arm_R", "hand_R", "wrist_R"), spaces=(("rider_pelvis", 1.0),), rot=(0, 0, 0), pole=(-0.5, -1, -0.2))
    a.goal("ik_hand_L", ("arm_L", "hand_L", "wrist_L"), spaces=(("rider_pelvis", 1.0),), rot=(0, 0, 0), pole=(0.5, -1, -0.2))
    a.secondary(["top"], driver="mount_body", freq=2.2, zeta=0.35, accel=0.05, max_deg=8)
    a.secondary(["tail_1", "tail_2", "tail_3"], driver="body", freq=2.0, zeta=0.30, accel=0.08, max_deg=30)
    for m_, d_ in (("mane_1", "neck_2"), ("mane_2", "neck_1"), ("mane_3", "mount_chest")):
        a.secondary([m_], driver=d_, freq=3.0, zeta=0.30, follow=0.9, hang=-1, max_deg=25)
    return a


def foot(a, n, pos=None, rot=None, blend=None, space="body"):
    """pos/rot: Curve keys or Sig (world delta from rest, or in `space` where blend > 0).  blend: scalar keys (t, w): 0 = world, 1 = `space`."""
    g_ = goal_(a, n)
    if pos is not None:
        g_.pos = pos if isinstance(pos, Sig) else Curve(pos)
    if rot is not None:
        g_.rot = rot if isinstance(rot, Sig) else Curve(rot)
    if blend is not None:
        w = Curve(blend)
        g_.spaces = (("world", Fn(lambda t: 1.0 - float(w(t)[0]))), (space, Fn(lambda t: float(w(t)[0]))))


def hold_lance(a, pos_keys=None, dir_keys=None, pos=None, dir_=None):
    gr = goal_(a, "ik_hand_R")
    if pos_keys is not None or pos is not None:
        gr.pos = M.abs_pos(WR0, pos if pos is not None else Curve(pos_keys))
    if dir_keys is not None or dir_ is not None:
        gr.rot = M.aim(A_L, dir_ if dir_ is not None else Curve(dir_keys))


def cs(u, c, amp=1.0):
    return amp * math.cos(2 * math.pi * (u - c))


# ---------------------------------------------------------------------------------------------- Idle
def clip_idle(rig):
    a = _anim(rig)
    T = 3.2
    f = 1 / T
    a.pos("body", Wave(V(0.005, 0, 0), f, 0.0))
    a.pos("body", Wave(V(0, 0.003, 0), 2 * f, 0.25))
    a.rot("body", Wave(V(0, 1.2, 1.6), f, 0.05))
    a.rot("mount_body", Wave(V(-0.6, -0.8, -1.0), f, 0.12))
    a.rot("mount_chest", Wave(V(-0.9, 0, 0), 2 * f, 0.10))
    a.rot("neck_1", Wave(V(1.3, 0.8, 0), f, 0.20))
    a.rot("neck_2", Wave(V(1.8, 2.0, 0), f, 0.26))
    a.rot("mount_head", Wave(V(2.6, 3.4, 0), f, 0.32))
    a.rot("mount_head", Wave(V(0.8, 0, 0), 2 * f, 0.10))
    a.rot("jaw", Wave(V(2.0, 0, 0), 2 * f, 0.30, bias=V(2.0, 0, 0)))
    for i, nm in enumerate(("tail_1", "tail_2", "tail_3")):
        a.rot(nm, Wave(V(0, 6 + 4 * i, 0), f, 0.15 + 0.07 * i))
    for i, nm in enumerate(("mane_1", "mane_2", "mane_3")):
        a.rot(nm, Wave(V(4.0, 0, 1.5), 2 * f, 0.1 + 0.12 * i))
        a.rot(nm, V(-6, 0, 0))
    # the near fore hoof paws: lift, scrape back, lift, plant
    foot(a, "hoof_fore_L", pos=[(0, Z3), (1.9, Z3), (2.15, V(0, 0.035, 0.02), "out_cubic"), (2.40, V(0, 0.006, -0.05), "in_out_cubic"), (2.65, V(0, 0.032, -0.01), "in_out_cubic"), (2.95, Z3, "in_out_cubic"), (T, Z3)],
         rot=[(0, Z3), (1.9, Z3), (2.15, V(35, 0, 0), "out_cubic"), (2.40, V(12, 0, 0), "in_out_cubic"), (2.65, V(30, 0, 0), "in_out_cubic"), (2.95, Z3, "in_out_cubic"), (T, Z3)])
    # rider: breath, look, lance sway
    a.rot("spine", Wave(V(-0.7, 0, 0), 2 * f, 0.06))
    a.rot("chest", Wave(V(-1.0, 0, 0), 2 * f, 0.10))
    a.rot("head", Wave(V(0.8, 3.0, 0), f, 0.40))
    hold_lance(a, dir_=Fn(lambda t: unit(A_L + V(0.012 * math.sin(2 * math.pi * (t / T + 0.2)), 0.015 * math.sin(2 * math.pi * 2 * t / T), 0))))
    return a, T, True, 30, ()


# ---------------------------------------------------------------------------------------------- Move: 3-beat canter in place
def clip_move(rig):
    a = _anim(rig)
    T = 0.9
    f = 1 / T
    duty = 0.46
    offs = {"hoof_hind_R": 0.0, "hoof_hind_L": 0.16, "hoof_fore_R": 0.16, "hoof_fore_L": 0.32}
    for nm, off in offs.items():
        fore = "fore" in nm
        stride, lift, z0, pk = (0.26, 0.13, 0.035, 38) if fore else (0.22, 0.10, -0.01, 26)

        def path(t, off=off, stride=stride, lift=lift, z0=z0, pk=pk):
            u = (t / T - off) % 1.0
            half = stride / 2
            if u < duty:
                w = u / duty
                pitch = 0.0
                if w > 0.8:
                    q = (w - 0.8) / 0.2
                    pitch = 22 * q * q * (3 - 2 * q)
                return V(0, 0.0, z0 + half - stride * w), pitch
            w = (u - duty) / (1 - duty)
            e = w * w * (3 - 2 * w)
            pitch = 22 * (1 - w) ** 2 + pk * math.sin(math.pi * w) - 8 * math.sin(math.pi * max(0.0, w - 0.7) / 0.3) ** 2
            return V(0, lift * math.sin(math.pi * w) ** 1.2, z0 - half + stride * e), pitch
        g_ = goal_(a, nm)
        g_.pos, g_.rot = Fn(lambda t, p=path: p(t)[0]), Fn(lambda t, p=path: V(p(t)[1], 0, 0))
    U = lambda t: t / T                                         # noqa: E731
    a.pos("body", Fn(lambda t: V(0, 0.030 * (cs(U(t), 0.90) - 0.3), 0)))
    a.rot("body", Fn(lambda t: V(3.0 * cs(U(t), 0.30), 1.0 * cs(U(t), 0.1), 1.2 * cs(U(t), 0.6))))
    a.rot("mount_body", Fn(lambda t: V(-2.0 * cs(U(t), 0.15), 1.2 * cs(U(t), 0.5), 0)))
    a.rot("mount_chest", Fn(lambda t: V(2.5 * cs(U(t), 0.25), 0, 0)))
    a.rot("neck_1", Fn(lambda t: V(4.0 * cs(U(t), 0.35), 0, 0)))
    a.rot("neck_2", Fn(lambda t: V(5.0 * cs(U(t), 0.42), 0, 0)))
    a.rot("mount_head", Fn(lambda t: V(-5.0 * cs(U(t), 0.42) + 3, 0, 0)))
    a.rot("jaw", Fn(lambda t: V(3 + 3 * cs(U(t), 0.4), 0, 0)))
    for i, nm in enumerate(("tail_1", "tail_2", "tail_3")):
        a.rot(nm, V(8 + 6 * i, 0, 0))
        a.rot(nm, Wave(V(0, 5, 0), f, 0.1 * i))
    for i, nm in enumerate(("mane_1", "mane_2", "mane_3")):
        a.rot(nm, V(-14 - 3 * i, 0, 0))
        a.rot(nm, Wave(V(5.0, 0, 2.0), 2 * f, 0.12 * i))
    a.rot("spine", Fn(lambda t: V(5 + 2.5 * cs(U(t), 0.40), 0, 0)))
    a.rot("chest", Fn(lambda t: V(3 + 1.5 * cs(U(t), 0.45), 0, 0)))
    a.rot("head", Fn(lambda t: V(-6 - 3.0 * cs(U(t), 0.40), 0, 0)))
    d0 = lambda t: unit(A_L + V(0, 0.05 * cs(U(t), 0.35), 0.0))        # noqa: E731
    hold_lance(a, dir_=Fn(d0), pos=Fn(lambda t: WR0 + V(0, 0.006 * cs(U(t), 0.35), 0)))
    return a, T, True, 30, ()


FOLD, TUCK, REACH = V(-0.01, 0.25, -0.035), V(-0.01, 0.20, 0.0), V(0.0, 0.06, 0.16)       # fore-fetlock targets in chest space (delta from rest)


def gf(elev, yaw=0.0):
    """glaive axis (butt -> hooked end) pointing FORWARD at `elev` degrees above horizontal."""
    e = math.radians(elev)
    return unit(V(math.sin(math.radians(yaw)) * math.cos(e), math.sin(e), math.cos(math.radians(yaw)) * math.cos(e)))


def gd(elev, yaw=6.6):
    """same, pointing BACKWARD (the carried pose is gd(30, 6.6))."""
    e = math.radians(elev)
    return unit(V(math.sin(math.radians(yaw)) * math.cos(e), math.sin(e), -math.cos(math.radians(yaw)) * math.cos(e)))


def _fore_rear(a, t_up, t_hold_end, extra=None):
    pass


# ---------------------------------------------------------------------------------------------- HitReact
def clip_hit(rig):
    a = _anim(rig)
    T = 0.45
    a.pos("body", Curve([(0, Z3), (0.10, V(0, -0.010, -0.060), "out_cubic"), (0.45, V(0, 0, -0.015), "in_out_cubic")]))
    a.rot("body", Curve([(0, Z3), (0.10, V(-9, 5, 3), "out_cubic"), (0.45, V(-3, 1, 0), "in_out_cubic")]))
    a.rot("mount_body", Curve([(0, Z3), (0.10, V(-4, 0, 0), "out_cubic"), (0.45, V(-1, 0, 0), "in_out_cubic")]))
    a.rot("neck_1", Curve([(0, Z3), (0.10, V(-8, 3, 0), "out_cubic"), (0.45, V(-2, 0, 0), "in_out_cubic")]))
    a.rot("neck_2", Curve([(0, Z3), (0.11, V(-8, -3, 0), "out_cubic"), (0.45, V(-2, 0, 0), "in_out_cubic")]))
    a.rot("mount_head", Curve([(0, Z3), (0.10, V(-16, 6, 0), "out_cubic"), (0.45, V(-6, 0, 0), "in_out_cubic")]))
    a.rot("jaw", Curve([(0, Z3), (0.10, V(18, 0, 0), "out_cubic"), (0.45, V(4, 0, 0), "in_out_cubic")]))
    for i, nm in enumerate(("tail_1", "tail_2", "tail_3")):
        a.rot(nm, Curve([(0, Z3), (0.12 + 0.02 * i, V(10, 0, 0), "out_cubic"), (0.45, V(2, 0, 0), "in_out_cubic")]))
    a.rot("spine", Curve([(0, Z3), (0.10, V(-10, 0, 0), "out_cubic"), (0.45, V(-4, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, Z3), (0.11, V(-8, 3, 0), "out_cubic"), (0.45, V(-2, 0, 0), "in_out_cubic")]))
    a.rot("head", Curve([(0, Z3), (0.12, V(-12, 5, 0), "out_cubic"), (0.45, V(-4, 0, 0), "in_out_cubic")]))
    for nm, dl in (("hoof_fore_L", 0.0), ("hoof_fore_R", 0.02)):
        foot(a, nm, pos=[(0, Z3), (0.06 + dl, V(0, 0.03, -0.01), "out_cubic"), (0.16 + dl, V(0, 0, -0.03), "in_out_cubic"), (0.45, V(0, 0, -0.02), "in_out_cubic")],
             rot=[(0, Z3), (0.06 + dl, V(22, 0, 0), "out_cubic"), (0.16 + dl, Z3, "in_out_cubic"), (0.45, Z3)])
    for nm in ("hoof_hind_L", "hoof_hind_R"):
        foot(a, nm, pos=[(0, Z3), (0.14, V(0, 0, -0.03), "out_cubic"), (0.45, V(0, 0, -0.02), "in_out_cubic")])
    hold_lance(a, pos_keys=[(0, WR0), (0.10, WR0 + V(0, 0.012, -0.03), "out_cubic"), (0.45, WR0 + V(0, 0, -0.006), "in_out_cubic")],
               dir_keys=[(0, A_L), (0.10, gd(44), "out_cubic"), (0.45, gd(34), "in_out_cubic")])
    return a, T, False, 60, ()


# ---------------------------------------------------------------------------------------------- Attack: rear, leap, lance thrust on landing
IMPACT = 1.00
_ATK = {}


def clip_attack(rig):
    a = _anim(rig)
    T, I = 2.0, IMPACT
    _ATK["a"] = a
    a.pos("body", Curve([(0, Z3), (0.40, V(0, -0.055, -0.030), "in_out_cubic"), (0.52, V(0, -0.065, -0.036)), (0.58, V(0, -0.078, -0.040), "in_cubic"), (0.64, V(0, 0.020, -0.020), "out_cubic"),
                         (0.76, V(0, 0.135, 0.040), "in_out_cubic"), (0.88, V(0, 0.075, 0.110), "in_out_cubic"), (0.97, V(0, -0.012, 0.150), "in_cubic"), (1.00, V(0, -0.050, 0.160), "out_quad"),
                         (1.15, V(0, -0.045, 0.160)), (1.50, V(0, -0.010, 0.070), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("body", Curve([(0, Z3), (0.40, V(-30, 0, 0), "in_out_cubic"), (0.55, V(-36, 0, 0), "out_cubic"), (0.64, V(-28, 0, 0), "in_out_cubic"), (0.76, V(-10, 0, 0), "in_out_cubic"),
                         (0.88, V(8, 0, 0), "in_out_cubic"), (1.0, V(13, 0, 0), "in_cubic"), (1.15, V(11, 0, 0)), (1.5, V(-3, 0, 0), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("mount_body", Curve([(0, Z3), (0.40, V(-5, 0, 0), "in_out_cubic"), (0.55, V(-6, 0, 0)), (0.76, V(-3, 0, 0), "in_out_cubic"), (0.9, V(4, 0, 0), "in_out_cubic"), (1.0, V(8, 0, 0), "in_cubic"), (1.15, V(6, 0, 0)), (1.5, V(-2, 0, 0), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("mount_chest", Curve([(0, Z3), (0.40, V(-4, 0, 0), "in_out_cubic"), (0.55, V(-5, 0, 0)), (0.88, V(4, 0, 0), "in_out_cubic"), (1.0, V(7, 0, 0), "in_cubic"), (1.15, V(5, 0, 0)), (2.0, Z3, "in_out_cubic")]))
    a.rot("neck_1", Curve([(0, Z3), (0.40, V(-4, 0, 0), "in_out_cubic"), (0.55, V(-6, 0, 0)), (0.76, V(2, 0, 0), "in_out_cubic"), (0.88, V(-2, 0, 0), "in_out_cubic"), (0.95, V(12, 0, 0), "in_cubic"), (1.1, V(9, 0, 0)), (1.5, V(-3, 0, 0), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("neck_2", Curve([(0, Z3), (0.40, V(2, 0, 0), "in_out_cubic"), (0.55, V(2, 0, 0)), (0.76, V(-4, 0, 0), "in_out_cubic"), (0.88, V(-6, 0, 0)), (0.95, V(14, 0, 0), "in_cubic"), (1.1, V(10, 0, 0)), (1.5, V(-2, 0, 0), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("mount_head", Curve([(0, Z3), (0.40, V(-6, 0, 0), "in_out_cubic"), (0.55, V(-10, 0, 0), "out_cubic"), (0.76, V(-12, 0, 0), "in_out_cubic"), (0.88, V(-8, 0, 0), "in_out_cubic"), (0.95, V(22, 0, 0), "in_cubic"), (1.1, V(16, 0, 0)), (1.5, V(2, 0, 0), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("jaw", Curve([(0, Z3), (0.30, Z3), (0.45, V(16, 0, 0), "out_cubic"), (0.62, V(16, 0, 0)), (0.86, V(12, 0, 0), "in_out_cubic"), (0.95, V(-9, 0, 0), "in_cubic"), (1.2, V(-9, 0, 0)), (1.6, Z3, "in_out_cubic"), (2.0, Z3)]))
    for i, nm in enumerate(("mane_1", "mane_2", "mane_3")):
        a.rot(nm, Curve([(0, Z3), (0.40, V(14, 0, 0), "in_out_cubic"), (0.55, V(18, 0, 0)), (0.76, V(-22, 0, 0), "in_out_cubic"), (1.0, V(-12, 0, 0)), (1.15, V(8, 0, 0), "out_cubic"), (2.0, Z3, "in_out_cubic")]))
    for i, nm in enumerate(("tail_1", "tail_2", "tail_3")):
        a.rot(nm, Curve([(0, Z3), (0.40, V(-10 - 4 * i, 0, 0), "in_out_cubic"), (0.76, V(10 + 6 * i, 0, 0), "in_out_cubic"), (1.0, V(4, 0, 0)), (2.0, Z3, "in_out_cubic")]))
    # ---- fore feet: world -> chest space (rear, fold) -> tuck -> reach -> plant (world), then two small steps back
    for nm, dl in (("hoof_fore_L", 0.0), ("hoof_fore_R", 0.03)):
        foot(a, nm, space="mount_chest",
             blend=[(0, 0), (0.12 + dl, 0), (0.30 + dl, 1, "in_out_cubic"), (0.90, 1), (0.98, 0, "in_out_cubic")],
             pos=[(0, Z3), (0.12 + dl, Z3), (0.30 + dl, FOLD, "in_out_cubic"), (0.46, FOLD + V(0, 0.02, 0.01)), (0.55, FOLD), (0.64, TUCK, "in_out_cubic"), (0.84, REACH, "in_out_cubic"),
                  (0.98, V(0, 0, 0.22), "in_cubic"), (1.15, V(0, 0, 0.22)), (1.28 + dl, V(0, 0.07, 0.16), "in_out_cubic"), (1.42 + dl, V(0, 0, 0.10), "in_out_cubic"),
                  (1.55 + dl, V(0, 0.05, 0.05), "in_out_cubic"), (1.70 + dl, V(0, 0, 0.012), "in_out_cubic"), (1.90, Z3, "in_out_cubic")],
             rot=[(0, Z3), (0.12 + dl, Z3), (0.30 + dl, V(35, 0, 0), "in_out_cubic"), (0.64, V(40, 0, 0)), (0.84, V(-12, 0, 0), "in_out_cubic"), (0.98, Z3, "in_out_cubic"), (1.15, Z3),
                  (1.28 + dl, V(25, 0, 0), "in_out_cubic"), (1.45 + dl, Z3, "in_out_cubic"), (1.55 + dl, V(20, 0, 0), "in_out_cubic"), (1.70 + dl, Z3, "in_out_cubic"), (2.0, Z3)])
    # ---- hind feet: planted through the rear, push off, trail in flight (body space), land, step back
    for nm, dl in (("hoof_hind_L", 0.0), ("hoof_hind_R", 0.02)):
        foot(a, nm, space="body",
             blend=[(0, 0), (0.56, 0), (0.66, 1, "in_out_cubic"), (0.90, 1), (0.98, 0, "in_out_cubic")],
             pos=[(0, Z3), (0.40, V(0, 0, -0.03), "in_out_cubic"), (0.56, V(0, 0, -0.03)), (0.66, V(0, 0.10, -0.06), "in_out_cubic"), (0.76, V(0, 0.12, -0.07)), (0.90, V(0, 0.06, 0.05), "in_out_cubic"),
                  (0.99, V(0, 0, 0.14), "in_cubic"), (1.15, V(0, 0, 0.14)), (1.24 + dl, V(0, 0.07, 0.10), "in_out_cubic"), (1.38 + dl, V(0, 0, 0.07), "in_out_cubic"),
                  (1.55 + dl, V(0, 0.06, 0.04), "in_out_cubic"), (1.78, Z3, "in_out_cubic"), (2.0, Z3)],
             rot=[(0, Z3), (0.56, Z3), (0.66, V(30, 0, 0), "in_out_cubic"), (0.90, V(10, 0, 0), "in_out_cubic"), (0.99, Z3, "in_out_cubic"), (1.15, Z3), (1.24 + dl, V(20, 0, 0), "in_out_cubic"),
                  (1.38 + dl, Z3, "in_out_cubic"), (1.55 + dl, V(20, 0, 0), "in_out_cubic"), (1.78, Z3, "in_out_cubic"), (2.0, Z3)])
    # ---- rider: clings in the rear, lunges onto the lance at the landing
    a.rot("spine", Curve([(0, Z3), (0.40, V(8, 0, 0), "in_out_cubic"), (0.55, V(10, 0, 0)), (0.88, V(6, 0, 0), "in_out_cubic"), (0.97, V(12, 0, 0), "in_cubic"), (1.15, V(12, 0, 0)), (1.6, V(3, 0, 0), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("chest", Curve([(0, Z3), (0.40, V(6, 0, 0), "in_out_cubic"), (0.88, V(4, 0, 0), "in_out_cubic"), (1.0, V(9, 0, 0), "in_cubic"), (1.15, V(8, 0, 0)), (2.0, Z3, "in_out_cubic")]))
    a.rot("head", Curve([(0, Z3), (0.40, V(-8, 0, 0), "in_out_cubic"), (0.55, V(-10, 0, 0)), (1.0, V(-12, 0, 0), "in_cubic"), (1.3, V(-8, 0, 0)), (2.0, Z3, "in_out_cubic")]))
    hold_lance(a, pos_keys=[(0, WR0), (0.40, WR0 + V(0, 0.03, -0.02), "in_out_cubic"), (0.88, WR0 + V(0, 0.04, -0.02), "in_out_cubic"), (1.0, WR0 + V(0, -0.01, 0.07), "snap_in"), (1.15, WR0 + V(0, -0.01, 0.07)), (2.0, WR0, "in_out_cubic")],
               dir_keys=[(0, A_L), (0.40, gd(50), "in_out_cubic"), (0.55, gd(56)), (0.76, gd(62), "in_out_cubic"), (0.88, gd(72, 4), "in_out_cubic"), (1.0, gf(-16, 6), "snap_in"),
                         (1.15, gf(-14, 6)), (1.6, gd(10), "in_out_cubic"), (2.0, A_L, "in_out_cubic")])
    return a, T, False, 60, (I,)


# ---------------------------------------------------------------------------------------------- Victory: levade, lance high, trumpet
def clip_victory(rig):
    a = _anim(rig)
    T = 1.8
    a.pos("body", Curve([(0, Z3), (0.6, V(0, -0.085, -0.040), "out_cubic"), (T, V(0, -0.080, -0.040), "in_out_cubic")]))
    a.rot("body", Curve([(0, Z3), (0.6, V(-36, 0, 0), "out_back"), (T, V(-34, 0, 0), "in_out_cubic")]))
    a.rot("mount_body", Curve([(0, Z3), (0.6, V(-6, 0, 0), "out_cubic"), (T, V(-4, 0, 0))]))
    a.rot("neck_1", Curve([(0, Z3), (0.6, V(0, 0, 0), "out_cubic"), (T, V(0, 0, 0))]))
    a.rot("neck_2", Curve([(0, Z3), (0.6, V(4, 0, 0), "out_cubic"), (T, V(4, 0, 0))]))
    a.rot("mount_head", Curve([(0, Z3), (0.6, V(-2, 0, 0), "out_cubic"), (T, V(-4, 0, 0))]))
    a.rot("jaw", Curve([(0, Z3), (0.45, V(24, 0, 0), "out_cubic"), (1.1, V(20, 0, 0)), (T, V(10, 0, 0), "in_out_cubic")]))
    for i, nm in enumerate(("mane_1", "mane_2", "mane_3")):
        a.rot(nm, Curve([(0, Z3), (0.6, V(18, 0, 0), "out_cubic"), (T, V(10, 0, 0))]))
        a.rot(nm, Wave(V(4, 0, 0), 1.6, 0.1 * i))
    for i, nm in enumerate(("tail_1", "tail_2", "tail_3")):
        a.rot(nm, Curve([(0, Z3), (0.6, V(-10 - 4 * i, 0, 0), "out_cubic"), (T, V(-8, 0, 0))]))
    for nm, dl in (("hoof_fore_L", 0.0), ("hoof_fore_R", 0.05)):
        foot(a, nm, space="mount_chest", blend=[(0, 0), (0.08 + dl, 0), (0.45 + dl, 1, "in_out_cubic"), (T, 1)],
             pos=[(0, Z3), (0.08 + dl, Z3), (0.45 + dl, FOLD, "in_out_cubic"), (0.9 + dl, FOLD + V(0, 0.03, 0.03), "in_out_cubic"), (1.3 + dl, FOLD, "in_out_cubic"), (T, FOLD + V(0, 0.02, 0.02), "in_out_cubic")],
             rot=[(0, Z3), (0.08 + dl, Z3), (0.45 + dl, V(35, 0, 0), "in_out_cubic"), (T, V(35, 0, 0))])
    for nm in ("hoof_hind_L", "hoof_hind_R"):
        foot(a, nm, pos=[(0, Z3), (0.6, V(0, 0, -0.03), "out_cubic"), (T, V(0, 0, -0.03))])
    a.rot("spine", Curve([(0, Z3), (0.3, V(6, 0, 0)), (0.6, V(-4, 0, 0), "out_cubic"), (T, V(-3, 0, 0))]))
    a.rot("chest", Curve([(0, Z3), (0.6, V(-8, 0, 0), "out_cubic"), (T, V(-8, 0, 0))]))
    a.rot("head", Curve([(0, Z3), (0.6, V(-10, 0, 0), "out_cubic"), (T, V(-9, 0, 0))]))
    hold_lance(a, pos_keys=[(0, WR0), (0.3, WR0 + V(0, 0.0, 0.0)), (0.6, WR0 + V(0, 0.03, -0.01), ("spring", 0.12, 1.5)), (T, WR0 + V(0, 0.035, -0.01), "in_out_cubic")],
               dir_keys=[(0, A_L), (0.3, gd(60), "in_out_cubic"), (0.65, gf(80), ("spring", 0.10, 1.5)), (T, gf(84), "in_out_cubic")])
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Taunt: rear, two stamps, lance levelled at the enemy
def clip_taunt(rig):
    a = _anim(rig)
    T = 1.3
    a.pos("body", Curve([(0, Z3), (0.45, V(0, -0.060, -0.030), "in_out_cubic"), (0.58, V(0, -0.070, -0.034)), (0.74, V(0, -0.020, 0.0), "in_cubic"), (0.86, V(0, 0.010, 0.0), "out_cubic"),
                         (0.98, V(0, -0.022, 0.0), "in_cubic"), (1.10, Z3, "out_cubic"), (T, Z3)]))
    a.rot("body", Curve([(0, Z3), (0.45, V(-30, 0, 0), "in_out_cubic"), (0.58, V(-32, 0, 0)), (0.74, V(5, 0, 0), "in_cubic"), (0.86, V(-4, 0, 0), "out_cubic"), (0.98, V(4, 0, 0), "in_cubic"), (1.10, V(-1, 0, 0), "out_cubic"), (T, Z3, "in_out_cubic")]))
    a.rot("mount_head", Curve([(0, Z3), (0.45, V(-8, 0, 0), "in_out_cubic"), (0.58, V(-12, 0, 0)), (0.80, V(26, 0, 0), "in_out_cubic"), (1.05, V(28, 0, 0)), (1.3 - 0.0, Z3, "in_out_cubic")]))
    a.rot("neck_1", Curve([(0, Z3), (0.45, V(-5, 0, 0), "in_out_cubic"), (0.80, V(16, 0, 0), "in_out_cubic"), (1.05, V(16, 0, 0)), (T, Z3, "in_out_cubic")]))
    a.rot("neck_2", Curve([(0, Z3), (0.45, V(-2, 0, 0), "in_out_cubic"), (0.80, V(18, 0, 0), "in_out_cubic"), (1.05, V(18, 0, 0)), (T, Z3, "in_out_cubic")]))
    a.rot("jaw", Curve([(0, Z3), (0.45, V(16, 0, 0), "out_cubic"), (0.74, V(4, 0, 0)), (T, Z3, "in_out_cubic")]))
    for i, nm in enumerate(("mane_1", "mane_2", "mane_3")):
        a.rot(nm, Curve([(0, Z3), (0.45, V(16, 0, 0), "in_out_cubic"), (0.74, V(-20, 0, 0), "in_cubic"), (1.1, V(-4, 0, 0)), (T, Z3, "in_out_cubic")]))
    for nm, dl in (("hoof_fore_L", 0.0), ("hoof_fore_R", 0.03)):
        foot(a, nm, space="mount_chest", blend=[(0, 0), (0.08 + dl, 0), (0.38 + dl, 1, "in_out_cubic"), (0.66, 1), (0.745 + dl, 0, "in_out_cubic")],
             pos=[(0, Z3), (0.08 + dl, Z3), (0.38 + dl, FOLD, "in_out_cubic"), (0.62, FOLD), (0.74 + dl, Z3, "in_cubic"), (0.86 + dl, V(0, 0.07, -0.02), "out_cubic"), (0.98 + dl, Z3, "in_cubic"), (T, Z3)],
             rot=[(0, Z3), (0.38 + dl, V(35, 0, 0), "in_out_cubic"), (0.62, V(35, 0, 0)), (0.74 + dl, Z3, "in_cubic"), (0.86 + dl, V(20, 0, 0), "out_cubic"), (0.98 + dl, Z3, "in_cubic"), (T, Z3)])
    for nm in ("hoof_hind_L", "hoof_hind_R"):
        foot(a, nm, pos=[(0, Z3), (0.45, V(0, 0, -0.03), "in_out_cubic"), (0.74, V(0, 0, -0.01)), (T, Z3, "in_out_cubic")])
    a.rot("spine", Curve([(0, Z3), (0.45, V(8, 0, 0), "in_out_cubic"), (0.74, V(-2, 0, 0)), (1.1, V(-5, 0, 0), "in_out_cubic"), (T, Z3, "in_out_cubic")]))
    a.rot("head", Curve([(0, Z3), (1.1, V(-6, 6, 0), "in_out_cubic"), (T, Z3, "in_out_cubic")]))
    hold_lance(a, pos_keys=[(0, WR0), (0.45, WR0 + V(0, 0.01, 0.0), "in_out_cubic"), (1.02, WR0 + V(0, -0.01, 0.03), "in_out_cubic"), (1.3 - 0.0, WR0, "in_out_cubic")],
               dir_keys=[(0, A_L), (0.45, gd(56), "in_out_cubic"), (0.74, gf(70)), (1.02, gf(-6, 4), "in_out_cubic"), (1.2, gf(-6, 4)), (T, A_L, "in_out_cubic")])
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Surrender: the horse kneels, the rider bows, the lance drops
def clip_surrender(rig):
    a = _anim(rig)
    T = 2.2
    a.pos("body", Curve([(0, Z3), (0.30, V(0, -0.010, -0.040), "out_cubic"), (0.55, V(0, -0.020, -0.020), "in_out_cubic"), (1.35, V(0, -0.140, 0.0), "in_out_cubic"), (T, V(0, -0.145, 0.0), "in_out_cubic")]))
    a.rot("body", Curve([(0, Z3), (0.30, V(-6, 0, 0), "out_cubic"), (0.55, Z3, "in_out_cubic"), (1.35, V(8, 0, 0), "in_out_cubic"), (T, V(8, 0, 0))]))
    a.rot("mount_body", Curve([(0, Z3), (1.35, V(4, 0, 0), "in_out_cubic"), (T, V(4, 0, 0))]))
    a.rot("neck_1", Curve([(0, Z3), (0.30, V(-4, 0, 0), "out_cubic"), (1.35, V(8, 0, 0), "in_out_cubic"), (T, V(9, 0, 0), "in_out_cubic")]))
    a.rot("neck_2", Curve([(0, Z3), (0.30, V(-4, 0, 0), "out_cubic"), (1.35, V(10, 0, 0), "in_out_cubic"), (T, V(11, 0, 0), "in_out_cubic")]))
    a.rot("mount_head", Curve([(0, Z3), (0.30, V(-12, 0, 0), "out_cubic"), (1.35, V(16, 0, 0), "in_out_cubic"), (T, V(18, 0, 0), "in_out_cubic")]))
    a.rot("jaw", Curve([(0, Z3), (0.3, V(8, 0, 0)), (1.35, V(6, 0, 0)), (T, V(2, 0, 0))]))
    for i, nm in enumerate(("mane_1", "mane_2", "mane_3")):
        a.rot(nm, Curve([(0, Z3), (1.35, V(20, 0, 0), "in_out_cubic"), (T, V(24, 0, 0))]))
    for i, nm in enumerate(("tail_1", "tail_2", "tail_3")):
        a.rot(nm, Curve([(0, Z3), (1.35, V(10 + 4 * i, 0, 0), "in_out_cubic"), (T, V(12 + 4 * i, 0, 0))]))
    for nm, dl in (("hoof_fore_L", 0.0), ("hoof_fore_R", 0.08)):
        foot(a, nm, pos=[(0, Z3), (0.55, Z3), (0.95 + dl, V(0, 0.06, -0.06), "in_out_cubic"), (1.35 + dl, V(0, -0.045, -0.115), "in_out_cubic"), (T, V(0, -0.045, -0.115))],
             rot=[(0, Z3), (0.55, Z3), (0.95 + dl, V(40, 0, 0), "in_out_cubic"), (1.35 + dl, V(75, 0, 0), "in_out_cubic"), (T, V(75, 0, 0))])
    for nm in ("hoof_hind_L", "hoof_hind_R"):
        foot(a, nm, pos=[(0, Z3), (0.55, Z3), (1.35, V(0, 0, -0.03), "in_out_cubic"), (T, V(0, 0, -0.03))])
    a.rot("spine", Curve([(0, Z3), (0.30, V(-3, 0, 0), "out_cubic"), (0.9, V(10, 0, 0), "in_out_cubic"), (1.6, V(22, 0, 0), "in_out_cubic"), (T, V(26, 0, 0), "in_out_cubic")]))
    a.rot("chest", Curve([(0, Z3), (0.9, V(5, 0, 0), "in_out_cubic"), (1.7, V(9, 0, 0), "in_out_cubic"), (T, V(10, 0, 0))]))
    a.rot("neck", Curve([(0, Z3), (1.0, V(8, 0, 0), "in_out_cubic"), (T, V(10, 0, 0))]))
    a.rot("head", Curve([(0, Z3), (0.3, V(-8, 0, 0), "out_cubic"), (1.0, V(18, 0, 0), "in_out_cubic"), (T, V(28, 2, 3), "in_out_cubic")]))
    hold_lance(a, pos_keys=[(0, WR0), (0.20, WR0 + V(0, -0.02, 0.01), "in_out_cubic"), (0.45, WR0 + V(0, -0.03, 0.01), "in_out_cubic"), (0.9, WR0 + V(-0.01, -0.06, 0.02), "in_out_cubic"), (T, WR0 + V(-0.01, -0.06, 0.02))],
               dir_keys=[(0, A_L), (0.30, gd(22), "in_out_cubic"), (0.9, gd(0), "in_out_cubic"), (T, gd(-8), "in_out_cubic")])
    M.release_weapon(a, "weapon", 0.45, 0.22, 0.016, A_L, (0.10, 0.0, -1.0), land_xz=(-0.22, -0.02), up_local=None, roll_deg=90.0)
    return a, T, False, 30, ()


def fix_impact_socket(rig, a):
    """socket_impact (under mount_body) = where the lance tip is at impactTime."""
    c = a.pose(IMPACT)
    sk = a.sk
    iw, ib = sk.ix["weapon"], sk.ix["mount_body"]
    tip = c.Pw[iw] + c.Rw[iw] @ (GLAIVE_T - sk.rest[iw])
    local = sk.rest[ib] + c.Rw[ib].T @ (tip - c.Pw[ib])
    return tuple(float(x) for x in local)


def make_clips(rig):
    import pickle
    cache = os.environ.get("FORGE_CLIPCACHE")
    if cache and os.path.exists(cache):
        with open(cache, "rb") as fh:
            out, sock = pickle.load(fh)
        rig.socket("socket_impact", "mount_body", sock)
        return out
    out = []
    for name, fn in CLIPS:
        a, dur, loop, fps, keep = fn(rig)
        out.append(a.bake(name, dur, loop=loop, fps=fps, keep_times=keep))
    sock = fix_impact_socket(rig, _ATK["a"])
    rig.socket("socket_impact", "mount_body", sock)
    if cache:
        with open(cache, "wb") as fh:
            pickle.dump((out, sock), fh)
    return out


CLIPS = [("Idle", clip_idle), ("Move", clip_move), ("Attack", clip_attack), ("HitReact", clip_hit), ("Victory", clip_victory), ("Taunt", clip_taunt), ("Surrender", clip_surrender)]


# ======================================================================================= placeholder clips (dev) + build
def stub_clips(rig):
    out = []
    for nm, dur, loop in (("Idle", 3.0, True), ("Move", 0.9, True), ("Attack", 2.0, False), ("HitReact", 0.45, False), ("Victory", 1.8, False), ("Taunt", 1.3, False), ("Surrender", 2.2, False)):
        c = Clip(nm, dur, loop=loop, fps=30)
        c.key("body", "pos", 0.0, (0, 0, 0))
        c.key("body", "pos", dur, (0, 0, 0))
        out.append(c)
    return out


def build(log=print):
    rig = make_rig()
    clips = stub_clips(rig) if os.environ.get("FORGE_STUB") else make_clips(rig)
    p = Piece("rime", "knight", rig, clips, impact_time=1.00, strike_range=0.50, attack_style="leap", seed=10)
    rc.pedestal_parts(p)
    horse_body(p)
    neck_and_crinet(p)
    head_parts(p)
    mane(p)
    barding(p)
    rider(p)
    glaive(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
