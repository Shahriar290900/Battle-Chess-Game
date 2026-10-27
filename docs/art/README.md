# Code-Forge Style Guide (shared by all 12 pieces)

Build-ready numbers for the Python/numpy forge. Sources: art-bible.md, capture-choreography.md,
asset-pipeline.md, `src/contracts/assetContract.ts`. Every sheet `docs/art/{asset_id}.md` obeys this file.
All designs are original; never reference existing franchises, characters or commercial sets.

**Revision 2 (recognisability pass).** Playtesters (chess players) asked for pieces they can recognise instantly and for proper contrast. Every sheet now carries a Staunton-style identity cue, exaggerated 15-20%, plus the new rig template bones (section 0) and 7 jointed clips. Knights are now **war-horses**. See sections 10 (recognisability tests), 11 (value / colour separation) and 12 (identity cue table). Where this revision conflicts with an older number in sections 0-9, the later statement wins.

## 0. Conventions

**Space.** 1 unit = 1 board square. glTF Y-up, front = +Z, base at y = 0, centred on x/z.
Character **right = -X**, character **left = +X** (facing +Z). `socket_weapon_R` therefore sits at x <= 0
for humanoids. Mirrored parts list the **+X (left)** side; the forge mirrors to -X and binds to the `_R` bone.

**Part notation (used in every part table).**

| Tag | Meaning |
|---|---|
| `L[(r,y)...]` | lathe about the Y axis through `ax=(x,z)` (default 0,0). Profile listed bottom to top. `sides=N` for faceted lathes; `axis=Z` (or `X`) spins about a horizontal axis through `c=(x,y,z)`, profile is then (r, offset along that axis), used for shields, discs, halos. |
| `S[(x,y,z;r)...]` | swept tube along the 3D polyline (Catmull-Rom, 6 samples/segment), radius `r` linearly interpolated; `r=a*b` = elliptical section (a = width in X, b = the other axis perpendicular to the path); `sec=N` ring sides (default 10; 6-8 for faceted ice/obsidian); `cap=round/flat`. |
| `E[(x,y)...]@z0..z1 b=` | bevelled extruded polygon: points in the front (XY) plane, thickness from z0 to z1, bevel `b` (2 segments). `plane=YZ` or `XZ` when the polygon lies in another plane (points are then (y,z) or (x,z)). |
| `B c=(x,y,z) s=(w,h,d) rd= e=` | rounded box or superellipsoid: centre, full size, corner radius `rd`, optional exponent `e` (2 = ellipsoid, 4 = pillowy block, 8+ = hard box). `rot=(rx,ry,rz)` degrees. |
| `C base=(x,y,z) n= len= r= tilt=` | crystal/shard cluster: `n` hex prisms with pointed tips, length range, base radius range, tilt cone half-angle around the up vector `up=(x,y,z)` (default +Y). |
| `+noise a=` | noise displacement amplitude in units after construction (frequency ~ 9/unit unless stated). |
| `xN` | repeat N times (ring or row, spacing given). |
| `M` | mirrored pair across x = 0 (numbers given are the +X side). |
| **S** / **F** | silhouette-critical part / focal emissive part: never dropped when merging for budget. |

**Rotation / translation notation in clip tables.** Degrees, Euler XYZ in the bone's local space about its pivot.
`+rx` pitches the bone's +Y toward +Z (torso leans forward; a hanging arm swings **backward**; a **forward/up arm
raise is negative rx**). `+ry` turns +Z toward +X (character's left). `+rz` tips +Y toward -X (character's right). Translations are in
units along parent-space axes. Easing: `io` = ease in/out, `out`, `in`, `lin`, `snap` (<= 0.04 s), `bk` = back-out overshoot.
Unlisted bones hold the previous keyed value (rest pose = 0 everywhere). Every looping clip ends on its t=0 value.

**Scale keys** (`sx/sy/sz`) are allowed on `body`/`top` for squash and stretch (non-humanoids especially) and on the queen's `weapon_summon` node. **`weapon_summon`** (queens) is a non-skinned node parented to the `wrist_R` bone (origin = grip, `socket_weapon_R`), scale 0 in every clip except Attack; its parts are modelled in grip-local coordinates (+Y along the shaft).

**Bones (rig templates in `tools/forge/anim/templates.py`; the forge places joints by absolute rest-pose positions measured off the meshes; each sheet section 3 lists the joint positions and an authoritative binding).**

