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
| `rig.py` | `Rig` (bones/sockets/aliases by absolute rest position) and the `Clip` keyframe DSL (+ dense baked tracks) |
| `anim/` | the animation toolkit: skeleton templates, smooth-skin auto-weights, curves, IK animator, gait/idle/strike generators, stick-figure debug (see below) |
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
* Bones: the contract bones must exist and keep their meaning; EXTRA bones are allowed (and expected: see **Animation toolkit**). Sockets are nodes under bones (`rig.socket`).
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
would tear the limb apart): rotate, or translate the *parent* (the toolkit's pelvis `pos` + leg IK does this for you). Weapons that must appear/disappear use `weapon_summon`-style scale tracks on a contract-allowed node.

### `piece.py`
`Piece(faction, role, rig, clips, display_name=, attack_style=, impact_time=, strike_range=, seed=)`; `.add(name, mesh, material, bone, bone2=, blend=(v0,v1), axis=1, lod1="auto"|"keep"|None, bake=True, occluder=True, frag=True, uv_scale=None, tint=None)`;
`.tri_count()`; `.build() -> (piece_bytes, fragment_bytes, stats)`. LOD1 and fragments are automatic. Fragments: 20/30/30/30/40/40 by *role*, `{EH,RH}_Interior` insides, inward thickness ray-limited. Extras/node names/skin/sockets/clips are written per contract.

## Checklist before reporting a piece done
1. `python3 tools/forge/build_all.py --only <id>`: validator PASS for piece and fragments; LOD0 under budget with ~3 % margin; GLB < ~2 MB.
2. `npm run turntables -- --ids <id>` and `--clip Attack`: look at the PNGs; silhouette at small size, one signature shape, material variety, emissive count, impact frame on the blow, nothing detached in any clip.
3. Faction pair `role_{role}.png`: Emberhold mid-value warm, Rime very dark with bright accents (greyscale test).
4. Delete scratch PNGs (`*_single_*.png`); keep only `{id}.png`, `{id}_attack.png`, `role_*.png`.

## Animation toolkit (`tools/forge/anim/`)

The old pieces were rigidly skinned statues with 6 bones and hand-typed key tables. The pawns (`pieces/emberhold_pawn.py`,
`rime_pawn.py`) are now the reference for the new workflow: **full skeleton -> smooth skin -> procedural, IK-driven clips baked to dense
LINEAR tracks**. Port the other 10 pieces the same way (knights use `quadruped_rig` + `quadruped_gait`). Run `python3 tools/forge/build_all.py --only <id>`.

### 1. Skeleton templates (`anim/templates.py`)
`humanoid_rig(JOINTS, weapon=pos, cape=[p1,p2,p3], shield=pos)` builds: `root > body(pelvis) > spine > chest > neck > head`, `top` (bedroll / backpack node,
under chest), `clavicle_X > arm_X (UPPER ARM, pivot at the shoulder) > hand_X (FOREARM, pivot at the ELBOW: legacy contract name) > wrist_X (the hand)`,
`thigh_X > shin_X > foot_X > toe_X`, `weapon` (under `wrist_R`; pass `weapon_parent="body"` for a sheathed sword), optional `cape_1..3` chain under `top`, optional `shield`.
Aliases: `upper_arm_X`, `forearm_X`, `fist_X`, `pelvis` (use them in `Piece.add`/`Skin`; not exported). Joints are ABSOLUTE rest positions measured off your meshes
(`..._R` mirrors `..._L` unless given). Rules: legs must be slightly bent at rest (hip-ankle distance < thigh+shin) and the elbow/knee positions must sit on the meshes' own
bend; `socket_weapon_R`/`socket_cast` go under `wrist_R`/`wrist_L`, `socket_impact` under `body`.
`quadruped_rig(J)` (knights): `root > body(rump) > mount_body(barrel) > mount_chest(withers) > neck_1 > neck_2 > mount_head > jaw`, `top` (saddle) under mount_body,
`hind_upper/lower/hoof_X` (hip -> hock -> fetlock) under body, `fore_upper/lower/hoof_X` under mount_chest, `tail_1..3`. Mount the rider by building the humanoid with
`pelvis_name="rider_pelvis"` and re-parenting to `top` (add the rider bones to the same Rig).

### 2. Smooth skinning (`anim/skin.py`)
Weights are computed from the final REST positions at write time (LOD0, LOD1 and fragments stay consistent; <= 4 influences, normalised). `Piece.add(name, mesh, mat, None, skin=...)`:
* `Skin.rigid(bone)` or simply `bone="shin_L"`: armour plates, weapons, crowns, pedestal. Layered plates follow the bone they sit on (greave/kneecap -> `shin`, cuirass -> `chest`, lames -> `spine`, pauldron -> `arm`, vambrace -> `hand_X`).
* `Skin.chain([bones], pre="body", tip=pt, zone=0.4)`: limbs/torso/neck/cape. Each vertex is projected on the bone polyline; weight slides between neighbouring bones with a smoothstep over +-zone x (shorter adjacent bone) around each joint, `pre` blends into the parent above the first joint. 0.35-0.45 = no candy-wrapper pinch.
* `Skin.nearest([(bone, p0, p1), ...], tau=0.03, bias={...})`: softmax of distance to bone SEGMENTS: skirts, tabards, loincloths. Combine with `Skin.gradient(rigid_body, nearest, axis=1, v0=0.58, v1=0.50)` so the waist follows the pelvis and the hem follows the thighs.
* `limb_tube(ctrl, radii, joints=[knee], spacing=.03, joint_spacing=.015, joint_zone=.045, sides=8)`: a swept tube with DENSE rings around the joint, so the blend zone has geometry to bend. Build ONE continuous tube through shoulder-elbow-wrist (or hip-knee-ankle) instead of one capped tube per bone. Two meshes sharing one chain skin also deform seamlessly (Rime thigh + shin).
Budget: dense joint rings cost ~16 tris each; pay for them by trimming repeated details (tufts, rivets, lips). Pawn LOD0 stays < 15k (14.85k / 13.3k).

### 3. Animation (`anim/curves.py`, `animator.py`, `motion.py`)
```python
from anim import Animator, Curve, Fn, Wave, humanoid_rig
from anim import motion as M
a = Animator(rig)
M.plant_feet(a)                                   # leg IK goals in plinth space + pelvis reach clamp (legs never over-extend / pop)
a.goal("ik_hand_R", ("arm_R","hand_R","wrist_R"), spaces=(("body", 1.0),), rot=(0,0,0))   # hand pinned to the hilt in PELVIS space
M.idle(a, period=3.0)                             # breath + weight shift (+ head stabilisation); loops when period == clip length
a.rot("chest", Curve([(0,(0,0,0)), (0.6,(12,-20,0),"anticipate"), (0.95,(18,22,0),"snap_in"), (2.0,(0,0,0),"in_out_cubic")]))   # Euler deg deltas
a.pos("body", Curve([...]))                       # metres, delta from rest
M.set_foot(a, "foot_L", pos=Curve([...]), rot=Curve([...]))                              # absolute-in-plinth foot targets (delta from rest ankle)
a.secondary(["top"], driver="chest", freq=2.3, zeta=0.32, accel=0.05)                   # spring follow-through / overlap
clip = a.bake("Attack", 2.0, loop=False, fps=60, keep_times=(0.95,))                    # dense LINEAR quaternion tracks, key-reduced
```
* **Curves**: keys WITHOUT an ease flow through a monotone cubic spline (organic arcs, never overshoots); an ease flag stops/starts there. Eases: `rig.EASE` names, presets `ease`, `ease_in_out`, `anticipate`, `snap_in`, `whip`, `soft_land`, `overshoot`, CSS bezier 4-tuples, `("spring", overshoot, half_cycles)` for settle. `{"tan":"flat"}` on a key = hold. `Curve(keys, loop=period)` for cycles. `Wave`, `Fn`, signals add with `+`, scale with `*`; `step_signal`/`pulse` for blend weights.
* **IK goals** (`Animator.goal`): 2-bone IK with `spaces=(("chest", w1), ("body", w2), ("world", w3))` blends (draw a sword: pelvis space -> chest space); `pos` is a DELTA from the rest joint in that space (`M.abs_pos(rest, curve)` lets you author absolute points), `rot` an Euler/3x3 (`M.aim(axis_rest, direction_curve)` = "point the blade here"), `weight` IK<->FK, `pole_target/pole_mix` steer the elbow/knee. A target equal to the rest pose yields the identity pose, so rest never pops. Mind arm reach (~0.25 m for pawns).
* **Gaits**: `M.biped_gait(a, period, stride, lift, duty, bob, sway, roll, twist, lean, arm_swing, toe_off, strike)` = contact/down/pass/up from foot paths + pelvis dip/sway/tilt/yaw, counter-twisting spine, arm counter-swing (set `arm_swing=0` for arms held by IK), heel-off/toe-up foot pitch, head stabilisation. `M.quadruped_gait(a, period, "walk"|"trot"|"canter", ...)` (leg phase offsets, spine wave, head bob, tail). Stance feet are exactly planted; `stride` sweeps them back over the plinth (0 = march on the spot). Contact windows are written to the clip's glTF animation `extras.footContacts` (`{ "foot_L": [[t0,t1],...] }`) for footstep audio/dust.
* **Strikes**: `M.strike_keys(rest, wind, hit, follow, t_wind, t_hit, ...)` builds anticipation -> wind -> snap -> hold -> follow -> recover keys; give proximal joints `lead=.04-.07` so pelvis -> chest -> arm -> weapon fire in sequence. Bake attacks at `fps=60` and pass `keep_times=(impact,)`: the weapon channel must reach its hit pose exactly at `impactTime`.
* **Surrender**: `M.release_weapon(a, "weapon", t0, floor_y, rest_y_off, axis_rest, heading, land_xz, up_local=blade_thickness_axis)` = free fall + two bounces + settle flat on the plinth. Kneel = lower the pelvis by (knee_y + thigh - hip_y), `set_foot` ankle to `knee - shin` behind it, foot pitch ~172 deg (instep down); the reach clamp and IK keep knees on the plinth.
* **Debug**: `anim.debug.stick_strip(animator, animator.sample(dur, fps, loop), times, "x.png")` renders front/side stick figures without a GLB build; `animator.sample()` also gives world positions to assert reach/contact numerically.

### 4. Porting checklist
1. Measure joints off the existing meshes; `humanoid_rig`/`quadruped_rig`; keep sockets. 2. Replace per-limb capped tubes with `limb_tube` + `Skin.chain`; cloth with `nearest`/`gradient`; plates `bone=`. 3. Keep LOD0 under budget (print `p.tri_count()`). 4. Write one `clip_*` function per clip returning `(animator, duration, loop, fps, keep_times)` and a `make_clips(rig)`. Keep clip durations and `impactTime`/`strikeRange` unchanged. 5. `build_all.py --only <id>`; render sheets and a strip per clip; look for tearing at knees/elbows/shoulders, plates poking through skin, feet leaving the plinth. 6. Surrender must end on the knees without sinking into the plinth.
