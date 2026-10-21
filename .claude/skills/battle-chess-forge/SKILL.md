---
name: battle-chess-forge
description: Plan, build and ship a cinematic 3D "battle chess" game — detailed PBR chess-piece assets made in Blender (bpy, headless), rigged capture animations where the attacking piece physically fights and shatters its target, a turn-based camera that swings to the active player's side, and a three.js + GSAP web client (with an optional Unity port). Use this skill whenever the user is working on the Chess Game project, asks for chess piece models, faction-themed chess sets, capture/kill animations, fracture or shatter effects for game pieces, chess camera rigs, GLB/glTF game assets for a board game, or wants to split this kind of game build across Claude Code subagents — even if they only mention one piece, one animation, or "make the pieces look better".
---

# Battle Chess Forge

Build a two-faction fantasy chess game where captures are staged fights: the attacker
draws a weapon or casts, strikes, and the defender breaks apart into physics debris.
The camera sits behind whoever's turn it is and cuts to cinematic angles for captures.

The working faction pair is **Emberhold** (bronze, forge-fire, highland warriors — plays
White) versus the **Rime Host** (obsidian armor, glacial ice, frost revenants — plays
Black). Full designs live in `references/art-bible.md`.

## Ground rules that keep the project shippable

1. **Original IP only.** Every piece, name, crest, crown shape and faction is invented
   for this project. Do not model, name, or "nod to" characters, houses, sigils, creatures
   or set pieces from existing franchises (TV series, films, novels, licensed chess sets),
   and do not take reference from a commercial set's sculpts. If an older asset or file in
   the repo carries franchise names, rename it to the art-bible names before building on it.
   This matters because the user intends to release the game, and a clean original set is
   the only kind that can be released.
2. **GLB is the master format.** Blender `.blend` sources → glTF 2.0 binary. Everything
   downstream (three.js, Unity via glTFast) reads the same GLBs.
3. **Contracts before content.** Agents work in parallel, so the asset contract
   (`references/asset-pipeline.md` → "Asset contract") is fixed first: node names, clip
   names, socket names, scale, origin, fragment naming. Code is written against the
   contract, not against a particular model.
4. **Validate every asset.** Run `python scripts/validate_glb.py <file-or-dir>` after any
   export. Do not hand an asset to the engine agent until it passes.
5. **Code-only geometry is a blockout.** Primitive/procedural meshes (lathes, spheres,
   boxes) read as toy-like no matter how many there are. "Detailed" means: sculpted or
   multires-detailed high-poly, retopologised low-poly, baked normal + AO, real PBR
   texture sets, bevelled edges, wear masks. Follow the detail pipeline; don't just add
   more primitives.

## Workflow

Work in phases. Each phase lists what to read and what "done" means.

### Phase 0 — Project scaffold and decisions (lead agent, ~1 session)
- Read `references/gameplay-architecture.md` (stack, folders, state machine).
- Scaffold the repo layout from that file. Pin dependency versions at least two weeks old.
- Write `docs/DECISIONS.md` recording: target platform (web first), performance budget,
  local hot-seat vs AI, art-bible faction names. Ask the user only about things that change
  the build (AI opponent yes/no, mobile support yes/no).
- Done when: `npm run dev` shows an empty lit board with orbit camera and a working
  rules engine (chess.js) passing the perft tests in `references/gameplay-architecture.md`.

### Phase 1 — Asset contract + blockouts (art-director + blender agents)
- Read `references/art-bible.md` and `references/asset-pipeline.md`.
- Produce 12 blockout GLBs (6 roles × 2 factions) that already satisfy the contract:
  correct names, armature with required bones, all required clips (can be crude),
  sockets, and pre-fractured fragment sets. Placeholder geometry is fine here.
- Done when: all 12 pass `validate_glb.py --stage blockout` and load in the engine.
- Don't make engine work wait for this: on day one run
  `python scripts/make_placeholder_glbs.py --out assets/models` to get 24 contract-valid
  stand-ins, and start Phase 2 in parallel.

### Phase 2 — Engine + camera + capture choreography (engine, cinematics, vfx agents in parallel)
- Read `references/gameplay-architecture.md` and `references/capture-choreography.md`.
- Implement: board & tiles, piece loading via the asset registry, picking/legal-move
  highlights, turn camera swing, the capture director, fracture + debris physics,
  faction VFX, special-move sequences (castling, en passant, promotion, check, mate).
- Done when: a full scripted game (`tests/games/*.pgn`) replays end-to-end with every
  capture type firing its sequence, no frame over budget on the reference machine.

### Phase 3 — Detail pass (blender agents, one per faction, in parallel)
- Replace blockouts with final assets via the detail pipeline in `asset-pipeline.md`
  (high-poly → retopo → bake → texture → LODs → fragments rebuilt from final mesh).
- Keep names and clip timings identical to the blockout so nothing downstream breaks.
- Done when: all 12 pass `validate_glb.py --stage final` and a side-by-side turntable
  render of the set is approved by the user.

### Phase 4 — Polish, audio, QA, ship
- Sound hooks fire from animation events; settings menu (camera mode, animation speed,
  "skip captures"); accessibility (move list, colour-blind highlight option).
- QA agent runs rule tests, asset validation, perf captures; fix regressions.

## Subagents

When running in Claude Code, delegate using the roster and prompts in
`references/subagents.md`. Summary of who can run at the same time:

| Phase | Parallel agents |
|---|---|
| 1 | `blender-emberhold` ∥ `blender-rime` (after `art-director` writes design sheets) |
| 2 | `engine-core` ∥ `cinematics` ∥ `vfx-shaders` (all against blockout GLBs) |
| 3 | `blender-emberhold` ∥ `blender-rime` ∥ `rig-animator` (clips) ; `qa` runs continuously |

Give each subagent the exact files it owns. Two agents never edit the same file; shared
types live in `src/contracts/` and only the lead edits them.

## Which reference to read when

- Designing or describing a piece, colours, materials, names → `references/art-bible.md`
- Making, rigging, fracturing, exporting a model; naming rules; poly/texture budgets → `references/asset-pipeline.md`
- Repo layout, rules engine, state machine, input, turn camera, loading → `references/gameplay-architecture.md`
- What each piece does when it captures; timing; debris; camera cuts; special moves → `references/capture-choreography.md`
- Spawning Claude Code subagents and their prompts → `references/subagents.md`
- Porting to Unity → `references/unity-port.md`

## Scripts and assets

- `scripts/make_placeholder_glbs.py` — dependency-free; writes all 24 contract-valid
  placeholder GLBs (pieces + fragments) so engine/cinematics/VFX can start immediately.
- `scripts/validate_glb.py` — dependency-free GLB checker for the asset contract
  (names, clips, sockets, fragments, triangle budget, texture sizes, base at origin).
  `--stage blockout|final`, `--json` for machine-readable output.
- `scripts/blender/piece_kit.py` — bpy helper module: pedestal generator, bevel/weighted
  normals, armature template with sockets, cell-fracture wrapper, NLA clip naming,
  contract-correct glTF export. Run with `blender -b -P your_piece.py`.
- `scripts/blender/example_pawn.py` — builds the Emberhold Shieldbearer blockout (expects
  piece_kit in `blender/lib/` or next to it). Template for the other 11 build scripts.
- `assets/claude-agents/*.md` — ready Claude Code subagent definitions; copy to
  `.claude/agents/` (see `references/subagents.md`).

The Blender scripts target Blender 4.2+ and were written without a Blender binary
available; run them first on one piece, fix any API drift, then fan out.
