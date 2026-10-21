# Code-Forge Style Guide (shared by all 12 pieces)

Build-ready numbers for the Python/numpy forge. Sources: art-bible.md, capture-choreography.md,
asset-pipeline.md, `src/contracts/assetContract.ts`. Every sheet `docs/art/{asset_id}.md` obeys this file.
All designs are original; never reference existing franchises, characters or commercial sets.

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

**Scale keys** (`sx/sy/sz`) are allowed on `body`/`top` for squash and stretch (non-humanoids especially) and on the queen's `weapon_summon` node. **`weapon_summon`** (queens) is a non-skinned node parented to the `hand_R` bone (origin = grip, `socket_weapon_R`), scale 0 in every clip except Attack; its parts are modelled in grip-local coordinates (+Y along the shaft).

**Bones (contract, do not add or rename).** `root` (pedestal, never animates), `body` (hips/pelvis, carries legs and skirt, lunges up to +/-0.3),
`top` (secondary overlay: whatever hangs or crowns the piece: crest, cloak, pack, brazier, ridge, censer chain, halo).
Humanoids: `spine` (child of body at the waist; chest, mantle, torso plates), `head` (neck pivot; helm, hood; crown unless on `top`),
`arm_L/arm_R` pivot at the **shoulder** and carry the upper arm and shoulder plate; `hand_L/hand_R` pivot at the **elbow** and carry forearm, hand
and whatever is held (so each arm has a shoulder and an elbow joint). Knights: `mount_body` (mount torso and legs), `mount_head` (neck pivot; head,
horns, mane front); the rider uses the humanoid bones (rider legs bind to `body`, which sits on the saddle).
Hierarchy: root > body > spine > head, arm_*, hand_* (child of arm_*), `top` child of spine (humanoid) or body (others); `mount_body` child of root, `mount_head` child of `mount_body`, `body` child of `mount_body` for knights.
Rigid-bound 100% to one bone, except cloth/cloak/mantle/mane parts marked `~soft`, which blend 2 bones (pivot-distance falloff).
There are no leg bones: **statues glide on their plinths**. Move = lean, bob, sway of `body`/`spine`, not stepping.

## 1. Proportions

Collector miniatures, not chibi: head ~ 1/6.5-1/7 of figure height, believable hands (hand length = 0.75 head height),
shoulder width 2.2-2.6 heads, forearm and shin thicker at the proximal end.
"Figure height" = plinth top (y 0.22) to top of the head (helm without crest). Total piece height is the contract height to the tallest feature.

| Role | Total H | Figure (0.22 -> head top) | Head height | Heads tall | Notes |
|---|---|---|---|---|---|
| Pawn | 1.05 | 0.80 (E) / 0.72 stooped (R) | 0.12 / 0.11 | 6.7 / 6.5 | shield / spikes set the top |
| Rook | 1.20 | tower | - | - | tower mass 0.22 -> 1.00, crown to 1.20 |
| Knight | 1.30 | rider seated 0.40 (seat y 0.78 -> head top 1.18) | rider head 0.09 | ~6.5 standing-equivalent | mount withers 0.80, mount head top 1.08, helm crest 1.22, lance/glaive tip 1.30 |
| Bishop | 1.40 | 1.05 (E) / 1.00 (R) | 0.15 / 0.14 | 7.0 / 7.1 | hood/lantern staff set the top |
| Queen | 1.55 | 1.20 | 0.17 | 7.0 | crown adds 0.13 (E); halo/hair adds 0.13 (R) |
| King | 1.70 | 1.32 (to head top) | 0.19 | 6.95 | broadest piece; crown/prisms add to 1.70 |

Role silhouette envelopes at the plinth top (max width x depth, units), a hard check:
pawn 0.55 x 0.50, rook 0.66 x 0.62, knight 0.52 x 0.80 (long axis Z), bishop 0.50 x 0.50, queen 0.62 x 0.50, king 0.74 x 0.56.
Nothing but weapons or horns may exceed 0.80 horizontally (pedestal Ø0.80; neighbours are 1.0 apart).
Minimum silhouette-defining feature thickness: **0.05** (about 2 px at 60 px piece height). Thinner = normal-map / material detail.

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

Procedural texture generators: hammered bronze, blackened steel, leather, fur, cloth, stone with ember cracks, obsidian, ice with cracks, frost.

