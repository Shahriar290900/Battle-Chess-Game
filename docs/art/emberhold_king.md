# emberhold_king - Emberhold Ember Sovereign

## 1. Identity
- **Name**: Emberhold Ember Sovereign. **Concept**: an older, broad-shouldered highland king in battle-worn bronze plate under a heavy fur mantle, wearing a tall **closed crown** (band, four fleurons, two crossing arches, orb) topped by a bronze **cross-pattee with an ember gem**; a great leaf-bladed greatsword planted point-down before him, both gauntleted hands on the pommel.
- **Identity cue (the only cross in the set)**: the cross-pattee finial. Crown stack y 1.41 -> 1.70 (0.29 tall, 0.216 wide = 1.6x head width, +20% over the previous crown); cross 0.10 wide x 0.11 tall, bar thickness 0.040 (pattee ends 0.056), ember gem on its face. It is the highest point of any piece. Secondary cues: widest body (0.74), vertical blade, closed dome of arches.
- **Never confusable with the queen**: closed (arches + orb + cross) with four fleurons and a bronze/oxblood dome, versus her open ring of nine tines with no arches and no cross.
- **60 px read**: at 1 px = 0.028 the crown+cross is ~10 px tall and the cross ~4 px wide: the cross arm must stay a clear plus sign against the dark backdrop (value of cross >= 0.55 luma).

## 2. Dimensions (total 1.70)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Boots + greaves | 0.22-0.56 | stance +-0.13 |
| Thighs / hip | 0.52-0.80 | |
| Tabard + belt | 0.50-0.92 | tabard to y 0.50 |
| Torso | 0.90-1.28 | chest depth 0.20 |
| Pauldrons + mantle | 1.22-1.42 | span x +-0.37 |
| Neck (short, sunk in the mantle) | 1.24-1.30 | |
| Head | 1.28-1.46 | head 0.18 (figure 1.24 -> 6.9 heads) |
| Crown band | 1.41-1.50 | r 0.098 -> 0.110 (overhangs the head by 0.04 each side) |
| Fleurons x4 | 1.50-1.555 | |
| Arches x2 + velvet cap | 1.50-1.565 | apex 1.565 |
| Orb | 1.556-1.608 | r 0.026 |
| Cross-pattee | 1.600-1.700 | arm span 0.100, centre y 1.668 |
| Greatsword | 0.222-1.30 | tip on plinth, pommel top 1.30 |
| Cloak (behind) | 0.34-1.30 | z -0.12..-0.30 |
Envelope: 0.74 wide x 0.56 deep (z -0.30..0.26). Crown never wider than 0.22.

## 3. Rig (humanoid template) and bone pivots
`humanoid_rig(J, weapon=(-0.08,0.70,0.24), cape=[(0,1.10,-0.20),(0,0.80,-0.24),(0,0.50,-0.26)])`; weapon parent `wrist_R`. Absolute rest joints (L side; R mirrored except where given), units as README section 0:

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`body`) | (0,0.76,0) | | elbow_L | (0.30,1.06,0.05) |
| spine | (0,0.90,0) | | wrist_L | (0.07,1.25,0.24) |
| chest | (0,1.08,0) | | wrist_R (explicit) | (-0.08,1.17,0.24) |
| neck | (0,1.24,0.005) | | hip_L | (0.11,0.78,0) |
| head (skull base) | (0,1.30,0.01) | | knee_L | (0.14,0.54,0.05) |
| top (cloak root) | (0,1.30,-0.12) | | ankle_L | (0.13,0.27,0.04) |
| clavicle_L | (0.09,1.27,0) | | toe_L | (0.13,0.245,0.15) |
| shoulder_L | (0.31,1.30,0) | | weapon (sword centre) | (-0.08,0.70,0.24) |

Bones: `root, body, spine, chest, neck, head, top, clavicle_L/R, arm_L/R` (upper arm, pivot at the shoulder), `hand_L/R` (= FOREARM, pivot at the elbow; alias forearm), `wrist_L/R` (the hand; alias fist), `thigh_*, shin_*, foot_*, toe_*, weapon, cape_1..3`.

