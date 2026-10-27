# rime_king - Rime Glacier Tyrant

## 1. Identity
- **Name**: Rime Glacier Tyrant. **Concept**: a massive armoured revenant lord in faceted obsidian plate; the glacier he was buried in breaks out through his back as a ridge of ice; his crown is a **ring of eight hovering ice prisms caged by four wire arches around a tall ice-crystal CROSS**; a frozen cape hangs mid-sway; a cracked visor glows. Unarmed: fist and backhand are his weapons.
- **Identity cue (the only cross in the set, in ice)**: a vertical crystal cross (0.12 wide x 0.14 tall, bars r 0.026/0.022, inner cyan core) floating inside a hovering ring of 8 prisms (ring r 0.115, y 1.515-1.62) joined to it by four arches. Crown stack y 1.515 -> 1.70, 0.23 wide (1.7x the helm), +20% over the previous ring. Back ridge and spiked pauldron are now **lower** (<= 1.44) so nothing competes with the cross.
- **Never confusable with the queen**: the queen has a crescent halo and a ring of tines; the tyrant has a cross and a closed cage.
- **60 px read**: the cross is the single brightest vertical on the piece (core glow + ice >= 0.75 luma); the ring reads as a bright dashed band with a visible dark gap (0.04) above the helm.

## 2. Dimensions (total 1.70)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Boots + greaves | 0.22-0.56 | stance +-0.14 |
| Thigh / hip / kilt | 0.52-0.90 | frozen mail kilt to 0.50 |
| Torso | 0.90-1.28 | chest depth 0.22 |
| Pauldrons | 1.22-1.42 | span x +-0.38 (L spiked to 1.44) |
| Neck + gorget | 1.24-1.355 | |
| Helm / head | 1.30-1.475 | head 0.18 (figure 1.25 -> 6.9 heads) |
| Back ridge | 0.95-1.42 | z -0.10..-0.26, tallest tip 1.42 |
| Prism ring | 1.515-1.62 | hover gap 0.04 above the helm, ring r 0.115 |
| Crystal cross | 1.56-1.70 | vertical bar 1.56-1.70, crossbar centre y 1.640, span 0.12 |
| Frozen cape | 0.38-1.30 | sweeps back and to the left, z to -0.30 |
Envelope: 0.76 wide x 0.56 deep (z -0.30..0.26). Crown never wider than 0.24.

## 3. Rig (humanoid template) and bone pivots
`humanoid_rig(J, cape=[(0,1.10,-0.20),(0.06,0.78,-0.26),(0.12,0.50,-0.28)])`. No weapon bone (unarmed). `top` is the floating crown (cross + prism ring + arches); it is parented to `chest` by the template, so it follows the body and gets its own lag/spin keys.

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`body`) | (0,0.76,0) | | elbow_L | (0.33,1.05,0.04) |
| spine | (0,0.92,0) | | wrist_L | (0.35,0.88,0.15) |
| chest | (0,1.10,0) | | hip_L | (0.12,0.78,0) |
| neck | (0,1.25,0.01) | | knee_L | (0.145,0.54,0.05) |
| head | (0,1.30,0.02) | | ankle_L | (0.14,0.27,0.05) |
| top (crown ring centre) | (0,1.56,0) | | toe_L | (0.14,0.245,0.17) |
| clavicle_L | (0.10,1.28,0) | | shoulder_L | (0.32,1.30,0) |

**Binding (authoritative; legacy Bone column of section 4 otherwise)**: 1 -> `foot`; 2-4, 39 -> `shin`; 5 -> `thigh`; 6-8, 40 -> `body` (kilt 7 `~soft` `thigh`); 9, 11 -> `spine`; 10, 12-17 -> `chest`; 18/19 -> `arm_L/R` (lames `~soft` clavicle); 20 -> `arm`; 21, 22 -> `hand_L/R` (forearm); 23 -> `wrist_L/R`; 24 -> `neck`; 25-30 -> `head`; 31-33, 41, 42 -> `top`; 34-37 -> `top` `~soft` `cape_1..3`; 38 -> `arm`.

