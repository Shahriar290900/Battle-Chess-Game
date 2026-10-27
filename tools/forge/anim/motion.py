"""motion.py - motion generators built on Animator: idle breathing + weight shift, biped gait, quadruped gait,
anticipation/strike/impact/recover key builders, head stabilisation, weapon release (drop + bounce).

All generators ADD layers to an Animator, so they stack (a gait under an upper-body strike, a breath under a taunt).
Euler conventions: +rx pitches +Y toward +Z (toe DOWN, hanging arm BACK; arm forward = negative rx), +ry turns +Z toward +X,
+rz raises the character's LEFT (+X) side / tips +Y toward -X.
"""
from __future__ import annotations

import math

import numpy as np

from .curves import Curve, Fn, Wave, Sig, ease_fn
from .xf import axis_angle, from_rotvec, rot_between, rotvec


def v3(x=0.0, y=0.0, z=0.0):
    return np.array([x, y, z], dtype=np.float64)


# ====================================================================================== feet / planting
def plant_feet(a, feet=(("foot_L", ("thigh_L", "shin_L", "foot_L")), ("foot_R", ("thigh_R", "shin_R", "foot_R"))), pole=(0, 0, 1)):
    """World-space (plinth) leg IK goals with feet flat at rest, plus the pelvis reach clamp.  Returns {name: Goal}."""
    out = {}
    for name, chain in feet:
        g = next((x for x in a.goals if x.name == name), None)
        if g is None:
            g = a.goal(name, chain, pos=None, rot=(0, 0, 0), pole=pole, contact=True)
        out[name] = g
    a.keep_legs_reachable(list(out))
    return out


def set_foot(a, name, pos=None, rot=None, weight=None):
    """Replace / assign the targets of an existing foot goal (pos: delta metres from the rest ankle, world space; rot: Euler deg)."""
    g = next(x for x in a.goals if x.name == name)
    if pos is not None:
        g.pos = pos if isinstance(pos, Sig) else Curve(pos)
    if rot is not None:
        g.rot = rot if isinstance(rot, Sig) else Curve(rot)
    if weight is not None:
        g.weight = weight
    return g


# ====================================================================================== head stabilisation
def stabilize(a, bone="head", ratio=0.5, pivot_chain=None):
    """Counter-rotate `bone` by `ratio` of everything above it (pelvis bob/tilt/yaw) so the head stays calm: classic
    'head leads, body follows'.  Adds a pre-IK hook."""
    ib = a.sk.ix[a.rig.resolve(bone)]
    ip = a.sk.parent[ib]

    def hook(t, ctx):
        Rp = ctx.Rw[ip]
        rv = rotvec(Rp)
        D = from_rotvec(-ratio * rv)
        ctx.R[ib] = Rp.T @ D @ Rp @ ctx.R[ib]
        ctx.fk()
    a.hook(hook)


# ====================================================================================== idle
def idle(a, period=3.0, breath=1.0, shift=1.0, sway=0.010, look=1.0, hands=True, loop_cycles=1, stab=0.45, phase=0.0):
    """Breathing + weight shift (+ micro look-around).  Loop-safe when period == clip duration.  Feet must be planted
    (call plant_feet first) so the weight shift reads as the body moving over fixed feet."""
    f = 1.0 / period
    b = breath
    s = shift
    # breath: chest swell, shoulders rise, spine lengthens, head counters
    a.rot("chest", Wave(v3(-1.8 * b), f * loop_cycles, phase))
    a.rot("spine", Wave(v3(-0.7 * b), f * loop_cycles, phase + 0.06))
    a.rot("clavicle_L", Wave(v3(0, 0, 1.4 * b), f * loop_cycles, phase + 0.04))
    a.rot("clavicle_R", Wave(v3(0, 0, -1.4 * b), f * loop_cycles, phase + 0.04))
    a.rot("neck", Wave(v3(0.9 * b), f * loop_cycles, phase + 0.12))
    a.pos("body", Wave(v3(0, 0.0022 * b, 0), f * loop_cycles, phase + 0.25))
    # weight shift: pelvis sways over one foot, hips tilt, spine/chest/head counter-balance (S-curve)
    ph = phase + 0.1
    a.pos("body", Wave(v3(sway * s, 0, 0), f, ph))
    a.rot("body", Wave(v3(0, 1.6 * s * look, 2.4 * s), f, ph + 0.02))
    a.rot("spine", Wave(v3(0, -1.0 * s * look, -2.0 * s), f, ph + 0.07))
    a.rot("chest", Wave(v3(0, -0.8 * s * look, -1.3 * s), f, ph + 0.12))
    a.rot("neck", Wave(v3(0, 1.4 * look, 0.8 * s), f, ph + 0.20))
    a.rot("head", Wave(v3(-0.6 * look, 3.4 * look, 1.2 * s), f, ph + 0.28))
    a.rot("head", Wave(v3(0.8 * look, 0, 0), f * 2, ph + 0.1))        # 2nd harmonic: tiny nod
    if hands:
        a.rot("arm_L", Wave(v3(-1.6 * s, 0, 1.2 * s), f, ph + 0.3))
        a.rot("arm_R", Wave(v3(1.0 * s, 0, 1.0 * s), f, ph + 0.35))
        a.rot("hand_L", Wave(v3(-2.2 * s, 0, 0), f, ph + 0.4))
        a.rot("hand_R", Wave(v3(-1.6 * s, 0, 0), f, ph + 0.45))
    if stab:
        stabilize(a, "head", stab)


