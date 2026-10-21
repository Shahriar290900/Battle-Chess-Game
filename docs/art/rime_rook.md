# rime_rook - Rime Glacier Bastion

## 1. Identity
- **Name**: Rime Glacier Bastion. **Concept**: a leaning tower of five uneven glacial ice monoliths lashed in silver wire around a black obsidian core, crowned with a splay of tilted ice shards.
- **Signature shape**: the crown of tilted ice shards (nine, tallest 0.20, splayed 20-35 deg outward, ~15% oversize) on a tower that tapers upward and leans 3 deg toward -X. Silhouette = narrow tapering stack with a jagged fan top; no flat parapet.
- Non-humanoid: bones `root, body, top`. Scale keys allowed on `body`/`top`.

## 2. Dimensions (total 1.20)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Base buttress shards | 0.22-0.50 | 5 clusters, tilt out |
| Monolith 1 | 0.22-0.46 | hex r 0.30 -> 0.27 |
| Monolith 2 | 0.44-0.66 | hex r 0.26, rot 18 |
| Monolith 3 | 0.64-0.86 | hex r 0.23, rot -12, offset (-0.02,0,0.02) |
| Monolith 4 | 0.84-1.00 | hex r 0.20, rot 25 |
| Obsidian core (visible gaps) | 0.22-1.04 | r 0.17 -> 0.12 |
| Crown shards | 1.00-1.20 | tips at 1.20 |
Envelope: 0.60 x 0.62 (hex corners), crown splay within r 0.26.

## 3. Bone pivots
root (0,0,0) | body (0,0.22,0) (core, monoliths, buttresses) | top (0,1.00,0) (crown shards, rune halo ring). `top` child of `body`.

## 4. Part list
Pedestal parts per README section 2.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | obsidian core **S** | L | sides=10 faceted, `(0.000,0.22)(0.170,0.22)(0.175,0.40)(0.160,0.60)(0.145,0.80)(0.125,1.00)(0.115,1.04)(0.000,1.04)` + conchoidal noise 0.008 | RH_Obsidian | body |
| 2 | monolith 1 **S** | L | sides=6, `(0.000,0.22)(0.292,0.22)(0.300,0.234)(0.296,0.40)(0.270,0.455)(0.000,0.46)` ; tilt rx 2 | RH_Ice | body |
| 3 | monolith 2 **S** | L | sides=6, rot ry 18, rx -3, `(0.000,0.44)(0.248,0.44)(0.260,0.455)(0.256,0.62)(0.236,0.664)(0.000,0.665)` | RH_Ice | body |
| 4 | monolith 3 **S** | L | sides=6, rot ry -12, rz 3, centre offset (-0.02,0,0.02), `(0.000,0.64)(0.218,0.64)(0.230,0.655)(0.226,0.82)(0.208,0.864)(0.000,0.865)` | RH_Ice | body |
| 5 | monolith 4 **S** | L | sides=6, rot ry 25, rx 4, offset (0.015,0,-0.02), `(0.000,0.84)(0.190,0.84)(0.200,0.855)(0.196,0.97)(0.170,1.005)(0.000,1.005)` | RH_Ice | body |
| 6 | chipped notch (M2 front-left corner) | cut | wedge 0.08 x 0.10 x 0.07 removed at (0.20,0.55,0.12) exposing obsidian | RH_Ice/RH_Obsidian | body |
| 7 | trapped bubbles x16 | B | spheres r 0.008-0.016 scattered inside monoliths (depth 0.03-0.09 from surface) | RH_Frost | body |
| 8 | inner crack planes x6 | texture | cyan-white crack textures inside ice, 4 cm apart | RH_Ice cracks | body |
| 9 | collar band 1 | L | sides=12, `(0.185,0.455)(0.200,0.46)(0.200,0.485)(0.185,0.49)` | RH_Obsidian | body |
| 10 | collar band 2 | L | sides=12, `(0.172,0.655)(0.185,0.66)(0.185,0.685)(0.172,0.69)` | RH_Obsidian | body |
| 11 | collar band 3 | L | sides=12, `(0.160,0.855)(0.172,0.86)(0.172,0.88)(0.160,0.885)` | RH_Obsidian | body |
| 12 | silver wire lashing x3 | S | helix about each collar, 3 turns, r 0.004, pitch 0.012, (0.20/0.185/0.172 radius) | RH_Silver | body |
| 13 | silver tie rods x6 | S | vertical (0.185,0.46,0)->(0.185,1.00,0) offset k*60 deg, r 0.0045, hidden in ice (visible where chipped) | RH_Silver | body |
| 14 | rune bands x2 | E | plane=XY wrapped ring y 0.56 and 0.76, 8 runes each 0.03 x 0.045 raised 0.004 on the ice surface | RH_Glow | body |
| 15 | glow crack in core **F1** | texture/E | zig-zag emissive seam 0.008 wide from y 0.30 to 0.95, visible via chipped notch and between monoliths | RH_Glow x4 | body |
| 16 | obsidian arrow slit | E | notch 0.03 x 0.09 at (0,0.34,0.30), through monolith 1 into core | RH_Obsidian | body |
| 17 | buttress shards x5 | C | bases ring r 0.30 at y 0.24, angles 20/95/170/245/310 deg; each n=2-3, len 0.14-0.28, r 0.025-0.04, tilt 25 outward | RH_Ice | body |
| 18 | frost caps | B | top faces of monoliths: thin slabs 0.012 tall, radius = ring - 0.01, rough 0.9, jagged edge | RH_Frost | body |
| 19 | frost drips x10 | C | small icicles hanging from underside of each overhang (len 0.03-0.07, r 0.006-0.01) | RH_Ice | body |
| 20 | crown socket ring | L | sides=12, `(0.100,0.995)(0.150,1.000)(0.150,1.030)(0.110,1.040)` | RH_Silver | top |
| 21 | crown shards (tall) **S** | C | base ring r 0.10 at y 1.02, n=5 at 0/72/144/216/288 deg ; len 0.14,0.17,0.19,0.20,0.16 ; r 0.026-0.038 ; tilt out 18-30 deg ; central tallest tip y 1.20 | RH_Ice | top |
| 22 | crown shards (short) | C | n=4 between the tall ones at r 0.15, len 0.08-0.11, r 0.018-0.026, tilt 35 | RH_Ice | top |
| 23 | crown core glow orb **F2** | B | c=(0,1.06,0) s=(0.06,0.06,0.06) e=2 | RH_Glow x3 | top |
| 24 | crown shard fracture lines | texture | cyan faint lines inside shards | RH_Ice cracks | top |
| 25 | frost mist base ring | texture | white gradient on tier-1 bottom 0.03, alpha mask for VFX hook | RH_Frost | body |
| 26 | silver band under crown | S | torus r=0.12, tube 0.006 at y 1.012 | RH_Silver | top |
| 27 | obsidian shard spurs x3 | C | black crystals growing from M3 (n=3 len 0.06-0.10) at the back-left | RH_Obsidian | body |
(27 parts; budget <= 18k. F1 = core crack; F2 = crown orb, low.)

