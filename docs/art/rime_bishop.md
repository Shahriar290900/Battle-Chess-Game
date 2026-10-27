# rime_bishop - Rime Frost Chanter

## 1. Identity
- **Name**: Rime Frost Chanter. **Concept**: a gaunt drowned caster in layered frozen robes and a frost-white beard, wearing a tall **translucent ice mitre split by a deep glowing diagonal slit**; a crooked staff from whose hook hangs a lantern of trapped blue light; five ice runes orbit the lantern.
- **Identity cue (the cyan-slit mitre)**: a faceted ice mitre, base y 1.070, top 1.322 (0.25 tall, 0.160 wide, 1.7x the head, +20% over the old crown), with a **diagonal slit 0.036 wide x 0.050 deep from (-0.072,1.248) to (+0.072,1.138), 38 deg, the same direction as the Emberhold slit, with a cyan glow strip inside**. Pale ice mitre against the dark robe + glowing slit = the brightest, most legible element on the piece. The old spiky ice crown is removed so the head can never read as a queen.
- Silhouette: spindly narrow figure, ogive mitre, tall crooked staff, and a detached ring of floating tablets around the lantern on the character's right (viewer's left, x < 0), clear of the mitre.

## 2. Dimensions (total 1.40)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Robe hem + frost | 0.22-0.34 | jagged hem r 0.24 |
| Robe layers | 0.30-0.78 | 3 layers |
| Torso + gorget | 0.76-1.00 | gorget fan reaches 1.06 |
| Head | 0.945-1.09 | head 0.145 |
| Ice mitre | 1.070-1.322 | faceted ogive, width 0.160 x depth 0.115, slit y 1.138-1.248 |
| Staff | 0.22-1.38 | crook end (-0.20,1.38,0.14) after the -0.03 shift |
| Lantern | 1.14-1.30 | hangs from the hook |
| Orbit runes | 1.18-1.36 | ring r 0.11 around the lantern (x -0.33..-0.11): clear of the mitre (half-width <= 0.08 at those heights) by >= 0.03 |
Envelope: body 0.50 wide x 0.46 deep; with the runes x -0.33..0.25 (floating parts excepted). 7.1 heads.

## 3. Rig (humanoid template) and bone pivots
`humanoid_rig(J, weapon=(-0.22,0.80,0.12))`, then re-parent `top` under `weapon` (the rune ring and the lantern ride the staff). No cape chain.

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`body`) | (0,0.58,0) | | elbow_L | (0.16,0.82,0.07) |
| spine | (0,0.70,0) | | wrist_L | (0.18,0.76,0.11) |
| chest | (0,0.84,0) | | wrist_R (staff grip) | (-0.22,0.88,0.12) |
| neck | (0,0.95,0.015) | | hip_L | (0.06,0.60,0) |
| head | (0,0.98,0.02) | | knee_L | (0.07,0.40,0.04) |
| top (rune orbit centre = lantern) | (-0.22,1.22,0.15) | | ankle_L | (0.065,0.26,0.05) |
| clavicle_L | (0.06,0.95,0) | | toe_L | (0.065,0.245,0.12) |
| shoulder_L | (0.13,0.96,0) | | weapon (staff centre) | (-0.22,0.80,0.12) |

**Coordinate shift for rows 21-32**: the staff, lantern and runes move 0.03 outboard: add x' = x - 0.03 to every x coordinate in rows 21-29 and 31-32; row 30 is rewritten below (orbit r 0.11).

**Binding (authoritative)**: 1-5, 33 -> `body` (robe `~soft` `thigh`); 6-8, 34 -> `chest`/`spine`; 9 -> `chest`; 10 -> `arm_L`; 11 -> `arm`/`hand` `~soft`; 12 -> `hand_L/R`; 13 -> `wrist_L/R`; 14-20 -> `head` (beard 16/17 `~soft` `neck`; lappets in 20 `~soft` `head`); 21-29 -> `weapon` (lantern swings with the staff); 30-32 -> `top`.

