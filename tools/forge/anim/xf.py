"""xf.py - tiny rotation / quaternion helpers shared by the animation toolkit (numpy only).

Conventions match rig.py / geom.py: Euler degrees XYZ extrinsic (R = Rz @ Ry @ Rx), quaternions are (x, y, z, w),
+X is the character's LEFT, +Z is forward, +Y up.
"""
from __future__ import annotations

import math

import numpy as np

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geom import rot_matrix, axis_angle, rot_between, normalize   # noqa: E402,F401

I3 = np.eye(3)


def euler(e):
    """Euler degrees (rx, ry, rz) -> 3x3."""
    return rot_matrix(float(e[0]), float(e[1]), float(e[2]))


def quat_from_mat(R):
    R = np.asarray(R, dtype=np.float64)
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = np.array([(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, 0.25 * s])
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = np.array([0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s, (R[2, 1] - R[1, 2]) / s])
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = np.array([(R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s, (R[0, 2] - R[2, 0]) / s])
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = np.array([(R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s, (R[1, 0] - R[0, 1]) / s])
    return q / np.linalg.norm(q)


def mat_from_quat(q):
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(q0, q1, u):
    d = float(np.dot(q0, q1))
    if d < 0:
        q1, d = -q1, -d
    if d > 0.9995:
        q = q0 + (q1 - q0) * u
        return q / np.linalg.norm(q)
    th = math.acos(min(1.0, d))
    s = math.sin(th)
    return (math.sin((1 - u) * th) * q0 + math.sin(u * th) * q1) / s


def rotvec(R):
    """3x3 -> axis * angle (radians)."""
    q = quat_from_mat(R)
    if q[3] < 0:
        q = -q
    s = np.linalg.norm(q[:3])
    if s < 1e-9:
        return np.zeros(3)
    return q[:3] / s * (2 * math.atan2(s, q[3]))


def from_rotvec(v):
    v = np.asarray(v, dtype=np.float64)
    a = np.linalg.norm(v)
    if a < 1e-12:
        return np.eye(3)
    return axis_angle(v / a, math.degrees(a))


def frame(axis, normal):
    """Orthonormal 3x3 whose first column is `axis`, second is `normal` (orthogonalised), third = x cross y."""
    x = normalize(np.asarray(axis, dtype=np.float64))
    n = np.asarray(normal, dtype=np.float64)
    y = n - np.dot(n, x) * x
    ln = np.linalg.norm(y)
    if ln < 1e-9:
        y = np.cross(x, [0.0, 0.0, 1.0] if abs(x[2]) < 0.9 else [1.0, 0.0, 0.0])
        ln = np.linalg.norm(y)
    y = y / ln
    return np.stack([x, y, np.cross(x, y)], 1)


def yaw_of(R):
    """Heading (deg, about +Y) of the +Z axis of R."""
    z = R[:, 2]
    return math.degrees(math.atan2(z[0], z[2]))
