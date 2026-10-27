# emberhold_knight - Emberhold Ashmane Rider

## 1. Identity
- **Name**: Emberhold Ashmane Rider. **Concept**: a **barded bronze war-horse**, a heavy charger in chanfron, crinet, peytral and crupper over an ash-dark coat, with a **mane of living flame** streaming from its arched crest. A bronze-armoured rider **crouches low over its neck** (seat 0.80, head top 1.07) with a short pennoned lance couched at the flank. The horse replaces the old war-elk.
- **Identity cue (the horse head and arched neck)**: the tallest, brightest and most central thing on the piece. Neck arches from the withers (0.80) to the poll (1.20) in a 0.42 rise (about 3x the old neck rise), with six overlapping bronze crinet plates and a flame mane; the head hangs 55 deg below horizontal, 0.30 long, with a bronze chanfron, eye rondels and two ear covers (tips y 1.30 = the top of the piece). **Everything above y 1.10 is horse** (the rider tops out at 1.10), from any azimuth.
- **Silhouette plan** (+20% on the old signature): side view = tall S-curve neck + wedge head over a long barrel, the rider a low hump behind, the lance a thin horizontal below the head; front view = a vertical column (crinet 0.17 wide, mane flames above, ears) with the rider's shoulders behind it and the lance to the viewer's left; rear view = the head and mane rise 0.20 above the rider's helm; top-down = a long teardrop (head/neck pointing +Z).
- Horse faces +Z. Mount uses the quadruped template; the rider uses the humanoid template, rooted on `top` (the saddle).

## 2. Dimensions (total 1.30)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Hooves / lower legs | 0.22-0.45 | greaves on the cannon bones |
| Upper legs | 0.40-0.70 | hind hock at 0.44 (z -0.31) |
| Barrel + barding | 0.47-0.78 | z -0.30..0.14, width 0.28 |
| Withers | 0.80 | at z 0.12 |
| Arched neck | 0.78-1.20 | base (z 0.16) -> poll (0,1.20,0.31), width 0.19 -> 0.085 |
| Horse head | 0.915-1.215 | length 0.30 at 55 deg ; muzzle (0,0.925,0.48) |
| Ears (bronze covers) | 1.20-1.30 | tips y 1.30 |
| Flame mane | 0.82-1.30 | 12 tongues; tallest tip 1.30 behind the ears |
| Saddle | 0.77-0.82 | seat y 0.80 |
| Rider (crouched) | 0.82-1.10 | torso leaned 55 deg, head top 1.07, helm 1.10 |
| Lance | y 0.80-0.915 | butt (-0.19,0.80,-0.16), tip (-0.19,0.915,0.50) |
Envelope: 0.46 wide (stirrups x +-0.21, rider shoulders +-0.17, crinet 0.17) x 0.80 deep (z -0.32 tail .. 0.48 muzzle; the lance tip at 0.50 is the weapon exception).

## 3. Rig (quadruped template + humanoid rider)
`quadruped_rig(JQ)` for the mount; `humanoid_rig(JR, weapon=(-0.19,0.86,0.15), pelvis_name="rider_pelvis")` for the rider, with `rider_pelvis` re-parented under `top` (the seat). The rider's own `top` is not created; the rider's `body` alias is `rider_pelvis`. The contract bones are satisfied by: `root, body` (= rump), `top` (= seat), `mount_body, mount_head`, and the rider's `spine, head, arm_*, hand_*`.

**Mount joints (L side; R mirrored)**

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| rump (`body`) | (0,0.66,-0.22) | | hip_L | (0.10,0.65,-0.22) |
| barrel (`mount_body`) | (0,0.64,-0.04) | | hock_L | (0.11,0.44,-0.31) |
| withers (`mount_chest`) | (0,0.78,0.12) | | fetlock_L | (0.11,0.29,-0.27) |
| neck_1 | (0,0.84,0.17) | | hoof_L | (0.11,0.22,-0.24) |
| neck_2 | (0,1.02,0.25) | | shoulder_L | (0.10,0.70,0.10) |
| head (poll, `mount_head`) | (0,1.19,0.31) | | elbow_L (carpus) | (0.11,0.45,0.15) |
| jaw | (0,1.06,0.33) | | fetlock_F_L | (0.11,0.30,0.16) |
| seat (`top`) | (0,0.80,-0.06) | | hoof_F_L | (0.11,0.22,0.17) |
| tail_1 / tail_2 / tail_3 | (0,0.70,-0.28) / (0,0.58,-0.33) / (0,0.45,-0.34) | | | |

