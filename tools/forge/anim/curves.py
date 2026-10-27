"""curves.py - animation curves: eased Bezier segments, flowing (PCHIP) splines, spring settles, springs-follow filters.

    c = Curve([(0, (0, 0, 0)),
               (0.3, (12, 0, 0), "out_cubic"),            # ease INTO this key with a preset ...
               (0.6, (-4, 0, 0), (0.2, 0, 0.1, 1)),       # ... or a CSS-style cubic-bezier(x1, y1, x2, y2)
               (0.9, (0, 0, 0), ("spring", 0.18, 1.5)),   # damped overshoot-and-settle (overshoot fraction, half-cycles)
               (1.2, (0, 0, 0))],
              loop=None)
    c(0.45) -> ndarray      c.sample(times) -> (n, d)

Keys WITHOUT an ease flow through a monotone cubic Hermite spline (PCHIP: smooth velocity, never overshoots a key),
which is what makes sparse keys read as organic arcs instead of stop-go.  A key with an ease flag, or `{"tan": "flat"}`,
stops/starts there.  `loop=period` makes the curve cyclic (the first key is copied to `period` if missing).
Values are scalars or vectors (default 3-vectors: Euler degrees or metres).
"""
from __future__ import annotations

import math

import numpy as np


# ------------------------------------------------------------------ easing functions
def cubic_bezier(x1, y1, x2, y2):
    """CSS-style easing: returns f(u) for the Bezier (0,0)-(x1,y1)-(x2,y2)-(1,1)."""
    def fx(s):
        return 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s * s * x2 + s ** 3

    def fy(s):
        return 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s * s * y2 + s ** 3

    def f(u):
        if u <= 0:
            return 0.0
        if u >= 1:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(28):
            mid = 0.5 * (lo + hi)
            if fx(mid) < u:
                lo = mid
            else:
                hi = mid
        return fy(0.5 * (lo + hi))
    return f


def spring_ease(overshoot=0.15, half_cycles=1.5):
    """Underdamped step response a -> b that overshoots by ~`overshoot` of the travel and settles exactly at u=1."""
    over = max(1e-3, overshoot)
    cyc = max(0.75, half_cycles)
    # amplitude of the first peak of exp(-c u) cos(pi * 2 * cyc * u / 2 ...) ~ over  ->  choose decay so peak ~ over
    w = math.pi * cyc * 2 / 2                       # cos argument per unit u (cyc half-cycles over u in 0..1)
    c = -math.log(over) / (math.pi / w) if over < 1 else 1.0
    c = max(c, 1.0)

    def f(u):
        if u <= 0:
            return 0.0
        if u >= 1:
            return 1.0
        y = 1 - math.exp(-c * u) * math.cos(w * u)
        return y + (1 - (1 - math.exp(-c) * math.cos(w))) * u ** 3     # force y(1) = 1
    return f


def _named(name):
    from rig import EASE
    return EASE[name]


PRESETS = {
    "ease": (0.25, 0.1, 0.25, 1.0), "ease_in": (0.42, 0, 1, 1), "ease_out": (0, 0, 0.58, 1), "ease_in_out": (0.42, 0, 0.58, 1),
    "anticipate": (0.6, -0.28, 0.735, 0.045),     # dips backwards first, then goes (use for wind-ups)
    "snap_in": (0.7, 0.0, 0.9, 0.35),             # slow start, violent finish: strikes
    "whip": (0.9, 0.0, 1.0, 0.3),
    "soft_land": (0.2, 0.9, 0.3, 1.0),
    "overshoot": (0.3, 1.0, 0.45, 1.25),
}
_CACHE: dict = {}


def ease_fn(spec):
    """str preset / rig.EASE name, 4-tuple bezier, ("spring", overshoot, half_cycles), or a callable."""
    if spec is None:
        return None
    if callable(spec):
        return spec
    key = spec if isinstance(spec, (str, tuple)) else tuple(spec)
    if key in _CACHE:
        return _CACHE[key]
    if isinstance(spec, str):
        f = cubic_bezier(*PRESETS[spec]) if spec in PRESETS else _named(spec)
    elif spec[0] == "spring":
        f = spring_ease(*spec[1:])
    else:
        f = cubic_bezier(*spec)
    _CACHE[key] = f
    return f


