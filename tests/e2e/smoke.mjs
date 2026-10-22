// End-to-end smoke test. Starts the Vite dev server, drives Brave (headless) once, and:
//   - screenshots the menu and an in-game board at 1280x720, 390x844 and 844x390
//   - plays a hot-seat game by clicking squares (including captures)
//   - starts a vs-AI game and checks the AI replies
//   - fails on any console error / page error
// Run: node tests/e2e/smoke.mjs
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const shots = join(here, '__screens__');
mkdirSync(shots, { recursive: true });
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const VIEWPORTS = [
  { name: '1280x720', width: 1280, height: 720 },
  { name: '390x844', width: 390, height: 844 },
  { name: '844x390', width: 844, height: 390 },
];

const log = (...a) => console.log(`[smoke ${((Date.now() - t0) / 1000).toFixed(1)}s]`, ...a);
const t0 = Date.now();
const errors = [];

const server = await createServer({ root, // No HMR/watch: other editors touching src/ must not reload the page mid-test.
  server: { port: 5199, strictPort: false, host: '127.0.0.1', hmr: false, watch: null }, logLevel: 'warn' });
await server.listen();
const url = `http://127.0.0.1:${server.config.server.port}/?debug&quality=low`; // software GL: skip the 2 s benchmark
log('dev server', url);

