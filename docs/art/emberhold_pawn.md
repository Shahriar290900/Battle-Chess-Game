# emberhold_pawn - Emberhold Shieldbearer

## 1. Identity
- **Name**: Emberhold Shieldbearer. **Concept**: a young highland levy in bronze half-plate, braced behind a dented forge-ring shield, short sword sheathed at the hip.
- **Signature shape**: a huge round shield (Ø0.42, ~15% oversize for a pawn), forward-left, with a domed boss. Silhouette = round head over a round disc.
- Faction rules: README sections 3-6. Greyscale target: mean luma 0.30-0.45.

## 2. Dimensions (total 1.05)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Boots | 0.22-0.29 | |
| Greaves / legs | 0.26-0.58 | knee at 0.43 |
| Skirt + belt | 0.44-0.62 | |
| Torso + pauldrons | 0.60-0.89 | shoulders at 0.86 |
| Head + helm | 0.90-1.02 | head 0.12 = 6.7 heads of 0.80 figure |
| Crest | 1.02-1.05 | tallest feature |
| Shield | 0.47-0.89, x -0.145..0.275 | round |
Envelope at plinth top: 0.55 wide (x -0.20..0.275 at the shield) x 0.50 deep (z -0.14..0.30).

## 3. Bone pivots (x, y, z)
root (0,0,0) | body (0,0.56,0) | spine (0,0.62,0) | head (0,0.90,0) | top (0,0.86,-0.09) | arm_L (0.19,0.86,0) | hand_L (0.205,0.77,0.03) | arm_R (-0.185,0.86,0) | hand_R (-0.20,0.76,0)

