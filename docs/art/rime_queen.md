# rime_queen - Rime Pale Tide Queen

## 1. Identity
- **Name**: Rime Pale Tide Queen. **Concept**: a tall spectral queen in obsidian gown-armour whose hem frays into drifting ice; a translucent ice veil, silver wire lacing, frost trailing across the floor. Her great crystal glaive is pulled from the air during Attack.
- **Signature shape**: a floating crescent halo of ice behind the head (outer r 0.21, floating, points up; tip y 1.55, ~15% oversize). Silhouette = narrow column gown, one wing-like ice shoulder, floating crescent over the head, ragged ice hem trailing behind.
- **Idle**: no weapon visible (`weapon_summon` scale 0).

## 2. Dimensions (total 1.55)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Trailing ice hem + floor frost | 0.22-0.40 | z -0.38..0.20, r 0.27 |
| Gown skirt | 0.26-0.85 | slim, r 0.24 -> 0.11 |
| Waist | 0.80-0.90 | r 0.095 |
| Torso + shoulders | 0.88-1.14 | width 0.40, L ice-wing shoulder to 1.30 |
| Neck | 1.14-1.22 | |
| Head | 1.22-1.39 | head 0.17 |
| Circlet + veil | 1.30-1.42 | |
| Halo crescent | 1.28-1.55 | floats behind head, z -0.15..-0.10, gap to skull 0.04+ |
Envelope: 0.60 wide (hem shards + wing) x 0.58 deep (hem trail z -0.38..0.20).

## 3. Bone pivots (x, y, z)
root (0,0,0) | body (0,0.78,0) | spine (0,0.90,0) | head (0,1.19,0.01) | top (0,1.40,-0.12) (halo; floats and rotates a few degrees) | arm_L (0.19,1.12,0) | hand_L (0.23,0.92,0.04) | arm_R (-0.19,1.12,0) | hand_R (-0.24,0.92,0.04) | node `weapon_summon` child of hand_R at (-0.24,0.80,0.12).

