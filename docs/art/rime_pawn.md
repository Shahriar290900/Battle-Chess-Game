# rime_pawn - Rime Thrall

## 1. Identity
- **Name**: Rime Thrall. **Concept**: a hunched revenant foot-soldier dragged up from the frozen sea, obsidian plates wired onto a gaunt frame, trailing a jagged ice cleaver.
- **Signature shape**: a row of icicle spikes rising diagonally off the spine (tallest tip 1.05) and the oversized jagged cleaver (blade 0.34 x 0.13, ~15% big) angled forward-low. Silhouette = forward-leaning comb of spikes with a diagonal blade.
- Greyscale target: mean luma <= 0.15; bright = spikes, cleaver, eyes, frost on shoulders.

## 2. Dimensions (total 1.05)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Feet / shins | 0.22-0.40 | knees bent, shins angled forward |
| Thighs / loincloth | 0.38-0.56 | |
| Torso (leaning 25 deg) | 0.50-0.82 | hip (0,0.52,-0.02) -> shoulder (0,0.78,0.10) |
| Head (tilted 12 deg) | 0.82-0.94 | head 0.11, figure 0.72 = 6.5 heads |
| Spine spikes | 0.78-1.05 | tallest tip 1.05 at z -0.12 |
| Cleaver | y 0.30-0.62, z 0.00-0.44 | tip low, forward |
Envelope: 0.50 wide x 0.52 deep (z -0.14..0.44 incl. cleaver tip; weapon exception).

## 3. Bone pivots (x, y, z)
root (0,0,0) | body (0,0.52,-0.02) | spine (0,0.58,-0.02) | head (0,0.80,0.12) | top (0,0.80,-0.07) | arm_L (0.18,0.78,0.07) | hand_L (0.21,0.60,0.11) | arm_R (-0.18,0.78,0.07) | hand_R (-0.215,0.60,0.14)