## 4. Part list
Pedestal parts `ped_tier1, ped_tier2, ped_trim, ped_emblem` per README section 2 (root, EH_Stone / EH_Bronze).

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | boot M | B | c=(0.075,0.250,0.030) s=(0.105,0.056,0.20) rd=0.022 e=4 | EH_Leather | body |
| 2 | boot toecap M | B | c=(0.075,0.252,0.105) s=(0.08,0.04,0.05) rd=0.015 e=3 | EH_Bronze | body |
| 3 | leg M | S | (0.075,0.27,0.02;0.034)->(0.078,0.34,0.01;0.040)->(0.080,0.43,0.025;0.046)->(0.074,0.51,0.0;0.056)->(0.070,0.58,0.0;0.060) | EH_Cloth (quilted hose) | body |
| 4 | greave M | S | (0.076,0.29,0.045;0.040)->(0.080,0.42,0.050;0.050) sec=8 `+noise 0.003` | EH_Bronze | body |
| 5 | knee cop M | B | c=(0.080,0.435,0.058) s=(0.075,0.06,0.045) rd=0.016 e=3 | EH_Bronze | body |
| 6 | skirt (quilted) | L | sides=16 `(0.105,0.585)(0.140,0.52)(0.152,0.455)(0.150,0.440)` + `+noise 0.008` ; soot gradient at hem | EH_Cloth | body |
| 7 | tasset plates x6 | B | row at y 0.50, radius 0.145, each s=(0.06,0.08,0.014) rd=0.008, overlap 30%, rot rx=-12 | EH_Bronze | body |
| 8 | belt | L | `(0.112,0.585)(0.118,0.592)(0.118,0.618)(0.112,0.625)` | EH_Leather | body |
| 9 | belt buckle | B | c=(0.0,0.603,0.118) s=(0.04,0.03,0.012) rd=0.005 + 3 rivets | EH_Bronze | body |
| 10 | gambeson torso | S | (0,0.60,0;0.105*0.085)->(0,0.72,0;0.115*0.090)->(0,0.84,0;0.135*0.095), quilt noise 0.004 | EH_Cloth | spine |
| 11 | breastplate | E | (-0.105,0.64)(0.105,0.64)(0.125,0.80)(0.100,0.885)(-0.100,0.885)(-0.125,0.80) @0.078..0.100 b=0.010, central ridge | EH_Bronze | spine |
| 12 | lame plates x3 | B | y=0.66/0.685/0.71, s=(0.20,0.028,0.026) rd=0.01 e=4, z=0.090 | EH_Bronze | spine |
| 13 | backplate | E | (-0.10,0.64)(0.10,0.64)(0.12,0.80)(0.095,0.885)(-0.095,0.885) @-0.100..-0.078 b=0.010 | EH_Bronze | spine |
| 14 | tabard | E | (-0.065,0.625)(0.065,0.625)(0.058,0.45)(0,0.40)(-0.058,0.45) @0.100..0.108 b=0.004 `~soft` (spine/body) | EH_Cloth, bronze hem trim | spine |
| 15 | fur collar (ring) | S | circle r=0.098 at y=0.885 closed; r=0.034; `+noise 0.012` at 18/u | EH_Fur | spine |
| 16 | pauldron L (large) | B | c=(0.190,0.868,0) s=(0.125,0.070,0.130) rd=0.02 e=3 + lip ring | EH_Bronze | arm_L |
| 17 | pauldron R (small, dented) | B | c=(-0.178,0.862,0) s=(0.098,0.058,0.105) rd=0.018 e=3, dent amp 0.006 | EH_Bronze | arm_R |
| 18 | upper arm L | S | (0.190,0.855,0;0.040)->(0.205,0.775,0.03;0.034) | EH_Cloth | arm_L |
| 19 | forearm L + gauntlet | S | (0.205,0.775,0.03;0.034)->(0.17,0.725,0.12;0.030)->(0.10,0.685,0.19;0.026); cuff B c=(0.15,0.71,0.145) s=(0.06,0.06,0.07) | EH_Bronze/EH_Leather | hand_L |
| 20 | hand L | B | c=(0.095,0.682,0.195) s=(0.045,0.04,0.05) e=3 (fist round shield grip) | EH_Leather | hand_L |
| 21 | upper arm R | S | (-0.185,0.855,0;0.040)->(-0.20,0.765,0;0.033) | EH_Cloth | arm_R |
| 22 | forearm R + gauntlet | S | (-0.20,0.765,0;0.033)->(-0.19,0.685,0.05;0.029)->(-0.168,0.628,0.095;0.025), cuff at 0.65 | EH_Leather/EH_Bronze | hand_R |
| 23 | hand R | B | c=(-0.163,0.620,0.100) s=(0.045,0.04,0.05) e=3 | EH_Leather | hand_R |
| 24 | head | B | c=(0,0.952,0.006) s=(0.095,0.115,0.108) e=2.4 (jaw taper: bottom 80% width), brow ridge B s=(0.09,0.012,0.03) at y 0.97 | EH_Leather (skin-tone via Cloth) | head |
| 25 | helm dome | L | `(0.054,0.935)(0.058,0.970)(0.052,1.000)(0.034,1.016)(0,1.022)` sides=18, `+noise 0.002` | EH_Bronze | head |
| 26 | nasal bar + cheek guards M | E | nasal (-0.008,0.925)(0.008,0.925)(0.006,0.99)(-0.006,0.99)@0.050..0.058; cheek (0.046,0.930)(0.056,0.930)(0.050,0.975)(0.044,0.985)@-0.030..0.040 | EH_Steel | head |
| 27 | helm crest fin **S** | E | plane=YZ (y,z): (1.000,-0.052)(1.030,-0.040)(1.050,-0.005)(1.040,0.030)(1.000,0.045) thickness x=-0.010..0.010 b=0.004 + 3 rivets | EH_Bronze | head |
| 28 | shield disc **S** | L | axis=Z c=(0.065,0.68,0.20) rot=(-6,10,0) profile (r,dz): (0,0.040)(0.050,0.040)(0.066,0.020)(0.105,0.014)(0.180,0.014)(0.205,0.020)(0.210,0.000)(0.196,-0.008)(0,-0.008) sides=40 `+noise 0.004` dents x4 | EH_Bronze | hand_L |
| 29 | shield forge ring | S | torus r=0.13, tube r=0.009 at z offset 0.020; 6 raised flame lugs (B 0.02x0.03x0.012) | EH_Steel | hand_L |
| 30 | shield rim + rivets | S/B | rim torus r=0.208 tube 0.010; 12 rivet domes r 0.010 at r 0.17 | EH_Bronze | hand_L |
| 31 | scabbard | S | (-0.165,0.585,0.06;0.021)->(-0.19,0.42,-0.01;0.022)->(-0.206,0.30,-0.075;0.015) cap=round | EH_Leather | body |
| 32 | chape + mouth band | B | band at mouth s=(0.05,0.02,0.05); chape c=(-0.206,0.30,-0.075) s=(0.03,0.04,0.03) | EH_Bronze | body |
| 33 | sword hilt + guard + pommel | S/E/B | grip (-0.165,0.585,0.06;0.012)->(-0.15,0.645,0.09;0.012) ; guard E 0.10 x 0.016 x 0.02 at (-0.158,0.62,0.078) ; pommel B r 0.016 at (-0.148,0.655,0.094) | EH_Steel/EH_Bronze | hand_R |
| 34 | sword blade (leaf, inside scabbard at idle) | E | along grip axis reversed, length 0.32, width taper 0.044->0.012 b=0.003 | EH_Steel | hand_R |
| 35 | bedroll + straps | B | c=(0,0.80,-0.125) s=(0.20,0.075,0.075) e=3, 2 straps S r 0.008 | EH_Cloth/EH_Leather | top |
| 36 | mantle scrap (left only) | E | (0.0,0.86)(0.17,0.84)(0.19,0.70)(0.07,0.72) @-0.115..-0.105 `~soft` | EH_Fur | top |
| 37 | **F** ember rune on shield boss | B | c=(0.065,0.68,0.246) s=(0.03,0.03,0.006) emissive | EH_Ember | hand_L |
(37 parts; budget <= 15k tris. Part 37 is the single focal ember; the pedestal groove cracks do not count.)