## 5. Pose
Leaning 3 deg toward -X (rz +3 on `body` at rest is baked into geometry, rest pose = 0). Top shards splayed. Monolith offsets create four visible seams where the obsidian core and silver ties show.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (0, 0.30, 0.34) (tower front base, topple contact) | body |
| `socket_cast` | (0, 1.12, 0) shard launch point | top |
| `socket_impact` | (0, 0.30, 0.40) | body |
| `socket_head` | (0, 1.22, 0) | top |

Extras: `impactTime 0.75`, `strikeRange 0.10`, `attackStyle slam`, `displayName "Rime Glacier Bastion"`, `contractVersion 1`. (Spike volley is engine VFX at `socket_cast`, fired at t = 0.50 s.)

## 7. Clips
**Idle** (loop 3.0 s) - cold glimmer
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 1.0 | top | rz +1.5, ry +4 (shards drift) ; sy 1.03 |
| 2.0 | top | rz -1.0, ry -3 |
| 1.5 | body | rz -0.6 (creak) |
| 3.0 | all | rest |

**Move** (loop 0.8 s) - glide with sway (engine hops/slides)
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +3, y 0 |
| 0.2 | body | y +0.02, rz -2 (step) ; top rx -5 |
| 0.4 | body | rx +5, y 0 |
| 0.6 | body | y +0.02, rz +2 (step) ; top rx -5 |
| 0.8 | all | = t0 |

**Attack** (1.8 s; impact 0.75)
| t | bone | value |
|---|---|---|
| 0.00-0.30 | body | rx -4, sy 0.96 (settle) ; top sy 1.2 (shards flare), rz +4 |
| 0.30-0.50 | anticipation (io) | top sy 1.35, rx -10 ; body rx -6, y +0.02 |
| 0.50 | event | volley: top sy 1.35 -> 0.4 in 0.06 s (snap) ; engine fires 3 spikes from socket_cast |
| 0.50-0.62 | body | rx -10, y +0.04 (tower hangs back) |
| 0.62-0.75 | **strike** (0.13 s) | body rx -10 -> +48 (topple), z +0.18 ; top rx +30, sy 0.4 -> 0.8 |
| 0.75 | **impact** | tower laid at 48 deg; socket_impact on target |
| 0.75-0.95 | hold | body rx +46, sy 0.96 ; frost puff |
| 0.95-1.80 | recover (io) | body rx -> 0 with overshoot -3 at 1.5 ; top sy 1.0 |

**HitReact** (0.4 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.08 | body | rx -9, rz +4, z -0.06 (snap) ; top rx +16, sy 0.9 |
| 0.40 | body | rx -3, rz +1 ; top rest |

**Victory** (1.5 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.5 | top | sy 1.5 (shards grow), rz 0 ; body y +0.03 |
| 1.0 | top | ry +20 (slow turn) |
| 1.5 | hold | top sy 1.3 |

## 8. Fragments (30)
Sharp: 14 elongated monolith shards (aspect 3:1), 8 crown shards (whole tips, intact), 4 obsidian core splinters, 4 silver wire/collar bits. Interior `RH_Interior` pale cracked ice; frost mist VFX on break. Crown tips keep the cyan glow for 0.3 s.

## 9. Readability
- vs `emberhold_rook`: narrower (0.60 vs 0.67), taller read (taper + lean), black/blue-white ice with no flat top or horizontal bands; Emberhold is warm, flat-crowned, with forward ram.
- vs other roles: the only piece with no figure and a hexagonal stacked-offset body; crown splay differs from bishop's single tall point. Tip height 1.20 exactly.