# ------------------------------------------------------------------ signals
class Sig:
    """Anything callable t -> ndarray; supports + and * so layers can be summed."""
    dim = 3

    def __call__(self, t):
        raise NotImplementedError

    def sample(self, times):
        return np.array([self(float(t)) for t in times])

    def __add__(self, other):
        return Fn(lambda t: self(t) + (other(t) if callable(other) else np.asarray(other, dtype=np.float64)))

    __radd__ = __add__

    def __mul__(self, k):
        return Fn(lambda t: self(t) * (k(t) if callable(k) else k))

    __rmul__ = __mul__

    def shift(self, dt):
        return Fn(lambda t: self(t - dt))


class Fn(Sig):
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, t):
        return np.asarray(self.fn(t), dtype=np.float64)


class Const(Sig):
    def __init__(self, v):
        self.v = np.asarray(v, dtype=np.float64)

    def __call__(self, t):
        return self.v


class Wave(Sig):
    """amp * sin(2 pi (freq t + phase)) per component; `amp` is a vector (or scalar)."""

    def __init__(self, amp, freq, phase=0.0, bias=0.0):
        self.amp = np.asarray(amp, dtype=np.float64)
        self.freq, self.phase = freq, phase
        self.bias = np.asarray(bias, dtype=np.float64)

    def __call__(self, t):
        return self.bias + self.amp * math.sin(2 * math.pi * (self.freq * t + self.phase))


def _pchip_slopes(ts, vs, cyclic=False, period=None):
    n = len(ts)
    m = np.zeros_like(vs)
    if n < 2:
        return m
    h = np.diff(ts)
    d = np.diff(vs, axis=0) / h[:, None]
    if cyclic:
        hp = np.concatenate([[h[-1]], h, [h[0]]])
        dp = np.concatenate([d[-1:], d, d[:1]])
        for k in range(n):
            d0, d1 = dp[k], dp[k + 1]
            w1, w2 = 2 * hp[k + 1] + hp[k], hp[k + 1] + 2 * hp[k]
            with np.errstate(divide="ignore", invalid="ignore"):
                mk = (w1 + w2) / (w1 / d0 + w2 / d1)
            m[k] = np.where(d0 * d1 > 0, mk, 0.0)
        return m
    for k in range(1, n - 1):
        d0, d1 = d[k - 1], d[k]
        w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            mk = (w1 + w2) / (w1 / d0 + w2 / d1)
        m[k] = np.where(d0 * d1 > 0, mk, 0.0)
    return m


class Curve(Sig):
    def __init__(self, keys, loop=None):
        ks = []
        for k in keys:
            t, v = float(k[0]), np.atleast_1d(np.asarray(k[1], dtype=np.float64))
            opt = k[2] if len(k) > 2 else None
            ease, tan = None, None
            if isinstance(opt, dict):
                ease, tan = opt.get("ease"), opt.get("tan")
            else:
                ease = opt
            ks.append([t, v, ease, tan])
        ks.sort(key=lambda k: k[0])
        self.loop = loop
        if loop is not None and ks and abs(ks[-1][0] - loop) > 1e-9:
            ks.append([float(loop), ks[0][1].copy(), None, None])
        self.t = np.array([k[0] for k in ks])
        self.v = np.array([k[1] for k in ks])
        self.ease = [ease_fn(k[2]) if k[2] != "hold" else "hold" for k in ks]
        self.dim = self.v.shape[1] if len(ks) else 1
        m = _pchip_slopes(self.t, self.v, cyclic=loop is not None) if len(ks) > 1 else np.zeros_like(self.v)
        for i, k in enumerate(ks):
            if k[3] == "flat" or (k[2] is not None and k[3] is None):
                m[i] = 0.0
            elif k[3] is not None and not isinstance(k[3], str):
                m[i] = np.asarray(k[3], dtype=np.float64)
        if loop is not None and len(ks) > 1:
            m[-1] = m[0]
        self.m = m

    def __call__(self, t):
        if self.loop is not None:
            t = t % self.loop
        ts = self.t
        if t <= ts[0]:
            return self.v[0].copy()
        if t >= ts[-1]:
            return self.v[-1].copy()
        i = int(np.searchsorted(ts, t, side="right") - 1)
        h = ts[i + 1] - ts[i]
        u = (t - ts[i]) / h
        e = self.ease[i + 1]
        if e == "hold":
            return self.v[i].copy()
        if e is not None:
            return self.v[i] + (self.v[i + 1] - self.v[i]) * e(u)
        u2, u3 = u * u, u * u * u
        return ((2 * u3 - 3 * u2 + 1) * self.v[i] + (u3 - 2 * u2 + u) * h * self.m[i]
                + (-2 * u3 + 3 * u2) * self.v[i + 1] + (u3 - u2) * h * self.m[i + 1])


