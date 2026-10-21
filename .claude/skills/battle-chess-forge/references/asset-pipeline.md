# Asset Pipeline

## Contents
1. Asset contract (names, rig, sockets, clips, extras, fragments)
2. Budgets
3. Blockout pipeline (headless bpy)
4. Detail pipeline (what makes it stop looking cartoonish)
5. Rigging & clip authoring
6. Fracture sets
7. Export & optimisation
8. Turntable approval renders

---

## 1. Asset contract

The engine and cinematics code depend only on this section. Changing it requires the lead
to update `src/contracts/assetContract.ts` and `scripts/validate_glb.py` in the same commit.

**Files** (`assets/models/`):
- `{faction}_{role}.glb` — the playable piece.
- `{faction}_{role}_fragments.glb` — pre-fractured version, loaded lazily on first capture.
- `faction` ∈ `emberhold`, `rime`; `role` ∈ `pawn rook knight bishop queen king`.
- Asset id = `{faction}_{role}`, e.g. `rime_queen`.

**Scene graph** (glTF is Y-up, front faces +Z, pedestal bottom at y = 0, centred on x/z):

```
{asset_id}                  (root node; carries extras, see below)
├── rig                     (armature; skinned)
│   └── bones: root, body, top   (required for every role)
│       humanoids also: spine, head, arm_L, hand_L, arm_R, hand_R
│       knights also:   mount_body, mount_head
├── {asset_id}_LOD0         (skinned mesh, full detail)
├── {asset_id}_LOD1         (skinned mesh, ~25 % tris)
├── weapon_summon           (queens only: a bone or node, scale 0 in every clip except Attack)
└── sockets (empties, parented to bones):
    socket_weapon_R   – weapon tip / hand grip (VFX trails attach here)
    socket_cast       – spell origin (bishops, rime king), any role may have it
    socket_impact     – where the blow lands, in the piece's local space at Attack impact
    socket_head       – crown / check aura anchor
```

**Animation clips** (exact names, case-sensitive):

| Clip | Loop | Length guide | Purpose |
|---|---|---|---|
| `Idle` | loop | 2–4 s | breathing / flame flicker; subtle |
| `Move` | loop | 0.6–1.0 s | stride/glide cycle while the engine translates the piece |
| `Attack` | once | 1.2–2.4 s | draw/summon → wind-up → impact → recover |
| `HitReact` | once | 0.3–0.6 s | stagger used when struck, before shattering |
| `Victory` | once | 1–2 s | after a capture or on checkmate |

Root motion is **not** baked into clips: the engine owns world position. Clips may move
the `body` bone ±0.3 units for lunges.

**Root-node extras** (Blender custom properties on the root object, exported with
`export_extras=True`):

```json
{
  "faction": "emberhold",
  "role": "pawn",
  "displayName": "Emberhold Shieldbearer",
  "impactTime": 0.95,          // seconds into Attack when the blow connects
  "strikeRange": 0.55,         // distance from target centre the attacker stops at
  "attackStyle": "melee",      // melee | leap | ranged | slam | summon
  "contractVersion": 1
}
```

**Fragments file**: one root `{asset_id}_fragments`, children `frag_000 … frag_NNN`
(12–40 pieces), each with its origin at its own centre of mass, assembled in rest pose so
that swapping the intact piece for the fragments is seamless. Interior faces use material
`{FACTION}_Interior` (`EH_Interior` glowing ember core, `RH_Interior` pale cracked ice).

## 2. Budgets

| Role | LOD0 tris (final) | LOD1 tris | Texture set |
|---|---|---|---|
| pawn | ≤ 15 k | ≤ 4 k | 1× 2K (baseColor, ORM, normal, emissive) |
| rook | ≤ 18 k | ≤ 5 k | 1× 2K |
| bishop | ≤ 22 k | ≤ 6 k | 1× 2K |
| queen | ≤ 30 k | ≤ 8 k | 1× 2K + weapon 1K |
| king | ≤ 30 k | ≤ 8 k | 1× 2K |
| knight | ≤ 35 k | ≤ 9 k | 1× 2K |

Full board ≈ 32 pieces → ~600 k tris at LOD0 worst case; fine for desktop WebGL2/WebGPU.
Mobile tier uses LOD1 everywhere. Textures max 2048², shipped as KTX2 (Basis UASTC for
normals, ETC1S for colour). Fragments: ≤ 6 k tris total per set (built from LOD1).

Blockout stage: any tri count ≤ 60 k, textures optional, but names/clips/sockets/extras
must already be correct.

**Placeholders without Blender:** `python scripts/make_placeholder_glbs.py --out assets/models`
writes all 24 contract-valid files (primitive figures, rigid skin, all clips) in seconds,
so engine work never waits on art. Khronos glTF-Validator reports 0 errors on them; its
"skinned mesh is not root" warning is expected for this hierarchy and harmless in three.js.

## 3. Blockout pipeline (headless bpy)

Use `scripts/blender/piece_kit.py`. Each piece gets its own build script
(`blender/build/{asset_id}.py`) modelled on `scripts/blender/example_pawn.py`:

