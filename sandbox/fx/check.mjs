// Playwright check: loads the FX sandbox, triggers every effect, screenshots to __screens__/, reports console errors + avg FPS.
// Usage: node sandbox/fx/check.mjs [tier] [comma,separated,effect names]   (starts its own vite on :5199)
import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const out = resolve(root, 'sandbox/fx/__screens__');
const tier = process.argv[2] || 'high';
rmSync(out, { recursive: true, force: true }); mkdirSync(out, { recursive: true });

const PORT = 5199;
const vite = spawn('npx', ['vite', '--port', String(PORT), '--strictPort', '--host', '127.0.0.1'], { cwd: root, stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitServer() { for (let i = 0; i < 60; i++) { try { const r = await fetch(`http://127.0.0.1:${PORT}/sandbox/fx.html`); if (r.ok) return; } catch {} await sleep(500); } throw new Error('vite did not start'); }

const errors = [];
let browser;
try {
  await waitServer();
  browser = await chromium.launch({ executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser', headless: true, timeout: 180000, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(`[${m.type()}] ${m.text()}`); });
  page.on('pageerror', (e) => errors.push('[pageerror] ' + e.message));
  await page.goto(`http://127.0.0.1:${PORT}/sandbox/fx.html`);
  const ready = () => page.waitForFunction(() => window.__fx?.ready, null, { timeout: 90000 });
  await ready();
  // Vite may full-reload the page (dep re-optimisation / other agents editing files): retry after re-ready.
  const ev = async (fn, arg) => { for (let i = 0; i < 5; i++) { try { return await page.evaluate(fn, arg); } catch (e) { if (i === 4) throw e; await sleep(1500); await ready(); } } };
  await ev((t) => window.__fx.setTier(t), tier);
  const only = process.argv[3] ? process.argv[3].split(',') : null;
  const names = (await ev(() => window.__fx.names.filter((n) => n !== 'respawn'))).filter((n) => !only || only.includes(n));
  const shots = {
    'shatter pawn': [0.6, 1.4], 'shatter queen (cut)': [0.6, 1.4], 'sweep ember (pawn)': [0.5, 1.1], 'sweep frost (queen)': [0.5, 1.0],
    'dissolve pawn': [0.5], 'dissolve queen': [0.5], 'column E': [0.4, 1.2], 'column R': [0.4, 1.2], 'mist': [2.0], 'iceSpikes': [0.6],
  };
  let n = 0;
  for (const name of names) {
    await ev(() => window.__fx.run('respawn'));
    await sleep(500);
    await ev(() => window.__fx.reset());
    await ev(() => window.__fx.pause(false));
    await ev((nm) => { window.__fx.pause(true); window.__fx.run(nm); }, name); // atomic: no frames between trigger and pause
    await sleep(1200); // async asset loads (fragments) complete while sim is paused
    const times = shots[name] || [0.35];
    let prev = 0;
    for (const t of times) {
      await ev((dt) => window.__fx.advance(dt), t - prev); prev = t;
      const file = `${String(++n).padStart(2, '0')}_${name.replace(/[^a-z0-9]+/gi, '_')}_${t}.png`;
      await page.screenshot({ timeout: 180000, path: resolve(out, file) });
    }
    await ev(() => { window.__fx.advance(5); window.__fx.pause(false); }); // fast-forward to the end of the effect
  }
  const stats = await ev(() => window.__fx.stats);
  console.log(`tier=${tier} effects=${names.length} avgFPS=${(stats.frames / stats.time).toFixed(1)} (all-run, software GL if headless)`);
  // dedicated FPS probe: 3 s idle + 3 s with a burst of effects
  await ev(() => { window.__fx.reset(); });
  await ev(() => { for (const nm of ['embers', 'sparks', 'smoke', 'frostMist', 'iceGlitter', 'shockwave E', 'iceSpikes', 'column R']) window.__fx.run(nm); });
  await sleep(2000);
  const s2 = await ev(() => window.__fx.stats);
  console.log(`burst avgFPS=${(s2.frames / s2.time).toFixed(1)}`);
} catch (e) { console.error('CHECK FAILED', e); errors.push(String(e)); }
finally { await browser?.close(); vite.kill(); }
console.log(errors.length ? `console issues (${errors.length}):\n` + [...new Set(errors)].slice(0, 20).join('\n') : 'no console errors');
console.log('screenshots:', out);
process.exit(errors.some((e) => e.startsWith('[error]') || e.startsWith('[pageerror]') || e.includes('FAILED')) ? 1 : 0);
