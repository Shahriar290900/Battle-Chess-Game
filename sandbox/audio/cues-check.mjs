// Headless Brave check for the contract v1.4 cues (slides, shields, armour, landings, categories).
//   1. sandbox/audio.html: every manifest file decodes (incl. loop guards), loops start / follow speed / stop, the
//      2-loop cap and the 6 s failsafe hold, category volumes persist.
//   2. the real game (?debug): a scripted game (pawn capture, rook hops, castling, rook capture) is played through
//      the real controller + cinematics while every audio-relevant bus event is logged; the expected sequence is asserted
//      and no slide loop may remain open.
// Own Vite port (5193, never 5173); closes only the browser and server it started.  Run:  node sandbox/audio/cues-check.mjs
import { chromium } from '@playwright/test';
import { createServer } from 'vite';

const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const PORT = Number(process.env.CUES_PORT ?? 5193);
if (PORT === 5173) throw new Error('refusing port 5173');
const t0 = Date.now();
const log = (...a) => console.log(`[cues ${((Date.now() - t0) / 1000).toFixed(0)}s]`, ...a);
const errors = [];
const expect = (cond, msg) => { if (!cond) { errors.push(msg); console.error('FAIL', msg); } else log('ok  ', msg); };

const server = await createServer({ server: { port: PORT, strictPort: true, host: '127.0.0.1', hmr: false, watch: null }, logLevel: 'error' });
await server.listen();
let browser;
try {
  for (let attempt = 1; !browser; attempt++) {
    try { browser = await chromium.launch({ executablePath: BRAVE, headless: true, timeout: 180000, args: ['--autoplay-policy=no-user-gesture-required'] }); }
    catch (e) { if (attempt >= 3) throw e; log('launch retry', e.message.split('\n')[0]); }
  }
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });

  // ------------------------------------------------------------------ 1. sandbox
  const sb = await ctx.newPage();
  sb.on('console', (m) => { if (['error', 'warning'].includes(m.type()) && !/Failed to load resource/.test(m.text())) errors.push(`sandbox ${m.type()}: ${m.text()}`); });
  sb.on('response', (r) => { if (r.status() >= 400 && !/theme\.mp3|favicon/.test(r.url())) errors.push(`HTTP ${r.status()} ${r.url()}`); });
  sb.on('pageerror', (e) => errors.push(`sandbox pageerror: ${e}`));
  await sb.goto(`http://127.0.0.1:${PORT}/sandbox/audio.html`);
  await sb.waitForSelector('#app h3');
  const probe = await sb.evaluate(() => window.sfxProbe());
  log('probe', JSON.stringify({ total: probe.total, keys: probe.keys, failed: probe.failed.length, kb: Math.round(probe.bytes / 1024) }));
  expect(probe.failed.length === 0, `every manifest file decodes (${probe.total} files, ${probe.keys} keys)`);

  const man = await sb.evaluate(async () => (await (await fetch('/audio/sfx/manifest.json')).json()).entries);
  const need = [];
  for (const f of ['emberhold', 'rime']) {
    need.push(`slide:${f}`, `slide:${f}:start`, `slide:${f}:stop`, `shield:flash:${f}`, `shield:break:${f}`, `armour:hit:${f}`, `armour:hit:${f}:heavy`, `land:${f}`, `land:${f}:s1`, `land:${f}:s2`, `land:${f}:s3`);
  }
  need.push('sting:draw');
  expect(need.every((k) => man[k]), 'manifest has every new key');
  expect(['slide:emberhold', 'slide:rime'].every((k) => man[k].loop && man[k].loop.end > man[k].loop.start + 2), 'slide loops carry a loop region');

  await sb.click('button:has-text("slide start")'); // unlocks audio, starts decoding the loop buffer
  await sb.waitForTimeout(1500);
  await sb.click('button:has-text("slide stop")');
  await sb.waitForTimeout(400);
  const dbg = () => sb.evaluate(() => window.slideProbe());
  // the first start only warms the loop buffer when it is not decoded yet; retrigger until a voice opens
  for (let i = 0; i < 12 && (await dbg()).loops < 1; i++) { await sb.click('button:has-text("slide start")'); await sb.waitForTimeout(400); }
  expect((await dbg()).loops === 1, 'slide start opens exactly one loop voice');
  await sb.locator('#slide-speed').fill('5');
  await sb.waitForTimeout(200);
  expect((await dbg()).loops === 1, 'moving the speed slider retargets the live loop (still one voice)');
  await sb.click('button:has-text("slide stop")');
  await sb.waitForTimeout(500);
  expect((await dbg()).loops === 0, 'slide stop releases the loop');

  // cap: three different pieces sliding at once -> never more than 2 loops
  await sb.evaluate(() => { const e = window.audio; for (const [f, r] of [['emberhold', 'pawn'], ['rime', 'queen'], ['emberhold', 'king']]) e.slide(f, r, 'start', 2); });
  await sb.waitForTimeout(250);
  expect((await dbg()).loops <= 2, `loop cap holds (loops=${(await dbg()).loops})`);
  await sb.evaluate(() => { const e = window.audio; for (const [f, r] of [['emberhold', 'pawn'], ['rime', 'queen'], ['emberhold', 'king']]) e.slide(f, r, 'stop', 0); });
  await sb.waitForTimeout(400);
  expect((await dbg()).loops === 0, 'all loops stopped');

  // failsafe: a start that never gets its stop dies after 6 s
  await sb.click('button:has-text("forget stop")');
  await sb.waitForTimeout(400);
  expect((await dbg()).loops === 1, 'forgotten slide is running');
  await sb.waitForTimeout(6300);
  expect((await dbg()).loops === 0, 'forgotten slide auto-stops after ~6 s');

  // categories persist
  await sb.locator('#cat-ambience').fill('0.3');
  await sb.locator('#cat-music').fill('0.6');
  const cats = await sb.evaluate(() => ({ dbg: window.audio.debug().categories, ls: JSON.parse(localStorage.getItem('battle-chess.audio.categories') ?? '{}') }));
  expect(Math.abs(cats.dbg.ambience - 0.3) < 1e-6 && Math.abs(cats.ls.music - 0.6) < 1e-6, `category volumes set + persisted ${JSON.stringify(cats.ls)}`);
  await sb.evaluate(() => { window.audio.setCategoryVolume('ambience', 1); window.audio.setCategoryVolume('music', 1); });
  // every new sfx button plays without errors
  for (const name of ['slide:emberhold', 'shield:flash:rime', 'shield:break:emberhold', 'armour:hit:rime', 'land:emberhold']) { await sb.getByRole('button', { name, exact: true }).first().click(); await sb.waitForTimeout(80); }
  await sb.click('button:has-text("fight sequence")');
  await sb.waitForTimeout(2200);
  await sb.close();

  // ------------------------------------------------------------------ 2. real game
  // Vite's first-run dependency optimiser may reload the page once mid-way; the phase is simply repeated then.
  const gamePhase = async () => {
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error' && !/favicon|Failed to load resource/.test(m.text())) errors.push(`game console.error: ${m.text()}`); });
  page.on('pageerror', (e) => errors.push(`game pageerror: ${e.message}`));
  page.on('framenavigated', (f) => { if (f === page.mainFrame()) log('navigated ->', f.url()); });
  page.on('console', (m) => { if (/reload|optimi|context lost|Error/i.test(m.text())) log('console:', m.type(), m.text().slice(0, 200)); });
  await page.goto(`http://127.0.0.1:${PORT}/?debug&quality=low`, { waitUntil: 'load', timeout: 120000 });
  log('game loading');
  await page.waitForSelector('.gate-btn:not([hidden])', { timeout: 180000 });
  await page.keyboard.press('Space');
  await page.waitForSelector('.menu:not([hidden])', { timeout: 30000 });
  await page.evaluate(async () => {
    const b = window.__bc;
    await b.attract?.stop?.(); // the launch flyover must be fully stopped (it skips sequences while stopping)
    window.__evlog = [];
    const t = performance.now();
    for (const n of ['move:slide', 'move:step', 'land', 'shield:flash', 'shield:break', 'armour:hit', 'capture:begin', 'capture:impact', 'capture:shatter', 'capture:end', 'attack:whoosh', 'castle', 'clash'])
      b.bus.on(n, (p) => window.__evlog.push({ n, t: Math.round(performance.now() - t), p }));
  });
  // a scripted game from a FEN: pawn takes pawn, rook hop, castle, rook takes rook
  const FEN = 'r3k2r/1pp2pp1/8/3p4/4P3/8/PPP2PPP/R3K2R w KQkq - 0 1';
  await page.evaluate((fen) => window.__bc.controller.newGame({ kind: 'hotseat', playerSide: 'w', aiLevel: 'easy', fen }), FEN);
  // the FEN position must be on the board (pieces loaded, state awaiting input) or the first move degrades to a plain sync
  for (let i = 0; i < 180; i++) {
    const ready = await page.evaluate(() => { const b = window.__bc; return b.controller.snapshot().state === 'awaitInput' && !!b.board.actorAt('e4') && !!b.board.actorAt('d5'); });
    if (ready) break;
    await page.waitForTimeout(500);
  }
  await page.waitForTimeout(1500);
  const mv = async (a, b, label) => {
    await page.evaluate(() => { window.__evlog.length = 0; });
    const ok = await page.evaluate(([x, y]) => window.__bc.controller.attemptMove(x, y), [a, b]);
    expect(ok, `${label}: ${a}${b} accepted`);
    log(`${label}: after attemptMove evlog=${await page.evaluate(() => window.__evlog.length)} busy=${await page.evaluate(() => window.__bc.controller.snapshot().busy)} state=${await page.evaluate(() => window.__bc.controller.snapshot().state)}`);
    // software GL shares the machine with other jobs: poll (bounded) instead of one long await
    for (let i = 0; i < 90 && !(await page.evaluate(() => window.__evlog.length)); i++) await page.waitForTimeout(500); // sequence start
    let idle = 0;
    for (let i = 0; i < 400 && idle < 3; i++) {
      await page.waitForTimeout(1000);
      const busy = await page.evaluate(() => window.__bc.services.sequences.running || window.__bc.controller.snapshot().busy);
      idle = busy ? 0 : idle + 1;
      if (i % 30 === 29) log(`${label}: waiting, events so far ${await page.evaluate(() => window.__evlog.length)}`);
    }
    await page.waitForTimeout(400);
    return page.evaluate(() => window.__evlog.map((e) => `${e.n}${e.p.phase ? ':' + e.p.phase : ''}${e.p.role ? '@' + e.p.role : ''}`));
  };
  const open = (names) => {
    let n = 0; for (const s of names) { if (s.startsWith('move:slide:start')) n++; else if (s.startsWith('move:slide:stop')) n--; }
    return n;
  };
  let seq = await mv('e4', 'd5', 'pawn x pawn');
  log(seq.join(' '));
  expect(seq.includes('capture:begin') && seq.includes('capture:impact') && seq.includes('capture:shatter') && seq.includes('capture:end'), 'capture beats present');
  expect(seq.some((s) => s.startsWith('shield:flash')) && seq.some((s) => s.startsWith('shield:break')), 'shield-bearing pawn defender: shield:flash + shield:break');
  expect(seq.lastIndexOf('shield:flash') < seq.indexOf('capture:impact') && seq.indexOf('shield:break') > seq.indexOf('capture:impact'), 'shield flash precedes the impact, break follows it');
  expect(seq.some((s) => s.startsWith('armour:hit')), 'pawn bash bites armour');
  expect(open(seq) === 0, 'no slide left open after the pawn capture');

  seq = await mv('a8', 'a4', 'black rook hop');
  log(seq.join(' '));
  expect(seq.filter((s) => s.startsWith('land')).length >= 3, `rook hops land per square (${seq.filter((s) => s.startsWith('land')).length})`);

  seq = await mv('e1', 'g1', 'castle');
  log(seq.join(' '));
  expect(seq.includes('move:slide:start@king') && seq.includes('move:slide:stop@king'), 'castling king slides');
  expect(seq.includes('land@rook') && seq.includes('castle'), 'castling rook lands, castle event');
  expect(open(seq) === 0, 'no slide left open after castling');

  seq = await mv('a4', 'a2', 'black rook x pawn');
  log(seq.join(' '));
  expect(seq.includes('land@rook') && seq.includes('capture:impact') && open(seq) === 0, 'black rook slam: land + impact, slides balanced');
  const loops = await page.evaluate(() => window.__bc.services.audio.debug?.().loops);
  expect(loops === 0, `no loop voice left running in the real game (loops=${loops})`);
  await page.close();
  };
  for (let attempt = 1; ; attempt++) {
    const before = errors.length;
    try { await gamePhase(); break; }
    catch (e) {
      if (attempt >= 3 || !/context was destroyed|navigation/i.test(String(e))) throw e;
      log('page navigated mid-run, repeating the game phase', String(e).split('\n')[0]);
      errors.length = before;
      for (const pg of ctx.pages()) await pg.close().catch(() => {});
    }
  }
} finally {
  await browser?.close();
  await server.close();
}
if (errors.length) { console.error('FAIL', errors.slice(0, 25)); process.exit(1); }
console.log('cue check passed');
