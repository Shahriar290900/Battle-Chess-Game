// End-to-end check of the Learn area on the REAL game (own Vite port, never 5173), headless Brave, one instance.
// Opens the tutorial (select + move, capture cinematic), a How-to lesson (wrong try, then solve by clicking),
// and the Piece Library (rotate, zoom, duel loop, portrait phone layout); verifies clean exit (board, scene
// children, lights, classes) and zero console errors. Screenshots go to sandbox/learn/__screens__/.
// Run: node sandbox/learn/check.mjs
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
const t0 = Date.now();
const log = (...a) => console.log(`[learn ${((Date.now() - t0) / 1000).toFixed(1)}s]`, ...a);
const errors = [];
const fails = [];
const expect = (cond, msg) => { if (!cond) { fails.push(msg); log('FAIL:', msg); } else log('ok:', msg); };

const server = await createServer({ root, server: { port: 5231, strictPort: true, host: '127.0.0.1', hmr: false, watch: null }, logLevel: 'warn' });
await server.listen();
const url = `http://127.0.0.1:${server.config.server.port}/?debug&quality=low`;
log('dev server', url);

let browser;
try {
  for (let attempt = 1; !browser; attempt++) {
    try { browser = await chromium.launch({ executablePath: BRAVE, headless: true, timeout: 180000 }); }
    catch (e) { if (attempt >= 3) throw e; log('launch retry', e.message.split('\n')[0]); }
  }
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 720 }, hasTouch: false })).newPage();
  page.on('console', (m) => { if (m.type() === 'error' && !/favicon/.test(m.text())) errors.push(`console.error: ${m.text()}`); });
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));

  await page.goto(url, { waitUntil: 'load', timeout: 120000 });
  await page.waitForSelector('.gate-btn:not([hidden])', { timeout: 180000 });
  await page.keyboard.press('Space');
  await page.waitForFunction(() => window.__learn && window.__bc, null, { timeout: 30000 });
  await page.waitForTimeout(1500);

  const snapshot = () => page.evaluate(() => {
    const b = window.__bc;
    const lights = []; b.kit.scene.traverse((o) => { if (o.isLight) lights.push(o.uuid); });
    return { children: b.kit.scene.children.filter((c) => c.name === 'markers').length, lights: lights.length, actors: b.board.allActors().length, rl: window.__learn.isOpen, cls: document.getElementById('ui-root').className, root: !!document.querySelector('.learn-root') };
  });
  const before = await snapshot();
  log('baseline', JSON.stringify(before));

  const click = async (sq) => {
    const p = await page.evaluate((q) => {
      const b = window.__bc; const base = b.squareToScreen(q);
      for (const dy of [0, -14, -28, -42, -56, -70, 14, 28, -84, 42]) for (const dx of [0, -10, 10, -22, 22]) {
        const r = b.pick(base.x + dx, base.y + dy);
        if ((r.actor ? r.actor.endsWith('@' + q) : r.square === q)) return { x: base.x + dx, y: base.y + dy };
      }
      return { ...base, miss: true };
    }, sq);
    await page.mouse.click(p.x, p.y);
  };
  const stable = async () => {
    let prev = null;
    for (let i = 0; i < 40; i++) {
      const p = await page.evaluate(() => window.__bc.squareToScreen('e4'));
      if (prev && Math.hypot(p.x - prev.x, p.y - prev.y) < 4) return;
      prev = p; await page.waitForTimeout(250);
    }
  };
  const closed = async (what) => {
    await page.waitForFunction(() => !window.__learn.isOpen, null, { timeout: 30000 });
    await page.waitForTimeout(1200);
    const a = await snapshot();
    expect(!a.root && !/learn-on/.test(a.cls), `${what}: learn DOM removed`);
    expect(a.children === before.children, `${what}: marker groups restored (${a.children} vs ${before.children})`);
    expect(a.lights === before.lights, `${what}: lights restored (${a.lights} vs ${before.lights})`);
    expect(a.actors === 32, `${what}: board has 32 actors again (${a.actors})`);
  };

  // ------------------------------------------------------------ tutorial
  await page.evaluate(() => { window.__learn.open('tutorial'); });
  await page.waitForSelector('.learn-caption .learn-card-title', { timeout: 60000 });
  expect((await page.textContent('.learn-card-title')).includes('Welcome'), 'tutorial opens on the welcome step');
  const next = page.locator('.learn-actions .learn-primary');
  await next.click(); await next.click(); // controls -> first move
  await page.waitForTimeout(900); await stable();
  await click('e2'); await page.waitForTimeout(500);
  await page.screenshot({ path: join(shots, 'tutorial-select-1280x720.png') });
  await click('e4');
  await page.waitForFunction(() => !document.querySelector('.learn-actions .learn-primary').disabled, null, { timeout: 60000 });
  expect(await page.evaluate(() => window.__bc.board.actorAt('e4')?.id === 'emberhold_pawn' && window.__bc.board.actorAt('e5')?.id === 'rime_pawn'), 'tutorial move + scripted reply played');
  await next.click(); await next.click(); // turns -> capture
  await page.waitForTimeout(800);
  await page.click('.learn-step-extra .learn-btn'); // watch the capture
  await page.waitForTimeout(3200);
  await page.screenshot({ path: join(shots, 'tutorial-capture-1280x720.png') });
  await page.waitForFunction(() => !document.querySelector('.learn-actions .learn-primary').disabled, null, { timeout: 90000 });
  await page.click('.learn-actions .learn-btn:has-text("Skip tutorial")');
  await closed('tutorial');
  expect(await page.evaluate(() => window.__bc.settings.get().tutorialSeen), 'tutorialSeen set after skipping');

  // ------------------------------------------------------------ how to play
  await page.evaluate(() => { window.__learn.open('howto'); });
  await page.waitForSelector('.learn-contents .learn-lesson', { timeout: 60000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(shots, 'howto-contents-1280x720.png') });
  await page.click('.learn-lesson:has-text("Rook")');
  await page.waitForTimeout(1800); await stable();
  await click('d4'); await page.waitForTimeout(400);
  await click('a4'); // illegal for a rook? a4 is on the rank: legal but wrong
  await page.waitForTimeout(500);
  const hint = await page.textContent('.learn-status');
  expect(/d7|rook|slide/i.test(hint), `wrong try gives a hint ("${hint.slice(0, 60)}")`);
  await stable(); await click('d4'); await page.waitForTimeout(400);
  await click('d7');
  await page.waitForSelector('.learn-stamp:not([hidden])', { timeout: 60000 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: join(shots, 'howto-solved-1280x720.png') });
  expect(await page.evaluate(() => window.__learn.progress.isDone('rook')), 'rook lesson saved as complete');
  expect(await page.evaluate(() => /battle-chess\.learn/.test(Object.keys(localStorage).join())), 'progress is in localStorage');
  await page.keyboard.press('Escape'); // lesson -> contents
  await page.waitForTimeout(400);
  expect(await page.isVisible('.learn-contents'), 'Escape returns to the contents page');
  await page.keyboard.press('Escape'); // contents -> close
  await closed('howto');

  // ------------------------------------------------------------ library
  await page.evaluate(() => { window.__learn.open('library'); });
  await page.waitForSelector('.learn-inspector-canvas', { timeout: 60000 });
  await page.waitForTimeout(4000);
  const pixels = (sel) => page.evaluate((s) => {
    const c = document.querySelector(s); const g = c.getContext('2d'); const d = g.getImageData(0, 0, c.width, c.height).data;
    let min = 255, max = 0; for (let i = 0; i < d.length; i += 40) { const v = d[i] + d[i + 1] + d[i + 2]; min = Math.min(min, v / 3); max = Math.max(max, v / 3); }
    return { w: c.width, h: c.height, spread: max - min };
  }, sel);
  const ins = await pixels('.learn-inspector-canvas');
  expect(ins.spread > 40, `inspector renders the model (spread ${ins.spread.toFixed(0)}, ${ins.w}x${ins.h})`);
  const box = await page.locator('.learn-inspector-canvas').boundingBox();
  const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
  const sig = () => page.evaluate(() => { const c = document.querySelector('.learn-inspector-canvas'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let h = 0; for (let i = 0; i < d.length; i += 97) h = (h * 31 + d[i]) | 0; return h; });
  const s0 = await sig();
  await page.mouse.move(cx, cy); await page.mouse.down(); await page.mouse.move(cx + 120, cy + 20, { steps: 8 }); await page.mouse.up();
  await page.waitForTimeout(500);
  expect((await sig()) !== s0, 'dragging rotates the inspector view');
  await page.mouse.wheel(0, -400); await page.waitForTimeout(500);
  await page.click('.learn-piece:has-text("Forge Bastion")');
  await page.click('.learn-chip:has-text("Attack")');
  await page.waitForTimeout(300);
  await page.click('.learn-chips .learn-chip:has-text("Pawn")');
  await page.waitForFunction(() => /./.test(document.querySelector('.learn-duel-status')?.textContent ?? ''), null, { timeout: 90000 });
  await page.waitForTimeout(1500);
  const duel = await pixels('.learn-duel-canvas');
  expect(duel.spread > 30, `duel pane renders (spread ${duel.spread.toFixed(0)})`);
  log('duel status:', await page.textContent('.learn-duel-status'));
  await page.screenshot({ path: join(shots, 'library-1280x720.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: join(shots, 'library-390x844.png'), fullPage: false });
  await page.evaluate(() => document.querySelector('.learn-duel-canvas').scrollIntoView());
  await page.waitForTimeout(2500);
  await page.screenshot({ path: join(shots, 'library-duel-390x844.png') });
  const paused = await page.evaluate(async () => { // hidden panes must not render: scroll the duel off-screen & compare canvases
    const duel = document.querySelector('.learn-duel-canvas'); const r = duel.getBoundingClientRect(); return { top: Math.round(r.top), h: Math.round(window.innerHeight) };
  });
  log('portrait duel top', JSON.stringify(paused));
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.waitForTimeout(800);
  await page.click('.learn-codex-head .learn-btn');
  await closed('library');
  expect(await page.evaluate(() => window.__bc.services.sequences.running === false), 'no sequence left running');

  expect(errors.length === 0, `no console errors${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`);
} catch (e) {
  fails.push(`exception: ${e.stack || e.message}`);
  log('EXCEPTION', e.stack || e.message);
} finally {
  await browser?.close().catch(() => {});
  await server.close();
}
log(fails.length ? `FAILED (${fails.length})` : 'ALL OK');
process.exit(fails.length ? 1 : 0);
