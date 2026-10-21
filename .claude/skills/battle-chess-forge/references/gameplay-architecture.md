# Gameplay Architecture (three.js web client)

## Contents
1. Stack
2. Repo layout
3. Coordinates
4. Game state machine
5. Rules engine & tests
6. Asset registry & PieceActor
7. Turn camera rig
8. Input
9. Rendering & quality tiers
10. Settings that must exist

---

## 1. Stack

- **Vite + TypeScript** (strict).
- **three** (WebGLRenderer; keep WebGPU behind a flag until stable on target browsers).
  Addons: `GLTFLoader`, `KTX2Loader`, `MeshoptDecoder`, `SkeletonUtils`, `RGBELoader`/HDR.
- **gsap** — all camera moves, capture choreography timelines, UI tweens.
- **chess.js** — rules, legality, SAN/FEN/PGN. The game never implements its own rules.
- **@dimforge/rapier3d-compat** — debris physics for fragments only (pieces are kinematic).
- **postprocessing** (pmndrs) — bloom (emissive only, luminance threshold), SMAA, vignette,
  optional chromatic aberration pulse on impacts.
- Optional AI: Stockfish WASM build in a Web Worker (UCI over `postMessage`). Check the
  engine build's licence (GPL) before bundling it in a closed-source release.

Pin exact versions at project start; choose releases at least two weeks old.

## 2. Repo layout

```
blender/build/            one bpy build script per asset ({asset_id}.py)
blender/src/              .blend sources (Git LFS)
assets/models/            exported GLBs (+ _fragments.glb)
assets/env/               HDRI, board textures
assets/audio/             sfx by event name
scripts/validate_glb.py   copied from this skill
src/contracts/            assetContract.ts, events.ts, types.ts   ← lead-owned
src/core/                 game.ts, stateMachine.ts, rules.ts, ai/stockfishWorker.ts
src/assets/               registry.ts, pieceActor.ts, fragmentPool.ts
src/render/               scene.ts, board.ts, lighting.ts, post.ts, quality.ts
src/camera/               cameraRig.ts
src/cinematics/           captureDirector.ts, choreographies/{role}.ts, specialMoves.ts
src/fx/                   particles.ts, debris.ts, shaders/{ember,frost,dissolve}.ts
src/audio/                audioBus.ts
src/ui/                   hud.ts, moveList.ts, promotionPicker.ts, settings.ts
tests/                    rules.perft.test.ts, replay.test.ts, games/*.pgn
```

## 3. Coordinates

- 1 unit = 1 square. Board centred at origin, top surface at y = 0.
- `x = fileIndex − 3.5` (a = 0 … h = 7); `z = 3.5 − rankIndex` (rank 1 = 0 … 8 = 7).
  So White (Emberhold) sits on +z looking toward −z.
- Rime pieces are rotated 180° about Y so their +Z front faces White.
- Helpers live in `src/contracts/types.ts`: `squareToWorld(sq)`, `worldToSquare(v)`.

## 4. Game state machine

```
Boot → Loading → TurnStart → AwaitInput → Resolving → (MoveSeq | CaptureSeq)
     → PostMove → (Promotion?) → TurnEnd → TurnStart …   GameOver on mate/draw
```

- `TurnStart`: camera rig swings to the side-to-move (unless camera mode says otherwise);
  if side-to-move is AI, request a move from the worker instead of AwaitInput.
- `Resolving`: `rules.move()` first (authoritative). Only after the rules accept the move
  does any animation start, so visuals can never desync from the position.
- Sequences are `async` functions returning a Promise; the state machine `await`s them.
  Every sequence must be skippable: it builds a GSAP timeline and exposes `skip()` which
  calls `tl.progress(1)` and snaps actors to their final transforms.
- `PostMove`: detect check/checkmate/stalemate/draws from chess.js and trigger
  `specialMoves.check()` or `specialMoves.checkmate()`.
- Emit events from `src/contracts/events.ts` (`turn:start`, `move:resolved`,
  `capture:begin`, `capture:impact`, `capture:end`, `check`, `game:over`) so audio and UI
  subscribe without coupling.

## 5. Rules engine & tests

`rules.ts` wraps chess.js and exposes `legalMovesFrom(sq)`, `move(from,to,promotion?)`
returning `{ san, captured, flags, isCastle, isEnPassant, promotion, check, mate }`.