def key(t, v, ease=None, **kw):
    """Key constructor with options: key(0.3, (10,0,0), tan="flat")."""
    if kw:
        d = dict(kw)
        if ease is not None:
            d["ease"] = ease
        return (t, v, d)
    return (t, v, ease) if ease is not None else (t, v)


def lerp_curve(a, b, w):
    """Blend two signals by a scalar signal w(t) in 0..1."""
    return Fn(lambda t: a(t) * (1 - float(np.asarray(w(t)).ravel()[0])) + b(t) * float(np.asarray(w(t)).ravel()[0]))


def pulse(t0, t1, ramp_in=0.08, ramp_out=0.08, amp=1.0):
    """Scalar signal: 0 -> amp over [t0 - ramp_in, t0], hold, amp -> 0 over [t1, t1 + ramp_out] (smoothstep)."""
    def f(t):
        a = (t - (t0 - ramp_in)) / max(ramp_in, 1e-6)
        b = ((t1 + ramp_out) - t) / max(ramp_out, 1e-6)
        u = min(max(min(a, b), 0.0), 1.0)
        return np.array([amp * u * u * (3 - 2 * u)])
    return Fn(f)


def step_signal(points, loop=None):
    """Scalar 0..1 signal through (t, value) points with smoothstep between them (weights/blends)."""
    pts = sorted(points)

    def f(t):
        if loop:
            t = t % loop
        if t <= pts[0][0]:
            return np.array([float(pts[0][1])])
        for (t0, v0), (t1, v1) in zip(pts[:-1], pts[1:]):
            if t <= t1:
                u = (t - t0) / max(t1 - t0, 1e-9)
                u = u * u * (3 - 2 * u)
                return np.array([v0 + (v1 - v0) * u])
        return np.array([float(pts[-1][1])])
    return Fn(f)


# ------------------------------------------------------------------ secondary motion filter
def spring_follow(x, dt, freq=2.5, zeta=0.45, drive=None, y0=None, substeps=4):
    """Second-order lag: y'' = w^2 (x - y) - 2 zeta w y' + drive.   x: (n, d) target samples at spacing dt;
    returns y (n, d).  Underdamped (zeta < 1) gives overshoot / follow-through; use for cape, bedroll, crest, tail, ears."""
    x = np.asarray(x, dtype=np.float64)
    w = 2 * math.pi * freq
    y = np.zeros_like(x)
    yy = x[0].copy() if y0 is None else np.asarray(y0, dtype=np.float64)
    vv = np.zeros_like(yy)
    h = dt / substeps
    for i in range(len(x)):
        y[i] = yy
        for _ in range(substeps):
            xi = x[i]
            a = w * w * (xi - yy) - 2 * zeta * w * vv
            if drive is not None:
                a = a + drive[i]
            vv = vv + a * h
            yy = yy + vv * h
    return y
