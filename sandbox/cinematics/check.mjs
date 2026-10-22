// Starts a Vite dev server, opens the sandbox in Brave (system browser, WebGL2), triggers every attacker role
// for both factions and screenshots setup / impact / resolve into sandbox/cinematics/__screens__/.
// Usage: node sandbox/cinematics/check.mjs [--only=queen] [--portrait]
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';
import { createServer } from 'vite';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const out = path.join(here, '__screens__');
mkdirSync(out, { recursive: true });
const args = process.argv.slice(2);
const only = args.find((a) => a.startsWith('--only='))?.slice(7);
const portrait = args.includes('--portrait');
const crowded = args.includes('--crowded');
const ROLES = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'].filter((r) => !only || r === only);
const FACTIONS = ['emberhold', 'rime'];
const CASES = crowded
  ? ['opening-w', 'opening-b', 'backrank-w', 'backrank-b'].map((n) => ({ name: 'crowded_' + n, scenario: n }))
  : ROLES.flatMap((role) => FACTIONS.map((faction) => ({ name: `${faction}_${role}`, role, faction })));

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const server = await createServer({ root, server: { host: '127.0.0.1', port: 5199, strictPort: false, hmr: false, watch: null }, logLevel: 'warn' });
await server.listen();
const url = `http://127.0.0.1:${server.config.server.port}/sandbox/cinematics.html`;
const consoleErrors = [];
let browser;
try {
  log('launching Brave');
  browser = await chromium.launch({
    executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser', headless: true, timeout: 180000,
    args: ['--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--disable-background-timer-throttling'],
  });
  const page = await browser.newPage({ viewport: portrait ? { width: 390, height: 844 } : { width: 1280, height: 720 } });
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + e.message));
  log('launched; opening', url);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  log('page loaded');
  await page.waitForFunction(() => window.__sandbox?.ready === true, null, { timeout: 120000, polling: 100 });
  log('sandbox ready');
  await page.evaluate(() => window.__sandbox.hideUi(true));
  const tag = portrait ? '_portrait' : '';

  for (const c of CASES) {
    const name = c.name + tag;
    // arm freezes: setup (0.5 s after begin), impact (at the event), resolve (1.4 s after the shatter)
    const results = await page.evaluate(([r, f, sc]) => {
      const s = window.__sandbox;
      s.clearFreezers();
      window.__shots = {};
      window.__done = false;
      const arm = (key, ev, ms) => s.armFreeze(ev, ms).then(() => { window.__shots[key] = true; });
      arm('setup', 'capture:begin', 550);
      arm('impact', 'capture:impact', 0);
      arm('resolve', 'capture:shatter', 1500);
      (sc ? s.playScenario(sc, 'full') : s.playCapture(r, f, 'full')).then(() => { window.__done = true; }, (e) => { s.errors.push('capture failed: ' + e + e?.stack); });
      return true;
    }, [c.role, c.faction, c.scenario]);
    void results;
    for (const key of ['setup', 'impact', 'resolve']) {
      log('waiting', name, key);
      try {
        await page.waitForFunction((k) => window.__shots[k] === true, key, { timeout: 25000, polling: 100 });
      } catch (e) {
        const diag = await page.evaluate(() => ({
          errors: window.__sandbox.errors, frozen: window.__sandbox.frozen, shots: window.__shots,
          events: window.__sandbox.eventLog.slice(-8).map((x) => x.name), done: window.__done,
        })).catch((err) => String(err));
        console.error(`stalled at ${name} ${key}`, JSON.stringify(diag));
        throw e;
      }
      await page.waitForTimeout(120); // let the frozen frame render
      await page.screenshot({ path: path.join(out, `${name}_${key}.png`), timeout: 30000 });
      log('shot', key);
      await page.evaluate(() => window.__sandbox.resume());
      // the next freezer needs the timeline running again; re-arm happens by events
    }
    await page.waitForFunction(() => window.__done === true, null, { timeout: 60000, polling: 100 });
    const state = await page.evaluate(() => ({ ts: 1, errors: window.__sandbox.errors.slice() }));
    console.log(`ok ${name}`, state.errors.length ? state.errors : '');
    consoleErrors.push(...state.errors);
  }
} finally {
  await browser?.close();
  await server.close();
}
if (consoleErrors.length) {
  console.error('console errors:\n' + [...new Set(consoleErrors)].join('\n'));
  process.exit(1);
}
console.log('sandbox check passed, screenshots in', out);