## 4. Part list
Pedestal parts per README section 2.
**Part numbers are stable ids; gaps = removed parts.** The Bone column uses legacy names; the binding table in section 3 is authoritative (new rig template).

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
| 15 | back ridge **S** | C | base along (0,0.98,-0.12) -> (0,1.30,-0.10) : n=7 crystals at y 0.98/1.05/1.12/1.19/1.25/1.30/1.34 ; lengths 0.12,0.17,0.22,0.24,0.20,0.15,0.10 ; r 0.030-0.050 ; tilt back 20 deg with 8 deg random roll ; **tallest tip y 1.42** (kept under the crown) | RH_Ice | chest |
| 16 | ridge base cracks | texture | glowing seams (cyan) radiating 0.05 around each crystal root, 2% area | RH_Glow x3 | spine |
| 17 | gorget | L | sides=8, `(0.095,1.27)(0.114,1.28)(0.118,1.33)(0.098,1.355)(0.076,1.355)` | RH_Obsidian | chest |
| 18 | pauldron L (huge, spiked) **S** | E x4 + C | lames L1 (0,0)(0.18,0.04)(0.27,0.13)(0.23,0.19)(0.05,0.11)@-0.09..0.11 at (0.31,1.32) ; L2..L4 scaled 0.88/0.76/0.64 ; 5 ice spikes on L1 len 0.06-0.12 (highest tip 1.44) | RH_Obsidian / RH_Ice | arm_L |
| 19 | pauldron R (smooth shell; asymmetric) **S** | B + E | shell B s=(0.22,0.12,0.22) e=2.6 at (-0.32,1.34,0) ; 2 lames below ; silver wire rune band | RH_Obsidian / RH_Silver | arm_R |
| 20 | upper arm M | S | (+-0.32,1.30,0;0.064)->(+-0.325,1.17,0.02;0.054)->(+-0.33,1.05,0.04;0.048) + rerebrace faceted sleeve | RH_Armour / RH_Obsidian | arm |
| 21 | elbow spike M | C | base=(+-0.36,1.05,-0.03) n=1 len 0.08 r 0.024 up=(+-1,0,-0.4) | RH_Ice | hand |
| 22 | forearm + vambrace M | S | (+-0.33,1.05,0.04;0.048)->(+-0.35,0.95,0.11;0.044)->(+-0.35,0.86,0.15;0.040) ; vambrace E plates x2 | RH_Armour / RH_Obsidian | hand |
| 23 | gauntlet fist M | B + S | block s=(0.085,0.07,0.095) rd=0.016 e=4 ; 4 knuckle spikes C len 0.03 ; thumb S r 0.012 ; ice crust on the R fist (C n=5 len 0.04-0.09) | RH_Obsidian / RH_Ice | hand_L / hand_R |
| 24 | neck | S | (0,1.24,0;0.064)->(0,1.30,0.02;0.058) | RH_Armour | neck |
| 25 | helm shell **S** | L | sides=8 faceted, `(0.090,1.300)(0.100,1.355)(0.096,1.410)(0.074,1.450)(0.036,1.470)(0,1.475)` ; cheek flares E M (0.09,1.32)(0.115,1.35)(0.10,1.39) | RH_Obsidian | head |
| 26 | visor plate | E | (-0.07,1.35)(0.07,1.35)(0.065,1.41)(-0.065,1.41) @0.090..0.108 b=0.006, thin horizontal slit cut 0.11 x 0.016 | RH_Obsidian | head |
| 27 | visor glow + crack **F1** | E | slit emissive 0.11 x 0.014 at y 1.378 ; 3 zig-zag cracks upward/downward 0.05-0.08 long, 0.004 wide | RH_Glow x6 | head |
| 28 | helm side horns M | C | base=(0.095,1.40,0) n=1 len 0.08 r 0.026 up=(1,0.4,-0.2) | RH_Ice | head |
| 29 | helm brow ridge | B | s=(0.18,0.020,0.04) at (0,1.416,0.09) | RH_Obsidian | head |
| 30 | helm silver wire lines | S | 4 vertical lines over the dome, tube 0.004 | RH_Silver | head |
| 31 | prism ring x8 **S** | C | ring r 0.115 around the head axis at y 1.515 ; each a hex prism (r 0.026, i.e. 0.052 across) with a pointed tip : heights 0.105/0.095 alternating ; bottoms at y 1.515, tips 1.62/1.61 ; each tilted outward 3 deg, spacing 45 deg (visible gap 0.04 to the helm top 1.475) | RH_Ice | top |
| 32 | prism ring band | S | torus r 0.115 tube 0.005 at y 1.522, thin cyan accent <= 3% area | RH_Silver (+RH_Glow x2 accent) | top |
| 33 | prism sub-shards x8 | C | tiny shards (len 0.03) hanging below each prism at y 1.48-1.51 | RH_Ice | top |
| 34 | frozen cape (main sweep) **S** | E | curved shell : (-0.20,1.30)(0.20,1.30)(0.34,1.0)(0.40,0.70)(0.34,0.42)(0.10,0.38)(-0.10,0.50)(-0.22,0.80), extruded @z -0.12..-0.30 with S-curve flare (sweeping toward +X and back) ; jagged lower edge ; faceted ripple ridges every 0.06 ; thickness 0.014 b=0.006 | RH_Cloth | spine |
| 35 | cape ice sheath | E | same outline, scaled 1.02, thickness 0.008, transmission on the leading edges | RH_Ice | spine |
| 36 | cape fastener | L | Ø0.05 disc each shoulder (snow-crystal), at the yoke fronts | RH_Silver | spine |
| 37 | cape frost caps | C | n=14 along the shoulders and folds, len 0.02-0.05 | RH_Frost | spine |
| 38 | shoulder frost build-up | B | thin caps 0.015 on top of the pauldron lames | RH_Frost | arm_L / arm_R |
| 39 | knee frost clusters M | C | n=3 each len 0.03-0.06 | RH_Frost | body |
| 40 | belt chain + hanging shards | S | chain from the belt plate down to y 0.62 (r 0.005) with 3 ice shards len 0.05-0.08 | RH_Silver / RH_Ice | body |
| 41 | **crystal cross S F2** | C x2 | vertical hex prism r 0.026, shaft y 1.585-1.670 + pointed top to 1.700 and pointed foot to 1.560 ; crossbar hex prism r 0.022, centre (0,1.640,0), x +-0.060 incl. 0.025 pointed ends ; inner cyan core line r 0.006 along both bars | RH_Ice / RH_Glow x5 (core) | top |
| 42 | crown arches x4 | S | silver wire r 0.005 from the prism tips at 0/90/180/270 deg (+-0.115,1.62,0) -> (+-0.065,1.66,0) -> (0,1.665,0) meeting the cross shaft (closed cage); thin ice sheath tube r 0.007 on two of them | RH_Silver / RH_Ice | top |
(42 parts; budget <= 30k. F1 = visor crack; F2 = crystal cross core. Ring band and ridge-base cracks are texture accents <= 3% area.)