# ====================================================================================== biped gait
def biped_gait(a, period, stride=0.03, lift=0.05, duty=0.58, bob=0.010, sway=0.012, roll=3.0, twist=6.0, lean=4.0,
               arm_swing=(10.0, 10.0), elbow=14.0, toe_off=22.0, strike=-8.0, heel=0.075, head_stab=0.55,
               feet=("foot_L", "foot_R"), chain=None, phase=0.0, shoulders=True):
    """Procedural in-place march / walk cycle: contact, down, pass, up poses fall out of the foot paths + pelvis curves.
      stride   total fore-aft foot travel (stance foot sweeps back by `stride`, swing foot goes forward): 0 = marching on the spot
      lift     swing-foot clearance (m);  duty = stance fraction of the cycle per leg (0.5-0.65)
      bob/sway pelvis dip (m, lowest at contact) and lateral shift over the stance foot;  roll/twist pelvis tilt/yaw (deg)
      lean     forward body pitch;  arm_swing (L, R) shoulder swing deg (opposite the legs);  elbow forearm flex coupling
      toe_off/strike foot pitch at lift-off (toe down +) and touch-down (toe up -);  heel = ankle->toe horizontal length
    Stance feet are exactly planted (zero velocity when stride = 0); contact markers land in clip.extras['footContacts']."""
    T = period
    names = list(feet)
    half = stride / 2

    def foot_path(phase_off, sgn):
        def pos(t):
            u = (t / T + phase_off) % 1.0
            if u < duty:                                      # stance: planted, sweeping back by `stride`, heel lifts at the end
                w = u / duty
                z = half - stride * w
                pitch = 0.0
                if w > 0.8:
                    q = (w - 0.8) / 0.2
                    pitch = toe_off * 0.6 * q * q * (3 - 2 * q)
                lift_y = 0.0
            else:                                             # swing: toe-off, clear, toe-up touch-down
                w = (u - duty) / (1 - duty)
                z = -half + stride * (w * w * (3 - 2 * w))
                lift_y = lift * math.sin(math.pi * w) ** 1.2
                pitch = toe_off * 0.6 * (1 - w) ** 2
                if w > 0.55:
                    pitch += strike * math.sin(math.pi * (w - 0.55) / 0.45) ** 2
            y = lift_y + heel * math.sin(math.radians(max(pitch, 0.0)))
            return v3(0, y, z), pitch
        return pos

    sig_pos, sig_rot = {}, {}
    for k, nm in enumerate(names):
        off = (0.5 * k + phase) % 1.0
        fp = foot_path(off, 1 if nm.endswith("_L") else -1)
        sig_pos[nm] = Fn(lambda t, fp=fp: fp(t)[0])
        sig_rot[nm] = Fn(lambda t, fp=fp: v3(fp(t)[1], 0, 0))
        g = next((x for x in a.goals if x.name == nm), None)
        if g is None:
            g = a.goal(nm, chain[k] if chain else (f"thigh_{nm[-1]}", f"shin_{nm[-1]}", nm), contact=True)
        g.pos, g.rot = sig_pos[nm], sig_rot[nm]
    a.keep_legs_reachable(names)
    f = 1.0 / T
    ph = phase
    # pelvis: dip at every contact (2 per cycle), shift over the stance foot, tilt, counter-twisting spine
    a.pos("body", Fn(lambda t: v3(0, -bob * (1 - math.cos(4 * math.pi * (t / T + ph))) / 2, 0)))
    a.pos("body", Wave(v3(sway, 0, 0), f, ph))
    a.rot("body", Wave(v3(0, twist, roll), f, ph))
    a.rot("body", v3(lean * 0.5, 0, 0))
    a.rot("spine", Wave(v3(0, -twist * 0.55, -roll * 0.7), f, ph + 0.05))
    a.rot("spine", v3(lean * 0.3, 0, 0))
    a.rot("chest", Wave(v3(0, -twist * 0.65, -roll * 0.5), f, ph + 0.10))
    a.rot("chest", v3(lean * 0.3, 0, 0))
    a.rot("chest", Wave(v3(-1.2, 0, 0), 2 * f, ph + 0.15))           # chest pitch pulses with each step
    a.rot("neck", Wave(v3(0, twist * 0.3, 0), f, ph + 0.15))
    a.rot("head", Wave(v3(1.0, 0, 0), 2 * f, ph + 0.3))
    if shoulders:
        a.rot("clavicle_L", Wave(v3(0, 0, 1.5), 2 * f, ph + 0.2))
        a.rot("clavicle_R", Wave(v3(0, 0, -1.5), 2 * f, ph + 0.2))
    # arms: counter-swing, forearm follows with a lag (overlap)
    for side, amp, sg in (("L", arm_swing[0], -1.0), ("R", arm_swing[1], 1.0)):
        if amp:
            a.rot(f"arm_{side}", Wave(v3(sg * amp, 0, 0), f, ph))
            a.rot(f"hand_{side}", Wave(v3(-elbow * 0.5, 0, 0), f, ph + 0.12, bias=v3(-elbow * 0.5)))
            a.rot(f"hand_{side}", Wave(v3(sg * amp * 0.35, 0, 0), f, ph + 0.18))
    if head_stab:
        stabilize(a, "head", head_stab)


