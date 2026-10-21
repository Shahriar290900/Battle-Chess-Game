# rime_bishop - Rime Frost Chanter

## 1. Identity
- **Name**: Rime Frost Chanter. **Concept**: a gaunt drowned caster in layered frozen robes, frost-white beard, a crooked staff from whose hook hangs a lantern of trapped blue light; five ice runes orbit the lantern.
- **Signature shape**: lantern staff + orbiting runes (runes ring r 0.14, ~15% larger than natural, floating with visible gaps). Silhouette = spindly narrow figure with a tall crooked staff, and a detached ring of floating tablets at the top right.

## 2. Dimensions (total 1.40)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Robe hem + frost | 0.22-0.34 | jagged hem r 0.24 |
| Robe layers | 0.30-0.78 | 3 layers |
| Torso + gorget | 0.76-1.00 | gorget fan reaches 1.06 |
| Head | 1.00-1.14 | head 0.14, figure 1.00 (0.22->1.22 with crown spikes) |
| Ice crown spikes | 1.14-1.22 | |
| Staff | 0.22-1.38 | crook end (-0.18,1.38,0.14) |
| Lantern | 1.14-1.30 | hangs from the hook |
| Orbit runes | 1.18-1.40 | ring r 0.14 around the lantern, top 1.40 |
Envelope: 0.50 wide (x -0.25..0.25 with runes) x 0.46 deep. 7.1 heads.

## 3. Bone pivots (x, y, z)
root (0,0,0) | body (0,0.58,0) | spine (0,0.70,0) | head (0,0.98,0.02) | top (-0.19,1.24,0.15) (rune orbit centre = lantern centre) | arm_L (0.13,0.96,0) | hand_L (0.16,0.82,0.07) | arm_R (-0.13,0.96,0) | hand_R (-0.17,0.82,0.07)