## 5. Pose
Weight on the right leg (body rz -3, pelvis tilts 3 deg). Left forearm raised, shield forward and angled out 10 deg; right hand rests on the sword grip at the hip, sword blade inside the scabbard. Head offset 1.5 deg toward the left.
Attack reads: the right hand draws along the scabbard axis (blade exits the mouth at (-0.165,0.585,0.06)).

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.15, 0.64, 0.09) (grip centre) | hand_R |
| `socket_cast` | (0.065, 0.80, 0.25) (shield face top) | hand_L |
| `socket_impact` | (-0.03, 0.62, 0.55) (blade tip level with target centre at strikeRange 0.55) | body |
| `socket_head` | (0, 1.04, 0) | head |

Extras: `impactTime 0.95`, `strikeRange 0.55`, `attackStyle melee`, `displayName "Emberhold Shieldbearer"`, `contractVersion 1`.

## 7. Clips (time s | bone | rotation deg / translation)
**Idle** (loop 3.0 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 1.5 | spine | rx +1.6 (io) |
| 1.5 | head | rx -1.0, ry +1.2 |
| 1.5 | body | y +0.004 |
| 1.5 | arm_L | rx -1.5 (shield rises with breath) |
| 1.5 | top | rx +2.5 (lag, bedroll) |
| 3.0 | all | rest |

**Move** (loop 0.8 s; steps at 0.2 and 0.6)
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +6, rz +3, y 0 |
| 0.2 | body | y +0.02, rz 0 (step) |
| 0.4 | body | rx +6, rz -3, y 0 |
| 0.6 | body | y +0.02, rz 0 (step) |
| 0.0/0.4/0.8 | arm_R | rx +10 / -10 / +10 |
| 0.0/0.4/0.8 | arm_L | rx -4 / -8 / -4 |
| 0.4 | top | rx -6 |
| 0.8 | all | = t0 |

**Attack** (2.0 s; impact 0.95)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.00-0.30 | arm_R / hand_R | rx -40 / rx -70, draws the blade clear (io); body rx +3 |
| 0.30-0.55 | arm_L | rx -25, translate z +0.10 (shield thrust, bk); body z +0.15, rx +8 |
| 0.55 | body | z +0.15 held; shield staggers the target (no impact event yet) |
| 0.55-0.82 | anticipation | arm_R rx -165, hand_R rx -35, body rx -8, z +0.05, spine rx -6, head rx -4 (io); arm_L rx -10 |
| 0.82-0.95 | **strike** (0.13 s snap) | arm_R rx -165 -> -75, hand_R rx -35 -> -5, body rx +16, z +0.28, spine rx +14, head rx +6 |
| 0.95 | **impact** | hold; socket_impact on the target |
| 0.95-1.10 | hold | squash: body y -0.02 |
| 1.10-2.00 | recover (io) | everything returns; blade stays out (engine may re-sheathe in Victory) |

**HitReact** (0.4 s)
| t | bone | value |
|---|---|---|
| 0.00 | body | rx 0, z 0 |
| 0.10 | body | rx -12, z -0.08 (snap) ; spine rx -8 ; head rx -14 ; arm_L rx +15 ; top rx +12 |
| 0.40 | body | rx -6, z -0.03 ; spine -4 ; head -6 ; arm_L +6 |

**Victory** (1.6 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.5 | arm_R | rx -150, rz +10 ; hand_R rx -30 (sword raised, bk) ; body y +0.03 |
| 0.5 | head | rx -8 |
| 1.0 | arm_L | rx -35 (shield lifts) |
| 1.6 | hold | held pose (hold last key) |

## 8. Fragments (20)
Coarse: shield splits into 3 big bronze segments (1 with the boss and ember rune), helm dome 1 piece, breastplate 2 slabs. Fine: legs/skirt 8 slabs, arms 4, small plates 2. Chunky bronze/stone with ember interior; shield rim arc survives as one curved fragment. Sword blade 1 splinter-free steel piece.

## 9. Readability
- vs `rime_pawn`: wide, round, mid-value (shield disc dominates), vertical head crest only 0.03 tall; Rime is hunched, dark, with a spine of spikes and a diagonal cleaver. Fill-black test: disc + head, perimeter/sqrt(area) ~ 4.
- vs other roles: only role whose largest mass is a vertical disc beside the torso; no vertical protrusion taller than 1.05; much smaller head-crest than the bishop's hood.
- Ember: one rune at the boss; armour is warm bronze mid-value with soot hems.
