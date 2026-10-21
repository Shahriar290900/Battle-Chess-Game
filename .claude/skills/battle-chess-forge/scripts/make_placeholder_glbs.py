#!/usr/bin/env python3
"""Generate 24 contract-valid placeholder GLBs (12 pieces + 12 fragment sets).

These are crude, rigidly-skinned primitive figures with every bone, socket, clip and
extra the asset contract requires. They exist so the engine, cinematics and VFX agents
can start Phase 2 before the Blender assets are ready. Replace them with real exports.

Usage:  python make_placeholder_glbs.py --out assets/models
No third-party dependencies.
"""
import argparse
import json
import math
import os
import struct

ROLES = ("pawn", "rook", "knight", "bishop", "queen", "king")
HEIGHT = {"pawn": 1.05, "rook": 1.20, "knight": 1.30, "bishop": 1.40, "queen": 1.55, "king": 1.70}
DISPLAY = {
    ("emberhold", "pawn"): "Emberhold Shieldbearer", ("rime", "pawn"): "Rime Thrall",
    ("emberhold", "rook"): "Emberhold Forge Bastion", ("rime", "rook"): "Rime Glacier Bastion",
    ("emberhold", "knight"): "Emberhold Ashmane Rider", ("rime", "knight"): "Rime Gravewind Rider",
    ("emberhold", "bishop"): "Emberhold Cinder Oracle", ("rime", "bishop"): "Rime Frost Chanter",
    ("emberhold", "queen"): "Emberhold Flamecrown Warden", ("rime", "queen"): "Rime Pale Tide Queen",
    ("emberhold", "king"): "Emberhold Ember Sovereign", ("rime", "king"): "Rime Glacier Tyrant",
}
ATTACK = {  # role: (attackStyle, impactTime, attackDuration, strikeRange)
    "pawn": ("melee", 0.95, 1.6, 0.55), "rook": ("slam", 0.75, 1.4, 0.10),
    "knight": ("leap", 1.00, 1.8, 0.50), "bishop": ("ranged", 1.10, 1.8, 1.50),
    "queen": ("summon", 1.30, 2.2, 0.70), "king": ("melee", 1.20, 2.0, 0.60),
}
PALETTE = {  # base, accent, interior(emissive)
    "emberhold": ((0.66, 0.44, 0.23), (1.0, 0.48, 0.10), (1.0, 0.45, 0.08)),
    "rime": ((0.06, 0.08, 0.11), (0.50, 0.83, 0.94), (0.75, 0.93, 1.0)),
}
PED_H = 0.22


# ------------------------------------------------------------------ geometry
def _box(c, s):
    cx, cy, cz = c
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    faces = [((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
             ((-1, 0, 0), [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)]),
             ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]),
             ((0, -1, 0), [(-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)]),
             ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
             ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)])]
    P, N, I = [], [], []
    for n, quad in faces:
        b = len(P)
        for sx, sy, sz in quad:
            P.append((cx + sx * hx, cy + sy * hy, cz + sz * hz))
            N.append(n)
        I += [b, b + 1, b + 2, b, b + 2, b + 3]
    return P, N, I


def _frustum(c, r0, r1, h, seg=16):
    """Capped cylinder/cone frustum standing on c (base centre), along +Y."""
    cx, cy, cz = c
    P, N, I = [], [], []
    slope = (r0 - r1) / h if h else 0
    for i in range(seg + 1):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        n = (ca, slope, sa)
        ln = math.sqrt(sum(v * v for v in n))
        n = tuple(v / ln for v in n)
        P += [(cx + r0 * ca, cy, cz + r0 * sa), (cx + r1 * ca, cy + h, cz + r1 * sa)]
        N += [n, n]
    for i in range(seg):
        a, b, c2, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        I += [a, b, d, a, d, c2]
    for y, r, ny in ((cy, r0, -1), (cy + h, r1, 1)):
        if r <= 1e-4:
            continue
        ctr = len(P)
        P.append((cx, y, cz))
        N.append((0, ny, 0))
        for i in range(seg):
            a = 2 * math.pi * i / seg
            P.append((cx + r * math.cos(a), y, cz + r * math.sin(a)))
            N.append((0, ny, 0))
        for i in range(seg):
            j = ctr + 1 + i
            k = ctr + 1 + (i + 1) % seg
            I += [ctr, k, j] if ny > 0 else [ctr, j, k]
    return P, N, I


