# rime_king - Rime Glacier Tyrant

## 1. Identity
- **Name**: Rime Glacier Tyrant. **Concept**: a massive armoured revenant lord in faceted obsidian plate; the glacier he was buried in is breaking out through his back as a ridge of ice; his "crown" is a ring of short vertical ice prisms hovering just above the helm; a frozen cape hangs mid-sway behind him; a cracked visor glows. He is unarmed: his fist and a backhand are his weapons.
- **Signature shape**: the back ridge of ice crystals (tallest tip 1.55) and the hovering prism ring (8 prisms, top 1.70, ~15% oversize, gap 0.04 above the helm). Silhouette = the heaviest dark block, spiked left pauldron, a ragged ridge behind, and a detached ring of ice prisms floating over the head.

## 2. Dimensions (total 1.70)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Boots + greaves | 0.22-0.56 | stance +-0.14 |
| Thigh / hip / kilt | 0.52-0.90 | frozen mail kilt to 0.50 |
| Torso | 0.90-1.28 | chest depth 0.22 |
| Pauldrons | 1.22-1.46 | span x +-0.38 (L spiked to 1.52) |
| Neck + gorget | 1.28-1.38 | |
| Helm / head | 1.35-1.52 | head 0.185 (figure 1.30 -> 7.0 heads) |
| Back ridge | 0.95-1.55 | z -0.10..-0.26 |
| Prism ring | 1.54-1.70 | hover gap 0.04, ring r 0.11 |
| Frozen cape | 0.38-1.30 | sweeps back and to the left, z to -0.30 |
Envelope: 0.76 wide x 0.56 deep (z -0.30..0.26).

## 3. Bone pivots (x, y, z)
root (0,0,0) | body (0,0.76,0) | spine (0,0.92,0) | head (0,1.33,0.02) | top (0,1.62,0) (prism ring; floats) | arm_L (0.32,1.30,0) | hand_L (0.33,1.05,0.04) | arm_R (-0.32,1.30,0) | hand_R (-0.33,1.05,0.04)

