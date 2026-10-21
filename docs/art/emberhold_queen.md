# emberhold_queen - Emberhold Flamecrown Warden

## 1. Identity
- **Name**: Emberhold Flamecrown Warden. **Concept**: an armoured warrior-queen in swept bronze pauldrons, a layered scale cloak and a tall forged crown of upward blades with a single ember gem. Hands empty at rest; the great hammer-staff is summoned from embers during Attack.
- **Signature shape**: the tall crown of seven upward blade-points (tallest 0.21 above the brow, top at y 1.55, ~15% oversize) and the swept-back winged pauldrons. Silhouette = A-line flared skirt-armour, a pinched waist, wide swept shoulders, and a spiked crown on a small head.
- **Idle**: no weapon visible (`weapon_summon` scale 0).

## 2. Dimensions (total 1.55)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Boots (greaves) | 0.22-0.42 | peek under hem |
| Skirt-armour (A-line) | 0.30-0.85 | hem r 0.27 -> waist r 0.115 |
| Waist (pinch) | 0.80-0.90 | r 0.105 |
| Torso + breastplate | 0.88-1.14 | shoulder width 0.46 |
| Pauldrons | 1.06-1.26 | span x +-0.31 |
| Neck | 1.14-1.22 | |
| Head | 1.22-1.39 | head 0.17 (figure 1.20 -> 7.0 heads) |
| Crown | 1.34-1.55 | band 1.34-1.39, blades to 1.55 |
| Cloak (behind) | 0.30-1.20 | z -0.12..-0.32 |
Envelope: 0.62 wide (pauldrons) x 0.50 deep (cloak flare z -0.28..0.22).

## 3. Bone pivots (x, y, z)
root (0,0,0) | body (0,0.78,0) | spine (0,0.90,0) | head (0,1.19,0.01) | top (0,1.17,-0.10) (cloak, braid) | arm_L (0.20,1.12,0) | hand_L (0.24,0.92,0.04) | arm_R (-0.20,1.12,0) | hand_R (-0.25,0.92,0.04) | node `weapon_summon` = child of hand_R at (-0.25,0.80,0.12) (grip), scale 0 in all clips except Attack.

