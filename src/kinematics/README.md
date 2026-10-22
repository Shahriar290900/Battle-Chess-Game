# Kinematics layer

Procedural secondary motion applied AFTER the clip pose each frame. `createKinematics(): KinematicsApi & KinematicsExtras`.

It only writes bone rotations (`body`/`mount_body`, `spine`, `head`, `mount_head`, `top`) plus `body` position-y (hop) and scale
(landing squash). It reads, and never writes, `actor.root` and `actor.model` (position, rotation). `weapon` and arm bones are untouched.
Layering is additive and drift-free: if the mixer rewrote a channel we layer on the new clip value, if the channel is static we
undo our previous offset first (see `bones.ts`).

## Engine-core calls
| When | Call |
|---|---|
| actor spawned (`createActor`/`spawnActor`) | `kin.attach(actor)` (after it is added to the scene) |
| actor removed / shattered / disposed | `kin.detach(actor)` (restores the clip pose) |
| every frame | `kin.update(dt)` AFTER all `actor.update(dt)` (mixer) and after cinematics/GSAP have moved `root`/`model`, BEFORE render. Pass the same time-scaled dt as the mixers (`dt * timeScale`): slow motion then slows springs too. `dt <= 0` is a no-op. |
| settings change | `kin.setEnabled(graphics.secondaryMotion)`. Off = zero cost, bone offsets restored; on = resumes from rest. |
| once (optional) | `kin.setCamera(rig.camera)` enables culling of actors > 26 u from or behind the camera. Hidden actors (`setFade(0)` => `model.visible=false`) are always skipped. |

`attach` is idempotent. Pieces teleported by `syncToFen`/undo (> 30 u/s apparent speed) are treated as warps: no inertial kick.
Assumes `root.parent` has an identity transform (the board scene), as everywhere else in the project.

## Cinematics calls
- `kin.lookAt(actor, worldPoint, weight = 1)`: head (humanoids, ±70 yaw / ±30 pitch, remainder to `spine`), `mount_head` + rider head
  (knights), `body`+`top` yaw (rooks). The point is COPIED, so call it again each frame to track a moving target, or once for a static one.
  Blends in over ~0.25 s. `lookAt(actor, null)` releases (blends out). Use for spectators watching a fight, and for the king while
  being checked (call `lookAt(king, checker.socketWorld('socket_head', v))`; release when the sequence ends).
- `kin.impulse(originWorld, strength, radius = 3)`: call at `capture:impact` (strength ~1.5 for pawn victims up to ~3 for slams)
  and when a leaping/slamming piece lands (origin = landing point, strength 1-2). Horizontal falloff `(1 - d/r)^2`, divided by role
  mass (pawn 0.6, bishop 0.9, knight 1.3, queen 1.3, king 2.0, rook 2.4). Strong hits on light pieces (mass <= 1) also hop a few cm.
  Wobble lasts ~0.6-1.2 s. The attacker and victim are scrub-gated (below) or removed, so they are not disturbed.
- Landing squash is automatic: a downward root/model speed > 1.5 u/s that is arrested (e.g. a knight leap) squashes `body`.

## Scripted clips
While the actor is in scrub mode (`actor.mode === 'scrub'`: `scrub()`, `attackTimeline()`, `clipTimeline()`: Attack, HitReact, Victory,
Taunt, Surrender) the additive layer fades to zero (~0.1 s) so it never fights a clip. It fades back in after `play()`.
Once-clips started with `actor.play()` (free mode) are not detected; prefer the timelines for scripted gestures.

## Tuning
`tables.ts`: per-role springs (`ROLE_CFG`) and look limits. Missing bones are skipped silently (placeholders, older GLBs);
an actor with no bones is a no-op. Cost: ~0.11 ms per update for 32 actors (node and in-browser), ~0 when disabled.