## 4. Part list
Pedestal parts per README section 2.

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | boot M | B | c=(0.14,0.255,0.05) s=(0.13,0.07,0.24) rd=0.02 e=4 ; toe spike C n=1 len 0.06 | RH_Obsidian / RH_Ice | body |
| 2 | greave M | S | (0.14,0.28,0.05;0.054)->(0.145,0.40,0.06;0.062)->(0.15,0.52,0.05;0.068) sec=8 faceted | RH_Obsidian | body |
| 3 | knee spike M | C | base=(0.15,0.55,0.09) n=1 len 0.09 r 0.03 up=(0.3,0.3,1) | RH_Ice | body |
| 4 | greave frost bands M | S | rings r+0.006 at y 0.34/0.46, tube 0.005 | RH_Silver | body |
| 5 | thigh M | S | (0.145,0.54,0.04;0.070)->(0.135,0.68,0.02;0.084)->(0.120,0.80,0;0.090) | RH_Armour | body |
| 6 | pelvis block | B | c=(0,0.82,0) s=(0.28,0.12,0.20) rd=0.03 e=3 | RH_Armour | body |
| 7 | frozen mail kilt strips x14 | E | each (-0.04,0)(0.04,0)(0.034,-0.20)(0,-0.26)(-0.034,-0.20) @r 0.18-0.22, hung from y 0.80, jagged, lengths 0.17-0.27, stiff outward tilt 12 deg, frost on top | RH_Cloth / RH_Frost | body |
| 8 | belt + rune plate | L / E | belt `(0.150,0.86)(0.162,0.865)(0.162,0.905)(0.150,0.91)` ; plate E 0.10 x 0.08 @0.162..0.176 with snow-crystal glyph (silver) | RH_Obsidian / RH_Silver | body |
| 9 | torso (barrel) | S | (0,0.92,0;0.15*0.105)->(0,1.08,0;0.18*0.12)->(0,1.24,0;0.21*0.12) | RH_Armour | spine |
| 10 | breastplate **S** | E | faceted (-0.18,0.96)(0.18,0.96)(0.215,1.12)(0.20,1.27)(0.0,1.31)(-0.20,1.27)(-0.215,1.12) @0.100..0.134 b=0.012, 5 facet ridges | RH_Obsidian | spine |
| 11 | rib lames x4 | B | y 0.94/0.98/1.02/1.06 s=(0.30,0.034,0.030) rd=0.01 e=4 z=0.12, silver wire edge | RH_Obsidian | spine |
| 12 | chest runes (silver wire) | S | 3 rune glyphs ~0.07 tall: tube r 0.004 on the breastplate | RH_Silver (+RH_Glow x2 in 1 glyph) | spine |
| 13 | ice breakthrough (chest, right) | C | base=(-0.13,1.10,0.12) n=4 len 0.06-0.11 r 0.015-0.026 tilt 30 | RH_Ice | spine |
| 14 | backplate | E | (-0.18,0.96)(0.18,0.96)(0.21,1.12)(0.19,1.27)(-0.19,1.27) @-0.134..-0.100 b=0.012 (cracked open along the spine) | RH_Obsidian | spine |
| 15 | back ridge **S** | C | base along (0,0.98,-0.12) -> (0,1.34,-0.10) : n=7 crystals at y 0.98/1.06/1.14/1.22/1.30/1.38/1.44 ; lengths 0.14,0.20,0.27,0.30,0.28,0.21,0.14 ; r 0.030-0.050 ; tilt back 20 deg with 8 deg random roll ; tallest tip y 1.55 | RH_Ice | spine |
| 16 | ridge base cracks | texture | glowing seams (cyan) radiating 0.05 around each crystal root, 2% area | RH_Glow x3 | spine |
| 17 | gorget | L | sides=8, `(0.095,1.30)(0.114,1.31)(0.118,1.36)(0.098,1.385)(0.076,1.385)` | RH_Obsidian | spine |
| 18 | pauldron L (huge, spiked) **S** | E x4 + C | lames L1 (0,0)(0.18,0.04)(0.27,0.13)(0.23,0.19)(0.05,0.11)@-0.09..0.11 at (0.31,1.32) ; L2..L4 scaled 0.88/0.76/0.64 ; 5 ice spikes on L1 len 0.07-0.17 (highest tip 1.52) | RH_Obsidian / RH_Ice | arm_L |
| 19 | pauldron R (smooth shell; asymmetric) **S** | B + E | shell B s=(0.22,0.12,0.22) e=2.6 at (-0.32,1.34,0) ; 2 lames below ; silver wire rune band | RH_Obsidian / RH_Silver | arm_R |
| 20 | upper arm M | S | (+-0.32,1.30,0;0.064)->(+-0.325,1.17,0.02;0.054)->(+-0.33,1.05,0.04;0.048) + rerebrace faceted sleeve | RH_Armour / RH_Obsidian | arm |
| 21 | elbow spike M | C | base=(+-0.36,1.05,-0.03) n=1 len 0.08 r 0.024 up=(+-1,0,-0.4) | RH_Ice | hand |
| 22 | forearm + vambrace M | S | (+-0.33,1.05,0.04;0.048)->(+-0.35,0.95,0.11;0.044)->(+-0.35,0.86,0.15;0.040) ; vambrace E plates x2 | RH_Armour / RH_Obsidian | hand |
| 23 | gauntlet fist M | B + S | block s=(0.085,0.07,0.095) rd=0.016 e=4 ; 4 knuckle spikes C len 0.03 ; thumb S r 0.012 ; ice crust on the R fist (C n=5 len 0.04-0.09) | RH_Obsidian / RH_Ice | hand_L / hand_R |
| 24 | neck | S | (0,1.30,0;0.064)->(0,1.37,0.02;0.058) | RH_Armour | head |
| 25 | helm shell **S** | L | sides=8 faceted, `(0.090,1.345)(0.100,1.40)(0.096,1.46)(0.074,1.50)(0.036,1.52)(0,1.525)` ; cheek flares E M (0.09,1.37)(0.115,1.40)(0.10,1.44) | RH_Obsidian | head |
| 26 | visor plate | E | (-0.07,1.40)(0.07,1.40)(0.065,1.46)(-0.065,1.46) @0.090..0.108 b=0.006, thin horizontal slit cut 0.11 x 0.016 | RH_Obsidian | head |
| 27 | visor glow + crack **F1** | E | slit emissive 0.11 x 0.014 at y 1.428 ; 3 zig-zag cracks upward/downward 0.05-0.08 long, 0.004 wide | RH_Glow x6 | head |
| 28 | helm side horns M | C | base=(0.095,1.45,0) n=1 len 0.10 r 0.026 up=(1,0.6,-0.2) | RH_Ice | head |
| 29 | helm brow ridge | B | s=(0.18,0.020,0.04) at (0,1.466,0.09) | RH_Obsidian | head |
| 30 | helm silver wire lines | S | 4 vertical lines over the dome, tube 0.004 | RH_Silver | head |
| 31 | prism ring x8 **S** | C | ring r 0.11 around the head axis at y 1.54 ; each a hex prism (r 0.022) with a pointed tip : heights 0.14/0.16 alternating ; bottoms at y 1.54, tips 1.68/1.70 ; each tilted outward 3 deg, spacing 45 deg | RH_Ice | top |
| 32 | prism ring glow torus **F2** | S | torus r 0.11 tube 0.004 at y 1.545 | RH_Glow x3 | top |
| 33 | prism sub-shards x8 | C | tiny shards (len 0.03) hanging below each prism at y 1.50-1.53 | RH_Ice | top |
| 34 | frozen cape (main sweep) **S** | E | curved shell : (-0.20,1.30)(0.20,1.30)(0.34,1.0)(0.40,0.70)(0.34,0.42)(0.10,0.38)(-0.10,0.50)(-0.22,0.80), extruded @z -0.12..-0.30 with S-curve flare (sweeping toward +X and back) ; jagged lower edge ; faceted ripple ridges every 0.06 ; thickness 0.014 b=0.006 | RH_Cloth | spine |
| 35 | cape ice sheath | E | same outline, scaled 1.02, thickness 0.008, transmission on the leading edges | RH_Ice | spine |
| 36 | cape fastener | L | Ø0.05 disc each shoulder (snow-crystal), at the yoke fronts | RH_Silver | spine |
| 37 | cape frost caps | C | n=14 along the shoulders and folds, len 0.02-0.05 | RH_Frost | spine |
| 38 | shoulder frost build-up | B | thin caps 0.015 on top of the pauldron lames | RH_Frost | arm_L / arm_R |
| 39 | knee frost clusters M | C | n=3 each len 0.03-0.06 | RH_Frost | body |
| 40 | belt chain + hanging shards | S | chain from the belt plate down to y 0.62 (r 0.005) with 3 ice shards len 0.05-0.08 | RH_Silver / RH_Ice | body |
(40 parts; budget <= 30k. F1 = visor crack; F2 = prism ring torus, low. The glow seams at the ridge base are a texture accent <= 3% area.)