## 4. Part list
Pedestal parts per README section 2.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | boot + greave M | S | (0.07,0.25,0.08;0.040)->(0.075,0.34,0.06;0.036)->(0.08,0.43,0.05;0.045) + toe B s=(0.08,0.05,0.14) | EH_Bronze / EH_Leather | body |
| 2 | skirt under-layer | L | sides=24, `(0.000,0.30)(0.255,0.30)(0.248,0.45)(0.205,0.62)(0.150,0.76)(0.115,0.86)(0.000,0.86)` | EH_Cloth | body |
| 3 | skirt lames row 1 (hem) x12 | E | each (-0.075,0)(0.075,0)(0.070,0.17)(0,0.20)(-0.070,0.17) curved r 0.27 @0..0.012 b=0.006, at y 0.28-0.48, k*30 deg | EH_Bronze | body |
| 4 | skirt lames row 2 x12 | E | same scaled 0.85 at y 0.44-0.62, offset 15 deg, r 0.225 | EH_Bronze | body |
| 5 | skirt lames row 3 x10 | E | scaled 0.70 at y 0.60-0.76, r 0.17, offset 0 | EH_Bronze | body |
| 6 | front split tabard | E | (-0.05,0.86)(0.05,0.86)(0.062,0.28)(0,0.22)(-0.062,0.28) @0.255..0.263 `~soft` (spine/body), embroidery lines | EH_Cloth (#7A2820) | body |
| 7 | belt + faulds | L / B | belt `(0.108,0.82)(0.118,0.826)(0.118,0.866)(0.108,0.872)` ; 7 fauld plates B s=(0.06,0.08,0.012) at y 0.78 | EH_Leather / EH_Bronze | body |
| 8 | belt medallion (anvil) | E | disc Ø0.06 @0.118..0.130 at (0,0.846) | EH_Bronze | body |
| 9 | torso gambeson | S | (0,0.84,0;0.105*0.075)->(0,0.97,0;0.120*0.085)->(0,1.10,0;0.140*0.088) waist pinch | EH_Cloth | spine |
| 10 | breastplate **S** | E | (-0.115,0.90)(0.115,0.90)(0.145,1.02)(0.130,1.12)(0.0,1.14)(-0.130,1.12)(-0.145,1.02) @0.074..0.098 b=0.012, central ridge, bust relief +noise 0.004 | EH_Bronze | spine |
| 11 | breastplate filigree | S | 6 spiral arcs on the plate r 0.004, forming a flame rosette Ø0.10 | EH_Steel (blackened) | spine |
| 12 | lame band x3 (waist) | B | y 0.90/0.93/0.96 s=(0.20,0.026,0.026) rd=0.01 e=4 | EH_Bronze | spine |
| 13 | backplate | E | (-0.12,0.90)(0.12,0.90)(0.14,1.04)(0.12,1.12)(-0.12,1.12) @-0.100..-0.078 b=0.010 | EH_Bronze | spine |
| 14 | gorget (neck ring) | L | `(0.060,1.13)(0.076,1.14)(0.082,1.17)(0.066,1.19)(0.052,1.19)` | EH_Bronze | spine |
| 15 | neck | S | (0,1.14,0;0.040)->(0,1.21,0.01;0.034) | EH_Leather (skin) | head |
| 16 | pauldron L (swept wing) **S** | E x3 | lames in plane tilted rz 25: L1 (0,0)(0.12,0.03)(0.19,0.10)(0.17,0.14)(0.04,0.08)@-0.05..0.07 ; L2 scaled 0.85 offset (0.01,-0.03) ; L3 scaled 0.7 offset (0.02,-0.06) ; rear tip sweeps back to z -0.06 ; b=0.008 ; centred (0.20,1.14) | EH_Bronze | arm_L |
| 17 | pauldron R (taller, spiked; asymmetric) **S** | E x3 + C | mirrored lames, +6% scale, plus 3 bronze spikes len 0.06-0.09 on the top lame | EH_Bronze | arm_R |
| 18 | upper arm M | S | (+-0.20,1.12,0;0.048)->(+-0.23,0.98,0.02;0.040)->(+-0.24,0.93,0.04;0.036) with rerebrace sleeve (r+0.006) | EH_Cloth / EH_Bronze | arm |
| 19 | forearm + vambrace M | S | (+-0.24,0.93,0.04;0.036)->(+-0.25,0.86,0.12;0.030)->(+-0.25,0.80,0.18;0.026) | EH_Bronze | hand |
| 20 | vambrace fins M | E | plane=YZ (y,z): (0.88,0.08)(0.84,0.16)(0.86,0.19)(0.90,0.12) thickness 0.012 | EH_Bronze | hand |
| 21 | hands M | B + S | gauntlet mitten s=(0.045,0.04,0.055) ; fingers 4 x r 0.007 ; R hand open slightly, L fist | EH_Leather / EH_Bronze | hand |
| 22 | head | B | c=(0,1.305,0.01) s=(0.115,0.17,0.12) e=2.3 | EH_Leather (skin) | head |
| 23 | eyes | B | s=(0.016,0.008,0.008) at (+-0.030,1.31,0.066) | EH_Ember x2 | head |
| 24 | cheek + nose guard | E | nasal (0.007 wide) (-0.007,1.26)(0.007,1.26)(0.005,1.33)(-0.005,1.33)@0.056..0.064 ; cheek M | EH_Bronze | head |
| 25 | crown band **S** | L | sides=24, `(0.082,1.335)(0.092,1.34)(0.092,1.385)(0.084,1.39)(0.080,1.385)(0.080,1.34)` | EH_Bronze | head |
| 26 | crown blades x7 **S** | E | each: base width 0.030, bevel b 0.004, tapered to a point; angles 0, +-37, +-77, +-120 deg around Z axis of head; heights (above y 1.39): 0.16 (front centre) ; 0.15 x2 ; 0.12 x2 ; 0.10 x2 ; tilted out 6 deg ; the front-centre tip y 1.55. Total 7 | EH_Bronze | head |
| 27 | crown inner cross-straps | S | 2 arcs over the head r 0.005 at y 1.39 | EH_Steel | head |
| 28 | crown gem **F1** | B | c=(0,1.362,0.094) s=(0.032,0.040,0.020) e=2.4 facets | EH_Ember x8 | head |
| 29 | gem bezel | S | torus ring r 0.021 tube 0.005 | EH_Bronze | head |
| 30 | braided hair | S | (0,1.36,-0.09;0.036)->(0,1.20,-0.14;0.030)->(0.03,1.02,-0.16;0.022)->(0.0,0.88,-0.14;0.014) + 6 braid segments (twist noise 0.006) ; 3 bronze rings | EH_Fur (dark) / EH_Bronze | top |
| 31 | cloak yoke | S | closed ring r 0.15 at y 1.16 tube 0.030, fur-trimmed | EH_Fur | spine |
| 32 | cloak backing | E | (-0.15,1.15)(0.15,1.15)(0.26,0.60)(0.26,0.30)(0,0.26)(-0.26,0.30)(-0.26,0.60) @-0.130..-0.124 `~soft` (spine/top) , asymmetric: hem cut at left by 0.06 | EH_Cloth | top |
| 33 | cloak scales row 1-10 (k=0..9) | B array | row y = 1.12 - 0.075k ; row z = -0.136 - 0.014k ; width 0.28 + 0.03k ; per row n = 6+k scales each s=(width/n*1.15, 0.082, 0.008) rd=0.003, rot rx=-6-k*0.6 , 30% overlap , per-scale bevel ; half-staggered | EH_Bronze (alternate rows EH_Steel in 1 of 4) | top (~soft) |
| 34 | scale ember seams | texture | 3% of scales get a rim ember | EH_Ember x3 | top |
| 35 | shoulder brooches M | L | Ø0.03 discs at the cloak yoke fronts | EH_Bronze | spine |
| 36 | **weapon_summon** hammer-staff shaft | S | local to grip: (0,-0.30,0;0.020)->(0,0.55,0;0.017)->(0,0.72,0;0.019), sec=10, leather wraps x4 | EH_Steel / EH_Leather | weapon_summon |
| 37 | **weapon_summon** hammer head **S** | B | c=(0,0.82,0) s=(0.34,0.18,0.18) rd=0.020 e=6 ; cheek plates E 0.15x0.15 each side; back spike C n=1 len 0.12 on -X ; ember cracks seams | EH_Bronze / EH_Stone | weapon_summon |
| 38 | **weapon_summon** collar + rings | L | `(0.026,0.70)(0.034,0.72)(0.034,0.74)(0.026,0.76)` ; pommel B r 0.03 at y -0.31 | EH_Bronze | weapon_summon |
| 39 | **weapon_summon** ember core **F2 (attack only)** | B | s=(0.08,0.05,0.05) inside the hammer face, 3 lines | EH_Ember x8 | weapon_summon |
(39 parts; budget <= 30k + weapon 1K texture. F1 = crown gem; F2 only exists while the weapon is summoned.)

## 5. Pose
Weight on the left leg, hips tilted 3 deg, shoulders counter-tilted -2 deg, chin raised 3 deg. Arms hang slightly away from the body (gap 0.08), hands open at the sides. Cloak settled, no weapon. The summon grip point is the open right hand.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.25, 0.80, 0.12) right palm (weapon_summon origin) | hand_R |
| `socket_cast` | (0, 0.90, 0.30) summon spiral target | body |
| `socket_impact` | (0, 0.30, 0.70) hammer head contact | body |
| `socket_head` | (0, 1.50, 0) | head |

