"""emberhold_knight - Emberhold Ashmane Rider.

A BARDED BRONZE WAR-HORSE charger (the horse replaced the old war-elk) carrying a crouched, armoured rider with a pennoned lance.
The horse is the identity cue: a tall arched neck of overlapping bronze crinet plates under a flame mane, a wedge-shaped head in a
bronze chanfron (face plate) with eye rondels and short upright ear covers, peytral / flanchards / crupper barding over an ash-dark
coat, a swept tail with an ember tip.  Everything above y 1.10 is horse; the rider tops out at 1.10, the ears and mane tips at 1.30.

Rig: quadruped_rig (spine chain body > mount_body > mount_chest, neck_1/2, mount_head, jaw, 4 legs x upper/lower/hoof, tail_1..3, three
mane bones) + the humanoid rider (rider_pelvis under the saddle bone `top`).  Smooth chain skins on legs / neck / barrel / tail / mane,
rigid barding plates.  Procedural IK clips: a real 3-beat canter, rear, leap, lance thrust, kneel.  Built from docs/art/emberhold_knight.md.
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
import _emberhold_common as C                      # noqa: E402

ASSET_ID = "emberhold_knight"
V = lambda *x: np.array(x, dtype=float)            # noqa: E731
COAT = lambda P: np.full(len(P), 1.22)             # ash coat tint
COAT_MAT = "EH_Leather"

# ======================================================================================= joints (rest pose, world coordinates)
HEAD_PITCH = 52.0                                   # head hangs this many degrees below horizontal
JQ = dict(rump=(0, 0.66, -0.22), barrel=(0, 0.64, -0.04), withers=(0, 0.78, 0.12), neck_1=(0, 0.85, 0.17), neck_2=(0, 1.03, 0.24),
          head=(0, 1.165, 0.305), jaw=(0, 1.10, 0.345), seat=(0, 0.80, -0.06),
          hip_L=(0.10, 0.64, -0.22), hock_L=(0.115, 0.435, -0.33), fetlock_L=(0.115, 0.29, -0.27), hoof_L=(0.115, 0.22, -0.235),
          shoulder_L=(0.10, 0.70, 0.10), elbow_L=(0.11, 0.45, 0.185), fetlock_F_L=(0.11, 0.30, 0.155), hoof_F_L=(0.11, 0.22, 0.185),
          tail_1=(0, 0.71, -0.30), tail_2=(0, 0.60, -0.365), tail_3=(0, 0.47, -0.385))
JR = dict(pelvis=(0, 0.835, -0.10), spine=(0, 0.875, -0.075), chest=(0, 0.935, -0.03), neck=(0, 0.985, 0.025), head=(0, 1.005, 0.055),
          top=(0, 0.80, -0.06),
          clavicle_L=(0.055, 0.955, -0.005), shoulder_L=(0.155, 0.945, 0.0), elbow_L=(0.185, 0.885, 0.065), wrist_L=(0.10, 0.875, 0.15),
          hip_L=(0.095, 0.82, -0.10), knee_L=(0.20, 0.74, 0.04), ankle_L=(0.20, 0.54, 0.01), toe_L=(0.20, 0.51, 0.09),
          elbow_R=(-0.19, 0.875, 0.03), wrist_R=(-0.20, 0.857, 0.11))
LANCE_B, LANCE_T = V(-0.20, 0.80, -0.19), V(-0.20, 0.93, 0.50)       # butt, tip of the lance
LANCE_C = (LANCE_B + LANCE_T) / 2
MANE_ROOTS = [(0, 1.14, 0.262), (0, 0.99, 0.205), (0, 0.84, 0.13)]    # mane_1..3 pivots (crest)


def make_rig() -> Rig:
    r = quadruped_rig(JQ)
    hr = humanoid_rig(JR, weapon=tuple(LANCE_C), pelvis_name="rider_pelvis")
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
    r.socket("socket_weapon_R", "weapon", tuple(LANCE_T))
    r.socket("socket_cast", "mount_head", (0, 1.30, 0.28))
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
BARREL = Stn([(0, .655, -.335), (0, .66, -.30), (0, .655, -.24), (0, .645, -.14), (0, .645, -.04), (0, .65, .06), (0, .655, .14), (0, .635, .21), (0, .615, .26), (0, .60, .29)],
             [.04, .115, .14, .135, .145, .15, .14, .115, .075, .03], [.05, .125, .135, .14, .135, .15, .145, .14, .10, .04], e=2.3, samples=3)
NECK = Stn([(0, .745, .095), (0, .85, .17), (0, .94, .21), (0, 1.03, .24), (0, 1.10, .27), (0, 1.165, .305)],
           [.116, .108, .090, .076, .063, .051], [.150, .135, .112, .094, .076, .058], e=2.4, samples=4)
COATM = dict(uv_scale=1, tint=COAT)


def barrel_z(z, th, grow=0.0):
    """Point on the barrel surface at world z (interpolated station), angle th (0 = +X side, 90 = underside, 270 = back)."""
    u = float(np.interp(z, BARREL.c[:, 2], BARREL.s))
    return BARREL.pt(u, th, grow)


def barrel_u(z):
    return float(np.interp(z, BARREL.c[:, 2], BARREL.s))


def horse_body(p: Piece):
    p.add("m_barrel", BARREL.mesh(K=20, stride=1).noised(0.0022, 16, 3, seed=2), COAT_MAT, None, skin=BARREL_SKIN, **COATM)
    for s, n in ((1, "L"), (-1, "R")):
        hx = s * 0.118
        ha = g.superellipsoid((0.046, 0.088, 0.090), 0.85, 0.9, 6, 12).rotated(-6, 0, 0).translated(hx - s * 0.006, 0.620, -0.215).noised(0.0022, 16, 2, seed=3 + s)
        p.add(f"m_haunch_{n}", ha, COAT_MAT, None, skin=Skin.nearest([("body", JQ["rump"], (0, 0.64, -0.08)), (f"hind_upper_{n}", JQ["hip_L"] if s > 0 else (-0.10, 0.64, -0.22), (s * 0.115, 0.435, -0.33))], tau=0.05, bias={"body": 1.6}), **COATM)
        sh = g.superellipsoid((0.044, 0.088, 0.080), 0.85, 0.9, 6, 12).rotated(8, 0, 0).translated(s * 0.112, 0.645, 0.115).noised(0.0022, 16, 2, seed=5 + s)
        p.add(f"m_shoulder_{n}", sh, COAT_MAT, None, skin=Skin.nearest([("mount_chest", (0, 0.72, 0.10), (0, 0.66, 0.22)), (f"fore_upper_{n}", (s * 0.10, 0.70, 0.10), (s * 0.11, 0.45, 0.185))], tau=0.05, bias={"mount_chest": 1.6}), **COATM)
    wi = g.superellipsoid((0.075, 0.055, 0.12), 0.8, 0.9, 5, 11).translated(0, 0.775, 0.095).noised(0.005, 14, 3, seed=7)
    p.add("m_withers", wi, COAT_MAT, None, skin=BARREL_SKIN, **COATM)
    # ---- legs: one continuous limb tube per leg with dense rings at the hock / carpus / fetlock, smooth chain skin
    for s, n in ((1, "L"), (-1, "R")):
        X = lambda v: (s * v[0], v[1], v[2])        # noqa: E731
        hip, hock, fet, hoof = (np.array(X(JQ[k])) for k in ("hip_L", "hock_L", "fetlock_L", "hoof_L"))
        hind = limb_tube([hip + [0, 0.05, 0.0], (hip + hock) / 2 + [0, 0.0, 0.01], hock, (hock + fet) / 2 + [0, 0, 0.004], fet, (fet + hoof) / 2 + [0, 0.012, 0], hoof + [0, 0.035, 0.0]],
                         [0.062, 0.052, 0.036, 0.027, 0.024, 0.029, 0.028], joints=[hock, fet], spacing=0.032, joint_spacing=0.016, joint_zone=0.045, sides=9, cap=None, up=(1, 0, 0), ellipse=(0.92, 1.1))
        p.add(f"m_hindleg_{n}", hind.noised(0.0016, 24, 2, seed=11 + s), COAT_MAT, None, skin=hind_skin(n), **COATM)
        pt_ = g.superellipsoid((0.026, 0.040, 0.030), 0.7, 0.7, 4, 9).translated(*(hock + [0, 0.0, -0.016]))
        p.add(f"m_hock_{n}", pt_, COAT_MAT, None, skin=hind_skin(n), **COATM)
        sho, car, ffet, fhoof = (np.array(X(JQ[k])) for k in ("shoulder_L", "elbow_L", "fetlock_F_L", "hoof_F_L"))
        fore = limb_tube([sho + [0, 0.05, 0.0], (sho + car) / 2 + [0, 0, 0.012], car, (car + ffet) / 2 + [0, 0, 0.002], ffet, (ffet + fhoof) / 2 + [0, 0.012, 0.004], fhoof + [0, 0.035, 0.0]],
                         [0.052, 0.043, 0.030, 0.024, 0.022, 0.027, 0.026], joints=[car, ffet], spacing=0.032, joint_spacing=0.016, joint_zone=0.045, sides=9, cap=None, up=(1, 0, 0), ellipse=(0.95, 1.05))
        p.add(f"m_foreleg_{n}", fore.noised(0.0016, 24, 2, seed=15 + s), COAT_MAT, None, skin=fore_skin(n), **COATM)
        kn = g.superellipsoid((0.030, 0.030, 0.030), 0.7, 0.7, 4, 9).translated(*(car + [0, 0.0, 0.006]))
        p.add(f"m_knee_{n}", kn, COAT_MAT, None, skin=fore_skin(n), **COATM)
        # hooves (steel) with a bronze coronet band, rigid on the hoof bones; fetlock tufts
        for key, hb, ftp, hfp, zc, front in (("hind", f"hind_hoof_{n}", fet, hoof, hoof[2] - 0.005, False), ("fore", f"fore_hoof_{n}", ffet, fhoof, fhoof[2] - 0.005, True)):
            xx = hfp[0]
            prof = np.array([(0.0, 0.2205), (0.040, 0.2205), (0.0415, 0.226), (0.0385, 0.246), (0.0345, 0.257), (0.030, 0.259), (0.0, 0.259)])
            hoofm = g.lathe(prof, 14, crease=50).scaled(1.0, 1.0, 1.18).translated(xx, 0, zc)
            p.add(f"m_{key}hoof_{n}", hoofm, "EH_Steel", hb, uv_scale=2)
            p.add(f"m_{key}coronet_{n}", g.torus(0.0345, 0.0048, 14, 4).scaled(1.0, 1.0, 1.18).translated(xx, 0.2585, zc), "EH_Bronze", hb, lod1=None)
        # greaves on the cannon bones (bronze) with rolled lips
        for key, a_, b_, lb, rr in (("hind", hock + [0, -0.045, 0.012], fet + [0, 0.02, 0.0], f"hind_lower_{n}", 0.034), ("fore", car + [0, -0.045, 0.004], ffet + [0, 0.02, 0.0], f"fore_lower_{n}", 0.031)):
            gr = g.tube([a_, (a_ + b_) / 2, b_], [rr + 0.004, rr - 0.001, rr - 0.004], sides=10, samples=2, cap=None, up=(1, 0, 0), ellipse=(0.95, 1.05))
            p.add(f"m_{key}greave_{n}", gr.noised(0.0012, 34, 2, seed=21 + s), "EH_Bronze", lb)
            for q, (pp, r2) in enumerate(((a_, rr + 0.005), (b_, rr - 0.002))):
                p.add(f"m_{key}lip_{n}{q}", g.torus(r2, 0.0042, 14, 4).translated(*pp), "EH_Bronze", lb, lod1=None)
    # ---- tail (chain skin) with strands and an ember tuft
    tp = [(0, 0.71, -0.30), (0, 0.62, -0.355), (0, 0.50, -0.385), (0, 0.40, -0.385), (0, 0.34, -0.37)]
    p.add("m_tail", g.tube(tp, [0.024, 0.032, 0.030, 0.022, 0.010], sides=8, samples=3, cap="round", cap_steps=1, up=(1, 0, 0)).noised(0.003, 18, 3, seed=9), COAT_MAT, None, skin=TAIL_SKIN, **COATM)
    st = []
    for k, (dx, dz, ln) in enumerate(((-0.016, -0.008, 0.36), (0.016, -0.010, 0.34), (0.0, -0.022, 0.30))):
        pts = [(dx * 0.3, 0.66, -0.335), (dx * 0.8, 0.56, -0.378 + dz), (dx * 1.3, 0.47, -0.398 + dz), (dx * 1.6, 0.47 - ln * 0.55, -0.385 + dz * 1.4)]
        st.append(g.tube(pts, [0.012, 0.013, 0.010, 0.0025], sides=5, samples=2, cap="round", cap_steps=1, up=(1, 0, 0)))
    p.add("m_tail_strands", merge(st).noised(0.002, 20, 2, seed=29), COAT_MAT, None, skin=TAIL_SKIN, **COATM)
    for k in range(3):
        a = (k - 1) * 0.5
        tuft = g.tube([(0.012 * a, 0.40, -0.385), (0.02 * a, 0.335, -0.388), (0.03 * a, 0.285, -0.382 - 0.01 * a)], [0.010, 0.008, 0.0015], sides=5, samples=2, cap="round", cap_steps=1, up=(1, 0, 0))
        p.add(f"m_tail_ember{k}", tuft, "EH_Flame", None, skin=TAIL_SKIN, bake=False, lod1="keep")
    for i, z in enumerate((0.0, -0.06)):
        p.add(f"m_tail_ring{i}", g.torus(0.034, 0.0055, 14, 4).rotated(14, 0, 0).translated(0, 0.585 - 0.07 * i, -0.368 - 0.012 * i), "EH_Bronze", "tail_2", lod1=None)
    # ---- fetlock feathering
    tuft = g.tube([(0, 0, 0), (0.002, -0.018, 0.004), (0.004, -0.036, 0.010)], [0.013, 0.009, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    rng = np.random.default_rng(77)
    for s, n in ((1, "L"), (-1, "R")):
        for key, jj, bn in (("hind", JQ["fetlock_L"], f"hind_hoof_{n}"), ("fore", JQ["fetlock_F_L"], f"fore_hoof_{n}")):
            pos = [(s * jj[0] + 0.020 * math.sin(a), jj[1] - 0.004, jj[2] + 0.020 * math.cos(a)) for a in np.arange(5) * TAU / 5]
            nrm = [(math.sin(a) * 0.6, -1, math.cos(a) * 0.6) for a in np.arange(5) * TAU / 5]
            p.add(f"m_{key}feather_{n}", g.instances(tuft, pos, nrm, 1.0, spins=rng.random(5) * 360), COAT_MAT, bn, uv_scale=2, tint=COAT, lod1=None)


# ======================================================================================= neck, crinet, head, mane
HPIV = np.array(JQ["head"])


def to_head(m):
    """Canonical head frame (poll at the origin, muzzle along +Z, up = +Y) -> world."""
    return m.rotated(HEAD_PITCH, 0, 0).translated(*HPIV)


def hpt(v):
    a = math.radians(HEAD_PITCH)
    x, y, z = v
    return np.array([x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)]) + HPIV


def _head_stn(zs, top, bot, hw, e=2.5, samples=3):
    top, bot = np.asarray(top, float), np.asarray(bot, float)
    path = [(0, (t + b) / 2, z) for z, t, b in zip(zs, top, bot)]
    return Stn(path, hw, (top - bot) / 2, e=e, samples=samples)


HZ = [-0.02, 0.03, 0.08, 0.13, 0.18, 0.24, 0.29, 0.325, 0.343]
H_TOP = [0.042, 0.048, 0.046, 0.038, 0.028, 0.017, 0.009, 0.001, -0.008]
H_BOT = [-0.070, -0.080, -0.068, -0.044, -0.030, -0.020, -0.018, -0.016, -0.012]
H_HW = [0.042, 0.050, 0.054, 0.050, 0.042, 0.036, 0.036, 0.032, 0.022]
HEAD = _head_stn(HZ, H_TOP, H_BOT, H_HW)
JZ = [0.04, 0.08, 0.13, 0.18, 0.24, 0.29, 0.325, 0.343]
J_TOP = [-0.060, -0.058, -0.034, -0.020, -0.010, -0.008, -0.006, -0.004]       # overlaps the head by 0.01
J_BOT = [-0.090, -0.090, -0.075, -0.055, -0.042, -0.040, -0.034, -0.030]
J_HW = [0.044, 0.046, 0.042, 0.034, 0.028, 0.026, 0.024, 0.017]
JAW = _head_stn(JZ, J_TOP, J_BOT, J_HW, e=2.3)
JAW_PIV = (0, -0.05, 0.05)


def neck_and_crinet(p: Piece):
    p.add("m_neck", NECK.mesh(K=16, cap0=False, cap1=False).noised(0.004, 16, 3, seed=13), COAT_MAT, None, skin=NECK_SKIN, **COATM)
    # crinet: overlapping bronze lames over the back and sides of the neck (the brightest arch on the piece)
    centers = [0.10, 0.25, 0.40, 0.55, 0.70, 0.86]
    for i, uc in enumerate(centers):
        du = 0.075
        bn = "neck_1" if uc < 0.50 else "neck_2"
        us = [uc - du, uc - du * 0.15, uc + du * 0.9]
        gr = [0.016 + 0.0014 * i, 0.021 + 0.0014 * i, 0.013 + 0.0014 * i]
        sh = NECK.shell(us, 150, 390, nth=11, grow=gr, crease=40)
        p.add(f"m_crinet_{i}", sh.noised(0.0009, 34, 2, seed=30 + i), "EH_Bronze", bn)
        lip = g.tube([NECK.pt(us[0], th, gr[0] + 0.002) for th in np.linspace(150, 390, 12)], 0.0048, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
        p.add(f"m_crinet_lip_{i}", lip, "EH_Bronze", bn, lod1=None)
        # centre stud on the crest
        c0 = NECK.pt(uc, 270, gr[1] + 0.004)
        p.add(f"m_crinet_stud_{i}", g.dome(0.0085 - 0.0004 * i, 0.007, 7, 1).aimed(unit(NECK.pt(uc, 270, 0.1) - NECK.at(uc)[0]), c0), "EH_Steel", bn, lod1=None)


def head_parts(p: Piece):
    skull = to_head(HEAD.mesh(K=18, cap0=True, cap1=True, crease=55).noised(0.0025, 22, 2, seed=16))
    p.add("m_skull", skull, COAT_MAT, "mount_head", **COATM)
    jaw = to_head(JAW.mesh(K=14, cap0=True, cap1=True, crease=55).noised(0.002, 22, 2, seed=17))
    p.add("m_jaw", jaw, COAT_MAT, "jaw", **COATM)
    # nostrils + muzzle lips
    nos = [to_head(g.superellipsoid((0.0085, 0.0045, 0.012), 0.7, 0.7, 3, 7).rotated(0, s * 12, 0).translated(s * 0.017, -0.004, 0.331)) for s in (-1, 1)]
    p.add("m_nostrils", merge(nos), "EH_Steel", "mount_head", lod1=None)
    # chanfron: face plate conforming to the skull, rolled edges, central ridge, brow boss, rivets
    us = np.linspace(0.04, 0.985, 9)
    gr = 0.007 + 0.002 * np.sin(np.linspace(0, math.pi, 9))
    chan = to_head(HEAD.shell(us, -152, -28, nth=11, grow=gr, crease=40).noised(0.0010, 34, 2, seed=18))
    p.add("m_chanfron", chan, "EH_Bronze", "mount_head")
    ridge = [hpt(HEAD.pt(u, -90, 0.0105)) for u in np.linspace(0.04, 0.99, 8)]
    p.add("m_chanfron_ridge", g.tube([np.array(q) for q in ridge], [0.0070, 0.0085, 0.0085, 0.0080, 0.0075, 0.0070, 0.0060, 0.0045], sides=5, samples=2, cap="round", cap_steps=1), "EH_Bronze", "mount_head")
    ed = []
    for th in (-152, -28):
        ed.append(g.tube([np.array(hpt(HEAD.pt(u, th, g_ + 0.001))) for u, g_ in zip(us, gr)], 0.0047, sides=4, samples=2, cap="round", cap_steps=1))
    ed.append(g.tube([np.array(hpt(HEAD.pt(0.985, th, gr[-1] + 0.001))) for th in np.linspace(-152, -28, 9)], 0.0047, sides=4, samples=1, cap="round", cap_steps=1))
    ed.append(g.tube([np.array(hpt(HEAD.pt(0.04, th, gr[0] + 0.001))) for th in np.linspace(-152, -28, 9)], 0.0047, sides=4, samples=1, cap="round", cap_steps=1))
    p.add("m_chanfron_edges", merge(ed), "EH_Bronze", "mount_head", lod1=None)
    rv_pos, rv_n = [], []
    for u in (0.30, 0.50, 0.70, 0.86):
        for th in (-128, -52):
            q = HEAD.pt(u, th, 0.0085)
            rv_pos.append(hpt(q))
            rv_n.append(hpt(HEAD.pt(u, th, 0.1)) - hpt(HEAD.at(u)[0]))
    p.add("m_chanfron_rivets", g.instances(g.dome(0.0058, 0.0042, 6, 1), rv_pos, rv_n), "EH_Steel", "mount_head", lod1=None)
    # eye rondels (bronze) + ember eyes
    ey, rd = [], []
    for s in (-1, 1):
        c = np.array([s * 0.0545, 0.010, 0.088])
        rd.append(g.torus(0.0235, 0.0058, 14, 4).rotated(0, 0, 90).rotated(0, s * 14, 0).translated(*c))
        rd.append(g.lathe(np.array([(0.0, 0.0), (0.019, 0.0), (0.0225, 0.005), (0.0, 0.0085)]), 12, crease=45).rotated(0, 0, -90 * s).rotated(0, s * 14, 0).translated(*(c + [s * 0.0, 0, 0])))
        ey.append(g.superellipsoid((0.0085, 0.0125, 0.0125), 0.7, 0.7, 3, 7).translated(s * 0.0545, 0.0095, 0.090))
    p.add("m_eye_rondels", to_head(merge(rd)), "EH_Bronze", "mount_head")
    p.add("m_eyes", to_head(merge(ey)), "EH_Flame", "mount_head", bake=False, lod1="keep")
    # bridle: noseband, cheek straps, browband, bit rings; reins to the rider's left hand
    nb = [hpt(HEAD.pt(0.74, th, 0.016)) for th in np.linspace(0, 360, 14, endpoint=False)]
    p.add("m_noseband", g.tube(nb, 0.0050, sides=4, samples=1, cap=None, closed=True, smooth=True), "EH_Leather", "mount_head", uv_scale=2, lod1=None)
    for s in (-1, 1):
        cs = [hpt(np.array([s * 0.048, -0.030, 0.255])), hpt(np.array([s * 0.056, -0.008, 0.150])), hpt(np.array([s * 0.0565, 0.028, 0.095])), hpt(np.array([s * 0.050, 0.044, 0.030]))]
        p.add(f"m_cheekstrap_{'L' if s > 0 else 'R'}", g.tube(cs, 0.0042, sides=4, samples=3, cap="round", cap_steps=1), "EH_Leather", "mount_head", uv_scale=2, lod1=None)
        ring = g.torus(0.0100, 0.0030, 10, 4).rotated(0, 0, 90).translated(*hpt(np.array([s * 0.047, -0.027, 0.262])))
        p.add(f"m_bit_{'L' if s > 0 else 'R'}", ring, "EH_Steel", "mount_head", lod1=None)
    bb = [hpt(np.array([x, 0.040 - 0.000, 0.012])) for x in np.linspace(-0.056, 0.056, 7)]
    p.add("m_browband", g.tube(bb, 0.0050, sides=4, samples=2, cap="round", cap_steps=1), "EH_Leather", "mount_head", uv_scale=2, lod1=None)
    bit = hpt(np.array([0.047, -0.027, 0.262]))
    wr = np.array(JR["wrist_L"])
    reins = g.tube([bit, bit + (wr - bit) * 0.35 + [0.012, -0.015, 0.0], bit + (wr - bit) * 0.72 + [0.008, -0.018, 0], wr + [0.0, 0.005, 0.0]], 0.0036, sides=4, samples=3, cap="round", cap_steps=1)
    p.add("m_reins", reins, "EH_Leather", None, skin=Skin.nearest([("mount_head", bit, bit + [0, 0, 0.01]), ("wrist_L", wr, wr + [0, 0, 0.01])], tau=0.09), uv_scale=2, lod1=None)
    # ears: bronze covers over short upright ears (tips y 1.30, tilted 8 deg forward)
    for s, n in ((1, "L"), (-1, "R")):
        base = np.array([s * 0.034, 1.190, 0.318])
        tip = np.array([s * 0.030, 1.300, 0.345])
        mid = (base + tip) / 2 + [s * 0.006, 0.0, -0.004]
        ear = Stn([base, mid, tip], [0.019, 0.017, 0.0035], [0.0105, 0.0095, 0.002], e=2.2, samples=3, up=(1, 0, 0)).mesh(K=10, cap0=True, cap1=True)
        p.add(f"m_ear_{n}", ear, COAT_MAT, "mount_head", uv_scale=2, tint=COAT)
        st = Stn([base + [0, -0.005, 0.0045], mid + [0, -0.004, 0.0075], tip + [0, -0.012, 0.004]], [0.0185, 0.0165, 0.0030], [0.0105, 0.0095, 0.002], e=2.2, samples=3, up=(1, 0, 0))
        cov = st.shell([0.0, 0.4, 0.75, 0.97], 110, 250, nth=7, grow=0.0045, crease=40)
        p.add(f"m_earcover_{n}", cov, "EH_Bronze", "mount_head")
        p.add(f"m_earrim_{n}", g.torus(0.0215, 0.0048, 12, 4).scaled(0.85, 1.0, 0.7).translated(*(base + [0, -0.004, 0.003])), "EH_Bronze", "mount_head", lod1=None)


def mane(p: Piece):
    rng = np.random.default_rng(31)
    crest = [NECK.pt(u, 270, -0.004) for u in np.linspace(0.05, 1.0, 14)]
    fskin = Fringe(NECK_SKIN, np.array(crest))
    fur, emb = [], []
    n = 18
    for i in range(n):
        u = 0.985 - 0.90 * i / (n - 1)
        sgn = 1 if i % 2 else -1
        base = NECK.pt(u, 270, -0.004)
        L = (0.090 + 0.100 * smoothstep(0.1, 1.0, u)) * (0.85 + 0.3 * rng.random())          # longest at the poll (tip y ~1.29)
        d = unit(V(sgn * (0.28 + 0.14 * rng.random()), 0.62, -0.68))
        wob = 0.010 * (1 + rng.random())
        p1 = base + d * L * 0.30 + V(sgn * 0.006, 0.014, 0.0)
        p2 = base + d * L * 0.60 + V(-sgn * wob, 0.002, -0.014)
        p2b = base + d * L * 0.78 + V(sgn * wob * 0.8, -0.006, -0.026)
        p3 = base + d * L * 1.0 + V(-sgn * wob * 0.6, -0.022, -0.046)
        rad = 0.016 - 0.002 * (1 - u)
        fur.append(g.tube([base - [0, 0.006, 0], p1, p2, p2b], [rad, rad * 0.82, rad * 0.55, rad * 0.38], sides=6, samples=2, cap="round", cap_steps=1, smooth=True, up=(1, 0, 0), ellipse=(0.75, 1.35)))
        emb.append(g.tube([p2b, p3], [rad * 0.38, 0.0022], sides=5, samples=2, cap="round", cap_steps=1, smooth=True, up=(1, 0, 0), ellipse=(0.75, 1.35)))
    p.add("m_mane", merge(fur).noised(0.0016, 26, 2, seed=32), "EH_Fur", None, skin=fskin, uv_scale=2, tint=lambda P: np.full(len(P), 1.0))
    p.add("m_mane_ember", merge(emb), "EH_Flame", None, skin=fskin, bake=False, lod1="keep")
    back = []
    for i in range(5):
        z = 0.085 - i * 0.045
        base = np.array([0, 0.792 - 0.014 * i, z])
        Ln = 0.065 + 0.03 * rng.random()
        back.append(g.tube([base, base + [0.006 * (-1) ** i, Ln * 0.6, -Ln * 0.3], base + [0.0, Ln, -Ln * 0.8]], [0.011, 0.008, 0.002], sides=5, samples=1, cap="round", cap_steps=1, smooth=True, up=(1, 0, 0)))
    p.add("m_back_embers", merge(back), "EH_Flame", None, skin=BARREL_SKIN, bake=False, lod1=None)


# ======================================================================================= barding, caparison, saddle
ANVIL = np.array([(-.026, -.010), (.026, -.010), (.020, .002), (.010, .004), (.010, .014), (-.026, .016), (-.034, .010)])


def barding(p: Piece):
    # ---- peytral: four overlapping bronze bands hugging the chest, each proud of the one behind, lames hanging
    zr = [(0.075, 0.145), (0.115, 0.190), (0.155, 0.232), (0.195, 0.272)]
    for k, (z0, z1) in enumerate(zr):
        us = [barrel_u(z0), barrel_u((z0 + z1) / 2), barrel_u(z1)]
        gr = [0.012 + 0.0035 * k, 0.017 + 0.0035 * k, 0.011 + 0.0035 * k]
        sh = BARREL.shell(us, -32, 212, nth=17, grow=gr, crease=40)
        p.add(f"m_peytral_{k}", sh.noised(0.0010, 30, 2, seed=40 + k), "EH_Bronze", "mount_chest")
        lip = g.tube([BARREL.pt(us[-1], th, gr[-1] + 0.0015) for th in np.linspace(-32, 212, 14)], 0.0050, sides=4, samples=1, cap="round", cap_steps=1, smooth=True)
        p.add(f"m_peytral_lip_{k}", lip, "EH_Bronze", "mount_chest", lod1=None)
    boss = g.lathe(np.array([(0, 0), (0.030, 0), (0.033, 0.005), (0.026, 0.014), (0, 0.016)]), 18, crease=45).rotated(90, 0, 0).translated(0, 0.598, 0.287)
    anv = g.extrude(ANVIL * 0.62, 0.005, 0.0, 1).translated(0, 0.598, 0.304)
    p.add("m_peytral_boss", merge([boss, anv]), "EH_Steel", "mount_chest", lod1=None)
    rv = [barrel_z(z, th, 0.0245) for z in (0.17,) for th in (60, 120)] + [barrel_z(0.21, th, 0.0245) for th in (70, 110)]
    p.add("m_peytral_rivets", g.instances(g.dome(0.0070, 0.005, 6, 1), rv, [barrel_z(0.2, 90, 1) - barrel_z(0.2, 90, 0)] * len(rv)), "EH_Bronze", "mount_chest", lod1=None)
    # ---- flanchard: four overlapping plates per side
    for s, n in ((1, "L"), (-1, "R")):
        pls = []
        for k in range(4):
            z = 0.040 - k * 0.092
            c = barrel_z(z, 22 if s > 0 else 158, 0.020)
            pl = g.plate(0.108, 0.150, 0.012, 0.006, bend_r=0.16, inner_x=1, drop_back=True)
            pls.append(pl.rotated(0, 90 * s, 0).rotated(0, 0, -s * 10).translated(*c))
        p.add(f"m_flank_{n}", merge(pls), "EH_Bronze", "mount_body")
        rim = g.tube([barrel_z(z, 62 if s > 0 else 118, 0.016) for z in (0.07, 0.0, -0.1, -0.2, -0.27)], 0.0065, sides=5, samples=2, cap="round", cap_steps=1)
        p.add(f"m_flank_rim_{n}", rim, "EH_Bronze", "mount_body", lod1=None)
        ps = [barrel_z(z, 22 if s > 0 else 158, 0.030) + [s * 0.002, 0.0, 0.0] for z in (0.025, -0.065, -0.155, -0.245)]
        p.add(f"m_flank_rivets_{n}", g.instances(g.dome(0.0072, 0.005, 6, 1), ps, [(s, 0.05, 0)] * 4), "EH_Bronze", "mount_body", lod1=None)
    # ---- crupper: three overlapping plates over the rump with small spikes
    for k, (z0, z1) in enumerate(((-0.205, -0.255), (-0.240, -0.290), (-0.272, -0.322))):
        us = [barrel_u(z0), barrel_u((z0 + z1) / 2), barrel_u(z1)]
        gr = [0.011 + 0.003 * k, 0.015 + 0.003 * k, 0.010 + 0.003 * k]
        sh = BARREL.shell(us, 205, 335, nth=13, grow=gr, crease=40)
        p.add(f"m_crupper_{k}", sh.noised(0.0010, 30, 2, seed=50 + k), "EH_Bronze", "body")
    sp = [barrel_z(z, 270, 0.020) for z in (-0.235, -0.275, -0.315)]
    p.add("m_crupper_spikes", g.instances(g.cone(0.011, 0.040, 6), sp, [(0, 1, -0.55)] * 3), "EH_Bronze", "body", lod1=None)
    # ---- caparison: oxblood cloth over the back and flanks, scalloped bronze-trimmed hem
    zs = np.linspace(0.07, -0.255, 11)
    th0 = 146 - 11 * np.sin(zs * 58 + 0.6)
    th1 = 394 + 11 * np.sin(zs * 58 + 0.6)
    us = [barrel_u(z) for z in zs]
    cap = BARREL.shell(us, th0, th1, nth=23, grow=0.011, crease=60)
    p.add("m_caparison", cap.noised(0.0028, 14, 2, seed=11), "EH_Cloth", None, skin=BARREL_SKIN, uv_scale=2,
          tint=lambda P: (0.50 + 0.50 * smoothstep(0.50, 0.78, P[:, 1]))[:, None] * np.array([1.1, 0.98, 0.88]))
    for s, th_arr, n in ((1, th1, "L"), (-1, th0, "R")):
        tr = g.tube([BARREL.pt(u, th, 0.015) for u, th in zip(us, th_arr)], 0.0058, sides=4, samples=2, cap="round", cap_steps=1, smooth=True)
        p.add(f"m_cap_trim_{n}", tr, "EH_Bronze", None, skin=BARREL_SKIN, lod1=None)
    tas = g.tube([(0, 0, 0), (0, -0.018, 0), (0, -0.036, 0)], [0.0080, 0.0070, 0.0], sides=5, samples=1, cap=None, smooth=False)
    tp = [BARREL.pt(u, th, 0.015) for th_arr in (th1, th0) for u, th in zip(us[::1], th_arr)]
    p.add("m_cap_tassels", g.instances(tas, tp, [(0, -1, 0)] * len(tp), 1.0), "EH_Bronze", None, skin=BARREL_SKIN, lod1=None)
    # ---- saddle with cantle, pommel, stitching; girth, stirrup straps, stirrups
    sad = g.superellipsoid((0.100, 0.024, 0.120), 0.55, 0.6, 5, 12).translated(0, 0.806, -0.060)
    cant = g.superellipsoid((0.092, 0.038, 0.016), 0.5, 0.6, 4, 10).translated(0, 0.826, -0.178)
    pom = g.superellipsoid((0.032, 0.034, 0.022), 0.55, 0.6, 4, 10).translated(0, 0.828, 0.050)
    p.add("m_saddle", merge([sad, cant, pom]), "EH_Leather", "mount_body", uv_scale=2)
    st = [g.tube([(s * 0.098 * math.cos(t), 0.826, -0.060 + 0.113 * math.sin(t)) for t in np.linspace(-1.2, 1.2, 8)], 0.0030, sides=4, samples=1, cap="round", cap_steps=1) for s in (-1, 1)]
    p.add("m_saddle_stitch", merge(st), "EH_Bronze", "mount_body", lod1=None)
    girth = g.tube([barrel_z(0.015, th, 0.019) for th in np.linspace(0, 360, 16, endpoint=False)], 0.0085, sides=4, samples=1, cap=None, closed=True, smooth=True)
    p.add("m_girth", girth, "EH_Leather", "mount_body", uv_scale=2, lod1=None)
    for s, n in ((1, "L"), (-1, "R")):
        strap = g.tube([(s * 0.150, 0.790, -0.040), (s * 0.188, 0.690, -0.010), (s * 0.204, 0.560, 0.012)], 0.0085, sides=5, samples=2, cap="round", cap_steps=1, ellipse=(1.0, 0.45), up=(0, 0, 1))
        p.add(f"m_stirrup_strap_{n}", strap, "EH_Leather", "mount_body", uv_scale=2)
        ring = g.torus(0.027, 0.0046, 14, 4).rotated(0, 0, 90).translated(s * 0.204, 0.512, 0.020)
        p.add(f"m_stirrup_{n}", ring, "EH_Steel", "mount_body", lod1=None)
    # breast-collar tufts
    tuft = g.tube([(0, 0, 0), (0.002, -0.020, 0.004), (0.004, -0.040, 0.012)], [0.015, 0.010, 0.0], sides=4, samples=1, cap=None, smooth=False, up=(0, 0, 1))
    rng = np.random.default_rng(78)
    pos = [(rng.normal(0, 0.05), 0.505 - 0.02 * rng.random(), 0.205 + 0.04 * rng.random()) for _ in range(8)]
    p.add("m_chest_tufts", g.instances(tuft, pos, [(rng.normal(0, 0.2), -1, 0.4) for _ in range(8)], 1.2, spins=rng.random(8) * 360), COAT_MAT, "mount_chest", uv_scale=2, tint=COAT, lod1=None)


# ======================================================================================= the rider (crouched, secondary)
RJ = {k: np.array(v, float) for k, v in JR.items()}
for k_ in list(RJ):
    if k_.endswith("_L") and k_[:-1] + "R" not in RJ:
        RJ[k_[:-1] + "R"] = V(-RJ[k_][0], RJ[k_][1], RJ[k_][2])
LEG_SKIN = {s: Skin.chain([f"thigh_{s}", f"shin_{s}", f"foot_{s}"], pre="rider_pelvis", tip=tuple(RJ[f"toe_{s}"]), zone=0.40) for s in "LR"}
ARM_SKIN = {s: Skin.chain([f"arm_{s}", f"hand_{s}"], pre=f"clavicle_{s}", tip=tuple(RJ[f"wrist_{s}"]), zone=0.42) for s in "LR"}
RT_SKIN = Skin.chain(["rider_pelvis", "spine", "chest"], tip=tuple(RJ["neck"]), zone=0.45)
TORSO = Stn([(0, .825, -.112), (0, .875, -.085), (0, .935, -.045), (0, .990, .008)], [.094, .100, .116, .122], [.074, .076, .082, .072], e=2.4, samples=4)


def lerp3(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


def rider(p: Piece):
    for s, nm in ((1, "L"), (-1, "R")):
        hip, knee, ank, toe = (RJ[f"{k}_{nm}"] for k in ("hip", "knee", "ankle", "toe"))
        hose = limb_tube([hip + [0, 0.02, 0], lerp3(hip, knee, 0.5) + [0, 0, 0.004], knee, lerp3(knee, ank, 0.5), ank + [0, 0.01, 0]], [0.050, 0.046, 0.040, 0.035, 0.031],
                         joints=[knee], spacing=0.05, joint_spacing=0.024, joint_zone=0.05, sides=8, cap=None, up=(0, 0, 1))
        p.add(f"r_hose_{nm}", hose, "EH_Cloth", None, skin=LEG_SKIN[nm], uv_scale=2, tint=lambda P: np.full(len(P), 0.7))
        boot = g.superellipsoid((0.040, 0.040, 0.072), 0.55, 0.62, 4, 9).rotated(10, 0, 0).translated(s * 0.200, 0.516, 0.038)
        shaft = g.tube([(s * 0.200, 0.600, 0.020), (s * 0.200, 0.530, 0.015)], [0.036, 0.040], sides=9, samples=1, cap=None, smooth=False)
        p.add(f"r_boot_{nm}", merge([boot, shaft]), "EH_Leather", f"foot_{nm}", uv_scale=2)
        g0, g1 = lerp3(knee, ank, 0.88) + [0, 0, 0.008], lerp3(knee, ank, 0.22) + [0, 0, 0.008]
        greave = g.tube([g0, (g0 + g1) / 2, g1], [0.040, 0.043, 0.047], sides=9, samples=2, cap=None, up=(0, 0, 1)).noised(0.0014, 34, 2, seed=40 + s)
        p.add(f"r_greave_{nm}", greave, "EH_Bronze", f"shin_{nm}")
        cop = g.superellipsoid((0.040, 0.036, 0.034), 0.65, 0.65, 4, 9).translated(*(knee + [s * 0.004, 0.0, 0.036]))
        fin = g.extrude_plane(np.array([(0.725, 0.060), (0.725, 0.108), (0.770, 0.098), (0.775, 0.066)]), 0.008, "YZ", bevel=0.003, bevel_segments=1).translated(s * 0.236, 0, 0)
        p.add(f"r_kneecop_{nm}", merge([cop, fin]), "EH_Bronze", f"shin_{nm}")
    # torso: gambeson, cuirass, backplate, belt, waist lames
    p.add("r_torso", TORSO.mesh(K=14, cap0=True, cap1=True).noised(0.0012, 20, 2, seed=3), "EH_Cloth", None, skin=RT_SKIN, uv_scale=2)
    cu = TORSO.shell([0.12, 0.30, 0.50, 0.70, 0.90], -8, 188, nth=15, grow=[0.008, 0.013, 0.015, 0.014, 0.008], crease=45)
    p.add("r_cuirass", cu.dented(3, 0.026, 0.003, seed=44), "EH_Bronze", "chest")
    p.add("r_cuirass_ridge", g.tube([TORSO.pt(u, 90, gg + 0.002) for u, gg in zip(np.linspace(0.14, 0.92, 5), (0.012, 0.018, 0.020, 0.018, 0.012))], 0.0065, sides=5, samples=2, cap="round", cap_steps=1), "EH_Bronze", "chest", lod1=None)
    for th, nm in ((-8, "R"), (188, "L")):
        p.add(f"r_cuirass_edge_{nm}", TORSO.edge(np.linspace(0.14, 0.9, 5), th, 0.014, 0.0045, 4), "EH_Bronze", "chest", lod1=None)
    bk = TORSO.shell([0.15, 0.40, 0.65, 0.92], 200, 340, nth=11, grow=[0.008, 0.012, 0.012, 0.008], crease=45)
    p.add("r_backplate", bk, "EH_Bronze", "chest")
    belt = TORSO.shell([0.02, 0.07, 0.13], 0, 360 - 360 / 14, nth=14, grow=[0.006, 0.010, 0.006], crease=50)
    p.add("r_belt", g.loft(np.stack([TORSO.pt(u, np.linspace(0, 360, 14, endpoint=False), gg) for u, gg in zip([0.02, 0.05, 0.10, 0.13], [0.006, 0.012, 0.012, 0.006])]), closed=True, crease=50), "EH_Leather", "spine", uv_scale=2, lod1=None)
    for i, u in enumerate((0.22, 0.30)):
        lm = TORSO.shell([u - 0.04, u, u + 0.03], -10, 190, nth=13, grow=[0.011, 0.016, 0.012], crease=45)
        p.add(f"r_waist_lame_{i}", lm, "EH_Bronze", "spine", lod1=None if i else "auto")
    # fur mantle (heavy on the left) + collar
    K = 26
    th = np.linspace(0, TAU, K, endpoint=False)
    path = np.stack([0.112 * np.sin(th), 0.985 - 0.012 * np.abs(np.sin(th)) ** 1.5 + 0.040 * np.cos(th), 0.075 * np.cos(th) - 0.000 + 0.0], 1)
    ring_ = g.tube(path, 0.028, sides=7, samples=1, cap=None, closed=True, up=(0, 1, 0), smooth=False).noised(0.006, 18, 3, seed=45)
    flap = g.superellipsoid((0.060, 0.030, 0.065), 0.7, 0.8, 4, 10).noised(0.006, 14, 3, seed=46).translated(0.150, 0.970, -0.010)
    p.add("r_mantle", merge([ring_, flap]), "EH_Fur", "chest", uv_scale=2, tint=lambda P: np.full(len(P), 0.8))
    # pauldrons (large left / small right)
    p.add("r_pauldron_L", C.pauldron(+1, (0.168, 0.968, 0.0), 0.92, lames=3, seed=1, tilt_deg=16, flare=0.009), "EH_Bronze", "arm_L")
    p.add("r_pauldron_R", C.pauldron(-1, (-0.162, 0.964, 0.0), 0.74, lames=2, dent=True, seed=2, tilt_deg=16, flare=0.009), "EH_Bronze", "arm_R")
    # arms: continuous sleeve + vambrace + hands
    for s, nm in ((1, "L"), (-1, "R")):
        sh, el, wr = RJ[f"shoulder_{nm}"], RJ[f"elbow_{nm}"], RJ[f"wrist_{nm}"]
        fd = unit(wr - el)
        sleeve = limb_tube([sh + [0, -0.006, 0], lerp3(sh, el, 0.5), el, lerp3(el, wr - fd * 0.03, 0.5), wr - fd * 0.03], [0.036, 0.034, 0.030, 0.027, 0.024],
                           joints=[el], spacing=0.04, joint_spacing=0.02, joint_zone=0.045, sides=8, cap="round", cap_steps=1, up=(0, 1, 0))
        p.add(f"r_sleeve_{nm}", sleeve.noised(0.0012, 14, 2, seed=20 + s), "EH_Cloth", None, skin=ARM_SKIN[nm], uv_scale=2)
        v0, v1 = lerp3(el, wr, 0.15), lerp3(el, wr, 0.75)
        vam = g.tube([v0, (v0 + v1) / 2, v1], [0.031, 0.029, 0.027], sides=8, samples=2, cap="flat", up=(0, 1, 0))
        p.add(f"r_vambrace_{nm}", vam.noised(0.0012, 34, 2, seed=24 + s), "EH_Bronze", f"hand_{nm}")
        p.add(f"r_elbow_cop_{nm}", g.superellipsoid((0.030, 0.030, 0.030), 0.65, 0.65, 4, 8).translated(*(el + [s * 0.014, 0.0, -0.010])), "EH_Bronze", f"hand_{nm}", lod1=None)
    wl = RJ["wrist_L"]
    p.add("r_hand_L", merge([g.superellipsoid((0.026, 0.022, 0.032), 0.55, 0.6, 4, 9).translated(wl[0], wl[1] - 0.004, wl[2] + 0.014)]), "EH_Leather", "wrist_L", uv_scale=2)
    wr_ = RJ["wrist_R"]
    ld = unit(LANCE_T - LANCE_B)
    fing = [g.torus(0.0172, 0.0072, 10, 4).aimed(ld, wr_ + ld * dz) for dz in (-0.020, -0.004, 0.012)]
    back = g.superellipsoid((0.030, 0.026, 0.030), 0.5, 0.6, 4, 9).translated(*(wr_ + [0.0, 0.020, -0.004]))
    p.add("r_hand_R", merge(fing + [back]), "EH_Leather", "wrist_R", uv_scale=2)
    # head: face, low bronze helm with face slit + nasal bar + crest (top 1.10), cheek guards, gorget
    hc = np.array([0.0, 1.040, 0.062])
    skull = g.superellipsoid((0.043, 0.047, 0.047), 0.92, 0.95, 5, 11).translated(*hc)
    nose = g.superellipsoid((0.006, 0.012, 0.010), 0.6, 0.6, 3, 6).translated(hc[0], hc[1] - 0.006, hc[2] + 0.046)
    p.add("r_face", merge([skull, nose]), "EH_Skin", "head", uv_scale=2, tint=lambda P: np.full(len(P), 0.7))
    helm = g.lathe(g.spline(np.array([(0.053, 1.010), (0.057, 1.040), (0.052, 1.072), (0.032, 1.092), (0.0, 1.100)]), 3), 18, crease=55).translated(0, 0, hc[2] - 0.004).noised(0.0010, 40, 2, seed=52)
    p.add("r_helm", helm, "EH_Bronze", "head")
    visor = g.extrude(np.array([(-0.028, -0.006), (0.028, -0.006), (0.032, 0.006), (-0.032, 0.006)]), 0.012, 0.003, 1).translated(0, 1.043, hc[2] + 0.048)
    nasal = g.extrude(np.array([(-0.0060, 1.010), (0.0060, 1.010), (0.0050, 1.085), (-0.0050, 1.085)]), 0.006, 0.0015, 1).translated(0, 0, hc[2] + 0.050)
    p.add("r_visor", merge([visor, nasal]), "EH_Steel", "head")
    crest = g.extrude_plane(np.array([(1.075, -0.040), (1.098, -0.026), (1.100, 0.0), (1.092, 0.030), (1.070, 0.038)]), 0.012, "YZ", bevel=0.004, bevel_segments=1).translated(0, 0, hc[2])
    p.add("r_helm_crest", crest, "EH_Bronze", "head", lod1="keep")
    p.add("r_helm_band", g.torus(0.0545, 0.0045, 18, 4).translated(0, 1.050, hc[2] - 0.004), "EH_Bronze", "head", lod1=None)
    cheek = [g.extrude_plane(np.array([(1.008, hc[2] - 0.026), (1.006, hc[2] + 0.022), (1.030, hc[2] + 0.030), (1.048, hc[2] + 0.014), (1.044, hc[2] - 0.024)]) - [0, hc[2]] + [0, hc[2]], 0.006, "YZ", bevel=0.0015, bevel_segments=1).translated(s * 0.046, 0, 0) for s in (-1, 1)]
    p.add("r_cheek_guards", merge(cheek), "EH_Steel", "head", lod1=None)
    gor = g.lathe(np.array([(0.058, 0.972), (0.064, 0.980), (0.066, 1.000), (0.058, 1.016), (0.052, 1.014), (0.056, 0.998), (0.054, 0.980)]), 16, crease=45).translated(0, 0, 0.034)
    p.add("r_gorget", gor, "EH_Bronze", "chest", lod1=None)
    p.add("r_neck", g.tube([(0, 0.975, 0.020), (0, 1.015, 0.050)], [0.036, 0.034], sides=8, samples=1, cap=None, smooth=False), "EH_Skin", "neck", uv_scale=2)


def lance(p: Piece):
    base, tip = LANCE_B, LANCE_T
    mid = (base + tip) / 2
    ld = unit(tip - base)
    shaft = g.tube([base, mid, tip - ld * 0.06], [0.014, 0.0125, 0.0100], sides=8, samples=3, cap="round", cap_steps=1, up=(1, 0, 0))
    p.add("r_lance_shaft", shaft.noised(0.0010, 30, 2, seed=60), "EH_Leather", "weapon", uv_scale=2)
    rings = [g.torus(0.0165 - 0.002 * i, 0.0048, 10, 4).aimed(ld, base + (tip - base) * u) for i, u in enumerate((0.40, 0.62, 0.82))]
    rings.append(g.torus(0.0165, 0.0055, 10, 4).aimed(ld, base + ld * 0.04))
    p.add("r_lance_rings", merge(rings), "EH_Bronze", "weapon")
    head = g.blade(0.110, 0.040, 0.011, tip=0.45, taper=0.9, fuller=0.0015, rows=3).aimed(ld, tip - ld * 0.110 + ld * 0.004)
    collar = g.lathe(np.array([(0.0120, 0.0), (0.021, 0.006), (0.021, 0.022), (0.014, 0.030), (0.0100, 0.032)]), 10, crease=45).aimed(ld, tip - ld * 0.112)
    p.add("r_lance_head", head, "EH_Steel", "weapon", occluder=False)
    p.add("r_lance_collar", collar, "EH_Bronze", "weapon")
    pen = np.array([(0, 0.016), (-0.160, 0.050), (-0.122, 0.0), (-0.160, -0.050), (0, -0.016)])
    cloth = g.extrude(pen, 0.004, 0.0008, 1)
    cloth = g.warp(cloth, lambda P: np.column_stack([P[:, 0], P[:, 1], P[:, 2] + 0.010 * np.sin(P[:, 0] * 38) * np.abs(P[:, 0]) * 6]), 70)
    pos = base + (tip - base) * 0.86
    cloth = cloth.rotated(0, 90, 0).translated(*pos)
    p.add("r_pennon", cloth, "EH_Cloth", "weapon", uv_scale=2, lod1=None)


# ======================================================================================= animation (IK quadruped + rider)
from anim.curves import Sig                         # noqa: E402

FEET = {"hoof_hind_L": (("hind_upper_L", "hind_lower_L", "hind_hoof_L"), (0, 0, -1)), "hoof_hind_R": (("hind_upper_R", "hind_lower_R", "hind_hoof_R"), (0, 0, -1)),
        "hoof_fore_L": (("fore_upper_L", "fore_lower_L", "fore_hoof_L"), (0, 0, 1)), "hoof_fore_R": (("fore_upper_R", "fore_lower_R", "fore_hoof_R"), (0, 0, 1))}
A_L = unit(LANCE_T - LANCE_B)                       # lance axis (butt -> tip) at rest
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
    d0 = lambda t: unit(V(0, 0.07 + 0.035 * cs(U(t), 0.35), 1.0))        # noqa: E731
    hold_lance(a, dir_=Fn(d0), pos=Fn(lambda t: WR0 + V(0, 0.006 * cs(U(t), 0.35), 0)))
    return a, T, True, 30, ()


FOLD, TUCK, REACH = V(-0.01, 0.25, -0.035), V(-0.01, 0.20, 0.0), V(0.0, 0.06, 0.16)       # fore-fetlock targets in chest space (delta from rest)


def lance_dir(elev, yaw=0.0):
    e = math.radians(elev)
    return unit(V(math.sin(math.radians(yaw)), math.sin(e), math.cos(e)))


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
               dir_keys=[(0, A_L), (0.10, lance_dir(22), "out_cubic"), (0.45, lance_dir(14), "in_out_cubic")])
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
    a.rot("neck_1", Curve([(0, Z3), (0.40, V(0, 0, 0), "in_out_cubic"), (0.55, V(-2, 0, 0)), (0.76, V(3, 0, 0), "in_out_cubic"), (0.88, V(4, 0, 0)), (1.0, V(3, 0, 0)), (1.5, V(-3, 0, 0), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("neck_2", Curve([(0, Z3), (0.40, V(4, 0, 0), "in_out_cubic"), (0.55, V(4, 0, 0)), (0.76, V(4, 0, 0), "in_out_cubic"), (0.88, V(5, 0, 0)), (1.0, V(4, 0, 0)), (1.5, V(-2, 0, 0), "in_out_cubic"), (2.0, Z3, "in_out_cubic")]))
    a.rot("mount_head", Curve([(0, Z3), (0.40, V(4, 0, 0), "in_out_cubic"), (0.55, V(2, 0, 0), "out_cubic"), (0.76, V(-4, 0, 0), "in_out_cubic"), (0.88, V(2, 0, 0), "in_out_cubic"), (1.15, V(3, 0, 0)), (2.0, Z3, "in_out_cubic")]))
    a.rot("jaw", Curve([(0, Z3), (0.30, Z3), (0.45, V(14, 0, 0), "out_cubic"), (0.62, V(14, 0, 0)), (0.80, Z3, "in_out_cubic"), (2.0, Z3)]))
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
    hold_lance(a, pos_keys=[(0, WR0), (0.40, WR0 + V(0, 0.01, 0.0), "in_out_cubic"), (0.88, WR0 + V(0, -0.01, 0.03), "in_out_cubic"), (1.0, WR0 + V(0, -0.02, 0.05), "snap_in"), (1.15, WR0 + V(0, -0.02, 0.05)), (2.0, WR0, "in_out_cubic")],
               dir_keys=[(0, A_L), (0.40, lance_dir(4), "in_out_cubic"), (0.55, lance_dir(10)), (0.76, lance_dir(2), "in_out_cubic"), (0.88, lance_dir(8), "in_out_cubic"), (1.0, lance_dir(16), "snap_in"),
                         (1.15, lance_dir(16)), (1.6, lance_dir(12), "in_out_cubic"), (2.0, A_L, "in_out_cubic")])
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
               dir_keys=[(0, A_L), (0.3, lance_dir(20), "in_out_cubic"), (0.65, lance_dir(48), ("spring", 0.10, 1.5)), (T, lance_dir(52), "in_out_cubic")])
    return a, T, False, 30, ()


# ---------------------------------------------------------------------------------------------- Taunt: rear, two stamps, lance levelled at the enemy
def clip_taunt(rig):
    a = _anim(rig)
    T = 1.3
    a.pos("body", Curve([(0, Z3), (0.45, V(0, -0.060, -0.030), "in_out_cubic"), (0.58, V(0, -0.070, -0.034)), (0.74, V(0, -0.020, 0.0), "in_cubic"), (0.86, V(0, 0.010, 0.0), "out_cubic"),
                         (0.98, V(0, -0.022, 0.0), "in_cubic"), (1.10, Z3, "out_cubic"), (T, Z3)]))
    a.rot("body", Curve([(0, Z3), (0.45, V(-30, 0, 0), "in_out_cubic"), (0.58, V(-32, 0, 0)), (0.74, V(5, 0, 0), "in_cubic"), (0.86, V(-4, 0, 0), "out_cubic"), (0.98, V(4, 0, 0), "in_cubic"), (1.10, V(-1, 0, 0), "out_cubic"), (T, Z3, "in_out_cubic")]))
    a.rot("mount_head", Curve([(0, Z3), (0.45, V(-6, 0, 0), "in_out_cubic"), (0.58, V(-10, 0, 0)), (0.74, V(14, 0, 0), "in_cubic"), (0.98, V(10, 0, 0)), (1.2, V(-4, 0, 0), "out_cubic"), (T, Z3, "in_out_cubic")]))
    a.rot("neck_1", Curve([(0, Z3), (0.45, V(0, 0, 0), "in_out_cubic"), (0.74, V(8, 0, 0), "in_cubic"), (1.1, V(-2, 0, 0)), (T, Z3, "in_out_cubic")]))
    a.rot("neck_2", Curve([(0, Z3), (0.45, V(3, 0, 0), "in_out_cubic"), (0.74, V(8, 0, 0), "in_cubic"), (1.1, V(-2, 0, 0)), (T, Z3, "in_out_cubic")]))
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
               dir_keys=[(0, A_L), (0.45, lance_dir(8), "in_out_cubic"), (0.74, lance_dir(4)), (1.02, lance_dir(-4, 4), "in_out_cubic"), (1.2, lance_dir(-4, 4)), (T, A_L, "in_out_cubic")])
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
               dir_keys=[(0, A_L), (0.30, lance_dir(8), "in_out_cubic"), (0.9, lance_dir(-5), "in_out_cubic"), (T, lance_dir(-20), "in_out_cubic")])
    M.release_weapon(a, "weapon", 0.45, 0.22, 0.016, A_L, (0.0, 0.0, 1.0), land_xz=(-0.26, 0.04), up_local=None, roll_deg=90.0)
    return a, T, False, 30, ()


def fix_impact_socket(rig, a):
    """socket_impact (under mount_body) = where the lance tip is at impactTime."""
    c = a.pose(IMPACT)
    sk = a.sk
    iw, ib = sk.ix["weapon"], sk.ix["mount_body"]
    tip = c.Pw[iw] + c.Rw[iw] @ (LANCE_T - sk.rest[iw])
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
    p = Piece("emberhold", "knight", rig, clips, impact_time=1.00, strike_range=0.50, attack_style="leap", seed=13)
    C.pedestal_parts(p)
    horse_body(p)
    neck_and_crinet(p)
    head_parts(p)
    mane(p)
    barding(p)
    if "rider" in globals():
        rider(p)
        lance(p)
    log(f"  {ASSET_ID}: {len(p.parts)} parts, {p.tri_count()} LOD0 tris before baking")
    if os.environ.get("FORGE_DRY"):
        return p
    return p.build(log)


if __name__ == "__main__":
    glb, frag, stats = build()
    print(stats)