## 5. Pose
Colossal, planted, weight on the left leg; shoulders back; chin level; fists loosely closed at the sides with the arms 0.08 away from the hips; the frozen cape swept to the left and back; the ridge breaking through the back (lower than the crown); crown ring hovering with a visible 0.04 gap above the helm and the crystal cross standing in its centre. The right fist is the larger (ice-crusted).

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.35, 0.88, 0.17) right fist | wrist_R |
| `socket_cast` | (-0.35, 0.88, 0.17) right fist (spike eruption source: the engine targets the floor under the victim) | wrist_R |
| `socket_impact` | (-0.15, 1.00, 0.60) backhand contact | body |
| `socket_head` | (0, 1.74, 0) above the cross | top |

Extras: `impactTime 1.20`, `strikeRange 0.60`, `attackStyle melee`, `displayName "Rime Glacier Tyrant"`, `contractVersion 1`. (Ice spike eruption: engine VFX at t = 0.70.)

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Legs/pelvis | Torso/neck/head | Arms | Secondary (`top` crown ring, cape_1..3).

**Idle** (loop 4.0 s) - slow, ominous
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest |
| 1.4 | body x +0.008, rz +2; thigh_L rx -1, shin_L rx +1.2 | chest rx -1.6, spine rx -0.6 (inhale); head rx -1, ry +1.5 | clavicles rz +-1.2; fists relax: wrist rx +3 | top y +0.012, ry +10 (ring drifts, lags the head by 0.15 s); cape_1/2/3 rx +1/+2/+3 |
| 2.8 | body x -0.008, rz -1.5 | chest rx +0.7; head ry -2 | hand_R rx -2 (knuckles flex) | top y -0.004, ry +20 |
| 4.0 | rest | rest | rest | top ry 0 via a final -20 key |

