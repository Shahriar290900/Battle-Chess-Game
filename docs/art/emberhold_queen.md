# emberhold_queen - Emberhold Flamecrown Warden

## 1. Identity
- **Name**: Emberhold Flamecrown Warden. **Concept**: an armoured warrior-queen in swept bronze pauldrons, a layered scale cloak and a **tall open coronet of nine bronze tines, each tipped with an ember bead, with a small ember orb standing in the centre**. Hands empty at rest; the great hammer-staff is summoned from embers during Attack.
- **Identity cue**: the pointed open coronet. Band y 1.350-1.410; **9 tines** (5 tall to 1.550, 4 short to 1.515, alternating, base 0.050 wide, splayed out 8 deg); ember bead r 0.014 on each tip; orb r 0.021 on a 0.09 stalk in the centre, top 1.549 (same level as the tall tines). Crown stack 0.20 tall, 0.21 wide with the splay (1.8x the head). +20% over the previous crown.
- **Never confusable with the king**: NO arches, NO cross, NO dome: the tines are open and see-through at 60 px, the orb sits inside them. She is also slimmer (0.62 vs 0.74), 0.15 shorter, with a flared A-line skirt and a pinched waist.
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
| Coronet band | 1.350-1.410 | r 0.088 -> 0.096 |
| Tines x9 | 1.410-1.550 | tall 0.140, short 0.105 |
| Orb + stalk | 1.414-1.549 | orb r 0.021 centred y 1.528 |
| Cloak (behind) | 0.30-1.20 | z -0.12..-0.32 |
Envelope: 0.62 wide (pauldrons) x 0.50 deep (cloak flare z -0.28..0.22). Crown 0.21 wide.

## 3. Rig (humanoid template) and bone pivots
`humanoid_rig(J, cape=[(0,1.10,-0.16),(0,0.78,-0.22),(0,0.50,-0.28)])`; `weapon_summon` is a non-skinned node under `wrist_R` (origin = grip), scale 0 in every clip except Attack. No `weapon` bone (nothing held at rest).

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`body`) | (0,0.78,0) | | elbow_L | (0.24,0.93,0.04) |
| spine | (0,0.90,0) | | wrist_L | (0.25,0.80,0.18) |
| chest | (0,1.02,0) | | wrist_R | (-0.25,0.80,0.18) |
| neck | (0,1.15,0.005) | | hip_L | (0.07,0.80,0) |
| head | (0,1.19,0.01) | | knee_L | (0.08,0.56,0.04) |
| top (cloak / braid root) | (0,1.17,-0.10) | | ankle_L | (0.075,0.27,0.04) |
| clavicle_L | (0.07,1.13,0) | | toe_L | (0.075,0.245,0.12) |
| shoulder_L | (0.20,1.12,0) | | `weapon_summon` | (-0.25,0.80,0.18) under `wrist_R` |

**Binding (authoritative)**: 1 -> `foot`; 2 -> `body` `~soft` `thigh` (skirt follows the kneel); 3-5 -> `body` (hem rows 70% body / 30% `thigh`); 6-8 -> `body` (tabard `~soft` `spine`); 9, 12 -> `spine`; 10, 11, 13, 14, 31, 35 -> `chest`; 15 -> `neck`; 16, 17 -> `arm_L/R` (lames `~soft` clavicle); 18 -> `arm`; 19, 20 -> `hand_L/R` (forearm); 21 -> `wrist`; 22-29 -> `head`; 30 braid -> `top` `~soft` `head`; 32-34 -> `top` `~soft` `cape_1..3`; 36-39 -> `weapon_summon`.

