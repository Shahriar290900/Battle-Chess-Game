# rime_pawn - Rime Thrall

## 1. Identity
- **Name**: Rime Thrall. **Concept**: a hunched revenant foot-soldier dragged up from the frozen sea, obsidian plates wired onto a gaunt frame, a **round faceted obsidian helm with a glowing visor slit**, trailing a jagged ice cleaver.
- **Identity cue (the round helm)**: a faceted obsidian dome, Ø0.164 (1.7x the head), top 1.036 + an ice knob (r 0.014, top 1.050), brim studs (frost) all round, a cyan visor slit across the front. It is the tallest and roundest thing on the piece: the spine spikes are **cut down to <= 0.95** and the horn stubs removed, so the helm is the dominant top shape. The hunch is eased from 25 to 18 deg to bring the helm to 1.05.
- Greyscale target: mean luma <= 0.15; bright = helm slit, knob/brim frost, cleaver, frost on shoulders.
- Silhouette: round dome over a compact hunched body, a low comb of short spikes behind and a diagonal blade in front.

## 2. Dimensions (total 1.05)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Feet / shins | 0.22-0.40 | knees bent, shins angled forward |
| Thighs / loincloth | 0.38-0.56 | |
| Torso (leaning 18 deg) | 0.52-0.84 | hip (0,0.53,-0.02) -> shoulder (0,0.80,0.08) |
| Head (tilted 15 deg) | 0.88-0.99 | head 0.105 |
| Round helm | 0.905-1.029 | Ø0.164, faceted dome (14 sides), brim studs at y 0.912 |
| Ice knob | 1.022-1.050 | tallest feature |
| Spine spikes | 0.80-0.95 | tallest tip 0.95 at z -0.12 (below the helm) |
| Cleaver | y 0.30-0.62, z 0.00-0.44 | tip low, forward |
Envelope: 0.50 wide x 0.52 deep (z -0.14..0.44 incl. cleaver tip; weapon exception).

## 3. Rig (humanoid template) and bone pivots
`humanoid_rig(J, weapon=(-0.19,0.42,0.30), cape=[(0,0.72,-0.10),(0.04,0.56,-0.14),(0.07,0.44,-0.16)])`; weapon parent `wrist_R`. `top` = the spike comb + cape root (child of `chest`).

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`body`) | (0,0.54,-0.02) | | elbow_L | (0.205,0.69,0.10) |
| spine | (0,0.60,-0.02) | | wrist_L | (0.205,0.55,0.14) |
| chest | (0,0.70,0.03) | | wrist_R | (-0.215,0.53,0.16) |
| neck | (0,0.79,0.08) | | hip_L | (0.085,0.54,0) |
| head | (0,0.85,0.12) | | knee_L | (0.088,0.40,0.10) |
| top (spikes + cape) | (0,0.80,-0.07) | | ankle_L | (0.085,0.27,0.05) |
| clavicle_L | (0.07,0.79,0.06) | | toe_L | (0.085,0.245,0.14) |
| shoulder_L | (0.18,0.80,0.07) | | weapon (cleaver) | (-0.19,0.42,0.30) |

**Binding (authoritative)**: 1 -> `foot`; 2, 3, 4 -> `shin` (knee cluster 4 `~soft` `thigh`); 5 -> `thigh`; 6, 7, 32 -> `body`; 8, 10 -> `spine`; 9, 11, 33 -> `chest`; 12, 13 -> `top` (spikes `~soft` `chest` at the root); 14-16 -> `arm_L/R`; 17 -> `arm`; 18-20 -> `hand_L/R` (forearm); 21 -> `wrist`; 22 -> `neck`; 23-27, 41 -> `head`; 28-30 -> `weapon`; 31 -> `top` `~soft` `cape_1..3`.