**Move** (loop 1.0 s; steps 0.25, 0.75) - heavy glacial stride
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | body rx +5; thigh_L rx -15, shin_L rx +8 (heel strike); thigh_R rx +10, shin_R rx +4 | spine ry +5 (counter-twist) | arm_L rx +10, arm_R rx -10 (swing), forearms rx -12 | top y +0.01; cape rx +4/+6/+8 |
| 0.25 | step L: body y +0.02, rz +3; thigh_R rx +22, shin_R rx +46 (R foot lifts 0.05) | head rz -2 | | cape lags |
| 0.5 | body rx +5, y 0; legs mirror of t0 | spine ry -5 | arms mirror | top rx -3, ry +15 (ring trails behind) |
| 0.75 | step R: body y +0.02, rz -3; thigh_L rx +22, shin_L rx +46 | head rz +2 | | |
| 1.0 | = t0 | | | |

**Attack** (2.4 s; **impact 1.20**) - fist slam (spikes erupt at 0.70), then a backhand
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.55 (io) | weight to the back leg: body rx -4, y +0.02; thigh_R rx +6, shin_R rx +14 | spine rx -8, ry +10; head rx -6 | arm_R rx -105, hand_R rx -30 (elbow flexed, fist overhead); arm_L rx -10 | top y +0.03 (ring lifts); cape rx +8 |
| 0.55-0.70 (snap) | pelvis leads: body rx +18, z +0.16; lunge thigh_L rx -18, shin_L rx +26, foot_L +0.14; thigh_R rx +10, shin_R rx +6 | spine rx -8 -> +22; head rx +8 | arm_R rx -105 -> -20, hand_R rx -30 -> 0 (fist to the floor) | cape +20 overshoot |
| 0.70 | event: ice spikes erupt under the target (engine, 0.7 s `back.out`) | | | |
| 0.70-1.07 (io) | body ry +8, z -0.05; shin_R rx +18 (weight back, coiling) | spine ry +58, rx 0; head ry -10 (eyes on target) | arm_R rx -78, ry +25, hand_R rx -30 (fist across the chest) | top ry -8 |
| 1.07-1.20 (snap; pelvis +0.06 s, spine +0.03 s lead) | body ry +8 -> -12, z +0.24; foot_L pivots rz -20; thigh_L rx -22, shin_L rx +28 | spine ry +58 -> -42; head ry -10 -> +6 | arm_R rx -78 held, ry +25 -> -30; hand_R rx -30 -> -5 (arm whips out); arm_L rx +12 (counter) | cape +25 (whip), top ry +30 |
| 1.20 | **impact** | | back of the fist at `socket_impact`; target shatters | |
| 1.20-1.40 hold | body y -0.03 | spine ry -42 held | arm_R follows through ry -36 | cape/top overshoot 20% |
| 1.40-2.40 (io) | to rest | to rest | to rest | ring swirl top ry +20 |

