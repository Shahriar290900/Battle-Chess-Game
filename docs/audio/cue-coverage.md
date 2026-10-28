# Audio cue coverage

Every beat of every choreography and special move, the bus event it emits, the sample key the audio module plays
(`src/audio/index.ts`) and the files behind that key (`public/audio/sfx/manifest.json`). `F` = faction (`emberhold` | `rime`).
Emission sites are in `src/cinematics/**`; the audit is enforced by `tests/cinematics/audioCues.test.ts`.

Categories (see `src/audio/categories.ts`): **E** effects, **A** ambience, **I** interface, **M** music. Master volumes
(`musicVolume`, `sfxVolume`) multiply the category volume.

## Event -> key -> files

| Event | Sample key | Files (variations) | Cat |
|---|---|---|---|
| `move:step` (walk footfall, hop landing) | `move:step:F`, `step:knight:F`, `step:heavy:F` | `move_step_F__0-2`, `step_knight_F__0-2`, `step_heavy_F__0-1` | A |
| `move:slide` start | loop `slide:F` (+ lurch `slide:F:start`) | `slide_F__0-1` (seamless 2.4 s loop, guard 0.1 s), `slide_F_start__0-1` | A |
| `move:slide` stop | `slide:F:stop` (settle thud) + loop release | `slide_F_stop__0-1` | A |
| `attack:whoosh` | `attack:whoosh:ROLE[:rime]` | `attack_whoosh_ROLE[_rime]__0-1` | E |
| `capture:impact` | `hit:ATTACKER:F` | `hit_ROLE_F__*` | E |
| `clash` | `clash:F[:heavy]` | `clash_F[_heavy]__*` | E |
| `shield:flash` | `shield:flash:F` | `shield_flash_F__0-2` (Emberhold bronze bell + parry + light whoosh; Rime glassy ring) | E |
| `shield:break` | `shield:break:F` | `shield_break_F__0-1` (Emberhold splintering wood, torn metal, scattering rivets; Rime cracking ice slab then shatter) | E |
| `armour:hit` light / heavy | `armour:hit:F`, `armour:hit:F:heavy` | `armour_hit_F[_heavy]__0-2` | E |
| `land` strength < .34 / < .67 / else | `land:F:s1` / `s2` / `s3` (`land:F` = s2) | `land_F_s1-3__0-1` | E |
| `capture:shatter` | `shatter:F[:light|:heavy]` | `shatter_F[_tier]__*` | E |
| `debris:impact` | `debris:F:s1-3` | `debris_F_s1-3__*` | A |
| `summon` / `spell` | `summon:F` / `spell:F` | `summon_F__*`, `spell_F__*` | E |
| `castle` | `castle` | `castle__0-1` | E |
| `promotion` | `promote:F` | `promote_F__*` | E |
| `check` | `check` | `check__0-1` | E |
| `taunt` | `taunt:F` / `rear:F` (knight) | `taunt_F__*`, `rear_F__*` | E |
| `surrender` | `kneel` | `kneel__0-1` | E |
| `weapon:drop` | `drop:F` | `drop_F__*` | E |
| `game:over` checkmate | `mate` | `mate__*` | E |
| `game:over` stalemate / draw | `sting:draw` | `sting_draw__0` | E |
| `capture:begin` knight | `gallop:F` | `gallop_F__*` | A |
| `ui:*`, `loading:done` | `ui:*`, `loading:done` | `ui_*__*`, `loading_done__0` | I |

Slides are looped voices (`samples.startLoop/updateLoop/stopLoop`): pitch 0.78-1.28x, gain 0.4-1x and low-pass 0.7-5.9 kHz follow
`speed` (squares per second, timeline time-scale included), times a per-role weight (pawn 1.12 ... king 0.80). At most 2 loops run
at once (the oldest is released) and any loop is auto-stopped 6 s after its last start/update.

## Beat table

`slide` = `move:slide` start/stop pair (balanced, forced stop on skip/watchdog/finish). `step` = `move:step`.

### Non-capture moves (`moveSequence.ts`)

