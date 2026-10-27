# emberhold_pawn - Emberhold Shieldbearer

## 1. Identity
- **Name**: Emberhold Shieldbearer. **Concept**: a young highland levy in bronze half-plate, a **big round bronze bowl-helm** on his head, braced behind a dented forge-ring shield, short sword sheathed at the hip.
- **Identity cue (the round helm)**: a hemispherical bronze helm, Ø0.164 (1.7x the head, +20% over the previous dome), y 0.912 -> 1.036, with a rim band, four radial ribs and a round button (r 0.014, top 1.050). The helm is the dominant top shape and the only element above the shoulders; the old crest fin is gone. The shield is reduced to Ø0.36 (was 0.42) and lowered so the helm stays the largest round form at the top.
- Silhouette: ball (helm) over a smaller disc (shield) over two stout legs; compact and short, no protrusion above 1.05. Faction rules: README sections 3-6. Greyscale target: mean luma 0.45-0.55 (README section 4).

## 2. Dimensions (total 1.05)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Boots | 0.22-0.29 | |
| Greaves / legs | 0.26-0.58 | knee at 0.43 |
| Skirt + belt | 0.44-0.62 | |
| Torso + pauldrons | 0.60-0.89 | shoulders at 0.86 |
| Head | 0.895-1.01 | head 0.115 |
| Round helm | 0.912-1.036 | Ø0.164 (r 0.082), brim band 0.912-0.936 |
| Button | 1.022-1.050 | tallest feature |
| Shield | 0.48-0.84, x -0.115..0.245 | round Ø0.36 |
Envelope at plinth top: 0.55 wide (x -0.20..0.275 at the pauldron/shield) x 0.50 deep (z -0.14..0.30).

## 3. Rig (humanoid template) and bone pivots
`humanoid_rig(J, weapon=(-0.15,0.64,0.09), shield=(0.065,0.66,0.20), cape=[(0,0.76,-0.12)])`; weapon parent `wrist_R`, shield parent `hand_L` (the forearm).

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`body`) | (0,0.56,0) | | elbow_L | (0.205,0.77,0.03) |
| spine | (0,0.62,0) | | wrist_L | (0.10,0.69,0.19) |
| chest | (0,0.74,0) | | wrist_R | (-0.165,0.62,0.10) |
| neck | (0,0.875,0.004) | | hip_L | (0.075,0.58,0) |
| head | (0,0.90,0.005) | | knee_L | (0.08,0.43,0.03) |
| top (bedroll) | (0,0.80,-0.10) | | ankle_L | (0.075,0.27,0.03) |
| clavicle_L | (0.07,0.84,0) | | toe_L | (0.075,0.245,0.11) |
| shoulder_L | (0.19,0.86,0) | | weapon / shield | (-0.15,0.64,0.09) / (0.065,0.66,0.20) |

**Binding (authoritative)**: 1, 2 -> `foot`; 3 -> `thigh` above the knee / `shin` below (cut at y 0.43, 0.04 overlap blend); 4, 5 -> `shin` (cop `~soft` `thigh`); 6-9, 14 -> `body` (tabard `~soft` `spine`); 10, 12 -> `spine`; 11, 13, 15 -> `chest`; 16-18, 21 -> `arm_L/R` (pauldron lames `~soft` clavicle); 19, 22 -> `hand_L/R` (forearm); 20, 23 -> `wrist_L/R`; 24-27, 38 -> `head`; 28-30, 37 -> `shield`; 31, 32 -> `body`; 33, 34 -> `weapon`; 35, 36 -> `top`.