**Binding (authoritative; the Bone column of section 4 keeps the legacy names)**: parts 5-8 -> `body` (tasset plates `~soft` thigh); 9, 11 -> `spine`; 10, 12-14, 16 -> `chest`; 24 -> `neck`; 25-33, 41, 42 -> `head`; 17/18 -> `arm_L/arm_R` (lames L2-L4 `~soft` 25% `clavicle`); 19 -> `arm`; 20, 21 -> `hand_L/R` (forearm); 22, 23 -> `wrist_L/R`; 1 -> `foot`; 2, 3 -> `shin` (knee cop 50% `thigh`); 4 -> `thigh`; 15, 34, 35 -> `top` `~soft` `cape_1..3` (3-link falloff); 36-40 -> `weapon`.

## 4. Part list
Pedestal parts per README section 2.
**Part numbers are stable ids; gaps = removed parts.** The Bone column uses legacy names; the binding table in section 3 is authoritative (new rig template).

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
| 16 | gorget | L | `(0.085,1.27)(0.100,1.28)(0.104,1.32)(0.090,1.34)(0.072,1.34)` (lowered 0.03: head sinks into the mantle) | EH_Bronze | chest |
| 17 | pauldron L (massive) **S** | E x4 + B | lames L1 (0,0)(0.16,0.04)(0.24,0.12)(0.21,0.17)(0.05,0.10)@-0.08..0.10 centred (0.30,1.32) ; L2..L4 scaled 0.88/0.76/0.64 stepping down 0.04 ; top dome B s=(0.15,0.07,0.17) e=2.5 | EH_Bronze | arm_L |
| 18 | pauldron R (more dented, with a spike; asymmetric) **S** | E x4 + B | as L but 0.94 scale, one lame cracked, 1 bronze spike C len 0.07 | EH_Bronze | arm_R |
| 19 | upper arm M | S | (+-0.31,1.30,0;0.060)->(+-0.31,1.16,0.02;0.050)->(+-0.30,1.05,0.05;0.045) + rerebrace B sleeve | EH_Cloth / EH_Bronze | arm |
| 20 | elbow cop M | B | c=(+-0.31,1.05,0.04) s=(0.07,0.07,0.07) e=2.4 + fin | EH_Bronze | hand |
| 21 | forearm + vambrace M | S | (+-0.30,1.05,0.05;0.045)->(+-0.19,1.12,0.16;0.040)->(+-0.09,1.16,0.23;0.034) | EH_Bronze | hand |
| 22 | gauntlet hand M | B + S | gauntlet block s=(0.065,0.055,0.070) rd=0.012 e=4 ; finger plates x4 S r 0.010 ; at (-0.08,1.18,0.24) and (-0.08,1.27,0.24) (L on top) | EH_Bronze / EH_Leather | hand_L/hand_R |
| 23 | gauntlet rings x4 | S | torus r 0.014 tube 0.004 on fingers, 2 per hand, (one gold-coloured: bronze bright) | EH_Bronze | hand |
| 24 | neck | S | (0,1.24,0;0.060)->(0,1.30,0.01;0.056) | EH_Leather (skin) | neck |
| 25 | head | B | c=(0,1.37,0.01) s=(0.135,0.18,0.145) e=2.3 | EH_Leather (skin) | head |
| 26 | beard + moustache | S | grey-brown clumps: (0,1.33,0.07)->(0,1.24,0.10;0.04->0.015) x5 side clumps | EH_Fur (grey) | head |
| 27 | brow + cheek lines | texture / E | brow ridge B s=(0.13,0.016,0.04) at y 1.40 ; scar groove 0.004 | EH_Leather | head |
| 28 | eyes | B | s=(0.016,0.008,0.008) at (+-0.034,1.385,0.075), dim ember | EH_Ember x2 | head |
| 29 | crown band **S** | L | sides=24, `(0.092,1.410)(0.098,1.412)(0.108,1.420)(0.110,1.490)(0.106,1.500)(0.098,1.498)(0.092,1.490)` ; engraved ring grooves x2 ; 16 rivet domes r 0.008 at y 1.455 | EH_Bronze | head |
| 30 | crown fleurons x4 **S** | E | each pointed fleuron (-0.030,0)(0.030,0)(0.024,0.030)(0.012,0.040)(0,0.055)(-0.012,0.040)(-0.024,0.030) thickness 0.016 b=0.004, standing on the band at y 1.50, angles 45+k*90 deg, r 0.104, tilt out 6 deg ; top 1.555 | EH_Bronze | head |
| 31 | **cross-pattee finial S F1** | E x2 + B | vertical bar (-0.020..0.020 wide, flaring to +-0.028 at the ends) y 1.600-1.700, thickness z 0.030 ; horizontal arm y 1.650-1.686 (centre 1.668), x +-0.050 flaring to 0.034 tall at the ends ; b 0.006, polished bevel ; ember gem B c=(0,1.668,0.022) s=(0.026,0.026,0.012) e=2.4 in a bezel torus r 0.016 tube 0.004 ; top y 1.700 | EH_Bronze / EH_Ember x8 | head |
| 32 | crown arches x2 **S** | S | two crossing arches (XY and ZY planes), elliptical tube 0.020 x 0.014 : (+-0.100,1.50,0)->(+-0.070,1.540,0)->(0,1.565,0) ; foot bosses B r 0.016 at the four band points 0/90/180/270 deg | EH_Bronze | head |
| 33 | band gems x3 | B | c=(0,1.455,0.108) s=(0.024,0.030,0.012) and (+-0.075,1.455,0.078) | EH_Ember x3 (dim) | head |
| 34 | cloak backing | E | (-0.22,1.28)(0.22,1.28)(0.30,0.80)(0.26,0.36)(0,0.32)(-0.26,0.36)(-0.30,0.80) @-0.30..-0.12 curved, `~soft` (spine/top), left hem torn | EH_Cloth | top |
| 35 | cloak fur trim | S | along front edges tube 0.025 | EH_Fur | top |
| 36 | sword blade (leaf) **S** | E | (-0.08,0.222)(-0.135,0.40)(-0.145,0.60)(-0.14,0.80)(-0.13,0.88)(0.01,0.88)(0.015,0.80)(0.01,0.60)(0.00,0.40) @0.230..0.250 b=0.006 ; centre fuller groove (0.03 wide, depth 0.006) to y 0.78 ; nicks x4 | EH_Steel | hand_R |
| 37 | sword fuller ember line **F2 (subtle)** | S | (-0.065,0.30,0.25)->(-0.065,0.76,0.25) tube 0.004 | EH_Ember x2 | hand_R |
| 38 | crossguard | E | (-0.23,0.88)(0.07,0.88)(0.09,0.915)(0.07,0.945)(-0.23,0.945)(-0.25,0.915) @0.220..0.260 b=0.008, with downturned tips | EH_Bronze | hand_R |
| 39 | grip + wraps | S | (-0.08,0.945,0.24;0.016)->(-0.08,1.20,0.24;0.016) leather wraps x6 | EH_Leather | hand_R |
| 40 | pommel disc | L | axis=Z c=(-0.08,1.265,0.24) `(0.000,0.020)(0.040,0.020)(0.044,0.000)(0.040,-0.020)(0.000,-0.020)` | EH_Bronze | hand_R |
| 41 | velvet cap (visible between the arches) | B | c=(0,1.500,0) s=(0.184,0.070,0.184) e=2 (top y 1.535) ; oxblood gives the bronze a dark value to read against | EH_Cloth (#7A2820) | head |
| 42 | orb | B + L | c=(0,1.582,0) r 0.026 (y 1.556-1.608) ; equator band `(0.027,1.576)(0.029,1.580)(0.029,1.584)(0.027,1.588)` | EH_Bronze | head |
(42 parts; budget <= 30k. F1 = cross gem (and the orb catches its glow); F2 = blade fuller ember, dim. Crown must keep >= 0.006 bevels so the rim light catches every edge.)

## 5. Pose
Immovable. Feet wide (stance 0.26), weight even; chest out; head level, chin 2 deg down; the greatsword planted point-down 0.24 in front of the right-centre body, both gauntlets stacked on the pommel (right below), elbows out 20 deg. Cloak hangs straight. The crown is level and fully visible from the 36 deg seat camera: the sword pommel (top 1.30) and gauntlets (top 1.34) stay below the beard line so they never overlap the crown.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.08, 0.222, 0.24) blade tip (grip is at y 1.0-1.25) | weapon |
| `socket_cast` | (0, 0.90, 0.30) | body |
| `socket_impact` | (-0.02, 0.70, 0.60) cleave contact | body |
| `socket_head` | (0, 1.56, 0) crown centre (orb) | head |

