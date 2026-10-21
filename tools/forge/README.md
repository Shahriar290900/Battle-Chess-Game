# Code Forge

Procedural, Blender-free asset pipeline: numpy/scipy/Pillow geometry + textures -> contract-v1 GLBs
(skinned, 5 clips, sockets, extras, LOD0/LOD1, pre-fractured fragments) written to `public/models/`.
No other dependency (no trimesh, no Blender). Reference implementation: `pieces/emberhold_pawn.py`
(read it top to bottom; every pattern below is used there).

```
python3 tools/forge/build_all.py --only emberhold_pawn      # build + validate (--stage final)
python3 tools/forge/build_all.py                            # every pieces/*.py; others keep their placeholder
npm run turntables -- --ids emberhold_pawn                  # 8-view sheet  -> docs/art/turntables/emberhold_pawn.png
npm run turntables -- --ids emberhold_pawn --clip Attack    # 6-frame strip -> emberhold_pawn_attack.png
npm run turntables -- --ids emberhold_pawn --single 30      # one big close-up (--dist 2.5 --ty 0.55 --pitch 12); delete after review
npm run turntables                                          # all assets + role_{role}.png faction pairs
```
Shell: if `npm`/`node` is missing, `export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH"`.
The renderer launches **Brave once** (`/Applications/Brave Browser.app/...`, override with `BRAVE_PATH`) and a Vite dev
server, renders everything, then closes both. Do not run several at once (8 GB machine). `turntables --clip X --times a,b,c,d,e,f` samples explicit times.

## Files

| File | Role |
|---|---|
| `geom.py` | Mesh class + primitives (lathe, tube/sweep, extrude, plate, loft, superellipsoid, torus, blade, crystals, cloth), noise, bend/warp, instances, QEM decimation |
| `textures.py` | tileable PBR sets (`get_texture_set(name)`), material registry, per-vertex AO + edge-wear bake |
| `rig.py` | `Rig` (bones/sockets by absolute rest position) and the `Clip` keyframe DSL |
| `piece.py` | `Piece`: collects parts, bakes, builds LOD1, writes piece GLB + fragments GLB |
| `fracture.py` | Voronoi triangle clustering -> shells with `{EH,RH}_Interior` insides (called by `Piece.build`) |
| `gltf_writer.py` | low level GLB writer (skins, animations LINEAR/STEP, KHR emissive_strength / transmission / volume / ior) |
| `build_all.py` | discovers `pieces/*.py`, calls `build()`, writes files, runs `scripts/validate_glb.py` |

A piece script is `tools/forge/pieces/{asset_id}.py` exposing `build() -> (piece_glb_bytes, fragments_glb_bytes, stats)`
(just `return piece.build()`). Put `sys.path.insert(0, <tools/forge>)` at the top as the pawn does.

## Conventions (non-negotiable)

* Y up, **front = +Z**, pedestal bottom at y = 0, centred on x/z. Units = board squares. **Character right = -X, left = +X.**
* Everything is modelled directly in **world rest-pose coordinates** (the pose in the Idle t=0 frame). Bones have no rest rotation.
* Winding is CCW from outside. `lathe` profiles are `(r, y)` listed counter-clockwise: **up the outer wall bottom-to-top, then back toward the axis** (solid on your left).
  Open shells (skirts, cloth) are single sided: use `EH_Cloth` (double sided) or add an inner wall.
* Bones: use exactly the sheet's contract bones (`docs/art/README.md` section 0). Do not add bones. Sockets are nodes under bones (`rig.socket`).
* Budgets (validator): LOD0 pawn 15k / rook 18k / bishop 22k / queen,king 30k / knight 35k; LOD1 4k/5k/6k/8k/8k/9k; fragments <= 6k. `Piece.build` auto-makes LOD1 (QEM, ~25 %) and fragments (count by role).
  **Keep LOD0 about 3 % under budget**; print `p.tri_count()` while building (the pawn sits at 14.8k).
* Emissive discipline: 1-2 focal points per piece (art README section 3). The pawn has the boss rune + a thin groove seam only.
* GLB size: textures are 256 px tiles (1024 px/m), JPEG; fragments use 128 px. Pawn is ~1.9 MB / 0.8 MB before meshopt/KTX2. Do not raise `tex_res`.

## Worked example (condensed from `pieces/emberhold_pawn.py`)

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, geom as g
from geom import merge, smoothstep
from piece import Piece
from rig import Rig, Clip