## 4. Part list
Pedestal parts `ped_tier1, ped_tier2, ped_trim, ped_emblem` per README section 2 (root, EH_Stone / EH_Bronze).
**Part numbers are stable ids; gaps = removed parts.** The Bone column uses legacy names; the binding table in section 3 is authoritative (new rig template).

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
| 25 | **round helm dome S** | L | sides=24, `(0.076,0.912)(0.081,0.935)(0.082,0.965)(0.077,0.995)(0.062,1.018)(0.036,1.032)(0,1.036)` (Ø0.164) ; face window cut front 0.066 wide x 0.060 tall at y 0.925-0.985 ; hammered `+noise 0.002` | EH_Bronze | head |
| 26 | nasal bar + cheek guards M | E | nasal (-0.008,0.925)(0.008,0.925)(0.006,0.99)(-0.006,0.99)@0.050..0.058; cheek (0.046,0.930)(0.056,0.930)(0.050,0.975)(0.044,0.985)@-0.030..0.040 | EH_Steel | head |
| 27 | **helm rim band + button S** | L + B | rim band `(0.078,0.912)(0.088,0.916)(0.090,0.930)(0.080,0.936)` with 16 rivet domes r 0.007 ; button B c=(0,1.036,0) r 0.014 e=2 (top 1.050) | EH_Bronze | head |
| 28 | shield disc **S** | L | axis=Z c=(0.065,0.66,0.20) rot=(-6,10,0) profile (r,dz): (0,0.035)(0.044,0.035)(0.058,0.018)(0.092,0.012)(0.158,0.012)(0.180,0.018)(0.185,0.000)(0.172,-0.007)(0,-0.007) sides=40 `+noise 0.004` dents x4 (Ø0.36) | EH_Bronze | shield |
| 29 | shield forge ring | S | torus r=0.114, tube r=0.008 at z offset 0.018; 6 raised flame lugs (B 0.02x0.03x0.012) | EH_Steel | shield |
| 30 | shield rim + rivets | S/B | rim torus r=0.182 tube 0.009; 12 rivet domes r 0.009 at r 0.15 | EH_Bronze | shield |
| 31 | scabbard | S | (-0.165,0.585,0.06;0.021)->(-0.19,0.42,-0.01;0.022)->(-0.206,0.30,-0.075;0.015) cap=round | EH_Leather | body |
| 32 | chape + mouth band | B | band at mouth s=(0.05,0.02,0.05); chape c=(-0.206,0.30,-0.075) s=(0.03,0.04,0.03) | EH_Bronze | body |
| 33 | sword hilt + guard + pommel | S/E/B | grip (-0.165,0.585,0.06;0.012)->(-0.15,0.645,0.09;0.012) ; guard E 0.10 x 0.016 x 0.02 at (-0.158,0.62,0.078) ; pommel B r 0.016 at (-0.148,0.655,0.094) | EH_Steel/EH_Bronze | hand_R |
| 34 | sword blade (leaf, inside scabbard at idle) | E | along grip axis reversed, length 0.32, width taper 0.044->0.012 b=0.003 | EH_Steel | hand_R |
| 35 | bedroll + straps | B | c=(0,0.80,-0.125) s=(0.20,0.075,0.075) e=3, 2 straps S r 0.008 | EH_Cloth/EH_Leather | top |
| 36 | mantle scrap (left only) | E | (0.0,0.86)(0.17,0.84)(0.19,0.70)(0.07,0.72) @-0.115..-0.105 `~soft` | EH_Fur | top |
| 37 | **F** ember rune on shield boss | B | c=(0.065,0.66,0.236) s=(0.03,0.03,0.006) emissive | EH_Ember | shield |
| 38 | helm radial ribs x4 | S | bronze straps r 0.006 from the rim to the button over the dome at 45/135/225/315 deg (makes the dome read as a sphere and catches the rim light) | EH_Bronze | head |
(38 parts; budget <= 15k tris. Row 27 replaces the crest fin; part 37 is the single focal ember; the pedestal groove cracks do not count.)

## 5. Pose
Weight on the right leg (body rz -3, pelvis tilts 3 deg). Left forearm raised, shield forward and angled out 10 deg; right hand rests on the sword grip at the hip, sword blade inside the scabbard. Head offset 1.5 deg toward the left, helm level so the dome stays a clean circle from the seat camera.
Attack reads: the right hand draws along the scabbard axis (blade exits the mouth at (-0.165,0.585,0.06)).

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.15, 0.64, 0.09) (grip centre) | weapon |
| `socket_cast` | (0.065, 0.78, 0.25) (shield face top) | shield |
| `socket_impact` | (-0.03, 0.62, 0.55) (blade tip level with target centre at strikeRange 0.55) | body |
| `socket_head` | (0, 1.08, 0) | head |

