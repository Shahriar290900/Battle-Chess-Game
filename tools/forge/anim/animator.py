"""animator.py - bakes a layered, IK-driven procedural animation into dense, key-reduced rig.Clip tracks.

    a = Animator(rig)
    a.rot("spine", [(0, (0,0,0)), (0.5, (12,0,0)), (1.0, (0,0,0))])        # Euler-degree curve (list of keys or any Sig)
    a.pos("body", Curve(...))                                               # metres, delta from rest
    a.goal("foot_L", ("thigh_L","shin_L","foot_L"), pos=Curve(...), rot=Curve(...))   # world-space (plinth) 2-bone IK
    a.goal("hand_R", ("arm_R","hand_R","wrist_R"), spaces=[("chest", 1.0)], pos=..., rot=...)
    a.keep_legs_reachable(["foot_L", "foot_R"])        # lowers the pelvis so planted feet never over-extend (no leg pop)
    a.secondary(["cape_1","cape_2","cape_3"], driver="top", freq=2.2, zeta=0.35)     # spring follow-through / overlap
    clip = a.bake("Move", 0.8, loop=True, fps=30)       # -> rig.Clip with dense LINEAR quaternion/translation tracks

Order of evaluation per frame: FK curves -> pre-hooks -> pelvis reach clamp -> IK goals (in the order added) ->
world overrides (dropped weapon) -> [after sampling] secondary springs -> foot contacts -> key reduction.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .curves import Curve, Const, Sig, spring_follow
from .skeleton import Skeleton, two_bone_ik
from .xf import euler, from_rotvec, mat_from_quat, quat_from_mat, rotvec, slerp


def _as_sig(v, dim=3):
    if v is None:
        return None
    if isinstance(v, Sig):
        return v
    if callable(v):
        return v
    if isinstance(v, (list, tuple)) and v and isinstance(v[0], (list, tuple)) and len(v[0]) >= 2 and np.ndim(v[0][0]) == 0 and np.ndim(v[0][1]) in (0, 1) and isinstance(v[0][1], (list, tuple, np.ndarray)):
        return Curve(v)
    return Const(v)


@dataclass
class Goal:
    name: str
    upper: str
    lower: str
    end: str
    pos: object = None                 # Sig t -> delta metres in `spaces`
    rot: object = None                 # Sig t -> Euler degrees of the end bone in `spaces` (None: leave the end bone's FK rotation)
    spaces: tuple = (("world", 1.0),)  # ((bone | "world", weight Sig/float), ...)
    weight: object = 1.0               # IK/FK blend
    pole: tuple = (0.0, 0.0, 1.0)      # fallback bend direction in the parent frame
    twist: object = 0.0                # bend-plane twist (deg) about the root->target axis
    stretch: float = 1.0
    pole_target: object = None         # bend direction in the parent frame the elbow/knee is steered toward ...
    pole_mix: object = 0.0             # ... by this 0..1 amount (Sig or float): 0 keeps the rest bend direction


@dataclass
class Secondary:
    chain: list
    driver: str
    freq: float = 2.5
    zeta: float = 0.4
    follow: float = 0.8
    accel: float = 0.0                 # gain of the linear-acceleration pendulum drive (cape/bedroll/tail)
    hang: float = 1.0                  # +1 for things hanging down from the attach point, -1 for things sticking up
    max_deg: float = 25.0
    decay: float = 0.8                 # freq multiplier per chain link
    axes: tuple = (1.0, 0.0, 1.0)      # which rotation axes respond (x pitch, y yaw, z roll); y off by default
    follow_decay: float = 1.0


@dataclass
class Override:
    bone: str
    fn: object                          # fn(t) -> None | (R_world 3x3, P_world 3)


class Ctx:
    def __init__(self, sk):
        self.sk = sk
        self.R, self.T = sk.identity()
        self.Rw = self.Pw = None

    def fk(self):
        self.Rw, self.Pw = self.sk.fk(self.R, self.T)
        return self

    def world(self, bone):
        i = self.sk.ix[bone]
        return self.Rw[i], self.Pw[i]


@dataclass
class Sampled:
    times: np.ndarray
    R: np.ndarray          # (f, n, 3, 3) local rotations
    T: np.ndarray          # (f, n, 3) local translation deltas
    Rw: np.ndarray
    Pw: np.ndarray
    contacts: dict = field(default_factory=dict)


class Animator:
    def __init__(self, rig):
        self.rig = rig
        self.sk = Skeleton(rig)
        self._rot: dict = {}
        self._pos: dict = {}
        self.goals: list[Goal] = []
        self.pre_hooks: list = []
        self.overrides: list[Override] = []
        self.secondaries: list[Secondary] = []
        self._reach_goals: list[str] = []
        self.reach_margin = 0.012          # keep this fraction of the leg length as minimum knee bend
        self.contact_goals: list[str] = []

    # ------------------------------------------------------------------ authoring
    def rot(self, bone, sig):
        """Add (sum) an Euler-degree layer on `bone`.  `sig`: list of Curve keys or any Sig / constant."""
        s = _as_sig(sig)
        b = self.rig.resolve(bone)
        self._rot[b] = s if b not in self._rot else self._rot[b] + s
        return s

    def pos(self, bone, sig):
        s = _as_sig(sig)
        b = self.rig.resolve(bone)
        self._pos[b] = s if b not in self._pos else self._pos[b] + s
        return s

    def goal(self, name, chain, pos=None, rot=None, spaces=(("world", 1.0),), weight=1.0, pole=(0, 0, 1), twist=0.0, stretch=1.0, contact=False,
             pole_target=None, pole_mix=0.0):
        up, lo, en = (self.rig.resolve(c) for c in chain)
        g = Goal(name, up, lo, en, _as_sig(pos), _as_sig(rot), tuple((self.rig.resolve(s) if s != "world" else s, w) for s, w in spaces),
                 weight, pole, twist, stretch, pole_target, pole_mix)
        self.goals.append(g)
        if contact:
            self.contact_goals.append(name)
        return g

    def keep_legs_reachable(self, goal_names, margin=None):
        self._reach_goals = list(goal_names)
        if margin is not None:
            self.reach_margin = margin

    def hook(self, fn):
        """fn(t, ctx): runs after the FK curves, before IK.  Mutate ctx.R / ctx.T then call ctx.fk()."""
        self.pre_hooks.append(fn)
        return fn

    def secondary(self, chain, driver, **kw):
        s = Secondary([self.rig.resolve(c) for c in chain], self.rig.resolve(driver), **kw)
        self.secondaries.append(s)
        return s

    def override(self, bone, fn):
        self.overrides.append(Override(self.rig.resolve(bone), fn))

    # ------------------------------------------------------------------ per-frame solve
    @staticmethod
    def _w(v, t):
        if callable(v):
            return float(np.asarray(v(t)).ravel()[0])
        return float(v)

    def _target(self, g: Goal, t, ctx: Ctx):
        sk = self.sk
        ie = sk.ix[g.end]
        delta = np.zeros(3) if g.pos is None else np.asarray(g.pos(t), dtype=np.float64)[:3]
        rot_e = None if g.rot is None else np.asarray(g.rot(t), dtype=np.float64)
        if rot_e is not None and rot_e.shape != (3, 3):
            rot_e = euler(rot_e.ravel()[:3])
        P = np.zeros(3)
        Qs = []
        tot = 0.0
        for space, w in g.spaces:
            w = self._w(w, t)
            if w <= 1e-6:
                continue
            if space == "world":
                Rs, Ps, O = np.eye(3), np.zeros(3), np.zeros(3)
            else:
                i = sk.ix[space]
                Rs, Ps, O = ctx.Rw[i], ctx.Pw[i], sk.rest[i]
            P += w * (Ps + Rs @ (sk.rest[ie] - O + delta))
            if rot_e is not None:
                Qs.append((w, quat_from_mat(Rs @ rot_e)))
            tot += w
        if tot <= 1e-9:
            return None, None
        P /= tot
        R = None
        if Qs:
            q0 = Qs[0][1]
            acc = np.zeros(4)
            for w, q in Qs:
                acc += w * (q if np.dot(q, q0) >= 0 else -q)
            R = mat_from_quat(acc / np.linalg.norm(acc))
        return P, R

    def _reach(self, t, ctx):
        if not self._reach_goals:
            return
        sk = self.sk
        dy = 0.0
        for gname in self._reach_goals:
            g = next(x for x in self.goals if x.name == gname)
            if self._w(g.weight, t) < 0.5 or any(s != "world" for s, _ in g.spaces):
                continue
            tgt, _ = self._target(g, t, ctx)
            if tgt is None:
                continue
            H = ctx.Pw[sk.ix[g.upper]]
            l1 = np.linalg.norm(sk.rest[sk.ix[g.lower]] - sk.rest[sk.ix[g.upper]])
            l2 = np.linalg.norm(sk.rest[sk.ix[g.end]] - sk.rest[sk.ix[g.lower]])
            A = (l1 + l2) * (1 - self.reach_margin)
            hh = math.hypot(tgt[0] - H[0], tgt[2] - H[2])
            v = H[1] - tgt[1]
            if hh < A:
                need = v - math.sqrt(A * A - hh * hh)
                dy = max(dy, need)
        if dy > 1e-6:
            ib = sk.ix["body"]
            ctx.T[ib][1] -= dy
            ctx.fk()

    def _solve_goal(self, g: Goal, t, ctx: Ctx):
        sk = self.sk
        w = self._w(g.weight, t)
        if w <= 1e-6:
            return
        tgt, Rt = self._target(g, t, ctx)
        if tgt is None:
            return
        iu, il, ie = sk.ix[g.upper], sk.ix[g.lower], sk.ix[g.end]
        Ru0, Rl0, Re0 = ctx.R[iu].copy(), ctx.R[il].copy(), ctx.R[ie].copy()
        twist = self._w(g.twist, t)
        pm = self._w(g.pole_mix, t) if g.pole_target is not None else 0.0
        two_bone_ik(sk, ctx.R, ctx.Rw, ctx.Pw, g.upper, g.lower, g.end, tgt, g.pole, None, twist_deg=twist, stretch=g.stretch,
                    pole_target=g.pole_target, pole_mix=pm)
        if w < 0.999:
            for i, R0 in ((iu, Ru0), (il, Rl0)):
                q = slerp(quat_from_mat(R0), quat_from_mat(ctx.R[i]), w)
                ctx.R[i] = mat_from_quat(q)
        ctx.fk()
        if Rt is not None:
            Rw_target = Rt
            Rl_world = ctx.Rw[il]
            Re_ik = Rl_world.T @ Rw_target
            if w < 0.999:
                Re_ik = mat_from_quat(slerp(quat_from_mat(Re0), quat_from_mat(Re_ik), w))
            ctx.R[ie] = Re_ik
            ctx.fk()

    def pose(self, t, overrides=True) -> Ctx:
        sk = self.sk
        ctx = Ctx(sk)
        for b, s in self._rot.items():
            ctx.R[sk.ix[b]] = euler(s(t))
        for b, s in self._pos.items():
            ctx.T[sk.ix[b]] = np.asarray(s(t), dtype=np.float64)[:3]
        ctx.fk()
        for h in self.pre_hooks:
            h(t, ctx)
        self._reach(t, ctx)
        for g in self.goals:
            self._solve_goal(g, t, ctx)
        if overrides:
            for ov in self.overrides:
                res = ov.fn(t)
                if res is None:
                    continue
                Rwant, Pwant = res
                i = sk.ix[ov.bone]
                p = sk.parent[i]
                Rp, Pp = ctx.Rw[p], ctx.Pw[p]
                ctx.R[i] = Rp.T @ Rwant
                ctx.T[i] = Rp.T @ (Pwant - Pp) - sk.off[i]
                ctx.fk()
        return ctx

    def world_at(self, bone, t, overrides=False):
        c = self.pose(t, overrides=overrides)
        i = self.sk.ix[bone]
        return c.Rw[i].copy(), c.Pw[i].copy()

    # ------------------------------------------------------------------ sampling / secondary / contacts
    def sample(self, duration, fps=30, loop=False, cycles=3) -> Sampled:
        sk = self.sk
        n = int(round(duration * fps))
        if abs(n / fps - duration) > 1e-6:
            raise ValueError(f"duration {duration} is not a whole number of frames at {fps} fps")
        reps = cycles if loop else 1
        nf = n * reps + (0 if loop else 1)
        times = np.arange(nf) / fps
        R = np.empty((nf, sk.n, 3, 3))
        T = np.empty((nf, sk.n, 3))
        for f, t in enumerate(times):
            c = self.pose(float(t))
            R[f], T[f] = c.R, c.T
        Rw = np.empty_like(R)
        Pw = np.empty((nf, sk.n, 3))
        for f in range(nf):
            Rw[f], Pw[f] = sk.fk(R[f], T[f])
        for sec in self.secondaries:
            self._apply_secondary(sec, R, T, Rw, Pw, 1.0 / fps)
        if self.secondaries:
            for f in range(nf):
                Rw[f], Pw[f] = sk.fk(R[f], T[f])
        if loop:                                         # keep the LAST cycle (springs have settled), plus the closing frame
            sl = slice((reps - 1) * n, reps * n)
            R, T, Rw, Pw, times = R[sl], T[sl], Rw[sl], Pw[sl], times[sl] - times[sl][0]
            R = np.concatenate([R, R[:1]])
            T = np.concatenate([T, T[:1]])
            Rw = np.concatenate([Rw, Rw[:1]])
            Pw = np.concatenate([Pw, Pw[:1]])
            times = np.concatenate([times, [duration]])
        out = Sampled(times, R, T, Rw, Pw)
        out.contacts = self._contacts(out, fps)
        return out

    def _apply_secondary(self, sec: Secondary, R, T, Rw, Pw, dt):
        sk = self.sk
        idr = sk.ix[sec.driver]
        first = sk.ix[sec.chain[0]]
        nf = len(R)
        anchor = Pw[:, first]
        acc = np.zeros_like(anchor)
        if nf > 2:
            acc[1:-1] = (anchor[2:] - 2 * anchor[1:-1] + anchor[:-2]) / (dt * dt)
            acc[0], acc[-1] = acc[1], acc[-2]
        acc = np.clip(acc, -30, 30)
        drive_base = np.stack([sec.hang * acc[:, 2], np.zeros(nf), -sec.hang * acc[:, 0]], 1)
        parent_R = Rw[:, idr].copy()
        for k, b in enumerate(sec.chain):
            ib = sk.ix[b]
            x = np.array([rotvec(parent_R[f]) for f in range(nf)])
            for f in range(1, nf):                          # unwrap rotvec jumps
                d = x[f] - x[f - 1]
                if np.linalg.norm(d) > 3.0:
                    x[f] = x[f - 1]
            fr = sec.freq * (sec.decay ** k)
            drive = drive_base * (sec.accel / max(1, k + 1))
            y = spring_follow(x, dt, fr, sec.zeta, drive=drive)
            e = (y - x) * (sec.follow * sec.follow_decay ** k) * np.array(sec.axes)
            ang = np.linalg.norm(e, axis=1, keepdims=True)
            lim = math.radians(sec.max_deg)
            e = np.where(ang > lim, e / np.maximum(ang, 1e-9) * lim, e)
            newR = np.empty((nf, 3, 3))
            for f in range(nf):
                newR[f] = from_rotvec(e[f]) @ parent_R[f]
            ip = sk.parent[ib]
            for f in range(nf):
                R[f, ib] = Rw[f, ip].T @ newR[f]
                Rw[f, ib] = newR[f]
                Pw[f, ib] = Pw[f, ip] + Rw[f, ip] @ (sk.off[ib] + T[f, ib])
            parent_R = newR

    def _contacts(self, S: Sampled, fps):
        out = {}
        for gname in self.contact_goals:
            g = next(x for x in self.goals if x.name == gname)
            ie = self.sk.ix[g.end]
            P = S.Pw[:, ie]
            rest_y = self.sk.rest[ie][1]
            floor = min(rest_y, P[:, 1].min()) + 0.012
            speed = np.zeros(len(P))
            speed[1:-1] = np.abs(P[2:, 1] - P[:-2, 1]) * fps / 2          # vertical speed only: a stance foot may sweep back over the plinth
            speed[0], speed[-1] = speed[1], speed[-2]
            down = (P[:, 1] < floor) & (speed < 0.18)
            runs, start = [], None
            for f, d in enumerate(down):
                if d and start is None:
                    start = f
                if (not d or f == len(down) - 1) and start is not None:
                    end = f if not d else f
                    runs.append([round(float(S.times[start]), 3), round(float(S.times[end]), 3)])
                    start = None
            out[g.end] = runs
        return out

    # ------------------------------------------------------------------ bake
    def bake(self, name, duration, loop=False, fps=30, tol_deg=0.10, tol_m=0.0004, keep_times=(), sampled=None):
        """-> rig.Clip with dense, key-reduced tracks.  `keep_times` (e.g. the impact time) are always keys."""
        from rig import Clip
        S = sampled or self.sample(duration, fps, loop)
        clip = Clip(name, duration, loop=loop, fps=fps)
        sk = self.sk
        times = S.times
        keep = {int(round(k * fps)) for k in keep_times}
        for i, b in enumerate(sk.names):
            q = np.array([quat_from_mat(S.R[f, i]) for f in range(len(times))])
            for f in range(1, len(q)):
                if np.dot(q[f], q[f - 1]) < 0:
                    q[f] = -q[f]
            ang = 2 * np.degrees(np.arccos(np.clip(np.abs(q[:, 3]), -1, 1)))
            if ang.max() > 0.06:
                idx = reduce_rot(times, q, tol_deg, keep)
                clip.set_dense(b, "rot", times[idx], q[idx])
            d = S.T[:, i]
            if np.abs(d).max() > 0.0002:
                idx = reduce_vec(times, d, tol_m, keep)
                clip.set_dense(b, "pos", times[idx], d[idx])
        if S.contacts:
            clip.extras["footContacts"] = S.contacts
        return clip


# ------------------------------------------------------------------ key reduction
def _rot_err(q0, q1, u, q):
    return 2 * math.degrees(math.acos(min(1.0, abs(float(np.dot(slerp(q0, q1, u), q))))))


def reduce_rot(times, q, tol_deg, keep=()):
    n = len(times)
    keepf = {0, n - 1} | set(int(k) for k in keep if 0 <= k < n)
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        worst, wi = -1.0, -1
        for k in range(a + 1, b):
            u = (times[k] - times[a]) / (times[b] - times[a])
            e = _rot_err(q[a], q[b], u, q[k])
            if e > worst:
                worst, wi = e, k
        mk = [k for k in keepf if a < k < b]
        if mk and worst <= tol_deg:
            wi = mk[0]
            worst = tol_deg + 1
        if worst > tol_deg:
            keepf.add(wi)
            stack.append((a, wi))
            stack.append((wi, b))
    return sorted(keepf)


def reduce_vec(times, v, tol, keep=()):
    n = len(times)
    keepf = {0, n - 1} | set(int(k) for k in keep if 0 <= k < n)
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        u = ((times[a + 1:b] - times[a]) / (times[b] - times[a]))[:, None]
        interp = v[a] * (1 - u) + v[b] * u
        err = np.linalg.norm(interp - v[a + 1:b], axis=1)
        wi = int(np.argmax(err)) + a + 1
        worst = err.max()
        mk = [k for k in keepf if a < k < b]
        if mk and worst <= tol:
            wi = mk[0]
            worst = tol + 1
        if worst > tol:
            keepf.add(wi)
            stack.append((a, wi))
            stack.append((wi, b))
    return sorted(keepf)