## 4. Part list
Pedestal parts per README section 2.
**Part numbers are stable ids; gaps = removed parts.** The Bone column uses legacy names; the binding table in section 3 is authoritative (new rig template). Rows 21-32 take the x-0.03 shift from section 3.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | robe layer 1 (outer, torn) **S** | L | sides=14 faceted, `(0.000,0.22)(0.238,0.225)(0.245,0.26)(0.230,0.40)(0.190,0.55)(0.140,0.68)(0.000,0.70)` ; hem cut into 14 jagged tongues of varying length (0.03-0.09) | RH_Cloth | body |
| 2 | robe layer 2 (under) | L | sides=12, `(0.000,0.24)(0.205,0.245)(0.200,0.32)(0.170,0.46)(0.135,0.60)(0.000,0.62)` offset ry 12, shorter hem | RH_Armour | body |
| 3 | robe layer 3 (waist wrap) | S | spiral band (0,0.62,0;0.145)->(0,0.76,0;0.135) pitch 0.04 3 turns, tube r 0.018 | RH_Cloth | body |
| 4 | hem frost build-up | C | n=18 along the hem, len 0.03-0.07, r 0.006-0.012, tilt out 40 | RH_Frost / RH_Ice | body |
| 5 | boots (barely visible) M | B | c=(0.07,0.24,0.18) s=(0.07,0.04,0.13) rd=0.02 | RH_Obsidian | body |
| 6 | chest robe | S | (0,0.70,0;0.12*0.09)->(0,0.84,0;0.11*0.085)->(0,0.96,0;0.13*0.090) | RH_Cloth | spine |
| 7 | chest plate shards (asymmetric, left only) | E | 3 overlapping triangles: (0.02,0.90)(0.12,0.92)(0.07,0.80); (0.02,0.84)(0.10,0.82)(0.05,0.72); (0.02,0.78)(0.09,0.74)(0.05,0.66) @0.085..0.097 b=0.004 | RH_Obsidian | spine |
| 8 | silver wire lacing | S | zig-zag across robe front (x +-0.07, y 0.62-0.92), 8 loops r 0.004 | RH_Silver | spine |
| 9 | gorget (high collar) **S** | E | fan of 7 obsidian plates around the neck: each (0,0)(0.025,0)(0.018,0.10)(0,0.12) at radius 0.08, rotated k*30 deg from -90 to +90, y base 0.97, tips y up to 1.06 | RH_Obsidian | spine |
| 10 | shoulder pieces | B | L c=(0.15,0.97,0) s=(0.09,0.045,0.09) (obsidian, frost cap) ; R is bare cloth drape (asymmetry) | RH_Obsidian / RH_Frost | arm_L |
| 11 | sleeve M | S | (+-0.13,0.96,0;0.032)->(+-0.16,0.83,0.07;0.040)->(+-0.17,0.78,0.11;0.055) ragged cuffs | RH_Cloth | arm / hand |
| 12 | cuff icicles M | C | n=4 at wrist len 0.04-0.07 | RH_Ice | hand_L/hand_R |
| 13 | hand M | S | bony fingers: 4 tubes r 0.005 len 0.05 + thumb ; palm B s=(0.035,0.03,0.04) | RH_Frost (grey-white) | hand_L/hand_R |
| 14 | head | B | c=(0,1.02,0.015) s=(0.095,0.145,0.105) e=2.2 gaunt, cheek hollows via noise 0.008 | RH_Armour (pale-grey skin: use RH_Frost mixed 40%) | head |
| 15 | eyes (dim, part of the head cluster) | B | s=(0.014,0.008,0.008) at (+-0.024,1.040,0.065) | RH_Glow x3 | head |
| 16 | frozen beard **S** | C | n=9 drips: base along jaw (0,0.98,0.06) spread +-0.04, len 0.08-0.18, r 0.010-0.014, tilt down-forward 15 | RH_Frost / RH_Ice | head |
| 17 | beard mass | B | c=(0,0.95,0.05) s=(0.07,0.07,0.06) e=2 | RH_Frost | head |
| 18 | **ice mitre shell S** | L | sides=8 faceted, scale z 0.72 (width 0.160 x depth 0.115), `(0.080,1.070)(0.088,1.100)(0.084,1.150)(0.070,1.205)(0.048,1.255)(0.024,1.295)(0.007,1.318)(0,1.322)` ; chamfer 0.004 ; 1 chipped notch 0.03 wide on the upper-left edge (asymmetry) ; inner cracks | RH_Ice (value >= 0.70) | head |
| 19 | **mitre slit S F1** | cut + E | diagonal groove across the front, centreline from (-0.072,1.248) to (+0.072,1.138) (38 deg), 0.036 wide at the surface tapering to 0.006 at depth 0.050, round-capped, continues 25% around the flank ; glow strip E 0.016 wide inside along the full length ; silver lip wire r 0.004 on both edges | RH_Glow x5 / RH_Silver | head |
| 20 | mitre base band + lappets | L + E | band `(0.084,1.066)(0.090,1.070)(0.090,1.090)(0.084,1.094)` scale z 0.72, silver ; 2 tattered lappets E (-0.026,0)(0.026,0)(0.022,-0.16)(0,-0.20)(-0.022,-0.16) at x=+-0.05, z -0.07, hanging from y 1.08 `~soft` | RH_Silver / RH_Cloth | head |
| 21 | staff shaft (crooked) **S** | S | (-0.19,0.22,0.12;0.020)->(-0.19,0.60,0.12;0.015)->(-0.20,0.95,0.11;0.014)->(-0.21,1.15,0.12;0.015)->(-0.20,1.30,0.14;0.013)->(-0.17,1.37,0.17;0.011)->(-0.13,1.36,0.19;0.008) hooked, bark-like twist noise 0.006 | RH_Obsidian | hand_R |
| 22 | staff silver bands x4 | L | rings r +0.004 at y 0.50, 0.80, 1.05, 1.28 | RH_Silver | hand_R |
| 23 | staff foot spike | C | n=1 len 0.06 down, ice | RH_Ice | hand_R |
| 24 | staff ice growth (mid) | C | base=(-0.21,0.95,0.11) n=4 len 0.05-0.11 r 0.008-0.014 | RH_Ice | hand_R |
| 25 | lantern chain | S | (-0.13,1.36,0.19)->(-0.17,1.31,0.15), r 0.004, 5 links | RH_Silver | hand_R |
| 26 | lantern cage | S | 4 vertical bars r 0.006 from (-0.19,1.15,0.15)+-0.035 to (+-0.02,1.30) with top & bottom rings ; hex section | RH_Silver | hand_R |
| 27 | lantern ice glass | B | c=(-0.19,1.22,0.15) s=(0.07,0.12,0.07) e=3 | RH_Ice | hand_R |
| 28 | lantern light core **F2** | B | c=(-0.19,1.22,0.15) s=(0.04,0.07,0.04) e=2 emissive | RH_Glow x5 | hand_R |
| 29 | lantern cap + base | L | cap `(0,1.30)(0.03,1.285)(0.045,1.275)`; base `(0,1.14)(0.035,1.15)(0.02,1.16)` at ax=(-0.19,0.15) | RH_Silver | hand_R |
| 30 | orbit runes x5 | E | each tablet (-0.025,-0.035)(0.025,-0.035)(0.03,0.0)(0.025,0.035)(-0.025,0.035)(-0.03,0) @-0.007..0.007 b=0.004, rune glyph raised 0.003 ; positions on a **horizontal circle r 0.11** centred (-0.22,y,0.15): angles 0/72/144/216/288, y = 1.20/1.29/1.24/1.33/1.27 (top <= 1.36 with tilt), each tilted 15 to 30 deg | RH_Ice with RH_Glow glyph | top |
| 31 | rune glyph glow | E | glyph lines on each tablet, 0.004 wide | RH_Glow x3 | top |
| 32 | rune connection motes | B | 3 small drifting crystals r 0.008 between runes | RH_Ice | top |
| 33 | frost drips from sleeves/robe | C | n=10 small | RH_Frost | body/arms |
| 34 | back frost ridge (small) | C | base=(0,0.92,-0.08) n=3 len 0.06-0.10 | RH_Ice | spine |
(34 parts; budget <= 22k. F1 = head cluster (mitre slit + dim eyes); F2 = lantern core (runes' glyph glow is a texture accent <= 3%). Rows 18-20 replace the old ice crown spikes, scalp straps/diadem and cowl scrap.)

## 5. Pose
Gaunt, slightly stooped (spine 5 deg forward), chin tucked; right hand on the staff at 0.92; left hand held open at the hip, fingers spread, icicles hanging from the cuff. The orbit runes hang in a slow ring around the lantern. Head turned 6 deg left so the slit faces the 36 deg seat camera; beard drips visible from the front 45-degree camera. The mitre stays level and unobstructed.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.22, 0.92, 0.12) staff grip | weapon |
| `socket_cast` | (-0.22, 1.22, 0.15) lantern centre | top |
| `socket_impact` | (0, 0.70, 1.45) beam end | body |
| `socket_head` | (0, 1.36, 0.02) above the mitre | head |

Extras: `impactTime 1.10`, `strikeRange 1.50`, `attackStyle ranged`, `displayName "Rime Frost Chanter"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Legs/pelvis | Torso/neck/head | Arms/staff | Secondary (`top` rune ring, lappets, hem).

**Idle** (loop 3.4 s) - the runes turn slowly
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest |
| 1.0 | body x +0.005, rz +1.5; thigh_L rx -1 | chest rx -1.4, spine rx -0.6; head rx -1.5, ry +2 (the slit glints) | | top ry +120 (runes orbit, lin) |
| 1.7 | | | | top ry +180 |
| 2.2 | body x -0.005 | head rz -2 | wrist_R rz +1.2 (staff creaks) ; hand_L rx -3 (fingers spread) | top ry +270; lappets sway +-3 |
| 3.4 | rest | rest | rest | top ry +360 (full orbit = visually rest) |

**Move** (loop 1.0 s; steps 0.25, 0.75) - drifts, the staff drags a frost line
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.0 | body rx +5; thigh_L rx -10, shin_L rx +6 | spine ry +3 | staff planted | top ry 0 |
| 0.25 | step L: body y +0.02, rz -2; thigh_R rx +18, shin_R rx +36 | head rz -1.5 | staff slides forward 0.04 | top ry +90 |
| 0.5 | body rx +7 | head rx +4 | | top ry +180 |
| 0.75 | step R: body y +0.02, rz +2 | head rz +1.5 | | top ry +270 |
| 1.0 | = t0 | | | top ry +360 |

**Attack** (2.4 s; **impact 1.10**) - runes whirl, converge into a beam
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | body rx -2; weight back | spine rx -5; head rx -6 | arm_R rx -20 (lantern lifts) | |
| 0.30-0.95 (io) | feet planted; body y +0.01 | spine rx -8; head rx -8 (mitre tips back; slit flares) | arm_L rx -85, hand_L rx -15 (hand opens toward the target); staff held | top ry 0 -> +900 accelerating (runes whirl), top sx,sz 1 -> 1.15 ; lantern flare (engine) |
| 0.95-1.10 (snap; pelvis leads 0.06 s) | body z +0.10; lunge thigh_L rx -10, shin_L rx +14 | spine rx -8 -> +10 | arm_R rx -20 -> -70 (staff thrust), hand_R rx -10 | top sx,sz 1.15 -> 0.3 (runes converge on the lantern), ry +900 -> +1080 |
| 1.10 | **impact**: beam fires from `socket_cast` to `socket_impact` | | | |
| 1.10-1.30 hold | pose held | | | top sx,sz 0.3 -> 0.6 |
| 1.30-2.40 (io) | to rest | to rest | to rest | runes re-orbit (sx,sz 1.0 by 2.0) |

**HitReact** (0.45 s) - freezes mid-pose when the engine freezes the target
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.10 | body rx -12, z -0.07; thigh_L rx +6, shin_L rx +10 | spine rx -10; head rx -16 (+0.04 s) | arm_R rx +10 | top ry +40 (runes jolt); lappets +14 |
| 0.45 | body rx -5 | spine rx -4, head rx -6 | | |

**Victory** (1.8 s, ends held)
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest |
| 0.6 | body y +0.015 | spine rx -6; head rx -12 | arm_R rx -45, hand_R rx -15 (staff held high); arm_L rx -50 | |
| 1.0 | | | | top ry +720 (runes whirl), sx,sz 1.2 |
| 1.8 | hold | hold | hold | top sx,sz 1.0 |

**Taunt** (1.3 s, once) - the runes fan out and point, the slit blazes
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.00-0.35 | body rx -2 | chest rx -4; head rx -6, ry toward the foe | arm_R rx -25, hand_R rx -10 (staff tips toward the target) | top ry +200, sx,sz 1 -> 1.2 |
| 0.35-0.90 | hold | head rz +6 (slow tilt) | arm_L rx -55, hand_L rx -30, wrist_L rx -20 (open palm, fingers beckon x2) | runes freeze into a line pointing at the foe (top ry stops at the foe's bearing); slit glow +40% |
| 0.90-1.30 | settle | head level | arms drop | runes resume orbit |

**Surrender** (2.2 s, once, holds the last pose) - lets the staff fall, kneels, the runes die
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.04 | head rx -10 | wrist_R opens (rx +25) | runes jolt top ry +60 |
| 0.30-0.55 | | | **`weapon` (staff + lantern + `top` runes) released at 0.45**: topples sideways, bounces twice, lantern glass cracks (cyan flash) | runes stop orbiting, fall with the staff |
| 0.55-1.20 (io) | kneel: body y -0.26; thigh_L rx -75, shin_L rx +95; thigh_R rx +20, shin_R rx +108 | spine rx +10 | arms hang | hem tongues spread on the plinth |
| 1.20-1.75 | hold | spine rx +20, chest rx +10, neck rx +20, head rx +30 (mitre bows; slit glow dims to 30%) | hands to the thighs, palms up | lappets fall forward |
| 1.75-2.20 | hold | slow breath | hold | |

## 8. Fragments (30)
Sharp: 10 long robe/ice shards (thin triangles), **mitre 4 (two long wedges either side of the slit that keep a cyan edge glow + apex shard)**, 5 gorget plates (flat 3-5-sided obsidian), 4 beard icicles, staff 3 splinters + hook as 1 curved shard, lantern glass 3 (cyan flash), 5 rune tablets (intact, flying) and sleeves/hands 3. `RH_Interior` pale ice; the lantern light bursts as a cyan flash.

## 9. Readability
- **Identity cue**: translucent ice mitre with a glowing cyan diagonal slit; lantern staff + orbiting runes.
- vs `emberhold_bishop`: narrow, darker, jagged hem and a floating ring of tablets; pale translucent mitre with a glowing slit vs opaque bronze mitre with a red slit; bare gaunt face with a long white beard vs a cowled collar; cold lantern vs warm hanging censer; Rime perimeter/sqrt(area) ~ 6.
- vs `rime_queen`: no spiked ring (the queen has nine tines and a halo); a single smooth mitre; no skirt flare.
- vs other roles: only humanoid whose silhouette includes detached floating parts; the 1.40 peak comes from the staff hook, the mitre peaks at 1.322.
- Silhouette test: the slit glow is a >= 4 px bright diagonal at 60 px; top-down: an elongated oval (mitre) with a bright diagonal line.
