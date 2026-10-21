# Capture Choreography

How a capture plays out, per attacking role, plus special moves and the VFX/physics
toolkit. All timings are for "Full" mode; "Quick" scales the whole timeline to ~40 %
and skips the approach walk.

## Contents
1. The capture director (common skeleton)
2. Impact feel: hit-stop, slow-mo, shake
3. Per-attacker sequences (6)
4. Defender response by role & faction
5. Special moves (castling, en passant, promotion, check, mate, stalemate)
6. Camera shot library
7. VFX toolkit
8. Audio hooks

---

## 1. The capture director

`captureDirector.play({ attacker, defender, from, to, flags }) → Promise<void>` builds one
master GSAP timeline with labels, so skip/slow-mo work everywhere:

| Label | What happens |
|---|---|
| `setup` | `cameraRig.borrow()`; pick shot from the attacker's `attackStyle`; dim the rest of the board 30 %; other pieces play a short "look" turn toward the fight |
| `face` | attacker and defender yaw to face each other (0.25 s) |
| `approach` | attacker plays `Move`, translates to `to − dir × strikeRange` (speed ≈ 2.2 units/s, ease `power1.inOut`); defender braces |
| `attack` | attacker's `attackTimeline()` nested here |
| `impact` | at `attack + extras.impactTime`: hit-stop → defender `HitReact` 0.12 s → **shatter** → slow-mo |
| `resolve` | attacker finishes `Attack`, walks the last `strikeRange` onto `to`, plays `Victory` |
| `cleanup` | fragments sink/dissolve, pooled; captured icon flies to the side tray; `cameraRig.restore()` |

Guarantees: when the promise resolves, the attacker sits exactly on `to`, the defender is
removed, the camera is back at the seat, and no tweens remain on actors.

## 2. Impact feel

- **Hit-stop**: tween `gsap.globalTimeline.timeScale()` to 0.03 for 70–110 ms (longer for
  heavier attackers), then back to 0.35 (slow-mo) and ramp to 1.0 over 0.6 s.
  Physics uses `dt × timeScale` so debris slows with everything else.
- **Camera shake**: trauma model (offset = trauma² × noise), trauma 0.35 for pawns, up to
  0.8 for queen/king/rook slams; decays in 0.5 s.
- **Flash**: 1-frame emissive spike on the defender + bloom intensity pulse.
- **Directional debris**: impulse along the strike direction (from `socket_weapon_R`
  velocity at impact, falling back to attacker→defender), magnitude by attacker weight,
  plus random torque; a few fragments get an upward kick so the burst reads in 3D.

## 3. Per-attacker sequences

`attackStyle` decides the shot and approach; the faction decides the VFX flavour.

### Pawn — melee duel (Shieldbearer / Rime Thrall)
Approach to strikeRange 0.55 → Emberhold: draws sword (hand to hip, 0.3 s), shield-bash
staggers the target, overhead chop. Rime: cleaver drag-scrape (frost trail along the floor),
lunging two-hand hack. Impact at ~0.95 s. Shot: `lowSide`. Total ≈ 3.0 s.
En passant variant: sidestep along the rank, horizontal slash, then step forward.

### Rook — the slam (Forge Bastion / Glacier Bastion)
No walk: the tower *hops* along the line (0.25 s per square, small dust/frost puff on each
landing). At the target it rises 1.2 units, hangs 0.15 s, crashes down. Emberhold adds a
brazier fire burst on landing; Rime first fires 3 crown shards that pin the target, then
topples onto it. Shockwave ring + board crack decal (fades over 4 s). Shot: `topDownSlam`
→ cut to `lowSide` for the landing. ≈ 3.2 s.

### Knight — the leap (Ashmane / Gravewind)
Mount rears (0.4 s), parabolic leap along the L path (peak 1.6 units; the leap path
follows the L as a smooth curve, not a straight line), lance/glaive strike on landing.
Emberhold leaves ember trail from the mane; Rime mount headbutts first (ice crack) then the
rider's glaive finishes. Shot: `trackingLeap`. ≈ 3.0 s.

### Bishop — the spell (Cinder Oracle / Frost Chanter)
Bishop stays put or advances only to 1.5 units away. Channel at `socket_cast` (0.6 s,
gathering particles), then:
- Emberhold: censer swing releases a rolling fire wave along the diagonal; target cracks
  with glowing seams, then bursts outward.
- Rime: orbiting runes converge into a beam; target **freezes** (white frost shader
  sweep 0.4 s, `HitReact` frozen mid-pose) then shatters into ice.
Bishop glides onto the square after the burst. Shot: `overShoulder` from behind the
caster. ≈ 3.4 s.

### Queen — the summoned great-weapon (Flamecrown Warden / Pale Tide Queen)
The showpiece. Hero orbit shot starts behind the queen.
1. Summon (0.6 s): particles spiral from the pedestal into `socket_weapon_R`;
   `weapon_summon` scales in (Emberhold hammer-staff forged from embers; Rime crystal
   glaive grown from frost).
