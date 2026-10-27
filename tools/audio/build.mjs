// Reproducible SFX pipeline:  npm run audio:build
//   1. fetch  CC0 source packs (licence-verified)         -> tools/audio/raw/        (gitignored)
//   2. prep   decode to 44.1 kHz mono WAV                  -> tools/audio/work/src/   (gitignored)
//   3. design python3 design.py (numpy/scipy layering)     -> tools/audio/work/out/   (gitignored)
//   4. encode ffmpeg-static -> MP3, write manifest.json    -> public/audio/sfx/
//   5. report numeric analysis                             -> docs/audio/sfx-report.md
// Flags: --skip-fetch, --only=<key-prefix>[,<prefix>]  (design/encode only those keys)
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, readdirSync, rmSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const ffmpeg = createRequire(import.meta.url)('ffmpeg-static');
const args = process.argv.slice(2);
const only = (args.find((a) => a.startsWith('--only=')) ?? '').slice(7).split(',').filter(Boolean);
const run = (cmd, a, opts = {}) => execFileSync(cmd, a, { stdio: 'inherit', cwd: here, ...opts });

if (!args.includes('--skip-fetch') && !existsSync(join(here, 'raw', 'sources.lock.json'))) run('node', [join(here, 'fetch.mjs')]);
run('node', [join(here, 'prep.mjs')]);
run('python3', [join(here, 'design.py'), ...only]);

const reg = JSON.parse(readFileSync(join(here, 'work', 'registry.json'), 'utf8'));
const outDir = join(root, 'public', 'audio', 'sfx');
mkdirSync(outDir, { recursive: true });
const entries = {};
for (const [key, e] of Object.entries(reg.entries)) {
  const files = [];
  for (const base of e.files) {
    const src = join(here, 'work', 'out', `${base}.wav`);
    const name = `${base}.mp3`;
    const kbps = e.priority === 3 ? 112 : 96;
    execFileSync(ffmpeg, ['-v', 'error', '-y', '-i', src, '-ac', '1', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', `${kbps}k`, '-map_metadata', '-1', join(outDir, name)]);
    files.push(name);
  }
  const ent = { files, gain: e.gain, priority: e.priority };
  if (e.preload) ent.preload = true;
  if (e.cooldown) ent.cooldown = e.cooldown;
  entries[key] = ent;
}
for (const [k, target] of Object.entries(reg.aliases)) if (entries[target]) entries[k] = { ...entries[target] };
const keys = Object.keys(entries).sort();
const manifest = { version: 1, entries: Object.fromEntries(keys.map((k) => [k, entries[k]])) };
writeFileSync(join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 1));
// remove stale mp3s not referenced
const used = new Set(Object.values(entries).flatMap((e) => e.files));
if (!only.length) for (const f of readdirSync(outDir)) if (f.endsWith('.mp3') && !used.has(f)) rmSync(join(outDir, f));
const total = readdirSync(outDir).filter((f) => f.endsWith('.mp3')).reduce((n, f) => n + statSync(join(outDir, f)).size, 0);
console.log(`${keys.length} keys, ${used.size} files, ${(total / 1048576).toFixed(2)} MB`);
run('python3', [join(here, 'report.py'), ffmpeg]);
