// Copies the user's theme MP3 to public/audio/theme.mp3 (gitignored). Missing source = warn, exit 0.
import { copyFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const defaultSrc = resolve(root, '..', 'Game of Thrones - Main Theme (Extended) HD.mp3');
const src = resolve(process.argv[2] ?? process.env.MUSIC_SRC ?? defaultSrc);
const dest = resolve(root, 'public/audio/theme.mp3');

if (!existsSync(src)) {
  console.warn(`[prepare-music] source not found: ${src}\n  Continuing without music (players can load their own track).`);
  process.exit(0);
}
mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log(`[prepare-music] ${src} -> public/audio/theme.mp3 (${(statSync(dest).size / 1048576).toFixed(1)} MB)`);
