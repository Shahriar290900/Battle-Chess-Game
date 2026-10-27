# emberhold_bishop - Emberhold Cinder Oracle

## 1. Identity
- **Name**: Emberhold Cinder Oracle. **Concept**: a forge-seer in a sooted ember-red robe and embroidered stole, crowned with a tall **bronze mitre cut by a deep diagonal slit**, leaning on a tall crook-staff from which a chained bronze censer swings, trailing smoke and sparks.
- **Identity cue (the slit mitre)**: a pointed-oval bronze mitre, base y 1.070, top 1.348 (0.28 tall, 0.176 wide, 2.0x the head width, +20% over the old hood), with a **diagonal slit 0.036 wide x 0.050 deep running from upper-left (-0.078,1.262) to lower-right (+0.078,1.146), 38 deg**, lined with oxblood so it reads as a dark diagonal stroke on bright bronze. Slit + mitre are the dominant head shape; the staff and censer are secondary.
- **Never confusable with the pawn** (round helm) **or the queen** (spiked ring): a smooth ogive with one dark diagonal line. Slit lines and rim piping give the mitre a bright edge on both light and dark squares.
- Silhouette: a single narrow cone with a tall mitre, a vertical staff and a swinging weight beside it.

## 2. Dimensions (total 1.40)
| Mass | y range | Notes |
|---|---|---|
| Pedestal | 0.00-0.22 | README section 2 |
| Robe hem + boots | 0.22-0.32 | hem r 0.27 |
| Robe skirt | 0.30-0.70 | cone r 0.27 -> 0.14 |
| Waist / belt / beads | 0.68-0.76 | |
| Torso + stole + shoulders | 0.74-1.00 | shoulder width 0.30 |
| Head (cowl collar to the chin) | 0.955-1.105 | head 0.15 |
| Mitre | 1.070-1.348 | ogive, width 0.176 x depth 0.127, slit y 1.146-1.262 |
| Staff | 0.22-1.40 | crook top 1.40 at x -0.20 |
| Censer | 1.08-1.20 | hangs from the crook on a 0.20 chain |
Envelope: 0.50 wide (x -0.25..0.27) x 0.46 deep. Figure 1.05 (0.22 -> 1.27 incl. mitre brow), ~7.0 heads. The censer (centre x -0.21) must stay >= 0.06 clear of the mitre (half-width 0.088) at every swing angle <= 25 deg.

## 3. Rig (humanoid template) and bone pivots
`humanoid_rig(J, weapon=(-0.20,0.80,0.10), cape=[(-0.205,1.30,0.16),(-0.21,1.22,0.14)])` then re-parent `top` under `weapon` (the staff carries the censer; `cape_1/2` are the two chain links, the censer is skinned to `cape_2`).

| Joint | pos | | Joint | pos |
|---|---|---|---|---|
| pelvis (`body`) | (0,0.60,0) | | elbow_L | (0.17,0.84,0.06) |
| spine | (0,0.72,0) | | wrist_L | (0.19,0.78,0.10) |
| chest | (0,0.86,0) | | wrist_R (staff grip) | (-0.20,0.90,0.10) |
| neck | (0,0.97,0.01) | | hip_L | (0.07,0.62,0) |
| head | (0,1.00,0.012) | | knee_L | (0.08,0.42,0.04) |
| top (censer pendulum pivot) | (-0.20,1.38,0.16) | | ankle_L | (0.075,0.26,0.05) |
| clavicle_L | (0.07,0.95,0) | | toe_L | (0.075,0.245,0.13) |
| shoulder_L | (0.14,0.98,0) | | weapon (staff centre) | (-0.20,0.80,0.10) |

**Binding (authoritative)**: 1-4, 6-8 -> `body` (robe `~soft` `thigh`); 5, 9, 10 -> `chest` (stole `~soft` `spine`); 11 -> `chest`; 12 -> `arm_L/R`; 13 sleeve -> `arm`/`hand` `~soft`; 14 -> `hand_L/R` (forearm); 15 -> `wrist_L/R`; 16, 17 -> `head`; 18-21, 41 -> `head` (21 lappets `~soft` `head`/`neck`); 22-26 -> `weapon`; 27 -> `top`; 28-32 -> `cape_2` (censer, swings); 33, 34 -> `head`/`hand`.

