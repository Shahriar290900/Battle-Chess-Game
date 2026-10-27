# emberhold_rook - Emberhold Forge Bastion

## 1. Identity
- **Name**: Emberhold Forge Bastion. **Concept**: a squat round siege-tower of soot-black masonry and bronze strapwork, a **wide crenellated parapet with a working brazier burning INSIDE the crenels**, and a bronze ram-head battering beam on its face.
- **Identity cue (the crenellated top)**: **5 big stone merlons** (each 0.22 wide x 0.075 deep x 0.13 tall, y 1.04 -> 1.17, +20% over the old 8 small merlons) on a ring r 0.30, outer face r 0.336, i.e. the parapet is **0.67 wide against a 0.54 shaft top**; crenel notches 0.157 wide x 0.13 deep, one centred on the front. The brazier (rim r 0.215, y 1.10) sits inside the ring; flames show in the notches and rise to 1.20.
- Silhouette = a stepped-flare block with a mushroom top, five tooth-shaped merlons, a fire glow between them, no figure. Never confusable with a pawn (round) or a bishop (narrow cone).
- Non-humanoid: bones `root, body, top, weapon`. Scale keys (`sx/sy/sz`) on `body`/`top` allowed for squash/stretch.

## 2. Dimensions (total 1.20)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Batter base + door | 0.22-0.42 | base r 0.31 |
| Tower shaft (masonry courses) | 0.42-0.86 | r 0.31 -> 0.27 |
| Corbel / machicolation ring | 0.86-0.985 | r 0.27 -> 0.335 (the overhang that makes the top wider than the body) |
| Parapet wall | 0.985-1.040 | r 0.285-0.336 |
| Merlons x5 | 1.040-1.170 | 0.22 wide x 0.075 deep x 0.13 tall; crenel gap 0.157, depth 0.13 |
| Brazier bowl (inside) | 1.020-1.100 | r 0.215 rim |
| Flames | 1.09-1.20 | tallest tip 1.20 (centre tongue) |
| Ram beam | y 0.48-0.64, z 0.26-0.46 | |
Envelope: 0.67 wide (corbel/merlon Ø0.67) x 0.76 deep (z -0.335..0.46 ram); ram is the weapon exception.

## 3. Bone pivots
root (0,0,0) | body (0,0.22,0) | top (0,1.00,0) (brazier, flames, banner) | weapon (0,0.56,0.37) (ram beam + head + horns; child of `body`). `body` carries tower, door, merlons, cradle. `top` is a child of `body`. No humanoid bones.
Binding: parts 1-17, 22, 23, 29-31 -> `body`; 18-21 -> `weapon`; 24-28 -> `top`. The merlon ring is part of `body` so the crenel profile never deforms (it may squash with `body` sy only).

