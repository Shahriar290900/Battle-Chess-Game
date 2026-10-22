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
const modes = ['--check', '--mate', '--attract'].filter((a) => args.includes(a));
const modeArg = modes[0];
const ROLES = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'].filter((r) => !only || r === only);
const FACTIONS = ['emberhold', 'rime'];
const CASES = crowded
  ? ['opening-w', 'opening-b', 'backrank-w', 'backrank-b'].map((n) => ({ name: 'crowded_' + n, scenario: n }))
  : ROLES.flatMap((role) => FACTIONS.map((faction) => ({ name: `${faction}_${role}`, role, faction })));

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const server = await createServer({ root, server: { host: '127.0.0.1', port: 5199, strictPort: false, hmr: false, watch: null }, optimizeDeps: { entries: ['sandbox/cinematics.html'], include: ['chess.js', 'gsap', 'three', 'three/examples/jsm/loaders/GLTFLoader.js', 'three/examples/jsm/utils/SkeletonUtils.js'] }, logLevel: 'warn' });
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
  page.on('console', (m) => { if (m.type() === 'error') { consoleErrors.push(m.text()); log('console.error', m.text().slice(0, 300)); } });
  page.on('pageerror', (e) => { consoleErrors.push('pageerror: ' + e.message); log('pageerror', e.message.slice(0, 300)); });
  log('launched; opening', url);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  log('page loaded');
  try {
    await page.waitForFunction(() => window.__sandbox?.ready === true, null, { timeout: 60000, polling: 100 });
  } catch (e) {
    const d = await page.evaluate(() => ({ status: document.getElementById('status')?.textContent, errors: window.__sandbox?.errors })).catch((x) => String(x));
    console.error('sandbox never became ready', JSON.stringify(d));
    throw e;
  }
  log('sandbox ready');
  await page.evaluate(() => window.__sandbox.hideUi(true));
  const tag = portrait ? '_portrait' : '';

  const snap = async (file, pre = 150) => {
    await page.waitForTimeout(pre);
    await page.screenshot({ path: path.join(out, file + '.png'), timeout: 30000 });
    log('shot', file);
  };
  /** Freeze the GSAP world `ms` after "now", screenshot it, resume. */
  const frozenShot = async (file, ms) => {
    await page.evaluate((m) => window.__sandbox.freezeAfter(m), ms);
    await snap(file);
    await page.evaluate(() => window.__sandbox.resume());
  };

  for (const mode of modes) {
  if (mode === '--check') {
    for (const role of ROLES) {
      await page.evaluate(([r]) => { window.__done = false; window.__sandbox.playCheck(r, 'emberhold', 'full').then(() => { window.__done = true; }); }, [role]);
      await frozenShot(`check_${role}${tag}`, 900);
      await page.waitForFunction(() => window.__done === true, null, { timeout: 60000, polling: 100 });
      log('ok check', role, await page.evaluate(() => window.__sandbox.eventLog.filter((e) => e.name === 'taunt').length));
    }
  } else if (mode === '--mate') {
    await page.evaluate(() => { window.__done = false; window.__sandbox.playMate().then(() => { window.__done = true; }); });
    for (const [i, ms] of [1300, 1500, 1800].entries()) await frozenShot(`mate_${i + 1}${tag}`, ms);
    await page.waitForFunction(() => window.__done === true, null, { timeout: 60000, polling: 100 });
    const info = await page.evaluate(() => ({ n: window.__sandbox.board.allActors().length, drops: window.__sandbox.eventLog.filter((e) => e.name === 'weapon:drop').length, sur: window.__sandbox.eventLog.filter((e) => e.name === 'surrender').length }));
    log('ok mate', JSON.stringify(info));
    await snap(`mate_end${tag}`);
    if (info.n !== 32 || info.sur !== 1) consoleErrors.push('mate: expected 32 pieces and 1 surrender, got ' + JSON.stringify(info));
  } else if (mode === '--attract') {
    await page.evaluate(() => window.__sandbox.startAttract());
    let elapsed = 0;
    for (const [i, at] of [3000, 9000, 14500, 24000, 42000].entries()) {
      await frozenShot(`attract_${i + 1}${tag}`, at - elapsed - 150 * 1);
      elapsed = at;
    }
    await page.evaluate(() => window.__sandbox.resume());
    await page.evaluate(() => window.__sandbox.stopAttract());
    const info = await page.evaluate(() => ({ n: window.__sandbox.board.allActors().length, game: window.__sandbox.eventLog.filter((e) => /^(game|turn):/.test(e.name)).length, caps: window.__sandbox.eventLog.filter((e) => e.name === 'capture:impact').length, errors: window.__sandbox.errors.slice() }));
    log('attract stopped', JSON.stringify(info));
    if (info.n !== 32 || info.game !== 0) consoleErrors.push('attract: bad state ' + JSON.stringify(info));
    consoleErrors.push(...info.errors);
    await snap(`attract_stopped${tag}`, 1200);
  }
  }
  if (!modes.length)
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