# ====================================================================================== quadruped gait
def quadruped_gait(a, period, kind="walk", stride=0.28, lift=0.07, bob=0.012, head_bob=7.0, spine_wave=2.5, tail_swing=10.0,
                   legs=None, phase=0.0):
    """Mount gait (knights).  `legs` maps leg-name -> (chain, phase_offset): defaults to the quadruped_rig bones
    walk: LH, LF, RH, RF at 0/.25/.5/.75 (lateral sequence);  trot: diagonal pairs at 0/.5;  canter: 3-beat (RH, LH+RF, LF) with a suspension.
    Feet: stance sweeps back by `stride` over the plinth, swing arcs forward with `lift`; hooves stay flat; spine undulates, the head bobs
    opposite the forelegs, the tail trails (see `Animator.secondary`)."""
    T = period
    if legs is None:
        off = {"walk": {"hind_L": 0.0, "fore_L": 0.25, "hind_R": 0.5, "fore_R": 0.75},
               "trot": {"hind_L": 0.0, "fore_R": 0.0, "hind_R": 0.5, "fore_L": 0.5},
               "canter": {"hind_R": 0.0, "hind_L": 0.33, "fore_R": 0.33, "fore_L": 0.66}}[kind]
        legs = {}
        for side in "LR":
            legs[f"hoof_hind_{side}"] = ((f"hind_upper_{side}", f"hind_lower_{side}", f"hind_hoof_{side}"), off[f"hind_{side}"])
            legs[f"hoof_fore_{side}"] = ((f"fore_upper_{side}", f"fore_lower_{side}", f"fore_hoof_{side}"), off[f"fore_{side}"])
    duty = {"walk": 0.68, "trot": 0.5, "canter": 0.4}[kind]
    half = stride / 2
    for nm, (chain, po) in legs.items():
        po = (po + phase) % 1.0

        def pos(t, po=po):
            u = (t / T + po) % 1.0
            if u < duty:
                w = u / duty
                return v3(0, 0, half - stride * w)
            w = (u - duty) / (1 - duty)
            e = w * w * (3 - 2 * w)
            return v3(0, lift * math.sin(math.pi * w) ** 1.3, -half + stride * e)

        def rot(t, po=po):
            u = (t / T + po) % 1.0
            if u < duty:
                return v3(0, 0, 0)
            w = (u - duty) / (1 - duty)
            return v3(18 * (1 - w) ** 2 - 10 * math.sin(math.pi * max(0, w - 0.6) / 0.4) ** 2, 0, 0)
        g = next((x for x in a.goals if x.name == nm), None)
        if g is None:
            g = a.goal(nm, chain, contact=True, pole=(0, 0, -1) if "hind" in nm else (0, 0, 1))
        g.pos, g.rot = Fn(pos), Fn(rot)
    a.keep_legs_reachable(list(legs))
    f = 1.0 / T
    cyc = 2 if kind == "walk" else 1
    a.pos("body", Fn(lambda t: v3(0, -bob * (1 - math.cos(2 * math.pi * 2 * (t / T + phase))) / 2, 0)))
    a.rot("body", Wave(v3(spine_wave, 0, 1.2), f, phase))
    a.rot("mount_body", Wave(v3(-spine_wave * 0.6, 1.5, 0.8), f, phase + 0.1))
    a.rot("mount_chest", Wave(v3(spine_wave * 0.5, -1.0, 0), 2 * f, phase + 0.2))
    a.rot("neck_1", Wave(v3(head_bob * 0.5, 0, 0), 2 * f, phase + 0.35))
    a.rot("neck_2", Wave(v3(head_bob * 0.7, 0, 0), 2 * f, phase + 0.45))
    a.rot("mount_head", Wave(v3(-head_bob * 0.5, 0, 0), 2 * f, phase + 0.55))
    for i, nm in enumerate(("tail_1", "tail_2", "tail_3"), 1):
        if nm in a.rig.bones:
            a.rot(nm, Wave(v3(0, tail_swing * i / 2, 0), f, phase + 0.2 + 0.12 * i))


