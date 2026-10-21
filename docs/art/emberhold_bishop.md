# emberhold_bishop - Emberhold Cinder Oracle

## 1. Identity
- **Name**: Emberhold Cinder Oracle. **Concept**: a hooded forge-seer in a sooted ember-red robe and embroidered stole, leaning on a tall crook-staff from which a chained bronze censer swings, trailing smoke and sparks.
- **Signature shape**: the tall peaked hood (peak 1.27, ~15% tall) and the hanging censer on a chain (pendulum bound to `top`). Silhouette = a single narrow peaked cone with a long vertical staff and a swinging weight beside it.

## 2. Dimensions (total 1.40)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Robe hem + boots | 0.22-0.32 | hem r 0.27 |
| Robe skirt | 0.30-0.70 | cone r 0.27 -> 0.14 |
| Waist / belt / beads | 0.68-0.76 | |
| Torso + stole + shoulders | 0.74-1.00 | shoulder width 0.30 |
| Head (inside hood) | 1.02-1.17 | head 0.15 |
| Hood (peaked) | 0.98-1.27 | peak 1.27 |
| Staff | 0.22-1.40 | crook top 1.40 at x -0.20 |
| Censer | 1.08-1.20 | hangs from crook on a 0.20 chain |
Envelope: 0.50 wide (x -0.25..0.27) x 0.46 deep. Figure 1.05 (0.22->1.27), 7.0 heads.

## 3. Bone pivots (x, y, z)
root (0,0,0) | body (0,0.60,0) | spine (0,0.72,0) | head (0,1.00,0.01) | top (-0.20,1.38,0.16) (censer pendulum pivot) | arm_L (0.14,0.98,0) | hand_L (0.17,0.84,0.06) | arm_R (-0.14,0.98,0) | hand_R (-0.17,0.84,0.06)

