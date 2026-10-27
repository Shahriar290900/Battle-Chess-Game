# Playtest duel

A scripted duel through the **real UI**: two personas play Battle Chess in headless Brave using screen-coordinate
clicks, taps, drags, menus, settings and dialogs. The harness only reads game state through the `window.__bc` debug
hook (`?debug`) and uses it to *set up* scenario positions (`controller.newGame({fen})`); every move is real input.

## Run

```sh
export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH"   # if node/npx are missing
node tests/playtest/duel.mjs
```

It starts its own Vite server (default port **5391**, never 5173) and ONE headless Brave, and closes only those.
Expect 15-25 minutes on software GL (cold start alone is 1-2 min).

Environment variables:

| var | default | meaning |
|---|---|---|
| `PLAYTEST_PORT` | 5391 | dev-server port (5173 is refused) |
| `PLAYTEST_SEED` | 20261023 | seeds Chaos's move choice and engine noise |
| `PLAYTEST_BUDGET_MIN` | 24 | time budget; remaining phases are skipped when it runs out |
| `PLAYTEST_ONLY` | all | comma list of phases: `duel,scenarios,careful-vs-ai,chaos-vs-ai,phone` |
| `PLAYTEST_DUEL_PLIES` | 70 | ply cap of the duel game (Chaos resigns via the pause menu if no result by then) |

## The personas

* **Careful** (White): moves from a depth-3 alpha-beta engine (`lib/engine.mjs`, chess.js + material/PST eval, seeded noise)
  using click-click. Opens the move list and compares it with the rules, changes settings mid-game (Animations
  Quick/Off, animation speed, tile highlights, colour-blind, graphics preset High/Low), pauses/resumes, undoes, uses the
  J shortcut, takes a mate back with Undo from the game-over state, replays it and asks for a Rematch. Also finishes a
  mate-in-1 scenario and plays one vs-Computer (Easy) game (undo of an exchange, "Thinking" HUD check, resign).
* **Chaos** (Black): random/aggressive legal moves plus edge cases: off-board misclicks, selecting the wrong colour,
  double-click, illegal destinations, undo spam (U key and button), drag-and-drop, drags to illegal squares and outside
  the canvas, Escape/pause during a sequence, tap/Space/keyboard spam during cinematics, viewport changes mid-move
  (1280x720 -> 390x844 -> 844x390 -> 1280x720), settings during a sequence, Main Menu mid-sequence + Continue.
  Scenario games (FEN set-up, UI moves): castling both sides and an illegal castle, en passant, promotion to
  queen (with picker cancel via Escape and board clicks while the picker is open), knight (with capture), rook,
  bishop, black promotion, stalemate (plus undo out of it), insufficient material, resign/rematch/Continue, the
  main-menu Resign arm timeout, Credits/How to Play, keyboard menu navigation. One vs-Computer (Easy) game as Rime Host
  (clicks while the AI thinks, pause/undo/Main Menu while it thinks, viewport hops) and a **phone touch** game in a second
  context (390x844, `isMobile`, `hasTouch`: taps, CDP touch drag, long-press tooltip, rotation to landscape).

## Output (`tests/playtest/out/`, wiped at each run)

```
out/summary.json                 phases, per-persona counts
out/<careful|chaos>/
  actions.jsonl     every action: ts, t, phase, action, target, expected_fen vs observed_fen, UI state, latency
  anomalies.jsonl   deduplicated anomalies: type, severity, detail, screenshot, data
  console.jsonl     console errors/warnings, page errors, failed requests (with phase)
  latency.jsonl     per-sample latency (ms)
  fps.jsonl         frame-time stats per game segment, bucketed idle / sequence / ai, plus long tasks
  shots/            key-moment shots and anomaly shots (anom-NNN-<type>.jpg (JPEG q60; all shots of a run capped at 20 MB))
  summary.json      counts by action, anomalies by type, games, latency p50/p95, fps, console digest
```

### Notes for reviewers
* The dev machine is often shared; timeouts scale with host load (`D.T`) and `stuck-sequence` anomalies record the load
  average. Treat sequence/latency numbers from a run with load > ~20 as inflated. A quiet-machine full run takes ~14 min.
* Positions for scenario games are set via `controller.newGame({fen})` (setup only); `harness-exception` and
  `harness-illegal-move` anomalies are harness faults, everything else is a candidate game finding.
* A failed drag falls back to click-click and is reported as `drag-not-accepted` / `touch-drag-not-accepted` with the
  pointer events seen by the page (`data.pointerEvents`); the touch drag is flaky (passes in some runs).
* `illegal-input-played-a-move` after a double-click on a tall piece is reproducible: the second click lands on the
  upper body of the selected piece and resolves to the legal destination tile behind it.

### Latency kinds
All taken from in-page timestamps (`pointerdown` event timestamp to the app event), so polling jitter is excluded:
`select` (pointerdown to `ui:select`), `select-visual` (to the next animation frame), `move-accept`, `move-start`
(first `move:step`/`capture:begin`/...), `move-first-frame`, `sequence-quiet`/`sequence-capture` (move accepted to
back at `awaitInput`), `game-start-to-ready`, `setting-apply-2frames`.

### FPS
Headless software GL makes absolute fps meaningless. `fps.jsonl` reports frame-time mean/sd/p50/p95/p99/max, count of
frames > 100 ms / > 250 ms, `longtasks` (count/total/max ms) and `stalls` (> 1 s gaps), split by controller state.

### Anomaly types
`board-desync` (3D actors vs chess.js FEN: wrong/missing/ghost/duplicate actor, off-square, invisible, left lifted),
`fen-mismatch`, `move-not-accepted`, `no-select-feedback`, `selected-piece-not-lifted`, `stuck-sequence` (> 8 s) /
`stuck-sequence-fatal` (50 s, with Space/Skip/Escape recovery tries), `invisible-modal-blocks-input`,
`screen-visible-but-input-live`, `hud-turn-mismatch`, `captured-tray-mismatch`, `journal-mismatch`, `offscreen`,
`overlap`, `text-overflow`, `text-clipped-y`, `touch-target` (< 40 px on phone-size viewports), `no-tooltip`,
`tooltip-not-shown`, `tooltip-clipped`, `board-clipped`, `hud-covers-board`, `square-unreachable` (a UI element sits
on a board square), `ui-click-failed`, `setting-not-applied`, `gameover-*`, `promotion-*`, `undo-*`, `page-error`,
`harness-exception` (a harness bug, not a game bug). Layout findings are deduplicated per element x layer x viewport.
`severity` is `info` for `no-tooltip`/`touch-target`, `error` for state corruption, `warn` otherwise.

## Layout

`duel.mjs` (phases and personas), `lib/driver.mjs` (UI driver and checks), `lib/page.mjs` (functions that run inside the
page), `lib/recorder.mjs` (output sink), `lib/engine.mjs` (move chooser).