## 4. Part list
Pedestal parts per README section 2 (root; obsidian, silver trim, frost).
**Part numbers are stable ids; gaps = removed parts.** The Bone column uses legacy names; the binding table in section 3 is authoritative (new rig template).

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | foot M | B | c=(0.08,0.248,0.045) s=(0.09,0.05,0.18) rd=0.02 e=3 ; 3 toe spikes S (0.08,0.245,0.14;0.014)->(0.08,0.26,0.19;0.003) | RH_Armour (grey flesh) / RH_Ice claws | body |
| 2 | shin M | S | (0.085,0.26,0.05;0.026)->(0.088,0.34,0.075;0.034)->(0.085,0.41,0.10;0.040) (forward-leaning) | RH_Armour | body |
| 3 | shin plate M | E | plane=YZ (y,z): (0.28,0.085)(0.40,0.12)(0.41,0.145)(0.29,0.11), thickness x=0.070..0.104 b=0.006 | RH_Obsidian | body |
| 4 | knee ice cluster M | C | base=(0.088,0.425,0.14) n=3 len 0.05-0.09 r 0.012-0.018 tilt 35 up=(0,0.3,1) | RH_Ice | body |
| 5 | thigh M | S | (0.085,0.41,0.10;0.040)->(0.080,0.48,0.03;0.050)->(0.070,0.55,-0.01;0.054) | RH_Armour | body |
| 6 | pelvis | B | c=(0,0.545,-0.02) s=(0.20,0.10,0.14) rd=0.03 e=3 | RH_Armour | body |
| 7 | loincloth strips x5 | E | each (-0.016,0)(0.016,0)(0.012,-0.15)(0,-0.19)(-0.012,-0.15)@0..0.008, hung at z 0.07, x = -0.08..0.08 step 0.04, lengths 0.15-0.20, tattered tips, frost on top face | RH_Cloth | body |
| 8 | torso | S | (0,0.54,-0.02;0.085*0.070)->(0,0.66,0.03;0.098*0.078)->(0,0.78,0.08;0.120*0.080) (hunch 18 deg) | RH_Armour | spine |
| 9 | chest plate (cracked) **F2** | E | plane XY: (-0.09,0.60)(0.09,0.60)(0.11,0.74)(0.08,0.80)(-0.08,0.80)(-0.11,0.74) @ z0.085..0.105 (tilted rot=(25,0,0)), split by a zig-zag crack gap 0.006 wide filled with RH_Glow seam | RH_Obsidian + RH_Glow | spine |
| 10 | rib bands x3 | S | arcs radius 0.095 at y 0.62/0.67/0.72, r=0.008, partial (front 200 deg) | RH_Silver | spine |
| 11 | back plates x3 | E | overlapping scales at y 0.62/0.69/0.76, 0.17 x 0.07, z -0.07..-0.058, rot rx 25, b=0.006, jagged lower edge | RH_Obsidian | spine |
| 12 | spine spikes **S (demoted)** | C | base=(0,0.80,-0.07) n=5 along the spine, lengths 0.10,0.13,0.17,0.15,0.11, r 0.020-0.012, tilt up=(0,1,-0.55) fan 12 deg; each spike chipped, **tallest tip y 0.95** (below the helm) | RH_Ice | top |
| 13 | spine spike bases | B | 5 obsidian collars r 0.03 at the root of each spike | RH_Obsidian | top |
| 14 | shoulder plate L (large) | B | c=(0.200,0.800,0.07) s=(0.13,0.05,0.12) rd=0.015 e=3 rot rz -10 ; frost cap B on top (s=0.12,0.018,0.11) | RH_Obsidian / RH_Frost | arm_L |
| 15 | shoulder plate R (small, cracked) | B | c=(-0.190,0.790,0.07) s=(0.09,0.045,0.10) rd=0.012 e=3 ; frost cap | RH_Obsidian / RH_Frost | arm_R |
| 16 | shoulder ice cluster L | C | base=(0.21,0.82,0.03) n=4 len 0.08-0.16 r 0.012-0.022 tilt 30 | RH_Ice | arm_L |
| 17 | upper arm M | S | (0.185,0.775,0.07;0.030)->(0.205,0.69,0.10;0.025) (long, gaunt) | RH_Armour | arm_L/R |
| 18 | forearm M | S | (0.205,0.69,0.10;0.025)->(0.21,0.60,0.11;0.026)->(0.20,0.52,0.14;0.020) | RH_Armour | hand_L/R |
| 19 | vambrace M | E | plane=YZ (y,z): (0.57,0.11)(0.63,0.11)(0.62,0.14)(0.56,0.14), thickness x=0.19..0.23 b=0.005 ; silver wire wrap S x3 r 0.004 | RH_Obsidian / RH_Silver | hand_L/R |
| 20 | elbow ice spur M | C | base=(0.21,0.62,0.07) n=2 len 0.07-0.11 r 0.012 up=(1,0,-0.3) | RH_Ice | hand_L/R |
| 21 | hand M | B + S | palm B s=(0.04,0.045,0.04) e=3 at (0.20,0.50,0.14) ; 4 finger tubes S length 0.04, r 0.006 clawed | RH_Armour | hand_L/R |
| 22 | neck | S | (0,0.78,0.08;0.030)->(0,0.85,0.13;0.026) | RH_Armour | neck |
| 23 | head | B | c=(0,0.935,0.16) s=(0.085,0.105,0.10) e=2.3 rot=(15,0,10) (tilted down + 10 deg roll) | RH_Armour | head |
| 24 | **round helm dome S** | L | sides=14 faceted, axis through (0,0.95,0.15) tilted 15 deg forward with the head, `(0.076,0.905)(0.081,0.928)(0.082,0.957)(0.077,0.987)(0.062,1.011)(0.036,1.025)(0,1.029)` (Ø0.164) ; angular chamfers 0.004 ; closed front with a visor slit | RH_Obsidian | head |
| 25 | visor slit **F1** | E | one horizontal slit 0.100 x 0.012 across the front of the dome at y 0.935, inset 0.004, glowing | RH_Glow x6 | head |
| 26 | frozen jaw / beard icicles | C | base=(0,0.885,0.205) n=5 len 0.03-0.07 r 0.006-0.010 tilt 20 up=(0,-1,0.3) | RH_Ice | head |
| 27 | helm brim studs x8 | C | ring r 0.084 at y 0.912, each frost stud len 0.02 r 0.008 (keeps the outline round; replaces the horn stubs) | RH_Frost / RH_Ice | head |
| 28 | cleaver blade **S** | E | polygon (x,y) in the blade plane, local blade frame: root (0,0)->(0.03,0.02)->(0.12,0.05)->(0.22,0.10)->(0.30,0.13)->(0.34,0.06)[tip]->(0.31,0.02)->(0.22,-0.02)->(0.14,-0.03)->(0.04,-0.04) ; jagged top edge: 5 teeth 0.02 tall; thickness 0.026, bevel 0.006 ; blade frame placed at guard (-0.205,0.52,0.20), pointing to tip (-0.17,0.34,0.44) | RH_Ice (transmission, inner cracks) | hand_R |
| 29 | cleaver spine crystals | C | base along blade back, n=4 len 0.04-0.08 r 0.010 | RH_Ice | hand_R |
| 30 | cleaver guard + handle | E / S | guard B s=(0.07,0.03,0.025); handle S (-0.205,0.52,0.20;0.015)->(-0.12,0.50,0.02;0.017), silver wire wrap x6 r 0.004 ; pommel B r 0.02 at butt | RH_Obsidian / RH_Silver | hand_R |
| 31 | tattered cape (half) | E | polygon (0.0,0.80)(0.16,0.78)(0.20,0.50)(0.12,0.42)(0.04,0.50)(-0.02,0.40)(-0.10,0.55) @-0.095..-0.088, jagged hem `~soft` (spine/top) | RH_Cloth | top |
| 32 | frost hem clusters | C | n=6 small (len 0.02-0.04) along loincloth and cape hems | RH_Frost / RH_Ice | body/top |
| 33 | silver wire lacing | S | zig-zag S r=0.004 across chest plate seam, 6 loops | RH_Silver | spine |
| 41 | helm ice knob **S** | B | c=(0,1.036,0.15) r 0.014 e=2 (top y 1.050) | RH_Ice | head |
(34 parts. Eyes are now the visor slit (focal point 1); the glow seam in the chest plate is the single allowed secondary focal element, <= 3% area. Rows 24-27 replace the half-helm, eye slits, icicles and horn stubs.)