**Rider joints (L side; R mirrored except wrist_R)**

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`rider_pelvis`) | (0,0.82,-0.08) | | elbow_L | (0.17,0.89,0.10) |
| spine | (0,0.87,-0.05) | | wrist_L (reins) | (0.12,0.86,0.18) |
| chest | (0,0.94,0.01) | | wrist_R (lance grip, explicit) | (-0.15,0.86,0.12) |
| neck | (0,0.99,0.065) | | hip_L | (0.09,0.82,-0.08) |
| head | (0,1.00,0.09) | | knee_L | (0.17,0.72,0.05) |
| clavicle_L | (0.06,0.96,0.03) | | ankle_L | (0.17,0.52,0.02) |
| shoulder_L | (0.16,0.95,0.03) | | toe_L | (0.17,0.49,0.09) |
| weapon (lance centre) | (-0.19,0.86,0.15) | | | |

**Binding (authoritative)**: 1 -> `mount_body`; 2, 11 -> `body` (rump); 3, 9, 27 -> `mount_chest`; 4 -> `fore_upper` (shoulder -> y 0.45) / `fore_lower` (0.45 -> 0.30) / `fore_hoof` (0.30 -> hoof); 5 -> `hind_upper` (hip -> hock) / `hind_lower` (hock -> fetlock) / `hind_hoof`; 6-8 -> `fore_hoof` / `hind_hoof`; 7 greaves -> `*_lower`; 10, 12-14 -> `mount_body` (caparison 12 `~soft` `body`); 15 -> `tail_1..3`; 16 -> `neck_1`/`neck_2` (split at y 0.95, `~soft` 0.06 overlap); 17 -> `neck_1` (first 3) / `neck_2` (last 3); 18-25, 28 (bridle) -> `mount_head` (20 jaw -> `jaw`); 26 mane -> `neck_1`/`neck_2` `~soft` (flicker in shader); 29 -> `foot_L/R`; 30, 31 -> `thigh`/`shin`; 32 -> `spine`; 33, 34 -> `chest`; 35 -> `arm_L/R`; 36 -> `arm`/`hand_L/R` (forearm); 37-39 -> `head`; 40-42 -> `weapon`; 43 -> `wrist_L/R`.