| Beat | Event(s) | Notes |
|---|---|---|
| Pawn / bishop / queen glide | `slide` around the walk, `step` per footfall | `Stage.walk` |
| King heavy walk | `slide`, `step` every 0.5 s | |
| Rook hops (per square) | `step` + `land` (0.4) per hop landing | `Stage.hop`, no slide (airborne) |
| Knight leap | `step` + `land` (0.55) on landing | no slide (airborne) |
| Quick mode | pieces are placed, no slide | resolve walk still slides |

### Captures (`captureDirector.ts` + `choreographies/*`)

| Beat | Event(s) | Sample |
|---|---|---|
| Setup | `capture:begin` (ducks music, warms hit/shatter/slide/armour/land/shield files) | |
| Approach: pawn walk (+ Rime drag-scrape) | `slide`, `step` | `slide:F`, `move:step:F` |
| Approach: en-passant sidestep | `slide` (0.25 s glide) | `slide:F` |
| Approach: bishop / queen / king walk | `slide`, `step` (king: heavy) | |
| Approach: rook hops | `step` + `land` per hop | `land:F:s2` |
| Approach: knight rear + leap | `attack:whoosh` at lift-off | |
| Knight landing | `step`, `land` (0.7) | `land:F:s2/s3` |
| Emberhold pawn draw / shield bash | `shield:flash` (attacker F) + `armour:hit` light (defender F) | `shield:flash:F`, `armour:hit:F` |
| Rime knight headbutt (ice crack) | `armour:hit` heavy | `armour:hit:rime:heavy` |
| Rime rook crown shards (x3) | `armour:hit` light each, ~0.2 s after launch | `armour:hit:rime` |
| Rime king ice spikes | `spell` + `armour:hit` heavy | |
| Wind-up / strike | `attack:whoosh` 0.22 s before impact | `attack:whoosh:ROLE` |
| Queen summon | `summon` | `summon:F` |
| Bishop channel | `spell` | `spell:F` |
| Shield-bearing defender (any pawn) blocks | `shield:flash` (defender F) 0.04 s before impact | `shield:flash:F` |
| Impact | `capture:impact` (+ `clash` for non-bishops) | `hit:ROLE:F`, `clash:F` |
| Rook slam landing | `land` (0.9) | `land:F:s3` |
| Queen Emberhold ground slam | `land` (0.85) | `land:F:s3` |
| Queen Rime glaive sweep | `slide` (0.9 s glide), `armour:hit` light 0.12 s before impact | |
| Bishop seams crack / frost bites | `armour:hit` light at half the sweep | |
| Shatter | `capture:shatter` (+ `shield:break` for shield-bearing defenders) | `shatter:F[:tier]`, `shield:break:F` |
| Debris rain | `debris:impact` (fx) | `debris:F:s1-3` |
| Resolve glide onto `to` | `slide` | |
| Victory / cleanup | `capture:end` (unducks) | |
| Mode `off` | `slide` for the 0.35 s lunge, `shield:flash`, `capture:impact`, `shield:break`, `capture:shatter` | |
| Skip / watchdog | every open slide gets its `stop` before `capture:end` | |

### Special moves (`specialMoves.ts`)

| Beat | Event(s) |
|---|---|
| Castling king walk | `slide`, `step` |
| Castling rook high hop | `land` (0.8) + `step` when it drops, then `castle` |
| Promotion column | `promotion` |
| Checkmate: king kneels | `surrender`, `weapon:drop`, `land` (0.7) as the knees meet the floor, then `game:over` -> `mate` |
| Checkmate: every loser drops its weapon | `weapon:drop` per piece (staggered) |
| Stalemate | `game:over` -> `sting:draw` |

### Check provoke (`provoke.ts`)

| Beat | Event(s) |
|---|---|
| Taunt starts | `taunt` |
| Pawn weapon-beats on the shield (x3) | `shield:flash` each |
| Pawn with Taunt clip | `shield:flash` at the weapon beat |
| Rook lurch and return | `slide` x2, `land` (0.4) on return |
| Knight rear and snort | `taunt` (rear), `land` (0.5) when the forelegs come down |
| Bishop swirl | `spell` |
| Queen point | `summon` |
| King fist raise | `taunt` |
| Off mode | `taunt` only |

### Attract mode

Plays the real sequences, so it inherits every cue above (and the stop-on-skip guarantee).