# ====================================================================================== strike builders
def strike_keys(rest, wind, hit, follow=None, t0=0.0, t_wind=0.5, t_hit=0.95, t_settle=None, t_end=2.0, lead=0.0,
                anticipate=True, wind_ease="in_out_cubic", hit_ease="snap_in", recover_ease="in_out_cubic", dip=0.18):
    """Key list for one channel: rest -> (anticipation dip) -> wind-up -> STRIKE arriving exactly at t_hit-lead -> hold
    (settle) -> optional follow-through -> recover to rest.  `lead` makes proximal joints peak slightly before the weapon
    (kinetic chain: pelvis lead .06, chest .03, arm 0).  The weapon channel must use lead=0 so impactTime stays exact."""
    rest, wind, hit = (np.asarray(v, dtype=np.float64) for v in (rest, wind, hit))
    keys = [(t0, rest)]
    if anticipate and t_wind - t0 > 0.12:
        keys.append((t0 + (t_wind - t0) * 0.45, rest - (wind - rest) * dip, "ease_in_out"))
    keys.append((t_wind - lead * 0.5, wind, wind_ease if not (anticipate and False) else "anticipate"))
    keys.append((t_hit - lead, hit, hit_ease))
    t_s = t_settle if t_settle is not None else t_hit + 0.12
    if follow is not None:
        f = np.asarray(follow, dtype=np.float64)
        keys.append((t_hit - lead + 0.06, hit + (f - hit) * 0.25, "out_quad"))
        keys.append((t_s, f, "out_cubic"))
    else:
        keys.append((t_s, hit, {"tan": "flat"}))
    keys.append((t_end, rest, recover_ease))
    return keys


