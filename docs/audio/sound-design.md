# Sound design notes

Goal: action-packed, impactful, cinematic. Every hit is a stack of four layers, then compressed, loudness-matched and limited.

| Layer | Source | Purpose |
|---|---|---|
| Sub thump | synthesised pitch-dropping sine (`dsp.sub_drop`, tanh-saturated so harmonics survive phone speakers) | chest-weight, the "boom" |
| Crack | first 60-90 ms of a Kenney metal/plate impact, high-passed | sharp transient (median 1 ms to peak) |
| Body | CC0 stone, metal, glass/ice, flesh-armour (thwack), swords, creature calls | the material of the blow |
| Tail | generated impulse response (decaying shaped noise, faction specific) convolved with the mix | stone hall (Emberhold, rt60 ~1.4 s, dark) or ice cavern (Rime, rt60 ~2.3 s, bright) |

Master chain per file (`dsp.master`): 22 Hz high-pass, silence trim, bass-harmonic enhancer, feed-forward compressor (3:1), loudness match to the target maximum momentary K-weighted loudness (-14 LUFS-M for cinematic hits; steps, UI and debris sit lower and are balanced by manifest `gain`), look-ahead limiter at -1 dBFS, fade-out. MP3, mono, 44.1 kHz, 96 kbps (112 kbps for priority-3 hits).

## Palette

- **Rook slam** `hit:rook:*`: mortar-like boom (CC0 explosions low-passed + sub), stone tower collapse (cave-in + boulder + plate impacts), rubble rain (20 scattered rock clips, decaying density). Emberhold adds a fire whoosh; Rime adds ice crack and shard rain.
- **Pawn** `hit:pawn:*`: steel through armour (sword clash high-passed for the shriek, plate + flesh-thwack crunch, blade scrape). Rime: cleaver hack with ice crack and frost hiss.
- **Knight** `hit:knight:*`, `gallop:*`, `step:knight:*`, `rear:*`: hoof clops sliced from a CC0 trot recording, rearing bellow and ghostly whinny designed from pitched, vibrato-modulated CC0 monster/troll/scream recordings, lance impact plus armour clash with an arena crowd roar sweetener.
- **Queen** `hit:queen:*`, `summon:*`: Emberhold hammer ground smash with shockwave rumble; Rime glacial sweeping cut into a crystalline shatter cascade.
- **King** `hit:king:*`: Emberhold heavy cleave with a pitched-down, low-passed "time-slow" copy and sub whoomp; Rime rising ice-spike eruption then backhand and shatter.
- **Bishop** `hit:bishop:*`, `spell:*`: Emberhold fire-wave roar and cracking seams; Rime frost-beam hum, freeze crackle, crystal crack.
- **Shatter** `shatter:<faction>[:light|:heavy]`: bronze/stone chunks with ember hiss and crackle (Emberhold); glass/ice explosion and tinkles (Rime). Tier chosen by defender role.
- **Debris** `debris:<faction>:s1..s3`: three strengths per faction, 2 variations each.
- **Others**: `check` (war drum, horn sting), `mate` (gong, choir swell, drum roll, horn, crowd), `castle` (winch, stone grind, thuds), `promote:*` (holy forge ring / crystal bloom), `clash:*` (+`:heavy` with crowd), `drop:*` (metal bounce and ring / ice on stone), `kneel`, `taunt:*`, `ui:*`, `loading:done`.

## Contract v1.4 cues

Full beat-by-beat mapping: `docs/audio/cue-coverage.md`.