## 4. Part list
Pedestal parts per README section 2.
**Part numbers are stable ids; gaps = removed parts.** The Bone column uses legacy names; the binding table in section 3 is authoritative (new rig template).

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
| 25 | coronet band **S** | L | sides=24, `(0.082,1.350)(0.088,1.354)(0.096,1.368)(0.096,1.405)(0.090,1.410)(0.084,1.405)(0.082,1.360)` ; engraved ring groove x1 ; 18 rivet domes r 0.006 | EH_Bronze | head |
| 26 | coronet tines x9 **S** | E | each a tapered spike : base width 0.050, thickness 0.020, tip point width 0.010, b=0.004 ; standing on the band at y 1.410, radius 0.094, angles k*40 deg from the front (0, 40, 80...) ; heights 0.140 at 0/+-80/+-160 deg (5 tall, tips y 1.550), 0.105 at +-40/+-120 deg (4 short, tips y 1.515) ; tilt out 8 deg ; ember bead B r 0.014 on each tip (EH_Ember x3, accent cluster) | EH_Bronze / EH_Ember x3 | head |
| 27 | orb stalk + cap disc | S + L | cap `(0,1.405)(0.060,1.408)(0.060,1.414)(0,1.416)` ; stalk S (0,1.414,0;0.008)->(0,1.510,0;0.007) ; **no arches** (keeps the coronet open) | EH_Bronze | head |
| 28 | coronet orb **F1** | B | c=(0,1.528,0) r 0.021 e=2 (top y 1.549) ; ember core visible through a bronze lattice of 6 slits | EH_Ember x7 | head |
| 29 | orb bezel | S | torus r 0.024 tube 0.004 at y 1.510 | EH_Bronze | head |
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
(39 parts; budget <= 30k + weapon 1K texture. F1 = coronet orb + tine beads (one cluster at the crown); F2 only exists while the weapon is summoned.)

## 5. Pose
Weight on the left leg, hips tilted 3 deg, shoulders counter-tilted -2 deg, chin raised 3 deg. Arms hang slightly away from the body (gap 0.08), hands open at the sides. Cloak settled, no weapon. The coronet is level and crisp against the sky from the seat camera: braid and cloak yoke never rise above y 1.30.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.25, 0.80, 0.18) right palm (weapon_summon origin) | wrist_R |
| `socket_cast` | (0, 0.90, 0.30) summon spiral target | body |
| `socket_impact` | (0, 0.30, 0.70) hammer head contact | body |
| `socket_head` | (0, 1.58, 0) above the orb | head |

