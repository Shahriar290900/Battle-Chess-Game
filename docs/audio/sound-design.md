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

## Runtime (src/audio)

- `samples.ts`: lazy manifest, decode-on-demand AudioBuffer cache (22 MB budget, LRU, `preload` entries pinned), +-4 % pitch and small gain jitter, no immediate variation repeat, per-key cooldown, 18-voice limit with priority stealing, and a low-priority bus (steps, UI, debris) that ducks to 30 % for ~1 s whenever a priority-3 cinematic hit starts.
- `index.ts`: every event maps to a sample key; the procedural synth in `sfx.ts` plays only if a file is missing or not yet decoded. `capture:begin` warms the hit/shatter/whoosh files seconds before the blow.
- `preloadSfx(report)` (also `audio.preload`) fetches and decodes the `preload` entries during the loading screen, before the AudioContext is unlocked (OfflineAudioContext decoding), capped at 9 s.

## Rebuild

```
npm run audio:build            # fetch (licence-verified) -> prep -> design -> encode -> report
node tools/audio/build.mjs --skip-fetch --only=hit:,shatter:
```

Raw downloads and intermediates (`tools/audio/raw`, `tools/audio/work`, ~650 MB) are gitignored and can be deleted after a build.
