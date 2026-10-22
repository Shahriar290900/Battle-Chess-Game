// Graphics-combination + physics stress check. Usage: node sandbox/fx/stress.mjs
// Verifies every bloom/SMAA/resolution/physics/particles combination renders a non-black frame, then runs a
// 3-simultaneous-queen-shatter stress test on a crowded board and reports FPS (software GL if headless).
import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const out = resolve(root, 'sandbox/fx/__screens__'); mkdirSync(out, { recursive: true });
const PORT = 5199;
const vite = spawn('npx', ['vite', '--port', String(PORT), '--strictPort', '--host', '127.0.0.1'], { cwd: root, stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let browser; const errors = [];
try {
  for (let i = 0; i < 60; i++) { try { if ((await fetch(`http://127.0.0.1:${PORT}/sandbox/fx.html`)).ok) break; } catch {} await sleep(500); }
  browser = await chromium.launch({ executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser', headless: true, timeout: 180000, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(`[${m.type()}] ${m.text().slice(0, 200)}`); });
  page.on('pageerror', (e) => errors.push('[pageerror] ' + e.message));
  await page.goto(`http://127.0.0.1:${PORT}/sandbox/fx.html`);
  const ready = () => page.waitForFunction(() => window.__fx?.ready, null, { timeout: 90000 });
  await ready();
  const ev = async (fn, arg) => { for (let i = 0; i < 4; i++) { try { return await page.evaluate(fn, arg); } catch (e) { if (i === 3) throw e; await sleep(1500); await ready(); } } };
  await ev(() => window.__fx.pause(true));
  let bad = 0, n = 0;
  for (const bloom of [true, false]) for (const antialias of [true, false]) for (const res of [1, 0.5]) for (const physics of ['simple', 'full']) for (const particles of ['low', 'high']) {
    await ev((g) => window.__fx.setGfx(g), { bloom, antialias, resolutionScale: res, physics, particles });
    const r = await ev(() => window.__fx.probe());
    n++; if (r.lum < 1 || r.err !== 0) { bad++; console.log('BLACK/ERR', { bloom, antialias, res, physics, particles }, r); }
  }
  for (const t of ['low', 'medium', 'high']) {
    await ev((tt) => window.__fx.setTier(tt), t);
    const r = await ev(() => window.__fx.probe());
    n++; if (r.lum < 1 || r.err !== 0) { bad++; console.log('BLACK/ERR tier', t, r); }
  }
  console.log(`graphics combos checked=${n} black/error=${bad}`);
  // stress
  for (const [physics, tier] of [['full', 'high'], ['simple', 'low']]) {
    await ev(() => window.__fx.pause(false));
    await ev((t) => window.__fx.setTier(t), tier);
    await ev((p) => window.__fx.setGfx({ physics: p }), physics);
    await ev(() => window.__fx.run('respawn')); await sleep(800);
    await ev(() => window.__fx.reset());
    await ev(() => window.__fx.run('stress x3 queens'));
    await sleep(6000); // real-time run for the FPS reading
    const st0 = await ev(() => window.__fx.stats);
    console.log(`stress physics=${physics} tier=${tier}: avgFPS=${(st0.frames / st0.time).toFixed(1)}`);
    await ev(() => { document.getElementById('ui').style.display = 'none'; });
    await ev(() => window.__fx.run('respawn')); await sleep(800);
    await ev(() => { window.__fx.pause(true); window.__fx.run('stress x3 queens'); });
    await sleep(2500); // fragment loads complete while paused
    for (const t of [0.35, 0.9]) { await ev((dt) => window.__fx.advance(dt), t); await page.screenshot({ timeout: 180000, path: resolve(out, `stress_${physics}_${tier}_${t}.png`) }); }
    await ev(() => { window.__fx.advance(4); window.__fx.pause(false); document.getElementById('ui').style.display = ''; });
  }
} catch (e) { console.error('STRESS FAILED', e); errors.push(String(e)); }
finally { await browser?.close(); vite.kill(); }
console.log(errors.length ? 'console issues:\n' + [...new Set(errors)].slice(0, 12).join('\n') : 'no console errors');
process.exit(0);