## 4. Part list
Pedestal parts per README section 2.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | robe hem flare **S** | L | sides=24, `(0.000,0.22)(0.265,0.225)(0.272,0.245)(0.268,0.30)(0.240,0.45)(0.200,0.58)(0.150,0.70)(0.000,0.70)` + fold noise 0.008 (12/unit), soot gradient from hem to y 0.40 | EH_Cloth | body |
| 2 | robe pleat ribs x10 | S | vertical creases from hem to waist, (r*cos,0.26,r*sin)->(0.6r,0.70) r 0.010, amplitude varies | EH_Cloth (darker) | body |
| 3 | hem trim + embroidery band | L | `(0.272,0.246)(0.277,0.252)(0.277,0.285)(0.272,0.290)` | EH_Bronze (thread) | body |
| 4 | boots M (visible at hem) | B | c=(0.075,0.24,0.20) s=(0.09,0.05,0.15) rd=0.02 e=3 | EH_Leather | body |
| 5 | upper robe | S | (0,0.70,0;0.145*0.115)->(0,0.84,0;0.130*0.105)->(0,0.97,0;0.150*0.100) | EH_Cloth | spine |
| 6 | belt | L | sides=18, `(0.148,0.72)(0.158,0.725)(0.158,0.755)(0.148,0.76)` | EH_Leather | body |
| 7 | belt buckle (anvil glyph) | E | 0.045 x 0.035 @0.150..0.162 at (0,0.74) | EH_Bronze | body |
| 8 | prayer beads **(asym, left hip)** | S + B | cord S (0.07,0.745,0.14)->(0.13,0.62,0.12)->(0.14,0.50,0.10) r 0.004 ; 12 beads B r 0.014 along it | EH_Bronze / EH_Stone | body |
| 9 | stole | E | plane XY: (-0.05,0.98)(0.05,0.98)(0.062,0.50)(0.0,0.44)(-0.062,0.50) @z 0.105..0.113 `~soft` (spine/body) b=0.004 | EH_Cloth (#7A2820) | spine |
| 10 | stole embroidery | E | 3 anvil/flame glyphs 0.04 on stole, raised 0.003 | EH_Bronze | spine |
| 11 | shoulder mantle | S | closed ring r 0.15 at y 0.98 tube 0.036 + back flare `+noise 0.008` | EH_Cloth | spine |
| 12 | shoulder cape pieces | B | M c=(+-0.15,0.99,0) s=(0.09,0.05,0.12) e=3 ; right one drooping lower (-0.03) | EH_Bronze | arm_L/arm_R |
| 13 | bell sleeve M | S | (+-0.14,0.98,0;0.040)->(+-0.17,0.84,0.06;0.052)->(+-0.19,0.78,0.10;0.070) wide cuff, r grows | EH_Cloth | arm / hand |
| 14 | sleeve inner cuff | L | rings at sleeve ends, inner radius 0.05, rim thickness 0.008 | EH_Cloth (soot) | hand_L/hand_R |
| 15 | hands M | B + S | palm s=(0.04,0.035,0.045) ; 4 finger tubes r 0.005 | EH_Leather | hand_L/hand_R |
| 16 | head | B | c=(0,1.075,0.012) s=(0.10,0.15,0.11) e=2.3 (gaunt long face) | EH_Leather (skin) | head |
| 17 | eyes (deep set) | B | s=(0.014,0.008,0.008) at (+-0.026,1.090,0.060), dim ember | EH_Ember x2 **F2** | head |
| 18 | hood shell **S** | L | sides=20, `(0.108,0.98)(0.118,1.04)(0.112,1.12)(0.088,1.19)(0.050,1.240)(0.016,1.268)(0,1.274)` , front cut-out window (width 0.09, y 1.03-1.16) | EH_Cloth | head |
| 19 | hood face opening rim | S | arc around the cut-out r 0.009 | EH_Bronze (embroidery) | head |
| 20 | hood peak tip cap | B | r 0.014 at (0,1.272,0) | EH_Bronze | head |
| 21 | hood back drape | E | (-0.10,1.02)(0.10,1.02)(0.13,0.72)(0.0,0.62)(-0.13,0.72) @-0.12..-0.112 `~soft` (head/spine) | EH_Cloth | spine |
| 22 | staff shaft **S** | S | (-0.20,0.22,0.10;0.020)->(-0.20,0.80,0.10;0.016)->(-0.20,1.28,0.12;0.015)->(-0.20,1.37,0.17;0.016) | EH_Bronze (dark, wrapped) | hand_R |
| 23 | staff grip wraps x5 | L | rings r 0.021, 0.012 tall at y 0.86-0.96 | EH_Leather | hand_R |
| 24 | staff foot cap | L | `(0.000,0.22)(0.024,0.22)(0.026,0.27)(0.020,0.30)` at ax=(-0.20,0.10) | EH_Steel | hand_R |
| 25 | staff crook | S | (-0.20,1.30,0.13;0.016)->(-0.20,1.38,0.18;0.014)->(-0.20,1.40,0.21;0.010) hooked end | EH_Bronze | hand_R |
| 26 | staff finials (flame ring) | C | 4 small tines n=4 len 0.04, at (-0.20,1.30,0.12) r 0.02 | EH_Bronze | hand_R |
| 27 | chain | S | links: (-0.20,1.38,0.17) -> (-0.205,1.30,0.16) -> (-0.21,1.22,0.14), r 0.004, 12 torus links alternating 90 deg | EH_Steel | top |
| 28 | censer cap | L | sides=14, `(0.000,1.215)(0.018,1.212)(0.040,1.185)(0.050,1.165)` ax=(-0.21,0.14) | EH_Bronze | top |
| 29 | censer bowl | L | sides=14, `(0.050,1.165)(0.056,1.130)(0.040,1.092)(0.016,1.075)(0.000,1.072)` ax=(-0.21,0.14) ; 8 vent slits 0.010 wide | EH_Bronze | top |
| 30 | censer coals **F1** | B | c=(-0.21,1.125,0.14) s=(0.07,0.05,0.07) e=2 emissive visible through vents | EH_Ember x6 | top |
| 31 | censer smoke wisp (geometry stub) | S | (-0.21,1.215,0.14;0.012)->(-0.21,1.34,0.12;0.003) translucent grey (VFX attaches here) | EH_Cloth (smoke) | top |
| 32 | censer rim studs | B | x8 r 0.006 at the bowl lip | EH_Steel | top |
| 33 | soot streaks / ash patches | texture | up the hood back and sleeve cuffs | EH_Cloth dark | head/arms |
| 34 | ember scorch seam on left cuff | texture | 3% area | EH_Ember x2 | hand_L |
(34 parts; budget <= 22k. F1 = censer coals; F2 = dim eye glints.)

## 5. Pose
Weight on the right foot, slight forward lean (3 deg); hood turned 5 deg left; right hand grips the staff 0.68 above the plinth, left hand hangs open-palmed at the hip, fingers curled. Censer hangs at rest, swaying slightly. The staff's crook leans 3 deg toward the viewer.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.20, 0.92, 0.10) staff grip | hand_R |
| `socket_cast` | (-0.21, 1.12, 0.14) censer centre | top |
| `socket_impact` | (0, 0.45, 1.45) fire wave contact | body |
| `socket_head` | (0, 1.30, 0) above hood peak | head |

Extras: `impactTime 1.10`, `strikeRange 1.50`, `attackStyle ranged`, `displayName "Emberhold Cinder Oracle"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 3.6 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.9 | top | rx +6, rz -4 (censer sway) |
| 1.8 | spine | rx +1.5 ; head rx -1.5 ; top rx -4, rz +5 |
| 2.7 | top | rx +4, rz -3 ; hand_R rz +1 |
| 3.6 | all | rest |

**Move** (loop 1.0 s; steps 0.25, 0.75) - glide
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +4, y 0 ; top rx +12 |
| 0.25 | body | y +0.02 (step), rz +2 |
| 0.5 | body | rx +6 ; top rx -14 |
| 0.75 | body | y +0.02 (step), rz -2 |
| 1.0 | all | = t0 |

**Attack** (2.4 s; impact 1.10)
| t | bone | value |
|---|---|---|
| 0.00-0.30 | raise | arm_R rx -22, hand_R rx -10 (staff lifts 0.05) ; spine rx -5 ; arm_L rx -30 |
| 0.30-0.95 | channel (io) | arm_L rx -80, hand_L rx -25 (palm out, particles at hand) ; head rx -8 ; spine rx -8 ; **top swings in a circle**: 0.30 rx +35 / 0.50 rz +50 / 0.70 rx -45 / 0.90 rz -55 / 0.95 rx +60 (speeds up) |
| 0.95-1.10 | **strike** (0.15 s snap) | arm_R rx -22 -> -75, hand_R rx -10 -> -30 ; top rx +60 -> +85 (censer whips forward) ; spine rx -8 -> +12 ; body z +0.10 |
| 1.10 | **impact** | fire wave leaves socket_cast toward socket_impact |
| 1.10-1.30 | hold | top rx +95 -> +60 ; arm_L holds |
| 1.30-2.40 | recover (io) | to rest; censer pendulum damped (rx +10, -6, +3) |

**HitReact** (0.45 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.10 | body | rx -11, z -0.07 ; spine rx -9 ; head rx -14 ; arm_R rx +8 ; top rx -30 (censer thrown back) |
| 0.45 | body rx -4 ; spine rx -3 ; head rx -5 ; top rx +8 |

**Victory** (1.8 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.6 | arm_R | rx -40, hand_R rx -10 (staff raised, planted taller) ; head rx -10 ; spine rx -6 |
| 0.8 | top | rx +30 -> -20 -> +10 (censer spin) |
| 1.8 | hold | arms raised, top damped |

## 8. Fragments (30)
Coarse: hood 4 chunks (the peak intact), robe 8 slabs (hem 4, mid 4), stole 2, shoulders 2, staff 3 bronze rods, censer 2 + coals 2 glowing lumps. Fine: sleeves 4, belt/beads 3. All chunky stone/bronze with `EH_Interior` ember cores; censer sprays sparks.

## 9. Readability
- vs `rime_bishop`: hooded cone with a mid-value red robe, bronze staff at the right, a heavy hanging censer vs a narrow dark silhouette with bare head, high gorget and a pale lantern with orbiting runes; Emberhold fill-black = cone + staff + dangling weight, perimeter/sqrt(area) ~ 4.2.
- vs other roles: only piece with a single tall peaked cone, no weapon, narrowest overall envelope (0.50); the 1.40 peak/staff sits between the knight (1.30) and the queen (1.55), and the unbroken cone separates it from the queen's flared skirt and crown.
