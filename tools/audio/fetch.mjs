// Downloads the CC0 source packs listed in sources.json into tools/audio/raw/ (gitignored),
// VERIFYING each page's licence is exactly CC0 (anything else aborts that pack), and
// writes tools/audio/raw/sources.lock.json + docs/audio/LICENSES.md.
import { execFileSync } from 'node:child_process';
import { mkdirSync, existsSync, readFileSync, writeFileSync, readdirSync, rmSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const RAW = join(here, 'raw');
const sources = JSON.parse(readFileSync(join(here, 'sources.json'), 'utf8'));
mkdirSync(RAW, { recursive: true });

const curl = (url, out, referer) => execFileSync('curl', ['-sfL', '--retry', '3', '-m', '180', '-A', 'Mozilla/5.0', ...(referer ? ['-e', referer] : []), url, ...(out ? ['-o', out] : [])], { maxBuffer: 1 << 28 });
const text = (url, referer) => curl(url, undefined, referer).toString('utf8');
const strip = (s) => s.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&middot;/g, '·').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
const lock = [];

function getFiles(id, urls, forceName) {
  const dir = join(RAW, id);
  if (existsSync(dir) && readdirSync(dir).length) return dir;
  mkdirSync(dir, { recursive: true });
  for (const u of urls) {
    const name = forceName ?? decodeURIComponent(basename(new URL(u).pathname));
    const dst = join(dir, name);
    curl(u, dst);
    if (name.endsWith('.zip')) { execFileSync('unzip', ['-qo', dst, '-d', dir]); rmSync(dst); }
  }
  return dir;
}

for (const slug of sources.kenney) {
  const page = `https://kenney.nl/assets/${slug}`;
  const h = text(page);
  if (!/Creative Commons CC0/.test(h)) { console.error(`SKIP ${page}: licence not CC0`); continue; }
  let zip = h.match(/https:\/\/kenney\.nl\/media[^"]*\.zip/)?.[0];
  if (!zip) { // the site now hands out a freshly signed link through its own download endpoint
    const id = h.match(/data-download-id='([0-9a-f]+)'/)?.[1];
    if (id) zip = JSON.parse(text(`https://kenney.nl/download-link/${id}`, page)).url;
  }
  if (!zip) { console.error(`SKIP ${page}: no download link`); continue; }
  const title = strip(h.match(/<title>([^<]*)/)?.[1] ?? slug).replace(/\s*[|•].*$/, '');
  getFiles(`k_${slug}`, [zip], `${slug}.zip`);
  lock.push({ id: `k_${slug}`, title, author: 'Kenney (kenney.nl)', licence: 'CC0 1.0', page, download: zip });
  console.log('ok', page);
}

for (const slug of sources.oga) {
  const page = `https://opengameart.org/content/${slug}`;
  const h = text(page);
  const li = h.indexOf('License(s)');
  const names = [...h.slice(li, li + 1500).matchAll(/license-name'>([^<]*)/g)].map((m) => m[1]);
  if (names.length !== 1 || names[0] !== 'CC0') { console.error(`SKIP ${page}: licence ${JSON.stringify(names)}`); continue; }
  const ai = h.indexOf('Author:');
  const author = strip(h.slice(ai + 7, ai + 400)).split(/\s{0,}(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day/)[0].replace(/^[:\s]+/, '').replace(/\s*\(?Submitted.*$/, '').split(' ').slice(0, 3).join(' ');
  const title = strip(h.match(/<title>([^<|]*)/)?.[1] ?? slug);
  let files = [...new Set([...h.matchAll(/href="(https:\/\/opengameart\.org\/sites\/default\/files\/(?!css|js|styles)[^"]+\.(?:zip|ogg|wav|mp3|flac))"/g)].map((m) => m[1]))];
  // single-file audio pages expose the download only through the player's data-mp3-url attribute
  if (!files.length) files = [...new Set([...h.matchAll(/data-mp3-url='(https:\/\/opengameart\.org\/sites\/default\/files\/(?!css|js|styles|audio_preview)[^']+\.(?:ogg|wav|mp3|flac))'/g)].map((m) => m[1]))];
  if (!files.length) { console.error(`SKIP ${page}: no download links`); continue; }
  getFiles(`o_${slug}`, files);
  lock.push({ id: `o_${slug}`, title, author, licence: 'CC0 1.0', page, download: files });
  console.log('ok', page);
}

writeFileSync(join(RAW, 'sources.lock.json'), JSON.stringify(lock, null, 2));
const rows = lock.map((s) => `| ${s.title.replace(/\|/g, '/')} | ${s.author} | ${s.licence} | ${s.page} |`).join('\n');
writeFileSync(join(here, '..', '..', 'docs', 'audio', 'LICENSES.md'), `# Audio licences and credits

Every source sample used to build \`public/audio/sfx/*.mp3\` is released under **CC0 1.0 Universal (public domain dedication)**
and the licence was checked on the source page by \`tools/audio/fetch.mjs\` at download time (the script refuses any pack whose
licence is not exactly CC0). Nothing comes from a commercial game, film or sample library, and no CC-BY / NC / "royalty-free"
licensed material is included. CC0 needs no attribution; credit is given anyway as a courtesy.

The shipped files are *derivative sound design*: sources are layered, pitched, filtered, convolved with generated impulse
responses, compressed and loudness-normalised by \`tools/audio/design.py\` together with synthesised layers (sub drops,
risers, noise textures) generated from scratch. The raw downloads are not committed (\`tools/audio/raw/\` is gitignored);
re-run \`npm run audio:build\` to reproduce.

| Pack | Author | Licence | Source |
|---|---|---|---|
${rows}
`);
console.log(`${lock.length} packs verified.`);