## 4. Part list
Pedestal parts per README section 2.
**Part numbers are stable ids; gaps = removed parts.** The Bone column uses legacy names; the binding table in section 3 is authoritative (new rig template).

| # | Part | Prim | Key numbers | Material | Bone |
|---|---|---|---|---|---|
| 1 | robe hem flare **S** | L | sides=24, `(0.000,0.22)(0.265,0.225)(0.272,0.245)(0.268,0.30)(0.240,0.45)(0.200,0.58)(0.150,0.70)(0.000,0.70)` + fold noise 0.008 (12/unit), soot gradient from hem to y 0.40 | EH_Cloth | body |
| 2 | robe pleat ribs x10 | S | vertical creases from hem to waist, (r*cos,0.26,r*sin)->(0.6r,0.70) r 0.010, amplitude varies | EH_Cloth (darker) | body |
| 3 | hem trim + embroidery band | L | `(0.272,0.246)(0.277,0.252)(0.277,0.285)(0.272,0.290)` | EH_Bronze (thread) | body |
| 4 | boots M (visible at hem) | B | c=(0.075,0.24,0.20) s=(0.09,0.05,0.15) rd=0.02 e=3 | EH_Leather | body |
| 5 | upper robe | S | (0,0.70,0;0.145*0.115)->(0,0.84,0;0.130*0.105)->(0,0.97,0;0.150*0.100) | EH_Cloth | spine |
| 6 | belt | L | sides=18, `(0.148,0.72)(0.158,0.725)(0.158,0.755)(0.148,0.76)` | EH_Leather | body |
| 7 | belt buckle (anvil glyph) | E | 0.045 x 0.035 @0.150..0.162 at (0,0.74) | EH_Bronze | body |
| 8 | prayer beads **(asym, left hip)** | S + B | cord S (0.07,0.745,0.14)->(0.13,0.62,0.12)->(0.14,0.50,0.10) r 0.004 ; 12 beads B r 0.014 along it | EH_Bronze / EH_Stone | body |
| 9 | stole | E | plane XY: (-0.05,0.98)(0.05,0.98)(0.062,0.50)(0.0,0.44)(-0.062,0.50) @z 0.105..0.113 `~soft` (spine/body) b=0.004 | EH_Cloth (#7A2820) | spine |
| 10 | stole embroidery | E | 3 anvil/flame glyphs 0.04 on stole, raised 0.003 | EH_Bronze | spine |
| 11 | shoulder mantle + cowl collar | S | closed ring r 0.15 at y 0.98 tube 0.036 + back flare ; cowl collar ring r 0.085 at y 1.00 tube 0.030 (pulled down, hugs the neck) `+noise 0.008` | EH_Cloth | chest |
| 12 | shoulder cape pieces | B | M c=(+-0.15,0.99,0) s=(0.09,0.05,0.12) e=3 ; right one drooping lower (-0.03) | EH_Bronze | arm_L/arm_R |
| 13 | bell sleeve M | S | (+-0.14,0.98,0;0.040)->(+-0.17,0.84,0.06;0.052)->(+-0.19,0.78,0.10;0.070) wide cuff, r grows | EH_Cloth | arm / hand |
| 14 | sleeve inner cuff | L | rings at sleeve ends, inner radius 0.05, rim thickness 0.008 | EH_Cloth (soot) | hand_L/hand_R |
| 15 | hands M | B + S | palm s=(0.04,0.035,0.045) ; 4 finger tubes r 0.005 | EH_Leather | hand_L/hand_R |
| 16 | head | B | c=(0,1.03,0.012) s=(0.10,0.15,0.11) e=2.3 (gaunt long face) | EH_Leather (skin) | head |
| 17 | eyes (deep set) | B | s=(0.014,0.008,0.008) at (+-0.026,1.045,0.060), dim ember | EH_Ember x2 **F2** | head |
| 18 | **mitre shell S** | L | sides=24, scale z 0.72 (oval section, width 0.176 x depth 0.127), `(0.088,1.070)(0.092,1.100)(0.088,1.160)(0.074,1.220)(0.052,1.275)(0.026,1.315)(0.008,1.333)(0,1.336)` ; hammered `+noise 0.003` ; edge wear on the two side seams | EH_Bronze | head |
| 19 | **mitre slit S** | cut + S | diagonal groove across the front, centreline from (-0.078,1.262) to (+0.078,1.146) (38 deg), 0.036 wide at the surface tapering to 0.006 at depth 0.050, round-capped ends, continues 25% around the flank ; lining = oxblood cloth strip ; 2 bronze lip tubes r 0.005 along both edges | EH_Cloth (#5E1F1A) / EH_Bronze | head |
| 20 | mitre base band + apex cap | L + B | band `(0.090,1.066)(0.096,1.070)(0.096,1.092)(0.090,1.096)` scale z 0.72, with 14 rivet domes ; apex cap B r 0.012 at (0,1.336,0) (top 1.348) | EH_Bronze | head |
| 21 | mitre lappets x2 | E | each (-0.026,0)(0.026,0)(0.022,-0.17)(0,-0.20)(-0.022,-0.17) at x=+-0.05, z -0.065, hanging from y 1.08, bronze-fringed tip, `~soft` (head/neck) | EH_Cloth (#7A2820) / EH_Bronze | head |
| 22 | staff shaft **S** | S | (-0.20,0.22,0.10;0.020)->(-0.20,0.80,0.10;0.016)->(-0.20,1.28,0.12;0.015)->(-0.20,1.37,0.17;0.016) | EH_Bronze (dark, wrapped) | hand_R |
| 23 | staff grip wraps x5 | L | rings r 0.021, 0.012 tall at y 0.86-0.96 | EH_Leather | hand_R |
| 24 | staff foot cap | L | `(0.000,0.22)(0.024,0.22)(0.026,0.27)(0.020,0.30)` at ax=(-0.20,0.10) | EH_Steel | hand_R |
| 25 | staff crook | S | (-0.20,1.30,0.13;0.016)->(-0.20,1.38,0.18;0.014)->(-0.20,1.40,0.21;0.010) hooked end | EH_Bronze | hand_R |
| 26 | staff finials (flame ring) | C | 4 small tines n=4 len 0.04, at (-0.20,1.30,0.12) r 0.02 | EH_Bronze | hand_R |
| 27 | chain | S | links: (-0.20,1.38,0.17) -> (-0.205,1.30,0.16) -> (-0.21,1.22,0.14), r 0.004, 12 torus links alternating 90 deg | EH_Steel | top |
| 28 | censer cap | L | sides=14, `(0.000,1.215)(0.018,1.212)(0.040,1.185)(0.050,1.165)` ax=(-0.21,0.14) | EH_Bronze | top |
| 29 | censer bowl | L | sides=14, `(0.050,1.165)(0.056,1.130)(0.040,1.092)(0.016,1.075)(0.000,1.072)` ax=(-0.21,0.14) ; 8 vent slits 0.010 wide | EH_Bronze | top |
| 30 | censer coals **F1** | B | c=(-0.21,1.125,0.14) s=(0.07,0.05,0.07) e=2 emissive visible through vents | EH_Ember x6 | top |
| 31 | censer smoke wisp (geometry stub) | S | (-0.21,1.215,0.14;0.012)->(-0.21,1.34,0.12;0.003) translucent grey (VFX attaches here) | EH_Cloth (smoke) | top |
| 32 | censer rim studs | B | x8 r 0.006 at the bowl lip | EH_Steel | top |
| 33 | soot streaks / ash patches | texture | up the mitre back (darkening the lower 30%) and the sleeve cuffs | EH_Cloth dark | head/arms |
| 34 | ember scorch seam on left cuff | texture | 3% area | EH_Ember x2 | hand_L |
| 41 | mitre edge piping | S | 2 tubes r 0.005 following the left/right silhouette edge of the mitre from y 1.07 to 1.33 (bright edge that survives on dark squares) | EH_Bronze (polished) | head |
(35 parts; budget <= 22k. F1 = censer coals; F2 = dim eye glints. Rows 18-21 replaced the hood (shell, rim, tip cap, back drape) with mitre, slit, band + cap and lappets; the hood is gone, a pulled-down cowl collar is in row 11.)

## 5. Pose
Weight on the right foot, slight forward lean (3 deg); head turned 5 deg left (the slit stays visible: it faces the front camera, mitre turned with the head); right hand grips the staff 0.68 above the plinth, left hand hangs open-palmed at the hip, fingers curled. Censer hangs at rest, swaying slightly. The staff's crook leans 3 deg toward the viewer. The mitre stays level.

## 6. Sockets and extras
| Socket | Local pos | Parent |
|---|---|---|
| `socket_weapon_R` | (-0.20, 0.92, 0.10) staff grip | weapon |
| `socket_cast` | (-0.21, 1.12, 0.14) censer centre | cape_2 |
| `socket_impact` | (0, 0.45, 1.45) fire wave contact | body |
| `socket_head` | (0, 1.38, 0) above the mitre | head |

Extras: `impactTime 1.10`, `strikeRange 1.50`, `attackStyle ranged`, `displayName "Emberhold Cinder Oracle"`, `contractVersion 1`.

## 7. Clips (jointed beats; conventions in README section 7)
Columns: Legs/pelvis | Torso/neck/head | Arms/staff | Secondary (`top` pendulum, `cape_1/2` chain, lappets). The robe hides the legs but the knees drive it.

**Idle** (loop 3.6 s)
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest |
| 0.9 | body x +0.006, rz +2 (weight on R); thigh_L rx -1, shin_L rx +1 | chest rx -1.4, spine rx -0.5 | wrist_R rz +1 (staff steadies) | top rx +6, rz -4 (censer sways); cape_1/2 rx +3/+5 |
| 1.8 | | chest rx +1.0; head rx -1.5 (mitre nods) | hand_L rx -2 (fingers curl) | top rx -4, rz +5; lappets sway +-3 |
| 2.7 | body x -0.005 | head ry +2 | | top rx +4, rz -3 |
| 3.6 | rest | rest | rest | rest |

**Move** (loop 1.0 s; steps 0.25, 0.75) - glide, the staff taps each step
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.0 | body rx +4, y 0; thigh_L rx -10, shin_L rx +5 | spine ry +3; head level (stab 0.5) | staff planted | top rx +12 (censer swings forward) |
| 0.25 | step L: body y +0.02, rz +2; thigh_R rx +18, shin_R rx +36 (hem swings) | head rz -1.5 | staff lifts 0.03 and re-plants forward 0.04 (weapon y +0.03 at 0.2, y 0 at 0.3) | top rx -2 |
| 0.5 | body rx +6 | spine ry -3 | | top rx -14 (censer drags back) |
| 0.75 | step R: body y +0.02, rz -2 | head rz +1.5 | staff taps again (y +0.03 at 0.7) | top rx +4 |
| 1.0 | = t0 | | | |

**Attack** (2.4 s; **impact 1.10**) - circles the censer, then thrusts and releases a fire wave
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | body rx -2; weight back (thigh_R rx +5) | spine rx -5 | arm_R rx -22, hand_R rx -10 (staff lifts 0.05); arm_L rx -30 | top rx -8 |
| 0.30-0.95 (io) | body y +0.01; feet planted | spine rx -8; head rx -8 (the mitre tips back, slit catches the glow) | arm_L rx -80, hand_L rx -25 (palm out, particles at hand); staff held | **top swings in a circle**: 0.30 rx +35 / 0.50 rz +50 / 0.70 rx -45 / 0.90 rz -55 / 0.95 rx +60 (speeds up) ; chain links lag 0.04 s each |
| 0.95-1.10 (snap; pelvis leads 0.06 s) | body z +0.10, rx +6; lunge thigh_L rx -12, shin_L rx +16 | spine rx -8 -> +12 | arm_R rx -22 -> -75, hand_R rx -10 -> -30 (staff thrust) | top rx +60 -> +85 (censer whips forward) |
| 1.10 | **impact**: fire wave leaves `socket_cast` toward `socket_impact` | | | |
| 1.10-1.30 hold | | | arm_L holds | top rx +95 -> +60 |
| 1.30-2.40 (io) | to rest | to rest | to rest | censer pendulum damped (rx +10, -6, +3) |

**HitReact** (0.45 s)
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.10 | body rx -11, z -0.07; thigh_L rx +5, shin_L rx +9 | spine rx -9; head rx -14 (+0.04 s) | arm_R rx +8 | top rx -30 (censer thrown back); lappets +12 |
| 0.45 | body rx -4 | spine rx -3; head rx -5 | | top rx +8 |

**Victory** (1.8 s, ends held)
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.0 | rest | rest | rest | rest |
| 0.6 | body y +0.015 | spine rx -6; head rx -10 | arm_R rx -40, hand_R rx -10 (staff raised, planted taller) | |
| 0.8 | | | | top rx +30 -> -20 -> +10 (censer spin) |
| 1.8 | hold | hold | hold | top damped |

**Taunt** (1.3 s, once) - swings the censer, points the staff, bows the mitre
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.00-0.35 | body rx -2; weight to the R foot | chest rx -4; head rx -4 | arm_R rx -30, hand_R rx -15 (staff tilts toward the foe) | top rx +40 (censer swings out) |
| 0.35-0.90 | hold | head rx +10 (slow bow, the slit points at the foe), rz +4 | arm_L rx -50, hand_L rx -30, wrist_L curl (beckon) | top rx -30 -> +25 (two swings), sparks |
| 0.90-1.30 | settle | head level | arms drop | censer damped |

**Surrender** (2.2 s, once, holds the last pose) - drops the staff, kneels
| t | Legs / pelvis | Torso / neck / head | Arms / staff | Secondary |
|---|---|---|---|---|
| 0.00-0.30 | stagger: body rx -6, z -0.04 | head rx -10 | wrist_R opens (rx +25) | censer swings back |
| 0.30-0.55 | | | **`weapon` (staff + censer) released at 0.45**: topples forward-right, bounces twice, the censer chain clatters and spills ember coals (VFX) | |
| 0.55-1.20 (io) | kneel: body y -0.26; thigh_L rx -75, shin_L rx +95 (planted +0.10); thigh_R rx +20, shin_R rx +108 | spine rx +10 | arms hang | robe hem pools on the plinth |
| 1.20-1.75 | hold | spine rx +20, chest rx +10, neck rx +20, head rx +30 (the mitre bows; slit faces the plinth) | hands on the thighs, palms up (hand_L/R rx -35) | lappets fall forward |
| 1.75-2.20 | hold | slow breath | hold | |

## 8. Fragments (30)
Coarse: **mitre 4 chunks (the two halves either side of the slit stay as large wedges; the apex stays intact)**, robe 8 slabs (hem 4, mid 4), stole 2, shoulders 2, staff 3 bronze rods, censer 2 + coals 2 glowing lumps. Fine: sleeves 3, belt/beads 3. All chunky stone/bronze with `EH_Interior` ember cores; censer sprays sparks.

## 9. Readability
- **Identity cue**: bronze mitre with a deep diagonal oxblood slit; staff + chained censer.
- vs `rime_bishop`: a bronze mitre (warm, opaque, red-lined slit) on a red robe, bronze staff and heavy hanging censer vs a translucent ice mitre with a glowing cyan slit, a narrow dark silhouette and a pale lantern with orbiting runes. Emberhold fill-black = cone + staff + dangling weight, perimeter/sqrt(area) ~ 4.2.
- vs other roles: the only piece whose dominant head shape is a pointed oval with a diagonal cut; narrowest envelope (0.50); the pawn has a round helm, the queen/king have crowns. The 1.40 staff/1.348 mitre sit between the knight (1.30) and the queen (1.55).
- Silhouette tests: mitre top-width/height ratio 0.63 +-0.05; the slit reads as a >= 4 px dark diagonal at 60 px (value step >= 0.30 vs the bronze).