def build():
    rig = Rig()                                    # contract bones, absolute rest positions
    rig.add("root", None, (0, 0, 0)); rig.add("body", "root", (0, .56, 0)); rig.add("spine", "body", (0, .62, 0))
    rig.add("head", "spine", (0, .90, 0)); rig.add("top", "spine", (0, .86, -.09))
    rig.add("arm_L", "spine", (.19, .86, 0)); rig.add("hand_L", "arm_L", (.205, .77, .03))   # hand_* pivot at the ELBOW
    rig.add("arm_R", "spine", (-.185, .86, 0)); rig.add("hand_R", "arm_R", (-.20, .76, 0))
    rig.socket("socket_weapon_R", "hand_R", (-.15, .64, .09)); rig.socket("socket_impact", "body", (-.03, .62, .55))
    rig.socket("socket_head", "head", (0, 1.04, 0))

    idle = Clip("Idle", 3.0, loop=True)            # rot = Euler degrees delta; ease on a key shapes the segment ENDING at it
    idle.keys("spine", "rot", [(0, (0, 0, 0)), (1.5, (1.6, 0, 0), "in_out_cubic"), (3.0, (0, 0, 0), "in_out_cubic")])
    attack = Clip("Attack", 2.0, fps=60)           # strike must land at impact_time exactly
    attack.keys("arm_R", "rot", [(0, (0, 0, 0)), (.82, (-165, 0, 0), "in_out_cubic"), (.95, (-75, 0, 0), "in_cubic"), (2.0, (-20, 0, 0))])
    clips = [idle, ...]                            # Idle, Move, Attack, HitReact, Victory are all required

    p = Piece("emberhold", "pawn", rig, clips, impact_time=0.95, strike_range=0.55, attack_style="melee")

    # 1. a tapered swept limb + a lathe + a bevelled plate (never plain cylinders)
    leg = g.tube([(.075, .27, .02), (.078, .34, .01), (.080, .43, .02), (.070, .58, 0)], [.034, .040, .046, .060],
                 sides=8, samples=2, cap=None, up=(0, 0, 1))
    p.add("leg_L", leg, "EH_Cloth", "body", uv_scale=2)                       # name, mesh, material, bone
    helm = g.lathe(g.spline(np.array([(.058, .926), (.0645, .966), (.043, 1.014), (0, 1.0245)]), 1), 20).uv_box(0.25).noised(.0016, 40, 2)
    p.add("helm", helm, "EH_Bronze", "head")                                  # lathe poles distort UVs: use uv_box on domes
    lame = g.plate(.135, .082, .010, radius=.0045, bend_r=.12, taper=lambda t: 1 - .18 * (t + 1) / 2, drop_back=True)
    p.add("tasset", lame.rotated(-14, 0, 0).translated(0, .50, .118), "EH_Bronze", "body")

    # 2. 2-bone soft skin (cloth/fur): weight slides from `bone` at coordinate blend[0] to `bone2` at blend[1] along axis
    cloth = g.cloth_panel(.13, .215, cols=7, rows=6, flare=.35, curve=40, thickness=.004).translated(0, .628, .118)
    p.add("tabard", cloth, "EH_Cloth", "spine", bone2="body", blend=(.60, .46))

    # 3. repeated details: instances (pointing along +Y -> aligned to normals); vertex tint = soot gradient after the AO bake
    rivets = g.instances(g.dome(.0105, .009, 6, 1), [(.381 * np.sin(t), .123, .381 * np.cos(t)) for t in np.arange(12) * np.pi / 6],
                         [(np.sin(t), 0, np.cos(t)) for t in np.arange(12) * np.pi / 6])
    p.add("trim_rivets", rivets, "EH_Bronze", "root", lod1=None)             # lod1=None: dropped from LOD1 and fragments
    plinth = g.lathe([(0, 0), (.39, 0), (.40, .01), (.40, .07), (.37, .10), (.36, .20), (.34, .22), (0, .22)], 48, crease=40)
    p.add("stone", plinth, "EH_Stone", "root", tint=lambda P: .55 + .45 * smoothstep(0, .2, P[:, 1]))

    return p.build()                                # (piece_glb_bytes, fragments_glb_bytes, stats)