let browser;
try {
  // Cold start can take ~60 s; other tools on a shared machine may SIGTERM stray Brave processes, so retry.
  for (let attempt = 1; !browser; attempt++) {
    try {
      browser = await chromium.launch({ executablePath: BRAVE, headless: true, timeout: 180000 });
    } catch (e) {
      if (attempt >= 3) throw e;
      log(`browser launch failed (attempt ${attempt}): ${e.message.split('\n')[0]}; retrying`);
    }
  }
  const ctx = await browser.newContext({ viewport: { width: VIEWPORTS[0].width, height: VIEWPORTS[0].height }, hasTouch: false });
  const page = await ctx.newPage();
  page.on('console', (m) => {
    if (m.type() === 'error') {
      const text = m.text();
      if (/favicon/.test(text)) return;
      errors.push(`console.error: ${text}`);
    }
  });
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));

  await page.goto(url, { waitUntil: 'load', timeout: 120000 });
  log('page loaded; waiting for the tap gate');
  await page.waitForSelector('.gate-btn:not([hidden])', { timeout: 180000 });
  await page.screenshot({ path: join(shots, 'loading-gate-1280x720.png') });
  await page.click('.gate-btn');
  await page.waitForSelector('.menu-overlay:not([hidden])', { timeout: 30000 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: join(shots, 'menu-1280x720.png') });
  log('menu shown; quality tier =', await page.evaluate(() => window.__bc.quality.tier));

  // ---------------------------------------------------------------- helpers
  const state = () => page.evaluate(() => { const s = window.__bc.controller.snapshot(); return { state: s.state, plies: s.moves.length, turn: s.turn, fen: s.fen }; });
  const waitFor = async (pred, what, timeout = 90000) => {
    const start = Date.now();
    for (;;) {
      const s = await state();
      if (pred(s)) return s;
      if (Date.now() - start > timeout) throw new Error(`timeout waiting for ${what}; state=${JSON.stringify(s)}`);
      await page.waitForTimeout(150);
    }
  };
  // Pieces occlude each other (tall king in front of a pawn), so click a screen point that really resolves
  // to the wanted square: the piece standing there, or the bare tile when the square is empty.
  const click = async (sq) => {
    const p = await page.evaluate((q) => {
      const b = window.__bc;
      const base = b.squareToScreen(q);
      for (const dy of [0, -14, -28, -42, -56, -70, 14, 28, -84, 42])
        for (const dx of [0, -10, 10, -22, 22]) {
          const r = b.pick(base.x + dx, base.y + dy);
          if ((r.actor ? r.actor.endsWith('@' + q) : r.square === q)) return { x: base.x + dx, y: base.y + dy };
        }
      return { ...base, miss: true };
    }, sq);
    if (p.miss) log(`warning: no unoccluded point found for ${sq}`);
    await page.mouse.click(p.x, p.y);
  };
  // The follow camera swings for ~1.4 s after each turn; wait until the board stops moving on screen.
  const waitCameraStable = async () => {
    let prev = null;
    for (let i = 0; i < 40; i++) {
      const p = await page.evaluate(() => window.__bc.squareToScreen('e4'));
      if (prev && Math.hypot(p.x - prev.x, p.y - prev.y) < 5) return; // idle drift moves ~3 px per sample
      prev = p;
      await page.waitForTimeout(250);
    }
  };
  const play = async (from, to) => {
    const before = (await state()).plies;
    await waitCameraStable();
    await click(from);
    await page.waitForTimeout(250);
    await waitCameraStable();
    await click(to);
    await waitFor((s) => s.plies === before + 1, `${from}-${to} to be accepted`, 8000);
    log(`played ${from}${to}`);
  };
  const settle = (n) => waitFor((s) => s.state === 'awaitInput' && s.plies === n, `awaitInput at ply ${n}`);

  // ---------------------------------------------------------------- hot-seat
  await page.click('text=Two Players');
  await waitFor((s) => s.state === 'awaitInput', 'hot-seat to start');
  await page.waitForTimeout(2200); // camera + settle
  await page.screenshot({ path: join(shots, 'game-1280x720.png') });

  await play('e2', 'e4'); await settle(1);
  await page.waitForTimeout(1600); // Follow-turn camera swing to Black
  await page.screenshot({ path: join(shots, 'game-black-seat-1280x720.png') });
  await play('d7', 'd5'); await settle(2);
  await page.waitForTimeout(1600);
  await play('e4', 'd5'); // capture
  await page.waitForTimeout(1200);
  await page.screenshot({ path: join(shots, 'capture-1280x720.png') });
  await settle(3);
  await play('d8', 'd5'); await settle(4); // queen recaptures
  log('hot-seat capture sequence done; fen =', (await state()).fen);

  // ---------------------------------------------------------------- viewports (menu + in-game)
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.waitForTimeout(1800);
    await page.screenshot({ path: join(shots, `game-${vp.name}.png`) });
    await page.click('.btn-menu');
    await page.waitForSelector('.menu-overlay:not([hidden])');
    await page.waitForTimeout(300);
    await page.screenshot({ path: join(shots, `menu-${vp.name}.png`) });
    await page.click('text=Resume');
    await page.waitForTimeout(300);
  }
  // Settings panel on the smallest viewport (checks scrolling card fits)
  await page.click('.btn-settings');
  await page.waitForSelector('.settings-card');
  await page.screenshot({ path: join(shots, 'settings-844x390.png') });
  await page.click('text=Done');

  // ---------------------------------------------------------------- vs AI
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.click('.btn-menu');
  await page.click('text=Play vs Computer');
  await page.click('.seg:has-text("Easy")');
  await page.waitForTimeout(200);
  await page.screenshot({ path: join(shots, 'menu-vs-ai-1280x720.png') });
  await page.click('text=Begin');
  await waitFor((s) => s.state === 'awaitInput' && s.plies === 0, 'vs-AI game to start');
  await page.waitForTimeout(2000);
  await play('e2', 'e4');
  const after = await waitFor((s) => s.state === 'awaitInput' && s.plies === 2, 'the AI to reply', 90000);
  log('AI replied; fen =', after.fen);
  await page.waitForTimeout(1600);
  await page.screenshot({ path: join(shots, 'vs-ai-1280x720.png') });

  // ---------------------------------------------------------------- one medium-quality look (menu + in-game)
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(url.replace('quality=low', 'quality=medium'), { waitUntil: 'load', timeout: 120000 });
  await page.waitForSelector('.gate-btn:not([hidden])', { timeout: 180000 });
  await page.click('.gate-btn');
  await page.waitForSelector('.menu-overlay:not([hidden])', { timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: join(shots, 'medium-menu-1280x720.png') });
  await page.click('text=Two Players');
  await waitFor((s) => s.state === 'awaitInput', 'medium game to start');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: join(shots, 'medium-game-1280x720.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(1800);
  await page.screenshot({ path: join(shots, 'medium-game-390x844.png') });
  log('medium tier =', await page.evaluate(() => window.__bc.quality.tier));

  if (errors.length) throw new Error(`console errors:\n  ${[...new Set(errors)].join('\n  ')}`);
  log('PASS: no console errors; screenshots in', shots);
} catch (e) {
  console.error('[smoke] FAILED:', e.message);
  if (errors.length) console.error('[smoke] console errors so far:\n  ' + [...new Set(errors)].join('\n  '));
  process.exitCode = 1;
} finally {
  await browser?.close();
  await server.close();
}