def _sphere(c, r, lat=8, lon=12):
    P, N, I = [], [], []
    for i in range(lat + 1):
        t = math.pi * i / lat
        for j in range(lon + 1):
            p = 2 * math.pi * j / lon
            n = (math.sin(t) * math.cos(p), math.cos(t), math.sin(t) * math.sin(p))
            P.append(tuple(c[k] + r * n[k] for k in range(3)))
            N.append(n)
    for i in range(lat):
        for j in range(lon):
            a = i * (lon + 1) + j
            b = a + lon + 1
            I += [a, a + 1, b, a + 1, b + 1, b]
    return P, N, I


def _between(a, b, w):
    """Thin box from point a to point b (approximate limb), axis-aligned on the dominant axis."""
    c = tuple((a[k] + b[k]) / 2 for k in range(3))
    s = [max(abs(b[k] - a[k]), w) for k in range(3)]
    return _box(c, s)


# ------------------------------------------------------------------ piece builders
class Piece:
    def __init__(self, faction, role):
        self.faction, self.role = faction, role
        self.bones = {}     # name -> (parent, absolute pos)
        self.order = []
        self.parts = []     # (geom, bone, material 0 base / 1 accent)
        self.sockets = {}   # name -> (bone, absolute pos)
        self.summon = None  # (geom relative to hand_R, bone)

    def bone(self, name, parent, pos):
        self.bones[name] = (parent, pos)
        self.order.append(name)

    def part(self, geom, bone, mat=0):
        self.parts.append((geom, bone, mat))


def build_humanoid(p, y0, f, crown=False, weapon="sword", offhand=None):
    """Rigid humanoid standing at height y0 with figure height f."""
    Y = lambda t: y0 + t * f
    p.bone("body", "root", (0, Y(0.42), 0))
    p.bone("spine", "body", (0, Y(0.60), 0))
    p.bone("head", "spine", (0, Y(0.86), 0))
    p.bone("top", "head", (0, Y(1.0), 0))
    sh, hd = 0.17 * f, 0.19 * f
    p.bone("arm_L", "spine", (-sh, Y(0.80), 0))
    p.bone("hand_L", "arm_L", (-hd, Y(0.50), 0.03 * f))
    p.bone("arm_R", "spine", (sh, Y(0.80), 0))
    p.bone("hand_R", "arm_R", (hd, Y(0.50), 0.03 * f))
    p.part(_box((-0.06 * f, (y0 + Y(0.42)) / 2, 0), (0.09 * f, 0.42 * f, 0.10 * f)), "body")
    p.part(_box((0.06 * f, (y0 + Y(0.42)) / 2, 0), (0.09 * f, 0.42 * f, 0.10 * f)), "body")
    p.part(_frustum((0, Y(0.40), 0), 0.13 * f, 0.16 * f, 0.42 * f, 12), "spine")
    p.part(_sphere((0, Y(0.92), 0), 0.085 * f), "head")
    for side, s in (("L", -1), ("R", 1)):
        p.part(_between((s * sh, Y(0.80), 0), (s * hd, Y(0.52), 0.03 * f), 0.06 * f), f"arm_{side}")
        p.part(_box((s * hd, Y(0.50), 0.03 * f), (0.06 * f, 0.06 * f, 0.06 * f)), f"hand_{side}", 1)
    if crown:
        for i in range(6):
            a = 2 * math.pi * i / 6
            p.part(_frustum((0.06 * f * math.cos(a), Y(0.97), 0.06 * f * math.sin(a)), 0.018 * f, 0.0, 0.07 * f, 6), "top", 1)
    tip = (hd, Y(0.50), 0.03 * f)
    if weapon == "sword":
        L = 0.42 * f
        p.part(_box((hd, Y(0.50) + L / 2, 0.03 * f), (0.025 * f, L, 0.05 * f)), "hand_R", 1)
        tip = (hd, Y(0.50) + L, 0.03 * f)
    elif weapon == "lance":
        L = 0.7 * f
        p.part(_frustum((hd, Y(0.40), 0.03 * f), 0.018 * f, 0.004, L, 8), "hand_R", 1)
        tip = (hd, Y(0.40) + L, 0.03 * f)
    p.sockets["socket_weapon_R"] = ("hand_R", tip)
    p.sockets["socket_head"] = ("head", (0, Y(1.02), 0))
    if offhand == "shield":
        p.part(_box((-hd - 0.02 * f, Y(0.52), 0.07 * f), (0.30 * f, 0.34 * f, 0.03 * f)), "hand_L", 1)
    elif offhand == "staff":
        L = 0.95 * f
        p.part(_frustum((-hd, Y(0.10), 0.03 * f), 0.015 * f, 0.015 * f, L, 8), "hand_L", 0)
        p.part(_sphere((-hd, Y(0.10) + L + 0.04 * f, 0.03 * f), 0.05 * f), "hand_L", 1)
        p.sockets["socket_cast"] = ("hand_L", (-hd, Y(0.10) + L + 0.04 * f, 0.03 * f))