## 4. Part list
Pedestal parts per README section 2.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | gown skirt inner (tide folds) **S** | L | sides=16 faceted, `(0.000,0.26)(0.215,0.265)(0.222,0.34)(0.200,0.50)(0.160,0.66)(0.120,0.80)(0.100,0.88)(0.000,0.88)` + fold noise 0.007 | RH_Armour | body |
| 2 | gown outer panels x8 | E | curved tall plates (-0.06,0.88)(0.06,0.88)(0.080,0.30)(0,0.24)(-0.080,0.30) @r 0.12-0.23 flaring, rot k*45 deg, thickness 0.012 b=0.006, jagged lower point, alternating lengths 0.60/0.52 | RH_Obsidian | body |
| 3 | tide-wave trim (silver) x3 rows | S | scalloped wave curves on the panels: arc r 0.03, 6 per row, rows at y 0.40/0.55/0.70, tube r 0.004 | RH_Silver | body |
| 4 | fraying hem tongues x16 | E | each (0,0)(0.03,0)(0.02,-0.12)(0,-0.20)(-0.02,-0.12)(-0.03,0) hanging below y 0.30 tilted outward 25 deg, lengths 0.08-0.20, translucent | RH_Ice (cloth-to-ice gradient: top RH_Cloth) | body |
| 5 | trailing ice train (rear) **S** | C | base=(0,0.26,-0.20) n=7 len 0.10-0.22, r 0.020-0.040, up=(0,0.35,-1) tilt 20, drags onto z -0.38 | RH_Ice | body |
| 6 | floor frost trail | E | irregular fan decal on plinth top (0,0.222,-0.10)(+-0.20,0.222,-0.30) thickness 0.006, fringe of 20 tiny crystals len 0.02-0.04 | RH_Frost | body |
| 7 | belt of linked plates | L / B | `(0.098,0.84)(0.106,0.845)(0.106,0.880)(0.098,0.885)` + 5 diamond plates B s=(0.04,0.05,0.012) | RH_Obsidian / RH_Silver | body |
| 8 | torso | S | (0,0.86,0;0.095*0.070)->(0,0.98,0;0.112*0.078)->(0,1.10,0;0.135*0.082) slender | RH_Armour | spine |
| 9 | bodice plate **S** | E | (-0.105,0.90)(0.105,0.90)(0.130,1.02)(0.115,1.12)(0.0,1.14)(-0.115,1.12)(-0.130,1.02) @0.070..0.092 b=0.010 faceted ridge, vertical facet lines | RH_Obsidian | spine |
| 10 | silver lacing | S | criss-cross lacing across bodice, 10 crossings, r 0.004 | RH_Silver | spine |
| 11 | collar crystals (gorget) | C | n=7 around neck r 0.07, len 0.05-0.11, tilt out 25 | RH_Ice | spine |
| 12 | shoulder wing L (ice, tall) **S** | C | base=(0.19,1.12,0) n=5 fan: len 0.10,0.15,0.18,0.14,0.09 ; r 0.020-0.032 ; up=(0.5,1,-0.2) fan 40 deg ; highest tip y 1.30 | RH_Ice | arm_L |
| 13 | shoulder R (smaller obsidian guard; asymmetric) | B | c=(-0.19,1.14,0) s=(0.11,0.05,0.11) rd=0.015 e=3 + frost cap | RH_Obsidian / RH_Frost | arm_R |
| 14 | pauldron L base | B | c=(0.19,1.12,0) s=(0.12,0.05,0.12) e=3 | RH_Obsidian | arm_L |
| 15 | upper arm M | S | (+-0.19,1.12,0;0.034)->(+-0.22,0.98,0.02;0.027)->(+-0.23,0.93,0.04;0.024) | RH_Armour | arm |
| 16 | forearm + vambrace M | S | (+-0.23,0.93,0.04;0.026)->(+-0.24,0.86,0.12;0.021)->(+-0.24,0.80,0.17;0.016) ; vambrace E fins plane=YZ (0.90,0.06)(0.84,0.14)(0.86,0.17)(0.91,0.10) | RH_Obsidian / RH_Silver | hand |
| 17 | hands M (taloned) | B + S | palm s=(0.038,0.035,0.045) ; fingers 4 x S len 0.055 r 0.006 ending in ice claws | RH_Armour / RH_Ice | hand |
| 18 | head | B | c=(0,1.305,0.01) s=(0.105,0.17,0.115) e=2.3 elongated, hollow cheeks | RH_Frost mixed pale skin | head |
| 19 | eyes **F1** | B | s=(0.018,0.008,0.008) at (+-0.028,1.315,0.063) | RH_Glow x6 | head |
| 20 | ice veil **S** | E | plane XY curved: (-0.062,1.285)(0.062,1.285)(0.075,1.19)(0.0,1.15)(-0.075,1.19) @0.060..0.066 jagged hem, translucent, with fold noise 0.005 | RH_Ice (thin, transmission) | head |
| 21 | circlet | S | ring r 0.058 at y 1.37 tube 0.005, + point gem C n=1 len 0.05 at front | RH_Silver / RH_Ice | head |
| 22 | hair strands (frost) x7 | S | (0,1.34,-0.04;0.010)->(+-0.05,1.20,-0.12)->(+-0.09,1.00,-0.20;0.002), flowing back, translucent | RH_Frost / RH_Ice | top (~soft with head) |
| 23 | halo crescent **S** | E | plane XY, outer r 0.21, inner r 0.155, centre (0,1.34), spanning angles 20 deg -> 160 deg then wrapped to a crescent (thick at the top, thin at the tips) ; 14 samples per arc ; thickness z -0.145..-0.105 b=0.006 ; top of the arc y 1.55 | RH_Ice | top |
| 24 | halo outer thorns x9 | C | along the outer edge, len 0.03-0.07, r 0.008-0.012, radiating | RH_Ice | top |
| 25 | halo inner glow line **F2** | S | arc r 0.158 inside the crescent, tube 0.004 | RH_Glow x4 | top |
| 26 | halo orbit shards x3 | C | floating shards near the tips, len 0.05, gap 0.04 from halo | RH_Ice | top |
| 27 | back cape (shrouded mist cloak) | E | (-0.14,1.14)(0.14,1.14)(0.22,0.70)(0.20,0.34)(0.10,0.30)(0,0.40)(-0.10,0.30)(-0.20,0.36)(-0.22,0.70) @-0.120..-0.114 `~soft` (spine/top), jagged ice-fray hem | RH_Cloth | top |
| 28 | cape frost caps | C | n=12 along the shoulder line and folds len 0.02-0.05 | RH_Frost | top |
| 29 | knee-bone spikes (through gown) M | C | n=2 at (+-0.08,0.52,0.18) len 0.05, pointing out through the cloth | RH_Ice | body |
| 30 | **weapon_summon** glaive shaft | S | local to grip: (0,-0.55,0;0.018)->(0,0.55,0;0.014)->(0,0.72,0;0.016) silver wire wraps x6 | RH_Obsidian / RH_Silver | weapon_summon |
| 31 | **weapon_summon** glaive blade **S** | E | plane=YZ (y,z): (0.70,0)(0.82,0.05)(0.95,0.14)(1.08,0.26)(1.20,0.30)[tip](1.14,0.20)(1.02,0.08)(0.90,0.00)(0.80,-0.03) thickness x -0.020..0.020 b=0.005, inner cracks | RH_Ice | weapon_summon |
| 32 | **weapon_summon** crystal growths | C | base=(0,0.72,0) n=6 len 0.08-0.20 r 0.014-0.024 along the blade back | RH_Ice | weapon_summon |
| 33 | **weapon_summon** socket collar + butt | L / C | collar `(0.020,0.66)(0.030,0.69)(0.030,0.74)(0.020,0.76)` ; butt C n=1 len 0.08 at y -0.55 | RH_Silver / RH_Ice | weapon_summon |
(33 parts; budget <= 30k. F1 = eyes; F2 = halo glow line. Glaive blade carries its own cyan crack lines, texture only.)