## 4. Part list
Pedestal parts per README section 2. Prefix `m_` = mount, `r_` = rider. Mount modelled in world rest-pose coordinates (x = width, y = up, z = forward).

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | m_barrel **S** | S | (0,0.66,-0.27;0.15w*0.15h)->(0,0.64,-0.06;0.165*0.165)->(0,0.65,0.12;0.150*0.165) `+noise 0.005` | EH_Fur (dark ash coat #4A3A2C) | mount_body |
| 2 | m_haunch M | B | c=(0.115,0.62,-0.21) s=(0.12,0.22,0.22) e=2.3 | EH_Fur | body |
| 3 | m_shoulder M | B | c=(0.10,0.64,0.10) s=(0.12,0.22,0.18) e=2.3 | EH_Fur | mount_chest |
| 4 | m_foreleg M | S | upper (0.10,0.70,0.10;0.055)->(0.11,0.45,0.15;0.034) ; lower ->(0.11,0.30,0.16;0.026) ; pastern ->(0.11,0.22,0.17;0.030) | EH_Fur | fore_upper/lower/hoof |
| 5 | m_hindleg M | S | upper (0.10,0.65,-0.22;0.068)->(0.11,0.44,-0.31;0.040) ; lower ->(0.11,0.29,-0.27;0.026) ; pastern ->(0.11,0.22,-0.24;0.030) (hock angle) | EH_Fur | hind_upper/lower/hoof |
| 6 | m_hooves x4 | B | c=(+-0.11,0.236,0.17) and (+-0.11,0.236,-0.24), s=(0.06,0.03,0.07) rd=0.01 e=3 | EH_Bronze (caps) / EH_Steel | *_hoof |
| 7 | m_leg greaves x4 | S | wrapping the cannon bones (r +0.008), 0.12 long, sec=8, flared top lip | EH_Bronze | *_lower |
| 8 | m_fetlock tufts x4 | S | 5 fur tufts each len 0.04 at the fetlocks | EH_Fur | *_hoof |
| 9 | m_peytral (chest barding) **S** | E | plane XY mirrored: (-0.15,0.50)(0.15,0.50)(0.17,0.66)(0.12,0.78)(-0.12,0.78)(-0.17,0.66) @ z 0.14..0.168 bent around the chest (curve R 0.17) b=0.010 + 3 lames ; anvil relief 0.07 x 0.06 raised 0.005 | EH_Bronze | mount_chest |
| 10 | m_flanchard plates x4 M | B | c=(0.162,0.62,0.06-k*0.09) s=(0.02,0.16,0.09) rd=0.01 e=4, k=0..3, overlap 25% | EH_Bronze | mount_body |
| 11 | m_crupper (rump armour) | E | (-0.13,0.76)(0.13,0.76)(0.15,0.60)(0,0.54)(-0.15,0.60) @ z -0.30..-0.27 curved, b=0.010 + 3 small spikes len 0.04 | EH_Bronze | body |
| 12 | m_caparison (oxblood) | E | (-0.17,0.78)(0.17,0.78)(0.20,0.50)(0.12,0.42)(-0.12,0.42)(-0.20,0.50) over the barrel, stitched bronze-trimmed hem `~soft` | EH_Cloth | mount_body |
| 13 | m_saddle | B | c=(0,0.795,-0.06) s=(0.19,0.045,0.22) rd=0.02 e=3 ; cantle B s=(0.18,0.07,0.03) at z -0.17 ; pommel s=(0.06,0.06,0.04) at z 0.05 | EH_Leather | mount_body |
| 14 | m_girth + stirrup straps M | S | (0.16,0.64,-0.04)->(0.17,0.52,0.0) r 0.007 ; stirrup rings T r 0.025 | EH_Leather / EH_Steel | mount_body |
| 15 | m_tail | S | (0,0.70,-0.28;0.03)->(0,0.58,-0.33;0.04)->(0,0.45,-0.34;0.014), braided, 2 bronze rings, ember tuft tip C n=5 len 0.05 | EH_Fur / EH_Bronze / EH_Ember | tail_1..3 |
| 16 | m_neck (arched) **S** | S | (0,0.80,0.16;0.095w*0.105d)->(0,0.94,0.22;0.070*0.085)->(0,1.07,0.27;0.052*0.065)->(0,1.17,0.31;0.042*0.052) | EH_Fur | neck_1/neck_2 |
| 17 | m_crinet (neck armour) x6 **S** | B | arched bronze plates following the neck: c along the path at y 0.84/0.92/1.00/1.07/1.13/1.18, widths 0.170/0.150/0.130/0.115/0.100/0.090, each 0.045 tall x depth 0.100->0.075, rd 0.012 e=4, overlap 20%, tilt with the neck, bevel 0.006 (the bronze arch is the brightest line on the piece) | EH_Bronze | neck_1/2 |
| 18 | m_skull | S | (0,1.19,0.30;0.052w*0.060d)->(0,1.07,0.38;0.046*0.058)->(0,0.97,0.44;0.040*0.046)->(0,0.925,0.48;0.036*0.040) (55 deg below horizontal) | EH_Fur | mount_head |
| 19 | m_jowl + cheek M | B | c=(+-0.035,1.06,0.33) s=(0.07,0.12,0.11) e=2 | EH_Fur | mount_head |
| 20 | m_jaw | S | (0,1.04,0.34;0.026)->(0,0.95,0.44;0.022)->(0,0.915,0.47;0.018) | EH_Fur | jaw |
| 21 | m_muzzle + nostrils | B | c=(0,0.93,0.475) s=(0.07,0.06,0.07) e=2 ; two flared nostril recesses r 0.008 depth 0.01 | EH_Fur (dark) | mount_head |
| 22 | m_chanfron (face plate) **S** | E | plane=YZ (y,z) outline: (1.215,0.285)(1.19,0.335)(1.08,0.405)(0.98,0.455)(0.935,0.485)(0.915,0.470)(0.955,0.430)(1.06,0.360)(1.15,0.300) ; thickness x -0.036..0.036, central ridge 0.012, b=0.008, hammered | EH_Bronze | mount_head |
| 23 | m_eye rondels M | B | cones r 0.030 depth 0.020 at (+-0.058,1.10,0.34), eye hole 0.012 | EH_Bronze | mount_head |
| 24 | m_ears + ear covers M **S** | E | plane XY leaf (x,y): (0.030,1.200)(0.075,1.205)(0.064,1.300)(0.040,1.285), thickness z 0.014, tilt forward 10 deg, top y 1.300 ; bronze cover over the front 60% | EH_Bronze / EH_Fur | mount_head |
| 25 | m_eyes M **F2** | B | c=(+-0.052,1.09,0.345) s=(0.016,0.014,0.012) under the rondels | EH_Ember x5 | mount_head |
| 26 | m_mane (flame) **S F1** | S | 12 flame tongues along the crest from (0,1.19,0.25) to (0,0.82,0.13): tongue k: base on the crest, direction up-and-back (swept 30 deg), length 0.18 (at the poll) down to 0.09, radius 0.026->0.004, s-curve noise 0.012 ; **tallest tip y 1.30 (z 0.20, behind the ears)** ; vertex gradient bronze #A8713A -> ember #FF7A1A | EH_Fur / EH_Ember tips | neck_1/2 `~soft` |
| 27 | m_withers embers | S | 5 clumps along the withers len 0.07-0.10 | EH_Fur / EH_Ember tips | mount_chest |
| 28 | m_bridle + reins | S | cheek strap (0.045,0.93,0.46)->(0.04,1.04,0.34)->(0.045,1.15,0.30) r 0.004 ; reins (0.04,0.95,0.44)->(0.08,0.93,0.30)->(0.12,0.90,0.18) r 0.004 (to the rider's hand) | EH_Leather | mount_head / wrist_L |
| 29 | r_boot M | B | c=(0.17,0.50,0.03) s=(0.065,0.09,0.12) rd=0.02 e=3 rot rx 15 | EH_Leather | foot_L/R |
| 30 | r_leg M | S | (0.09,0.82,-0.08;0.050)->(0.17,0.72,0.05;0.042)->(0.17,0.55,0.03;0.032) (thigh to calf, knee forward) | EH_Cloth | thigh/shin |
| 31 | r_greave + knee cop M | S/B | greave S (0.17,0.60,0.04;0.040)->(0.17,0.52,0.02;0.033) ; cop B s=(0.07,0.06,0.05) at (0.17,0.72,0.07) | EH_Bronze | shin/thigh |
| 32 | r_torso | S | (0,0.82,-0.08;0.10*0.08)->(0,0.90,-0.04;0.115*0.085)->(0,0.95,0.02;0.13*0.09) (leaned 55 deg) | EH_Cloth | spine |
| 33 | r_cuirass | E | (-0.105,0.00)(0.105,0.00)(0.125,0.12)(0.105,0.20)(-0.105,0.20)(-0.125,0.12) @0.052..0.074 b=0.009, ridge ; placed along the leaned torso ; backplate mirror | EH_Bronze | chest |
| 34 | r_fur mantle (heavy on L) | S | closed ring r 0.11 at y 0.96 tube 0.032 + L flap B s=(0.12,0.06,0.13) `+noise 0.012` | EH_Fur | chest |
| 35 | r_pauldron L (large) / R (small) | B | L c=(0.17,0.96,0.03) s=(0.115,0.06,0.115) e=3 ; R c=(-0.16,0.955,0.03) s=(0.09,0.05,0.095) e=3 | EH_Bronze | arm_L/R |
| 36 | r_arm M | S | upper (+-0.16,0.95,0.03;0.034)->(+-0.17,0.89,0.10;0.028) ; forearm ->(+-0.12,0.86,0.18;0.022) ; gauntlet cuff B | EH_Cloth / EH_Bronze | arm / hand |
| 37 | r_head | B | c=(0,1.02,0.095) s=(0.075,0.08,0.085) e=2.3 | EH_Leather (skin) | head |
| 38 | r_helm (low) | L | sides=16, `(0.044,0.985)(0.046,1.015)(0.040,1.045)(0.022,1.062)(0,1.068)` + face slit visor E (0.05 x 0.010) at y 1.02 + nasal bar | EH_Bronze / EH_Steel | head |
| 39 | r_helm crest (low) | E | plane=YZ: (1.060,-0.040)(1.095,-0.020)(1.100,0.0)(1.085,0.030)(1.060,0.040) x -0.007..0.007 (top 1.100, never above) | EH_Bronze | head |
| 40 | r_lance shaft **S** | S | (-0.19,0.80,-0.16;0.014)->(-0.19,0.855,0.12;0.013)->(-0.19,0.90,0.40;0.010) | EH_Leather / EH_Bronze rings x3 | weapon |
| 41 | r_lance head | E | leaf blade along the shaft length 0.10, width 0.038, tip at (-0.19,0.915,0.50) b=0.003 + socket collar | EH_Steel | weapon |
| 42 | r_pennon | E | swallow-tail (0,0)(-0.16,0.04)(-0.12,0)(-0.16,-0.04) @0..0.004 on the shaft at z 0.36 (streams to -Z) `~soft` | EH_Cloth | weapon |
| 43 | r_hands M | B | mitten blocks s=(0.04,0.035,0.045) | EH_Leather | wrist_L/R |
(43 parts; budget <= 35k. F1 = mane tips; F2 = horse eyes. Rider has no emissive. The crinet (17), chanfron (22) and ear covers (24) must keep >= 0.006 bevels and roughness 0.30-0.38 so the rim light draws the neck and head as the brightest line.)

## 5. Pose
Standing at rest, weight on the left foreleg, near hind resting (heel up 0.01). Head held collected, 55 deg below horizontal, poll at 1.20, ears forward. Neck arched, flame mane flowing back along it. Rider crouched forward, helm turned 5 deg toward the left; lance couched at the right flank (7.7 deg rising, tip 0.50), left hand on the reins. Tail low, ember tuft 0.45 high. Rider and lance never rise above the horse's poll.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.19, 0.915, 0.50) lance tip | weapon |
| `socket_cast` | (0, 1.30, 0.28) between the ears (ember trail source) | mount_head |
| `socket_impact` | (-0.10, 0.78, 0.62) lance point on landing | mount_body |
| `socket_head` | (0, 1.36, 0.30) above the ears | mount_head |

Extras: `impactTime 1.00`, `strikeRange 0.50`, `attackStyle leap`, `displayName "Emberhold Ashmane Rider"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Hindquarters (body/rump, hind legs) | Forequarters (barrel, fore legs) | Neck / head / mane | Rider / lance | Secondary (tail, caparison). Knee/hock/carpus: hind_lower rx - = hock flexes (hoof forward-up), fore_lower rx + = carpus folds (hoof back-up). Feet are IK-planted unless a beat says "lifts".

**Idle** (loop 3.2 s) - a restless charger
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / lance | Secondary |
|---|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest | rest |
| 1.0 | weight onto L hind: body x +0.006, hind_lower_R rx -4 (R heel rests, 0.01) | mount_chest rx -0.8 (breath); fore_lower_R rx +3 | neck_1 rx +1.5, neck_2 rx +2, mount_head rx +3, ry +4 (nostrils scenting); jaw rx +3 | spine rx +1; wrist_R rz +1 (lance sway) | tail_1/2/3 ry +6/+10/+14 (swish, each 0.10 s later); caparison hem +2 ; mane tongues flicker |
| 1.6 | body y +0.004 | mount_body rx -0.8 | ears twitch (shader) | spine rx +1 | |
| 2.2 | back to centre | fore_upper_L rx -3, fore_lower_L rx +8 (L fore lifts 0.015, paws) | mount_head rx -2, ry -3 | | tail ry -8/-12/-16 |
| 3.2 | rest | rest | rest | rest | rest |

**Move** (loop 0.9 s; steps 0.15 and 0.30) - the 3-beat gallop (canter: R hind, L hind + R fore, L fore, then suspension)
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / lance | Secondary |
|---|---|---|---|---|---|
| 0.00 (beat 1) | R hind lands: hind_upper_R rx -22, hind_lower_R rx -32 (hock flex, coil); body y -0.015 | mount_body rx +3 | neck_1 rx +6, neck_2 rx +8, mount_head rx -4 (head dips) | spine rx +14 (crouched), rider_pelvis y -0.01 | tail rx -6 |
| 0.15 (beat 2, **step**) | L hind lands: hind_upper_L rx -20, hind_lower_L rx -30 ; push-off: hind_upper_R rx +10 | R fore reaches: fore_upper_R rx -35, fore_lower_R rx +10 | neck rx -3 (head rises) | wrist_R holds the lance level (weapon rx +- 2) | caparison hem lags +4 |
| 0.30 (beat 3, **step**) | hind legs extend: hind_upper rx +14, hind_lower rx -10 | L fore (lead) lands: fore_upper_L rx -40, fore_lower_L rx +5; mount_chest rx +4 | neck_1 rx -6, neck_2 rx -8, mount_head rx +4 | | tail rx -12 |
| 0.40-0.75 suspension | body y +0.05, rx -3 ; hind_upper rx +18, hind_lower rx -10 (trail) | all fore: fore_upper rx -20, fore_lower rx +80 (carpus folded) | neck_1 rx -8, neck_2 rx -10, mount_head rx +6 (nods up) ; mane streams (tongues lean back +20 deg) | spine rx +16; pennon streams | tail_1/2/3 rx -14/-20/-26 (streams) |
| 0.9 | = t0 | | | | |

**Attack** (2.0 s; **impact 1.00**; the engine runs the leap arc 0.45-0.95) - rear, leap, lance thrust on landing
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / lance | Secondary |
|---|---|---|---|---|---|
| 0.00-0.40 (io) **rear** | hocks flex to take the weight: hind_lower rx -20, hind_upper rx -10 ; body y +0.06 | mount_body rx -26 (forehand lifts), fore_upper rx -50, fore_lower rx +100 (carpus folded, hooves at chest height) | neck_1 rx -8, mount_head rx -12 ; jaw rx +10 (snort) | spine rx +10 (clings), arm_R rx -50, hand_R rx -10 (lance lifts) | tail_1/2/3 rx -12/-18/-24 ; mane tongues stand up (rx -22 on the mane) |
| 0.40-0.55 hold | body y +0.07 | mount_body rx -32 | mount_head rx -22 (head high, nostrils flare) ; mane blazes, ember trail (engine) | head rx -8 | |
| 0.55-0.88 **leap** (engine arc) | **gather then launch**: 0.55 hind_upper rx -25, hind_lower rx -40 (deep crouch, 0.04 s) -> 0.60 explosive extension hind_upper rx +25, hind_lower rx +10 ; in flight hind legs trail (hind_upper rx +20, hind_lower rx -8) | mount_body rx -26 -> +14 (nose-down) ; fore legs tuck: fore_upper rx -30, fore_lower rx +100, then reach for landing: fore_upper rx -42, fore_lower rx +5 at 0.84 | mount_head rx -22 -> +8 ; neck_2 rx +10 (stretches toward the target) ; mane streams back | spine rx +10 ; arm_R rx -35 / hand_R rx +90 (net lance pitch +55 couched) | tail streams rx -26 |
| 0.88-1.00 **strike** (0.12 s snap; hind end leads 0.04 s) | landing impact: body y -0.04 ; hind_upper rx -12, hind_lower rx -20 absorb | mount_body rx +14 -> +22, z +0.15 ; fore hooves plant (IK contact) | mount_head rx +8 | arm_R rx -35 -> -20 ; hand_R rx +90 -> +105 (lance thrust, net +85 at impact) ; spine rx +16 | caparison whip +20 |
| 1.00 | **impact**: hooves plant; lance tip at `socket_impact` | | | | |
| 1.00-1.15 hold | squash mount_body y -0.04 | | | | mane top rx +20 whip |
| 1.15-2.00 (io) | to rest | mount_body rx 0 with a -4 overshoot at 1.5 | to rest | lance lowers to the carry | tail settles |

**HitReact** (0.45 s)
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / lance | Secondary |
|---|---|---|---|---|---|
| 0.10 | hind_upper rx +4, hind_lower rx -8 (hocks sit); body rx -9, z -0.07 | fore_upper rx +10 (forehand jolts) | mount_head rx -16 (head throws up), neck_1 rx -8 ; jaw rx +18 (whinny) | spine rx -10 ; arm_R rx +12 | mane rx +16 ; tail +10 |
| 0.45 | body rx -3 (settles at 60%) | | mount_head rx -6 | | |

**Victory** (1.8 s, ends held) - rears into a heraldic levade, lance high
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / lance | Secondary |
|---|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest | |
| 0.6 (bk) | hocks flex then straighten: hind_lower rx -25 -> 0 ; body y +0.05 | mount_body rx -22 ; fore_upper rx -50, fore_lower rx +95 (pawing the air) | mount_head rx -14, neck_1 rx -8, neck_2 rx -10 ; jaw rx +10 ; mane blazes | arm_R rx -150, hand_R rx -25 (lance raised high) ; head rx -8 | tail rx -20 |
| 1.8 | hold | mount_body rx -14 (settling), lance still raised | | | |

**Taunt** (1.3 s, once) - paws the ground twice and tosses its head at the enemy king
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / lance | Secondary |
|---|---|---|---|---|---|
| 0.00-0.30 | weight back: hind_lower rx -10 ; body rx -2 | fore_upper_R rx -35, fore_lower_R rx +55 (R fore lifts 0.08) | neck_2 rx -6, mount_head rx -10 | arm_R rx -45 (lance dips toward the foe), tip at the target | mane flares |
| 0.30-0.45 (snap) | | R fore scrapes back: fore_upper_R rx -35 -> +5, fore_lower_R rx +55 -> +10 (hoof drags a spark line) | head toss: mount_head rx -20, jaw rx +14 | | mane tongues +25 |
| 0.45-0.80 | | second scrape at 0.70 | mount_head rx +4 | pennon snaps | tail ry +12 |
| 0.80-1.30 | settle | fore returns, IK-plant | head level | lance returns | |

**Surrender** (2.2 s, once, holds the last pose) - the horse kneels; the rider drops the lance
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / lance | Secondary |
|---|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.04 | fore_upper rx +6 | mount_head rx -12 | wrist_R opens (rx +25) | |
| 0.30-0.55 | | | | **`weapon` (lance) released at 0.45**: topples forward, bounces twice, lies on the plinth ahead of the horse | pennon flutters down |
| 0.55-1.35 (io) | haunches stay up: hind_lower rx -10, body rx +8 | **both forelegs kneel**: fore_upper rx -50, fore_lower rx +120, fore_hoof rx +10 ; mount_chest y -0.18 (knees on the plinth) | neck_1 rx +20, neck_2 rx +25, mount_head rx +35 (head bowed, muzzle low) ; jaw rx +6 ; mane tongues droop | spine rx +22 (the rider slumps), rider_pelvis y -0.02 | tail_1/2/3 rx +10/+14/+18 (hangs) |
| 1.35-2.20 | hold | hold | hold, slow breath | head rx +28, arm_L/R rx +10, wrist palms up | caparison settles, mane flames dim 40% |

## 8. Fragments (30)
Coarse: horse torso 6 slabs (fur-coat stone with ember interior), **head 3 (chanfron plate keeps its ridge; the ears are whole bronze pieces), crinet 3 bronze arches**, barding plates 4 bronze slabs, rider cuirass 2 + helm 1 + pauldrons 2, lance shaft 2 + head 1, legs 6 chunks, saddle/blanket 2. Chunky bronze/stone, glowing `EH_Interior`; the mane breaks into 4 ember puffs (particles, no mesh).

## 9. Readability
- **Identity cue**: arched barded war-horse neck + chanfroned head with flame mane; rider crouched and secondary.
- vs `rime_knight`: warm bronze-armoured horse with an opaque dark coat, flame mane and a forward lance vs a bone-white skeletal steed with ribs, crystal mane and a rearward glaive; mean luma 0.40-0.50 vs <= 0.15 with a bright skull.
- vs other roles: only 4-legged, longest silhouette (0.80 deep); the neck/head column rising to 1.30 is unique. Everything above 1.10 is horse; top 1.30 is taller than the rook (1.20), shorter than the bishop (1.40).
- Silhouette tests (README "Recognisability rules"): from all 8 azimuths (45 deg steps) the horse head+neck must hold >= 60% of the silhouette area above y 0.95; no rider or weapon pixel above the poll (1.20); top-down = a teardrop with the head/neck as the narrow end.