def build_piece(faction, role):
    p = Piece(faction, role)
    H = HEIGHT[role]
    p.bone("root", None, (0, 0, 0))
    p.part(_frustum((0, 0, 0), 0.40, 0.33, PED_H, 24), "root")
    p.part(_frustum((0, PED_H - 0.03, 0), 0.345, 0.345, 0.02, 24), "root", 1)
    if role == "rook":
        p.bone("body", "root", (0, PED_H, 0))
        p.bone("top", "body", (0, H - 0.18, 0))
        p.part(_frustum((0, PED_H, 0), 0.30, 0.26, H - 0.18 - PED_H, 16), "body")
        p.part(_frustum((0, H - 0.18, 0), 0.31, 0.31, 0.06, 16), "top", 1)
        for i in range(6):
            a = 2 * math.pi * i / 6
            p.part(_box((0.24 * math.cos(a), H - 0.06, 0.24 * math.sin(a)), (0.09, 0.12, 0.09)), "top")
        p.sockets["socket_weapon_R"] = ("top", (0, H, 0.25))
        p.sockets["socket_head"] = ("top", (0, H, 0))
    elif role == "knight":
        p.bone("mount_body", "root", (0, 0.45, 0))
        p.bone("mount_head", "mount_body", (0, 0.66, 0.26))
        p.part(_box((0, 0.48, -0.02), (0.22, 0.20, 0.52)), "mount_body")
        for x in (-0.08, 0.08):
            for z in (-0.20, 0.16):
                p.part(_box((x, (PED_H + 0.40) / 2, z), (0.06, 0.40 - PED_H, 0.06)), "mount_body")
        p.part(_box((0, 0.68, 0.30), (0.12, 0.26, 0.12)), "mount_head")
        p.part(_box((0, 0.76, 0.40), (0.10, 0.10, 0.18)), "mount_head", 1)
        build_humanoid(p, 0.56, H - 0.56, weapon="lance")
        p.bones["body"] = ("mount_body", p.bones["body"][1])
    else:
        f = H - PED_H
        build_humanoid(
            p, PED_H, f,
            crown=role in ("queen", "king"),
            weapon={"pawn": "sword", "bishop": None, "queen": None, "king": "sword"}[role],
            offhand={"pawn": "shield", "bishop": "staff"}.get(role),
        )
        if role == "queen":
            hy = p.bones["hand_R"][1]
            L = 1.1 * f
            p.summon = _frustum((hy[0], hy[1] - 0.3 * f, hy[2]), 0.03 * f, 0.02 * f, L, 10)
            p.sockets["socket_weapon_R"] = ("hand_R", (hy[0], hy[1] - 0.3 * f + L, hy[2]))
    p.sockets["socket_impact"] = ("root", (0, PED_H + 0.4 * (H - PED_H), 0.45))
    return p


