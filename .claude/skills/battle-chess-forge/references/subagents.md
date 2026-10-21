# Subagent Orchestration (Claude Code)

## Setup

Copy the agent definitions into the project so Claude Code can spawn them:

```bash
mkdir -p .claude/agents && cp <skill>/assets/claude-agents/*.md .claude/agents/
mkdir -p scripts blender/lib && cp <skill>/scripts/validate_glb.py scripts/ \
  && cp <skill>/scripts/blender/piece_kit.py blender/lib/
```

The lead (main session) owns `src/contracts/**`, `docs/DECISIONS.md`, `package.json`,
and merges. Agents never edit files outside their ownership list.

## Ownership map

| Agent | Owns | Reads |
|---|---|---|
| lead | `src/contracts/**`, configs, `docs/DECISIONS.md` | everything |
| `art-director` | `docs/art/**` | art-bible, renders |
| `blender-emberhold` | `blender/build/emberhold_*`, `blender/src/emberhold_*`, `assets/models/emberhold_*` | asset-pipeline, art docs |
| `blender-rime` | same pattern for `rime_*` | asset-pipeline, art docs |
| `rig-animator` | `blender/anim/**`, actions inside .blend files | asset-pipeline §5, choreography §3 |
| `engine-core` | `src/core`, `src/assets`, `src/render` (not post.ts), `src/camera`, `src/ui`, `tests` | gameplay-architecture |
| `cinematics` | `src/cinematics/**` | choreography, architecture §4/6/7 |
| `vfx-shaders` | `src/fx/**`, `src/render/post.ts` | choreography §2/4/7, art-bible §6–7 |
| `qa` | nothing (read-only + reports in `docs/qa/`) | all |

## Phase plan with parallelism

```
Phase 0  lead: scaffold, contracts, DECISIONS.md, perft tests green
Phase 1  art-director ──► (blender-emberhold ∥ blender-rime) blockouts ──► qa
Phase 2  engine-core ∥ cinematics ∥ vfx-shaders   (against blockouts)   qa after each merge
Phase 3  blender-emberhold ∥ blender-rime detail pass ──► rig-animator final clips
         ∥ cinematics tuning timings to final clips ; art-director approves turntables
Phase 4  lead + engine-core polish/settings/audio ; qa full regression
```

Hand-offs are files, not conversation: an agent finishes by listing the paths it changed
and the command output proving its check passed (validator, tests).

## Task prompt template

When spawning an agent, give it a self-contained brief:

```
Task: <one sentence outcome>
Asset ids / files: <exact list>
Contract version: 1 (references/asset-pipeline.md §1)
Inputs ready: <paths>
Definition of done: <validator stage / tests / render to produce>
Do not touch: <paths owned by others>
Report: changed paths, check output, open questions
```

### Example briefs

- **blender-rime, Phase 1**: "Build contract-valid blockouts for all six rime_* assets
  using piece_kit, matching heights and signature shapes in art-bible §5. Done when
  `validate_glb.py assets/models --stage blockout` passes for rime_* and fragments exist."
- **cinematics, Phase 2**: "Implement captureDirector with the label skeleton and the
  pawn + rook choreographies. Done when replay.test.ts passes in instant mode and a
  recorded clip of each is in docs/qa/clips/."
- **vfx-shaders, Phase 2**: "Implement particle pool with embers/sparks/frostMist/
  iceGlitter presets and debris.shatter() using rapier, timeScale-aware. Expose APIs in
  src/fx/index.ts. Done when the fx sandbox scene runs at 60 fps Medium with 400 particles."

## Conflict rules

- Contract change needed → agent stops and reports; the lead updates contract + validator
  in one commit and re-briefs affected agents.
- Two agents need the same helper → the lead adds it to `src/contracts/` or a shared util.
- Long-running Blender jobs: run one Blender process per agent; avoid more than two
  simultaneous Cycles bakes on one machine.