## 4. Part list
Pedestal parts per README section 2.
**Part numbers are stable ids; gaps = removed parts.** Bone column: see section 3 (rook has no humanoid bones; rows 18-21 bind to `weapon`).

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | tower shaft (stepped courses) **S** | L | sides=24, `(0.000,0.22)(0.300,0.22)(0.310,0.235)(0.305,0.30)(0.312,0.305)(0.300,0.36)(0.306,0.365)(0.292,0.42)(0.298,0.425)(0.284,0.48)(0.289,0.485)(0.276,0.54)(0.281,0.545)(0.270,0.60)(0.274,0.605)(0.270,0.70)(0.272,0.78)(0.270,0.86)` + course noise 0.003 | EH_Stone | body |
| 2 | masonry joints (mortar grooves) | texture | 7 courses, block width 0.12, offset half per course, groove depth 0.005 | EH_Stone | body |
| 3 | corbel ring | L | sides=24, `(0.270,0.86)(0.290,0.875)(0.320,0.90)(0.335,0.925)(0.335,0.975)(0.300,0.985)` | EH_Stone | body |
| 4 | corbel brackets x10 | B | two under each merlon, r=0.30, y 0.88-0.93, each s=(0.035,0.06,0.07) e=4, rot (25,0,0) outward-slanted | EH_Stone | body |
| 5 | parapet wall | L | sides=40, `(0.285,0.985)(0.336,0.985)(0.336,1.040)(0.285,1.040)` | EH_Stone | body |
| 6 | **merlons x5 S** | ring-sector extrusion | centres at angles 36 + 72k deg (k=0..4: a crenel is centred on the front, a merlon on the back) ; each r 0.26-0.336, angular width 41 deg (tangential 0.22 at r 0.30), y 1.040-1.170, rd 0.008, bevel top 0.006 ; crenel gap 30 deg = 0.157, depth 0.13 | EH_Stone | body |
| 7 | bronze cap strips on merlons x5 | B | s=(0.225,0.012,0.08) following the sector at y 1.170-1.182 | EH_Bronze | body |
| 8 | bronze band lower | L | sides=24, `(0.307,0.395)(0.317,0.40)(0.317,0.44)(0.307,0.445)` | EH_Bronze | body |
| 9 | bronze band mid | L | sides=24, `(0.280,0.64)(0.290,0.645)(0.290,0.68)(0.280,0.685)` | EH_Bronze | body |
| 10 | bronze band upper | L | sides=24, `(0.272,0.82)(0.282,0.825)(0.282,0.855)(0.272,0.86)` | EH_Bronze | body |
| 11 | vertical straps x8 | E | each (-0.020,0.425)(0.020,0.425)(0.018,0.84)(-0.018,0.84) @0.0..0.012 (wraps onto tower at r~0.28, tapering), at k*45+22.5 deg, 3 rivets each | EH_Bronze | body |
| 12 | strap rivets x48 | B | r 0.009 domes along straps | EH_Bronze | body |
| 13 | arrow slits x3 **F2** | E | cut (0.014 wide x 0.10 tall) at angles 45, -60, 150 deg, y 0.58-0.68, depth 0.04; interior plane glows | EH_Ember (dim x2.0) | body |
| 14 | slit frames x3 | E | (0.040 x 0.12) around each slit @0..0.010 | EH_Bronze | body |
| 15 | iron door (front low) | E | arch: (-0.07,0.22)(0.07,0.22)(0.07,0.34)(0.05,0.40)(0,0.43)(-0.05,0.40)(-0.07,0.34) @0.27..0.285 b=0.008 + 3 hinge straps B | EH_Steel / EH_Bronze | body |
| 16 | door frame stones | E | arch ring thickness 0.025 around the door @0.27..0.30 | EH_Stone | body |
| 17 | ram cradle (mount plate) **S** | E | (-0.12,0.46)(0.12,0.46)(0.14,0.58)(0.12,0.68)(-0.12,0.68)(-0.14,0.58) @0.26..0.285 b=0.012 | EH_Bronze | body |
| 18 | ram beam | S | (0,0.56,0.27;0.070)->(0,0.56,0.37;0.075)->(0,0.56,0.44;0.080) sec=12, bronze hoops x3 at z 0.30/0.36/0.41 (r+0.008) | EH_Bronze | weapon |
| 19 | ram head **S** | B | c=(0,0.56,0.465) s=(0.17,0.16,0.19) e=2.2 + brow ridge, nostrils: 2 recesses depth 0.012 | EH_Bronze | weapon |
| 20 | ram horns M | S | spiral: (0.07,0.60,0.43;0.026)->(0.115,0.62,0.40;0.022)->(0.130,0.57,0.37;0.016)->(0.105,0.53,0.38;0.010) | EH_Bronze | weapon |
| 21 | ram head ember eyes (tiny) | B | s=(0.012,0.008,0.006) x2 at (+-0.040,0.595,0.545) | EH_Ember | weapon |
| 22 | drape banner (asymmetric) | E | (0.10,0.98)(0.22,0.96)(0.24,0.74)(0.17,0.70)(0.10,0.76) @0.30..0.307 placed at ry 40deg, `~soft` hem sag 0.01 | EH_Cloth | body |
| 23 | chain swag | S | catenary between brackets at +-45 deg, r=0.006 x 2 | EH_Steel | body |
| 24 | brazier bowl **S** | L | sides=20, `(0.000,1.020)(0.080,1.020)(0.150,1.045)(0.200,1.080)(0.215,1.100)(0.200,1.103)(0.180,1.085)(0.120,1.058)(0.000,1.045)` ; sits inside the merlon ring (inner radius 0.26) | EH_Bronze | top |
| 25 | bowl lugs x5 | B | r=0.205, y 1.07, at the merlon angles, s=(0.03,0.03,0.04) | EH_Bronze | top |
| 26 | coals bed | B | c=(0,1.085,0) s=(0.30,0.04,0.30) e=2.5 +noise 0.012 | EH_Ember | top |
| 27 | flame tongues x7 **F1** | S | bases on r=0.10 ring at y 1.09: tongue k: (r cos,1.09,r sin;0.040)->(0.6x,1.14;0.032)->(x*0.35,1.18;0.018)->(0,1.20;0.002). Heights 0.08-0.11 (tips y 1.17-1.20, centre tongue 1.20), lean +3 deg toward the front crenel, s-curve noise 0.015; flicker via vertex shader | EH_Ember x6 | top |
| 28 | flame core | S | (0,1.09,0;0.06)->(0,1.17,0;0.008) lighter #FFC260 | EH_Ember x8 | top |
| 29 | scorch soot streaks x6 | texture | on parapet inside and above slits | EH_Stone dark | body |
| 30 | base rubble | B | 4 blocks at plinth edge: c=(0.26,0.245,0.20) s=(0.07,0.05,0.06) rot ; (-0.27,0.24,0.12) ; (0.12,0.24,-0.28) ; (-0.18,0.24,-0.26), chipped | EH_Stone | body |
| 31 | cracks with ember seams | texture | 3 seams on shaft, widths 0.004, total <= 3% area | EH_Ember x3 | body |
(31 parts. Focal points: F1 flames, F2 arrow slits at low intensity. Merlon top faces must catch the rim light: bevel 0.006, roughness 0.85, frost-free.)

