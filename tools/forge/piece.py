"""piece.py - assembles a contract-v1 piece GLB (+ fragments GLB) from parts, a rig and clips.

    p = Piece("emberhold", "pawn", rig, clips)
    p.add("shield_rim", mesh, "EH_Bronze", bone="arm_L")
    p.add("cloak", mesh, "EH_Cloth", bone="spine", bone2="cloak", blend=(y_top, y_bottom))   # smooth skin
    glb, frag_glb, stats = p.build()

Part meshes must be in WORLD rest-pose coordinates (pedestal bottom at y = 0, front = +Z).
UVs are expected in "metres / 0.25" (geom primitives' default tile); materials tile every 0.25 m.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

import textures as T
from fracture import build_fragments
from geom import Mesh, decimate, merge
from gltf_writer import GlbBuilder, Primitive
from rig import Clip, Rig

CONTRACT_VERSION = 1
LOD0_BUDGET = {"pawn": 15000, "rook": 18000, "bishop": 22000, "queen": 30000, "king": 30000, "knight": 35000}
LOD1_BUDGET = {"pawn": 4000, "rook": 5000, "bishop": 6000, "queen": 8000, "king": 8000, "knight": 9000}
FRAG_COUNT = {"pawn": 20, "rook": 30, "knight": 30, "bishop": 30, "queen": 40, "king": 40}
FRAG_BUDGET = 6000
DISPLAY = {
    ("emberhold", "pawn"): "Emberhold Shieldbearer", ("rime", "pawn"): "Rime Thrall",
    ("emberhold", "rook"): "Emberhold Forge Bastion", ("rime", "rook"): "Rime Glacier Bastion",
    ("emberhold", "knight"): "Emberhold Ashmane Rider", ("rime", "knight"): "Rime Gravewind Rider",
    ("emberhold", "bishop"): "Emberhold Cinder Oracle", ("rime", "bishop"): "Rime Frost Chanter",
    ("emberhold", "queen"): "Emberhold Flamecrown Warden", ("rime", "queen"): "Rime Pale Tide Queen",
    ("emberhold", "king"): "Emberhold Ember Sovereign", ("rime", "king"): "Rime Glacier Tyrant",
}
DEFAULT_EXTRAS = {  # attackStyle, impactTime, strikeRange
    "pawn": ("melee", 0.95, 0.55), "rook": ("slam", 0.75, 0.10), "knight": ("leap", 1.0, 0.50),
    "bishop": ("ranged", 1.1, 1.5), "queen": ("summon", 1.3, 0.7), "king": ("melee", 1.2, 0.6),
}


def _jpeg(a, q, ss):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, format="JPEG", quality=q, subsampling=ss, optimize=True)
    return buf.getvalue()


def _half(a):
    """2x box downsample of a (n,n[,c]) array (tileable inputs stay tileable)."""
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def _encode_set(ts):
    """Size-tuned encoding of a texture set (the geometry is >50 % of a GLB, the normal maps most of the rest).
    256 px piece sets: colour / ORM / emissive at full size, normal map from the half-res height field (128 px).
    128 px fragment sets: colour / emissive full, ORM and normal at 64 px.  JPEG 4:2:0 for colour and emissive."""
    if not ts.jpeg:
        return ts.images()
    n = ts.albedo.shape[0]
    frag = n <= 128
    u8 = T.to_u8
    base = _jpeg(u8(ts.albedo), 78 if frag else 80, 2)
    orm_a = u8(np.stack([ts.ao, ts.rough, ts.metal], -1))
    orm = _jpeg(u8(_half(np.stack([ts.ao, ts.rough, ts.metal], -1))) if frag else orm_a, 72 if frag else 76, 0)
    h = _half(ts.height)
    nrm = _jpeg(u8(T.height_to_normal(h, ts.normal_strength)), 76 if frag else 80, 0)
    emi = None if ts.emissive is None else _jpeg(u8(ts.emissive), 78 if frag else 80, 2)
    return base, orm, nrm, emi, "image/jpeg"


@dataclass
class Part:
    name: str
    mesh: Mesh
    material: str
    bone: str
    bone2: str | None = None
    lod1: object = "auto"        # "auto" decimate | "keep" | None (omit from LOD1 and fragments)
    bake: bool = True            # bake AO / wear vertex colours
    occluder: bool = True        # contributes to other parts' AO
    frag: bool = True            # included in the fragment source
    tint: object = None          # optional fn(P (n,3)) -> (n,3) multiplier applied to baked colours (soot gradients)


class Piece:
    def __init__(self, faction, role, rig: Rig, clips: list[Clip], display_name=None, attack_style=None,
                 impact_time=None, strike_range=None, tex_res=T.DEFAULT_RES, frag_tex_res=128, seed=1):
        self.faction, self.role, self.rig, self.clips = faction, role, rig, clips
        self.asset_id = f"{faction}_{role}"
        st, it, sr = DEFAULT_EXTRAS[role]
        self.extras = {"faction": faction, "role": role, "displayName": display_name or DISPLAY[(faction, role)],
                       "impactTime": impact_time if impact_time is not None else it,
                       "strikeRange": strike_range if strike_range is not None else sr,
                       "attackStyle": attack_style or st, "contractVersion": CONTRACT_VERSION}
        self.parts: list[Part] = []
        self.tex_res = tex_res
        self.frag_tex_res = frag_tex_res
        self.seed = seed
        self.prefix = "EH" if faction == "emberhold" else "RH"

    # ------------------------------------------------------------ authoring
    def add(self, name, mesh: Mesh, material: str, bone: str, bone2=None, blend=None, axis=1, lod1="auto",
            bake=True, occluder=True, frag=True, uv_scale=None, tint=None):
        """Add a part.  `blend=(v0, v1)` with `bone2` smoothly shifts weight from `bone` (at coordinate v0 along
        `axis`) to `bone2` (at v1) - use for cloaks, skirts, fur.  Otherwise the part is rigidly bound to `bone`."""
        assert bone in self.rig.bones or bone in self.rig.nodes, f"unknown bone {bone}"
        if mesh is None or mesh.tri_count == 0:
            return
        m = mesh if mesh.N is not None else mesh.shade()
        if uv_scale is not None:
            m = m.transformed_uv((uv_scale, uv_scale))
        if bone2 is not None and blend is not None:
            t = np.clip((m.P[:, axis] - blend[0]) / (blend[1] - blend[0]), 0, 1)
            t = t * t * (3 - 2 * t)
            m = m.copy()
            m.A["bw"] = t[:, None]
        self.parts.append(Part(name, m, material, bone, bone2 if blend is not None else None, lod1, bake, occluder, frag, tint))

    def add_all(self, name, meshes, material, bone, **kw):
        self.add(name, merge(meshes), material, bone, **kw)

    # ------------------------------------------------------------ build
    def tri_count(self):
        """Skinned LOD0 triangles (parts on unskinned rig nodes are counted by `node_tri_count`)."""
        return sum(p.mesh.tri_count for p in self.parts if not self._is_node(p))

    def node_tri_count(self):
        return sum(p.mesh.tri_count for p in self.parts if self._is_node(p))

    def _is_node(self, p):
        return p.bone in self.rig.nodes

    def _bake(self, log):
        occ = [p for p in self.parts if p.occluder and not self._is_node(p)]
        meshes = [p.mesh for p in occ]
        mats = [p.material for p in occ]
        cols = T.bake_vertex_colors(meshes, mats, seed=self.seed, tex_res=self.tex_res)
        for p, c in zip(occ, cols):
            p.mesh = p.mesh.copy()
            p.mesh.C = c if p.bake else np.ones((len(p.mesh.P), 4))
        nodep = [p for p in self.parts if self._is_node(p)]
        if nodep:   # node parts (summoned weapon) get their own AO pass: they must not darken the body at rest
            cols = T.bake_vertex_colors([p.mesh for p in nodep], [p.material for p in nodep], seed=self.seed + 7, tex_res=self.tex_res)
            for p, c in zip(nodep, cols):
                p.mesh = p.mesh.copy()
                p.mesh.C = c if p.bake else np.ones((len(p.mesh.P), 4))
        for p in self.parts:
            if not p.occluder and not self._is_node(p):
                p.mesh = p.mesh.copy()
                p.mesh.C = np.ones((len(p.mesh.P), 4))
            if p.tint is not None:
                p.mesh.C = p.mesh.C.copy()
                p.mesh.C[:, :3] = np.clip(p.mesh.C[:, :3] * np.asarray(p.tint(p.mesh.P))[:, None] if np.ndim(p.tint(p.mesh.P)) == 1 else p.mesh.C[:, :3] * p.tint(p.mesh.P), 0, 1)

    def _lod1(self, budget, log):
        """Decimate parts so the sum fits `budget` (~25 % of LOD0)."""
        t0 = self.tri_count()
        target = min(budget * 0.94, 0.26 * t0)
        keep_fixed = sum(p.mesh.tri_count for p in self.parts if p.lod1 == "keep")
        auto = [p for p in self.parts if p.lod1 == "auto"]
        auto_tris = sum(p.mesh.tri_count for p in auto)
        scale = max(0.03, (target - keep_fixed) / max(auto_tris, 1))
        for _ in range(5):
            out = []
            for p in self.parts:
                if p.lod1 is None:
                    continue
                m = p.mesh
                if p.lod1 == "auto" and m.tri_count > 16:
                    tgt = max(10, int(round(m.tri_count * scale)))
                    m = decimate(m, tgt)
                out.append((p, m))
            total = sum(m.tri_count for _, m in out)
            if total <= budget * 0.97:
                return out
            scale *= 0.85
        return out

    def build(self, log=print):
        self._bake(log)
        node_parts = [p for p in self.parts if self._is_node(p)]
        self.parts = [p for p in self.parts if not self._is_node(p)]
        try:
            lod1_parts = self._lod1(LOD1_BUDGET[self.role], log)
        finally:
            self.parts = self.parts + node_parts
        piece_bytes, sizes = self._write_piece(lod1_parts, node_parts)
        frag_src = [(m, p.material) for p, m in lod1_parts if p.frag]
        frags = build_fragments(frag_src, FRAG_COUNT[self.role], f"{self.prefix}_Interior", budget=FRAG_BUDGET - 200,
                                seed=self.seed)
        frag_bytes = self._write_fragments(frags)
        stats = {"lod0_tris": self.tri_count(), "lod1_tris": sum(m.tri_count for _, m in lod1_parts),
                 "fragments": len(frags), "fragment_tris": sum(f.tris for f in frags),
                 "piece_bytes": len(piece_bytes), "fragment_bytes": len(frag_bytes)}
        return piece_bytes, frag_bytes, stats

    # ------------------------------------------------------------ writers
    def _mat_index(self, g: GlbBuilder, cache: dict, name: str, res=None) -> int:
        if name in cache:
            return cache[name]
        ts = T.get_texture_set(name, res or self.tex_res)
        base, orm, normal, emi, mime = _encode_set(ts)
        has_emi = emi is not None
        cache[name] = g.material(
            name, base_color=(1, 1, 1, 1), metallic=1.0, roughness=1.0,
            emissive=(1, 1, 1) if has_emi else None, emissive_strength=ts.emissive_strength if has_emi else None,
            base_tex=base, orm_tex=orm, normal_tex=normal, emissive_tex=emi, normal_scale=1.0,
            transmission=ts.transmission, ior=ts.ior, thickness=ts.thickness, attenuation_color=ts.attenuation_color,
            attenuation_distance=ts.attenuation_distance, double_sided=ts.double_sided, mime=mime)
        return cache[name]

    def _prims(self, g, items, cache):
        by_mat: dict = {}
        for p, m in items:
            by_mat.setdefault(p.material, []).append((p, m))
        prims = []
        for mat, lst in by_mat.items():
            Ps, Ns, UVs, Cs, Fs, Js, Ws = [], [], [], [], [], [], []
            off = 0
            for p, m in lst:
                m = m.compact() if m.N is not None else m.shade()
                n = len(m.P)
                b1 = self.rig.index(p.bone)
                bw = m.A["bw"][:, 0] if "bw" in m.A else np.zeros(n)
                b2 = self.rig.index(p.bone2) if p.bone2 else b1
                J = np.zeros((n, 4), dtype=np.int64)
                W = np.zeros((n, 4))
                J[:, 0], J[:, 1] = b1, b2
                W[:, 0], W[:, 1] = 1 - bw, bw
                Ps.append(m.P)
                Ns.append(m.N)
                UVs.append(m.UV)
                Cs.append(m.C if m.C is not None else np.ones((n, 4)))
                Fs.append(m.F + off)
                Js.append(J)
                Ws.append(W)
                off += n
            prims.append(Primitive(np.concatenate(Ps), np.concatenate(Ns), np.concatenate(UVs), np.concatenate(Fs),
                                   self._mat_index(g, cache, mat), np.concatenate(Cs), np.concatenate(Js),
                                   np.concatenate(Ws)))
        return prims

    def _write_piece(self, lod1_parts, node_parts=()):
        g = GlbBuilder()
        cache: dict = {}
        rig = self.rig
        node_of = {name: g.node(name, translation=rig.local(name)) for name in rig.order}
        for name, b in rig.bones.items():
            if b.parent:
                g.add_child(node_of[b.parent], node_of[name])
        for sname, (bone, pos) in rig.sockets.items():
            g.add_child(node_of[bone], g.node(sname, translation=pos - rig.pos(bone)))
        ibm = np.zeros((len(rig.order), 4, 4))
        for i, name in enumerate(rig.order):
            ibm[i] = np.eye(4)
            ibm[i][:3, 3] = -rig.pos(name)
        skin = g.skin([node_of[n] for n in rig.order], ibm, skeleton=node_of["root"])
        for nname, (nbone, npos) in rig.nodes.items():     # unskinned mesh nodes (queen weapon_summon), animated by scale
            items = [p for p in node_parts if p.bone == nname]
            prims = []
            by_mat: dict = {}
            for p in items:
                by_mat.setdefault(p.material, []).append(p.mesh.translated(*(-npos)))
            for mat, ms in by_mat.items():
                ms = [m.compact() if m.N is not None else m.shade() for m in ms]
                prims.append(Primitive(np.concatenate([m.P for m in ms]), np.concatenate([m.N for m in ms]),
                                       np.concatenate([m.UV for m in ms]),
                                       np.concatenate([m.F + o for m, o in zip(ms, np.cumsum([0] + [len(m.P) for m in ms[:-1]]))]),
                                       self._mat_index(g, cache, mat),
                                       np.concatenate([m.C if m.C is not None else np.ones((len(m.P), 4)) for m in ms])))
            nn = g.node(nname, translation=npos - rig.pos(nbone), mesh=g.mesh(nname, prims) if prims else None, scale=(0, 0, 0))   # rest scale 0: hidden unless a clip scales it up
            g.add_child(node_of[nbone], nn)
            node_of[nname] = nn
        lod0 = g.node(f"{self.asset_id}_LOD0", mesh=g.mesh(f"{self.asset_id}_LOD0",
                      self._prims(g, [(p, p.mesh) for p in self.parts if not self._is_node(p)], cache)), skin=skin)
        lod1 = g.node(f"{self.asset_id}_LOD1", mesh=g.mesh(f"{self.asset_id}_LOD1",
                      self._prims(g, lod1_parts, cache)), skin=skin)
        rig_node = g.node("rig", children=[node_of["root"]])
        root = g.node(self.asset_id, children=[rig_node, lod0, lod1], extras=self.extras)
        g.scene([root])
        for clip in self.clips:
            chans = []
            for ch in clip.bake(rig):
                chans.append({**ch, "node": node_of[ch["bone"]]})
            g.animation(clip.name, chans)
        data = g.to_bytes()
        return data, len(data)

    def _write_fragments(self, frags):
        g = GlbBuilder()
        cache: dict = {}
        kids = []
        for i, f in enumerate(frags):
            prims = []
            for m, mat in f.prims:
                m = m.compact()
                n = len(m.P)
                prims.append(Primitive(m.P, m.N, m.UV, m.F, self._mat_index(g, cache, mat, self.frag_tex_res),
                                       m.C if m.C is not None else np.ones((n, 4))))
            name = f"frag_{i:03d}"
            kids.append(g.node(name, mesh=g.mesh(name, prims), translation=f.centroid))
        root = g.node(f"{self.asset_id}_fragments", children=kids, extras={"faction": self.faction, "role": self.role})
        g.scene([root])
        return g.to_bytes()
