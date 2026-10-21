# emberhold_knight - Emberhold Ashmane Rider

## 1. Identity
- **Name**: Emberhold Ashmane Rider. **Concept**: a heavily armoured rider on a barded highland war-elk whose mane smoulders with embers; a pennoned lance rides at rest.
- **Signature shape**: the elk's broad forward-swept palmate horns (span 0.52, ~15% oversize) over a streaming ember mane. Silhouette = long horizontal barrel, upright rider, wide antler "fork" forward, lance diagonal.
- Elk faces +Z. Rider uses humanoid bones, mount uses `mount_body`/`mount_head`.

## 2. Dimensions (total 1.30)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Hooves / lower legs | 0.22-0.38 | |
| Upper legs | 0.38-0.62 | hind hock at 0.36 |
| Barrel + barding | 0.46-0.78 | z -0.30..0.22 |
| Withers | 0.80 | |
| Neck | 0.74-0.96 | rises forward z 0.18 -> 0.36 |
| Elk head | 0.84-1.00 | muzzle z 0.52 |
| Horns | 0.98-1.08 | span x +-0.26, forward z 0.34-0.56 |
| Saddle | 0.76-0.82 | seat y 0.78 |
| Rider legs | 0.54-0.80 | hang at barrel sides |
| Rider torso | 0.80-1.06 | |
| Rider head + helm | 1.06-1.18 | head 0.09 |
| Helm crest | 1.18-1.22 | |
| Lance (tip) | up to 1.30 | tip (-0.16,1.30,0.44) |
Envelope: 0.52 wide (horns) x 0.80 deep (z -0.30..0.52, tail to -0.34). Rider seated torso+head 0.40 (about 6.5 heads standing-equivalent).

## 3. Bone pivots (x, y, z)
root (0,0,0) | mount_body (0,0.60,0) | mount_head (0,0.76,0.20) | body (0,0.78,-0.04) | spine (0,0.84,-0.04) | head (0,1.07,-0.02) | top (0,0.82,0.12) | arm_L (0.105,1.04,-0.03) | hand_L (0.115,0.95,0.03) | arm_R (-0.105,1.04,-0.03) | hand_R (-0.12,0.95,0.04)