## 5. Pose
Colossal, planted, weight on the left leg; shoulders back; chin level; fists loosely closed at the sides with the arms 0.08 away from the hips; the frozen cape swept to the left and back; the ridge breaking through the back; prism ring hovering with a visible gap above the helm. The right fist is the larger (ice-crusted).

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.35, 0.86, 0.17) right fist | hand_R |
| `socket_cast` | (-0.35, 0.86, 0.17) right fist (spike eruption source: the engine targets the floor under the victim) | hand_R |
| `socket_impact` | (-0.15, 1.00, 0.60) backhand contact | body |
| `socket_head` | (0, 1.74, 0) above the prism ring | top |

Extras: `impactTime 1.20`, `strikeRange 0.60`, `attackStyle melee`, `displayName "Rime Glacier Tyrant"`, `contractVersion 1`. (Ice spike eruption: engine VFX at t = 0.70.)

## 7. Clips
**Idle** (loop 4.0 s) - slow ominous
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 1.4 | spine | rx +1.2 ; head rx -1, ry +1.5 |
| 1.4 | top | y +0.012, ry +10 (ring drifts) |
| 2.8 | top | y -0.004, ry +20 ; head ry -2 |
| 4.0 | all | rest (top ry 0 via a final -20 key) |

**Move** (loop 1.0 s; speed 1.4; steps 0.25, 0.75)
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +5 ; top y +0.01 |
| 0.25 | body | y +0.02 (step), rz +3 ; head rz -2 |
| 0.5 | body | rx +5 ; top rx -3, ry +15 |
| 0.75 | body | y +0.02 (step), rz -3 |
| 1.0 | all | = t0 |

