# rime_queen - Rime Pale Tide Queen

## 1. Identity
- **Name**: Rime Pale Tide Queen. **Concept**: a tall spectral queen in obsidian gown-armour whose hem frays into drifting ice; a translucent ice veil, silver wire lacing, frost trailing across the floor; she wears a **pointed open coronet of nine ice-crystal tines with a small glowing orb in the centre**, and a **crescent halo floats behind her head**. Her great crystal glaive is pulled from the air during Attack.
- **Identity cue**: the crystal coronet in front, crescent halo behind. Band y 1.350-1.405 (silver); **9 hex-prism tines** (5 tall to 1.550, 4 short to 1.515, base 0.052 across, splay 8 deg), glow orb r 0.020 on a 0.09 stalk, top 1.548. Crown stack 0.20 tall, +20% over the previous halo-only crown. The halo is demoted to a dim, wide arc **behind** (apex 1.51, centre z -0.14).
- **Never confusable with the king**: no cross, no arches, no closed cage; tines are open and the halo is behind the head, not around a cross.
- **Idle**: no weapon visible (`weapon_summon` scale 0).

## 2. Dimensions (total 1.55)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Trailing ice hem + floor frost | 0.22-0.40 | z -0.38..0.20, r 0.27 |
| Gown skirt | 0.26-0.85 | slim, r 0.24 -> 0.11 |
| Waist | 0.80-0.90 | r 0.095 |
| Torso + shoulders | 0.88-1.14 | width 0.40, L ice-wing shoulder to 1.30 |
| Neck | 1.14-1.22 | |
| Head | 1.22-1.39 | head 0.17 |
| Coronet band | 1.350-1.405 | silver, r 0.088 -> 0.094 |
| Crystal tines x9 | 1.405-1.550 | tall 0.145, short 0.110 |
| Orb + stalk | 1.412-1.548 | orb r 0.020 centred y 1.528 |
| Veil | 1.15-1.29 | below the coronet, never above 1.29 |
| Halo crescent | 1.28-1.51 | floats behind head, z -0.16..-0.12, apex 1.51 (0.04 below the tall tines) |
Envelope: 0.60 wide (hem shards + wing) x 0.58 deep (hem trail z -0.38..0.20). Halo outer width 0.46 (x +-0.23).

## 3. Rig (humanoid template) and bone pivots
`humanoid_rig(J, cape=[(0,1.10,-0.16),(0,0.78,-0.22),(0,0.50,-0.28)])`; `weapon_summon` node under `wrist_R`, scale 0 except in Attack. `top` = the halo (floats, rotates a few degrees); hair and cape lag from `head`/`top`.

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`body`) | (0,0.78,0) | | elbow_L | (0.23,0.93,0.04) |
| spine | (0,0.90,0) | | wrist_L | (0.24,0.80,0.17) |
| chest | (0,1.02,0) | | wrist_R | (-0.24,0.80,0.17) |
| neck | (0,1.15,0.005) | | hip_L | (0.06,0.80,0) |
| head | (0,1.19,0.01) | | knee_L | (0.07,0.56,0.04) |
| top (halo centre) | (0,1.40,-0.14) | | ankle_L | (0.065,0.27,0.04) |
| clavicle_L | (0.07,1.13,0) | | toe_L | (0.065,0.245,0.12) |
| shoulder_L | (0.19,1.12,0) | | `weapon_summon` | (-0.24,0.80,0.17) under `wrist_R` |

**Binding (authoritative)**: 1-7, 29 -> `body` (gown/hem `~soft` `thigh`; hem tongues 4 and train 5 lag 0.1 s via the lower gown weights); 8, 10 -> `spine`; 9, 11 -> `chest`; 12, 14 -> `arm_L`; 13 -> `arm_R`; 15 -> `arm`; 16 -> `hand_L/R` (forearm); 17 -> `wrist`; 18-22, 43, 44 -> `head` (hair 22 `~soft` `top`); 23-26 -> `top`; 27, 28 -> `top` `~soft` `cape_1..3`; 30-33 -> `weapon_summon`.