## 5. Pose
Tall and still. Weight on the right foot, hips tilted 3 deg. Arms low, hands open and slightly turned out, fingers curled, gap 0.08 to the body. Head tilted 3 deg to the right, chin high. Halo floats above and behind, gap visible between skull and crescent. Hem tongues drift outward 25 deg. No weapon.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.24, 0.80, 0.12) palm (weapon_summon origin) | hand_R |
| `socket_cast` | (0, 1.38, -0.10) halo centre | top |
| `socket_impact` | (0, 0.70, 0.70) cut plane contact | body |
| `socket_head` | (0, 1.52, -0.12) halo apex | top |

Extras: `impactTime 1.30`, `strikeRange 0.70`, `attackStyle summon`, `displayName "Rime Pale Tide Queen"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 3.8 s) - ghostly sway
| t | bone | value |
|---|---|---|
| 0.0 | all | rest ; weapon_summon scale 0 |
| 1.2 | body | y +0.012 (floats) ; spine rx +1.2 |
| 1.9 | top | ry +6, rz +3 (halo drifts) ; head rz +1.5 |
| 2.6 | body | y -0.004 ; top ry -4 |
| 3.8 | all | rest |

**Move** (loop 1.0 s; steps 0.25, 0.75) - glide, hem trails
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +5, y +0.02 ; top rx -6 |
| 0.25 | body | y +0.03 (soft step) |
| 0.5 | body | rx +7, rz +2 ; top rx -10, ry +8 |
| 0.75 | body | y +0.03, rz -2 |
| 1.0 | all | = t0 |

**Attack** (2.4 s; impact 1.30)
| t | bone | value |
|---|---|---|
| 0.00-0.45 | pull from the air | weapon_summon scale 0 -> 1.15 -> 1.0 by 0.45 ; arm_R rx -75, hand_R rx -20 (reach & grip) ; spine rx -3 ; head rx -5 ; halo top ry +20 |
| 0.45-1.05 | glide wind-up (io) | body y +0.03, z -0.10, rx -6 ; spine ry -60 (turn right) ; arm_R rx -85, ry -20 ; hand_R rx -20 ; arm_L rx -40, rz +20 ; head ry +20 |
| 1.05-1.17 | hold | glaive horizontal at the right-back; head fixed on target |
| 1.17-1.30 | **sweeping strike** (0.13 s snap) | spine ry -60 -> +72 ; body ry -5 -> +15, z +0.28 ; arm_R rx -85 held ; top ry -20 (halo lags) |
| 1.30 | **impact** | cut plane at socket_impact ; frozen crescent VFX |
| 1.30-1.55 | hold | follow-through spine ry +72 -> +60 ; frost trail |
| 1.55-2.40 | recover (io) | to rest ; weapon_summon dissolves at 2.1-2.4 |

**HitReact** (0.5 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.10 | body | rx -10, z -0.07 ; spine rx -9 ; head rx -14, rz +6 ; arm_L/arm_R rx +12 ; top rx +14, ry +12 (halo jolts) |
| 0.50 | body rx -4 ; head rx -5 |

**Victory** (2.0 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.6 | arm_R | rx -60, hand_R rx -25 (palm up) ; arm_L rx -30 ; head rx -12 ; spine rx -6 ; body y +0.03 |
| 1.2 | top | ry +30, rz 0 (halo glows, engine pulse) |
| 2.0 | hold | held, mist on the floor |

## 8. Fragments (40)
Sharp: 12 long hem/gown ice shards (aspect 4:1), 8 obsidian plate shards (flat, 3-5 sides), 6 halo crescent arcs (curved thin), 4 wing crystals (whole prisms), head 3 (veil/jaw/crown), arms 4, cape splinters 3. `RH_Interior` pale cracked ice; frost mist and glitter spray; eyes flash cyan 0.2 s.

## 9. Readability
- vs `emberhold_queen`: dark slim gown vs wide bronze skirt/shoulders; halo crescent at 1.55 instead of a spiked crown; frayed tongues and a crystal wing on one shoulder; luma <= 0.15 with bright halo/veil/eyes only.
- vs other roles: highest floating shape behind a head (only role with a detached halo); long flared hem; no staff; the king has broad shoulders and a prism ring.