## 4. Part list
Pedestal parts per README section 2 (root; obsidian, silver trim, frost).

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | foot M | B | c=(0.08,0.248,0.045) s=(0.09,0.05,0.18) rd=0.02 e=3 ; 3 toe spikes S (0.08,0.245,0.14;0.014)->(0.08,0.26,0.19;0.003) | RH_Armour (grey flesh) / RH_Ice claws | body |
| 2 | shin M | S | (0.085,0.26,0.05;0.026)->(0.088,0.34,0.075;0.034)->(0.085,0.41,0.10;0.040) (forward-leaning) | RH_Armour | body |
| 3 | shin plate M | E | plane=YZ (y,z): (0.28,0.085)(0.40,0.12)(0.41,0.145)(0.29,0.11), thickness x=0.070..0.104 b=0.006 | RH_Obsidian | body |
| 4 | knee ice cluster M | C | base=(0.088,0.425,0.14) n=3 len 0.05-0.09 r 0.012-0.018 tilt 35 up=(0,0.3,1) | RH_Ice | body |
| 5 | thigh M | S | (0.085,0.41,0.10;0.040)->(0.080,0.48,0.03;0.050)->(0.070,0.55,-0.01;0.054) | RH_Armour | body |
| 6 | pelvis | B | c=(0,0.545,-0.02) s=(0.20,0.10,0.14) rd=0.03 e=3 | RH_Armour | body |
| 7 | loincloth strips x5 | E | each (-0.016,0)(0.016,0)(0.012,-0.15)(0,-0.19)(-0.012,-0.15)@0..0.008, hung at z 0.07, x = -0.08..0.08 step 0.04, lengths 0.15-0.20, tattered tips, frost on top face | RH_Cloth | body |
| 8 | torso | S | (0,0.54,-0.02;0.085*0.070)->(0,0.65,0.03;0.098*0.078)->(0,0.76,0.09;0.120*0.080) | RH_Armour | spine |
| 9 | chest plate (cracked) **F2** | E | plane XY: (-0.09,0.60)(0.09,0.60)(0.11,0.74)(0.08,0.80)(-0.08,0.80)(-0.11,0.74) @ z0.085..0.105 (tilted rot=(25,0,0)), split by a zig-zag crack gap 0.006 wide filled with RH_Glow seam | RH_Obsidian + RH_Glow | spine |
| 10 | rib bands x3 | S | arcs radius 0.095 at y 0.62/0.67/0.72, r=0.008, partial (front 200 deg) | RH_Silver | spine |
| 11 | back plates x3 | E | overlapping scales at y 0.62/0.69/0.76, 0.17 x 0.07, z -0.07..-0.058, rot rx 25, b=0.006, jagged lower edge | RH_Obsidian | spine |
| 12 | spine spikes **S** | C | base=(0,0.80,-0.07) n=5 along the spine, lengths 0.15,0.20,0.25,0.22,0.17, r 0.020-0.012, tilt up=(0,1,-0.55) fan 12 deg; each spike chipped, top tip at y 1.05 | RH_Ice | top |
| 13 | spine spike bases | B | 5 obsidian collars r 0.03 at the root of each spike | RH_Obsidian | top |
| 14 | shoulder plate L (large) | B | c=(0.200,0.800,0.07) s=(0.13,0.05,0.12) rd=0.015 e=3 rot rz -10 ; frost cap B on top (s=0.12,0.018,0.11) | RH_Obsidian / RH_Frost | arm_L |
| 15 | shoulder plate R (small, cracked) | B | c=(-0.190,0.790,0.07) s=(0.09,0.045,0.10) rd=0.012 e=3 ; frost cap | RH_Obsidian / RH_Frost | arm_R |
| 16 | shoulder ice cluster L | C | base=(0.21,0.82,0.03) n=4 len 0.08-0.16 r 0.012-0.022 tilt 30 | RH_Ice | arm_L |
| 17 | upper arm M | S | (0.185,0.775,0.07;0.030)->(0.205,0.69,0.10;0.025) (long, gaunt) | RH_Armour | arm_L/R |
| 18 | forearm M | S | (0.205,0.69,0.10;0.025)->(0.21,0.60,0.11;0.026)->(0.20,0.52,0.14;0.020) | RH_Armour | hand_L/R |
| 19 | vambrace M | E | plane=YZ (y,z): (0.57,0.11)(0.63,0.11)(0.62,0.14)(0.56,0.14), thickness x=0.19..0.23 b=0.005 ; silver wire wrap S x3 r 0.004 | RH_Obsidian / RH_Silver | hand_L/R |
| 20 | elbow ice spur M | C | base=(0.21,0.62,0.07) n=2 len 0.07-0.11 r 0.012 up=(1,0,-0.3) | RH_Ice | hand_L/R |
| 21 | hand M | B + S | palm B s=(0.04,0.045,0.04) e=3 at (0.20,0.50,0.14) ; 4 finger tubes S length 0.04, r 0.006 clawed | RH_Armour | hand_L/R |
| 22 | neck | S | (0,0.77,0.08;0.030)->(0,0.82,0.14;0.026) | RH_Armour | head |
| 23 | head | B | c=(0,0.875,0.17) s=(0.085,0.105,0.10) e=2.3 rot=(20,0,10) (tilted down + 10 deg roll) | RH_Armour | head |
| 24 | half-helm | L | sides=14 `(0.048,0.84)(0.052,0.88)(0.046,0.915)(0.028,0.935)(0,0.942)`, centred on head, rot as head ; angular chamfers | RH_Obsidian | head |
| 25 | eye slits **F1** | E | two slits (0.014 x 0.008) at y 0.882, x=+-0.020, z 0.222 inset 0.004 | RH_Glow | head |
| 26 | frozen jaw / beard icicles | C | base=(0,0.84,0.215) n=5 len 0.03-0.07 r 0.006-0.010 tilt 20 up=(0,-1,0.3) | RH_Ice | head |
| 27 | helm horn stubs M | C | base=(0.045,0.91,0.15) n=1 len 0.07 r 0.012 up=(0.6,1,-0.2) | RH_Ice | head |
| 28 | cleaver blade **S** | E | polygon (x,y) in the blade plane, local blade frame: root (0,0)->(0.03,0.02)->(0.12,0.05)->(0.22,0.10)->(0.30,0.13)->(0.34,0.06)[tip]->(0.31,0.02)->(0.22,-0.02)->(0.14,-0.03)->(0.04,-0.04) ; jagged top edge: 5 teeth 0.02 tall; thickness 0.026, bevel 0.006 ; blade frame placed at guard (-0.205,0.52,0.20), pointing to tip (-0.17,0.34,0.44) | RH_Ice (transmission, inner cracks) | hand_R |
| 29 | cleaver spine crystals | C | base along blade back, n=4 len 0.04-0.08 r 0.010 | RH_Ice | hand_R |
| 30 | cleaver guard + handle | E / S | guard B s=(0.07,0.03,0.025); handle S (-0.205,0.52,0.20;0.015)->(-0.12,0.50,0.02;0.017), silver wire wrap x6 r 0.004 ; pommel B r 0.02 at butt | RH_Obsidian / RH_Silver | hand_R |
| 31 | tattered cape (half) | E | polygon (0.0,0.80)(0.16,0.78)(0.20,0.50)(0.12,0.42)(0.04,0.50)(-0.02,0.40)(-0.10,0.55) @-0.095..-0.088, jagged hem `~soft` (spine/top) | RH_Cloth | top |
| 32 | frost hem clusters | C | n=6 small (len 0.02-0.04) along loincloth and cape hems | RH_Frost / RH_Ice | body/top |
| 33 | silver wire lacing | S | zig-zag S r=0.004 across chest plate seam, 6 loops | RH_Silver | spine |
(33 parts. Eyes are focal point 1; the glow seam in the chest plate is the single allowed secondary focal element, <= 3% area.)

