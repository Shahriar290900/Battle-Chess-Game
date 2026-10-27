# rime_rook - Rime Glacier Bastion

## 1. Identity
- **Name**: Rime Glacier Bastion. **Concept**: a leaning tower of uneven glacial ice monoliths lashed in silver wire around a black obsidian core, flaring at the top into an obsidian collar that carries **five ice monoliths cut into merlons**, a cold light burning in the crenels.
- **Identity cue (the crenellated top)**: **5 blocky ice merlons** (each 0.20 wide x 0.075 deep x 0.14 tall, top y 1.15-1.20 hand-cut uneven, flat bevelled tops, frost caps) on a flared obsidian collar r 0.334 (**0.67 wide against a 0.40 shaft top**); crenel gaps 0.15 wide x 0.14 deep, one centred on the front; the glow orb shows between them. The old fan of spiked shards is gone: merlons are blocks with flat tops, never spikes.
- Silhouette: narrow tapering stack with a mushroom flare and five tooth-shaped blocks; leans 2 deg toward -X (was 3 deg). The ice walls keep their jagged chips at the shaft only.
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
| Crown collar (flared obsidian) | 0.960-1.048 | r 0.15 -> 0.334 |
| Merlon monoliths x5 | 1.040-1.150..1.200 | tops 1.18 / 1.20 / 1.16 / 1.19 / 1.17 ; crenel gap 0.15 |
| Core glow orb | 1.025-1.125 | r 0.05, visible through the crenels |
Envelope: 0.67 wide (collar/merlon Ø0.67) x 0.67 deep; tower body 0.60 at the hex corners.

## 3. Bone pivots
root (0,0,0) | body (0,0.22,0) (core, monoliths, buttresses) | top (0,1.00,0) (collar, merlons, core orb, silver band). `top` is a child of `body`. No humanoid bones, no `weapon` bone (Surrender is a slump, see section 7).
Binding: parts 1-19, 25, 27 -> `body`; 20-24, 26 -> `top`. The merlon ring is rigid with `top` (it may tilt, scale sy, rotate ry; crenel gaps never deform).

## 4. Part list
Pedestal parts per README section 2.
**Part numbers are stable ids; gaps = removed parts.** Bone column: see section 3. Rows 20-24, 26 replace the old splayed shard crown.

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
| 20 | **crown collar (flared obsidian) S** | L | sides=10 faceted, `(0.150,0.960)(0.230,0.985)(0.300,1.005)(0.334,1.030)(0.334,1.045)(0.290,1.048)(0.150,1.045)` ; 5 under-bracket icicles C n=1 len 0.06 pointing down at the merlon angles | RH_Obsidian / RH_Ice | top |
| 21 | **ice merlons x5 S** | ring-sector extrusion | centres at angles 36 + 72k deg (crenel centred on the front) ; each r 0.26-0.334, tangential width 0.20 at r 0.30 (angular 38 deg), crenel gap 0.15 ; base y 1.040, tops y 1.18 / 1.20 / 1.16 / 1.19 / 1.17 (k=0..4) ; flat top with chamfer 0.012 and one diagonal chip 0.03 ; outward tilt 4 deg, yaw jitter +-6 deg ; frosted ice (transmission 0.5) | RH_Ice | top |
| 22 | merlon frost caps + edge wire | B + S | caps 0.012 thick on every merlon top (bright, value >= 0.85) ; silver edge wire r 0.004 along the top edges | RH_Frost / RH_Silver | top |
| 23 | crown core glow orb **F2** | B | c=(0,1.075,0) s=(0.10,0.10,0.10) e=2 (visible through the crenels) | RH_Glow x4 | top |
| 24 | crown shard fracture lines | texture | cyan faint lines inside shards | RH_Ice cracks | top |
| 25 | frost mist base ring | texture | white gradient on tier-1 bottom 0.03, alpha mask for VFX hook | RH_Frost | body |
| 26 | silver band at the collar edge | S | torus r=0.332, tube 0.006 at y 1.034 | RH_Silver | top |
| 27 | obsidian shard spurs x3 | C | black crystals growing from M3 (n=3 len 0.06-0.10) at the back-left | RH_Obsidian | body |
(27 parts; budget <= 18k. F1 = core crack; F2 = crown orb. Row 24 (shard fracture lines) now applies to the merlons. Tilt of the whole tower is 2 deg, not 3.)

## 5. Pose
Leaning 2 deg toward -X (rz +2 on `body` baked into geometry, rest pose = 0). The collar and merlons are level (they sit on `top` and do not inherit the lean). Monolith offsets create four visible seams where the obsidian core and silver ties show; the cold orb glows through the front crenel.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (0, 0.30, 0.34) (tower front base, topple contact) | body |
| `socket_cast` | (0, 1.12, 0) shard launch point (through the front crenel) | top |
| `socket_impact` | (0, 0.30, 0.40) | body |
| `socket_head` | (0, 1.24, 0) | top |

Extras: `impactTime 0.75`, `strikeRange 0.10`, `attackStyle slam`, `displayName "Rime Glacier Bastion"`, `contractVersion 1`. (Spike volley is engine VFX at `socket_cast`, fired at t = 0.50 s.)