## 4. Part list
Pedestal parts per README section 2.
**Part numbers are stable ids; gaps = removed parts.** The Bone column uses legacy names; the binding table in section 3 is authoritative (new rig template).

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | gown skirt inner (tide folds) **S** | L | sides=16 faceted, `(0.000,0.26)(0.215,0.265)(0.222,0.34)(0.200,0.50)(0.160,0.66)(0.120,0.80)(0.100,0.88)(0.000,0.88)` + fold noise 0.007 | RH_Armour | body |
| 2 | gown outer panels x8 | E | curved tall plates (-0.06,0.88)(0.06,0.88)(0.080,0.30)(0,0.24)(-0.080,0.30) @r 0.12-0.23 flaring, rot k*45 deg, thickness 0.012 b=0.006, jagged lower point, alternating lengths 0.60/0.52 | RH_Obsidian | body |
| 3 | tide-wave trim (silver) x3 rows | S | scalloped wave curves on the panels: arc r 0.03, 6 per row, rows at y 0.40/0.55/0.70, tube r 0.004 | RH_Silver | body |
| 4 | fraying hem tongues x16 | E | each (0,0)(0.03,0)(0.02,-0.12)(0,-0.20)(-0.02,-0.12)(-0.03,0) hanging below y 0.30 tilted outward 25 deg, lengths 0.08-0.20, translucent | RH_Ice (cloth-to-ice gradient: top RH_Cloth) | body |
| 5 | trailing ice train (rear) **S** | C | base=(0,0.26,-0.20) n=7 len 0.10-0.22, r 0.020-0.040, up=(0,0.35,-1) tilt 20, drags onto z -0.38 | RH_Ice | body |
| 6 | floor frost trail | E | irregular fan decal on plinth top (0,0.222,-0.10)(+-0.20,0.222,-0.30) thickness 0.006, fringe of 20 tiny crystals len 0.02-0.04 | RH_Frost | body |
| 7 | belt of linked plates | L / B | `(0.098,0.84)(0.106,0.845)(0.106,0.880)(0.098,0.885)` + 5 diamond plates B s=(0.04,0.05,0.012) | RH_Obsidian / RH_Silver | body |
| 8 | torso | S | (0,0.86,0;0.095*0.070)->(0,0.98,0;0.112*0.078)->(0,1.10,0;0.135*0.082) slender | RH_Armour | spine |
| 9 | bodice plate **S** | E | (-0.105,0.90)(0.105,0.90)(0.130,1.02)(0.115,1.12)(0.0,1.14)(-0.115,1.12)(-0.130,1.02) @0.070..0.092 b=0.010 faceted ridge, vertical facet lines | RH_Obsidian | spine |
| 10 | silver lacing | S | criss-cross lacing across bodice, 10 crossings, r 0.004 | RH_Silver | spine |
| 11 | collar crystals (gorget) | C | n=7 around neck r 0.07, len 0.05-0.11, tilt out 25 | RH_Ice | spine |
| 12 | shoulder wing L (ice, tall) **S** | C | base=(0.19,1.12,0) n=5 fan: len 0.10,0.15,0.18,0.14,0.09 ; r 0.020-0.032 ; up=(0.5,1,-0.2) fan 40 deg ; highest tip y 1.30 | RH_Ice | arm_L |
| 13 | shoulder R (smaller obsidian guard; asymmetric) | B | c=(-0.19,1.14,0) s=(0.11,0.05,0.11) rd=0.015 e=3 + frost cap | RH_Obsidian / RH_Frost | arm_R |
| 14 | pauldron L base | B | c=(0.19,1.12,0) s=(0.12,0.05,0.12) e=3 | RH_Obsidian | arm_L |
| 15 | upper arm M | S | (+-0.19,1.12,0;0.034)->(+-0.22,0.98,0.02;0.027)->(+-0.23,0.93,0.04;0.024) | RH_Armour | arm |
| 16 | forearm + vambrace M | S | (+-0.23,0.93,0.04;0.026)->(+-0.24,0.86,0.12;0.021)->(+-0.24,0.80,0.17;0.016) ; vambrace E fins plane=YZ (0.90,0.06)(0.84,0.14)(0.86,0.17)(0.91,0.10) | RH_Obsidian / RH_Silver | hand |
| 17 | hands M (taloned) | B + S | palm s=(0.038,0.035,0.045) ; fingers 4 x S len 0.055 r 0.006 ending in ice claws | RH_Armour / RH_Ice | hand |
| 18 | head | B | c=(0,1.305,0.01) s=(0.105,0.17,0.115) e=2.3 elongated, hollow cheeks | RH_Frost mixed pale skin | head |
| 19 | eyes (dim) | B | s=(0.018,0.008,0.008) at (+-0.028,1.315,0.063) | RH_Glow x3 | head |
| 20 | ice veil **S** | E | plane XY curved: (-0.062,1.265)(0.062,1.265)(0.075,1.19)(0.0,1.15)(-0.075,1.19) @0.060..0.066 jagged hem, translucent, fold noise 0.005 (top edge now under the eyes: the coronet must stay clear) | RH_Ice (thin, transmission) | head |
| 21 | coronet band **S** | L | sides=18 faceted, `(0.082,1.350)(0.088,1.354)(0.094,1.364)(0.094,1.400)(0.088,1.405)(0.082,1.400)` ; 18 tiny studs r 0.005 | RH_Silver | head |
| 22 | hair strands (frost) x7 | S | (0,1.34,-0.04;0.010)->(+-0.05,1.20,-0.12)->(+-0.09,1.00,-0.20;0.002), flowing back, translucent | RH_Frost / RH_Ice | top (~soft with head) |
| 23 | halo crescent (demoted, behind) **S** | E | plane XY, outer r 0.23, inner r 0.17, centre (0,1.28), spanning angles 15 deg -> 165 deg (thick at the top 0.06, thin at the tips 0.02) ; 14 samples per arc ; thickness z -0.16..-0.12 b=0.006 ; apex y 1.51 ; body dark ice (value <= 0.35) with a 0.012 silver edge wire | RH_Ice (dim) / RH_Silver | top |
| 24 | halo outer thorns x9 | C | along the outer edge, len 0.03-0.07, r 0.008-0.012, radiating | RH_Ice | top |
| 25 | halo inner glow line (accent) | S | arc r 0.172 inside the crescent, tube 0.004, <= 3% area | RH_Glow x2 | top |
| 26 | halo orbit shards x3 | C | floating shards near the tips, len 0.05, gap 0.04 from halo | RH_Ice | top |
| 27 | back cape (shrouded mist cloak) | E | (-0.14,1.14)(0.14,1.14)(0.22,0.70)(0.20,0.34)(0.10,0.30)(0,0.40)(-0.10,0.30)(-0.20,0.36)(-0.22,0.70) @-0.120..-0.114 `~soft` (spine/top), jagged ice-fray hem | RH_Cloth | top |
| 28 | cape frost caps | C | n=12 along the shoulder line and folds len 0.02-0.05 | RH_Frost | top |
| 29 | knee-bone spikes (through gown) M | C | n=2 at (+-0.08,0.52,0.18) len 0.05, pointing out through the cloth | RH_Ice | body |
| 30 | **weapon_summon** glaive shaft | S | local to grip: (0,-0.55,0;0.018)->(0,0.55,0;0.014)->(0,0.72,0;0.016) silver wire wraps x6 | RH_Obsidian / RH_Silver | weapon_summon |
| 31 | **weapon_summon** glaive blade **S** | E | plane=YZ (y,z): (0.70,0)(0.82,0.05)(0.95,0.14)(1.08,0.26)(1.20,0.30)[tip](1.14,0.20)(1.02,0.08)(0.90,0.00)(0.80,-0.03) thickness x -0.020..0.020 b=0.005, inner cracks | RH_Ice | weapon_summon |
| 32 | **weapon_summon** crystal growths | C | base=(0,0.72,0) n=6 len 0.08-0.20 r 0.014-0.024 along the blade back | RH_Ice | weapon_summon |
| 33 | **weapon_summon** socket collar + butt | L / C | collar `(0.020,0.66)(0.030,0.69)(0.030,0.74)(0.020,0.76)` ; butt C n=1 len 0.08 at y -0.55 | RH_Silver / RH_Ice | weapon_summon |
| 43 | **coronet tines x9 S** | C | hex prisms with pointed tips on the band at y 1.405, radius 0.090, angles k*40 deg from the front ; 5 tall (0/+-80/+-160 deg) length 0.145, tips y 1.550 ; 4 short (+-40/+-120 deg) length 0.110, tips y 1.515 ; base r 0.026 (0.052 across), tilt out 8 deg ; faint inner cyan core on the tall five | RH_Ice (bright, value >= 0.75) | head |
| 44 | **coronet orb F2** | B + S | stalk S (0,1.405,0;0.007)->(0,1.508,0;0.006) ; orb B c=(0,1.528,0) r 0.020 e=2 (top y 1.548) | RH_Glow x5 / RH_Silver | head |
(35 parts; budget <= 30k. F1 = eyes (dim x3, count with the orb as the head cluster); F2 = coronet orb. Halo glow line and glaive cracks are texture accents <= 3%.)