Extras: `impactTime 0.95`, `strikeRange 0.55`, `attackStyle melee`, `displayName "Emberhold Shieldbearer"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Legs/pelvis | Torso/neck/head | Arms/weapon/shield | Secondary (`top` bedroll, cape_1).

**Idle** (loop 3.0 s)
| t | Legs / pelvis | Torso / neck / head | Arms / weapon / shield | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest |
| 1.5 | body y +0.004, rz -3.5 (weight onto R); thigh_L rx -1.5, shin_L rx +2 (L knee soft) | chest rx -1.6, spine rx -0.6 (inhale); head rx -1, ry +1.2 | arm_L rx -1.5 (shield rises with the breath) ; wrist_R grips the hilt | top rx +2.5 (bedroll lags 0.1 s) |
| 3.0 | rest | rest | rest | rest |

**Move** (loop 0.8 s; steps 0.2, 0.6) - shield-up march
| t | Legs / pelvis | Torso / neck / head | Arms / weapon / shield | Secondary |
|---|---|---|---|---|
| 0.0 | body rx +6, rz +3, y 0; thigh_L rx -14, shin_L rx +8 (reach); thigh_R rx +10 | spine ry +4 | arm_R rx +10 (swings back); arm_L rx -4 (shield steady) | |
| 0.2 | step L: body y +0.02, rz 0; shin_R rx +40 (R foot lifts 0.05) | head rz -1.5 | | |
| 0.4 | body rx +6, rz -3, y 0; legs mirror | spine ry -4 | arm_R rx -10; arm_L rx -8 | top rx -6 |
| 0.6 | step R: body y +0.02 | head rz +1.5 | | |
| 0.8 | = t0 | | | |

**Attack** (2.0 s; **impact 0.95**) - draws, shield bash, overhead chop
| t | Legs / pelvis | Torso / neck / head | Arms / weapon / shield | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | body rx +3; weight forward | spine rx +2 | arm_R rx -40, hand_R rx -70 (draws the blade clear, io) | |
| 0.30-0.55 | step: body z +0.15, rx +8; thigh_L rx -18, shin_L rx +22 (lunge), foot_L +0.10 | spine rx +6 | arm_L rx -25, translate z +0.10 (shield thrust, bk): the shield staggers the target (no impact yet) | bedroll rx -8 |
| 0.55-0.82 (io) | anticipation: body rx -8, z +0.05; thigh_L rx +6, shin_L rx +12 (sinks back) ; thigh_R rx +8 | spine rx -6; head rx -4 | arm_R rx -165, hand_R rx -35 (sword overhead); arm_L rx -10 (shield guard) | top rx +10 |
| 0.82-0.95 (snap; pelvis leads 0.06 s, chest 0.03 s) | body rx +16, z +0.28; thigh_L rx -22, shin_L rx +30; thigh_R rx +14 (trailing) | spine rx +14; head rx +6 | arm_R rx -165 -> -75, hand_R rx -35 -> -5; wrist_R snap +20 | top rx +18 |
| 0.95 | **impact**: hold; `socket_impact` on the target | | | |
| 0.95-1.10 | body y -0.02 (squash) | | | |
| 1.10-2.00 (io) | to rest | to rest | all return; blade stays out (engine may re-sheathe in Victory) | |

**HitReact** (0.4 s)
| t | Legs / pelvis | Torso / neck / head | Arms / weapon / shield | Secondary |
|---|---|---|---|---|
| 0.10 | body rx -12, z -0.08 (snap); thigh_L rx +6, shin_L rx +10 | spine rx -8; head rx -14 (helm rings: +0.04 s) | arm_L rx +15 (shield jolts) | top rx +12 |
| 0.40 | body rx -6, z -0.03 | spine rx -4; head rx -6 | arm_L rx +6 | |

**Victory** (1.6 s, ends held)
| t | Legs / pelvis | Torso / neck / head | Arms / weapon / shield | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | |
| 0.5 (bk) | body y +0.03 (small hop), knees extend | head rx -8 | arm_R rx -150, rz +10, hand_R rx -30 (sword raised) | |
| 1.0 | | | arm_L rx -35 (shield lifts) | |
| 1.6 | hold | hold | hold | |

**Taunt** (1.2 s, once) - bangs the sword on the shield rim twice
| t | Legs / pelvis | Torso / neck / head | Arms / weapon / shield | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | body rx +3, y +0.01; thigh_L rx -8 | chest rx -3; head rx -4 (looks at the foe over the rim) | arm_L rx -30 (shield up); arm_R rx -70, hand_R rx -35 (sword drawn up) | |
| 0.30-0.45 (snap) | | head rx +4 | arm_R rx -70 -> -45, hand_R -35 -> -10 : the blade strikes the shield rim (clang) | shield jolts arm_L rx +4 |
| 0.45-0.75 | | | rebound arm_R -70 ; second clang at 0.70 | |
| 0.75-1.20 | settle | head level | arms lower | |

**Surrender** (2.0 s, once, holds the last pose) - drops the sword, kneels, shield lowered
| t | Legs / pelvis | Torso / neck / head | Arms / weapon / shield | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.03 | head rx -10 | wrist_R opens | |
| 0.30-0.55 | | | **`weapon` (sword) released at 0.45**: clatters, bounces twice, lies on the plinth | |
| 0.55-1.20 (io) | kneel: body y -0.22; thigh_L rx -70, shin_L rx +90 (planted +0.08); thigh_R rx +20, shin_R rx +105, foot_R rx -65 | spine rx +10 | arm_L rx +5 (the shield lowers and rests on the plinth edge) ; arm_R hangs | bedroll slumps rx +10 |
| 1.20-1.70 | hold | spine rx +20, chest rx +8, neck rx +18, head rx +30 (the round helm bows) | hand_R palm up on the thigh | |
| 1.70-2.00 | hold | slow breath | hold | |

## 8. Fragments (20)
Coarse: shield splits into 3 big bronze segments (1 with the boss and ember rune), **helm dome splits into 2 halves + the button (button stays whole)**, breastplate 2 slabs. Fine: legs/skirt 7 slabs, arms 3, small plates 2. Chunky bronze/stone with ember interior; shield rim arc survives as one curved fragment. Sword blade 1 splinter-free steel piece.

## 9. Readability
- **Identity cue**: big round bronze helm with a button; short, compact body.
- vs `rime_pawn`: both have a round helm; Emberhold = smooth bronze hemisphere + round shield disc, mid-high value, upright; Rime = faceted dark dome with a glowing slit, hunched, spike comb below the helm, diagonal cleaver. Fill-black test: ball + disc, perimeter/sqrt(area) ~ 4.
- vs other roles: only role with a round ball head over a vertical disc; no feature taller than the helm (1.05); the bishop has a pointed slit mitre, the rook a crenellated flat top.
- Silhouette tests: helm width/height ratio 1.25-1.35 (dome), no concavity above the shoulders, top-down = circle with a rim ring.
