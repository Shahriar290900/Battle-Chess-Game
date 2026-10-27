"""templates.py - skeleton templates.  Bones are placed by ABSOLUTE rest-pose joint positions measured off your meshes.

    rig = humanoid_rig(J)                 # J: dict of joint positions (see HUMANOID_JOINTS); right side mirrored from left
    rig = quadruped_rig(J)                # mounts (knights)

Contract bones keep their meaning:  body = pelvis, spine/chest = torso, head, top = backpack/bedroll/rider seat node,
arm_L/R = UPPER ARM (pivot at the shoulder), hand_L/R = FOREARM (pivot at the ELBOW - legacy name), weapon = held weapon
(the thing Surrender drops), mount_body / mount_head for mounts.  New semantic bones carry the rest: clavicle_L, wrist_L
(the hand), thigh_L, shin_L, foot_L, toe_L, neck, cape_1..3, ...   Aliases (`rig.resolve`) let code say upper_arm_L / forearm_L / fist_L.

    HUMANOID_JOINTS = pelvis, spine, chest, neck, head, top, clavicle_L, shoulder_L, elbow_L, wrist_L, hip_L, knee_L, ankle_L, toe_L
    (…_R optional: defaults to the mirror of _L; pass explicit …_R for asymmetric rest poses)
"""
from __future__ import annotations

import numpy as np

from rig import Rig

HUMANOID_JOINTS = ("pelvis", "spine", "chest", "neck", "head", "top", "clavicle_L", "shoulder_L", "elbow_L", "wrist_L",
                   "hip_L", "knee_L", "ankle_L", "toe_L")


def _mir(p):
    p = np.asarray(p, dtype=np.float64)
    return np.array([-p[0], p[1], p[2]])


def humanoid_rig(J, weapon=None, shield=None, cape=None, weapon_parent="wrist_R", shield_parent="hand_L", top_parent="chest",
                 pelvis_name="body", aliases=True):
    """Build the humanoid skeleton.
    weapon: absolute position (centre of mass) of the `weapon` bone, parented to `weapon_parent` (use "body" for a sheathed sword).
    shield: absolute position of an optional `shield` bone under `shield_parent` (lets a spring rattle the shield).
    cape:   list of 2-3 absolute positions -> bones cape_1..cape_n (a hanging chain under `top`).
    Returns the Rig (not yet sockets)."""
    J = dict(J)
    for k in list(J):
        if k.endswith("_L") and k[:-1] + "R" not in J:
            J[k[:-1] + "R"] = _mir(J[k])
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add(pelvis_name, "root", J["pelvis"])
    r.add("spine", pelvis_name, J["spine"])
    r.add("chest", "spine", J["chest"])
    r.add("neck", "chest", J["neck"])
    r.add("head", "neck", J["head"])
    r.add("top", top_parent, J["top"])
    for s in "LR":
        r.add(f"clavicle_{s}", "chest", J[f"clavicle_{s}"])
        r.add(f"arm_{s}", f"clavicle_{s}", J[f"shoulder_{s}"])
        r.add(f"hand_{s}", f"arm_{s}", J[f"elbow_{s}"])
        r.add(f"wrist_{s}", f"hand_{s}", J[f"wrist_{s}"])
    for s in "LR":
        r.add(f"thigh_{s}", pelvis_name, J[f"hip_{s}"])
        r.add(f"shin_{s}", f"thigh_{s}", J[f"knee_{s}"])
        r.add(f"foot_{s}", f"shin_{s}", J[f"ankle_{s}"])
        r.add(f"toe_{s}", f"foot_{s}", J[f"toe_{s}"])
    if weapon is not None:
        r.add("weapon", weapon_parent, weapon)
    if shield is not None:
        r.add("shield", shield_parent, shield)
    if cape:
        prev = "top"
        for i, p in enumerate(cape, 1):
            r.add(f"cape_{i}", prev, p)
            prev = f"cape_{i}"
    if aliases:
        for s in "LR":
            r.add_alias(f"upper_arm_{s}", f"arm_{s}")
            r.add_alias(f"forearm_{s}", f"hand_{s}")
            r.add_alias(f"fist_{s}", f"wrist_{s}")
        r.add_alias("pelvis", pelvis_name)
    return r


QUAD_JOINTS = ("rump", "barrel", "withers", "neck_1", "neck_2", "head", "jaw", "seat",
               "hip_L", "hock_L", "fetlock_L", "hoof_L", "shoulder_L", "elbow_L", "fetlock_F_L", "hoof_F_L",
               "tail_1", "tail_2", "tail_3")


def quadruped_rig(J):
    """Mount skeleton for knights.  J = absolute rest joints (left side given, right mirrored):
        rump (-> `body`, hindquarters root), barrel (-> `mount_body`), withers (-> `mount_chest`), neck_1, neck_2,
        head (-> `mount_head`, pivot at the poll), jaw (optional), seat (-> `top`, the rider's saddle node),
        hip_L, hock_L, fetlock_L, hoof_L      hind leg: hind_upper (hip->hock), hind_lower (hock->fetlock), hind_hoof (fetlock->hoof tip)
        shoulder_L, elbow_L, fetlock_F_L, hoof_F_L   fore leg: fore_upper (shoulder->carpus `elbow_L`), fore_lower (carpus->fetlock), fore_hoof
        tail_1..tail_3 (optional chain under `body`).
    Hierarchy: root > body > mount_body > mount_chest > neck_1 > neck_2 > mount_head > jaw ; body > hind legs, tail ;
    mount_chest > fore legs ; mount_body > top.  Use `humanoid_rig(..., pelvis_name="rider_pelvis")` + re-parenting for riders."""
    J = dict(J)
    for k in list(J):
        if k.endswith("_L") and k[:-1] + "R" not in J:
            J[k[:-1] + "R"] = _mir(J[k])
    r = Rig()
    r.add("root", None, (0, 0, 0))
    r.add("body", "root", J["rump"])
    r.add("mount_body", "body", J["barrel"])
    r.add("mount_chest", "mount_body", J["withers"])
    r.add("neck_1", "mount_chest", J["neck_1"])
    r.add("neck_2", "neck_1", J["neck_2"])
    r.add("mount_head", "neck_2", J["head"])
    if "jaw" in J:
        r.add("jaw", "mount_head", J["jaw"])
    r.add("top", "mount_body", J["seat"])
    for s in "LR":
        r.add(f"hind_upper_{s}", "body", J[f"hip_{s}"])
        r.add(f"hind_lower_{s}", f"hind_upper_{s}", J[f"hock_{s}"])
        r.add(f"hind_hoof_{s}", f"hind_lower_{s}", J[f"fetlock_{s}"])
        r.add(f"fore_upper_{s}", "mount_chest", J[f"shoulder_{s}"])
        r.add(f"fore_lower_{s}", f"fore_upper_{s}", J[f"elbow_{s}"])
        r.add(f"fore_hoof_{s}", f"fore_lower_{s}", J[f"fetlock_F_{s}"])
    prev = "body"
    for i in (1, 2, 3):
        if f"tail_{i}" in J:
            r.add(f"tail_{i}", prev, J[f"tail_{i}"])
            prev = f"tail_{i}"
    return r