## 5. Pose
Hunched with spine 25 deg forward; left foot ahead. Head tilted forward and 10 deg right-roll, eyes lit. Right hand holds the cleaver at the hip, blade angled down-forward (tip 0.44 ahead, 0.10 above the plinth top); left arm hangs, fingers hooked. Spikes lean back from the arch, creating a clear dorsal comb.
For attack: the blade is long enough that raising arm_R (+arm_L swinging onto the handle butt) reads as a two-hand chop.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.16, 0.51, 0.11) (handle centre; trail on tip via blade) | hand_R |
| `socket_cast` | (0, 0.88, 0.22) | head |
| `socket_impact` | (-0.02, 0.50, 0.55) | body |
| `socket_head` | (0, 0.96, 0.14) | head |

Extras: `impactTime 0.95`, `strikeRange 0.55`, `attackStyle melee`, `displayName "Rime Thrall"`, `contractVersion 1`.

## 7. Clips
**Idle** (loop 3.4 s) - twitchy, slow
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 1.0 | spine | rx +2.0 ; head rx -2, rz +4 (tilt deepens) |
| 1.0 | top | rx +3 (spikes sway) |
| 2.2 | arm_L / hand_L | rx -4 / rx -6 (fingers flex) ; head ry -3 |
| 2.2 | body | y -0.004 |
| 3.4 | all | rest |

**Move** (loop 0.9 s; steps 0.2, 0.65) - lurch
| t | bone | value |
|---|---|---|
| 0.0 | body | rx +8, rz +4 ; spine rx +4 |
| 0.2 | body | y +0.015 (step) |
| 0.45 | body | rx +10, rz -4 ; head rx +6 ; arm_L rx +14, arm_R rx -4 |
| 0.65 | body | y +0.015 (step) |
| 0.9 | all | = t0 |
| 0.45 | top | rx -8 |

**Attack** (2.1 s; impact 0.95)
| t | bone | value |
|---|---|---|
| 0.00-0.30 | body | z +0.12, rx +12 ; arm_R rx +25 (blade tip scrapes the plinth) ; head rx +8 (drag) |
| 0.30-0.80 | anticipation (io) | body rx -14, z -0.10, y -0.02 ; spine rx -12 ; arm_R rx -125, hand_R rx -30 ; arm_L rx -105, ry -55, hand_L rx -20 (left hand grabs the handle butt) ; head rx -6 ; top rx +10 |
| 0.80-0.95 | **strike** (0.15 s snap) | body rx +24, z +0.28 ; spine rx +18 ; arm_R rx -125 -> -35 ; arm_L rx -105 -> -20 ; hand_R rx -30 -> -5 ; head rx +10 |
| 0.95 | **impact** | hold, blade tip on socket_impact |
| 0.95-1.10 | hold | body y -0.025 (squash) ; spikes `top` rx +20 whip-through |
| 1.10-2.10 | recover (io) | to rest; cleaver drags back |

**HitReact** (0.4 s)
| t | bone | value |
|---|---|---|
| 0.00 | all | rest |
| 0.08 | body | rx -13, z -0.09 (snap) ; spine rx -9 ; head rx -16, rz -10 ; arm_L rx +22 ; top rx +16 |
| 0.40 | body | rx -5 ; head rx -6 ; arm_L rx +8 |

**Victory** (1.5 s)
| t | bone | value |
|---|---|---|
| 0.0 | all | rest |
| 0.6 | spine | rx -12 (draws up) ; head rx -18 (face lifts, howl) ; arm_R rx -130, hand_R rx -20 (cleaver overhead) ; arm_L rx -100 |
| 1.5 | hold | held |

## 8. Fragments (20)
Sharp: spikes shatter into 6 long ice spears (aspect 4:1); cleaver blade 3 shards; obsidian chest plate 3 flat triangular plates, back plates 2; head 2 (visor half + jaw); limbs 4 thin splinters. Interiors pale cracked ice. Cape rags become 2 light splinters. Eye-slit pieces keep RH_Glow on their faces for a 0.2 s flash.

## 9. Readability
- vs `emberhold_pawn`: dark (mean luma ~0.13) vs mid-value bronze; silhouette is a diagonal comb and a protruding blade (Z-length 0.58) vs a round shield disc; perimeter/sqrt(area) ~ 5.6.
- vs other roles: forward-leaning hunch is unique; head is lowest of any humanoid; no tall single spire (that is the bishop); tallest tip only 1.05.