Extras: `impactTime 1.30`, `strikeRange 0.70`, `attackStyle summon`, `displayName "Emberhold Flamecrown Warden"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Legs/pelvis | Torso/neck/head | Arms | Secondary (`top` cloak/braid, cape_1..3, crown). The skirt hides the legs but the knees still bend: they drive the skirt `~soft` and the kneel.

**Idle** (loop 3.6 s) - regal stillness
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | rest ; weapon_summon scale 0 | rest | rest | rest |
| 1.2 | body x +0.008, rz +3 (hip tilt); thigh_L rx -1, shin_L rx +1 | chest rx -1.6, spine rx -0.6; head rx -1, ry +1.5 | clavicles rz +-1.2 | top rx +2 (braid lags 0.1 s) |
| 1.8 | | | wrist_L rx -2 | cape_1/2/3 rx +1/+2/+3 (cloak settles) |
| 2.4 | body x -0.006, rz -2 | chest rx +0.6; head rz +1 | arm_R rx -1.5, hand_R rx -3 (fingers flex) | crown tine beads shimmer (shader, no bone) |
| 3.6 | rest | rest | rest | rest |

**Move** (loop 1.0 s; steps 0.25, 0.75) - stately glide
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | body rx +4; thigh_L rx -12, shin_L rx +6 ; thigh_R rx +8 | spine ry +4 (counter-twist) ; head level (stab 0.5) | arm_R rx -4, arm_L rx +4 | top rx +6; cape rx +4/+6/+8 |
| 0.25 | step L: body y +0.02, rz +2 ; thigh_R rx +20, shin_R rx +40 (hem lifts and swings) | head rz -1.5 | arm_R rx +6, arm_L rx -6 | cape lags |
| 0.5 | body rx +6 ; legs mirror t0 | spine ry -4 | arms mirror | top rx -8 |
| 0.75 | step R: body y +0.02, rz -2 | head rz +1.5 | arm_R rx -6, arm_L rx +6 | |
| 1.0 | = t0 | | | |

**Attack** (2.4 s; **impact 1.30**) - summons a hammer-staff, spins, overhead slam
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.40 | weight back: body rx -2; thigh_R rx +6 | spine rx -4; head rx -6 | arm_R rx -35, hand_R rx -20 (reaches for the grip); arm_L rx -20 | **weapon_summon** scale 0 -> 1.15 (0.30 s) -> 1.0 (0.40 s), embers spiral (engine) |
| 0.40-1.00 (io) | advance and spin: body ry 0 -> -360 (lin, 0.55 s), y +0.02; feet pivot on the ball (foot_L rz follows, 3 small steps) | spine ry counter -20 then free; head leads (ry spot-the-target, locks on target at 0.95) | arm_R rx -110, hand_R rx -35; arm_L rx -95, rz +20 (left hand takes the lower grip) | top/cloak rx -15 (whips out 0.10 s behind) ; scale cloak overshoots +20% |
| 1.00-1.17 hold | coil: body rx -6; thigh_L rx +8, shin_L rx +16; thigh_R rx +8, shin_R rx +16 | spine rx -10; head rx -8 | arm_R rx -165, hand_R rx -30; arm_L rx -150; weapon head above 1.7 | |
| 1.17-1.30 (snap; pelvis leads 0.06 s) | body rx +20, z +0.25; lunge thigh_L rx -24, shin_L rx +30; trailing thigh_R rx +14 | spine rx +18; head rx +8 | arm_R rx -165 -> -40, arm_L rx -150 -> -45; hand_R rx -30 -> -10 | top rx +25 (cloak whip) |
| 1.30 | **impact** | | hammer head on `socket_impact`; shockwave (engine) | |
| 1.30-1.55 hold | body y -0.03 (squash), z +0.25 held | | | cloak overshoot 20% |
| 1.55-2.40 (io) | to rest | to rest | to rest | weapon_summon scale 1 -> 0 over 2.1-2.4 (engine dissolve) |

**HitReact** (0.5 s)
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.10 | body rx -11, z -0.07; thigh_L rx +6, shin_L rx +10 | spine rx -9; head rx -14 (+0.04 s) ; crown tilts rz +6 | arm_L/R rx +12 | top rx +16 (braid whips) |
| 0.50 | body rx -4 | spine rx -3, head rx -5 | | |

**Victory** (2.0 s, ends held)
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | |
| 0.5 | body y +0.015 | spine rx -6; head rx -10 | arm_R rx -150, hand_R rx -20 (fist raised) | |
| 1.0 | | | | top rx +10 (cloak billows); tine beads flare (+40% emissive) |
| 2.0 | hold | hold | hold | |

**Taunt** (1.3 s, once) - a regal beckon and a toss of the crown
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.35 | body rx -3; weight to the L leg | chest rx -4; head rx -6 + rz +5 (chin raised, tilted) | arm_R rx -70, hand_R rx -45 (forearm up) ; arm_L on hip (hand_L rx -60) | cloak rx +6 |
| 0.35-0.85 | hold | head ry +4 | wrist_R curls twice: rx -35 -> +10 at 0.50 and 0.72 (come to me) | tine beads flare |
| 0.85-1.30 | settle | head level, one slow blink (none: eyes dim 0.1 s) | arms drop | cloak settles |

**Surrender** (2.2 s, once, holds the last pose) - kneels, empty hands palm-up, coronet lowered
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.04 | head rx -10 | arms drop rx +10 | crown tilts rz +4 |
| 0.30-1.10 (io) | kneel: body y -0.28, z +0.03; thigh_L rx -75, shin_L rx +95 (hidden under the hem, foot planted +0.10); thigh_R rx +20, shin_R rx +108 | spine rx +10 | arms hang | skirt hem spreads r +0.03 on the plinth; cloak drags down 0.05 |
| 1.10-1.70 | hold | spine rx +20, chest rx +10, neck rx +20, head rx +28 (coronet tilts forward, beads dim) | arm_L/R rx -25, hand_L/R rx -45, wrist palms up on the thighs (surrender, nothing to drop; `weapon_summon` stays 0) | cloak settles |
| 1.70-2.20 | hold | slow breath | hold | beads fade -30% |

## 8. Fragments (40)
Coarse: 8 skirt-armour slabs, 6 cloak scale clusters (6 scales each), 2 pauldron wings (whole), 4 breastplate chunks, **coronet 4 (band 2, two tine groups of 4-5 that keep their ember beads and points; the orb stays an ember lump)**, head 3, arms 6, braid 2, boots 3, pedestal-edge rubble 2. Chunky bronze and stone with `EH_Interior` ember cores.

## 9. Readability
- **Identity cue**: open nine-tine coronet with ember-tipped points and a small orb; no cross.
- vs `rime_queen`: wide swept shoulders + warm bronze open coronet + scale cloak (mean luma 0.45-0.55); Rime is slim, dark, with a crystal coronet and a halo behind. Perimeter/sqrt(area) ~ 4.
- vs `emberhold_king`: open points vs closed dome + cross; slimmer (0.62 vs 0.74), 0.15 shorter.
- vs other roles: crown (tip 1.55) on a small head + flared A-line skirt; waist pinch; empty hands. The bishop is a cone with a slit mitre and a staff.
- Silhouette tests: >= 5 tine peaks in the top profile of the front 180 deg arc at 60 px; top-down: a ring of 9 spikes.
