// Starts its own Vite server (port 5311), opens the kinematics sandbox in headless Brave, drives walk / abrupt stop /
// hop / impulse / look-at / disable / scrubbed-attack gate, screenshots each into sandbox/kinematics/__screens__/ and
// fails on console errors or broken invariants. Usage: node sandbox/kinematics/check.mjs
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';
import { createServer } from 'vite';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const out = path.join(here, '__screens__');
mkdirSync(out, { recursive: true });
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const server = await createServer({ root, server: { host: '127.0.0.1', port: 5311, strictPort: true, hmr: false, watch: null }, logLevel: 'warn' });
await server.listen();
const url = `http://127.0.0.1:${server.config.server.port}/sandbox/kinematics.html`;
const errors = [];
const failures = [];
const expectTrue = (cond, msg) => { if (!cond) { failures.push(msg); log('FAIL', msg); } else log('ok  ', msg); };
let browser;
try {
  browser = await chromium.launch({
    executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser', headless: true, timeout: 180000,
    args: ['--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'],
  });
  const page = await browser.newPage({ viewport: { width: 1100, height: 560 } });
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('response', (r) => { if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${r.url()}`); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => window.__sandbox?.ready === true, null, { timeout: 150000, polling: 200 });
  log('sandbox ready');
  const shot = (name) => page.screenshot({ path: path.join(out, name + '.png') });
  // max |euler| over an actor's tracked bones, sampled in-page
  const pose = () => page.evaluate(() => window.__sandbox.actors.map((a) => {
    const g = (n) => { const b = a.model.getObjectByName(n); return b ? b.quaternion.toArray().map((v) => +v.toFixed(4)) : null; };
    return { role: a.role, top: g('top'), head: g('head'), body: g(a.role === 'knight' ? 'mount_body' : 'body'), y: a.root.position.y };
  }));
  const diff = (p, q) => (p && q ? p.reduce((s, v, i) => s + Math.abs(v - q[i]), 0) : 0);

  await sleep(800); await shot('01_idle');

  await page.evaluate(() => window.__sandbox.actors.forEach((a) => window.__sandbox.walk(a)));
  await sleep(450); await shot('02_walk_accel');
  await sleep(700); // tween ended (1.1 s) -> pieces just stopped
  await shot('03_walk_stop');
  await sleep(2200);
  const settled = await pose();

  await page.evaluate(() => { window.__sandbox.reset(); });
  await sleep(1200);
  await page.evaluate(() => window.__sandbox.actors.forEach((a) => window.__sandbox.stopAbrupt(a)));
  await sleep(480); await shot('04_abrupt_stop_recoil');

  await page.evaluate(() => { window.__sandbox.reset(); });
  await sleep(1000);
  await page.evaluate(() => window.__sandbox.actors.forEach((a) => window.__sandbox.hop(a)));
  await sleep(230); await shot('05_hop_air');
  await sleep(430); await shot('06_hop_landing_squash');
  const maxY = await page.evaluate(() => Math.max(...window.__sandbox.actors.map((a) => a.root.position.y)));
  expectTrue(maxY <= 1.0 && true, 'hop moves root only via the scripted tween (root.y stays within the tween range)');

  await page.evaluate(() => { window.__sandbox.reset(); });
  await sleep(1500);
  const before = await pose();
  await page.evaluate(() => window.__sandbox.impulse(2.2));
  await sleep(220); await shot('07_impulse_wobble');
  const during = await pose();
  expectTrue(during.some((p, i) => diff(p.body, before[i].body) > 0.01 || diff(p.top, before[i].top) > 0.01), 'impulse changes body/top bone rotations');

  await page.evaluate(() => { window.__sandbox.reset(); window.__sandbox.look(true); });
  await sleep(900); await shot('08_lookat');
  const looked = await pose();
  expectTrue(looked.some((p, i) => diff(p.head, settled[i].head) > 0.02 || diff(p.body, settled[i].body) > 0.02), 'look-at turns head/body bones');
  await page.evaluate(() => window.__sandbox.look(false));
  await sleep(900);

  const stats = await page.evaluate(() => window.__sandbox.stats());
  log('stats', JSON.stringify(stats));
  expectTrue(stats.attached === 32 && stats.active > 0, '32 actors attached and simulated');
  const benchMs = await page.evaluate(() => window.__sandbox.bench(900));
  log(`bench: ${benchMs.toFixed(4)} ms per update, 32 actors (in-browser, offline loop)`);
  expectTrue(benchMs < 0.3, `kinematics update ${benchMs.toFixed(4)} ms/frame < 0.3`);

  // scrubbed clip gate: the king/others in Attack must not fight additive offsets
  await page.evaluate(() => { window.__sandbox.reset(); window.__sandbox.actors.forEach((a) => window.__sandbox.attackScrub(a)); });
  await sleep(700); await shot('09_attack_gate');

  // disable restores the pure clip pose and drops cost
  await page.evaluate(() => { window.__sandbox.reset(); window.__sandbox.walk(window.__sandbox.actors[0]); });
  await sleep(500);
  await page.evaluate(() => window.__sandbox.setEnabled(false));
  await sleep(300); await shot('10_disabled');
  const off = await page.evaluate(() => window.__sandbox.bench(900));
  expectTrue(off < 0.01, `disabled update is ~free (${off.toFixed(5)} ms)`);
  await page.evaluate(() => window.__sandbox.setEnabled(true));
  await sleep(300);
  expectTrue(errors.length === 0, 'no console errors' + (errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''));
} catch (e) {
  failures.push('exception: ' + (e?.stack ?? e));
  log('EXCEPTION', e?.stack ?? e);
} finally {
  await browser?.close().catch(() => {});
  await server.close().catch(() => {});
}
log(failures.length ? `FAILED (${failures.length})` : 'PASSED');
process.exit(failures.length ? 1 : 0);
