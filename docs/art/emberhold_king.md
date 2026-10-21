# emberhold_king - Emberhold Ember Sovereign

## 1. Identity
- **Name**: Emberhold Ember Sovereign. **Concept**: an older, broad-shouldered highland king in battle-worn bronze plate under a heavy fur mantle, a plain thick crown with six squat points and ember gems, a great leaf-bladed greatsword planted point-down before him, both gauntleted hands on the pommel.
- **Signature shape**: the vertical greatsword (blade width 0.14, ~15% oversize) in front of the body and the heavy crown (band 0.10 thick, six squat points, finial gems; top 1.70). Silhouette = the widest, heaviest piece: massive pauldrons, fur mantle, central vertical blade, crown with a flat-topped rim of six knobs.

## 2. Dimensions (total 1.70)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Boots + greaves | 0.22-0.56 | stance +-0.13 |
| Thighs / hip | 0.52-0.80 | |
| Tabard + belt | 0.50-0.92 | tabard to y 0.50 |
| Torso | 0.90-1.28 | chest depth 0.20 |
| Pauldrons + mantle | 1.22-1.42 | span x +-0.37 |
| Neck | 1.28-1.36 | |
| Head | 1.35-1.54 | head 0.19 (figure 1.32 -> 6.95 heads) |
| Crown | 1.46-1.70 | band 1.46-1.56, points 1.56-1.66, finial gems 1.70 |
| Greatsword | 0.222-1.30 | tip on plinth, pommel top 1.30 |
| Cloak (behind) | 0.34-1.30 | z -0.12..-0.30 |
Envelope: 0.74 wide x 0.56 deep (z -0.30..0.26).

## 3. Bone pivots (x, y, z)
root (0,0,0) | body (0,0.76,0) | spine (0,0.90,0) | head (0,1.33,0.01) | top (0,1.30,-0.12) (cloak) | arm_L (0.31,1.30,0) | hand_L (0.30,1.05,0.05) | arm_R (-0.31,1.30,0) | hand_R (-0.30,1.05,0.05)

