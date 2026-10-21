# emberhold_rook - Emberhold Forge Bastion

## 1. Identity
- **Name**: Emberhold Forge Bastion. **Concept**: a squat round siege-tower of soot-black masonry and bronze strapwork, a working brazier for a crown, a bronze ram-head battering beam on its face.
- **Signature shape**: the brazier crown with its fan of flame tongues (flames +15% tall: tips reach 1.20) over a crenellated corbel ring, and the forward ram beam. Silhouette = wide stepped-flare block, crenel notches, flame fan on top.
- Non-humanoid: bones `root, body, top` only. Scale keys (`sx/sy/sz`) on `body`/`top` are allowed for squash/stretch.

## 2. Dimensions (total 1.20)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Batter base + door | 0.22-0.42 | base r 0.31 |
| Tower shaft (masonry courses) | 0.42-0.86 | r 0.31 -> 0.27 |
| Corbel / machicolation ring | 0.86-0.98 | r 0.27 -> 0.335 |
| Parapet + merlons | 0.98-1.06 | 8 merlons |
| Brazier bowl | 1.00-1.12 | r 0.22 |
| Flames | 1.06-1.20 | tallest tip 1.20 |
| Ram beam | y 0.48-0.64, z 0.26-0.46 | |
Envelope: 0.67 wide (corbel Ø0.67) x 0.76 deep (z -0.335..0.46 ram); ram is the weapon exception.

## 3. Bone pivots
root (0,0,0) | body (0,0.22,0) | top (0,1.00,0)  (brazier, flames, banner). `body` carries tower, ram, door. `top` is child of `body`.

## 4. Part list
Pedestal parts per README section 2.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | tower shaft (stepped courses) **S** | L | sides=24, `(0.000,0.22)(0.300,0.22)(0.310,0.235)(0.305,0.30)(0.312,0.305)(0.300,0.36)(0.306,0.365)(0.292,0.42)(0.298,0.425)(0.284,0.48)(0.289,0.485)(0.276,0.54)(0.281,0.545)(0.270,0.60)(0.274,0.605)(0.270,0.70)(0.272,0.78)(0.270,0.86)` + course noise 0.003 | EH_Stone | body |
| 2 | masonry joints (mortar grooves) | texture | 7 courses, block width 0.12, offset half per course, groove depth 0.005 | EH_Stone | body |
| 3 | corbel ring | L | sides=24, `(0.270,0.86)(0.290,0.875)(0.320,0.90)(0.335,0.925)(0.335,0.975)(0.300,0.985)` | EH_Stone | body |
| 4 | corbel brackets x16 | B | r=0.30, y 0.88-0.93, each s=(0.035,0.06,0.07) e=4, rot (25,0,0) outward-slanted | EH_Stone | body |
| 5 | parapet wall | L | sides=24, `(0.300,0.985)(0.318,0.985)(0.318,1.030)(0.300,1.030)` | EH_Stone | body |
| 6 | merlons x8 **S** | B | r=0.309, y 1.030-1.085 (h 0.055), each s=(0.12,0.055,0.055) rd=0.006 e=8, rot ry = k*45, crenel gap 0.075 between | EH_Stone | body |
| 7 | bronze cap strips on merlons x8 | B | s=(0.125,0.012,0.06) at y 1.088 | EH_Bronze | body |
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
| 18 | ram beam | S | (0,0.56,0.27;0.070)->(0,0.56,0.37;0.075)->(0,0.56,0.44;0.080) sec=12, bronze hoops x3 at z 0.30/0.36/0.41 (r+0.008) | EH_Bronze | body |
| 19 | ram head **S** | B | c=(0,0.56,0.465) s=(0.17,0.16,0.19) e=2.2 + brow ridge, nostrils: 2 recesses depth 0.012 | EH_Bronze | body |
| 20 | ram horns M | S | spiral: (0.07,0.60,0.43;0.026)->(0.115,0.62,0.40;0.022)->(0.130,0.57,0.37;0.016)->(0.105,0.53,0.38;0.010) | EH_Bronze | body |
| 21 | ram head ember eyes (tiny) | B | s=(0.012,0.008,0.006) x2 at (+-0.040,0.595,0.545) | EH_Ember | body |
| 22 | drape banner (asymmetric) | E | (0.10,0.98)(0.22,0.96)(0.24,0.74)(0.17,0.70)(0.10,0.76) @0.30..0.307 placed at ry 40deg, `~soft` hem sag 0.01 | EH_Cloth | body |
| 23 | chain swag | S | catenary between brackets at +-45 deg, r=0.006 x 2 | EH_Steel | body |
| 24 | brazier bowl **S** | L | sides=20, `(0.000,1.000)(0.080,1.000)(0.160,1.040)(0.215,1.095)(0.225,1.115)(0.210,1.118)(0.190,1.090)(0.130,1.050)(0.000,1.045)` | EH_Bronze | top |
| 25 | bowl lugs x6 | B | r=0.205, y 1.05, s=(0.03,0.03,0.04) | EH_Bronze | top |
| 26 | coals bed | B | c=(0,1.100,0) s=(0.30,0.04,0.30) e=2.5 +noise 0.012 | EH_Ember | top |
| 27 | flame tongues x7 **F1** | S | bases on r=0.10 ring at y 1.10: tongue k: (r cos,1.10,r sin;0.040)->(0.6x,1.15;0.032)->(x*0.35,1.19;0.018)->(0,1.20;0.002). Heights 0.08-0.10 (tips y 1.17-1.20, centre tongue 1.20), s-curve noise 0.015; flicker via vertex shader | EH_Ember x6 | top |
| 28 | flame core | S | (0,1.10,0;0.06)->(0,1.18,0;0.008) lighter #FFC260 | EH_Ember x8 | top |
| 29 | scorch soot streaks x6 | texture | on parapet inside and above slits | EH_Stone dark | body |
| 30 | base rubble | B | 4 blocks at plinth edge: c=(0.26,0.245,0.20) s=(0.07,0.05,0.06) rot ; (-0.27,0.24,0.12) ; (0.12,0.24,-0.28) ; (-0.18,0.24,-0.26), chipped | EH_Stone | body |
| 31 | cracks with ember seams | texture | 3 seams on shaft, widths 0.004, total <= 3% area | EH_Ember x3 | body |
(31 parts. Focal points: F1 flames, F2 arrow slits at low intensity.)