Extras: `impactTime 1.30`, `strikeRange 0.70`, `attackStyle summon`, `displayName "Emberhold Flamecrown Warden"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 3.6 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest ; weapon_summon scale 0 |
| 1.2 | spine | rx +1.4 ; head rx -1, ry +1.5 |
| 1.8 | top | rx +3 (cloak settles) |
| 2.4 | arm_R | rx -1.5 ; hand_R rx -3 (fingers flex) |
| 3.6 | all | rest |

**Move** (loop 1.0 s; steps 0.25, 0.75) - stately glide
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +4 ; top rx +6 |
| 0.25 | body | y +0.02 (step), rz +2 ; arm_R rx +6, arm_L rx -6 |
| 0.5 | body | rx +6 ; top rx -8 |
| 0.75 | body | y +0.02 (step), rz -2 ; arm_R rx -6, arm_L rx +6 |
| 1.0 | all | = t0 |

**Attack** (2.4 s; impact 1.30)
| t | bone | value |
|---|---|---|
| 0.00-0.40 | summon | weapon_summon scale 0 -> 1.15 (0.30) -> 1.0 (0.40), embers spiral (engine) ; arm_R rx -35, hand_R rx -20 (reaching up to the grip) ; arm_L rx -20 ; spine rx -4 ; head rx -6 |
| 0.40-1.00 | advance & spin (io) | body ry 0 -> -360 (lin, 0.55 s), y +0.02 ; arm_R rx -110 / hand_R rx -35 ; arm_L rx -95, rz +20 (left hand takes the lower grip) ; top rx -15 (cloak whips) |
| 1.00-1.17 | overhead hold | arm_R rx -165, hand_R rx -30 ; arm_L rx -150 ; spine rx -10 ; body rx -6 ; head rx -8 ; weapon head above 1.7 |
| 1.17-1.30 | **strike** (0.13 s snap) | arm_R rx -165 -> -40 ; arm_L rx -150 -> -45 ; hand_R rx -30 -> -10 ; body rx +20, z +0.25 ; spine rx +18 ; top rx +25 |
| 1.30 | **impact** | hammer head on socket_impact ; shockwave (engine) |
| 1.30-1.55 | hold | body y -0.03 (squash), z +0.25 held |
| 1.55-2.40 | recover (io) | to rest ; weapon_summon scale 1 -> 0 over 2.1-2.4 (engine dissolve) |

**HitReact** (0.5 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.10 | body | rx -11, z -0.07 ; spine rx -9 ; head rx -14 ; arm_L rx +12, arm_R rx +12 ; top rx +16 |
| 0.50 | body rx -4 ; spine rx -3 ; head rx -5 |

**Victory** (2.0 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest (weapon_summon scale 0) |
| 0.5 | arm_R | rx -150, hand_R rx -20 (fist raised) ; head rx -10 ; spine rx -6 |
| 1.0 | top | rx +10 ; body y +0.015 |
| 2.0 | hold | fist raised, head up |

## 8. Fragments (40)
Coarse: 8 skirt-armour slabs, 6 cloak scale clusters (6 scales each), 2 pauldron wings (whole), 4 breastplate chunks, crown 3 (band + 2 blade groups; gem stays an ember lump), head 3, arms 6, braid 2, boots 4, pedestal-edge rubble 2. Chunky bronze and stone with `EH_Interior` ember cores; blades keep their points.

## 9. Readability
- vs `rime_queen`: wide swept shoulders + spiked crown + scale cloak, mid-value bronze; Rime is slim, dark, with a floating crescent and frayed hem. Perimeter/sqrt(area) ~ 4.
- vs other roles: crown (tip 1.55) on a small head + flared A-line skirt; waist pinch; empty hands. The king is wider/heavier with a vertical sword; the bishop is a cone with a staff.
