# rime_knight - Rime Gravewind Rider

## 1. Identity
- **Name**: Rime Gravewind Rider. **Concept**: a skeletal rider in wired obsidian plate on a gaunt ice ram whose rib cage is hollow and lit by a cold inner glow; a hooked glaive stands upright at its side.
- **Signature shape**: the ram's two spiral crystal horns (curled side horns, plus twin rising crystal spirals to y 1.08; ~15% oversize). Silhouette = lean, angular, tall at the front, with a vertical glaive hook rising behind the horns.
- Mount faces +Z.

## 2. Dimensions (total 1.30)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Hooves / lower legs | 0.22-0.38 | thin |
| Upper legs | 0.38-0.60 | |
| Rib cage / back | 0.48-0.74 | z -0.28..0.16 |
| Neck | 0.70-0.84 | low, forward |
| Ram head | 0.72-0.92 | muzzle z 0.52 |
| Spiral horns | 0.70-1.08 | span x +-0.24 |
| Saddle seat | 0.74 | |
| Rider torso (bones) | 0.76-1.00 | |
| Rider skull | 1.00-1.09 | head 0.09 |
| Skull crown spikes | 1.09-1.15 | |
| Glaive | 0.62-1.30 | hook tip 1.30 |
Envelope: 0.52 wide x 0.80 deep (z -0.30..0.52).

## 3. Bone pivots (x, y, z)
root (0,0,0) | mount_body (0,0.58,0) | mount_head (0,0.72,0.16) | body (0,0.75,-0.05) | spine (0,0.80,-0.05) | head (0,1.00,-0.04) | top (0,0.78,-0.10) | arm_L (0.095,0.98,-0.05) | hand_L (0.105,0.90,-0.01) | arm_R (-0.095,0.98,-0.05) | hand_R (-0.11,0.90,0.00)