| Material id | Colour (hex) | Luma | Spec | Use |
|---|---|---|---|---|
| `EH_Bronze` | #A8713A | 0.47 | metal 1, rough 0.35, hammered normal, edge wear (#C99A5E on curvature>0.6), cavity grime (#4A3220) | armour, crowns, rings |
| `EH_Steel` | #3B3A38 | 0.23 | metal 1, rough 0.45, polished edges (#7A7872) | blades, hooks, under-plates |
| `EH_Leather` | #5A3A22 | 0.22 | rough 0.7, grain + stitch normal | straps, belts, boots |
| `EH_Fur` | #6B5440 | 0.34 | rough 0.85, strong AO | collars, mantles |
| `EH_Cloth` | #5E1F1A | 0.17 | rough 0.9, weave normal, soot gradient to hem (#1E1814) | surcoats, cloaks |
| `EH_Stone` | #4A433C, soot #1E1814 | 0.28 | rough 0.85, chipped, ember cracks | pedestal, masonry |
| `EH_Ember` | #FF7A1A emissive x4-8 | 0.56 | bloom | cracks, gems, braziers, elk eyes |
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
| Mean luma | 0.30-0.45 | **<= 0.15** |
| Median luma | 0.28-0.42 | <= 0.12 |
| Pixels >= 0.65 | <= 6% (ember, bronze highlights) | **8-15%** (ice, silver, glow, frost) |
| Pixels <= 0.10 | <= 12% (soot) | >= 55% |
| Structure | broad warm mid-value mass; light = metal edges + ember | black mass with sparse, very bright accents |

Pedestals follow the rule (Emberhold stone mid-dark, Rime obsidian). Against the dark carved-stone board, Rime silhouettes are lifted by (a) frost on every upward face,
(b) silver wire lines on plate borders, (c) translucent ice at extremities (horns, blades, prisms). Never put pure black next to pure white on an Emberhold piece.

## 5. Silhouette readability (45 deg top-down, ~60 px tall)

At 60 px, 1 px = 0.02 units (pawn) to 0.03 (king).
1. **One signature shape per piece, enlarged ~15%**, on the outer silhouette, never inside it.
2. **Role ordering by outline**: pawn = round head over a round shield/mass, no tall protrusion; rook = flat-topped block with crenel notches; knight = long horizontal body with forward horn/neck rise (only role with Z-length > 0.7);
   bishop = one narrow tall taper to a point, nothing wider than 0.5; queen = crown + flared A-line skirt with waist pinch; king = widest shoulders + tallest crown + vertical sword/ridge.
   Heights follow the contract; no feature of a lower role passes the next role's height.
3. **Factions**: Emberhold = convex, rounded, low centre of mass, horizontal bands, symmetric main shapes (shields, discs, crowns). Rime = tall/narrow, concave cuts, radiating spikes, asymmetric growths, floating parts with visible gaps.
   Test: silhouette perimeter / sqrt(area): Emberhold <= 4.3, Rime >= 5.0.
4. **Negative space**: at least one gap >= 0.06 between arm and torso (or main mass and weapon) per piece.
5. **Top-down check**: head/crown/hood is the highest-contrast element; weapons must not hide the head from a +Z, 45 deg-down view.
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

## 7. Clip rules (every sheet)

- **Idle** (loop 2-4 s, subtle): breathing = `spine` +/-1.5 deg rx, `body` y +/-0.004, `head` +/-1 deg drift, `top` lag. Ends on its t=0 pose.
- **Move** (loop 0.6-1.0 s): glide with `body` rx 4-8 deg lean, y bob 0.015-0.03 twice per loop, roll +/-3 deg. Footstep callbacks at keys named `step` (2 per loop).
- **Attack** (1.2-2.4 s): anticipation >= 0.3 s (io), strike 0.08-0.15 s (snap), impact at `impactTime` exactly (`socket_impact` is on the blow then), hold 0.1, recover.
- **HitReact** (0.3-0.6 s): recoil away from +Z (rx -8 to -14 body/spine, head snaps back), settles at 60% of the pose.
- **Victory** (1-2 s): weapon raised or planted, head up, ends in a held pose.
- Translation local to the parent bone; body lunge limit +/-0.3. No root motion.

## 8. Fragments (global)

Counts follow `FRAGMENT_COUNT` (pawn 20, rook/knight/bishop 30, queen/king 40), built from LOD1 volumes.
Emberhold: chunky slabs/blocks (0.05-0.12), irregular convex pieces (5-9 faces), `EH_Interior` glowing ember core; ~10% are small plates keeping bronze + rivets.
Rime: sharp elongated shards (aspect 2.5-4:1, 4-6 faces, pointed ends) with `RH_Interior`; ~25% thin triangular splinters; obsidian plates break to flat 3-5-sided shards with a bright inner edge.
Each sheet lists coarse vs. fine cells and what stays intact (weapon heads, crowns).

## 9. Delivery

Names: `{asset_id}`, `{asset_id}_LOD0`, `{asset_id}_LOD1`, `rig`, sockets as empties. Budgets: pawn <= 15k LOD0, rook <= 18k, bishop <= 22k, queen/king <= 30k, knight <= 35k.
Each sheet's part table is modelling intent; the forge may merge parts of the same material and bone for tri budget but must not drop **S** or **F** parts.
