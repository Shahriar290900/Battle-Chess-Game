# rime_knight - Rime Gravewind Rider

## 1. Identity
- **Name**: Rime Gravewind Rider. **Concept**: a **skeletal frost steed**: a gaunt war-horse of bone-white ice with an exposed rib cage lit from inside, a skull in a half-chanfron of black obsidian, **glowing cyan eyes** and a **mane of crystal shards** swept along its arched neck. A skeletal rider in wired obsidian plate **crouches low over its neck**; his hooked glaive is carried reversed, blade trailing over the croup, so it never competes with the head. The steed replaces the old ice ram.
- **Identity cue (the horse head and arched neck)**: the neck arches from the withers (0.80) to the poll (1.20) in a 0.40 rise; the **bone-white skull is the brightest shape on the piece** (value >= 0.85) against black obsidian and a dark ribcage, with two cyan eyes (the F1 focal point) and a half-chanfron of black obsidian across the forehead for a hard value edge. Crystal mane shards rise to 1.30 (the top of the piece) behind two ice-shard ears. **Everything above y 1.10 is horse** from any azimuth (rider skull/helm tops out at 1.07).
- **Silhouette plan** (+20% on the old signature): side view = tall S-curve neck, bright wedge skull with an open jaw, crystal comb along the crest, a transparent ribcage under a long spine, the rider a low dark hump, the glaive a thin diagonal behind; front view = a bright column of skull and crystal mane with the rider's shoulders behind it; rear view = head and mane rise 0.23 above the rider's helm; top-down = a long teardrop with the head as the narrow end.
- Steed faces +Z. Mount uses the quadruped template; the rider uses the humanoid template, rooted on `top`.

## 2. Dimensions (total 1.30)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Hooves / lower legs | 0.22-0.45 | thin, gaunt |
| Upper legs | 0.40-0.70 | hock at 0.44 (z -0.31) |
| Rib cage / back | 0.46-0.78 | z -0.28..0.14, 9 rib pairs |
| Withers | 0.80 | at z 0.12 |
| Arched neck | 0.78-1.20 | base (z 0.16) -> poll (0,1.20,0.31) |
| Skull | 0.915-1.215 | length 0.30 at 55 deg ; muzzle (0,0.925,0.48) ; jaw hangs open 12 deg |
| Ear shards | 1.20-1.285 | |
| Crystal mane | 0.82-1.30 | 11 crystals ; tallest tip 1.30 behind the ears |
| Saddle seat | 0.80 | |
| Rider (crouched) | 0.82-1.10 | skull top 1.06, half-helm 1.07 |
| Glaive | 0.76-1.18 | butt (-0.17,0.76,0.20), hook tip (-0.12,1.18,-0.36) |
Envelope: 0.46 wide x 0.80 deep (z -0.32 tail .. 0.48 muzzle; the glaive hook at z -0.36 is the weapon exception).

## 3. Rig (quadruped template + humanoid rider)
`quadruped_rig(JQ)` for the mount; `humanoid_rig(JR, weapon=(-0.15,0.92,0.00), pelvis_name="rider_pelvis")` for the rider, `rider_pelvis` re-parented under `top` (the seat). Contract bones: `root, body` (= rump), `top` (= seat), `mount_body, mount_head`, rider `spine, head, arm_*, hand_*`.

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
| pelvis (`rider_pelvis`) | (0,0.82,-0.08) | | elbow_L | (0.16,0.89,0.09) |
| spine | (0,0.87,-0.05) | | wrist_L (reins) | (0.12,0.86,0.17) |
| chest | (0,0.94,0.01) | | wrist_R (glaive grip, explicit) | (-0.15,0.86,0.10) |
| neck | (0,0.99,0.065) | | hip_L | (0.09,0.82,-0.08) |
| head | (0,1.00,0.09) | | knee_L | (0.16,0.72,0.05) |
| clavicle_L | (0.06,0.96,0.03) | | ankle_L | (0.16,0.52,0.02) |
| shoulder_L | (0.15,0.95,0.03) | | toe_L | (0.16,0.49,0.09) |
| weapon (glaive centre) | (-0.15,0.92,0.00) | | | |