## 5. Pose
Squat, solid, perfectly planted. Flames lean slightly toward +Z (3 deg) and show through the front crenel. The ram head points forward and slightly down (-4 deg). Banner hangs to the left of the ram. Attack lifts the whole tower (engine raises 1.2), so keep the shaft in one rigid piece.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (0, 0.56, 0.54) ram nose | weapon |
| `socket_cast` | (0, 1.12, 0) brazier centre | top |
| `socket_impact` | (0, 0.30, 0.46) | body |
| `socket_head` | (0, 1.22, 0) | top |

Extras: `impactTime 0.75`, `strikeRange 0.10`, `attackStyle slam`, `displayName "Emberhold Forge Bastion"`, `contractVersion 1`.

## 7. Clips (squash-and-stretch beats; conventions in README section 7)
No limbs: `body` squash/stretch + rock stands in for knee/elbow bends (the tower "crouches" and "springs"); `top` (flames) overlaps 0.08 s behind; `weapon` (ram) leads on strikes.

**Idle** (loop 2.4 s) - flames breathe
| t | body | top (brazier, flames) | weapon (ram) |
|---|---|---|---|
| 0.0 | rest | sy 1.00, rx 0 | rest |
| 0.6 | | sy 1.12, rz +2 | |
| 1.2 | sy 1.003 (settles) | sy 0.96, rz -1.5, rx +1 | rx -0.5 (ram nods) |
| 1.8 | | sy 1.08, rz +1 | |
| 2.4 | rest | rest | rest |

**Move** (loop 0.7 s; steps 0.5, 0.7) - hop-lurch; the engine shoves 0.25 s per square
| t | body | top | weapon |
|---|---|---|---|
| 0.0 | sy 1.0 | sy 1.0 | rest |
| 0.1 | sy 0.94, y -0.015 (crouch: coil) | sy 1.2 (flames stretch up) | z -0.01 |
| 0.3 | sy 1.06, y +0.04, rx +5 (hop apex, spring) | sy 0.9 | z +0.02 |
| 0.5 | sy 0.96, y 0 (landing, **step**, dust puff) | sy 1.3 (flames whip up: follow-through) | |
| 0.7 | = t0 (**step**) | = t0 | |

