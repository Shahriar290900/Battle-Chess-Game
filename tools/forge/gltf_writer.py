"""gltf_writer.py - dependency-light GLB writer (numpy only) for the code forge.

Supports: node hierarchy, skinned meshes (JOINTS_0/WEIGHTS_0 + inverse bind matrices), TRS animations
(LINEAR / STEP), root extras, PBR materials with embedded textures (baseColor, ORM, normal, emissive),
KHR_materials_emissive_strength / transmission / volume / ior, vertex colours (COLOR_0) and several
primitives (one per material) per mesh.

    g = GlbBuilder()
    m = g.material("EH_Bronze", base_png=..., orm_png=..., normal_png=..., metallic=1, roughness=1)
    mesh = g.mesh("body", [Primitive(P, N, UV, F, material=m, colors=C, joints=J, weights=W)])
    root = g.node("emberhold_pawn", children=[...], extras={...})
    g.scene([root])
    g.write("out.glb")
"""
from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass, field

import numpy as np

FLOAT, USHORT, UINT, UBYTE = 5126, 5123, 5125, 5121
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963


@dataclass
class Primitive:
    positions: np.ndarray
    normals: np.ndarray | None
    uvs: np.ndarray | None
    indices: np.ndarray
    material: int | None = None
    colors: np.ndarray | None = None      # (n,4) floats 0..1 -> COLOR_0 (normalized ubyte)
    joints: np.ndarray | None = None      # (n,4) ints
    weights: np.ndarray | None = None     # (n,4) floats