**Binding (authoritative)**: 1-3, 5 -> `mount_body` (ridge dips into `mount_chest` at the withers); 4 -> `mount_body`; 6 -> `mount_body` (`~soft` `body`); 7 -> `fore_upper` (-> y 0.45) / `fore_lower` (0.45 -> 0.30) / `fore_hoof`; 8 -> `hind_upper` / `hind_lower` / `hind_hoof`; 9 -> `*_hoof`; 10 -> `*_lower`/`*_upper` at the joints; 11 -> `tail_1..3`; 12, 13 -> `neck_1`/`neck_2` (split y 0.95, `~soft`); 14-17, 19, 22 -> `mount_head` (18 jaw + teeth -> `jaw`); 20, 21 mane -> `neck_1`/`neck_2` `~soft`; 23 -> `mount_body`; 24 -> `mount_chest`; 25 -> `thigh`/`shin`; 26 -> `shin`/`thigh`; 27 -> `foot`; 28 -> `rider_pelvis`; 29 -> `spine`/`chest`; 30 -> `chest`; 31 -> `arm_L/R`; 32 -> `arm`/`hand` (forearm); 33 -> `wrist`; 34-36 -> `head`; 37 -> `chest` `~soft` `spine`; 38-40 -> `weapon`.

## 4. Part list
Pedestal parts per README section 2. `m_` = mount, `r_` = rider. World rest-pose coordinates (x = width, y = up, z = forward).

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | m_spine ridge **S** | S | (0,0.70,-0.28;0.026)->(0,0.74,-0.08;0.028)->(0,0.80,0.12;0.030) sec=6 ; vertebra knobs B r 0.032 x10 | RH_Ice | mount_body |
| 2 | m_ribs x9 pairs M | S | rib k at z=-0.22+0.04k (k=0..8): (0,0.70,z;0.012)->(0.10,0.70,z;0.012)->(0.16,0.60,z+0.01;0.011)->(0.12,0.48,z+0.02;0.007) sec=6 (ribs are 0.024 wide, spaced 0.04: see-through) | RH_Ice | mount_body |
| 3 | m_sternum | S | (0,0.47,-0.20;0.012)->(0,0.46,0.12;0.012) | RH_Ice | mount_body |
| 4 | m_frost-light core **F2** | B | c=(0,0.60,-0.06) s=(0.20,0.16,0.34) e=2 `+noise 0.01` (seen through the rib gaps) | RH_Glow x3 | mount_body |
| 5 | m_pelvis | B | c=(0,0.64,-0.25) s=(0.22,0.14,0.14) rd=0.03 e=3 | RH_Ice (cloudy) | mount_body |
| 6 | m_pelt scraps x3 | E | torn patches on haunch/shoulder, jagged edges, e.g. (0.10,0.70)(0.17,0.62)(0.14,0.50)(0.09,0.58)@z-0.20 curved | RH_Cloth | mount_body |
| 7 | m_foreleg M | S | (0.10,0.70,0.10;0.036)->(0.11,0.45,0.15;0.024)->(0.11,0.30,0.16;0.018)->(0.11,0.22,0.17;0.022) (gaunt; joint knobs B r 0.030 at the carpus) | RH_Ice | fore_upper/lower/hoof |
| 8 | m_hindleg M | S | (0.10,0.65,-0.22;0.042)->(0.11,0.44,-0.31;0.030)->(0.11,0.29,-0.27;0.020)->(0.11,0.22,-0.24;0.022) (joint knobs at the hock) | RH_Ice | hind_upper/lower/hoof |
| 9 | m_hooves x4 | B | c=(+-0.11,0.236,0.17) and (+-0.11,0.236,-0.24), s=(0.06,0.03,0.07) rd=0.01 e=3, frost rim | RH_Obsidian | *_hoof |
| 10 | m_leg joint spurs x4 | C | at carpus/hock: n=2 len 0.04-0.06 pointing back | RH_Ice | *_lower |
| 11 | m_tail | S | (0,0.70,-0.28;0.018)->(0,0.58,-0.33;0.014)->(0,0.45,-0.34;0.004) bony chain with 5 ice shards | RH_Ice | tail_1..3 |
| 12 | m_neck core (arched) **S** | S | (0,0.80,0.16;0.060w*0.070d)->(0,0.94,0.22;0.048*0.056)->(0,1.07,0.27;0.040*0.046)->(0,1.17,0.31;0.034*0.040) ; frozen sinew sheath S r +0.016 (translucent), giving a 0.11-wide neck at the base | RH_Ice (cloudy) | neck_1/neck_2 |
| 13 | m_neck vertebrae x7 + spines | B + C | discs r 0.030 along the neck, each with a spinous spike len 0.04-0.07 r 0.012 | RH_Frost | neck_1/2 |
| 14 | m_skull **S** | S | (0,1.19,0.30;0.050w*0.056d)->(0,1.07,0.38;0.044*0.054)->(0,0.97,0.44;0.036*0.040)->(0,0.925,0.48;0.032*0.036) (55 deg below horizontal, bone white) | RH_Frost (bone-white, value >= 0.85) | mount_head |
| 15 | m_zygomatic arch + sockets M | S + cut | arch S (+-0.046,1.10,0.30)->(+-0.050,1.09,0.36) r 0.008 ; eye socket recess depth 0.014 r 0.020 at (+-0.050,1.09,0.345) | RH_Frost | mount_head |
| 16 | m_half-chanfron **S** | E | plane=YZ (y,z): (1.215,0.285)(1.19,0.335)(1.10,0.395)(1.03,0.425)(1.06,0.360)(1.15,0.300) thickness x -0.034..0.034 b=0.006, silver wire edge r 0.004 (black plate on the white skull = hard value edge) | RH_Obsidian / RH_Silver | mount_head |
| 17 | m_eyes M **F1** | B | c=(+-0.050,1.09,0.345) s=(0.020,0.016,0.014) deep in the sockets | RH_Glow x6 | mount_head |
| 18 | m_jaw + teeth | S + C | jaw S (0,1.04,0.34;0.020)->(0,0.95,0.44;0.016)->(0,0.915,0.47;0.012) hanging open 12 deg ; 8 teeth C len 0.015 | RH_Frost | jaw |
| 19 | m_ears M | C | n=1 len 0.09 r 0.022 at (+-0.040,1.20,0.285) up=(+-0.2,1,-0.2) ; tip y 1.285 | RH_Ice | mount_head |
| 20 | m_mane crystals x11 **S** | C | along the crest from (0,1.20,0.26) to (0,0.82,0.13), spacing 0.04: base r 0.020-0.030, length 0.17 (at the poll) down to 0.08, swept back 35 deg ; **tallest tip y 1.30 (z 0.20)** ; translucent, value >= 0.75 | RH_Ice | neck_1/2 `~soft` |
| 21 | m_mane glints | texture | cyan core lines in 4 crystals, <= 3% area | RH_Glow x3 | neck_1/2 |
| 22 | m_bridle + chain M | S | (0.045,0.93,0.46)->(0.04,1.04,0.34)->(0.045,1.15,0.30) r 0.004 + links ; reins to the rider's hand | RH_Silver | mount_head / wrist_L |
| 23 | m_saddle (rotted) | B | c=(0,0.795,-0.06) s=(0.17,0.035,0.20) rd=0.02 e=3 + tattered blanket E over the haunch `~soft` | RH_Armour / RH_Cloth | mount_body |
| 24 | m_peytral scraps | E | 3 broken obsidian lames across the chest (+-0.13,0.58..0.74) @ z 0.14..0.16 b=0.006, ribs visible behind | RH_Obsidian | mount_chest |
| 25 | r_leg bones M | S | (0.09,0.82,-0.08;0.022)->(0.16,0.72,0.05;0.018)->(0.16,0.55,0.03;0.014) | RH_Silver (bone wire) | thigh/shin |
| 26 | r_greave + knee plate M | E/B | greave plane=YZ (y,z): (0.60,0.01)(0.68,0.05)(0.69,0.08)(0.61,0.05) x +-0.150..0.165 b=0.005 ; knee B s=(0.05,0.05,0.04) at (0.16,0.72,0.07) | RH_Obsidian | shin/thigh |
| 27 | r_boot + stirrup M | B/S | boot s=(0.05,0.06,0.10) at (0.16,0.50,0.03) ; stirrup S ring r 0.022 | RH_Obsidian / RH_Silver | foot |
| 28 | r_pelvis | B | c=(0,0.82,-0.08) s=(0.15,0.07,0.10) rd=0.02 | RH_Obsidian | rider_pelvis |
| 29 | r_spine + rib cage | S | spine (0,0.84,-0.07;0.014)->(0,0.95,0.02;0.012) ; 5 rib pairs arcs radius 0.075, r 0.007 along the leaned torso | RH_Silver / RH_Ice | spine/chest |
| 30 | r_breastplate (half, broken) | E | jagged half plate along the leaned chest, b=0.007, jagged right edge | RH_Obsidian | chest |
| 31 | r_pauldron L (large spiked) / R (bare bone) | B/C | L c=(0.155,0.955,0.03) s=(0.10,0.05,0.10) e=3 + 3 ice spikes len 0.05-0.08 (tops <= 1.03) ; R B s=(0.05,0.03,0.05) | RH_Obsidian / RH_Ice | arm_L/R |
| 32 | r_arm M | S | upper (+-0.15,0.95,0.03;0.016)->(+-0.16,0.89,0.09;0.014) ; forearm ->(+-0.12,0.86,0.17;0.012) ; vambrace E 0.05 x 0.05 | RH_Silver / RH_Obsidian | arm / hand |
| 33 | r_hand M | S | 4 bony finger tubes r 0.004 + thumb on palm B s=(0.035,0.03,0.035) | RH_Silver | wrist |
| 34 | r_skull | B | c=(0,1.02,0.095) s=(0.072,0.08,0.082) e=2.2 ; jaw wedge, 2 eye-socket recesses r 0.014 | RH_Frost mixed 70% obsidian dust (dimmer than the steed's skull) | head |
| 35 | r_half-helm | L | sides=12, `(0.044,0.990)(0.046,1.020)(0.040,1.048)(0.020,1.064)(0,1.070)` (top 1.07, open face, no crown spikes: nothing reads as a crown) | RH_Obsidian | head |
| 36 | r_eye lights M (dim) | B | s=(0.013,0.009,0.009) at (+-0.022,1.03,0.130) | RH_Glow x3 | head |
| 37 | r_cloak scraps | E | torn cloak down the back: (0,0.98)(0.10,0.92)(0.14,0.76)(0.08,0.62)(0.02,0.68)(-0.04,0.60)(-0.12,0.74)(-0.09,0.92) @ z -0.10..-0.094 jagged hem `~soft` | RH_Cloth | chest |
| 38 | r_glaive haft **S** | S | (-0.17,0.76,0.20;0.015)->(-0.15,0.86,0.10;0.014)->(-0.13,1.00,-0.10;0.013)->(-0.12,1.08,-0.26;0.012) with 4 silver wire wraps r +0.003 (carried reversed: rises toward the rear) | RH_Obsidian / RH_Silver | weapon |
| 39 | r_glaive blade (hooked) **S** | E | plane=YZ (y,z): (1.06,-0.25)(1.12,-0.28)(1.18,-0.34)[tip](1.15,-0.31)(1.10,-0.27)(1.05,-0.24) thickness x -0.14..-0.12 b=0.004 ; back spike (1.12,-0.20) | RH_Ice | weapon |
| 40 | r_glaive butt cap | C | 1 prism len 0.06 at (-0.17,0.76,0.20) pointing forward-down | RH_Ice | weapon |
(40 parts; budget <= 35k. F1 = steed eyes (the rider's lights are dim accents); F2 = rib-cage frost-light. Crown spikes removed: the rider must never read as a crowned figure.)

## 5. Pose
The steed stands square, head collected 55 deg below horizontal with the jaw open 12 deg, poll at 1.20, ice-shard ears forward; the crystal mane swept back along the arched neck. Rider crouched forward, skull turned 5 deg toward the left; glaive held reversed (blade trailing over the croup, tip y 1.18, below the poll). Tattered cloak hangs behind the saddle.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.12, 1.14, -0.30) glaive hook mid | weapon |
| `socket_cast` | (0, 0.60, 0.0) rib-light core | mount_body |
| `socket_impact` | (-0.08, 0.76, 0.62) bite/glaive blow | mount_body |
| `socket_head` | (0, 1.36, 0.30) above the ears | mount_head |

Extras: `impactTime 1.00`, `strikeRange 0.50`, `attackStyle leap`, `displayName "Rime Gravewind Rider"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Hindquarters (body/rump, hind legs) | Forequarters (barrel, fore legs) | Neck / head / mane | Rider / glaive | Secondary (tail, pelt, rib-light). hind_lower rx - = hock flexes; fore_lower rx + = carpus folds. Feet IK-planted unless a beat says "lifts". The steed moves with a faint stiff-jointed rattle (small high-frequency rz on the leg bones in Idle/Move, +-0.8 deg).

**Idle** (loop 3.4 s) - restless, cold
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / glaive | Secondary |
|---|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest | rest |
| 1.1 | body x +0.005, hind_lower_L rx -4 (shifts weight) | mount_chest rx -0.8 ; fore_lower_R rx +3 | neck_1 rx +2, neck_2 rx +3, mount_head rx +4, ry -5 (scenting) ; jaw rx +5 (opens a little, teeth show) | spine rx +1 ; wrist_R rz +1.5 (glaive sway) | tail_1/2/3 ry +5/+9/+13 ; rib-light pulse +15% |
| 2.3 | | mount_body rx -1 | mount_head ry +4, rx -2 ; mane crystals chime (rz +- 2) | head ry +4 (skull turns) | tail ry -7/-11/-15 |
| 3.4 | rest | rest | rest | rest | rest |

**Move** (loop 0.9 s; steps 0.15 and 0.30) - the 3-beat gallop (R hind, L hind + R fore, L fore, suspension)
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / glaive | Secondary |
|---|---|---|---|---|---|
| 0.00 (beat 1) | R hind lands: hind_upper_R rx -22, hind_lower_R rx -32 ; body y -0.015 | mount_body rx +4 | neck_1 rx +6, neck_2 rx +8, mount_head rx -4 ; jaw rx +4 | spine rx +14 (crouched) | pelt scraps rx +6 |
| 0.15 (beat 2, **step**) | L hind lands: hind_upper_L rx -20, hind_lower_L rx -30 | R fore reaches: fore_upper_R rx -35, fore_lower_R rx +10 | neck rx -3 | glaive steady (wrist_R rz +- 2) | |
| 0.30 (beat 3, **step**) | hind_upper rx +14, hind_lower rx -10 (extend) | L fore lands: fore_upper_L rx -40, fore_lower_L rx +5 ; mount_chest rx +4 | neck_1 rx -6, neck_2 rx -8, mount_head rx +4 | | tail rx -12 |
| 0.40-0.75 suspension | body y +0.05, rx -3 ; hind_upper rx +18, hind_lower rx -10 | fore_upper rx -20, fore_lower rx +80 | neck_1 rx -8, neck_2 rx -10, mount_head rx +6 ; crystal mane streams back +20 deg | spine rx +16 ; cloak streams | tail_1/2/3 rx -14/-20/-26 ; rib-light flickers |
| 0.9 | = t0 | | | | |

**Attack** (2.0 s; **impact 1.00**; the engine runs the leap arc 0.45-0.95) - rear, leap, bite then glaive
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / glaive | Secondary |
|---|---|---|---|---|---|
| 0.00-0.40 (io) **rear** | hocks flex: hind_lower rx -20, hind_upper rx -10 ; body y +0.05 | mount_body rx -22 ; fore_upper rx -50, fore_lower rx +100 (hooves at chest height) | mount_head rx -24, neck_1 rx -8 ; jaw rx +14 (skull screams) | arm_R rx -45, hand_R rx -45 (glaive swings back over the shoulder, net -90) ; body rx +8 | pelt rx +16 ; mane crystals chime |
| 0.40-0.55 hold | body y +0.06 | mount_body rx -26 | mount_head rx -30 ; head (rider) rx -8 ; eyes flare | | rib-light +40% |
| 0.55-0.85 **leap** (engine arc) | **gather then launch**: 0.55 hind_upper rx -25, hind_lower rx -40 (crouch) -> 0.60 hind_upper rx +25, hind_lower rx +10 (push) ; trail hind_upper rx +20, hind_lower rx -8 | mount_body rx -22 -> +10 ; fore legs tuck fore_upper rx -30, fore_lower rx +100, then reach fore_upper rx -42, fore_lower rx +5 at 0.84 | mount_head rx -30 -> -5 ; neck_2 rx +10 (stretches at the target) ; mane streams | arm_R rx -45 -> -55 ; spine rx +5 | tail streams rx -26 |
| 0.85-0.93 **bite** (0.08 s snap) | landing prep: hind_upper rx -10 | mount_body rx +10 -> +18, z +0.10 | mount_head rx -5 -> +42, jaw rx +25 -> 0 (the jaws snap shut) ; engine ice crack at 0.93 | | |
| 0.93-1.00 **glaive strike** (0.07 s snap, impact at 1.00; hind end leads 0.04 s) | landing: body y -0.04 ; hind_lower rx -20 absorbs | fore hooves plant (IK contact) | mount_head rx +42 held | arm_R rx -55 -> -30 ; hand_R rx -45 -> +75 (net haft pitch from -100 to +45: the reversed glaive flips forward and cuts over the neck) ; spine rx +18 ; body z +0.12 | cloak whip +20 |
| 1.00 | **impact**: glaive hook on `socket_impact` | | | | |
| 1.00-1.15 hold | landing squash y -0.03 | | | | |
| 1.15-2.00 (io) | to rest | to rest, -4 overshoot at 1.5 | to rest | glaive returns reversed | rib-light settles |

**HitReact** (0.45 s)
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / glaive | Secondary |
|---|---|---|---|---|---|
| 0.10 | body rx -10, z -0.07 ; hind_lower rx -8 | fore_upper rx +10 | mount_head rx -22 ; neck_1 rx -8 ; jaw rx +20 (screech) | spine rx -10 ; head rx -14 ; arm_R rx +10 | crystals shed 3 shards (VFX) ; rib-light flickers |
| 0.45 | body rx -3 | | mount_head rx -8 | | |

**Victory** (1.6 s, ends held) - rears, glaive overhead
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / glaive | Secondary |
|---|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest | |
| 0.6 | hind_lower rx -25 -> 0 ; body y +0.05 | mount_body rx -20 ; fore_upper rx -50, fore_lower rx +95 | mount_head rx -22 ; jaw rx +16 ; eyes flare | arm_R rx -150, hand_R rx +10 (glaive overhead, vertical) ; head rx -10 | tail rx -20 ; mane crystals ring |
| 1.6 | hold | rear held (mount_body rx -16) | | | |

**Taunt** (1.3 s, once) - a head-toss with rattling jaws, hoof scrape, the glaive twirled
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / glaive | Secondary |
|---|---|---|---|---|---|
| 0.00-0.30 | weight back: hind_lower rx -10 | fore_upper_R rx -35, fore_lower_R rx +55 (R fore lifts 0.08) | mount_head rx -12 | arm_R rx -60 (glaive lifts off the croup) | crystals chime |
| 0.30-0.45 (snap) | | R fore scrapes back: fore_upper_R rx -35 -> +5, fore_lower_R rx +55 -> +10 (frost sparks) | head toss mount_head rx -22 ; jaw rx +25 -> 0 -> +25 -> 0 -> +25 (three rattling snaps, 0.07 s each) | glaive spins a half-turn about the haft (wrist_R rz +180 over 0.30 s) | rib-light +40% |
| 0.45-0.80 | | second scrape at 0.70 | mount_head rx +4 | | |
| 0.80-1.30 | settle | IK-plant | head level | glaive returns | |

**Surrender** (2.2 s, once, holds the last pose) - the steed kneels, the rider lets go of the glaive
| t | Hindquarters | Forequarters | Neck / head / mane | Rider / glaive | Secondary |
|---|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.04 | fore_upper rx +6 | mount_head rx -14 ; jaw rx +20 | wrist_R opens (rx +25) | rib-light flickers |
| 0.30-0.55 | | | | **`weapon` (glaive) released at 0.45**: slides off the croup, bounces twice, lies behind the steed | |
| 0.55-1.35 (io) | haunches up: hind_lower rx -10, body rx +8 | **both forelegs kneel**: fore_upper rx -50, fore_lower rx +120 ; mount_chest y -0.18 | neck_1 rx +20, neck_2 rx +25, mount_head rx +35 (skull lowered), jaw rx +8 ; crystal mane droops, dims | spine rx +22 (the rider collapses forward) | tail rx +10/+14/+18 |
| 1.35-2.20 | hold | hold | hold ; eyes dim to 30% | head rx +28 ; arms hang, palms up | rib-light fades to 30% |

## 8. Fragments (30)
Sharp: 8 steed body shards (4 ribs break into thin curved spikes), **head 3 (the bone-white skull breaks into a muzzle wedge, a brow piece with the obsidian half-chanfron attached, and the jaw), mane 4 (whole crystals, glowing tips)**, 3 neck shards, 5 rider bone/obsidian shards (flat 3-5 sided), glaive hook as 1 curved blade piece + 2 haft splinters, 4 saddle/cloak splinters. Interior pale cracked ice; the rib light flashes cyan for 0.3 s.

## 9. Readability
- **Identity cue**: bone-white skeletal horse head with glowing eyes on an arched neck with a crystal mane; see-through ribs; rider dark and low.
- vs `emberhold_knight`: skeletal, see-through, bone-white skull and cyan glow vs a warm bronze-barded horse with a flame mane; reversed glaive trailing vs a forward lance; mean luma <= 0.15 with a bright skull and mane vs 0.40-0.50.
- vs other roles: four legs and 0.80 depth mark the knight; the neck/head column rising to 1.30 is unique. Everything above 1.10 is horse; top 1.30 is taller than the rook (1.20), shorter than the bishop staff (1.40).
- Silhouette tests (README "Recognisability rules"): from all 8 azimuths the horse head+neck holds >= 60% of the silhouette area above y 0.95; no rider or weapon pixel above the poll (1.20); top-down = a teardrop with the skull as the narrow end.
