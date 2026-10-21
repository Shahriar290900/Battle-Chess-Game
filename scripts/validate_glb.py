#!/usr/bin/env python3
"""Validate battle-chess GLB assets against the asset contract (contract version 1).

Usage:
    python validate_glb.py <file.glb | directory> [--stage blockout|final] [--json]

Checks (see references/asset-pipeline.md section 1):
  * file naming  {faction}_{role}.glb  /  {faction}_{role}_fragments.glb
  * root node named after the asset id, with required extras
  * required bones, sockets, LOD meshes, animation clips
  * triangle budgets, texture sizes (PNG/JPEG/KTX2), pedestal at origin, height range
  * fragment files: root + frag_### children, count and triangle budget

No third-party dependencies. Exit code 1 if any asset has errors.
"""
import argparse
import json
import math
import os
import re
import struct
import sys

CONTRACT_VERSION = 1
FACTIONS = ("emberhold", "rime")
ROLES = ("pawn", "rook", "knight", "bishop", "queen", "king")
CLIPS = ("Idle", "Move", "Attack", "HitReact", "Victory")
BASE_BONES = ("root", "body", "top")
HUMANOID_BONES = ("spine", "head", "arm_L", "hand_L", "arm_R", "hand_R")
MOUNT_BONES = ("mount_body", "mount_head")
BASE_SOCKETS = ("socket_weapon_R", "socket_impact", "socket_head")
EXTRAS_KEYS = ("faction", "role", "displayName", "impactTime", "strikeRange", "attackStyle", "contractVersion")
ATTACK_STYLES = ("melee", "leap", "ranged", "slam", "summon")
HEIGHTS = {"pawn": 1.05, "rook": 1.20, "knight": 1.30, "bishop": 1.40, "queen": 1.55, "king": 1.70}
LOD0_BUDGET = {"pawn": 15000, "rook": 18000, "bishop": 22000, "queen": 30000, "king": 30000, "knight": 35000}
LOD1_BUDGET = {"pawn": 4000, "rook": 5000, "bishop": 6000, "queen": 8000, "king": 8000, "knight": 9000}
BLOCKOUT_TRI_CAP = 60000
FRAGMENT_TRI_BUDGET = 6000
MAX_TEXTURE = 2048
NAME_RE = re.compile(r"^(emberhold|rime)_(pawn|rook|knight|bishop|queen|king)(_fragments)?\.glb$")


# ---------------------------------------------------------------- GLB parsing
def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 20:
        raise ValueError("file too small to be GLB")
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError("not a GLB (bad magic)")
    if version != 2:
        raise ValueError(f"glTF version {version}, expected 2")
    offset, gltf, binchunk = 12, None, b""
    while offset < min(length, len(data)):
        clen, ctype = struct.unpack_from("<I4s", data, offset)
        chunk = data[offset + 8: offset + 8 + clen]
        if ctype == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            binchunk = chunk
        offset += 8 + clen
    if gltf is None:
        raise ValueError("GLB has no JSON chunk")
    return gltf, binchunk