## 4. Part list
Pedestal parts per README section 2. Prefix `m_` = mount, `r_` = rider.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | m_barrel **S** | S | (0,0.64,-0.27;0.15w*0.14h)->(0,0.62,-0.02;0.165*0.165)->(0,0.60,0.18;0.155*0.17) (r=width*height) `+noise 0.005` | EH_Fur (dark, #4A3A2C ash coat) | mount_body |
| 2 | m_haunch M | B | c=(0.115,0.60,-0.20) s=(0.12,0.20,0.20) e=2.3 | EH_Fur | mount_body |
| 3 | m_foreleg M | S | (0.11,0.60,0.15;0.055)->(0.115,0.46,0.17;0.034)->(0.12,0.34,0.19;0.026)->(0.12,0.25,0.20;0.030) | EH_Fur | mount_body |
| 4 | m_hindleg M | S | (0.12,0.62,-0.20;0.065)->(0.13,0.46,-0.12;0.044)->(0.12,0.35,-0.22;0.030)->(0.12,0.25,-0.20;0.030) (hock angle) | EH_Fur | mount_body |
| 5 | m_hooves x4 | B | c=(+-0.12,0.236,0.205) and (+-0.12,0.236,-0.20), s=(0.06,0.03,0.07) rd=0.01 e=3 | EH_Bronze/EH_Steel | mount_body |
| 6 | m_leg greaves x4 | S | wrapping lower legs (r +0.008), 0.10 long, sec=8 | EH_Bronze | mount_body |
| 7 | m_barding peytral (chest) **S** | E | plane XY mirrored: (-0.14,0.46)(0.14,0.46)(0.16,0.64)(0.10,0.74)(-0.10,0.74)(-0.16,0.64) @ z 0.14..0.168 bent around chest (curve R 0.17) b=0.010 + 3 lames | EH_Bronze | mount_body |
| 8 | m_barding flank plates x4 M | B | c=(0.158,0.60,0.06-k*0.10), s=(0.02,0.14,0.095) rd=0.01 e=4, k=0..3, overlap 25% | EH_Bronze | mount_body |
| 9 | m_blanket (oxblood) | E | (-0.17,0.78)(0.17,0.78)(0.19,0.52)(0.12,0.46)(-0.12,0.46)(-0.19,0.52) @ over barrel, stitched hem `~soft` | EH_Cloth | mount_body |
| 10 | m_saddle | B | c=(0,0.795,-0.04) s=(0.19,0.045,0.22) rd=0.02 e=3 ; cantle B s=(0.18,0.07,0.03) at z -0.15 ; pommel s=(0.06,0.06,0.04) at z 0.07 | EH_Leather | mount_body |
| 11 | m_girth + stirrup straps M | S | (0.16,0.62,-0.02)->(0.17,0.50,0.0) r 0.007 ; stirrup rings T r 0.025 | EH_Leather/EH_Steel | mount_body |
| 12 | m_tail | S | (0,0.64,-0.30;0.03)->(0,0.58,-0.38;0.04)->(0.02,0.46,-0.40;0.012) + ember tuft tip | EH_Fur / EH_Ember | mount_body |
| 13 | m_neck | S | (0,0.72,0.17;0.095w*0.10)->(0,0.84,0.27;0.075*0.08)->(0,0.92,0.34;0.062*0.065) | EH_Fur | mount_head |
| 14 | m_crinet (neck armour) x5 | B | rings along the neck: c along the path, each s=(0.13,0.045,0.075) rd=0.012 e=4, tilt with neck 55 deg | EH_Bronze | mount_head |
| 15 | m_skull | S | (0,0.93,0.34;0.062*0.062)->(0,0.89,0.43;0.050*0.056)->(0,0.84,0.51;0.036*0.040) | EH_Fur | mount_head |
| 16 | m_chanfron (face plate) | E | plane=YZ (y,z): (0.945,0.36)(0.93,0.46)(0.86,0.54)(0.82,0.54)(0.88,0.44)(0.92,0.36) thickness x -0.036..0.036 b=0.008, ridge | EH_Bronze | mount_head |
| 17 | m_muzzle + nostrils | B | c=(0,0.82,0.53) s=(0.07,0.06,0.07) e=2 ; two dark recesses r 0.007 | EH_Fur | mount_head |
| 18 | m_ears M | E | plane=XY leaf (0.045,0.96)(0.09,0.99)(0.06,0.93)@z 0.30..0.318 | EH_Fur | mount_head |
| 19 | m_eyes M **F2** | B | c=(+-0.052,0.915,0.43) s=(0.018,0.014,0.012) | EH_Ember x5 | mount_head |
| 20 | m_antler beam M **S** | S | (0.045,0.985,0.35;0.022)->(0.120,1.025,0.39;0.024)->(0.200,1.050,0.45;0.020)->(0.250,1.045,0.52;0.012) forward-swept | EH_Steel (dark horn) | mount_head |
| 21 | m_antler palm M **S** | E | plane=XZ (x,z): (0.12,0.40)(0.20,0.36)(0.27,0.44)(0.26,0.56)(0.20,0.55)(0.16,0.50)(0.12,0.47) thickness y 1.030..1.058 b=0.006, notched top edge | EH_Steel | mount_head |
| 22 | m_antler tines M | S | 4 tines from the palm: (x,1.045,z)->tip +0.07 to +0.11 forward & up (tips y 1.07-1.08), r 0.011->0.003 ; bronze tip caps | EH_Steel / EH_Bronze | mount_head |
| 23 | m_horn rings M | L | axis along beam, bands at 25% & 60%, r+0.006, 0.014 wide | EH_Bronze | mount_head |
| 24 | m_mane **F1** | S | 14 clumps along neck crest from (0,0.98,0.32) back to (0,0.80,0.14): clump k base on crest, direction up-back, length 0.10-0.17, radius 0.022->0.004, vertex gradient fur #6B5440 -> ember; `+noise 0.012` | EH_Fur / EH_Ember tips | top (~soft with mount_head) |
| 25 | m_back embers (withers) | S | 5 clumps along the barrel back, len 0.07-0.10 | EH_Fur / EH_Ember | top |
| 26 | r_boot M | B | c=(0.175,0.52,0.03) s=(0.065,0.09,0.12) rd=0.02 e=3 rot rx 15 | EH_Leather | body |
| 27 | r_leg M | S | (0.095,0.80,-0.04;0.050)->(0.15,0.70,0.08;0.042)->(0.17,0.58,0.05;0.032) (thigh to calf, knee forward) | EH_Cloth | body |
| 28 | r_greave + knee cop M | S/B | greave S (0.165,0.64,0.07;0.040)->(0.175,0.54,0.04;0.033) ; cop B s=(0.07,0.06,0.05) at (0.155,0.70,0.10) | EH_Bronze | body |
| 29 | r_torso | S | (0,0.80,-0.04;0.10*0.08)->(0,0.92,-0.03;0.115*0.085)->(0,1.03,-0.02;0.13*0.09) | EH_Cloth | spine |
| 30 | r_cuirass | E | (-0.105,0.84)(0.105,0.84)(0.125,0.97)(0.105,1.05)(-0.105,1.05)(-0.125,0.97) @0.052..0.074 b=0.009, ridge ; backplate mirror @-0.115..-0.093 | EH_Bronze | spine |
| 31 | r_fur mantle (asymmetric: heavy on L) | S | closed ring r 0.11 at y 1.05 tube 0.032 + L-side flap B s=(0.12,0.06,0.13) at (0.16,1.03,-0.02) `+noise 0.012` | EH_Fur | spine |
| 32 | r_pauldron L (large) / R (small) | B | L c=(0.170,1.05,-0.03) s=(0.115,0.06,0.115) e=3 ; R c=(-0.158,1.045,-0.03) s=(0.09,0.05,0.095) e=3 | EH_Bronze | arm_L/arm_R |
| 33 | r_arm M | S | upper (+-0.105,1.04,-0.03;0.034)->(+-0.12,0.96,0.01;0.028) ; forearm (+-0.12,0.96,0.01;0.028)->(+-0.12,0.89,0.09;0.022) ; gauntlet cuff B | EH_Cloth/EH_Bronze | arm / hand |
| 34 | r_head | B | c=(0,1.105,0.0) s=(0.082,0.095,0.092) e=2.3 | EH_Leather (skin) | head |
| 35 | r_helm | L | sides=16, `(0.048,1.070)(0.050,1.105)(0.044,1.140)(0.024,1.165)(0,1.180)` + conical crown, face-slit visor E (0.06 x 0.010) at y 1.108, nasal bar | EH_Bronze/EH_Steel | head |
| 36 | r_helm crest **S** | E | plane=YZ: (1.150,-0.045)(1.205,-0.030)(1.222,0.0)(1.190,0.035)(1.150,0.040) x -0.008..0.008 | EH_Bronze | head |
| 37 | r_lance shaft **S** | S | (-0.16,0.78,-0.16;0.014)->(-0.16,0.95,0.04;0.013)->(-0.16,1.24,0.38;0.010) | EH_Leather / EH_Bronze rings x3 | hand_R |
| 38 | r_lance head | E | leaf blade (x along shaft) length 0.10, width 0.038, tip at (-0.16,1.30,0.44) b=0.003 + socket collar | EH_Steel | hand_R |
| 39 | r_pennon | E | triangle swallow-tail (0,0)(-0.16,0.04)(-0.12,0)(-0.16,-0.04) @0..0.004 on the shaft at y 1.20 (streams to -Z) `~soft` | EH_Cloth | hand_R |
| 40 | r_hands M | B | mitten blocks s=(0.04,0.035,0.045) | EH_Leather | hand_L/hand_R |
| 41 | reins | S | (0.115,0.92,0.07)->(0.06,0.94,0.20)->(0.0,0.90,0.40) r 0.004 | EH_Leather | hand_L |
(41 parts; budget <= 35k. F1 = mane tips; F2 = elk eyes. Rider has no emissive.)

## 5. Pose
Standing at rest, weight on the left foreleg; head lowered 6 deg; antlers level. Rider upright, lance on the right hand, tilted 41 deg forward-up; left hand on the reins; helm turned 5 deg toward the left. Mane flows back along the neck.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.16, 1.30, 0.44) lance tip | hand_R |
| `socket_cast` | (0, 1.00, 0.36) between horns (ember trail source) | mount_head |
| `socket_impact` | (-0.10, 0.75, 0.58) lance point on landing | body |
| `socket_head` | (0, 1.20, 0) | head |