## 4. Part list
Pedestal parts per README section 2.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | boot M | B | c=(0.13,0.255,0.04) s=(0.12,0.07,0.22) rd=0.025 e=3.5 ; toe plate B s=(0.10,0.04,0.06) | EH_Leather / EH_Bronze | body |
| 2 | greave M | S | (0.13,0.28,0.05;0.050)->(0.135,0.40,0.06;0.058)->(0.14,0.50,0.05;0.064) sec=10 `+noise 0.003` | EH_Bronze | body |
| 3 | knee cop M | B | c=(0.14,0.545,0.075) s=(0.11,0.09,0.06) rd=0.02 e=3 + side fin E | EH_Bronze | body |
| 4 | thigh M | S | (0.14,0.54,0.04;0.066)->(0.13,0.68,0.02;0.080)->(0.115,0.80,0;0.086) | EH_Bronze (cuisse) | body |
| 5 | pelvis + tabard | L | sides=20, `(0.108,0.92)(0.150,0.78)(0.185,0.62)(0.200,0.50)(0.196,0.48)` skirt, front split | EH_Cloth | body |
| 6 | tasset plates x8 | B | ring r 0.17 at y 0.72, s=(0.08,0.12,0.014) rd=0.01 e=4 , overlap 25%, rot rx -10 | EH_Bronze | body |
| 7 | belt | L | `(0.150,0.88)(0.160,0.885)(0.160,0.925)(0.150,0.93)` | EH_Leather | body |
| 8 | buckle (anvil, large) | E | 0.08 x 0.06 @0.160..0.178 b=0.008 | EH_Bronze | body |
| 9 | torso | S | (0,0.92,0;0.14*0.10)->(0,1.08,0;0.170*0.115)->(0,1.24,0;0.200*0.115) (barrel chest) | EH_Cloth | spine |
| 10 | breastplate (dented) **S** | E | (-0.17,0.96)(0.17,0.96)(0.205,1.12)(0.19,1.27)(0,1.30)(-0.19,1.27)(-0.205,1.12) @0.100..0.130 b=0.014, ridge, dents (3, amp 0.008) | EH_Bronze | spine |
| 11 | plackart + lame bands x4 | B | y 0.94/0.98/1.02/1.06 s=(0.30,0.034,0.030) rd=0.012 e=4 z=0.12 | EH_Bronze | spine |
| 12 | chest crest relief (anvil) | E | 0.09 x 0.07 raised 0.006 | EH_Steel | spine |
| 13 | backplate | E | (-0.17,0.96)(0.17,0.96)(0.20,1.12)(0.18,1.27)(-0.18,1.27) @-0.130..-0.100 b=0.012 | EH_Bronze | spine |
| 14 | fur mantle (heavy) **S** | S | closed ring r 0.20 at y 1.30 tube 0.060 `+noise 0.014` + extra clumps on left 0.07 | EH_Fur | spine |
| 15 | fur mantle drape (back) | E | (-0.20,1.28)(0.20,1.28)(0.27,1.00)(-0.24,0.98) @-0.14..-0.11 `~soft` clumpy edge | EH_Fur | top |
| 16 | gorget | L | `(0.085,1.30)(0.100,1.31)(0.104,1.35)(0.090,1.37)(0.072,1.37)` | EH_Bronze | spine |
| 17 | pauldron L (massive) **S** | E x4 + B | lames L1 (0,0)(0.16,0.04)(0.24,0.12)(0.21,0.17)(0.05,0.10)@-0.08..0.10 centred (0.30,1.32) ; L2..L4 scaled 0.88/0.76/0.64 stepping down 0.04 ; top dome B s=(0.15,0.07,0.17) e=2.5 | EH_Bronze | arm_L |
| 18 | pauldron R (more dented, with a spike; asymmetric) **S** | E x4 + B | as L but 0.94 scale, one lame cracked, 1 bronze spike C len 0.07 | EH_Bronze | arm_R |
| 19 | upper arm M | S | (+-0.31,1.30,0;0.060)->(+-0.31,1.16,0.02;0.050)->(+-0.30,1.05,0.05;0.045) + rerebrace B sleeve | EH_Cloth / EH_Bronze | arm |
| 20 | elbow cop M | B | c=(+-0.31,1.05,0.04) s=(0.07,0.07,0.07) e=2.4 + fin | EH_Bronze | hand |
| 21 | forearm + vambrace M | S | (+-0.30,1.05,0.05;0.045)->(+-0.19,1.12,0.16;0.040)->(+-0.09,1.16,0.23;0.034) | EH_Bronze | hand |
| 22 | gauntlet hand M | B + S | gauntlet block s=(0.065,0.055,0.070) rd=0.012 e=4 ; finger plates x4 S r 0.010 ; at (-0.08,1.18,0.24) and (-0.08,1.27,0.24) (L on top) | EH_Bronze / EH_Leather | hand_L/hand_R |
| 23 | gauntlet rings x4 | S | torus r 0.014 tube 0.004 on fingers, 2 per hand, (one gold-coloured: bronze bright) | EH_Bronze | hand |
| 24 | neck | S | (0,1.30,0;0.060)->(0,1.37,0.01;0.055) | EH_Leather (skin) | head |
| 25 | head | B | c=(0,1.445,0.01) s=(0.135,0.19,0.145) e=2.3 | EH_Leather (skin) | head |
| 26 | beard + moustache | S | grey-brown clumps: (0,1.38,0.07)->(0,1.28,0.10;0.04->0.015) x5 side clumps | EH_Fur (grey) | head |
| 27 | brow + cheek lines | texture / E | brow ridge B s=(0.13,0.016,0.04) at y 1.47 ; scar groove 0.004 | EH_Leather | head |
| 28 | eyes | B | s=(0.016,0.008,0.008) at (+-0.034,1.455,0.075), dim ember | EH_Ember x2 | head |
| 29 | crown band **S** | L | sides=24, `(0.095,1.455)(0.108,1.46)(0.108,1.55)(0.100,1.56)(0.095,1.555)(0.095,1.46)` ; engraved ring grooves x2 | EH_Bronze | head |
| 30 | crown points x6 **S** | E | each squat trapezoid (-0.036,0)(0.036,0)(0.024,0.09)(-0.024,0.09) b=0.008, standing on the band at y 1.555, angles k*60 deg, r=0.101, tilt out 4 deg ; top y 1.645 | EH_Bronze | head |
| 31 | crown finial gems x6 **F1** | B | c at the point tops, y 1.665, r 0.020 (superellipsoid e=2.2) ; front-centre gem larger r 0.026 ; top y 1.70 | EH_Ember x8 | head |
| 32 | crown cross-braces | S | 2 arcs over the head r 0.006 at y 1.56 | EH_Steel | head |
| 33 | band gems x3 | B | in the band: c=(0,1.505,0.108) s=(0.024,0.030,0.012) and (+-0.075,1.505,0.078) | EH_Ember x4 | head |
| 34 | cloak backing | E | (-0.22,1.28)(0.22,1.28)(0.30,0.80)(0.26,0.36)(0,0.32)(-0.26,0.36)(-0.30,0.80) @-0.30..-0.12 curved, `~soft` (spine/top), left hem torn | EH_Cloth | top |
| 35 | cloak fur trim | S | along front edges tube 0.025 | EH_Fur | top |
| 36 | sword blade (leaf) **S** | E | (-0.08,0.222)(-0.135,0.40)(-0.145,0.60)(-0.14,0.80)(-0.13,0.88)(0.01,0.88)(0.015,0.80)(0.01,0.60)(0.00,0.40) @0.230..0.250 b=0.006 ; centre fuller groove (0.03 wide, depth 0.006) to y 0.78 ; nicks x4 | EH_Steel | hand_R |
| 37 | sword fuller ember line **F2 (subtle)** | S | (-0.065,0.30,0.25)->(-0.065,0.76,0.25) tube 0.004 | EH_Ember x2 | hand_R |
| 38 | crossguard | E | (-0.23,0.88)(0.07,0.88)(0.09,0.915)(0.07,0.945)(-0.23,0.945)(-0.25,0.915) @0.220..0.260 b=0.008, with downturned tips | EH_Bronze | hand_R |
| 39 | grip + wraps | S | (-0.08,0.945,0.24;0.016)->(-0.08,1.20,0.24;0.016) leather wraps x6 | EH_Leather | hand_R |
| 40 | pommel disc | L | axis=Z c=(-0.08,1.265,0.24) `(0.000,0.020)(0.040,0.020)(0.044,0.000)(0.040,-0.020)(0.000,-0.020)` | EH_Bronze | hand_R |
(40 parts; budget <= 30k. F1 = crown gems; F2 = blade fuller ember, dim.)