# ------------------------------------------------------------------ glTF writer
class GLB:
    def __init__(self):
        self.bin = bytearray()
        self.g = {"asset": {"version": "2.0", "generator": "battle-chess-forge placeholder"},
                  "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "materials": [],
                  "accessors": [], "bufferViews": [], "buffers": [{"byteLength": 0}]}

    def _view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        off = len(self.bin)
        self.bin += data
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        self.g["bufferViews"].append(v)
        return len(self.g["bufferViews"]) - 1

    def accessor(self, values, ctype, typ, target=None, minmax=False, normalized=False):
        fmt = {5126: "f", 5123: "H", 5125: "I", 5121: "B"}[ctype]
        comps = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}[typ]
        flat = [x for v in values for x in (v if isinstance(v, (tuple, list)) else (v,))]
        view = self._view(struct.pack(f"<{len(flat)}{fmt}", *flat), target)
        acc = {"bufferView": view, "componentType": ctype, "count": len(values), "type": typ}
        if normalized:
            acc["normalized"] = True
        if minmax:
            cols = [flat[i::comps] for i in range(comps)]
            acc["min"], acc["max"] = [min(c) for c in cols], [max(c) for c in cols]
        self.g["accessors"].append(acc)
        return len(self.g["accessors"]) - 1

    def material(self, name, rgb, metal, rough, emissive=None):
        m = {"name": name, "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [*rgb, 1.0],
                                                     "metallicFactor": metal, "roughnessFactor": rough}}
        if emissive:
            m["emissiveFactor"] = list(emissive)
        self.g["materials"].append(m)
        return len(self.g["materials"]) - 1

    def node(self, **kw):
        self.g["nodes"].append({k: v for k, v in kw.items() if v is not None})
        return len(self.g["nodes"]) - 1

    def mesh(self, name, prims):
        """prims: list of (P, N, I, material, joints or None)."""
        out = []
        for P, N, I, mat, joints in prims:
            attrs = {"POSITION": self.accessor(P, 5126, "VEC3", 34962, minmax=True),
                     "NORMAL": self.accessor(N, 5126, "VEC3", 34962)}
            if joints is not None:
                attrs["JOINTS_0"] = self.accessor([(j, 0, 0, 0) for j in joints], 5121, "VEC4", 34962)
                attrs["WEIGHTS_0"] = self.accessor([(1.0, 0.0, 0.0, 0.0)] * len(joints), 5126, "VEC4", 34962)
            ctype = 5123 if len(P) < 65535 else 5125
            out.append({"attributes": attrs, "indices": self.accessor(I, ctype, "SCALAR", 34963),
                        "material": mat})
        self.g["meshes"].append({"name": name, "primitives": out})
        return len(self.g["meshes"]) - 1

    def write(self, path):
        self.g["buffers"][0]["byteLength"] = len(self.bin)
        js = json.dumps(self.g, separators=(",", ":")).encode()
        js += b" " * ((4 - len(js) % 4) % 4)
        b = bytes(self.bin) + b"\x00" * ((4 - len(self.bin) % 4) % 4)
        total = 12 + 8 + len(js) + 8 + len(b)
        with open(path, "wb") as fh:
            fh.write(struct.pack("<4sII", b"glTF", 2, total))
            fh.write(struct.pack("<I4s", len(js), b"JSON") + js)
            fh.write(struct.pack("<I4s", len(b), b"BIN\x00") + b)


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def merge(parts, bone_index=None):
    """Merge geometry parts -> (P, N, I, joints)."""
    P, N, I, J = [], [], [], []
    for (gp, gn, gi), bone in parts:
        base = len(P)
        P += gp
        N += gn
        I += [base + i for i in gi]
        J += [bone_index[bone] if bone_index else 0] * len(gp)
    return P, N, I, J


def decimate_like(parts):
    """LOD1 placeholder: drop accent-only parts and reuse coarse geometry."""
    return [pt for pt in parts if pt[2] == 0 or pt[1] in ("root",)]


def quat_x(a):
    return (math.sin(a / 2), 0.0, 0.0, math.cos(a / 2))


def quat_z(a):
    return (0.0, 0.0, math.sin(a / 2), math.cos(a / 2))


