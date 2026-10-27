"""skeleton.py - forward kinematics for a Rig (identity rest rotations) plus the 2-bone IK solver.

All bones have world-aligned rest frames, so a local rotation R_loc is also "the rotation applied in parent-frame axes".
    sk = Skeleton(rig)
    Rw, Pw = sk.fk(R_loc, T_loc)       # R_loc (n,3,3), T_loc (n,3) = translation DELTA from the rest local offset
"""
from __future__ import annotations

import math

import numpy as np

from .xf import frame, normalize


class Skeleton:
    def __init__(self, rig):
        self.rig = rig
        self.names = list(rig.order)
        self.n = len(self.names)
        self.ix = {n: i for i, n in enumerate(self.names)}
        for a, b in rig.alias.items() if hasattr(rig, "alias") else []:
            self.ix[a] = self.ix[b]
        self.parent = np.array([self.ix[rig.bones[n].parent] if rig.bones[n].parent else -1 for n in self.names])
        self.rest = np.array([rig.bones[n].pos for n in self.names])
        self.off = np.array([rig.local(n) for n in self.names])
        self.children = [[j for j in range(self.n) if self.parent[j] == i] for i in range(self.n)]

    def i(self, name):
        return self.ix[name]

    def identity(self):
        return np.tile(np.eye(3), (self.n, 1, 1)), np.zeros((self.n, 3))

    def fk(self, R_loc, T_loc):
        Rw = np.empty_like(R_loc)
        Pw = np.empty((self.n, 3))
        for i in range(self.n):
            p = self.parent[i]
            loc = self.off[i] + T_loc[i]
            if p < 0:
                Rw[i] = R_loc[i]
                Pw[i] = loc
            else:
                Rw[i] = Rw[p] @ R_loc[i]
                Pw[i] = Pw[p] + Rw[p] @ loc
        return Rw, Pw

    def chain_to_root(self, name):
        out, i = [], self.ix[name]
        while i >= 0:
            out.append(i)
            i = self.parent[i]
        return out[::-1]


def two_bone_ik(sk, R_loc, Rw, Pw, upper, lower, end, target, pole_rest, pole_world_fn=None, twist_deg=0.0, soft=0.002, stretch=1.0,
                pole_target=None, pole_mix=0.0):
    """Solve a 2-bone chain upper -> lower -> end so that `end`'s joint reaches `target` (world).  Modifies R_loc[upper],
    R_loc[lower] and returns the clamped end position actually reached.

    Rest geometry (lengths, rest bend plane) comes from the skeleton, so a target equal to the rest end position yields
    the identity (rest) pose.  `pole_rest`: fallback bend direction in the PARENT frame (e.g. +Z for knees) used when the
    rest chain is straight; `pole_world_fn(parent_R)` maps it to world.  twist_deg rotates the bend plane about the
    hip->target axis (knee turn-out)."""
    iu, il, ie = sk.ix[upper], sk.ix[lower], sk.ix[end]
    H0, K0, E0 = sk.rest[iu], sk.rest[il], sk.rest[ie]
    l1, l2 = np.linalg.norm(K0 - H0), np.linalg.norm(E0 - K0)
    # rest bend plane (in the rest/parent frame): direction of the knee off the hip->end line
    dr = normalize(E0 - H0)
    kr = (K0 - H0) - np.dot(K0 - H0, dr) * dr
    if np.linalg.norm(kr) > 1.5e-3:
        pole_r = normalize(kr)
    else:
        pr = np.asarray(pole_rest, dtype=np.float64)
        pole_r = normalize(pr - np.dot(pr, dr) * dr)
    pidx = sk.parent[iu]
    Rp = Rw[pidx] if pidx >= 0 else np.eye(3)
    H = Pw[iu]
    d = np.asarray(target, dtype=np.float64) - H
    dist = np.linalg.norm(d)
    reach = (l1 + l2) * stretch
    lo = abs(l1 - l2) + 1e-4
    dist_c = min(max(dist, lo), reach * (1 - soft))
    dh = d / max(dist, 1e-9)
    # world bend direction = (rest pole, optionally blended toward `pole_target` given in the parent frame) carried by the parent's rotation
    pole_use = pole_r
    if pole_target is not None and pole_mix > 1e-4:
        pt = np.asarray(pole_target, dtype=np.float64)
        pt = pt - np.dot(pt, dr) * dr
        if np.linalg.norm(pt) > 1e-6:
            mixed = pole_r * (1 - pole_mix) + normalize(pt) * pole_mix
            mixed = mixed - np.dot(mixed, dr) * dr
            if np.linalg.norm(mixed) > 1e-6:
                pole_use = normalize(mixed)
    pole_w = Rp @ pole_use
    if twist_deg:
        c, s = math.cos(math.radians(twist_deg)), math.sin(math.radians(twist_deg))
        pole_w = pole_w * c + np.cross(dh, pole_w) * s + dh * np.dot(dh, pole_w) * (1 - c)
    pole_w = pole_w - np.dot(pole_w, dh) * dh
    if np.linalg.norm(pole_w) < 1e-6:
        pole_w = Rp @ np.asarray(pole_rest, dtype=np.float64)
        pole_w = pole_w - np.dot(pole_w, dh) * dh
    pole_w = normalize(pole_w)
    a = (l1 * l1 - l2 * l2 + dist_c * dist_c) / (2 * dist_c)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    K = H + dh * a + pole_w * h
    E = H + dh * dist_c
    # frames: axis + bend-plane normal (constant for both bones)
    n_w = np.cross(dh, pole_w)
    n_r = np.cross(dr, pole_r)
    Fr_u = frame(normalize(K0 - H0), n_r)
    Fr_l = frame(normalize(E0 - K0), n_r)
    Fn_u = frame(normalize(K - H), n_w)
    Fn_l = frame(normalize(E - K), n_w)
    Ru_w = Fn_u @ Fr_u.T
    Rl_w = Fn_l @ Fr_l.T
    R_loc[iu] = Rp.T @ Ru_w
    R_loc[il] = Ru_w.T @ Rl_w
    return E