Extras: `impactTime 1.00`, `strikeRange 0.50`, `attackStyle leap`, `displayName "Emberhold Ashmane Rider"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 3.2 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 1.0 | mount_head | rx +3, ry +4 (nostrils) |
| 1.0 | top | rx -4 (mane lifts) |
| 1.6 | mount_body | y +0.004, rx -0.8 (breath) ; spine rx +1 |
| 2.2 | mount_head | rx -2, ry -3 ; hand_R rz +1 (lance sway) |
| 3.2 | all | rest |

**Move** (loop 0.9 s; steps 0.15, 0.6) - the elk trots
| t | bone | value |
|---|---|---|
| 0.0 | mount_body | rx +3, y 0 ; mount_head rx +4 |
| 0.15 | mount_body | y +0.02 (step) |
| 0.45 | mount_body | rx +5, rz -2 ; mount_head rx -4 ; spine rx -2 |
| 0.6 | mount_body | y +0.02 (step), rz +2 |
| 0.9 | all | = t0 |
| 0.45 | top | rx -10 (mane streams) |

**Attack** (2.0 s; impact 1.00; engine runs the leap arc 0.45-0.95)
| t | bone | value |
|---|---|---|
| 0.00-0.40 | rear (io) | mount_body rx -26, y +0.06 ; mount_head rx -12 ; body rx +10, spine rx +8 ; arm_R rx -50, hand_R rx -10 (lance lifts) ; top rx -22 ; head rx -6 |
| 0.40-0.55 | hold rear | add mount_body rx -32 ; mount_head rx -22 ; head rx -8 ; top rx -30 (mane blazes, ember trail) |
| 0.55-0.88 | leap (engine arc) | mount_body rx -26 -> +14 (nose-down), mount_head rx -22 -> +8 ; body rx +6 ; arm_R rx -35 / hand_R rx +90 (net lance pitch +55 couched) ; spine rx +10 |
| 0.88-1.00 | **strike** (0.12 s snap) | mount_body rx +14 -> +22, z +0.15 ; arm_R rx -35 -> -20 ; hand_R rx +90 -> +105 (lance thrust, net +85 at impact) ; spine rx +16 |
| 1.00 | **impact** | landing: mount_body y -0.04 (squash), hooves plant ; lance tip at socket_impact |
| 1.00-1.15 | hold | hold; top rx +20 whip |
| 1.15-2.00 | recover (io) | to rest, mount_body rx 0 with -4 overshoot at 1.5 |

**HitReact** (0.45 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.10 | mount_body | rx -9, z -0.07 ; mount_head rx -16 (head throws up) ; spine rx -10 ; arm_R rx +12 ; top rx +16 |
| 0.45 | mount_body rx -3 ; mount_head rx -6 ; spine rx -4 |

**Victory** (1.8 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.6 | mount_body | rx -22, y +0.05 (rear) ; mount_head rx -14 ; top rx -25 ; arm_R rx -150, hand_R rx -25 (lance raised high) ; head rx -8 |
| 1.8 | hold | mount_body rx -14, lance still raised |

## 8. Fragments (30)
Coarse: elk torso 6 slabs (fur-coat stone with ember interior), antlers 3 big palm chunks (whole tines kept), barding plates 5 bronze slabs, rider cuirass 2 + helm 1 + pauldrons 2, lance shaft 2 + head 1, legs 6 chunks, saddle/blanket 2. Chunky bronze/stone, glowing `EH_Interior`; the mane breaks into 4 ember puffs (particles, no mesh).

## 9. Readability
- vs `rime_knight`: broad palmate antlers + low-slung long horizontal elk + diagonal lance vs tall spiral ram horns, upright glaive and see-through ribs; warm mid-value vs dark.
- vs other roles: only 4-legged, longest silhouette (0.80 deep); lance + antlers give the "fork" at the front. Top 1.30 (lance tip) is taller than the rook (1.20), shorter than the bishop (1.40).