```bash
blender -b --factory-startup -P blender/build/emberhold_pawn.py -- --out assets/models
python scripts/validate_glb.py assets/models/emberhold_pawn.glb --stage blockout
```

A blockout proves proportions, silhouette, socket placement and clip timing. Commit the
generated `.blend` alongside the GLB so the detail pass starts from it.

## 4. Detail pipeline

Procedural primitives can't reach "collector miniature" on their own — that is why the
earlier pack looked toy-like (icospheres for shoulders, plain cylinders for limbs, flat
vertex colours, no normal maps). The detail look comes from five things; do all five.

1. **High-poly form.** Sculpt in Blender (Voxel Remesh 0.005–0.01 → Multires 4–5 levels).
   Hard-surface armour: low-poly plates + Bevel (segments 3, harden normals) + Subdivision,
   then boolean-cut panel lines. Alpha/stamp brushes for rivets, scales, chain mail,
   stitching, fur clumps. Ice: start from Cell-fractured or crystal primitives, then
   sculpt chips and inner fracture planes.
   *Optional accelerator:* generate a base sculpt with an image-to-3D tool from the
   team's **own original concept art** (never from photos of commercial sets), then
   remesh and resculpt by hand. Check that tool's licence terms for commercial use.
2. **Retopology.** Quad retopo for deforming parts (cloaks, mounts, arms) with loops at
   joints; static parts (pedestal, crowns, armour plates) can use Decimate (planar +
   collapse) with weighted normals. Hit the budget table.
3. **UVs + bakes.** Texel density ~1024 px per unit. Bake from high to low in Cycles:
   tangent-space normal (OpenGL, matches glTF), AO, curvature, thickness (for ice).
   Use a cage / extrusion 0.01–0.02.
4. **Texturing.** Use the art-bible material node groups, driven by the baked
   curvature/AO masks (edge wear on bronze, frost on upward faces, soot in cavities,
   ember cracks emissive). Bake the result to baseColor, ORM (R=AO, G=rough, B=metal),
   normal, emissive. Substance Painter / ArmorPaint are fine alternatives — export with
   the glTF/ORM preset.
5. **Shading in engine.** HDRI environment, AgX/ACES tone mapping, bloom on emissive,
   contact shadows/AO. A detailed asset still looks flat under a single directional light.

## 5. Rigging & clip authoring

- Pieces are "living statues": bind rigid parts 100 % to one bone (no soft weights on
  armour) — it reads as carved stone/metal moving and is cheap to skin. Only cloth,
  cloaks, mounts' necks get smooth weights.
- Build actions in the Action editor, name them exactly per contract, push each to its own
  NLA track (or keep as stashed actions) and export with
  `export_animation_mode='ACTIONS'`.
- Author `Attack` with three readable beats: anticipation (≥ 0.3 s), fast strike
  (0.08–0.15 s), hold + recover. Put the impact frame at `impactTime`. Exaggerate:
  overshoot, squash on the pedestal, weapon smear frames (a stretched duplicate weapon
  mesh visible for 2 frames) — this sells weight at board scale.
- Queen `weapon_summon`: simplest as a bone with the weapon mesh rigidly bound to it,
  scale 0 in every clip, 0 → 1.15 → 1.0 over the first 0.4 s of Attack; the engine adds
  the particle burst at `socket_weapon_R`.

## 6. Fracture sets

1. Duplicate LOD1, apply modifiers, join into one mesh, make it manifold
   (`3D Print Toolbox → Make Manifold` or voxel remesh at low resolution).
2. Run **Cell Fracture** (an Extensions-platform add-on in Blender 4.2+): source = own
   verts + noise, 20–30 cells for pawns, 30–40 for others, margin 0.001, interior
   material = `{FACTION}_Interior`, recursion 1 with clustering on the pedestal for
   bigger slabs.
3. Rename shards `frag_000…`, set origin to centre of mass, parent under the fragments
   root, export to `{asset_id}_fragments.glb`.
4. `piece_kit.fracture()` is an add-on-free plane-bisect splitter (fine for blockouts and
   CI). For final assets run Cell Fracture on the same source and keep the naming above.

## 7. Export & optimisation

Blender glTF exporter settings (set in `piece_kit.export_glb`):
`export_format='GLB'`, `export_yup=True`, `export_apply=True`, `export_extras=True`,
`export_animations=True`, `export_animation_mode='ACTIONS'`, `export_skins=True`,
`export_def_bones=False`, `export_force_sampling=True`, `export_optimize_animation_size=True`.

Then optimise (Node, `@gltf-transform/cli`, KTX-Software `toktx` on PATH):

```bash
npx gltf-transform optimize in.glb out.glb --compress meshopt --texture-compress ktx2 \
    --texture-size 2048
```

The engine registers `MeshoptDecoder` and `KTX2Loader` on its `GLTFLoader`.

## 8. Turntable approval renders

`piece_kit.turntable(asset_id)` renders 8 frames at 45° steps in Eevee with the
presentation lighting from the art bible. Show the user Emberhold and Rime versions of
the same role side by side before moving on to the next role.