class GlbBuilder:
    def __init__(self, generator="battle-chess-forge (code forge)"):
        self.bin = bytearray()
        self.g: dict = {"asset": {"version": "2.0", "generator": generator}, "scene": 0, "scenes": [{"nodes": []}],
                        "nodes": [], "buffers": [{"byteLength": 0}], "bufferViews": [], "accessors": []}
        self._img_cache: dict = {}
        self._tex_cache: dict = {}
        self._ext: set = set()

    # ---------------------------------------------------------------- buffers
    def _view(self, data: bytes, target=None) -> int:
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target:
            v["target"] = target
        self.bin += data
        self.g["bufferViews"].append(v)
        return len(self.g["bufferViews"]) - 1

    def accessor(self, arr, typ=None, target=None, minmax=False, normalized=False, comp=None) -> int:
        a = np.ascontiguousarray(arr)
        if comp is None:
            comp = {np.dtype(np.float32): FLOAT, np.dtype(np.uint16): USHORT, np.dtype(np.uint32): UINT,
                    np.dtype(np.uint8): UBYTE}[a.dtype]
        if typ is None:
            typ = {1: "SCALAR", 2: "VEC2", 3: "VEC3", 4: "VEC4", 16: "MAT4"}[1 if a.ndim == 1 else a.shape[1]]
        view = self._view(a.tobytes(), target)
        acc = {"bufferView": view, "componentType": comp, "count": int(a.shape[0]), "type": typ}
        if normalized:
            acc["normalized"] = True
        if minmax:
            flat = a.reshape(a.shape[0], -1).astype(np.float64)
            acc["min"], acc["max"] = flat.min(0).tolist(), flat.max(0).tolist()
        self.g["accessors"].append(acc)
        return len(self.g["accessors"]) - 1

    # ---------------------------------------------------------------- textures / materials
    def image(self, data: bytes, name: str, mime="image/png") -> int:
        h = hashlib.sha1(data).hexdigest()
        if h in self._img_cache:
            return self._img_cache[h]
        view = self._view(data)
        self.g.setdefault("images", []).append({"bufferView": view, "mimeType": mime, "name": name})
        self._img_cache[h] = len(self.g["images"]) - 1
        return self._img_cache[h]

    def texture(self, data: bytes, name: str, mime="image/png") -> int:
        img = self.image(data, name, mime)
        if img in self._tex_cache:
            return self._tex_cache[img]
        if "samplers" not in self.g:
            self.g["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
        self.g.setdefault("textures", []).append({"source": img, "sampler": 0, "name": name})
        self._tex_cache[img] = len(self.g["textures"]) - 1
        return self._tex_cache[img]

    def material(self, name, base_color=(1, 1, 1, 1), metallic=0.0, roughness=1.0, emissive=None,
                 emissive_strength=None, base_tex=None, orm_tex=None, normal_tex=None, emissive_tex=None,
                 normal_scale=1.0, occlusion_strength=1.0, transmission=None, ior=None, thickness=None,
                 attenuation_color=None, attenuation_distance=None, double_sided=False, alpha_mode=None,
                 mime="image/png") -> int:
        """Textures are passed as encoded image bytes (PNG or JPEG) or None."""
        pbr: dict = {"baseColorFactor": [float(x) for x in base_color], "metallicFactor": float(metallic),
                     "roughnessFactor": float(roughness)}
        mat: dict = {"name": name, "pbrMetallicRoughness": pbr}
        if base_tex:
            pbr["baseColorTexture"] = {"index": self.texture(base_tex, f"{name}_baseColor", mime)}
        if orm_tex:
            t = self.texture(orm_tex, f"{name}_orm", mime)
            pbr["metallicRoughnessTexture"] = {"index": t}
            mat["occlusionTexture"] = {"index": t, "strength": float(occlusion_strength)}
        if normal_tex:
            mat["normalTexture"] = {"index": self.texture(normal_tex, f"{name}_normal", mime), "scale": float(normal_scale)}
        if emissive is not None:
            mat["emissiveFactor"] = [float(x) for x in emissive]
        if emissive_tex:
            mat["emissiveTexture"] = {"index": self.texture(emissive_tex, f"{name}_emissive", mime)}
        ext: dict = {}
        if emissive_strength is not None and emissive_strength != 1.0:
            ext["KHR_materials_emissive_strength"] = {"emissiveStrength": float(emissive_strength)}
        if transmission is not None:
            ext["KHR_materials_transmission"] = {"transmissionFactor": float(transmission)}
        if ior is not None:
            ext["KHR_materials_ior"] = {"ior": float(ior)}
        if thickness is not None:
            vol = {"thicknessFactor": float(thickness)}
            if attenuation_color is not None:
                vol["attenuationColor"] = [float(x) for x in attenuation_color]
            if attenuation_distance is not None:
                vol["attenuationDistance"] = float(attenuation_distance)
            ext["KHR_materials_volume"] = vol
        if ext:
            mat["extensions"] = ext
            self._ext.update(ext.keys())
        if double_sided:
            mat["doubleSided"] = True
        if alpha_mode:
            mat["alphaMode"] = alpha_mode
        self.g.setdefault("materials", []).append(mat)
        return len(self.g["materials"]) - 1

    # ---------------------------------------------------------------- geometry
    def mesh(self, name: str, prims: list[Primitive]) -> int:
        out = []
        for p in prims:
            P = np.asarray(p.positions, dtype=np.float32)
            attrs = {"POSITION": self.accessor(P, "VEC3", ARRAY_BUFFER, minmax=True)}
            if p.normals is not None:
                attrs["NORMAL"] = self.accessor(np.asarray(p.normals, dtype=np.float32), "VEC3", ARRAY_BUFFER)
            if p.uvs is not None:
                attrs["TEXCOORD_0"] = self.accessor(np.asarray(p.uvs, dtype=np.float32), "VEC2", ARRAY_BUFFER)
            if p.colors is not None:
                c = np.clip(np.round(np.asarray(p.colors) * 255.0), 0, 255).astype(np.uint8)
                if c.shape[1] == 3:
                    c = np.concatenate([c, np.full((len(c), 1), 255, np.uint8)], 1)
                attrs["COLOR_0"] = self.accessor(c, "VEC4", ARRAY_BUFFER, normalized=True)
            if p.joints is not None:
                attrs["JOINTS_0"] = self.accessor(np.asarray(p.joints, dtype=np.uint8), "VEC4", ARRAY_BUFFER)
                w = np.asarray(p.weights, dtype=np.float64)
                w = w / np.maximum(w.sum(1, keepdims=True), 1e-8)
                q = np.round(w * 255).astype(np.int64)          # normalized ubyte weights, forced to sum to 255
                q[np.arange(len(q)), q.argmax(1)] += 255 - q.sum(1)
                attrs["WEIGHTS_0"] = self.accessor(q.astype(np.uint8), "VEC4", ARRAY_BUFFER, normalized=True)
            idx = np.asarray(p.indices).reshape(-1)
            idx = idx.astype(np.uint16 if len(P) < 65535 else np.uint32)
            prim = {"attributes": attrs, "indices": self.accessor(idx, "SCALAR", ELEMENT_ARRAY_BUFFER), "mode": 4}
            if p.material is not None:
                prim["material"] = p.material
            out.append(prim)
        self.g.setdefault("meshes", []).append({"name": name, "primitives": out})
        return len(self.g["meshes"]) - 1

    # ---------------------------------------------------------------- scene graph
    def node(self, name, children=None, translation=None, rotation=None, scale=None, mesh=None, skin=None,
             extras=None) -> int:
        n: dict = {"name": name}
        if children:
            n["children"] = list(children)
        if translation is not None and any(abs(v) > 1e-9 for v in translation):
            n["translation"] = [float(v) for v in translation]
        if rotation is not None:
            n["rotation"] = [float(v) for v in rotation]
        if scale is not None:
            n["scale"] = [float(v) for v in scale]
        if mesh is not None:
            n["mesh"] = mesh
        if skin is not None:
            n["skin"] = skin
        if extras:
            n["extras"] = extras
        self.g["nodes"].append(n)
        return len(self.g["nodes"]) - 1

    def add_child(self, parent: int, child: int):
        self.g["nodes"][parent].setdefault("children", []).append(child)

    def skin(self, joint_nodes: list[int], inverse_bind: np.ndarray, skeleton: int | None = None, name="rig") -> int:
        """inverse_bind: (J,4,4) row-major matrices (converted to glTF column-major here)."""
        ibm = np.asarray(inverse_bind, dtype=np.float32).transpose(0, 2, 1).reshape(len(joint_nodes), 16)
        s: dict = {"name": name, "joints": list(joint_nodes), "inverseBindMatrices": self.accessor(ibm, "MAT4")}
        if skeleton is not None:
            s["skeleton"] = skeleton
        self.g.setdefault("skins", []).append(s)
        return len(self.g["skins"]) - 1

    def animation(self, name: str, channels: list[dict]) -> int:
        """channels: dicts {node, path ('translation'|'rotation'|'scale'), times (n,), values (n,3|4),
        interpolation ('LINEAR'|'STEP')}."""
        samplers, chans = [], []
        for ch in channels:
            t = np.asarray(ch["times"], dtype=np.float32)
            v = np.asarray(ch["values"], dtype=np.float32)
            samplers.append({"input": self.accessor(t, "SCALAR", minmax=True),
                             "output": self.accessor(v, "VEC4" if ch["path"] == "rotation" else "VEC3"),
                             "interpolation": ch.get("interpolation", "LINEAR")})
            chans.append({"sampler": len(samplers) - 1, "target": {"node": ch["node"], "path": ch["path"]}})
        self.g.setdefault("animations", []).append({"name": name, "samplers": samplers, "channels": chans})
        return len(self.g["animations"]) - 1

    def scene(self, roots: list[int]):
        self.g["scenes"][0]["nodes"] = list(roots)

    # ---------------------------------------------------------------- output
    def to_bytes(self) -> bytes:
        g = dict(self.g)
        g["buffers"] = [{"byteLength": len(self.bin)}]
        if self._ext:
            g["extensionsUsed"] = sorted(self._ext)
        js = json.dumps(g, separators=(",", ":")).encode()
        js += b" " * ((4 - len(js) % 4) % 4)
        b = bytes(self.bin) + b"\x00" * ((4 - len(self.bin) % 4) % 4)
        total = 12 + 8 + len(js) + 8 + len(b)
        return (struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(js), b"JSON") + js +
                struct.pack("<I4s", len(b), b"BIN\x00") + b)

    def write(self, path: str) -> int:
        data = self.to_bytes()
        with open(path, "wb") as fh:
            fh.write(data)
        return len(data)