## 5. Pose
Squat, solid, perfectly planted. Flames lean slightly toward +Z (3 deg). The ram head points forward and slightly down (-4 deg). Banner hangs to the left of the ram. Attack lifts the whole tower (engine raises 1.2), so keep the shaft in one rigid piece.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (0, 0.56, 0.54) ram nose | body |
| `socket_cast` | (0, 1.12, 0) brazier centre | top |
| `socket_impact` | (0, 0.30, 0.46) | body |
| `socket_head` | (0, 1.14, 0) | top |

Extras: `impactTime 0.75`, `strikeRange 0.10`, `attackStyle slam`, `displayName "Emberhold Forge Bastion"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 2.4 s) - flames breathe
| t | bone | value |
|---|---|---|
| 0.0 | top | sy 1.00, rx 0 |
| 0.6 | top | sy 1.12, rz +2 |
| 1.2 | top | sy 0.96, rz -1.5, rx +1 |
| 1.8 | top | sy 1.08, rz +1 |
| 2.4 | all | rest |
| 1.2 | body | sy 1.003 (settles) |

**Move** (loop 0.7 s) - hop-lurch; engine shoves 0.25 s per square
| t | bone | value |
|---|---|---|
| 0.0 | body | sy 1.0 |
| 0.1 | body | sy 0.94, y -0.015 (crouch) ; top sy 1.2 |
| 0.3 | body | sy 1.06, y +0.04, rx +5 (hop apex) ; top sy 0.9 |
| 0.5 | body | sy 0.96, y 0 (landing, step) ; top sy 1.3 |
| 0.7 | all | = t0 |
| step | callbacks | 0.5 and 0.7 (dust puff) |

**Attack** (1.7 s; impact 0.75; engine raises/drops the tower)
| t | bone | value |
|---|---|---|
| 0.00-0.40 | body | sy 0.92, y -0.03 (coil, io) ; top sy 1.4 (flames flare) |
| 0.40-0.62 | body | sy 1.10, rx -8, z -0.10 (rise & rear back, io) ; top sy 0.85, rx -10 |
| 0.62-0.75 | **strike** (0.13 s snap) | body rx -8 -> +20, z -0.10 -> +0.22, sy 1.10 -> 0.90 ; top rx +25 (flames whip forward) |
| 0.75 | **impact** | ram nose on socket_impact |
| 0.75-0.90 | hold | body sy 0.88, y -0.04 (squash) ; top sy 0.7 |
| 0.90-1.70 | recover (io) | body to rest with 1 overshoot (sy 1.03 at 1.2) |

**HitReact** (0.4 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.08 | body | rx -7, z -0.07, sy 0.96 (snap) ; top rx +14, sy 0.8 |
| 0.40 | body | rx -2, z -0.02 ; top sy 1.0 |

**Victory** (1.4 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.4 | body | sy 1.05, y +0.03 ; top sy 1.5 (flames roar) |
| 0.9 | top | sy 1.25, rz +3 |
| 1.4 | hold | body rest, top sy 1.25 |

## 8. Fragments (30)
Coarse: 8 big masonry blocks (shaft courses), 4 merlon chunks. Medium: corbel ring 4, bronze bands 3, ram head 3 (head stays 1 piece + 2 horns), brazier bowl 2, door 1, banner 1. Fine: 4 rubble chips. Chunky stone with `EH_Interior` glowing ember core; bronze keeps rivets.

## 9. Readability
- vs `rime_rook`: wide and horizontal (width 0.67 vs ice tower 0.55), warm stone with bronze straps vs vertical stacked monoliths; flame fan vs spike crown; forward ram vs none.
- vs other roles: only piece with a wide flat crenellated top and zero figure. Flame tips at 1.20 exactly; nothing taller than knight's 1.30.
