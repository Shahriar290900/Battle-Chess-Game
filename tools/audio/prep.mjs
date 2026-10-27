// Decodes every raw source (ogg/wav/mp3/flac) to 44.1 kHz mono float WAV in tools/audio/work/src/<pack>/<name>.wav
// using the pinned ffmpeg-static binary. Skips files already decoded.
import { execFileSync } from 'node:child_process';
import { mkdirSync, readdirSync, statSync, existsSync } from 'node:fs';
import { dirname, join, extname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const here = dirname(fileURLToPath(import.meta.url));
const ffmpeg = createRequire(import.meta.url)('ffmpeg-static');
const RAW = join(here, 'raw');
const OUT = join(here, 'work', 'src');
const EXT = new Set(['.ogg', '.wav', '.mp3', '.flac']);

function walk(d) {
  return readdirSync(d).flatMap((n) => {
    const p = join(d, n);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}
let n = 0;
for (const pack of readdirSync(RAW)) {
  const pd = join(RAW, pack);
  if (!statSync(pd).isDirectory()) continue;
  for (const f of walk(pd)) {
    if (!EXT.has(extname(f).toLowerCase()) || basename(f).startsWith('.')) continue;
    const name = basename(f, extname(f)).replace(/[^A-Za-z0-9_-]+/g, '_');
    mkdirSync(join(OUT, pack), { recursive: true });
    const dst = join(OUT, pack, `${name}.wav`);
    if (existsSync(dst)) continue;
    try {
      execFileSync(ffmpeg, ['-v', 'error', '-y', '-i', f, '-ac', '1', '-ar', '44100', '-c:a', 'pcm_f32le', dst]);
      n++;
    } catch { console.warn('could not decode', f); }
  }
}
console.log(`prep: decoded ${n} new files`);