def write_piece(p, out_dir):
    faction, role = p.faction, p.role
    asset = f"{faction}_{role}"
    style, impact, dur, strike = ATTACK[role]
    pre = "EH" if faction == "emberhold" else "RH"
    base_rgb, acc_rgb, _ = PALETTE[faction]
    g = GLB()
    mats = [g.material(f"{pre}_Base", base_rgb, 0.7 if faction == "emberhold" else 0.2, 0.4),
            g.material(f"{pre}_Accent", acc_rgb, 0.6, 0.3, emissive=tuple(c * 0.6 for c in acc_rgb))]

    # bones -> nodes
    bone_node, bone_index = {}, {}
    for i, name in enumerate(p.order):
        bone_index[name] = i
    for name in p.order:
        parent, pos = p.bones[name]
        rel = pos if parent is None else sub(pos, p.bones[parent][1])
        bone_node[name] = g.node(name=name, translation=list(rel))
    for name in p.order:
        parent = p.bones[name][0]
        if parent:
            g.g["nodes"][bone_node[parent]].setdefault("children", []).append(bone_node[name])
    # sockets
    for sname, (bone, pos) in p.sockets.items():
        n = g.node(name=sname, translation=list(sub(pos, p.bones[bone][1])))
        g.g["nodes"][bone_node[bone]].setdefault("children", []).append(n)
    summon_node = None
    if p.summon:
        hand = p.bones["hand_R"][1]
        sp, sn, si = p.summon
        sp = [sub(v, hand) for v in sp]
        m = g.mesh("weapon_summon", [(sp, sn, si, mats[1], None)])
        summon_node = g.node(name="weapon_summon", mesh=m, scale=[0.0, 0.0, 0.0])
        g.g["nodes"][bone_node["hand_R"]].setdefault("children", []).append(summon_node)

    ibm = []
    for name in p.order:
        x, y, z = p.bones[name][1]
        ibm.append((1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1))  # column-major
    ibm_acc = g.accessor(ibm, 5126, "MAT4")
    g.g["skins"] = [{"name": "rig", "joints": [bone_node[n] for n in p.order],
                     "skeleton": bone_node["root"], "inverseBindMatrices": ibm_acc}]

    def lod_mesh(name, parts):
        prims = []
        for mi in (0, 1):
            sel = [((gp, gn, gi), b) for (gp, gn, gi), b, m in parts if m == mi]
            if sel:
                P, N, I, J = merge(sel, bone_index)
                prims.append((P, N, I, mats[mi], J))
        return g.mesh(name, prims)

    lod0 = g.node(name=f"{asset}_LOD0", mesh=lod_mesh(f"{asset}_LOD0", p.parts), skin=0)
    lod1 = g.node(name=f"{asset}_LOD1", mesh=lod_mesh(f"{asset}_LOD1", decimate_like(p.parts)), skin=0)
    rig = g.node(name="rig", children=[bone_node["root"]])
    root = g.node(name=asset, children=[rig, lod0, lod1], extras={
        "faction": faction, "role": role, "displayName": DISPLAY[(faction, role)],
        "impactTime": impact, "strikeRange": strike, "attackStyle": style,
        "contractVersion": 1, "placeholder": True})
    g.g["scenes"][0]["nodes"] = [root]

    # ---------------------------------------------------------------- clips
    anims = []

    def clip(name, tracks):
        samplers, channels = [], []
        for node_name, path, times, values in tracks:
            node = summon_node if node_name == "weapon_summon" else bone_node[node_name]
            typ = "VEC4" if path == "rotation" else "VEC3"
            samplers.append({"input": g.accessor(times, 5126, "SCALAR", minmax=True),
                             "output": g.accessor(values, 5126, typ), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": path}})
        anims.append({"name": name, "samplers": samplers, "channels": channels})

    def T(bone, d=(0, 0, 0)):
        parent, pos = p.bones[bone]
        rel = pos if parent is None else sub(pos, p.bones[parent][1])
        return tuple(rel[i] + d[i] for i in range(3))

    is_rook = role == "rook"
    summon_rest = ("weapon_summon", "scale", [0.0, 1.0], [(0, 0, 0), (0, 0, 0)]) if p.summon else None

    def with_summon(tracks):
        return tracks + ([summon_rest] if summon_rest else [])

    sway = "body" if is_rook else "spine"
    clip("Idle", with_summon([(sway, "rotation", [0, 1.5, 3.0], [quat_z(0.0), quat_z(0.03), quat_z(0.0)])]))
    clip("Move", with_summon([("body", "translation", [0, 0.2, 0.4, 0.6, 0.8],
                               [T("body"), T("body", (0, 0.04, 0)), T("body"), T("body", (0, 0.04, 0)), T("body")])]))
    if is_rook:
        att = [("body", "translation", [0, impact * 0.55, impact * 0.8, impact, dur],
                [T("body"), T("body", (0, 0.6, -0.05)), T("body", (0, 0.65, 0.1)), T("body", (0, -0.02, 0.15)), T("body")])]
        hit = [("body", "rotation", [0, 0.15, 0.4], [quat_x(0), quat_x(-0.25), quat_x(0)])]
        vic = [("top", "translation", [0, 0.5, 1.2], [T("top"), T("top", (0, 0.1, 0)), T("top")])]
    else:
        arm = "arm_R"
        att = [(arm, "rotation", [0, impact * 0.45, impact * 0.85, impact, impact + 0.25, dur],
                [quat_x(0), quat_x(2.6), quat_x(2.7), quat_x(-1.3), quat_x(-1.1), quat_x(0)]),
               ("body", "translation", [0, impact * 0.8, impact, dur],
                [T("body"), T("body", (0, 0, -0.05)), T("body", (0, 0, 0.15)), T("body")])]
        if role == "knight":
            att.append(("mount_body", "rotation", [0, impact * 0.4, impact, dur],
                        [quat_x(0), quat_x(-0.45), quat_x(0.15), quat_x(0)]))
        hit = [("body", "rotation", [0, 0.15, 0.45], [quat_x(0), quat_x(-0.35), quat_x(0)])]
        vic = [(arm, "rotation", [0, 0.5, 1.3, 1.6], [quat_x(0), quat_x(2.9), quat_x(2.9), quat_x(0)])]
    if p.summon:
        att.append(("weapon_summon", "scale", [0, 0.25, 0.4, dur - 0.2, dur],
                    [(0, 0, 0), (1.15, 1.15, 1.15), (1, 1, 1), (1, 1, 1), (0, 0, 0)]))
    clip("Attack", att)
    clip("HitReact", with_summon(hit))
    clip("Victory", with_summon(vic))
    g.g["animations"] = anims
    path = os.path.join(out_dir, f"{asset}.glb")
    g.write(path)
    return path


def write_fragments(faction, role, out_dir):
    asset = f"{faction}_{role}"
    pre = "EH" if faction == "emberhold" else "RH"
    base_rgb, _, inner = PALETTE[faction]
    H = HEIGHT[role]
    count = {"pawn": 20, "queen": 40, "king": 40}.get(role, 30)
    sectors = 5 if count == 20 else (6 if count == 30 else 8)
    rings = count // sectors
    g = GLB()
    m_base = g.material(f"{pre}_Base", base_rgb, 0.5, 0.45)
    m_int = g.material(f"{pre}_Interior", inner, 0.0, 0.6, emissive=inner)
    kids = []
    k = 0
    for ri in range(rings):
        y0, y1 = H * ri / rings, H * (ri + 1) / rings
        r = 0.38 if y1 <= PED_H + 0.01 else 0.22 * (1.0 - 0.3 * ri / rings)
        for si in range(sectors):
            a0, a1 = 2 * math.pi * si / sectors, 2 * math.pi * (si + 1) / sectors
            # wedge prism: outer face (base material) + inner faces (interior material)
            c0, c1 = (r * math.cos(a0), r * math.sin(a0)), (r * math.cos(a1), r * math.sin(a1))
            pts = [(0, y0, 0), (c0[0], y0, c0[1]), (c1[0], y0, c1[1]),
                   (0, y1, 0), (c0[0], y1, c0[1]), (c1[0], y1, c1[1])]
            cen = tuple(sum(v[i] for v in pts) / 6 for i in range(3))
            loc = [sub(v, cen) for v in pts]
            outer_n = (math.cos((a0 + a1) / 2), 0, math.sin((a0 + a1) / 2))
            Po = [loc[1], loc[2], loc[5], loc[4]]
            Pi = [loc[0], loc[1], loc[2], loc[3], loc[4], loc[5]]
            Ii = [0, 2, 1, 3, 4, 5, 0, 1, 4, 0, 4, 3, 0, 3, 5, 0, 5, 2]
            Ni = [(0, -1, 0)] * 3 + [(0, 1, 0)] * 3
            mesh = g.mesh(f"frag_{k:03d}", [(Po, [outer_n] * 4, [0, 2, 1, 0, 3, 2], m_base, None),
                                            (Pi, Ni, Ii, m_int, None)])
            kids.append(g.node(name=f"frag_{k:03d}", mesh=mesh, translation=list(cen)))
            k += 1
    root = g.node(name=f"{asset}_fragments", children=kids, extras={"placeholder": True})
    g.g["scenes"][0]["nodes"] = [root]
    path = os.path.join(out_dir, f"{asset}_fragments.glb")
    g.write(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="assets/models")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for faction in ("emberhold", "rime"):
        for role in ROLES:
            print(write_piece(build_piece(faction, role), a.out))
            print(write_fragments(faction, role, a.out))


if __name__ == "__main__":
    main()