## 5. Pose
Tall and still. Weight on the right foot, hips tilted 3 deg. Arms low, hands open and slightly turned out, fingers curled, gap 0.08 to the body. Head tilted 3 deg to the right, chin high. Coronet level, halo floating behind and above with a visible gap (>= 0.04) to the skull and a clear dark gap between the halo arc and the tine tips on the 36 deg seat camera (halo is dim, tines are bright). Hem tongues drift outward 25 deg. No weapon.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.24, 0.80, 0.17) palm (weapon_summon origin) | wrist_R |
| `socket_cast` | (0, 1.40, -0.14) halo centre | top |
| `socket_impact` | (0, 0.70, 0.70) cut plane contact | body |
| `socket_head` | (0, 1.58, 0) above the orb | head |

Extras: `impactTime 1.30`, `strikeRange 0.70`, `attackStyle summon`, `displayName "Rime Pale Tide Queen"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Legs/pelvis | Torso/neck/head | Arms | Secondary (`top` halo, cape_1..3, hem). She floats: the feet never visibly step; knees still bend to drive the hem.

**Idle** (loop 3.8 s) - ghostly sway
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | rest ; weapon_summon scale 0 | rest | rest | rest |
| 1.2 | body y +0.012 (floats), rz +2; thigh_L rx -1 | chest rx -1.4, spine rx -0.5; head rz +1.5 | clavicles rz +-1.0; fingers curl: wrist rx +4 | hem tongues rx +4 (drift out) |
| 1.9 | | | | top ry +6, rz +3 (halo drifts, lags 0.2 s); cape_1/2/3 rx +2/+3/+4 |
| 2.6 | body y -0.004, rz -1.5 | chest rx +0.5; head rz -1 | wrist_R rx -3 | top ry -4; orb pulse +15% |
| 3.8 | rest | rest | rest | rest |

**Move** (loop 1.0 s; steps 0.25, 0.75) - glide, hem trails
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | body rx +5, y +0.02 ; thigh_L rx -10, shin_L rx +5 | spine ry +3 | arms hang, rx +-3 | top rx -6 ; cape +4/+7/+10 (trailing) |
| 0.25 | body y +0.03 (soft step), rz +2 | head rz -1.5 | | hem tongues rx +10 |
| 0.5 | body rx +7 ; legs mirror | spine ry -3 | | top rx -10, ry +8 |
| 0.75 | body y +0.03, rz -2 | head rz +1.5 | | |
| 1.0 | = t0 | | | |

**Attack** (2.4 s; **impact 1.30**) - pulls a crystal glaive from the air, glides, sweeping cut
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.45 | body rx -2 | spine rx -3; head rx -5 | arm_R rx -75, hand_R rx -20 (reach and grip) | weapon_summon scale 0 -> 1.15 -> 1.0 by 0.45; halo top ry +20 |
| 0.45-1.05 (io) | glide wind-up: body y +0.03, z -0.10, rx -6 ; thigh_R rx +8, shin_R rx +14 (coil) | spine ry -60 (turns right); head ry +20 (eyes stay on the target) | arm_R rx -85, ry -20, hand_R rx -20 (glaive back-right); arm_L rx -40, rz +20 | hem/cape stream backward 0.12 s late |
| 1.05-1.17 hold | | head fixed on target | glaive horizontal at the right-back | |
| 1.17-1.30 (snap; pelvis leads 0.06 s, spine 0.03 s) | body ry -5 -> +15, z +0.28; thigh_L rx -18, shin_L rx +22 | spine ry -60 -> +72; head ry +20 -> -10 | arm_R rx -85 held (sweeping arc), hand_R rx -20 -> +5 | top ry -20 (halo lags) |
| 1.30 | **impact** | | cut plane at `socket_impact`; frozen crescent VFX | |
| 1.30-1.55 hold | | spine ry +72 -> +60 | follow-through | frost trail; cape overshoot 20% |
| 1.55-2.40 (io) | to rest | to rest | to rest | weapon_summon dissolves 2.1-2.4 |

**HitReact** (0.5 s)
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.10 | body rx -10, z -0.07 | spine rx -9; head rx -14, rz +6 | arm_L/R rx +12 | top rx +14, ry +12 (halo jolts); orb flicker |
| 0.50 | body rx -4 | head rx -5 | | |

**Victory** (2.0 s, ends held)
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | |
| 0.6 | body y +0.03 | spine rx -6; head rx -12 | arm_R rx -60, hand_R rx -25 (palm up); arm_L rx -30 | |
| 1.2 | | | | top ry +30, rz 0 (halo pulse, engine); tine glow +30% |
| 2.0 | hold | hold | hold | mist on the floor |

**Taunt** (1.4 s, once) - a slow, mocking head-tilt and a frost-fingered wave
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.40 | body y +0.015 (rises) | chest rx -3; head rz -8, rx -4 | arm_R rx -55, hand_R rx -40, wrist_R rx -20 (palm out) | halo ry +10 |
| 0.40-0.95 | hold | head rz -8 -> +8 (slow side-to-side) | fingers ripple: wrist_R rx -20 <-> +15 twice; frost crawls up the forearm (VFX) | tine tips flare |
| 0.95-1.40 | settle | head level | arm drops | cape settles |

**Surrender** (2.2 s, once, holds the last pose) - drifts down into a kneel, empty palms
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.04 | head rx -10 | arms drop rx +10 | halo jolts ry +15 |
| 0.30-1.10 (io) | kneel: body y -0.28; thigh_L rx -75, shin_L rx +95; thigh_R rx +20, shin_R rx +108 (under the gown) | spine rx +10 | arms hang | hem tongues spread on the plinth; frost fan dims |
| 1.10-1.70 | hold | spine rx +20, neck rx +20, head rx +28 | hands to the thighs, palms up; `weapon_summon` stays 0 | halo sinks top y -0.04 and dims; orb fades |
| 1.70-2.20 | hold | slow breath | hold | cape settles |

## 8. Fragments (40)
Sharp: 12 long hem/gown ice shards (aspect 4:1), 8 obsidian plate shards (flat, 3-5 sides), **coronet: the 9 tines break away whole (they keep their glow tips) + band 1**, 6 halo crescent arcs (curved thin), 4 wing crystals (whole prisms), head 3 (veil/jaw/orb), arms 4, cape splinters 3. `RH_Interior` pale cracked ice; frost mist and glitter spray; eyes flash cyan 0.2 s.

## 9. Readability
- **Identity cue**: bright crystal open coronet in front, dim crescent halo behind; no cross.
- vs `emberhold_queen`: dark slim gown vs wide bronze skirt/shoulders; crystal tines + halo vs bronze tines with ember beads; frayed tongues and a crystal wing on one shoulder; luma <= 0.15 with bright tines/orb/veil/eyes only.
- vs `rime_king`: the king's cross sits inside a closed cage of prisms; the queen's tines are open and nothing is above 1.55.
- vs other roles: only humanoid with a halo behind the head and a coronet in front; long flared hem; no staff.
- Silhouette test: >= 5 tine peaks visible, halo arc visibly separate (dim, behind); top-down: ring of 9 spikes with a dim arc behind it.