## 7. Clips (squash-and-stretch beats; conventions in README section 7)
No limbs: `body` squash/stretch + rock stands in for knee/elbow bends; `top` (the merlon crown) overlaps 0.08 s behind and can scale sx,sz (ring expands, crenel gaps widen) and tilt.

**Idle** (loop 3.0 s) - cold glimmer
| t | body | top (collar, merlons, orb) |
|---|---|---|
| 0.0 | rest | rest |
| 1.0 | | rz +1.0, ry +3 (crown drifts on its seat) ; orb pulse +15% |
| 1.5 | rz -0.6 (creak) | |
| 2.0 | | rz -0.8, ry -2 |
| 3.0 | rest | rest |

**Move** (loop 0.8 s) - glide with sway (engine hops/slides)
| t | body | top |
|---|---|---|
| 0.0 | rx +3, y 0 | |
| 0.2 | y +0.02, rz -2 (**step**; the tower tips and re-plants) | rx -5 (merlons lag) |
| 0.4 | rx +5, y 0 | |
| 0.6 | y +0.02, rz +2 (**step**) | rx -5 |
| 0.8 | = t0 | = t0 |

**Attack** (1.8 s; **impact 0.75**)
| t | body | top |
|---|---|---|
| 0.00-0.30 | rx -4, sy 0.96 (settle) | sx,sz 1.1, rz +3 (merlons flare apart), orb +40% |
| 0.30-0.50 (io) | rx -6, y +0.02 | sx,sz 1.2, rx -10 |
| 0.50 | **event**: volley: top sx,sz 1.2 -> 0.9 in 0.06 s (snap); engine fires 3 spikes from `socket_cast` through the front crenel | |
| 0.50-0.62 | rx -10, y +0.04 (tower hangs back) | rx -8 |
| 0.62-0.75 **strike** (0.13 s; body leads 0.04 s) | rx -10 -> +48 (topple), z +0.18 | rx +30, sx,sz 1.0 |
| 0.75 | **impact**: tower laid at 48 deg; `socket_impact` on target | |
| 0.75-0.95 hold | rx +46, sy 0.96 ; frost puff | |
| 0.95-1.80 (io) | rx -> 0 with overshoot -3 at 1.5 | to rest |

**HitReact** (0.4 s)
| t | body | top |
|---|---|---|
| 0.08 | rx -9, rz +4, z -0.06 (snap) | rx +16, sy 0.9 |
| 0.40 | rx -3, rz +1 | rest |

**Victory** (1.5 s, ends held)
| t | body | top |
|---|---|---|
| 0.0 | rest | rest |
| 0.5 | y +0.03 | sy 1.15, sx,sz 1.1 (merlons lift), orb +60% |
| 1.0 | | ry +20 (slow turn) |
| 1.5 | hold | hold |

**Taunt** (1.2 s, once) - the crown rattles and the orb flares
| t | body | top |
|---|---|---|
| 0.00-0.30 | sy 0.95, y -0.02 (crouch) | sx,sz 1.1 |
| 0.30-0.45 (snap) | sy 1.06, y +0.02, rx +5 | sy 1.3 ; orb flares x2 ; ry +8 |
| 0.45-0.90 | rest-ish | rattle: rz +-2 at 14 Hz decaying (merlons chatter on the collar) |
| 0.90-1.20 (io) | settle | rest |

**Surrender** (2.0 s, once, holds the last pose) - the crown slumps and the light dies
| t | body | top |
|---|---|---|
| 0.00-0.30 | rx -4, sy 0.96 (stagger) | rz +4 |
| 0.30-1.30 (io) | sink: y -0.05, sy 0.89 ; bow rx +10, z +0.03 | slides forward: rx +14, z +0.03, sx,sz 0.96 (the merlon ring sags to one side); orb fades to 20% |
| 1.30-2.00 | hold; slow settle (sy 0.88) | hold, frost mist on the floor (engine) |

## 8. Fragments (30)
Sharp: 12 elongated monolith shards (aspect 3:1), **5 merlon blocks break away whole (they keep their frost caps and a cyan edge for 0.3 s)**, 4 obsidian core/collar splinters, 4 silver wire/collar bits. Interior `RH_Interior` pale cracked ice; frost mist VFX on break.

## 9. Readability
- **Identity cue**: 5 chunky ice merlons with flat tops and a cold glow between them, on a flared collar wider than the tower.
- vs `emberhold_rook`: dark obsidian/ice with a cold orb vs warm soot stone with fire in the notches and a forward ram; both have a 0.67-wide crenellated top. Value: Rime merlon tops (frost caps, >= 0.80) are far brighter than the body (<= 0.12), the Emberhold merlons stay mid-value.
- vs other roles: only piece with five tooth-like blocks around a flared ring and no figure; the hex-stacked offset body also differs from the bishop's single slim peak.
- Silhouette tests: >= 4 notches (>= 4 px wide, >= 4 px deep) in the top profile over the front 180 deg; top-down = ring with 5 gaps and a glowing centre.
