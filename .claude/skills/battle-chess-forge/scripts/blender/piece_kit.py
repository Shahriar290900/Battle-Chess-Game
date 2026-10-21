"""piece_kit — bpy helpers for battle-chess assets (Blender 4.2+, headless friendly).

Import from a build script run as:
    blender -b --factory-startup -P blender/build/<asset_id>.py -- --out assets/models

Conventions (match references/asset-pipeline.md):
  * Blender is Z-up; the glTF exporter converts to Y-up. Model the front facing -Y in
    Blender; it becomes +Z in glTF.
  * Pedestal bottom at z = 0, centred on x/y. 1 Blender unit = 1 board square.
  * Every mesh part is rigidly bound to one bone (vertex group named after the bone).
  * `weapon_summon` (queens) is a BONE scaled 0 in every clip except Attack.

Written without a Blender binary at hand: run once on a single piece and fix any API
drift before fanning out to all twelve.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

CLIPS = ("Idle", "Move", "Attack", "HitReact", "Victory")
FPS = 30


# ---------------------------------------------------------------- scene / args
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.fps = FPS
    scn.unit_settings.system = "METRIC"
    return scn


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = "assets/models"
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    return {"out": out, "turntable": "--turntable" in argv}


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def set_active(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# ---------------------------------------------------------------- materials
_MAT_CACHE = {}


def material(name, base, metal=0.0, rough=0.5, emissive=None, strength=0.0, transmission=0.0, ior=1.45):
    if name in _MAT_CACHE:
        return _MAT_CACHE[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if emissive:
        bsdf.inputs["Emission Color"].default_value = (*emissive, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    if transmission:
        bsdf.inputs["Transmission Weight"].default_value = transmission
        bsdf.inputs["IOR"].default_value = ior
    _MAT_CACHE[name] = m
    return m


def faction_materials(faction):
    if faction == "emberhold":
        return {
            "base": material("EH_Bronze", (0.66, 0.44, 0.23), 1.0, 0.35),
            "steel": material("EH_Steel", (0.23, 0.23, 0.22), 1.0, 0.45),
            "cloth": material("EH_Cloth", (0.37, 0.12, 0.10), 0.0, 0.9),
            "stone": material("EH_Stone", (0.12, 0.10, 0.08), 0.0, 0.8),
            "glow": material("EH_Ember", (1.0, 0.48, 0.10), 0.0, 0.5, (1.0, 0.48, 0.10), 6.0),
            "interior": material("EH_Interior", (0.3, 0.1, 0.02), 0.0, 0.6, (1.0, 0.4, 0.06), 4.0),
        }
    return {
        "base": material("RH_Obsidian", (0.06, 0.08, 0.11), 0.2, 0.12),
        "steel": material("RH_Silver", (0.62, 0.71, 0.77), 1.0, 0.3),
        "cloth": material("RH_Frost", (0.86, 0.94, 0.97), 0.0, 0.9),
        "stone": material("RH_Ice", (0.50, 0.83, 0.94), 0.0, 0.08, transmission=0.9, ior=1.31),
        "glow": material("RH_Glow", (0.44, 0.95, 1.0), 0.0, 0.4, (0.44, 0.95, 1.0), 5.0),
        "interior": material("RH_Interior", (0.75, 0.9, 1.0), 0.0, 0.3, (0.6, 0.9, 1.0), 2.0),
    }


# ---------------------------------------------------------------- mesh parts
def _obj_from_bm(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = link(bpy.data.objects.new(name, me))
    obj.data.materials.append(mat)
    return obj


def lathe(name, profile, mat, segments=48):
    """profile: list of (z, radius) from bottom to top. Closed caps."""
    bm = bmesh.new()
    rings = []
    for z, r in profile:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segments),
                                    r * math.sin(2 * math.pi * i / segments), z)) for i in range(segments)])
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj_from_bm(name, bm, mat)


def box(name, center, size, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _obj_from_bm(name, bm, mat)


def cone(name, base_center, r1, r2, depth, mat, segments=24, direction=(0, 0, 1)):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=r1, radius2=r2, depth=depth)
    bmesh.ops.translate(bm, vec=Vector((0, 0, depth / 2)), verts=bm.verts)
    rot = Vector((0, 0, 1)).rotation_difference(Vector(direction)).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(base_center), verts=bm.verts)
    return _obj_from_bm(name, bm, mat)


def sphere(name, center, radius, mat, scale=(1, 1, 1), segments=24, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _obj_from_bm(name, bm, mat)


def torus(name, z, major, minor, mat, seg=64, minor_seg=12):
    bm = bmesh.new()
    grid = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        row = []
        for j in range(minor_seg):
            b = 2 * math.pi * j / minor_seg
            r = major + minor * math.cos(b)
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z + minor * math.sin(b))))
        grid.append(row)
    for i in range(seg):
        for j in range(minor_seg):
            bm.faces.new((grid[i][j], grid[(i + 1) % seg][j], grid[(i + 1) % seg][(j + 1) % minor_seg],
                          grid[i][(j + 1) % minor_seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj_from_bm(name, bm, mat)


def detail(obj, bevel=0.004, segments=2, subdiv=0):
    """Blockout-to-mid detail: bevelled edges + weighted normals (+ optional subdivision)."""
    if bevel:
        m = obj.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments, m.limit_method = bevel, segments, "ANGLE"
        m.harden_normals = True
    if subdiv:
        s = obj.modifiers.new("Subsurf", "SUBSURF")
        s.levels = s.render_levels = subdiv
    obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL").keep_sharp = True
    return obj


def pedestal(faction, mats):
    """Two-tier plinth, trim bands and front emblem boss. Bound to bone 'root'."""
    parts = [
        lathe("pedestal", [(0.0, 0.40), (0.03, 0.405), (0.07, 0.39), (0.10, 0.37), (0.13, 0.355),
                           (0.16, 0.34), (0.19, 0.31), (0.22, 0.29)], mats["stone"], 64),
        torus("trim_low", 0.07, 0.392, 0.012, mats["steel"]),
        torus("trim_high", 0.19, 0.312, 0.010, mats["steel"]),
        sphere("emblem", (0, -0.355, 0.13), 0.045, mats["glow"], scale=(1, 0.35, 1)),
    ]
    for p in parts:
        detail(p, 0.003)
        bind(p, "root")
    return parts


# ---------------------------------------------------------------- rig
def armature(bones):
    """bones: list of (name, parent or None, head_xyz, tail_xyz). Returns armature object."""
    arm = bpy.data.armatures.new("rig")
    obj = link(bpy.data.objects.new("rig", arm))
    set_active(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for name, parent, head, tail in bones:
        b = arm.edit_bones.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        if parent:
            b.parent = eb[parent]
        eb[name] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in obj.pose.bones:
        pb.rotation_mode = "XYZ"
    return obj


def bind(obj, bone):
    vg = obj.vertex_groups.new(name=bone)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    obj["_bone"] = bone
    return obj


def join_parts(name, parts, rig):
    set_active(parts[0])
    for p in parts:
        p.select_set(True)
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = name
    obj.parent = rig
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    return obj


def make_lod1(lod0, name, ratio=0.25):
    lod1 = lod0.copy()
    lod1.data = lod0.data.copy()
    lod1.name = lod1.data.name = name
    link(lod1)
    lod1.modifiers.clear()
    dec = lod1.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = ratio
    arm = lod1.modifiers.new("Armature", "ARMATURE")
    arm.object = lod0.modifiers["Armature"].object
    return lod1


def socket(name, rig, bone, location):
    e = link(bpy.data.objects.new(name, None))
    e.empty_display_size = 0.05
    e.parent, e.parent_type, e.parent_bone = rig, "BONE", bone
    bpy.context.view_layer.update()
    e.matrix_world = Matrix.Translation(Vector(location))
    return e


def asset_root(asset_id, children, extras):
    root = link(bpy.data.objects.new(asset_id, None))
    for k, v in extras.items():
        root[k] = v
    for c in children:
        mw = c.matrix_world.copy()
        c.parent = root
        c.matrix_world = mw
    return root


# ---------------------------------------------------------------- animation
def clip(rig, name, keys, length_s):
    """keys: list of (time_s, bone, 'rot'|'loc'|'scale', (x, y, z)). Euler radians for rot.

    Creates an action, keys it, stashes it on its own NLA track (muted) so the glTF
    exporter (export_animation_mode='ACTIONS') writes it as a separate animation.
    """
    ad = rig.animation_data or rig.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad.action = act
    attr = {"rot": "rotation_euler", "loc": "location", "scale": "scale"}
    for t, bone, kind, val in keys:
        pb = rig.pose.bones[bone]
        setattr(pb, attr[kind], val)
        pb.keyframe_insert(attr[kind], frame=1 + t * FPS)
    for pb in rig.pose.bones:  # reset pose so the next clip starts clean
        pb.rotation_euler, pb.location, pb.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
    act.frame_range = (1, 1 + length_s * FPS)
    track = ad.nla_tracks.new()
    track.name = name
    track.strips.new(name, 1, act)
    track.mute = True
    ad.action = None
    return act


def check_clips(rig):
    names = {t.name for t in rig.animation_data.nla_tracks} if rig.animation_data else set()
    missing = [c for c in CLIPS if c not in names]
    if missing:
        raise RuntimeError(f"missing clips: {missing}")


# ---------------------------------------------------------------- fracture
def fracture(src, asset_id, interior_mat, count=24, seed=7):
    """Split the evaluated (decimated, rest-pose) mesh of `src` into `count` shards.

    Uses a plane-bisect splitter that works without add-ons. For final assets prefer the
    Cell Fracture extension (nicer Voronoi shards): run it on the same source, rename the
    shards frag_###, and parent them under '<asset_id>_fragments' exactly as below.
    """
    random.seed(seed)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
    base = link(bpy.data.objects.new(f"{asset_id}_fracture_src", me))
    base.matrix_world = src.matrix_world.copy()
    base.data.materials.append(interior_mat)
    inner_idx = len(base.data.materials) - 1

    shards = _bisect_fracture(base, count, inner_idx)
    root = link(bpy.data.objects.new(f"{asset_id}_fragments", None))
    for i, s in enumerate(shards):
        s.name = s.data.name = f"frag_{i:03d}"
        set_active(s)
        bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS", center="MEDIAN")
        s.parent = root
    return root, shards


def _bisect_fracture(obj, count, inner_idx):
    pieces = [obj]
    while len(pieces) < count:
        pieces.sort(key=lambda o: -len(o.data.vertices))
        target = pieces.pop(0)
        bb = [target.matrix_world @ Vector(c) for c in target.bound_box]
        co = sum(bb, Vector()) / 8 + Vector([random.uniform(-0.03, 0.03) for _ in range(3)])
        no = Vector([random.uniform(-1, 1) for _ in range(3)]).normalized()
        halves = []
        for keep_outer in (True, False):
            dup = target.copy()
            dup.data = target.data.copy()
            link(dup)
            bm = bmesh.new()
            bm.from_mesh(dup.data)
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=target.matrix_world.inverted() @ co,
                                         plane_no=no, clear_inner=keep_outer, clear_outer=not keep_outer)
            cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            filled = bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
            for f in filled["faces"]:
                f.material_index = inner_idx
            bm.to_mesh(dup.data)
            bm.free()
            if len(dup.data.vertices) >= 4:
                halves.append(dup)
            else:
                bpy.data.objects.remove(dup)
        bpy.data.objects.remove(target)
        pieces += halves
    return pieces


# ---------------------------------------------------------------- export / render
GLTF_OPTS = dict(
    export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
    export_extras=True, export_animations=True, export_animation_mode="ACTIONS",
    export_skins=True, export_def_bones=False, export_force_sampling=True,
    export_optimize_animation_size=True,
)


def export_glb(path, root):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    stack = [root]
    while stack:
        o = stack.pop()
        o.select_set(True)
        stack.extend(o.children)
    bpy.ops.export_scene.gltf(filepath=path, **GLTF_OPTS)
    print(f"[piece_kit] exported {path}")


def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)


def turntable(asset_id, out_dir, height=1.5, frames=8, res=(1280, 720)):
    scn = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = engine
            break
        except TypeError:
            continue
    scn.render.resolution_x, scn.render.resolution_y = res
    cam = link(bpy.data.objects.new("tt_cam", bpy.data.cameras.new("tt_cam")))
    scn.camera = cam
    key = link(bpy.data.objects.new("tt_key", bpy.data.lights.new("tt_key", "AREA")))
    key.data.energy, key.data.color = 600, (1.0, 0.85, 0.7)
    key.location = (2.0, -2.0, 2.5)
    rim = link(bpy.data.objects.new("tt_rim", bpy.data.lights.new("tt_rim", "AREA")))
    rim.data.energy, rim.data.color = 400, (0.6, 0.8, 1.0)
    rim.location = (-2.0, 2.0, 2.0)
    for lamp in (key, rim):
        lamp.rotation_euler = (Vector((0, 0, height / 2)) - lamp.location).to_track_quat("-Z", "Y").to_euler()
    target = Vector((0, 0, height * 0.5))
    for i in range(frames):
        a = 2 * math.pi * i / frames - math.pi / 2
        cam.location = target + Vector((3.2 * math.cos(a), 3.2 * math.sin(a), 0.9))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        scn.render.filepath = os.path.join(out_dir, f"{asset_id}_tt_{i:02d}.png")
        bpy.ops.render.render(write_still=True)