## 4. Part list
Pedestal parts per README section 2.

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
| 14 | head | B | c=(0,1.05,0.015) s=(0.095,0.145,0.105) e=2.2 gaunt, cheek hollows via noise 0.008 | RH_Armour (pale-grey skin: use RH_Frost mixed 40%) | head |
| 15 | eye glow **F1** | B | s=(0.014,0.008,0.008) at (+-0.024,1.07,0.065) | RH_Glow x6 | head |
| 16 | frozen beard **S** | C | n=9 drips: base along jaw (0,1.00,0.06) spread +-0.04, len 0.08-0.18, r 0.010-0.014, tilt down-forward 15 | RH_Frost / RH_Ice | head |
| 17 | beard mass | B | c=(0,0.97,0.05) s=(0.07,0.07,0.06) e=2 | RH_Frost | head |
| 18 | ice crown spikes | C | n=5 ring r 0.05 at y 1.12 (tilt 15), len 0.05-0.10 ; uneven (one broken) | RH_Ice | head |
| 19 | scalp straps + silver diadem | S | band S ring r 0.056 at y 1.10, tube 0.005 | RH_Silver | head |
| 20 | back-of-head cowl scrap | E | (0,1.12)(0.07,1.08)(0.09,0.92)(0.0,0.86)(-0.08,0.94)(-0.06,1.08) @-0.07..-0.063 `~soft` | RH_Cloth | head |
| 21 | staff shaft (crooked) **S** | S | (-0.19,0.22,0.12;0.020)->(-0.19,0.60,0.12;0.015)->(-0.20,0.95,0.11;0.014)->(-0.21,1.15,0.12;0.015)->(-0.20,1.30,0.14;0.013)->(-0.17,1.37,0.17;0.011)->(-0.13,1.36,0.19;0.008) hooked, bark-like twist noise 0.006 | RH_Obsidian | hand_R |
| 22 | staff silver bands x4 | L | rings r +0.004 at y 0.50, 0.80, 1.05, 1.28 | RH_Silver | hand_R |
| 23 | staff foot spike | C | n=1 len 0.06 down, ice | RH_Ice | hand_R |
| 24 | staff ice growth (mid) | C | base=(-0.21,0.95,0.11) n=4 len 0.05-0.11 r 0.008-0.014 | RH_Ice | hand_R |
| 25 | lantern chain | S | (-0.13,1.36,0.19)->(-0.17,1.31,0.15), r 0.004, 5 links | RH_Silver | hand_R |
| 26 | lantern cage | S | 4 vertical bars r 0.006 from (-0.19,1.15,0.15)+-0.035 to (+-0.02,1.30) with top & bottom rings ; hex section | RH_Silver | hand_R |
| 27 | lantern ice glass | B | c=(-0.19,1.22,0.15) s=(0.07,0.12,0.07) e=3 | RH_Ice | hand_R |
| 28 | lantern light core **F2** | B | c=(-0.19,1.22,0.15) s=(0.04,0.07,0.04) e=2 emissive | RH_Glow x5 | hand_R |
| 29 | lantern cap + base | L | cap `(0,1.30)(0.03,1.285)(0.045,1.275)`; base `(0,1.14)(0.035,1.15)(0.02,1.16)` at ax=(-0.19,0.15) | RH_Silver | hand_R |
| 30 | orbit runes x5 | E | each tablet (-0.025,-0.035)(0.025,-0.035)(0.03,0.0)(0.025,0.035)(-0.025,0.035)(-0.03,0) @-0.007..0.007 b=0.004, rune glyph raised 0.003 ; positions on circle r 0.14 centred (-0.19,y,0.15): angles 0/72/144/216/288, y = 1.20/1.30/1.24/1.34/1.28 (tallest 1.37 to 1.40 with tilt), each tilted 15 to 30 deg | RH_Ice with RH_Glow glyph | top |
| 31 | rune glyph glow | E | glyph lines on each tablet, 0.004 wide | RH_Glow x3 | top |
| 32 | rune connection motes | B | 3 small drifting crystals r 0.008 between runes | RH_Ice | top |
| 33 | frost drips from sleeves/robe | C | n=10 small | RH_Frost | body/arms |
| 34 | back frost ridge (small) | C | base=(0,0.92,-0.08) n=3 len 0.06-0.10 | RH_Ice | spine |
(34 parts; budget <= 22k. F1 = eyes, F2 = lantern core (runes' glyph glow is a texture accent <= 3%).)

## 5. Pose
Gaunt, slightly stooped (spine 5 deg forward), chin tucked; right hand on the staff at 0.92; left hand held open at the hip, fingers spread, icicles hanging from the cuff. The orbit runes hang in a slow ring around the lantern. Head turned 6 deg left; beard drips visible from the front 45-degree camera.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.19, 0.92, 0.12) staff grip | hand_R |
| `socket_cast` | (-0.19, 1.22, 0.15) lantern centre | top |
| `socket_impact` | (0, 0.70, 1.45) beam end | body |
| `socket_head` | (0, 1.24, 0.02) | head |

Extras: `impactTime 1.10`, `strikeRange 1.50`, `attackStyle ranged`, `displayName "Rime Frost Chanter"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 3.4 s) - the runes turn slowly
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 1.7 | top | ry +180 (runes orbit half-turn, lin) |
| 3.4 | top | ry +360 (full orbit) -> ends on rest pose visually |
| 1.0 | spine | rx +1.4 ; head rx -1.5, ry +2 |
| 2.2 | hand_R | rz +1.2 ; head rz -2 |
| 3.4 | all | rest |

**Move** (loop 1.0 s; steps 0.25, 0.75) - drifts
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +5 ; top ry 0 |
| 0.25 | body | y +0.02 (step), rz -2 |
| 0.5 | body | rx +7 ; head rx +4 ; top ry +180 |
| 0.75 | body | y +0.02 (step), rz +2 |
| 1.0 | all | = t0 ; top ry +360 |

**Attack** (2.4 s; impact 1.10)
| t | bone | value |
|---|---|---|
| 0.00-0.30 | raise | arm_R rx -20 (lantern lifts) ; spine rx -5 ; head rx -6 |
| 0.30-0.95 | channel (io) | arm_L rx -85, hand_L rx -15 (hand opens toward target) ; top ry 0 -> +900 accelerating (runes whirl), top sx,sz 1 -> 1.15 ; head rx -8 ; spine rx -8 ; lantern flare (engine) |
| 0.95-1.10 | **strike** (0.15 s snap) | arm_R rx -20 -> -70 (staff thrust), hand_R rx -10 ; top sx,sz 1.15 -> 0.3 (runes converge on the lantern; ry +900 -> +1080) ; spine -8 -> +10 ; body z +0.10 |
| 1.10 | **impact** | beam fires from socket_cast to socket_impact |
| 1.10-1.30 | hold | pose held, top sx,sz 0.3 -> 0.6 |
| 1.30-2.40 | recover (io) | to rest; runes re-orbit (sx,sz 1.0 by 2.0) |

**HitReact** (0.45 s) - freezes mid-pose when the engine freezes the target
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.10 | body | rx -12, z -0.07 ; spine rx -10 ; head rx -16 ; arm_R rx +10 ; top ry +40 (runes jolt) |
| 0.45 | body rx -5 ; spine rx -4 ; head rx -6 |

**Victory** (1.8 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.6 | arm_R | rx -45, hand_R rx -15 (staff held high) ; arm_L rx -50 ; head rx -12 ; spine rx -6 |
| 1.0 | top | ry +720 (runes whirl), sx,sz 1.2 |
| 1.8 | hold | top sx,sz 1.0 |

## 8. Fragments (30)
Sharp: 10 long robe/ice shards (thin triangles), 5 gorget plates (flat 3-5-sided obsidian), 4 beard icicles, staff 3 splinters + hook as 1 curved shard, lantern glass 3 (cyan flash), 5 rune tablets (intact, flying) and sleeves/hands 4. `RH_Interior` pale ice; the lantern light bursts as a cyan flash.

## 9. Readability
- vs `emberhold_bishop`: narrow, darker, jagged hem and a floating ring of tablets; bare head with ice crown and long white beard vs a hooded smooth cone; lantern (cold, pale) vs hanging censer (warm); Rime perimeter/sqrt(area) ~ 6.
- vs other roles: only humanoid whose silhouette includes detached floating parts; peak at 1.40 formed by the rune ring and staff hook, not by a crown.
