#!/usr/bin/env node
// Turntable / contact-sheet renderer: headless Brave (Playwright) + three.js via a Vite dev server.
//   npm run turntables                         all assets: 8-view sheets + per-role faction pairs
//   npm run turntables -- --ids emberhold_pawn --clip Attack
// Options: --ids a,b   --clip Attack|Idle|...   --lod 0|1   --roles-only   --no-roles   --out dir
import { createServer } from 'vite';
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2);
const opt = (name, def = null) => { const i = args.indexOf(`--${name}`); return i < 0 ? def : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };
const outDir = path.resolve(root, opt('out', 'docs/art/turntables'));
const lod = Number(opt('lod', 0));
const clip = opt('clip');
const rolesOnly = !!opt('roles-only');
const noRoles = !!opt('no-roles');
const timesArg = opt('times');   // --times 0.1,0.3,0.5,0.8,0.95,1.3 : explicit clip sample times (6)
const times = timesArg && timesArg !== true ? String(timesArg).split(',').map(Number) : null;
const single = opt('single');   // --single <yawDeg> [--dist 2.5 --ty 0.55 --pitch 12 --clip Attack --t 0.95]: one big close-up

const all = fs.readdirSync(path.join(root, 'public/models')).filter((f) => f.endsWith('.glb') && !f.includes('_fragments')).map((f) => f.replace('.glb', '')).sort();
const idArg = opt('ids');
const ids = idArg && idArg !== true ? String(idArg).split(',').map((s) => s.trim()).filter(Boolean) : all;
for (const id of ids) if (!all.includes(id)) { console.error(`unknown asset id ${id}`); process.exit(2); }
const roles = [...new Set(ids.map((i) => i.split('_')[1]))];
fs.mkdirSync(outDir, { recursive: true });

const server = await createServer({ root, logLevel: 'error', server: { host: '127.0.0.1', port: 0, strictPort: false }, clearScreen: false });
await server.listen();
const addr = server.httpServer.address();
const url = `http://127.0.0.1:${addr.port}/tools/preview/turntable.html`;
// Brave (user's browser; Playwright's bundled Chromium is unsupported on macOS 12). Launch ONCE: cold start can take ~60 s.
const BRAVE = process.env.BRAVE_PATH || '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const browser = await chromium.launch({ executablePath: BRAVE, headless: true, timeout: 180000, args: ['--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
let failed = 0;
try {
  const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) console.log(`[page ${m.type()}] ${m.text()}`.slice(0, 300)); });
  page.on('pageerror', (e) => console.log(`[pageerror] ${e.message}`));
  await page.goto(url);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  const save = async (name, dataUrl) => {
    const file = path.join(outDir, name);
    fs.writeFileSync(file, Buffer.from(dataUrl.split(',')[1], 'base64'));
    console.log(`wrote ${path.relative(root, file)}`);
  };
  if (single) {
    const o = { yaw: Number(single) || 30, dist: Number(opt('dist', 2.5)), ty: Number(opt('ty', 0.55)), pitch: Number(opt('pitch', 12)), lod, clip: clip || null, t: Number(opt('t', 0)) };
    for (const id of ids) await save(`${id}_single_${Math.round(o.yaw)}.png`, await page.evaluate(([i, oo]) => window.turntable.single(i, oo), [id, o]));
  } else if (!rolesOnly) {
    for (const id of ids) {
      try {
        if (clip) await save(`${id}_${String(clip).toLowerCase()}.png`, await page.evaluate(([i, c, l, T]) => window.turntable.clip(i, c, { lod: l, times: T }), [id, clip, lod, times]));
        else await save(`${id}.png`, await page.evaluate(([i, l]) => window.turntable.sheet(i, { lod: l }), [id, lod]));
      } catch (e) { failed++; console.error(`FAILED ${id}: ${e.message}`); }
    }
  }
  if (!noRoles && !clip && !single) {
    for (const role of roles) {
      try { await save(`role_${role}.png`, await page.evaluate(([r, l]) => window.turntable.role(r, { lod: l }), [role, lod])); }
      catch (e) { failed++; console.error(`FAILED role ${role}: ${e.message}`); }
    }
  }
} finally {
  await browser.close();
  await server.close();
}
process.exit(failed ? 1 : 0);