- **Humanoid** (`humanoid_rig`): `root` (pedestal, never animates) > `body` (= pelvis, lunges up to +/-0.3) > `spine` > `chest` > `neck` > `head`. `top` (child of `chest`) is the secondary overlay: cloak root, backpack, crown ring, halo, censer pendulum or rune-orbit centre. `clavicle_L/R` (child of `chest`) > `arm_L/R` (**upper arm**, pivot at the shoulder; alias `upper_arm_*`) > `hand_L/R` (**forearm**, pivot at the elbow, legacy name; alias `forearm_*`) > `wrist_L/R` (the hand and what is gripped; alias `fist_*`). `thigh_L/R` (child of `body`) > `shin_*` > `foot_*` > `toe_*`. Optional: `weapon` (child of `wrist_R`; the held weapon, the thing Surrender drops), `shield` (child of `hand_L`, i.e. the forearm), `cape_1..3` (chain under `top`).
- **Quadruped** (`quadruped_rig`, knights): `root` > `body` (= rump) > `mount_body` (barrel) > `mount_chest` (withers) > `neck_1` > `neck_2` > `mount_head` (pivot at the poll) > `jaw`; `top` (= the rider's saddle seat, child of `mount_body`); hind legs `hind_upper/hind_lower/hind_hoof_L/R` under `body`; fore legs `fore_upper/fore_lower/fore_hoof_L/R` under `mount_chest`; `tail_1..3` under `body`. The rider is `humanoid_rig(..., pelvis_name="rider_pelvis")` re-parented under `top`; its `weapon` carries the lance/glaive.
- **Rooks**: `root, body, top` (+ optional `weapon`: the Emberhold ram beam). No limbs; squash/stretch and rock stand in for joints.
- Rigid-bound 100% to one bone, except cloth/cloak/mantle/mane/tail parts marked `~soft`, which blend 2-3 bones (pivot-distance falloff). Legacy Bone columns in the part tables map as: torso parts on `spine` -> `spine` (below the waist line + 0.06) or `chest`; `hand_*` = forearm; gauntlet hands -> `wrist_*`; leg, boot and greave parts that say `body` -> `thigh`/`shin`/`foot`; held weapon parts -> `weapon`. **Each sheet's section 3 "Binding" overrides the Bone column.**
- Legs are real now: hips, knees, ankles and toes bend with the feet IK-planted (`plant_feet`); statues still glide on their plinths for Move (pelvis bob, lean, counter-twist, stride 0.03, lift 0.05). Surrender is a real kneel.

## 1. Proportions

Collector miniatures, not chibi: head ~ 1/6.5-1/7 of figure height, believable hands (hand length = 0.75 head height),
shoulder width 2.2-2.6 heads, forearm and shin thicker at the proximal end.
"Figure height" = plinth top (y 0.22) to top of the head (helm without crest). Total piece height is the contract height to the tallest feature.

| Role | Total H | Figure (0.22 -> head top) | Head height | Heads tall | Notes |
|---|---|---|---|---|---|
| Pawn | 1.05 | 0.82 (E) / 0.82 hunched 18 deg (R) | 0.115 / 0.105 | ~6 incl. the 0.164 helm | **round helm** (Ø0.164, top 1.05 with its button/knob) sets the top; shield Ø0.36 / spikes <= 0.95 stay below it |
| Rook | 1.20 | tower | - | - | tower mass 0.22 -> 1.00, flared crenellated top (Ø0.67) with **5 merlons** y 1.04-1.18, flames/orb to 1.20 |
| Knight | 1.30 | rider **crouched** (seat y 0.80 -> helm top 1.10) | rider head 0.08 | ~6.5 standing-equivalent | war-horse: withers 0.80, poll 1.20, ears / mane tips 1.30; **everything above 1.10 is horse**; lance tip 0.915, glaive hook 1.18 |
| Bishop | 1.40 | 1.05 (E) / 1.00 (R) | 0.15 / 0.145 | 7.0 / 7.1 | **mitre** (top 1.348 E / 1.322 R) is the dominant head shape; staff crook sets the 1.40 top |
| Queen | 1.55 | 1.20 | 0.17 | 7.0 | **open coronet of 9 tines** adds 0.16 (tips 1.55); Rime halo apex 1.51, behind |
| King | 1.70 | 1.25 (to head top) | 0.18 | 6.9 | broadest piece; **closed crown + cross** add 0.24-0.29 to 1.70 |

Role silhouette envelopes at the plinth top (max width x depth, units), a hard check:
pawn 0.55 x 0.50, rook 0.67 x 0.67 (Emberhold ram: 0.76 deep), knight 0.46 x 0.80 (long axis Z), bishop 0.50 x 0.50 (Rime rune ring excepted), queen 0.62 x 0.50, king 0.74 x 0.56. Crowns, mitres and helms: king crown <= 0.24 wide, queen coronet 0.21, mitre 0.18, pawn helm 0.17.
Nothing but weapons or horns may exceed 0.80 horizontally (pedestal Ø0.80; neighbours are 1.0 apart).
Minimum silhouette-defining feature thickness: **0.05** (about 2 px at 60 px piece height). Thinner = normal-map / material detail. Exception: thin arches, wires and chains (<= 0.012) are secondary detail and may never be the only thing that identifies a role; the identity cue itself (section 12) must obey 0.05.

## 2. Pedestal (identical geometry for all 12; only material differs)

Two-tier octagonal-to-round plinth, 0.22 tall, widest Ø0.80. Tier 1 (lower) is an octagon with **flats facing +-Z and +-X** (circumradius 0.40,
apothem 0.3696); it lofts into a circle over y 0.085-0.100. Tier 2 is round. For ring vertices at y <= 0.10:
`r(theta) = lerp(oct(theta), round_r(y), smooth(y))`, `oct(theta)=0.3696/cos(((theta mod 45deg)-22.5deg))`, `round_r` = profile radius below, `smooth` = 0 at y <= 0.085, 1 at y >= 0.100. Use 64 sides.

`PED_PROFILE` = `L[(r,y)]`, bottom to top (corners already bevelled 0.008):

| # | (r, y) | note |
|---|---|---|
| 0 | (0.000, 0.000) | bottom cap centre |
| 1 | (0.392, 0.000) | |
| 2 | (0.400, 0.008) | octagon circumradius reached |
| 3 | (0.400, 0.074) | tier 1 wall |
| 4 | (0.388, 0.085) | shoulder, start loft |
| 5 | (0.372, 0.100) | loft completes: round from here |
| 6 | (0.372, 0.108) | seat for trim band |
| 7 | (0.360, 0.108) | recess behind the band |
| 8 | (0.360, 0.138) | tier 2 wall |
| 9 | (0.372, 0.142) | tier 2 flare |
| 10 | (0.372, 0.178) | tier 2 wall |
| 11 | (0.352, 0.192) | chamfer |
| 12 | (0.352, 0.208) | top rim wall |
| 13 | (0.340, 0.220) | top rim bevel |
| 14 | (0.000, 0.220) | top plate (flat; feet stand at y = 0.22; usable foot radius <= 0.31) |

- **Trim band** (separate lathe, `sides=64`): `L[(0.360,0.110),(0.378,0.112),(0.380,0.122),(0.378,0.134),(0.360,0.136)]`.
  Emberhold: bronze, edge wear, 16 rivet domes (B r 0.012, y 0.123, r 0.381). Rime: `RH_Silver` wire with 16 notch cuts 0.012 wide and 8 tiny frost clusters on the upper side.
- **Top plate detail**: radial seams every 22.5 deg, depth 0.004; ring groove at r 0.28, depth 0.004. Emberhold: groove carries **ember cracks** (emissive 2.0).
  Rime: groove filled with frost (white, rough 0.9).
- **Emblem** (one per piece, inset, on tier 1's +Z flat): disc plaque Ø0.080 centred at `(0, 0.044, 0.3696)`, inset 0.006, with a raised 0.004 emblem.
  Emberhold: anvil (E polygon `(-.026,-.010),(.026,-.010),(.020,.002),(.010,.004),(.010,.014),(-.026,.016),(-.034,.010)`) inside a ring of six flames (six teardrops r 0.005 on a Ø0.066 circle); bronze on soot.
  Rime: six-pointed snow-crystal (three crossed bars 0.060 x 0.008 at 0/60/120 deg) pierced by a downward blade (E triangle 0.008 wide, 0.058 long); silver on obsidian.
- **Materials**: Emberhold pedestal = `EH_Stone` (chipped edges, soot gradient toward the bottom, ember cracks), `EH_Bronze` trim.
  Rime pedestal = `RH_Obsidian` tiers, `RH_Silver` trim, `RH_Frost` on faces with normal.y > 0.7 (top plate 40% coverage), 3 small crystals (C n=3 len 0.04-0.07) at the rear-left octagon corner.
- Binds to `root`. <= 1.8 k tris. Strong baked AO in the crevice at y 0.108.

## 3. Materials and palette

> Luma and roughness values in this table are superseded by section 11.4 (revised for board separation and rim lighting); colours/ids stay.

Procedural texture generators: hammered bronze, blackened steel, leather, fur, cloth, stone with ember cracks, obsidian, ice with cracks, frost.

| Material id | Colour (hex) | Luma | Spec | Use |
|---|---|---|---|---|
| `EH_Bronze` | #A8713A | 0.47 | metal 1, rough 0.35, hammered normal, edge wear (#C99A5E on curvature>0.6), cavity grime (#4A3220) | armour, crowns, rings |
| `EH_Steel` | #3B3A38 | 0.23 | metal 1, rough 0.45, polished edges (#7A7872) | blades, hooks, under-plates |
| `EH_Leather` | #5A3A22 | 0.22 | rough 0.7, grain + stitch normal | straps, belts, boots |
| `EH_Fur` | #6B5440 | 0.34 | rough 0.85, strong AO | collars, mantles |
| `EH_Cloth` | #5E1F1A | 0.17 | rough 0.9, weave normal, soot gradient to hem (#1E1814) | surcoats, cloaks |
| `EH_Stone` | #4A433C, soot #1E1814 | 0.28 | rough 0.85, chipped, ember cracks | pedestal, masonry |
| `EH_Ember` | #FF7A1A emissive x4-8 | 0.56 | bloom | cracks, gems, braziers, flame mane tips, horse eyes |
| `EH_Interior` | #FF7A1A core, #3A2418 shell | - | fracture faces glow | fragments only |
| `RH_Obsidian` | #10151C | 0.08 | metal 0.2, rough 0.12, conchoidal normal | armour plates |
| `RH_Armour` | #1C2E44 | 0.17 | metal 0.2, rough 0.25 | secondary plates |
| `RH_Silver` | #9FB4C4 | 0.69 | metal 1, rough 0.3 | wire, crowns, rune bands |
| `RH_Ice` | #7FD3F0 | 0.76 | transmission 0.9, IOR 1.31, rough 0.08, inner cracks (fake-ice on low tiers) | crystals, blades, horns |
| `RH_Frost` | #DCEFF7 | 0.92 | rough 0.9 | normal.y build-up, hems |
| `RH_Glow` | #6FF3FF emissive x3-6 | 0.85 | bloom | eyes, runes, lantern, cracks |
| `RH_Cloth` | #1C2E44 to #0A0E14, frosted hem | 0.12 | rough 0.9, stiff folds | tattered cloth |
| `RH_Interior` | #DCEFF7 pale cracked ice | - | fragments only | fragments only |

Emissive budget (hard cap): **1-2 focal points per piece**. Emberhold: ember in one brazier/gem/seam cluster (+ at most one more). Rime: cyan eyes count as one focal point; plus exactly one more (lantern, halo core, visor, rune).
Everything else is non-emissive; crack seams that follow part edges are allowed on <= 3% of surface area.

## 4. Greyscale value separation (faction)

Luma (Rec.709), area-weighted over the piece excluding the pedestal:

| Metric | Emberhold | Rime Host |
|---|---|---|
| Mean luma (albedo-weighted) | **0.42-0.50** (rendered 0.45-0.55) | **<= 0.12** (rendered <= 0.15) |
| Median luma | 0.40-0.50 | <= 0.10 |
| Pixels >= 0.65 | 8-14% (bronze edge wear, polished metal, ember) | **8-15%** (ice, silver, glow, frost; >= 0.85 on lit facets) |
| Pixels <= 0.12 | 10-18% (soot, AO, slit linings, cloth undersides) | >= 60% |
| Structure | broad warm **mid-high** value mass; light = metal edges + ember; dark = soot/AO accents | black mass with sparse, very bright accents; every extremity has a lit facet >= 0.88 and a shaded facet <= 0.20 |

The revised Emberhold target (0.50, equidistant from the light 0.70 and dark 0.30 squares) and the Rime target are derived in section 11.

Pedestals follow the rule (Emberhold stone mid-dark, Rime obsidian). Against the dark carved-stone board, Rime silhouettes are lifted by (a) frost on every upward face,
(b) silver wire lines on plate borders, (c) translucent ice at extremities (horns, blades, prisms). Never put pure black next to pure white on an Emberhold piece.

## 5. Silhouette readability (45 deg top-down, ~60 px tall)

At 60 px, 1 px = 0.02 units (pawn) to 0.03 (king).
1. **One signature shape per piece, enlarged ~15%**, on the outer silhouette, never inside it.
2. **Role ordering by outline** (Staunton cues, section 12): pawn = round helm over a compact body, no tall protrusion; rook = flat wide top with 5 merlon teeth and notches; knight = arched horse neck and head dominating the silhouette (only role with Z-length > 0.7), the rider low and secondary; bishop = narrow taper to a **pointed-oval mitre with a diagonal slit**; queen = **open ring of 9 tines** on a slim figure with a flared A-line skirt; king = widest shoulders + tallest crown, **closed dome topped by a cross**.
   Heights follow the contract; no feature of a lower role passes the next role's height.
3. **Factions**: Emberhold = convex, rounded, low centre of mass, horizontal bands, symmetric main shapes (shields, discs, crowns). Rime = tall/narrow, concave cuts, radiating spikes, asymmetric growths, floating parts with visible gaps.
   Test: silhouette perimeter / sqrt(area): Emberhold <= 4.3, Rime >= 5.0.
4. **Negative space**: at least one gap >= 0.06 between arm and torso (or main mass and weapon) per piece.
5. **Top-down check**: head/crown/mitre/helm/horse head is the highest-contrast element; weapons must not hide the head from a +Z, 45 deg-down view.
6. **3-value check**: the focal point is the lightest or the only emissive in the upper third.

## 6. Avoiding the toy look (mandatory)

- **No cylinders for limbs.** Every limb is a tapered `S[]` (radius changes >= 25% end to end) plus a sleeve/armour bulge sweep 3-6% larger over 40% of the length.
- **Layered plates**: overlapping plates with 0.006-0.012 gaps and offsets; >= 3 layers on the torso (underlayer, plate, trim). Plates get bevel 0.006-0.012 and a rolled lip.
- **Asymmetry**: each humanoid breaks mirror symmetry in >= 4 places (bigger pauldron, one-sided cloak, damaged horn, different glove, off-centre pouch). Mirroring only for the base layer.
- **Bevels everywhere**; no 90 deg edges on worn or held items. Ice/obsidian are faceted but chipped (chamfer 0.004).
- **Noise**: bronze/stone `a=0.003` at 40/unit (hammer), fur clumps `a=0.012` at 18/unit, ice `a=0.006` at 9/unit, cloth folds `a=0.008` at 12/unit.
- **Baked AO + edge wear** on every part; curvature drives bright metal (Emberhold) or frost/silver (Rime).
- **Three detail sizes**: large (> 0.15, silhouette), medium (0.04-0.15, plates, straps), small (< 0.04, rivets, stitches, runes: via texture or tiny B parts).
- **Emissive discipline** (section 3).
- **Weight in stance**: weight on one leg (hip tilt 3-5 deg), counter-tilted shoulders, head offset 1-2 deg. Only Rook/Bishop central masses may be perfectly symmetrical.
- **Hands**: mitten block with 4 finger grooves + thumb tube, always with a gauntlet cuff.

## 7. Clip rules (every sheet): 7 clips, jointed rigs

Required clips: **Idle, Move, Attack, HitReact, Victory**. Optional (all 12 sheets now provide them): **Taunt, Surrender**. `impactTime` and `strikeRange` are fixed per sheet (do not change them).

**Joint vocabulary** (degrees; Euler XYZ in the bone's local space; `+rx` pitches the bone's +Y toward +Z):
- Hanging arm / leg bones swing **backward** with `+rx`; a forward or up arm raise is `-rx`. Thigh forward = `thigh rx -`. Knee flex (shin folds back) = `shin rx +`. Elbow flex (forearm lifts forward) = `hand_* (forearm) rx -`. Wrist curl = `wrist rx`. Mount: hock flex (hoof comes forward-up) = `hind_lower rx -`; carpus fold (hoof goes back-up) = `fore_lower rx +`; neck up / head toss = `neck_*`, `mount_head rx -`; jaw open = `jaw rx +`.
- Feet are **IK-planted** (`plant_feet`, `contact=True`) unless a beat says "foot lifts"; the pelvis reach clamp keeps legs from over-extending. Skirted pieces (queen, bishop) still bend their knees: the skirt vertices are `~soft` to `thigh`.
- **Overlap and follow-through** (kinetic chain): on a strike the pelvis (`body`) leads by 0.06 s, `spine` by 0.03 s, `chest` 0.02 s, arms/weapon 0 (the weapon channel hits at `impactTime` exactly), `neck`/`head` lag 0.04 s; cloaks, capes, tails, braids and chains lag 0.06 s per link with 20% overshoot and settle in 0.3 s. Squash on landing/impact: `body` y -0.02 to -0.04. Every strike has anticipation (dip opposite to the strike by 18% of the wind-up angle) and a hold of 0.1-0.25 s.
- **Weight shifts**: hip tilt 3-5 deg (`body rz`), shoulders counter-tilt (`spine rz` -1.5), head offset 1-2 deg; a weight shift moves `body x` +/-0.010 over the planted feet.

**Clip contracts**
- **Idle** (loop 2-4 s, subtle): breathing = `chest` -1.4 to -1.8 deg rx, `spine` -0.6, clavicles rz +/-1.2, `body` y +/-0.004, `neck`/`head` +/-1-2 deg drift (the neck leads), one slow weight shift, `top`/cloth/tail lag. Ends on its t=0 pose.
- **Move** (loop 0.6-1.0 s): glide with `body` rx 4-8 deg lean, y bob 0.015-0.03 twice per loop, roll +/-3 deg, counter-twist `spine ry` +/-4-6, stride 0.03, lift 0.05; arms swing opposite the legs. Footstep callbacks at keys named `step` (2 per loop). **Knights** use the 3-beat gallop (0.9 s loop: R hind, L hind + R fore, L fore, then a 0.35 s suspension with the legs gathered; steps at 0.15 and 0.30), head dips on contact and nods up in flight, mane/tail stream back.
- **Attack** (1.2-2.4 s): anticipation >= 0.3 s (io), strike 0.08-0.15 s (snap), impact at `impactTime` exactly (`socket_impact` is on the blow then), hold 0.1, recover. Knights rear (0-0.4 s), hold, leap (engine arc 0.45-0.95, gather-launch-flight-reach), then strike at 0.88-1.00.
- **HitReact** (0.3-0.6 s): recoil away from +Z (rx -8 to -14 body/spine, head snaps back, knees give 6-10 deg), settles at 60% of the pose.
- **Victory** (1-2 s): weapon raised or planted, head up, ends in a held pose. Knights rear into a heraldic levade.
- **Taunt** (1.0-1.6 s, once): a provoking gesture toward the enemy king while giving check (the engine yaws the piece to the target); a character beat per piece (sheet section 7), ends back at rest.
- **Surrender** (1.5-2.5 s, once, **holds the last pose**): staggers, **releases `weapon` at 0.45 s** (`release_weapon`: free fall, 2 bounces, restitution 0.34, the weapon lies on the plinth), then a **real kneel**: `body` y -0.20 (pawn) to -0.31 (king), front thigh rx -70 to -75, front shin rx +90 to +95 (knee 90 deg, foot planted 0.08-0.12 forward), back thigh rx +20, back shin rx +105 to +110 (knee on the plinth, y 0.23), spine rx +10 -> +22, neck/head bow rx +20 -> +30, hands lowered (palms up or on the thighs). Pieces with no held weapon (Rime king, queens) lower their crown/halo/hands instead (stated per sheet); rooks slump and the fire/orb dies; knights kneel on both forelegs (`fore_upper` rx -50, `fore_lower` rx +120, `mount_chest` y -0.18) with the head bowed.
- Translation local to the parent bone; body lunge limit +/-0.3. No root motion.

## 8. Fragments (global)

Counts follow `FRAGMENT_COUNT` (pawn 20, rook/knight/bishop 30, queen/king 40), built from LOD1 volumes.
Emberhold: chunky slabs/blocks (0.05-0.12), irregular convex pieces (5-9 faces), `EH_Interior` glowing ember core; ~10% are small plates keeping bronze + rivets.
Rime: sharp elongated shards (aspect 2.5-4:1, 4-6 faces, pointed ends) with `RH_Interior`; ~25% thin triangular splinters; obsidian plates break to flat 3-5-sided shards with a bright inner edge.
Each sheet lists coarse vs. fine cells and what stays intact (weapon heads, crowns).

## 9. Delivery

Names: `{asset_id}`, `{asset_id}_LOD0`, `{asset_id}_LOD1`, `rig`, sockets as empties. Budgets: pawn <= 15k LOD0, rook <= 18k, bishop <= 22k, queen/king <= 30k, knight <= 35k.
Each sheet's part table is modelling intent; the forge may merge parts of the same material and bone for tri budget but must not drop **S** or **F** parts.

## 10. Recognisability rules

Goal: a chess player names the role in under a second, at ~60 px tall, from a seat camera at ~36 deg pitch, on a light **or** a dark square. The identity cue of each role (section 12) is a Staunton-style shape layered into the faction style, **exaggerated 15-20% over a natural proportion** and never hidden by anything the piece holds.

### 10.1 Test setup (run on every build; the turntable renderer can script it)
- Camera: pitch 36 deg, the game's seat FOV, orbit azimuths 0, +-45, +-90, 135, 180 deg. Render each piece alone on a **light square (luma 0.70)** and on a **dark square (luma 0.30)**, under the game lights, at two scales: **A = 60 px per piece height** and **B = fixed 1 px = 0.028 units** (king 60 px, queen 55, bishop 50, knight 46, rook 43, pawn 37 px).
- Silhouette = alpha mask (pedestal removed), Gaussian blur sigma 0.7 px, threshold 0.5. Greyscale = Rec.709 luma of the lit render.
- Every identity-cue size below is stated in units; at scale B divide by 0.028 for pixels (e.g. king cross 0.10 -> 3.6 px).

### 10.2 60 px silhouette tests (pass = all azimuths unless stated)
| Role | Silhouette test (top profile = max y per pixel column) | Pass criteria |
|---|---|---|
| **King** | the profile of the head region has exactly **one spike** (the cross) | cross >= 0.10 wide x 0.11 tall (>= 3.5 x 3.9 px at B); crown width >= 1.5x head width (0.216 vs 0.135); cross value >= 0.55 (E) / >= 0.80 (R); crown stack (band to cross top) >= 0.24 tall; Rime: dark gap >= 0.03 between helm and prism ring is visible |
| **Queen** | the profile of the head region has **>= 5 peaks** in the front 180 deg arc (9 around) | peak height >= 0.10 (3.5 px at B), tip spacing >= 0.07, no peak or centre element taller than the tall tines (+0.01), **no cross, no dome, no arch**; Rime: halo arc lies >= 0.04 below the tine tips and is dimmer (<= 0.35) |
| **Bishop** | the head is a **single pointed oval** (one apex) with one diagonal slit | mitre height/width 1.5-1.7 (0.28/0.176 E, 0.25/0.160 R), apex angle <= 70 deg, slit a continuous 35-42 deg segment >= 0.15 long, >= 0.030 wide at the surface, luma step >= 0.30 against its neighbours (dark oxblood on bronze; cyan glow on pale ice) |
| **Knight** | the contour above y 0.95 is an **S-curve neck ending in a wedge head** (55 deg below horizontal) | neck rise >= 0.40, head 0.28-0.32 long, **horse head+neck >= 60% of the silhouette area above y 0.95 in all 8 azimuths**, nothing of the rider above y 1.10 and nothing of the weapon above the poll (1.20), ears/mane tips = 1.30 |
| **Rook** | the top profile has **notches** | >= 4 notches (5 around) in any front 180 deg arc, each >= 0.157 wide x >= 0.13 deep (>= 5.6 x 4.6 px at B), merlon width >= crenel width, top width >= 1.2x the shaft top width (0.67 vs 0.54) |
| **Pawn** | the top profile is a **single dome** | helm width/height 1.25-1.35, helm Ø >= 0.16, nothing taller than the helm (+0.015 button/knob), total <= 1.05, compact: width/height <= 0.52 |

### 10.3 Top-down tests (orthographic, pedestal removed, 1 px = 0.01)
| Role | Footprint signature | Descriptor test |
|---|---|---|
| King | ring Ø0.22 with a **plus sign** at the centre and 4 radial arch bars | 4 convexity defects, central cross arms >= 0.10 span |
| Queen | ring of **9 spikes** (star) with a small dot (orb) at the centre | >= 9 convexity defects, no bars/cross |
| Bishop | **oval 0.176 x 0.127** with a diagonal line (the slit) | elongation 1.30-1.45, one linear groove at 35-42 deg |
| Knight | **teardrop** aligned with Z, head at the narrow end | elongation >= 1.8, length >= 0.78 |
| Rook | ring Ø0.67 with **5 gaps** | 5 convexity defects, circularity 0.85-0.95 |
| Pawn | **circle** (helm Ø0.164) beside a smaller disc (E shield) or a short blade (R) | circularity >= 0.88 for the helm |
Also: the head/crown/helm must be the highest-contrast element in the 45 deg top-down view (the weapon may not cover the head from +Z at 45 deg).

### 10.4 Confusion pairs that must never merge (check each at 60 px)
1. **King vs Queen**: cross + closed dome (1 spike) vs open tines (>= 5 peaks). The queen has no cross and no arch; the king has no spike ring.
2. **Queen vs Bishop**: 9 tines vs one smooth apex with a slit; the bishop has no spikes or crown, the queen no slit.
3. **Bishop vs Pawn**: pointed oval 1.6 tall vs dome 0.77 tall (aspect), slit vs button/knob.
4. **Rook vs Pawn**: flat wide notched top vs round dome.
5. **Knight vs everything**: the only quadruped; the horse head is the tallest thing; the rider never taller than the poll.
6. **Same role across factions**: the Emberhold and Rime pieces of one role must have the same silhouette signature (same IoU descriptors within 10%, different material/value); the factions differ by value and texture, the role by form.

### 10.5 Blind test (milestone gate)
10 chess players see 12 pieces x 3 azimuths for 0.5 s at scale A on light and dark squares. Pass: >= 95% correct role overall, >= 98% for king, queen, bishop and knight, >= 99% correct faction. A role below its threshold gets its cue scaled +10% (still inside the envelope) and the test repeated.

### 10.6 Cue rules
- Cue height >= 10% of the piece height (king crown stack 17%, queen coronet 13%, bishop mitre 20%, knight neck+head 35%, rook crenellated top 13%, pawn helm 12%), thickness >= 0.05 on the features that carry the cue (arches/wires are secondary).
- Cue silhouettes are on the outer outline, never inside it, and never occluded by held items from azimuth +-30 deg of the seat camera (the king's sword stays below the beard line; the bishop's censer stays >= 0.06 from the mitre; the Rime rune ring stays outboard of the mitre; the knight's lance/glaive stay below the poll).
- Exactly one cross in the set per faction (kings). No crowns on bishops, no mitres on pawns, no spikes taller than the helm on pawns, no arches on queens.

## 11. Value and colour separation guide

### 11.1 The board (what the pieces are read against)
Light squares **L = 0.70** luma (about #B3B3B3), dark squares **D = 0.30** (about #4D4D4D), measured in the lit render, near neutral (hue ~210 deg, saturation <= 0.06), roughness 0.65, no emissive, square-interior luma noise <= 0.04 so nothing on the board mimics a piece edge. Pieces stand on both colours and are seen against both, so every silhouette must separate from **both L and D**.

### 11.2 The separation law (edge values)
A silhouette-edge pixel (the outer 3 px ring) must be **>= 0.18 away from both squares**: |v - 0.70| >= 0.18 and |v - 0.30| >= 0.18. The only allowed edge bands are therefore:
- **dark: v <= 0.12** (soot, ambient occlusion, obsidian, slit linings, shaded facets),
- **mid: 0.48-0.52** (exactly between the squares: 0.20 from each),
- **bright: v >= 0.88** (polished edges, spec glints, lit ice facets, frost, ember/cyan glow).
Forbidden edge bands (they merge with a square): **0.18-0.40 and 0.60-0.80**. Check by measuring the 3 px edge ring on both square colours: >= 85% of the edge length must pass on each.

### 11.3 Faction value targets (greyscale of the lit render, pedestal excluded)
| | Emberhold (warm, mid-high) | Rime Host (low, bright accents) |
|---|---|---|
| Mean luma | **0.50 +-0.05** (albedo-weighted 0.42-0.50; the lit render adds the key/rim) | **<= 0.15** (albedo <= 0.12) |
| Body value | bronze/fur/stone 0.45-0.60 = 0.20 from both L and D | obsidian/armour 0.08-0.12 = 0.18-0.22 under D, 0.58-0.62 under L |
| Bands | <= 0.12: 10-18% (soot, AO, hems, slit linings) ; 0.12-0.40: 25-32% ; 0.45-0.60: 40-48% ; 0.60-0.88: 6-10% (edge wear, polished) ; >= 0.88: 2-4% (ember, glints) | <= 0.12: >= 60% ; 0.12-0.40: <= 20% ; 0.40-0.80: <= 6% ; **>= 0.80: 8-15%** (lit ice facets, frost, silver, glow) |
| Cross-faction check | the two factions' mean luma differ by >= 0.35 in greyscale | |
| Hue | bronze/ember 20-38 deg, saturation >= 0.45 (warm against the neutral board) | body hue 205-215 deg, saturation <= 0.35 ; glow 180-190 deg, saturation 0.6 |
| Focal | ember gem/mane/coals/orb only (1-2 clusters, section 3) | cyan eyes/slit/orb/core only (1-2 clusters) |

Why the targets differ: Emberhold at 0.50 is equidistant (0.20) from L and D, so its body never merges with either square; its edges alternate dark soot/AO (works on L) and bright bronze edge wear + rim light (works on D). Rime at <= 0.12 is black against L (Delta 0.58) and at least 0.18 under D; its extremities are rescued by **two-tone facets** (below) and the cold rim light.

### 11.4 Revised material values (these supersede the section 3 luma column)
| Material | Colour | Luma | Roughness | Notes |
|---|---|---|---|---|
| `EH_Bronze` | #BC8244 (was #A8713A) | 0.54 | 0.34 base, 0.30-0.38 allowed | hammered normal; edge wear #E0B070 (0.71) on curvature > 0.6; cavity grime #3A2618 (0.16); bevel >= 0.006 on every crown/helm/plate so a 1-2 px highlight rim appears at 60 px |
| `EH_Steel` | #55534F | 0.33 | 0.40 | polished edges #A8A49C (0.65) |
| `EH_Leather` | #6A4528 | 0.29 | 0.65 | |
| `EH_Fur` | #8A6E55 | 0.45 | 0.85 | strong AO keeps its dark side <= 0.15 |
| `EH_Cloth` | #7A2820 | 0.22 | 0.90 | soot hem #1E1814; used as the dark lining (slits, crown cap) that makes bronze read |
| `EH_Stone` | #6A6056, soot #1E1814 | 0.38 | 0.85 | pedestal and rook masonry; matte so the rim light does not blow it out |
| `EH_Ember` | #FF7A1A emissive x4-8 | 0.56 (renders >= 0.88) | - | bloom only here |
| `RH_Obsidian` | #10151C | 0.08 | 0.12-0.20 on facets only | facet normals differ >= 12 deg so the rim catches an edge on each plate |
| `RH_Armour` | #14202F (was #1C2E44) | 0.12 | 0.25 | keeps >= 0.18 under the dark squares |
| `RH_Silver` | #C6D6E2 | 0.83 | 0.30 | wire, crowns, rune bands: the bright edge line |
| `RH_Ice` | lit facet #E4F6FD (0.93) / shaded facet #173449 (0.19) | 0.93 / 0.19 | 0.06-0.12, transmission 0.9 (0.5 on rook merlons) | **two-tone rule**: every ice extremity (tines, mitre, crystals, merlons, cross, mane) shows a lit facet >= 0.88 and a shaded facet <= 0.20, so it separates from both L and D; flat 0.76 ice vanishes on a light square |
| `RH_Frost` | #DCEFF7 | 0.92 | 0.90 | caps, hems, bone-white skulls |
| `RH_Glow` | #6FF3FF emissive x3-6 | 0.85 | - | eyes, slits, orbs, cores |

### 11.5 Rim-light-friendly roughness and shape rules
- Lights: a warm key from the Emberhold side and a **cold rim light from the Rime side** (art-bible section 7). Every identity cue gets a **rim-catching edge**: bevel radius >= 0.006 (Emberhold bronze), facet angle step >= 12 deg (obsidian), chamfer 0.004 (ice).
- Roughness bands: polished metal 0.30-0.38 (broad but not mirror), stone/fur/cloth/leather 0.65-0.95 (they soak the rim and stay in the 0.12-0.45 body band), obsidian 0.12-0.20 on **facets only** (never on a flat area larger than 0.05 x 0.05: it would mirror the dark env and become a hole), ice 0.06-0.12 with a Fresnel edge brightening, frost 0.90. No roughness < 0.20 on any Emberhold surface.
- Fresnel rim term (shader): `(1 - N.V)^3` x 0.15 warm on `EH_Bronze`, x 0.25 cyan-white on `RH_Ice`/`RH_Silver`/`RH_Obsidian` (this is what lifts Rime edges over the dark squares).
- Contact: baked AO under overhangs (crown rim, mitre base, helm brim, merlons) <= 0.15 so the cue always has a dark undercut line against its own body.

### 11.6 Greyscale check (run with the silhouette tests)
Desaturate the 60 px renders on L and D; compute (a) mean and histogram vs 11.3, (b) the 3 px edge ring vs 11.2, (c) the cue region (crown/mitre/helm/horse head) is the highest-contrast element: its local Michelson contrast >= 0.5. If the edge test fails: Emberhold -> darken the AO under the cue or brighten the edge wear; Rime -> add a lit facet / silver wire / frost cap on the failing extremity.

## 12. Identity cue table (all 12 pieces)
| Piece | Height | Identity cue (one line) |
|---|---|---|
| `emberhold_king` | 1.70 | Closed bronze crown (band, 4 fleurons, 2 crossing arches, orb) topped by a **cross-pattee with an ember gem**; widest body, greatsword planted. |
| `rime_king` | 1.70 | **Ice-crystal cross** inside a hovering ring of 8 prisms caged by 4 wire arches; dark obsidian bulk, ridge and spikes kept below the crown. |
| `emberhold_queen` | 1.55 | **Open coronet of 9 bronze tines with ember-bead tips** and a small ember orb in the centre; slim, A-line skirt, no cross, no arches. |
| `rime_queen` | 1.55 | **Open coronet of 9 ice-crystal tines** and a small glow orb, with a dim **crescent halo behind**; slim spectral gown, no cross. |
| `emberhold_bishop` | 1.40 | **Bronze mitre cut by a deep diagonal oxblood slit** on a red robe; chained censer staff. |
| `rime_bishop` | 1.40 | **Translucent ice mitre with a glowing cyan diagonal slit**, frost beard, lantern staff with orbiting runes. |
| `emberhold_knight` | 1.30 | **Barded bronze war-horse**: arched crinet neck, chanfroned head, ear covers and a **flame mane**; the rider crouched low, lance couched. |
| `rime_knight` | 1.30 | **Skeletal frost steed**: bone-white skull with **glowing cyan eyes**, exposed lit ribs, **crystal mane**; rider low, glaive carried reversed. |
| `emberhold_rook` | 1.20 | Wide flared parapet with **5 stone merlons** and a **brazier burning inside the crenels**; bronze ram on its face. |
| `rime_rook` | 1.20 | Wide obsidian collar carrying **5 blocky ice-monolith merlons** with a cold orb glowing in the crenels; leaning ice tower. |
| `emberhold_pawn` | 1.05 | **Big round bronze helm** (rim, 4 ribs, button) over a compact body with a round shield; short and stout. |
| `rime_pawn` | 1.05 | **Round faceted obsidian helm** with a cyan visor slit and an ice knob, hunched, spikes kept below the helm. |