## 5. Pose
Hunched with the spine 18 deg forward; left foot ahead. Head tilted forward 15 deg and 10 deg right-roll, visor slit lit. Right hand holds the cleaver at the hip, blade angled down-forward (tip 0.44 ahead, 0.10 above the plinth top); left arm hangs, fingers hooked. The spike comb (<= 0.95) stays below the helm so the dome is a clean circle against the sky from the seat camera.
For attack: the blade is long enough that raising arm_R (+arm_L swinging onto the handle butt) reads as a two-hand chop.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.16, 0.51, 0.11) (handle centre; trail on tip via blade) | weapon |
| `socket_cast` | (0, 0.94, 0.20) | head |
| `socket_impact` | (-0.02, 0.50, 0.55) | body |
| `socket_head` | (0, 1.08, 0.14) | head |

Extras: `impactTime 0.95`, `strikeRange 0.55`, `attackStyle melee`, `displayName "Rime Thrall"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Legs/pelvis | Torso/neck/head | Arms/cleaver | Secondary (`top` spikes, cape_1..3).

**Idle** (loop 3.4 s) - twitchy, slow
| t | Legs / pelvis | Torso / neck / head | Arms / cleaver | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest |
| 1.0 | body y -0.003; thigh_L rx -2, shin_L rx +3 (knees flex) | chest rx -2.0, spine rx -1 ; head rx -2, rz +4 (tilt deepens; the visor glints) | wrist_R tightens (rx +3) | top rx +3 (spikes sway); cape_1/2/3 rx +2/+3/+4 |
| 2.2 | body y -0.004 | head ry -3 | arm_L rx -4, hand_L rx -6, wrist_L curls (fingers flex) | |
| 3.4 | rest | rest | rest | rest |

**Move** (loop 0.9 s; steps 0.2, 0.65) - lurch
| t | Legs / pelvis | Torso / neck / head | Arms / cleaver | Secondary |
|---|---|---|---|---|
| 0.0 | body rx +8, rz +4; thigh_L rx -16, shin_L rx +14 (reach); thigh_R rx +12, shin_R rx +10 | spine rx +4 | cleaver tip drags on the plinth (arm_R rx +20) | |
| 0.2 | step L: body y +0.015; thigh_R rx +20, shin_R rx +44 (R foot lifts 0.04) | | | |
| 0.45 | body rx +10, rz -4 | head rx +6 | arm_L rx +14, arm_R rx -4 | top rx -8 |
| 0.65 | step R: body y +0.015; thigh_L rx +20, shin_L rx +44 | | | |
| 0.9 | = t0 | | | |

**Attack** (2.1 s; **impact 0.95**) - drag, wind-up, two-hand hack
| t | Legs / pelvis | Torso / neck / head | Arms / cleaver | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | body z +0.12, rx +12; thigh_L rx -14, shin_L rx +16 | head rx +8 (drag) | arm_R rx +25 (blade tip scrapes the plinth) | |
| 0.30-0.80 (io) | anticipation: body rx -14, z -0.10, y -0.02; knees flex: thigh_L rx +6, shin_L rx +20; thigh_R rx +8, shin_R rx +22 | spine rx -12; head rx -6 (looks up at the foe) | arm_R rx -125, hand_R rx -30 ; arm_L rx -105, ry -55, hand_L rx -20 (left hand grabs the handle butt) | top rx +10 |
| 0.80-0.95 (snap; pelvis leads 0.06 s, spine 0.03 s) | body rx +24, z +0.28; lunge thigh_L rx -24, shin_L rx +28; thigh_R rx +16 | spine rx +18; head rx +10 | arm_R rx -125 -> -35, arm_L rx -105 -> -20; hand_R rx -30 -> -5 | top rx +20, cape whip |
| 0.95 | **impact**: hold, blade tip on `socket_impact` | | | |
| 0.95-1.10 | body y -0.025 (squash) | | | top rx +20 whip-through |
| 1.10-2.10 (io) | to rest | to rest | cleaver drags back | |

**HitReact** (0.4 s)
| t | Legs / pelvis | Torso / neck / head | Arms / cleaver | Secondary |
|---|---|---|---|---|
| 0.08 | body rx -13, z -0.09 (snap); thigh_L rx +6, shin_L rx +12 | spine rx -9; head rx -16, rz -10 (+0.04 s) | arm_L rx +22 | top rx +16 |
| 0.40 | body rx -5 | head rx -6 | arm_L rx +8 | |

**Victory** (1.5 s, ends held)
| t | Legs / pelvis | Torso / neck / head | Arms / cleaver | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | |
| 0.6 | body y +0.02 (rears up); knees extend | spine rx -12 (draws up); head rx -18 (face lifts, howl; visor flares) | arm_R rx -130, hand_R rx -20 (cleaver overhead); arm_L rx -100 | top rx +12 |
| 1.5 | hold | hold | hold | |

**Taunt** (1.2 s, once) - a howl and a cleaver scrape
| t | Legs / pelvis | Torso / neck / head | Arms / cleaver | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | body rx +4; weight forward | chest rx +6; head rx +12 (jaw drops) | arm_R rx +20 (blade tip scrapes the plinth: sparks) | |
| 0.30-0.80 | hold | chest rx -8; head rx -16 (howl, visor slit flares +50%) | arm_L rx -35, hand_L rx -20 (beckon, fingers curl x2) | top rx +10 (spikes bristle) |
| 0.80-1.20 | settle | head level | arms drop | |

**Surrender** (2.0 s, once, holds the last pose) - drops the cleaver and collapses
| t | Legs / pelvis | Torso / neck / head | Arms / cleaver | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -8, z -0.04 | head rx -12 | wrist_R opens | |
| 0.30-0.55 | | | **`weapon` (cleaver) released at 0.45**: clatters, bounces twice, lies on the plinth | |
| 0.55-1.20 (io) | kneel: body y -0.20; thigh_L rx -70, shin_L rx +90; thigh_R rx +20, shin_R rx +105 | spine rx +14 (the hunch deepens) | arms hang, fingers curl; arm_L rx -10, hand_L rx -30 | spikes (top) droop rx +10 |
| 1.20-1.70 | hold | spine rx +22, neck rx +20, head rx +32 (the helm bows, slit dims to 30%) | hands to the plinth | |
| 1.70-2.00 | hold | slow breath | hold | |

## 8. Fragments (20)
Sharp: spikes shatter into 5 long ice spears (aspect 4:1); cleaver blade 3 shards; obsidian chest plate 3 flat triangular plates, back plates 2; **helm: 3 wedge-shaped dome shards + the ice knob (stays whole, glowing)**; limbs 3 thin splinters. Interiors pale cracked ice. Cape rags become 2 light splinters. The visor-slit pieces keep RH_Glow for a 0.2 s flash.

## 9. Readability
- **Identity cue**: round faceted obsidian helm with a glowing visor slit and an ice knob; short, hunched, compact.
- vs `emberhold_pawn`: both have a round helm; dark (mean luma ~0.12) faceted dome with a cyan slit and frost studs vs a smooth warm bronze hemisphere; hunch + diagonal cleaver (Z-length 0.58) vs an upright body with a shield disc; perimeter/sqrt(area) ~ 5.
- vs other roles: head is the roundest and highest element; no tall spire (that is the bishop) and no crown; tallest tip 1.05 is the knob.
- Silhouette tests: helm width/height ratio 1.25-1.35; spike tips <= 0.95; top-down = a circle with a ring of studs.