**Attack** (1.7 s; **impact 0.75**; the engine raises/drops the tower)
| t | body | top | weapon |
|---|---|---|---|
| 0.00-0.40 (io) | sy 0.92, y -0.03 (coil) | sy 1.4 (flames flare through the crenels) | z -0.04 (ram draws back) |
| 0.40-0.62 (io) | sy 1.10, rx -8, z -0.10 (rises and rears back) | sy 0.85, rx -10 | z -0.08 |
| 0.62-0.75 **strike** (0.13 s snap; body leads 0.04 s) | rx -8 -> +20, z -0.10 -> +0.22, sy 1.10 -> 0.90 | rx +25 (flames whip forward) | z -0.08 -> +0.06 (ram thrust) |
| 0.75 | **impact**: ram nose on `socket_impact` | | |
| 0.75-0.90 hold | sy 0.88, y -0.04 (squash) | sy 0.7 | |
| 0.90-1.70 (io) | to rest with one overshoot (sy 1.03 at 1.2) | to rest | to rest |

**HitReact** (0.4 s)
| t | body | top | weapon |
|---|---|---|---|
| 0.08 | rx -7, z -0.07, sy 0.96 (snap) | rx +14, sy 0.8 | z -0.03 |
| 0.40 | rx -2, z -0.02 | sy 1.0 | |

**Victory** (1.4 s, ends held)
| t | body | top | weapon |
|---|---|---|---|
| 0.0 | rest | rest | rest |
| 0.4 | sy 1.05, y +0.03 | sy 1.5 (flames roar) | z +0.04 |
| 0.9 | | sy 1.25, rz +3 | |
| 1.4 | rest | hold sy 1.25 | rest |

**Taunt** (1.2 s, once) - roars flame and rams the air twice
| t | body | top | weapon |
|---|---|---|---|
| 0.00-0.30 | sy 0.94, y -0.02 (crouch) | sy 1.2 | z -0.04 |
| 0.30-0.40 (snap) | sy 1.06, y +0.02, rx +6 | sy 1.6 (fireball bursts out of the crenels) | z +0.08 (ram jab 1) |
| 0.40-0.65 | rest-ish | sy 1.0 | z 0 |
| 0.65-0.75 (snap) | sy 1.05, rx +6 | sy 1.5 | z +0.08 (ram jab 2) |
| 0.75-1.20 (io) | settle | settle | rest |

**Surrender** (2.0 s, once, holds the last pose) - the ram is unshipped, the tower slumps, the fire dies
| t | body | top | weapon |
|---|---|---|---|
| 0.00-0.30 | sy 0.96, rx -4 (stagger) | sy 0.8 | |
| 0.30-0.55 | | | **`weapon` (ram) released at 0.45**: drops off the cradle, thuds on the plinth front, bounces once |
| 0.55-1.30 (io) | sink: y -0.06, sy 0.88; bow rx +10, z +0.03 (the whole tower bows, merlons tilt forward) | sy 0.35 (flames sink into the bowl), embers fade | |
| 1.30-2.00 | hold; slow settle (sy 0.87) | sy 0.2, smoke only | |

## 8. Fragments (30)
Coarse: 8 big masonry blocks (shaft courses), **5 merlon chunks (each a whole merlon block with its bronze cap)**. Medium: corbel ring 4, bronze bands 3, ram head 3 (head stays 1 piece + 2 horns), brazier bowl 2, door 1, banner 1. Fine: 3 rubble chips. Chunky stone with `EH_Interior` glowing ember core; bronze keeps rivets.

## 9. Readability
- **Identity cue**: 5 wide stone merlons with fire glowing between them, on a flared parapet wider than the tower.
- vs `rime_rook`: warm soot stone with bronze straps (mean luma 0.40-0.50) and a visible fire in the notches vs dark obsidian with ice-block merlons and a cold core orb; Emberhold has a forward ram; width 0.67 vs ice tower body 0.55 (both crowns 0.67 wide).
- vs other roles: only piece with a wide flat crenellated top and zero figure. Flame tips at 1.20 exactly; nothing taller than the knight's 1.30.
- Silhouette tests: >= 4 notches (>= 4 px wide, >= 4 px deep at 60 px) in the top profile over the front 180 deg; top-down = a ring with 5 gaps.