## 5. Pose
Immovable. Feet wide (stance 0.26), weight even; chest out; head level, chin 2 deg down; the greatsword planted point-down 0.24 in front of the right-centre body, both gauntlets stacked on the pommel (right below), elbows out 20 deg. Cloak hangs straight. The crown is level.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.08, 0.222, 0.24) blade tip (grip is at y 1.0-1.25) | hand_R |
| `socket_cast` | (0, 0.90, 0.30) | body |
| `socket_impact` | (-0.02, 0.70, 0.60) cleave contact | body |
| `socket_head` | (0, 1.64, 0) crown centre | head |

Extras: `impactTime 1.20`, `strikeRange 0.60`, `attackStyle melee`, `displayName "Emberhold Ember Sovereign"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 4.0 s) - heavy breathing
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 1.4 | spine | rx +1.2 ; head rx -0.8 |
| 1.4 | arm_L/arm_R | rx -1 (shoulders lift) ; body y +0.004 |
| 2.8 | head | ry -2 ; top rx +2 (cloak) |
| 4.0 | all | rest |

**Move** (loop 1.0 s; speed 1.4; steps 0.25, 0.75) - heavy march
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +5, y 0 ; spine rx +2 |
| 0.25 | body | y +0.02 (step), rz +3 ; head rz -2 |
| 0.5 | body | rx +5 ; top rx -6 |
| 0.75 | body | y +0.02 (step), rz -3 ; head rz +2 |
| 1.0 | all | = t0 |

**Attack** (2.3 s; impact 1.20; engine slows time at impact)
| t | bone | value |
|---|---|---|
| 0.00-0.30 | hands grip | body rx +2 ; head rx +4 (looks at the target) |
| 0.30-0.95 | lift the sword (io) | arm_R rx -40 -> -120, hand_R rx -20 -> -45 ; arm_L rx -40 -> -118, hand_L rx -20 -> -42 ; spine rx -4 -> -12 ; body rx -4, y +0.02 ; blade swings up-forward (tip off the plinth) ; head rx -4 ; top rx +6 |
| 0.95-1.07 | overhead hold | arm_R rx -150, hand_R rx -45 ; arm_L rx -145 ; body rx -8 ; spine rx -14 ; sword vertical overhead |
| 1.07-1.20 | **strike** (0.13 s snap) | arm_R rx -150 -> -45 ; arm_L rx -145 -> -42 ; hand_R rx -45 -> -15 ; spine rx -14 -> +20 ; body rx +16, z +0.26 ; head rx +8 ; top rx +22 |
| 1.20 | **impact** | tip/edge at socket_impact ; time slows 0.2 for 0.8 s (engine) |
| 1.20-1.50 | hold | squash body y -0.035 ; cloak top rx +30 |
| 1.50-2.30 | recover (io) | sword returns to plant pose |

**HitReact** (0.5 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.10 | body | rx -8, z -0.06 ; spine rx -8 ; head rx -12 ; top rx +16 ; arm_R/arm_L rx +8 (resists the shove) |
| 0.50 | body rx -3 ; spine rx -3 ; head rx -4 |

**Victory** (2.0 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.7 | arm_R | rx -150, hand_R rx -35 (sword raised overhead, bk) ; arm_L rx -150 ; spine rx -10 ; head rx -10 ; body y +0.02 |
| 2.0 | hold | held |

## 8. Fragments (40)
Coarse: crown 4 (band 2 + 2 point groups; gems as glowing lumps), breastplate 6, backplate 3, pauldrons 4 (each lame group whole), mantle 3 (fur-stone), greatsword 3 (blade 2, guard+hilt 1), legs/greaves 8, tabard/tasset 6, arms 3. Chunky bronze/stone with `EH_Interior` ember core and spark showers; the pedestal is not fractured.

## 9. Readability
- vs `rime_king`: the widest solid mass (0.74) with a vertical blade and a flat ring of six squat crown points; warm mid-value. Rime has a hovering prism ring and a spiked back ridge on a dark mass, with empty hands.
- vs other roles: tallest piece (1.70), crown + central vertical sword. The queen is slim with a flared skirt and tall blade crown; the bishop is a cone.