```

## API cheat-sheet

### `geom.py`
* **Mesh**: `P F N UV C A`; `.translated(x,y,z) .scaled(sx[,sy,sz]) .rotated(rx,ry,rz[,pivot]) .rotated_axis(axis,deg,pivot) .at(pos,rot,scale) .aimed(dir,pos)` (local +Y -> dir),
  `.mirrored('x') .symmetrized('x') .flipped() .merge via merge([..])`, `.shade(crease)`, `.subdivided(n) .subdivided_to(max_edge)`, `.noised(amp,freq,octaves,seed)`, `.dented(count,radius,depth,seed,region)`,
  `.displaced(fn(P,N))`, `.uv_box(tile) .uv_planar(axis) .uv_cylindrical() .transformed_uv(scale)`, `.tri_count`, `.bounds()`.
* **Surfaces**: `lathe(profile, segments, sweep, shape=, shape_v=, round_profile=)` (`shape_v(theta, v)->(R,K)` gives per-height folds), `loft(rings(R,K,3), closed, cap_start, cap_end)`,
  `tube(path, radii, sides, samples, cap='round'|'flat'|None, cap_steps, up, twist, ellipse, section, closed)`, `extrude(poly2d, depth, bevel, bevel_segments)`,
  `extrude_plane(poly, depth, 'YZ'|'XZ')`, `plate(w,h,t, radius, bend_r, curve_y, taper, inner_x, drop_back)`, `rounded_box`, `superellipsoid(radii, e_lat, e_lon, rings, segments)`,
  `sphere ellipsoid torus(R,r,segments,sides,arc) cylinder cone disc_ring capsule dome blade(length,width,thickness,tip,taper,fuller,rows)`,
  `crystal`, `crystal_cluster(count,spread,height,radius,tilt,up)`, `cloth_panel(width,height,cols,rows,fold_amp,folds,flare,curve,thickness)`.
* **2D helpers**: `spline(points, samples)`, `bevel_polyline(points, radius, segments, closed, sharp)`, `ngon`, `rect_poly(w,h,r)`, `teardrop(length,width,n)`, `offset_polygon`, `triangulate_polygon`.
* **Shaping**: `warp(mesh, fn(P)->P)`, `bend(mesh, arc_axis, normal_axis, radius)`, `instances(base, positions, normals, scales, spins)`, `scatter_on_surface`, `decimate(mesh, target_tris)`, noise `noise3 fbm3`.
* Triangle cost reminders: tube = `sides * 2 * rings`; keep `samples<=2`, `sides 6-8`, `cap=None` where the end is hidden; `rounded_box` ~100 tris (use `extrude(rect, bevel_segments=1)` ~35); torus 10x4 = 80.
  `torus/tube` with `closed=True` is the way to draw rolled edges and rings. Noise displacement works on any mesh but only shows where vertices are dense.

### `textures.py`
`get_texture_set(name)`; names: `EH_Bronze EH_Steel EH_Leather EH_Fur EH_Cloth EH_Stone EH_Ember EH_EmberVein EH_Skin EH_Interior`, `RH_Obsidian RH_Ice RH_Frost RH_Silver RH_Glow RH_Interior`.
Add one with `register(MaterialDef("EH_Wood", gen_fn(n, seed) -> TextureSet, seed))` (see `gen_bronze`). `EH_Stone` carries NO emissive (dark pedestal); `EH_Ember` = focal glow (x6);
`EH_EmberVein` = dim seam (x1.8); `RH_Ice` writes KHR transmission/volume/ior. Textures tile every **0.25 m** and `Mesh` UVs default to that tile, so just pass `uv_scale=2` for finer detail (integer only: seams stay closed).
`bake_vertex_colors` is called by `Piece.build`: voxel-traced AO tinted with the material's grime colour + curvature edge wear (`TextureSet.wear`, `baked_tone`, `ao_strength`). `bake=False` for emissives.

### `rig.py`
`Rig.add(name, parent, abs_pos)`, `Rig.socket(name, bone, abs_pos)`. `Clip(name, duration, loop, fps)`: `.key(bone, 'rot'|'pos'|'scale', t, value, ease)`, `.keys(...)`, `.wave(bone, path, axis, amp, cycles)`, `.hold`, `.loop_close()`.
Rotation is Euler degrees X,Y,Z about the bone pivot, **+rx pitches +Y toward +Z: a hanging arm raises forward/up with negative rx**; `+ry` turns +Z toward +X; `+rz` tips +Y toward -X.
Easings: `linear in/out/in_out_quad|cubic, in_expo out_expo, in_back out_back in_out_back, out_elastic, smooth, hold`. STEP tracks: `key(..., step=True)` (scale toggles). Do not translate a child bone away from its parent (rigid skin
would tear the limb apart): rotate, or translate the *parent*. Weapons that must appear/disappear use `weapon_summon`-style scale tracks on a contract-allowed node.

### `piece.py`
`Piece(faction, role, rig, clips, display_name=, attack_style=, impact_time=, strike_range=, seed=)`; `.add(name, mesh, material, bone, bone2=, blend=(v0,v1), axis=1, lod1="auto"|"keep"|None, bake=True, occluder=True, frag=True, uv_scale=None, tint=None)`;
`.tri_count()`; `.build() -> (piece_bytes, fragment_bytes, stats)`. LOD1 and fragments are automatic. Fragments: 20/30/30/30/40/40 by *role*, `{EH,RH}_Interior` insides, inward thickness ray-limited. Extras/node names/skin/sockets/clips are written per contract.

## Checklist before reporting a piece done
1. `python3 tools/forge/build_all.py --only <id>`: validator PASS for piece and fragments; LOD0 under budget with ~3 % margin; GLB < ~2 MB.
2. `npm run turntables -- --ids <id>` and `--clip Attack`: look at the PNGs; silhouette at small size, one signature shape, material variety, emissive count, impact frame on the blow, nothing detached in any clip.
3. Faction pair `role_{role}.png`: Emberhold mid-value warm, Rime very dark with bright accents (greyscale test).
4. Delete scratch PNGs (`*_single_*.png`); keep only `{id}.png`, `{id}_attack.png`, `role_*.png`.