2. Advance with the weapon trailing (ribbon trail on).
3. Emberhold: spin and overhead **ground slam** — shockwave, fire column, target and
   nearby floor debris fly. Rime: gliding **sweeping cut** — the arc leaves a frozen
   crescent in the air, target shatters along the cut plane (split fragments into two
   groups by the cut plane and push them apart).
4. Weapon dissolves after `Victory`.
Hit-stop 110 ms, trauma 0.8. ≈ 4.0 s.

### King — the decisive blow (Ember Sovereign / Glacier Tyrant)
Slow, heavy walk (speed 1.4). Emberhold: lifts the greatsword overhead, single cleave,
time slows to 0.2 for 0.8 s. Rime: raises a fist; ice spikes erupt under the target and
lift it, then a backhand shatters it mid-air. Shot: `lowHero` (low angle, wide lens).
≈ 3.8 s.

## 4. Defender response

- `HitReact` always plays for 0.12 s before the shatter so the blow visibly connects.
- Fragment count & mass by defender role: pawn 20, rook/bishop/knight 30, queen/king 40;
  heavier pieces get a 0.2 s longer slow-mo tail.
- Faction flavour of the break:
  - Emberhold breaks like bronze-clad stone: chunky shards, glowing ember interiors,
    spark shower, smoke puff, metal clang.
  - Rime Host breaks like ice: sharp shards with transmission, frost mist, glittering
    micro-particles, high crystalline crash.
- Fragments live 1.6 s, then sink 0.2 units through the board while a dissolve shader
  eats them (edge glow in the faction colour), then return to the pool.

## 5. Special moves

- **Castling**: king and rook move simultaneously; the rook does its hop, the king walks;
  both turn to face forward and plant (small dust puff). Camera stays at the seat.
- **Promotion**: pawn reaches the last rank → a column (fire pillar / ice crystal cocoon)
  engulfs it for 0.8 s; the cocoon cracks and the promoted piece is revealed with its
  `Victory`. If the promoting move also captures, play the pawn capture first.
- **Check**: the checking piece glances toward the king; the king's `socket_head` aura
  pulses (ember red / cyan), a low drum hit, the king tile edge glows. No camera borrow.
- **Checkmate**: slow 360° orbit around the mated king; the king drops to a knee (use
  `HitReact` held), cracks spread over 1.5 s, it crumbles in slow motion; all winning
  pieces play `Victory`; UI overlay after 3 s.
- **Stalemate / draw**: both kings face each other, a neutral grey mist rolls across the
  board, overlay.

## 6. Camera shot library (`cinematics/shots.ts`)

Each shot returns `{ position(t), lookAt(t), fov }` built from attacker/defender world
positions, and is clamped to stay above the board (y ≥ 0.6) and outside other pieces
(raycast against piece colliders; push out if blocked).

- `lowSide` — perpendicular to the strike line, height 0.9, distance 3, FOV 35.
- `overShoulder` — behind the attacker, offset 0.6 to the side, height 1.4, FOV 40.
- `topDownSlam` — high above the target, slight tilt, FOV 45; cut on landing.
- `trackingLeap` — follows the knight's arc from the side, lags 0.1 s.
- `heroOrbit` — starts behind the attacker, orbits 120° to a 3/4 front view during the
  summon.
- `lowHero` — low (0.5) and close, wide FOV 55, looking up at the attacker.

## 7. VFX toolkit (`src/fx/`)

- **Particles**: one pooled GPU system (InstancedMesh quads, billboarded in the vertex
  shader, attributes for life/velocity/size/colour). Presets: `embers`, `sparks`, `smoke`,
  `frostMist`, `iceGlitter`, `summonSpiral`, `dustPuff`.
- **Shockwave**: expanding ring mesh with a fresnel/falloff shader + a screen-space
  distortion pulse (optional on High).
- **Ice spikes**: instanced cones (crystal material) scaled up with `back.out(2)`.
- **Weapon trail**: ribbon from the last 12 positions of `socket_weapon_R`, additive.
- **Frost sweep / ember crack**: shader uniforms on the defender's material
  (`onBeforeCompile` injection): a progress value sweeps a mask from impact point outward.
- **Dissolve**: noise threshold + edge emission; used for fragments and summoned weapons.
- **Board decals**: crack/scorch/frost decals (DecalGeometry) that fade over 4 s.
- **Fake ice (Low/Medium tiers)**: fresnel + matcap + emissive inner-crack texture instead
  of transmission.

## 8. Audio hooks

Event → sound set (randomise pitch ±5 %): `move:step:{faction}`, `attack:whoosh:{role}`,
`impact:{defenderFaction}`, `shatter:{defenderFaction}`, `summon:{faction}`, `spell:{faction}`,
`check`, `mate`. Footstep events come from the clip timeline (`addCallback` at the
foot-down times listed in each choreography file).