Extras: `impactTime 1.20`, `strikeRange 0.60`, `attackStyle melee`, `displayName "Emberhold Ember Sovereign"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Legs/pelvis | Torso/neck/head | Arms/weapon | Secondary. Feet are IK-planted unless a beat says "foot lifts". Overlap: pelvis leads, chest +0.03 s, head +0.06 s, cloak links +0.06 s each.

**Idle** (loop 4.0 s) - heavy breathing, weight shift
| t | Legs / pelvis | Torso / head | Arms / weapon | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest |
| 1.4 | body x +0.010, rz +2 (hip tilt); thigh_L rx -1, shin_L rx +1.5 (soft L knee), R leg locked | chest rx -1.8, spine rx -0.7 (inhale), neck rx +0.9; spine rz -1.5, head rz -1 (counter) | clavicles rz +-1.4 (shoulders lift); wrists hold the pommel | cape_1/2/3 rx +1/+2/+3 (lag) |
| 2.8 | body x -0.010, rz -1.5; shin_R rx +1.5 | chest rx +0.8 (exhale); head ry -2.5 (neck leads) | forearms rx -1 (elbows settle) | cape settles, crown gem pulse +10% |
| 4.0 | rest | rest | rest | rest |

**Move** (loop 1.0 s; steps 0.25, 0.75) - heavy march, sword carried: tip lifted 0.05 off the plinth and tilted back 15 deg onto the right pauldron (`weapon` rx +15, both wrists pinned to the grip)
| t | Legs / pelvis | Torso / neck / head | Arms / weapon | Secondary |
|---|---|---|---|---|
| 0.0 | body rx +5; thigh_L rx -16, shin_L rx +8 (L reaching, heel strike); thigh_R rx +10, shin_R rx +4 | spine rx +2, ry +5 (counter-twist); head level (stab 0.5) | arm_R/arm_L rx -40, forearms rx -50 (carry) | cape_1..3 rx +4/+6/+8 |
| 0.25 | step L: body y +0.02, rz +3; shin_L rx +4, foot_L flat; thigh_R rx +24, shin_R rx +48 (R foot lifts 0.05) | head rz -2 | weapon rz -2 (blade sway) | cape lags -4 |
| 0.5 | body rx +5, y 0; legs mirror of t0 | spine ry -5 | = t0 mirrored | cape rx -6/-8/-10 |
| 0.75 | step R: body y +0.02, rz -3; thigh_L rx +24, shin_L rx +48 | head rz +2 | weapon rz +2 | |
| 1.0 | = t0 | | | |

**Attack** (2.3 s; **impact 1.20**; the engine slows time at impact) - overhead two-handed cleave
| t | Legs / pelvis | Torso / neck / head | Arms / weapon | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | weight sinks onto the back leg: body y -0.015, thigh_R rx +6, shin_R rx +12; foot_L slides forward 0.05 | spine rx +2; head rx +4 (locks on the target) | wrists tighten on the pommel | |
| 0.30-0.95 (io) | body y +0.02, rx -4; knees straighten; foot_R drags back 0.06 | spine rx -4 -> -12, chest rx -6 (chest opens); head rx -4 | arm_R rx -40 -> -120, hand_R(forearm) rx -20 -> -45; arm_L rx -40 -> -118, hand_L -20 -> -42; blade lifts tip-first off the plinth | cape_1..3 rx +6/+9/+12 |
| 0.95-1.07 hold | coil: body rx -8, thigh_L rx +8, shin_L rx +18, thigh_R rx +10, shin_R rx +20 (both knees flex 18 deg) | spine rx -14, chest rx -6 | arm_R rx -150, hand_R rx -45; arm_L rx -145; sword vertical overhead; wrists cock back 20 | |
| 1.07-1.20 **strike** (0.13 s snap; pelvis leads 0.06 s, chest 0.03 s, arms 0) | body rx +16, z +0.26; L lunge: thigh_L rx -22, shin_L rx +30, foot_L planted +0.18; R trails: thigh_R rx +14, shin_R rx +8 | spine rx -14 -> +20, chest rx +8; neck/head rx +8 (0.04 s late) | arm_R rx -150 -> -45, arm_L rx -145 -> -42; hand_R rx -45 -> -15; wrist snap +25 | cape_1..3 rx +22 (whip, +0.06 s each) |
| 1.20 | **impact** | | edge/tip at `socket_impact`; time slows 0.2 for 0.8 s | |
| 1.20-1.50 hold | body y -0.035 (squash) | spine rx +20 held | weapon follows through 8 deg | cape rx +30 -> +10, 20% overshoot |
| 1.50-2.30 (io) | body to rest, feet re-centre | to rest | sword returns to the plant pose | cape settles |

**HitReact** (0.5 s)
| t | Legs / pelvis | Torso / neck / head | Arms / weapon | Secondary |
|---|---|---|---|---|
| 0.10 | body rx -8, z -0.06; thigh_L rx +6, shin_L rx +10 (brace) | spine rx -8, chest rx -4; head rx -12 (snap, +0.04 s) | arm_R/L rx +8 (resist the shove) | cape rx +16 |
| 0.50 | body rx -3 (settles at 60%) | spine rx -3, head rx -4 | | |

**Victory** (2.0 s, ends held)
| t | Legs / pelvis | Torso / neck / head | Arms / weapon | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | |
| 0.7 (bk) | body y +0.02, knees lock; weight rocks to heels (thigh rx +3) | spine rx -10, chest rx -6; head rx -10 | arm_R rx -150, hand_R rx -35; arm_L rx -150; sword raised overhead | cape rx +14 then settle; crown gem flare |
| 2.0 | hold | hold | hold | |

**Taunt** (1.4 s, once) - points the blade at the enemy king, then stamps the sword down
| t | Legs / pelvis | Torso / neck / head | Arms / weapon | Secondary |
|---|---|---|---|---|
| 0.00-0.40 | body rx -4; foot_R steps back 0.04 | chest rx -6; neck rx -8 (chin up) | arm_L lets go (rx +8); arm_R rx -75, hand_R rx -20; blade horizontal, tip at the target | cape rx +6 |
| 0.40-0.70 | hold | head rx +6 (slow deliberate nod) | blade holds; wrist rz +4 (point) | gem flare |
| 0.70-0.85 (snap) | foot_L lifts 0.03 and stamps: thigh_L rx -10; body rx +8, y -0.02 | chest rx +8 | arm_R rx -75 -> -35, hand_R rx -20 -> -5; tip drives into the plinth | cape +20 overshoot |
| 0.85-1.40 | settle | head up | stays planted | |

**Surrender** (2.4 s, once, holds the last pose) - drops the sword, kneels, bows
| t | Legs / pelvis | Torso / neck / head | Arms / weapon | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.04 | head rx -10 | wrists open (rx +20); grip loosens | crown tilts rz +3 |
| 0.30-0.55 | | | arms fall to rx -10; **`weapon` released at 0.45**: topples forward-left, bounces twice, lies on the plinth (heading +X) | cape rx +10 |
| 0.55-1.35 (io) | kneel: body y -0.31, z +0.04; thigh_L rx -75, shin_L rx +95 (L knee 90 deg, foot planted +0.12); thigh_R rx +20, shin_R rx +110, foot_R rx -70 (toes tucked, R knee on the plinth) | spine rx +10 | arms hang, hand_L/R rx -15 | cape drags down 0.05 |
| 1.35-1.95 | hold | spine rx +22, chest rx +12, neck rx +20, head rx +28 (eyes on the plinth); head rz +4 | arm_L rx -20, hand_L rx -40 (rests on the left thigh); arm_R rx +10, hand_R rx -25, wrist_R palm up (offering) | cape settles, 15% overshoot |
| 1.95-2.40 | hold | slow breath (chest rx -0.6) | hold | gem dims 30% |

## 8. Fragments (40)
Coarse: crown 5 (band 2, fleuron+arch group 2, cross + orb 1 kept whole as a glowing lump), breastplate 6, backplate 3, pauldrons 4 (each lame group whole), mantle 3 (fur-stone), greatsword 3 (blade 2, guard+hilt 1), legs/greaves 8, tabard/tasset 6, arms 2. Chunky bronze/stone with `EH_Interior` ember core and spark showers; the pedestal is not fractured.

## 9. Readability
- **Identity cue**: closed crown + cross-pattee with an ember gem; nothing else in the set carries a cross.
- vs `rime_king`: warm mid-high value (mean luma 0.45-0.55) solid mass with a bronze cross and a vertical blade; Rime is a dark block with an ice-crystal cross inside a hovering prism ring, empty hands.
- vs `emberhold_queen`: the king is wider (0.74 vs 0.62), 0.15 taller, closed dome + cross vs open tines.
- Silhouette tests (README "Recognisability rules"): cross visible as a plus >= 4 px wide at 60 px; top profile = band + 4 fleuron bumps + dome + cross spike (1 spike, never several).