| Cue | Emberhold | Rime |
|---|---|---|
| `slide:F` (loop, 2.4 s, seamless) | dragged concrete slab: stone-door grind + boulder drag granular bed, stick-slip rumble, gritty 0.5-3 kHz top, soft saturation | ice on stone: scrape rasp, tree-creak groan pitched an octave down, stick-slip band noise, Poisson crystalline crackle (glass / ice slivers) |
| `slide:F:start` (lurch) | stone shift + chain clank + grind onset + sub thump | scrape onset + ice tick + creak + thump |
| `slide:F:stop` (settle thud) | boulder drop + plate hit + sub + dust | glass-heavy thump + ice slice + snow crunch + shimmer |
| `shield:flash:F` | bronze bell (fundamental 740/880/988 Hz + 1.5x partial), CC0 ding, shield parry transient, 1.4-9 kHz whoosh of light | inharmonic glass partials (2.1-3.1 kHz fundamental), glass tick, ice sliver, shimmer, 3-12 kHz whoosh |
| `shield:break:F` | three wood cracks cut from the 35-cracks pack, plank + torn metal, 18 scattering rivets, sub, rock debris | cracking ice slab (rising crack rate), slab burst + glass break, scattered glass tinkle, shimmer tail |
| `armour:hit:F[:heavy]` | plate impact + shield-block body + chain + sub | metal impact + glass tick + frost crunch + sub |
| `land:F:s1-3` | concrete step -> plate + boulder drop -> boulder + falling rock + stone shift, sub and dust scale with strength | snow step -> glass-heavy + ice -> glass-heavy + ice slab + glass break + shimmer |
| `sting:draw` | hollow low horn, wind and a muffled drum for stalemate / draw | (shared) |

Loops carry a 0.1 s guard of repeated audio either side of the loop region (`manifest.loop = {start, end}`), so MP3 encoder
padding never lands inside the loop; the body itself is cross-faded (equal power, 0.4 s) and processed on three tiled copies.
Loudness targets (LUFS-M): slide loop -20, lurch -17, settle -16, shield flash -15, shield break -14, armour hit -16 / -14,
land -18 / -16 / -14, draw sting -17 (cinematic hits stay at -14; sustained layers sit lower and are balanced by manifest `gain`).

## Runtime (src/audio)

- `samples.ts`: lazy manifest, decode-on-demand AudioBuffer cache (22 MB budget, LRU, `preload` entries pinned), +-4 % pitch and small gain jitter, no immediate variation repeat, per-key cooldown, 18-voice limit with priority stealing, and a low-priority bus (steps, UI, debris) that ducks to 30 % for ~1 s whenever a priority-3 cinematic hit starts.
- `index.ts`: every event maps to a sample key; the procedural synth in `sfx.ts` plays only if a file is missing or not yet decoded. `capture:begin` warms the hit/shatter/whoosh files seconds before the blow.
- Looping voices (`startLoop / updateLoop / stopLoop`): `move:slide` start opens a loop plus the lurch one-shot, repeated starts retarget
  speed (playback rate 0.78-1.28x, gain 0.4-1x, low-pass 0.7-5.9 kHz, times a per-role weight), stop releases (0.14 s) and plays the
  settle thud. Max 2 loops (oldest released), 6 s failsafe since the last start/update, all loops released when the page is hidden.
- Categories (`categories.ts`): Music / Effects / Ambience / Interface, each a persisted 0..1 gain (`localStorage` key
  `battle-chess.audio.categories`). Music = `musicVolume` x music; Effects, Ambience, Interface = `sfxVolume` x category. API:
  `bus.setCategoryVolume(cat, v)`, `bus.getCategoryVolume(cat)` (also exported from `src/audio`). Key -> category by prefix
  (`categoryOf`): `ui:`/`loading:` -> interface; steps, hooves, slides, debris -> ambience; everything else -> effects.
- `preloadSfx(report)` (also `audio.preload`) fetches and decodes the `preload` entries during the loading screen, before the AudioContext is unlocked (OfflineAudioContext decoding), capped at 9 s.

## Rebuild

```
npm run audio:build            # fetch (licence-verified) -> prep -> design -> encode -> report
node tools/audio/build.mjs --skip-fetch --only=hit:,shatter:   # rebuilds just those keys and merges them over the shipped manifest
node tools/audio/build.mjs --skip-fetch --only=slide:,shield:,armour:,land:,sting:   # contract v1.4 cues
```

Raw downloads and intermediates (`tools/audio/raw`, `tools/audio/work`, ~1 GB) are gitignored and can be deleted after a build.