**HitReact** (0.5 s)
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.10 | body rx -8, z -0.05; thigh_L rx +5, shin_L rx +9 | spine rx -8; head rx -13, rz +4 (+0.04 s) | arm_L/R rx +8 | top y +0.02, ry +18; cape rx +14 |
| 0.50 | body rx -3 | spine rx -3, head rx -4 | | |

**Victory** (2.0 s, ends held)
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | |
| 0.7 | body y +0.02, knees straighten | spine rx -8; head rx -12 (face to the sky) | arm_R rx -150, hand_R rx -20 (fist raised); arm_L rx -20 | top y +0.03, ry +60 (ring spins up); cross core +30% |
| 2.0 | hold | hold | hold | ring slow spin top ry +120 |

**Taunt** (1.5 s, once) - the beckoning hand, then a knuckle crack
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.35 | body rx -3; weight to the L leg (thigh_R rx +5) | chest rx -5; head rz -6, rx -4 (looks down his nose) | arm_R rx -60, hand_R rx -50 (forearm up, palm up) | top ry +40 |
| 0.35-0.95 | hold | head ry +4 | wrist_R curls toward himself twice: rx -30 -> +10 at 0.50 and 0.80 (come here) ; arm_L fist clenches rx -8 | ring spin x2 |
| 0.95-1.50 | settle | head up | arm_R drops, hand_R rx -10; knuckle-crack: wrist_L rx +12 snap | cape settles |

**Surrender** (2.4 s, once, holds the last pose) - kneels; the crown is cast off and falls
| t | Legs / pelvis | Torso / neck / head | Arms | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.04 | head rx -10 | fists open (wrist rx +25) | ring jolts ry +25 |
| 0.30-0.55 | | | arms hang rx +6 | **`top` (crown) released at 0.45** via release_weapon: falls, bounces twice, lies on the plinth beside him; glow dims |
| 0.55-1.35 (io) | kneel: body y -0.31, z +0.04; thigh_L rx -75, shin_L rx +95 (planted +0.12); thigh_R rx +20, shin_R rx +110, foot_R rx -70 | spine rx +10 | arms hang | cape drags down 0.05 |
| 1.35-1.95 | hold | spine rx +24, chest rx +12, neck rx +22, head rx +30 | both fists to the plinth: arm_L/R rx -15, hand rx -35, wrists flat | cape settles |
| 1.95-2.40 | hold | slow breath | hold | frost mist on the floor (engine) |

## 8. Fragments (40)
Sharp: 10 ridge/prism shards (long, aspect 4:1; prisms stay whole hexagonal pieces with glowing cores; the **crystal cross breaks into 3 bars and stays glowing**), 8 obsidian breastplate/backplate shards (flat 3-5 sides, bright edge), 6 pauldron plate shards, 4 cape ice sheets (thin triangles), helm 3, arms 4, greaves/kilt 5. `RH_Interior` pale cracked ice, frost mist and glitter spray; the visor flashes cyan for 0.3 s.

## 9. Readability
- **Identity cue**: ice-crystal cross inside a hovering ring of prisms (closed cage).
- vs `emberhold_king`: dark block, empty hands, cyan cross in a floating ring; the Emberhold king is mid-high value with a bronze cross on a crown that sits on the head and a central vertical sword. Both crowns carry a cross; the **hovering gap** and the prisms separate them in silhouette, the cross itself unites "king". Rime perimeter/sqrt(area) ~ 5.8; Emberhold ~ 4.
- vs `rime_queen`: the queen's crescent is behind the head; the king's ring is level with and around the cross; the king is broader (0.76 vs 0.60).
- vs other roles: tallest (1.70) and broadest; only piece with a cross + ring; the ridge (<= 1.42) and spiked pauldron (<= 1.44) stay under the ring (1.515).