**Attack** (2.4 s; impact 1.20)
| t | bone | value |
|---|---|---|
| 0.00-0.55 | raise the fist (io) | arm_R rx -105, hand_R rx -30 ; spine rx -8, ry +10 ; body rx -4, y +0.02 ; head rx -6 ; arm_L rx -10 ; top y +0.03 |
| 0.55-0.70 | fist slam to the floor (snap) | arm_R rx -105 -> -20 ; hand_R rx -30 -> 0 ; spine rx -8 -> +22 ; body rx +18, z +0.16 ; head rx +8 |
| 0.70 | event | ice spikes erupt under the target (engine, 0.7 s `back.out`) |
| 0.70-1.07 | cock the backhand (io) | spine rx 0, ry +58 ; arm_R rx -78, ry +25 ; hand_R rx -30 (fist across the chest) ; body rx -4, ry +8 ; head ry -10 (eyes on target) ; top ry -8 |
| 1.07-1.20 | **strike** (0.13 s snap) | spine ry +58 -> -42 ; arm_R rx -78 held, ry +25 -> -30 ; hand_R rx -30 -> -5 ; body ry +8 -> -12, z +0.24 ; head ry -10 -> +6 |
| 1.20 | **impact** | back of the fist at socket_impact ; target shatters |
| 1.20-1.40 | hold | body y -0.03 ; cape (spine) follows |
| 1.40-2.40 | recover (io) | to rest, ring top ry +20 swirl |

**HitReact** (0.5 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.10 | body | rx -8, z -0.05 ; spine rx -8 ; head rx -13, rz +4 ; arm_L/arm_R rx +8 ; top y +0.02, ry +18 |
| 0.50 | body rx -3 ; spine rx -3 ; head rx -4 |

**Victory** (2.0 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.7 | arm_R | rx -150, hand_R rx -20 (fist raised) ; arm_L rx -20 ; spine rx -8 ; head rx -12 ; body y +0.02 ; top y +0.03, ry +60 |
| 2.0 | hold | held, ring slow spin (top ry +120) |

## 8. Fragments (40)
Sharp: 10 ridge/prism shards (long, aspect 4:1; prisms stay whole hexagonal pieces with glowing cores), 8 obsidian breastplate/backplate shards (flat 3-5 sides, bright edge), 6 pauldron plate shards, 4 cape ice sheets (thin triangles), helm 3, arms 4, greaves/kilt 5. `RH_Interior` pale cracked ice, frost mist and glitter spray; the visor flashes cyan for 0.3 s.

## 9. Readability
- vs `emberhold_king`: a dark block with a ragged ridge and a floating ring of prisms (gap), hands empty; the Emberhold king is mid-value with a central vertical sword and a flat six-knob crown. Rime perimeter/sqrt(area) ~ 5.8; Emberhold ~ 4.
- vs other roles: broadest and tallest (1.70); queen's halo is a single crescent, bishop's rune ring orbits a staff; only the king has a hovering ring over the head and a back ridge.