# ====================================================================================== weapon release
def release_weapon(a, bone, t0, floor_y, rest_y_off, axis_local, heading, land_xz=None, grav=9.8, restitution=0.34, bounces=2,
                   roll_deg=140.0, kick=(0.0, 0.0, 0.0), up_local=None):
    """From `t0` the held-weapon bone leaves the hand: free fall, `bounces` bounces, comes to rest on the plinth with its long
    axis (`axis_local`, rest-frame direction of the weapon's axis) pointing along the horizontal `heading`.  Call AFTER all
    other tracks of the clip exist (it samples the pose at t0).  `up_local`: rest-frame direction (e.g. a blade's thickness
    axis) that should end up vertical, so flat weapons lie FLAT instead of standing on edge.  Registers a world override on `bone`."""
    sk = a.sk
    ib = sk.ix[a.rig.resolve(bone)]
    c0 = a.pose(t0, overrides=False)
    R0, pa = c0.Rw[ib].copy(), c0.Pw[ib].copy()
    a0 = R0 @ np.asarray(axis_local, dtype=np.float64)
    d_h = np.asarray(heading, dtype=np.float64)
    d_h = d_h / np.linalg.norm(d_h)
    R_align = rot_between(a0, d_h)
    rv = rotvec(R_align)
    yf = floor_y + rest_y_off
    pf = np.array([pa[0], yf, pa[2]]) if land_xz is None else np.array([land_xz[0], yf, land_xz[1]])
    h = max(pa[1] - yf, 0.02)
    t_fall = math.sqrt(2 * h / grav)
    v = grav * t_fall
    impacts = [t0 + t_fall]
    arcs = []
    for k in range(bounces):
        vb = v * restitution ** (k + 1)
        dur = 2 * vb / grav
        arcs.append((impacts[-1], impacts[-1] + dur, vb))
        impacts.append(impacts[-1] + dur)
    t_land = impacts[-1]
    s_at = [0.78, 0.94, 1.0, 1.0][: len(impacts)]
    kick = np.asarray(kick, dtype=np.float64)
    phi = 0.0
    if up_local is not None:
        n_end = from_rotvec(rv) @ R0 @ np.asarray(up_local, dtype=np.float64)
        n_p = n_end - np.dot(n_end, d_h) * d_h
        y_p = np.array([0.0, 1.0, 0.0]) - d_h[1] * d_h
        n_p, y_p = n_p / np.linalg.norm(n_p), y_p / np.linalg.norm(y_p)
        ang = math.degrees(math.atan2(float(np.dot(np.cross(n_p, y_p), d_h)), float(np.dot(n_p, y_p))))
        if abs(ang) > 90:                                   # either face may point up: take the shorter twist
            n_p = -n_p
            ang = math.degrees(math.atan2(float(np.dot(np.cross(n_p, y_p), d_h)), float(np.dot(n_p, y_p))))
        phi = ang
        roll_deg = 0.0

    def sm(u):
        u = min(max(u, 0.0), 1.0)
        return u * u * (3 - 2 * u)

    def fn(t):
        if t < t0:
            return None
        if t < impacts[0]:
            tt = t - t0
            y = pa[1] - 0.5 * grav * tt * tt
            u = (t - t0) / max(impacts[0] - t0, 1e-6)
            s = s_at[0] * (u ** 1.4)
        else:
            y, s = yf, 1.0
            for k, (ta, tb, vb) in enumerate(arcs):
                if ta <= t < tb:
                    tt = t - ta
                    y = yf + vb * tt - 0.5 * grav * tt * tt
                    u = (t - ta) / max(tb - ta, 1e-6)
                    s = s_at[k] + (s_at[k + 1] - s_at[k]) * sm(u)
                    break
        horiz = min(1.0, (t - t0) / max(t_land - t0, 1e-6))
        horiz = horiz * (2 - horiz)
        pos = np.array([pa[0] + (pf[0] - pa[0]) * horiz + kick[0] * (t - t0), y, pa[2] + (pf[2] - pa[2]) * horiz + kick[2] * (t - t0)])
        R = from_rotvec(rv * s) @ R0
        if phi:
            R = axis_angle(d_h, phi * s) @ R
        if roll_deg and s > 0:
            R = axis_angle(d_h, roll_deg * s) @ R
        return R, pos
    a.override(bone, fn)
    return t_land


# ====================================================================================== authoring helpers
def abs_pos(rest, sig):
    """Author an IK target as an ABSOLUTE point (as if the body were in its rest pose) instead of a delta from the rest joint."""
    rest = np.asarray(rest, dtype=np.float64)
    s = sig if isinstance(sig, Sig) else Curve(sig)
    return Fn(lambda t: s(t) - rest)


def aim(axis_rest, dir_sig):
    """Goal.rot helper: rotation (3x3) taking the weapon's rest axis onto the direction curve `dir_sig(t)` (shortest arc)."""
    ax = np.asarray(axis_rest, dtype=np.float64)
    ax = ax / np.linalg.norm(ax)
    s = dir_sig if isinstance(dir_sig, Sig) else Curve(dir_sig)

    def f(t):
        d = np.asarray(s(t), dtype=np.float64)
        return rot_between(ax, d / max(np.linalg.norm(d), 1e-9))
    return Fn(f)


def blade_roll(R_fn, axis_rest, roll_sig):
    """Add a roll (deg about the blade axis, in the world) to an `aim` rotation signal."""
    ax = np.asarray(axis_rest, dtype=np.float64)
    ax = ax / np.linalg.norm(ax)
    s = roll_sig if isinstance(roll_sig, Sig) else Curve(roll_sig)

    def f(t):
        R = R_fn(t)
        d = R @ ax
        return axis_angle(d, float(np.asarray(s(t)).ravel()[0])) @ R
    return Fn(f)