# ---------------------------------------------------------------- math helpers
def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def node_matrix(node):
    if "matrix" in node:
        m = node["matrix"]  # column-major
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    tx, ty, tz = node.get("translation", [0, 0, 0])
    qx, qy, qz, qw = node.get("rotation", [0, 0, 0, 1])
    sx, sy, sz = node.get("scale", [1, 1, 1])
    r = [
        [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
        [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
        [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
    ]
    return [
        [r[0][0] * sx, r[0][1] * sy, r[0][2] * sz, tx],
        [r[1][0] * sx, r[1][1] * sy, r[1][2] * sz, ty],
        [r[2][0] * sx, r[2][1] * sy, r[2][2] * sz, tz],
        [0, 0, 0, 1],
    ]


def transform_point(m, p):
    return [sum(m[i][j] * (p[j] if j < 3 else 1.0) for j in range(4)) for i in range(3)]


IDENTITY = [[1 if i == j else 0 for j in range(4)] for i in range(4)]


# ---------------------------------------------------------------- scene helpers
class Scene:
    def __init__(self, gltf, binchunk):
        self.g, self.bin = gltf, binchunk
        self.nodes = gltf.get("nodes", [])
        self.parent = {}
        for i, n in enumerate(self.nodes):
            for c in n.get("children", []):
                self.parent[c] = i
        scene_idx = gltf.get("scene", 0)
        scenes = gltf.get("scenes", [])
        self.roots = scenes[scene_idx].get("nodes", []) if scenes else [
            i for i in range(len(self.nodes)) if i not in self.parent]
        self.world = {}

    def name(self, i):
        return self.nodes[i].get("name", f"<node {i}>")

    def find(self, name):
        for i, n in enumerate(self.nodes):
            if n.get("name") == name:
                return i
        return None

    def descendants(self, i):
        out, stack = [], list(self.nodes[i].get("children", []))
        while stack:
            c = stack.pop()
            out.append(c)
            stack.extend(self.nodes[c].get("children", []))
        return out

    def world_matrix(self, i):
        if i not in self.world:
            local = node_matrix(self.nodes[i])
            p = self.parent.get(i)
            self.world[i] = local if p is None else mat_mul(self.world_matrix(p), local)
        return self.world[i]

    def mesh_tris(self, mesh_idx):
        tris = 0
        for prim in self.g["meshes"][mesh_idx].get("primitives", []):
            mode = prim.get("mode", 4)
            if "indices" in prim:
                count = self.g["accessors"][prim["indices"]]["count"]
            else:
                count = self.g["accessors"][prim["attributes"]["POSITION"]]["count"]
            if mode == 4:
                tris += count // 3
            elif mode in (5, 6):
                tris += max(0, count - 2)
        return tris

    def mesh_bounds(self, node_idx, use_world=True):
        node = self.nodes[node_idx]
        if "mesh" not in node:
            return None
        # glTF ignores the transform of a skinned mesh node; vertices are in skeleton space.
        m = IDENTITY if ("skin" in node or not use_world) else self.world_matrix(node_idx)
        lo, hi = [math.inf] * 3, [-math.inf] * 3
        for prim in self.g["meshes"][node["mesh"]].get("primitives", []):
            acc = self.g["accessors"][prim["attributes"]["POSITION"]]
            if "min" not in acc or "max" not in acc:
                continue
            mn, mx = acc["min"], acc["max"]
            for x in (mn[0], mx[0]):
                for y in (mn[1], mx[1]):
                    for z in (mn[2], mx[2]):
                        p = transform_point(m, [x, y, z])
                        for k in range(3):
                            lo[k], hi[k] = min(lo[k], p[k]), max(hi[k], p[k])
        return None if lo[0] == math.inf else (lo, hi)

    def image_sizes(self):
        out = []
        for i, img in enumerate(self.g.get("images", [])):
            if "bufferView" not in img:
                out.append((img.get("name", f"image{i}"), None, None, "external"))
                continue
            bv = self.g["bufferViews"][img["bufferView"]]
            start = bv.get("byteOffset", 0)
            raw = self.bin[start:start + bv["byteLength"]]
            out.append((img.get("name", f"image{i}"), *image_dims(raw)))
        return out


def image_dims(raw):
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", raw[16:24])
        return w, h, "png"
    if raw[:12] == b"\xabKTX 20\xbb\r\n\x1a\n":
        w, h = struct.unpack_from("<II", raw, 20)
        return w, h, "ktx2"
    if raw[:2] == b"\xff\xd8":
        i = 2
        while i < len(raw) - 9:
            if raw[i] != 0xFF:
                i += 1
                continue
            marker = raw[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", raw[i + 5:i + 9])
                return w, h, "jpeg"
            seglen = struct.unpack(">H", raw[i + 2:i + 4])[0]
            i += 2 + seglen
        return None, None, "jpeg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return None, None, "webp"
    return None, None, "unknown"


# ---------------------------------------------------------------- checks
class Report:
    def __init__(self, path):
        self.path, self.errors, self.warnings, self.info = path, [], [], {}

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def check(self, cond, msg, hard=True):
        if not cond:
            (self.err if hard else self.warn)(msg)
        return cond


def validate_piece(sc, asset_id, faction, role, stage, r):
    final = stage == "final"
    root = sc.find(asset_id)
    if not r.check(root is not None, f"no node named '{asset_id}' (asset root)"):
        return
    r.check(root in sc.roots, f"'{asset_id}' should be a scene root node", hard=False)
    under = set(sc.descendants(root)) | {root}
    names = {sc.name(i): i for i in under}

    # extras
    extras = sc.nodes[root].get("extras", {}) or {}
    for k in EXTRAS_KEYS:
        r.check(k in extras, f"root extras missing '{k}'")
    if extras:
        r.info["extras"] = extras
        r.check(extras.get("faction") in (None, faction), f"extras.faction={extras.get('faction')!r}, expected {faction!r}")
        r.check(extras.get("role") in (None, role), f"extras.role={extras.get('role')!r}, expected {role!r}")
        if "attackStyle" in extras:
            r.check(extras["attackStyle"] in ATTACK_STYLES, f"extras.attackStyle must be one of {ATTACK_STYLES}")
        if "contractVersion" in extras:
            r.check(extras["contractVersion"] == CONTRACT_VERSION,
                    f"contractVersion {extras['contractVersion']} != {CONTRACT_VERSION}")
        sr = extras.get("strikeRange")
        if isinstance(sr, (int, float)):
            r.check(0.05 <= sr <= 2.0, f"strikeRange {sr} outside 0.05–2.0", hard=False)

    # bones
    skins = sc.g.get("skins", [])
    joint_names = {sc.name(j) for s in skins for j in s.get("joints", [])}
    r.check(bool(skins), "no skin/armature exported")
    need_bones = list(BASE_BONES)
    if role != "rook":
        need_bones += HUMANOID_BONES
    if role == "knight":
        need_bones += MOUNT_BONES
    missing = [b for b in need_bones if b not in joint_names]
    r.check(not missing, f"missing bones: {', '.join(missing)}")

    # sockets
    need_sockets = list(BASE_SOCKETS) + (["socket_cast"] if role == "bishop" else [])
    if role == "queen":
        need_sockets.append("weapon_summon")
    miss_s = [s for s in need_sockets if s not in names]
    r.check(not miss_s, f"missing sockets/nodes: {', '.join(miss_s)}")

    # LODs
    lod0, lod1 = names.get(f"{asset_id}_LOD0"), names.get(f"{asset_id}_LOD1")
    r.check(lod0 is not None and "mesh" in sc.nodes[lod0], f"missing mesh node '{asset_id}_LOD0'")
    r.check(lod1 is not None and "mesh" in sc.nodes[lod1], f"missing mesh node '{asset_id}_LOD1'", hard=final)
    if lod0 is not None and "mesh" in sc.nodes[lod0]:
        t0 = sc.mesh_tris(sc.nodes[lod0]["mesh"])
        r.info["lod0_tris"] = t0
        if final:
            r.check(t0 <= LOD0_BUDGET[role], f"LOD0 {t0} tris > budget {LOD0_BUDGET[role]}")
        else:
            r.check(t0 <= BLOCKOUT_TRI_CAP, f"LOD0 {t0} tris > blockout cap {BLOCKOUT_TRI_CAP}")
        b = sc.mesh_bounds(lod0)
        if b:
            lo, hi = b
            height = hi[1] - lo[1]
            r.info["bounds_min"], r.info["bounds_max"] = [round(v, 3) for v in lo], [round(v, 3) for v in hi]
            r.info["height"] = round(height, 3)
            r.check(abs(lo[1]) <= 0.02, f"pedestal bottom at y={lo[1]:.3f}, expected 0")
            cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
            r.check(abs(cx) <= 0.15 and abs(cz) <= 0.15, f"piece not centred (x={cx:.3f}, z={cz:.3f})", hard=False)
            target = HEIGHTS[role]
            r.check(abs(height - target) <= target * 0.15,
                    f"height {height:.2f} vs target {target:.2f} (±15 %)", hard=final)
            footprint = max(hi[0] - lo[0], hi[2] - lo[2])
            r.check(footprint <= 1.0, f"footprint {footprint:.2f} wider than one square", hard=False)
    if lod1 is not None and "mesh" in sc.nodes[lod1]:
        t1 = sc.mesh_tris(sc.nodes[lod1]["mesh"])
        r.info["lod1_tris"] = t1
        if final:
            r.check(t1 <= LOD1_BUDGET[role], f"LOD1 {t1} tris > budget {LOD1_BUDGET[role]}")

    # clips
    anims = {a.get("name"): a for a in sc.g.get("animations", [])}
    r.info["clips"] = sorted(k for k in anims if k)
    miss_c = [c for c in CLIPS if c not in anims]
    r.check(not miss_c, f"missing clips: {', '.join(miss_c)}")
    if "Attack" in anims and isinstance(extras.get("impactTime"), (int, float)):
        dur = clip_duration(sc, anims["Attack"])
        r.info["attack_duration"] = round(dur, 3)
        r.check(0 < extras["impactTime"] < dur, f"impactTime {extras['impactTime']} not inside Attack (0–{dur:.2f}s)")

    # textures + materials
    check_textures(sc, r, final)


def clip_duration(sc, anim):
    dur = 0.0
    for s in anim.get("samplers", []):
        acc = sc.g["accessors"][s["input"]]
        if "max" in acc:
            dur = max(dur, acc["max"][0])
    return dur


def check_textures(sc, r, final):
    sizes = sc.image_sizes()
    r.info["textures"] = [{"name": n, "w": w, "h": h, "fmt": f} for n, w, h, f in sizes]
    for n, w, h, f in sizes:
        if w and h:
            r.check(max(w, h) <= MAX_TEXTURE, f"texture '{n}' {w}x{h} > {MAX_TEXTURE}")
        if final and f not in ("ktx2",):
            r.warn(f"texture '{n}' is {f}; final assets should ship KTX2 (gltf-transform optimize)")
    if final:
        r.check(bool(sizes), "final asset has no textures (expected PBR texture set)")


def validate_fragments(sc, asset_id, stage, r):
    final = stage == "final"
    root_name = f"{asset_id}_fragments"
    root = sc.find(root_name)
    if not r.check(root is not None, f"no node named '{root_name}'"):
        return
    frags = [c for c in sc.nodes[root].get("children", []) if re.match(r"^frag_\d{3}$", sc.name(c))]
    r.info["fragments"] = len(frags)
    lo = 12 if final else 4
    r.check(lo <= len(frags) <= 40, f"{len(frags)} fragments (expected {lo}–40, named frag_###)")
    tris = sum(sc.mesh_tris(sc.nodes[f]["mesh"]) for f in frags if "mesh" in sc.nodes[f])
    r.info["fragment_tris"] = tris
    if final:
        r.check(tris <= FRAGMENT_TRI_BUDGET, f"fragments total {tris} tris > {FRAGMENT_TRI_BUDGET}")
    mats = {m.get("name", "") for m in sc.g.get("materials", [])}
    pref = "EH_" if asset_id.startswith("emberhold") else "RH_"
    r.check(f"{pref}Interior" in mats, f"no '{pref}Interior' material on fragment faces", hard=final)


def validate_file(path, stage):
    r = Report(path)
    fname = os.path.basename(path)
    m = NAME_RE.match(fname)
    if not m:
        r.err("file name must be {emberhold|rime}_{pawn|rook|knight|bishop|queen|king}[_fragments].glb")
        return r
    faction, role, is_frag = m.group(1), m.group(2), bool(m.group(3))
    asset_id = f"{faction}_{role}"
    r.info["asset_id"], r.info["kind"] = asset_id, "fragments" if is_frag else "piece"
    try:
        sc = Scene(*read_glb(path))
    except Exception as e:  # noqa: BLE001
        r.err(f"cannot parse GLB: {e}")
        return r
    if is_frag:
        validate_fragments(sc, asset_id, stage, r)
    else:
        validate_piece(sc, asset_id, faction, role, stage, r)
    return r


def collect(target):
    if os.path.isdir(target):
        return sorted(os.path.join(target, f) for f in os.listdir(target) if f.lower().endswith(".glb"))
    return [target]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="GLB file or directory of GLBs")
    ap.add_argument("--stage", choices=("blockout", "final"), default="blockout")
    ap.add_argument("--json", action="store_true", help="machine-readable output (includes extras for sidecars)")
    ap.add_argument("--expect-all", action="store_true", help="also fail if any of the 24 expected files is missing")
    a = ap.parse_args(argv)

    files = collect(a.target)
    reports = [validate_file(f, a.stage) for f in files]
    missing = []
    if a.expect_all and os.path.isdir(a.target):
        have = {os.path.basename(f) for f in files}
        missing = [f"{fa}_{ro}{suf}.glb" for fa in FACTIONS for ro in ROLES for suf in ("", "_fragments")
                   if f"{fa}_{ro}{suf}.glb" not in have]

    failed = any(r.errors for r in reports) or bool(missing)
    if a.json:
        print(json.dumps({"stage": a.stage, "ok": not failed, "missing": missing,
                          "assets": [{"file": r.path, "ok": not r.errors, "errors": r.errors,
                                      "warnings": r.warnings, **r.info} for r in reports]}, indent=2))
    else:
        for r in reports:
            status = "PASS" if not r.errors else "FAIL"
            extra = ""
            if "lod0_tris" in r.info:
                extra = f"  LOD0 {r.info['lod0_tris']} tris, h={r.info.get('height', '?')}"
            elif "fragments" in r.info:
                extra = f"  {r.info['fragments']} fragments"
            print(f"[{status}] {os.path.basename(r.path)}{extra}")
            for e in r.errors:
                print(f"    ERROR   {e}")
            for w in r.warnings:
                print(f"    warning {w}")
        if missing:
            print(f"Missing files ({len(missing)}): {', '.join(missing)}")
        n_ok = sum(1 for r in reports if not r.errors)
        print(f"\n{n_ok}/{len(reports)} passed  (stage: {a.stage})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