Tests (Vitest), implemented with `moves()/move()/undo()` recursion:
- perft(start, 1..4) = 20, 400, 8 902, 197 281
- perft("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 1..3)
  = 48, 2 039, 97 862
- `replay.test.ts`: replay each PGN in `tests/games/` through the state machine in
  headless "instant" mode (all sequences skipped) and assert final FEN matches.
  Include PGNs covering: both castlings, en passant, under-promotion, every
  attacker-role × defender-role capture, checkmate, stalemate.

## 6. Asset registry & PieceActor

- `registry.preload()` loads the 12 piece GLBs in parallel at Loading; fragments load
  lazily the first time a piece of that asset id is captured, then are pooled.
- Clone skinned pieces with `SkeletonUtils.clone()` — `Object3D.clone()` breaks skinning.
- `PieceActor` holds: `root`, `mixer` (AnimationMixer), `actions` by clip name, `extras`
  (from `root.userData` — GLTFLoader puts glTF extras there), `sockets` by name,
  `square`, `side`, `role`.
- `actor.play(clip, {fade})`, `actor.attackTimeline()` returns a GSAP timeline whose
  label `"impact"` sits at `extras.impactTime`, built by scrubbing
  `action.time` from GSAP (`onUpdate`) rather than letting the mixer free-run. Keeping
  GSAP as the single clock makes slow-motion and skip trivial.
- Validate on load: if a required clip/socket is missing, log a contract error and use a
  procedural fallback (tween the root) so the game still runs.

## 7. Turn camera rig

- Camera orbits a target at the board centre using a spherical proxy
  `{ azimuth, polar, radius, targetY }`. Tween the proxy with GSAP and rebuild the camera
  transform in `onUpdate`. Never lerp positions across the board — that dives through
  the pieces. Always rotate azimuth by the shorter arc to the seat.
- Seats: White azimuth 0, Black azimuth π; polar ≈ 52°, radius ≈ 11.5 (tune so the
  whole board fits at 16:9 and at 4:3; recompute radius on resize from FOV).
- Turn swing: 1.4 s `power2.inOut`, with a slight radius push-out (+1.0) mid-swing and a
  0.15 s settle.
- Modes (setting): **Follow turn** (hot-seat default), **Fixed to my side** (vs AI),
  **Free orbit** (OrbitControls enabled, limited polar range), **Top-down**.
- Cinematic hand-off: `cameraRig.borrow()` returns control to the capture director and
  `cameraRig.restore()` tweens back to the current seat.
- Small idle drift (±0.6° azimuth sine over 8 s) keeps the scene alive while waiting.

## 8. Input

- Tiles are one `InstancedMesh` (64 instances); raycast → `instanceId` → square.
- Pieces raycast against a simple invisible cylinder collider per actor (not the skinned
  mesh — raycasting skinned meshes is slow and imprecise).
- Click-click and drag-drop both supported. On select: lift piece 0.12 (GSAP), show
  legal destination markers (glow discs; red-tinted ring on capturable squares).
- Block input while a sequence runs; queue at most one "skip" click.
- Promotion: show `promotionPicker` with the four faction-styled options.

## 9. Rendering & quality tiers

- `renderer.outputColorSpace = SRGBColorSpace`, tone mapping AgX (or ACES), exposure ~1.
- One shadow-casting directional key light (2048² map, tight frustum around the board),
  warm; cold rim light from the Rime side; HDRI for IBL only (background is the scene).
- Tiers (`quality.ts`, auto-picked from a 2 s benchmark, overridable):
  - **High**: LOD0, transmission ice, bloom + SMAA, 2048 shadows, 400 debris particles.
  - **Medium**: LOD0 for focus pieces / LOD1 rest, fake-refraction ice, bloom.
  - **Low/mobile**: LOD1, no transmission, 1024 shadows, 120 particles, no SMAA.
- Budget: 60 fps on a mid-range laptop iGPU at Medium; capture sequences may dip to
  45 fps but never below 30.

## 10. Settings that must exist

Camera mode · capture animations (Full / Quick ≈ 40 % length / Off) · animation speed ·
quality tier · sound volumes · colour-blind move highlights · show move list.