## 4. Part list
Pedestal parts per README section 2. `m_` = mount, `r_` = rider.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | m_spine ridge **S** | S | (0,0.69,-0.28;0.026)->(0,0.72,-0.10;0.028)->(0,0.72,0.14;0.030) sec=6 knobs (vertebra B r 0.032 x9) | RH_Ice | mount_body |
| 2 | m_ribs x9 pairs M | S | rib k at z=-0.24+0.046k: (0,0.70,z;0.011)->(0.09,0.72,z;0.011)->(0.15,0.62,z+0.01;0.010)->(0.12,0.50,z+0.02;0.007) sec=6 | RH_Ice | mount_body |
| 3 | m_sternum | S | (0,0.47,-0.20;0.012)->(0,0.46,0.14;0.012) | RH_Ice | mount_body |
| 4 | m_frost-light core **F2** | B | c=(0,0.60,-0.04) s=(0.20,0.14,0.34) e=2 `+noise 0.01` (seen through the rib gaps) | RH_Glow x3 | mount_body |
| 5 | m_pelvis | B | c=(0,0.64,-0.25) s=(0.22,0.14,0.14) rd=0.03 e=3 | RH_Ice (cloudy) | mount_body |
| 6 | m_pelt scraps x3 | E | torn patches on haunch/shoulder, jagged edges, e.g. (0.10,0.70)(0.17,0.62)(0.14,0.50)(0.09,0.58)@z-0.20 curved | RH_Cloth | mount_body |
| 7 | m_foreleg M | S | (0.095,0.60,0.12;0.036)->(0.10,0.46,0.15;0.024)->(0.105,0.34,0.17;0.018)->(0.105,0.25,0.18;0.022) (gaunt) | RH_Ice | mount_body |
| 8 | m_hindleg M | S | (0.10,0.62,-0.22;0.042)->(0.115,0.47,-0.15;0.030)->(0.105,0.35,-0.25;0.020)->(0.105,0.25,-0.23;0.022) | RH_Ice | mount_body |
| 9 | m_hooves x4 | C | cloven hooves: base on plinth, 2 prisms each len 0.04, r 0.016 ; frost rim | RH_Obsidian | mount_body |
| 10 | m_leg joint spurs x4 | C | at knee/hock: n=2 len 0.04-0.06 pointing back | RH_Ice | mount_body |
| 11 | m_tail | S | (0,0.66,-0.30;0.018)->(0,0.56,-0.40;0.014)->(0,0.42,-0.42;0.004) bony chain with 3 ice shards | RH_Ice | mount_body |
| 12 | m_neck | S | (0,0.69,0.14;0.060)->(0,0.76,0.25;0.046)->(0,0.80,0.34;0.040) low-slung | RH_Ice | mount_head |
| 13 | m_neck vertebrae spikes x5 | C | along the crest: len 0.04-0.07, r 0.010 | RH_Ice | mount_head |
| 14 | m_skull | S | (0,0.82,0.34;0.048*0.052)->(0,0.80,0.43;0.040*0.046)->(0,0.76,0.52;0.026*0.030) ram snout | RH_Ice | mount_head |
| 15 | m_brow + cheek plates M | E | plane=YZ (y,z): (0.84,0.36)(0.86,0.44)(0.80,0.50)(0.78,0.40) x +-0.040..0.050 b=0.006 | RH_Obsidian | mount_head |
| 16 | m_eyes M **F1** | B | c=(+-0.040,0.835,0.43) s=(0.016,0.010,0.012) | RH_Glow x5 | mount_head |
| 17 | m_jaw | S | (0,0.74,0.40;0.020)->(0,0.71,0.50;0.014) hanging slightly open | RH_Ice | mount_head |
| 18 | m_curled horn M **S** | S | sec=6 twist 2 turns: (0.045,0.86,0.33;0.034)->(0.125,0.90,0.28;0.032)->(0.200,0.84,0.30;0.028)->(0.215,0.74,0.38;0.022)->(0.165,0.69,0.46;0.014)->(0.100,0.72,0.47;0.006) | RH_Ice | mount_head |
| 19 | m_horn spiral ridges M | S | helical rib r 0.006 around the horn, 5 turns | RH_Frost | mount_head |
| 20 | m_rising crystal spiral M **S** | S | twin spiral: (0.04,0.89,0.32;0.020)->(0.075,0.95,0.31;0.018)->(0.060,1.01,0.30;0.014)->(0.095,1.07,0.30;0.006), helix r 0.025, 2 turns, tip y 1.08 | RH_Ice | mount_head |
| 21 | m_horn glow inclusions M | B | 3 inner cores s=(0.014,0.03,0.014) per horn | RH_Glow x2 | mount_head |
| 22 | m_frost mane (icicles) | C | along neck crest n=8 len 0.05-0.10 r 0.008 draped back | RH_Frost | top (~soft with mount_head) |
| 23 | m_bridle + chain M | S | (0.045,0.80,0.44)->(0.04,0.84,0.22) r 0.004 + links | RH_Silver | mount_head |
| 24 | m_saddle | B | c=(0,0.745,-0.05) s=(0.17,0.035,0.20) rd=0.02 e=3 + tattered blanket E over haunch `~soft` | RH_Armour / RH_Cloth | mount_body |
| 25 | r_leg bones M | S | (0.085,0.76,-0.05;0.022)->(0.14,0.66,0.04;0.018)->(0.155,0.56,0.02;0.014) | RH_Silver (bone wire) | body |
| 26 | r_greave + knee plate M | E/B | greave plane=YZ (y,z): (0.58,0.01)(0.66,0.05)(0.67,0.08)(0.59,0.05) x +-0.150..0.165 b=0.005 ; knee B s=(0.05,0.05,0.04) | RH_Obsidian | body |
| 27 | r_boot + stirrup M | B/S | boot s=(0.05,0.06,0.10) at (0.16,0.52,0.04) ; stirrup S ring r 0.022 | RH_Obsidian / RH_Silver | body |
| 28 | r_pelvis | B | c=(0,0.77,-0.05) s=(0.15,0.07,0.10) rd=0.02 | RH_Obsidian | body |
| 29 | r_spine + rib cage | S | spine (0,0.80,-0.07;0.014)->(0,1.00,-0.06;0.012) ; 5 rib pairs arcs radius 0.075, r 0.007 y 0.84-0.96 | RH_Silver / RH_Ice | spine |
| 30 | r_breastplate (half, broken) | E | (-0.07,0.88)(0.09,0.86)(0.10,0.97)(0.04,1.00)(-0.04,0.96) @0.050..0.066 b=0.007, jagged right edge | RH_Obsidian | spine |
| 31 | r_pauldron L (large spiked) / R (bare bone) | B/C | L c=(0.145,1.00,-0.04) s=(0.10,0.05,0.10) e=3 + 3 ice spikes len 0.06-0.10 ; R B s=(0.05,0.03,0.05) | RH_Obsidian / RH_Ice | arm_L / arm_R |
| 32 | r_arm M | S | upper (+-0.095,0.98,-0.05;0.016)->(+-0.105,0.90,-0.01;0.014) ; forearm ->(+-0.105,0.84,0.07;0.012) ; vambrace E 0.05 x 0.05 | RH_Silver / RH_Obsidian | arm / hand |
| 33 | r_hand M | S | 4 bony finger tubes r 0.004 + thumb on palm B s=(0.035,0.03,0.035) | RH_Silver | hand_L/hand_R |
| 34 | r_skull | B | c=(0,1.045,-0.03) s=(0.078,0.09,0.09) e=2.2 ; jaw wedge, eye sockets 2 recesses r 0.014 | RH_Frost (bone-white) | head |
| 35 | r_eye lights M **F1** | B | s=(0.013,0.009,0.009) at (+-0.022,1.052,0.017) | RH_Glow x6 | head |
| 36 | r_crown spikes | C | n=5 ring r 0.04 at y 1.085, len 0.04-0.07, tilt 12 | RH_Ice | head |
| 37 | r_hood scraps (cloak) | E | torn cowl behind skull + cloak down the back: (0,1.06)(0.12,1.0)(0.16,0.80)(0.10,0.66)(0.04,0.72)(-0.02,0.62)(-0.12,0.78)(-0.10,1.0) @-0.100..-0.094, jagged hem `~soft` (head/top) | RH_Cloth | top |
| 38 | r_glaive haft **S** | S | (-0.17,0.60,0.01;0.015)->(-0.17,0.95,0.02;0.013)->(-0.17,1.20,0.02;0.012) with 4 silver wire wraps r +0.003 | RH_Obsidian / RH_Silver | hand_R |
| 39 | r_glaive blade (hooked) **S** | E | plane=YZ (y,z): (1.15,0.015)(1.20,0.06)(1.26,0.16)(1.30,0.24)[tip](1.27,0.20)(1.22,0.12)(1.18,0.08)(1.17,0.02) thickness x -0.18..-0.16 b=0.004 ; back spike (1.20,-0.04) | RH_Ice | hand_R |
| 40 | r_glaive butt cap | C | 1 prism len 0.06 at (-0.17,0.60,0.01) pointing down | RH_Ice | hand_R |
(40 parts; budget <= 35k. F1 = eyes (ram + rider); F2 = rib-cage frost-light.)

