"""rig.py - skeleton, sockets and a tiny keyframe DSL for the five contract clips.

Bones are defined by ABSOLUTE rest positions (no rest rotation), so a clip rotation of (rx, ry, rz) degrees
rotates the bone about its joint in world axes.  Right-hand rule: for the figure facing +Z, a NEGATIVE
rx swings a hanging arm forward/up (-90 = straight ahead, -180 = overhead).  Character's right side is -X.

    rig = Rig()
    rig.add("root", None, (0, 0, 0)); rig.add("body", "root", (0, .5, 0)); ...
    rig.socket("socket_weapon_R", "hand_R", (-.1, .5, .1))

    idle = Clip("Idle", 3.0, loop=True)
    idle.wave("spine", "rot", axis=0, amp=1.2, cycles=1)             # breathing (integer cycles => loops)
    idle.key("body", "pos", 0.0, (0, 0, 0)); idle.key("body", "pos", 1.5, (0, .004, 0), "in_out_cubic")

Values:  rot = Euler degrees delta from rest (XYZ extrinsic);  pos = metres delta from the rest local
translation;  scale = absolute multiplier (scalar or xyz).  `ease` on a key shapes the segment that ENDS at it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from geom import rot_matrix

CONTRACT_CLIPS = ("Idle", "Move", "Attack", "HitReact", "Victory")


# ------------------------------------------------------------------ rig
@dataclass
class Bone:
    name: str
    parent: str | None
    pos: np.ndarray


class Rig:
    def __init__(self):
        self.bones: dict[str, Bone] = {}
        self.sockets: dict[str, tuple[str, np.ndarray]] = {}

    def add(self, name, parent, pos):
        assert parent is None or parent in self.bones, f"parent {parent!r} must be added before {name!r}"
        self.bones[name] = Bone(name, parent, np.asarray(pos, dtype=np.float64))
        return name

    def socket(self, name, bone, pos):
        assert bone in self.bones
        self.sockets[name] = (bone, np.asarray(pos, dtype=np.float64))

    @property
    def order(self):
        return list(self.bones)

    def index(self, name):
        return self.order.index(name)

    def local(self, name):
        b = self.bones[name]
        return b.pos if b.parent is None else b.pos - self.bones[b.parent].pos

    def pos(self, name):
        return self.bones[name].pos.copy()


# ------------------------------------------------------------------ easing
def _out_back(t, s=1.70158):
    t = t - 1
    return t * t * ((s + 1) * t + s) + 1


def _in_back(t, s=1.70158):
    return t * t * ((s + 1) * t - s)


def _out_elastic(t):
    if t <= 0 or t >= 1:
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


EASE = {
    "linear": lambda t: t,
    "in_quad": lambda t: t * t,
    "out_quad": lambda t: 1 - (1 - t) ** 2,
    "in_out_quad": lambda t: 2 * t * t if t < .5 else 1 - (-2 * t + 2) ** 2 / 2,
    "in_cubic": lambda t: t ** 3,
    "out_cubic": lambda t: 1 - (1 - t) ** 3,
    "in_out_cubic": lambda t: 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2,
    "in_expo": lambda t: 0.0 if t <= 0 else 2 ** (10 * t - 10),
    "out_expo": lambda t: 1.0 if t >= 1 else 1 - 2 ** (-10 * t),
    "in_back": _in_back,
    "out_back": _out_back,
    "in_out_back": lambda t: (_in_back(t * 2) / 2) if t < .5 else (_out_back(t * 2 - 1) / 2 + .5),
    "out_elastic": _out_elastic,
    "smooth": lambda t: t * t * (3 - 2 * t),
    "hold": lambda t: 0.0,     # keep the previous value until the key time, then jump
}


# ------------------------------------------------------------------ animation
def _euler_to_quat(e):
    """Euler degrees (XYZ extrinsic, matches geom.rot_matrix) -> quaternion (x,y,z,w)."""
    ax, ay, az = (math.radians(v) / 2 for v in e)
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    qx = np.array([sx, 0, 0, cx])
    qy = np.array([0, sy, 0, cy])
    qz = np.array([0, 0, sz, cz])

    def mul(a, b):
        x1, y1, z1, w1 = a
        x2, y2, z2, w2 = b
        return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                         w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])
    q = mul(qz, mul(qy, qx))
    return q / np.linalg.norm(q)


@dataclass
class Track:
    bone: str
    path: str                                   # rot | pos | scale
    keys: list = field(default_factory=list)    # (time, value ndarray(3), ease)
    waves: list = field(default_factory=list)   # (axis, amp, cycles, phase)
    step: bool = False

    def eval(self, t, duration, default):
        ks = sorted(self.keys, key=lambda k: k[0])
        if not ks:
            v = np.array(default, dtype=np.float64)
        elif t <= ks[0][0]:
            v = ks[0][1].copy()
        elif t >= ks[-1][0]:
            v = ks[-1][1].copy()
        else:
            for a, b in zip(ks[:-1], ks[1:]):
                if a[0] <= t <= b[0]:
                    u = (t - a[0]) / max(b[0] - a[0], 1e-9)
                    u = EASE[b[2]](u)
                    v = a[1] * (1 - u) + b[1] * u
                    break
        for axis, amp, cycles, phase in self.waves:
            v = v.copy()
            v[axis] += amp * math.sin(2 * math.pi * (cycles * t / duration + phase))
        return v


class Clip:
    def __init__(self, name, duration, loop=False, fps=30):
        self.name, self.duration, self.loop, self.fps = name, float(duration), loop, fps
        self.tracks: dict[tuple[str, str], Track] = {}

    def _track(self, bone, path, step=False):
        k = (bone, path)
        if k not in self.tracks:
            self.tracks[k] = Track(bone, path, step=step)
        return self.tracks[k]

    @staticmethod
    def _v(path, value):
        if path == "scale":
            if np.ndim(value) == 0:
                return np.full(3, float(value))
        return np.asarray(value, dtype=np.float64)

    def key(self, bone, path, time, value, ease="linear", step=False):
        """Add a keyframe. For `step=True` tracks (scale toggles) no interpolation is baked."""
        self._track(bone, path, step).keys.append((float(time), self._v(path, value), ease))
        return self

    def keys(self, bone, path, items, step=False):
        """items: [(time, value) | (time, value, ease), ...]"""
        for it in items:
            self.key(bone, path, it[0], it[1], it[2] if len(it) > 2 else "linear", step)
        return self

    def hold(self, bone, path, value):
        """Constant track over the whole clip (also makes the clip reset the property)."""
        self.key(bone, path, 0.0, value)
        self.key(bone, path, self.duration, value)
        return self

    def wave(self, bone, path, axis, amp, cycles=1, phase=0.0):
        """Add amp*sin(2pi*(cycles*t/duration + phase)) on one axis. Integer cycles keep loops seamless."""
        self._track(bone, path).waves.append((axis, amp, cycles, phase))
        return self

    def loop_close(self):
        """Copy each track's first key to the clip end (seamless loop)."""
        for tr in self.tracks.values():
            if tr.keys and not tr.step:
                first = min(tr.keys, key=lambda k: k[0])
                if max(k[0] for k in tr.keys) < self.duration - 1e-6:
                    tr.keys.append((self.duration, first[1].copy(), "in_out_cubic"))
        return self

    def bake(self, rig: Rig):
        """-> list of channel dicts {bone, path('translation'|'rotation'|'scale'), times, values, interpolation}."""
        out = []
        n = max(2, int(math.ceil(self.duration * self.fps)) + 1)
        grid = np.linspace(0, self.duration, n)
        for (bone, path), tr in self.tracks.items():
            if tr.step:
                ts = sorted({k[0] for k in tr.keys} | {0.0})
                vals = [tr.eval(t, self.duration, (1, 1, 1)) for t in ts]
                out.append({"bone": bone, "path": "scale", "times": np.array(ts), "values": np.array(vals),
                            "interpolation": "STEP"})
                continue
            kt = np.array([k[0] for k in tr.keys])
            times = np.unique(np.concatenate([grid, kt[(kt >= 0) & (kt <= self.duration)]]))
            if path == "rot":
                vals = np.array([_euler_to_quat(tr.eval(t, self.duration, (0, 0, 0))) for t in times])
                # keep quaternion hemisphere continuous
                for i in range(1, len(vals)):
                    if np.dot(vals[i], vals[i - 1]) < 0:
                        vals[i] = -vals[i]
                out.append({"bone": bone, "path": "rotation", "times": times, "values": vals, "interpolation": "LINEAR"})
            elif path == "pos":
                rest = rig.local(bone)
                vals = np.array([rest + tr.eval(t, self.duration, (0, 0, 0)) for t in times])
                out.append({"bone": bone, "path": "translation", "times": times, "values": vals, "interpolation": "LINEAR"})
            elif path == "scale":
                vals = np.array([tr.eval(t, self.duration, (1, 1, 1)) for t in times])
                out.append({"bone": bone, "path": "scale", "times": times, "values": vals, "interpolation": "LINEAR"})
            else:
                raise ValueError(path)
        return out