## 5. Pose
Ram stands square, head lowered 10 deg so the spirals frame the face; rider upright, skull turned 5 deg toward the left. Glaive held vertical at the rider's right, butt on the stirrup line, hook forward. Tattered cloak hangs behind the saddle; frost mane draped on the neck.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.17, 1.28, 0.20) glaive hook mid | hand_R |
| `socket_cast` | (0, 0.60, 0.0) rib-light core | mount_body |
| `socket_impact` | (-0.08, 0.72, 0.60) glaive/head blow | body |
| `socket_head` | (0, 1.12, -0.03) | head |

Extras: `impactTime 1.00`, `strikeRange 0.50`, `attackStyle leap`, `displayName "Rime Gravewind Rider"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 3.4 s) - restless cold
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 1.1 | mount_head | rx +4, ry -5 (scenting) |
| 1.1 | top | rx +6 (mane drift) ; hand_R rz +1.5 (glaive sway) |
| 2.3 | mount_body | rx -1 ; spine rx +1.2 ; head ry +4 |
| 3.4 | all | rest |

**Move** (loop 0.8 s; steps 0.1, 0.5)
| t | bone | value |
|---|---|---|
| 0.0 | mount_body | rx +4 ; mount_head rx +6 |
| 0.1 | mount_body | y +0.02 (step) |
| 0.4 | mount_body | rx +6, rz -3 ; top rx -8 |
| 0.5 | mount_body | y +0.02 (step), rz +3 |
| 0.8 | all | = t0 |

**Attack** (2.1 s; impact 1.00)
| t | bone | value |
|---|---|---|
| 0.00-0.40 | rear (io) | mount_body rx -22, y +0.05 ; mount_head rx -24 ; body rx +8 ; arm_R rx -45, hand_R rx -45 (glaive swings back over shoulder, net -90) ; top rx +16 |
| 0.40-0.55 | hold | mount_head rx -30 ; head rx -8 |
| 0.55-0.85 | leap (engine arc) | mount_body rx -22 -> +10 ; mount_head rx -30 -> -5 ; arm_R rx -45 -> -55 ; spine rx +5 |
| 0.85-0.93 | **headbutt** (0.08 s snap) | mount_head rx -5 -> +42, mount_body rx +10 -> +18, z +0.10 ; engine ice crack at 0.93 |
| 0.93-1.00 | **glaive strike** (0.07 s snap, impact at 1.00) | arm_R rx -55 -> -30 ; hand_R rx -45 -> +75 (net haft pitch from -100 to +45) ; spine rx +18 ; body z +0.12 |
| 1.00 | **impact** | glaive hook on socket_impact |
| 1.00-1.15 | hold | landing squash mount_body y -0.03 |
| 1.15-2.10 | recover (io) | to rest |

**HitReact** (0.45 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.10 | mount_body | rx -10, z -0.07 ; mount_head rx -22 ; spine rx -10 ; head rx -14 ; arm_R rx +10 |
| 0.45 | mount_body rx -3 ; mount_head rx -8 |

**Victory** (1.6 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.6 | mount_body | rx -20, y +0.05 ; mount_head rx -22 ; arm_R rx -150, hand_R rx +10 (glaive overhead, vertical) ; head rx -10 |
| 1.6 | hold | rear held |

## 8. Fragments (30)
Sharp: 8 ram body shards (ribs break into thin curved spikes, 4 of them), 4 horn spiral segments (long thin), 4 skull/jaw shards, 5 rider bone/obsidian shards (flat 3-5 sided), glaive hook as 1 curved blade piece + 2 haft splinters, 4 saddle/cloak splinters. Interior pale cracked ice; the rib light flashes cyan for 0.3 s.

## 9. Readability
- vs `emberhold_knight`: lean, see-through, dark, vertical glaive; spiral horns not palmate antlers; no lance diagonal; mean luma <= 0.15 with a bright rib light.
- vs other roles: four legs and 0.80 depth mark the knight; glaive hook rises to 1.30; not as tall as bishop staff (1.40).
