// Scripted duel through the REAL UI: persona "Careful" (sensible chess, normal flows) vs persona "Chaos" (edge-case hunter).
// See tests/playtest/README.md. Run: node tests/playtest/duel.mjs   (env: PLAYTEST_PORT, PLAYTEST_SEED, PLAYTEST_BUDGET_MIN, PLAYTEST_ONLY)
import { chromium } from '@playwright/test';
import { Chess } from 'chess.js';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { bestMove, chaosMove, mulberry32 } from './lib/engine.mjs';
import { createDriver, sleep, Stuck } from './lib/driver.mjs';
import { probeInit } from './lib/page.mjs';
import { Recorder } from './lib/recorder.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, '..', '..');
const OUT = join(here, 'out');
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const PORT = Number(process.env.PLAYTEST_PORT || 5391); // never 5173
const SEED = Number(process.env.PLAYTEST_SEED || 20261023);
const BUDGET_MIN = Number(process.env.PLAYTEST_BUDGET_MIN || 24);
const ONLY = (process.env.PLAYTEST_ONLY || '').split(',').filter(Boolean);
const DUEL_PLIES = Number(process.env.PLAYTEST_DUEL_PLIES || 64);
const want = (name) => !ONLY.length || ONLY.includes(name);

const rng = mulberry32(SEED);
const rec = new Recorder(OUT, ['careful', 'chaos']);
const D = createDriver(rec, { rng });
D.deadline = Date.now() + BUDGET_MIN * 60000;
const log = D.log;
const VPS = { desktop: [1280, 720], portrait: [390, 844], landscape: [844, 390] };

let server, browser, context, page;
const phasesRun = [];

// ---------------------------------------------------------------------------------------------- browser plumbing
async function newPage(contextOpts, label) {
  if (context) await context.close().catch(() => undefined);
  context = await browser.newContext(contextOpts);
  await context.addInitScript(probeInit);
  page = await context.newPage();
  D.page = page; rec.page = page;
  page.on('console', (m) => {
    const t = m.type();
    if (t !== 'error' && t !== 'warning') return;
    const text = m.text();
    if (/favicon/.test(text)) return;
    const loc = m.location();
    rec.consoleMsg(t === 'error' ? 'error' : 'warning', text, loc && loc.url ? `${loc.url.split('/').slice(-2).join('/')}:${loc.lineNumber}` : undefined);
  });
  page.on('pageerror', (e) => { rec.consoleMsg('pageerror', `${e.message}\n${(e.stack || '').split('\n').slice(0, 3).join('\n')}`); void rec.anomaly('page-error', e.message.slice(0, 200), { severity: 'error' }); });
  page.on('crash', () => void rec.anomaly('page-crash', 'renderer crashed', { severity: 'error', shot: false }));
  page.on('requestfailed', (r) => { if (!/favicon/.test(r.url()) && !(/audio\//.test(r.url()) && /ERR_ABORTED/.test(r.failure()?.errorText ?? ''))) rec.consoleMsg('error', `requestfailed ${r.url()} ${r.failure()?.errorText}`); });
  log('opening page for', label);
  await page.goto(`http://127.0.0.1:${PORT}/?debug&quality=low`, { waitUntil: 'load', timeout: 180000 });
  await page.waitForSelector('.gate-btn:not([hidden])', { timeout: 240000 });
  await sleep(500);
  if (D.touch) await page.locator('.gate-btn').tap(); else await page.keyboard.press('Space');
  await page.waitForSelector('.menu:not([hidden])', { timeout: 60000 });
  await D.probeBus();
  await sleep(700);
  rec.act('boot', label, { tier: await page.evaluate(() => window.__bc.quality.tier), ui: await D.obs() });
}

async function resize(name) {
  const [w, h] = VPS[name];
  await page.setViewportSize({ width: w, height: h });
  rec.act('resize', name, { w, h });
  await sleep(500);
}

async function phase(name, persona, fn) {
  if (!want(name)) return;
  if (D.timeLeft() < 20000) { rec.use(persona, name); rec.note(`phase ${name} skipped: time budget exhausted`); log('SKIP (budget)', name); return; }
  rec.use(persona, name);
  const t0 = Date.now();
  log('=== phase', name);
  await D.flushFps('before:' + name);
  let status = 'ok';
  try { await fn(); }
  catch (e) {
    status = e instanceof Stuck ? 'stuck' : 'harness-exception';
    log('phase failed:', e.message);
    if (!(e instanceof Stuck)) { rec.note(`phase ${name} threw: ${e.stack?.split('\n').slice(0, 4).join(' | ')}`); await rec.anomaly('harness-exception', `${name}: ${e.message}`, { severity: 'error', key: name }); }
    await rec.shot(`fail-${name}.png`).catch(() => undefined);
    await recover();
  }
  await D.flushFps('phase:' + name);
  phasesRun.push({ name, persona, status, seconds: +((Date.now() - t0) / 1000).toFixed(1) });
}

/** After a failed phase: try to get back to a usable menu, else reload the page. */
async function recover() {
  try {
    await page.setViewportSize({ width: 1280, height: 720 }).catch(() => undefined);
    if (await D.ensureMainMenu()) return;
  } catch { /* fall through */ }
  rec.note('recover: reloading page');
  await page.goto(`http://127.0.0.1:${PORT}/?debug&quality=low`, { waitUntil: 'load', timeout: 180000 });
  await page.waitForSelector('.gate-btn:not([hidden])', { timeout: 240000 });
  await page.keyboard.press('Space');
  await page.waitForSelector('.menu:not([hidden])', { timeout: 60000 });
  await D.probeBus();
}

// ---------------------------------------------------------------------------------------------- shared game bits
async function gameOverCheck(label, { expectTitle, dismiss = 'View Board' } = {}) {
  const o = await D.waitFor((s) => s.overOpen, D.T(9000));
  if (!o) { await rec.anomaly('gameover-overlay-missing', `${label}: game over but no overlay within 9 s`, { severity: 'error' }); return null; }
  await sleep(400);
  const txt = await page.evaluate(() => ({ title: document.querySelector('.over .ttl')?.textContent, kick: document.querySelector('.over .kick')?.textContent, sub: document.querySelector('.over .sub')?.textContent, acts: Array.from(document.querySelectorAll('.over .btn')).map((b) => b.textContent.trim()) }));
  rec.act('gameover', label, { ...txt, result: o.result });
  if (expectTitle && !new RegExp(expectTitle, 'i').test(txt.title ?? '')) await rec.anomaly('gameover-title-wrong', `${label}: expected "${expectTitle}" got "${txt.title}" / "${txt.sub}"`, { key: label, severity: 'error' });
  await rec.shot(`gameover-${label.replace(/\W+/g, '-')}.png`);
  await D.audit('gameover');
  await D.hoverTips(['.over .btn:has-text("Rematch")'], 'gameover');
  if (dismiss) await D.uiClick(`.over .btn:has-text("${dismiss}")`, `gameover:${dismiss}`);
  await sleep(300);
  return txt;
}

async function togglePause(label) {
  await page.keyboard.press('Escape');
  const ok = await page.waitForSelector('.pause:not([hidden])', { timeout: D.T(6000) }).then(() => true).catch(() => false);
  if (!ok) { await rec.anomaly('pause-not-opening', `${label}: Escape did not open the pause menu`, { key: label, severity: 'error' }); return false; }
  await sleep(250);
  await D.audit('pause');
  return true;
}

// ---------------------------------------------------------------------------------------------- CAREFUL turn
async function carefulTurn() {
  rec.use('careful');
  const ctx = D.ctx;
  await D.reconcile('careful turn start');
  const n = ++ctx.cn;
  const hud = async () => (await D.obs()).hudVisible;
  if (n === 2 && (await hud())) { // open the move list and compare it with the game
    const before = await D.obs();
    if (!before.journalVisible) await D.uiClick('.ibtn[aria-label="Move list"]', 'hud:move-list');
    await sleep(350);
    const o = await D.obs();
    if (!o.journalVisible) await rec.anomaly('journal-not-shown', 'Move list button did not show the journal', { severity: 'error' });
    const sans = await page.evaluate(() => Array.from(document.querySelectorAll('.hud .journal .mv:not(.ph)')).map((e) => e.textContent));
    const want = ctx.mirror.history();
    if (sans.join(' ') !== want.join(' ')) await rec.anomaly('journal-mismatch', `journal "${sans.join(' ')}" vs rules "${want.join(' ')}"`, { key: 'journal-n2', severity: 'error' });
    await D.hoverTips(['.ibtn[aria-label="Move list"]', '.ibtn[aria-label="Undo"]', '.ibtn[aria-label="Pause menu"]'], 'hud');
    await D.audit('journal-open');
  }
  if (n === 3 && (await hud())) { // settings mid-game: animations Quick, highlight style
    if (await D.openSettings('hud')) {
      await D.audit('settings-general');
      await D.setRow('Gameplay', 'Animations', 'Quick', { path: 'captureMode', value: 'quick' });
      await D.setRow('Gameplay', 'Tile highlights', 'Brackets', { path: 'highlightStyle', value: 'brackets' });
      await D.audit('settings-gameplay');
      await D.hoverTips(['.settings .row[aria-label="Animations"]', '.settings .cats .btn:has-text("Video")'], 'settings');
      await rec.shot('settings-gameplay.png');
      await D.closeSettings();
      await D.integrity('after settings');
    }
  }
  if (n === 4 && (await hud())) {
    if (await D.openSettings('hud')) {
      await D.setRange('Gameplay', 'Animation speed', 'maximum', { path: 'animSpeed', min: 1.3 });
      await D.setRow('Gameplay', 'Move list', 'Off', { path: 'showMoveList', value: false });
      await D.setRow('Gameplay', 'Move list', 'On', { path: 'showMoveList', value: true });
      await D.closeSettings();
    }
  }
  if (n === 5 && (await hud())) { // graphics preset round trip
    if (await D.openSettings('hud')) {
      await D.setRow('Video', 'Preset', 'High', undefined);
      await sleep(900);
      await D.audit('settings-video');
      await rec.shot('settings-video.png');
      await D.setRow('Video', 'Preset', 'Low', undefined);
      await D.closeSettings();
      await D.syncCheck('after preset change');
    }
  }
  if (n === 6) { // pause + resume
    const before = await D.obs();
    if (await togglePause('careful n6')) {
      await D.hoverTips(['.pause .btn:has-text("Resume")', '.pause .btn:has-text("Resign")'], 'pause');
      await rec.shot('pause.png');
      await D.uiClick('.pause .btn:has-text("Resume")', 'pause:resume');
      await sleep(300);
      const a = await D.obs();
      if (a.fen !== before.fen || a.state !== 'awaitInput') await rec.anomaly('resume-changed-state', `pause/resume changed state ${before.state}->${a.state} fen ${before.fen === a.fen}`, { severity: 'error' });
    }
  }
  if (n === 8 && ctx.mirror.history().length >= 2) { // undo via HUD
    const before = await D.obs();
    if (before.canUndo) {
      const expFen = D.fenBefore(1);
      await D.uiClick('.ibtn[aria-label="Undo"]', 'hud:undo');
      await sleep(900);
      const after = await D.obs();
      rec.act('undo', 'hud-button', { expected_fen: expFen, observed_fen: after.fen, ui: after });
      if (after.fen !== expFen) await rec.anomaly('undo-wrong-position', `undo expected ${expFen} got ${after.fen}`, { severity: 'error' });
      await D.resync('careful undo');
      await D.syncCheck('after undo');
      return; // turn passes back to whoever is now on move
    } else await rec.anomaly('undo-disabled', `Undo disabled at ply ${before.plies}`, { key: 'undo-disabled', severity: 'warn' });
  }
  if (n === 10 && (await hud())) {
    if (await D.openSettings('hud')) {
      await D.setRow('Gameplay', 'Animations', 'Off', { path: 'captureMode', value: 'off' });
      await D.setRow('Gameplay', 'Tile highlights', 'Runes', { path: 'highlightStyle', value: 'runes' });
      await D.setRow('Gameplay', 'Colour-blind mode', 'On', { path: 'colorBlind', value: true });
      await D.setRow('Gameplay', 'Colour-blind mode', 'Off', { path: 'colorBlind', value: false });
      await D.closeSettings();
    }
    await page.keyboard.press('j'); await sleep(300); // keyboard shortcut: toggle move list
    const o = await D.obs();
    if (o.journalVisible !== (await D.getSetting('showMoveList'))) await rec.anomaly('journal-shortcut-mismatch', 'J key and setting disagree', { severity: 'error' });
  }
  const mv = bestMove(ctx.mirror.fen(), { depth: 3, rng });
  if (!mv) return;
  await D.humanMove(mv.from, mv.to, { via: 'click', promo: mv.promotion ? { q: 'queen', r: 'rook', b: 'bishop', n: 'knight' }[mv.promotion] : null });
}

// ---------------------------------------------------------------------------------------------- CHAOS turn
async function chaosTurn() {
  rec.use('chaos');
  const ctx = D.ctx;
  await D.reconcile('chaos turn start');
  const n = ++ctx.xn;
  const o0 = await D.obs();
  const say = (t) => log('chaos:', t);
  if (n === 1) { // misclicks, wrong-colour selects, double click, illegal destinations
    say('misclicks / illegal inputs');
    await D.cameraStable();
    for (let i = 0; i < 3; i++) { const e = await D.emptyPoint(); await D.tap(e.x + i * 17, e.y); rec.act('misclick', 'off-board', { x: e.x + i * 17, y: e.y }); await sleep(120); }
    let c0 = await D.evCount('ui:select');
    await D.clickSq('e2', 'opponent-piece'); await sleep(300); // White piece while Black is to move
    if ((await D.evCount('ui:select')) > c0) await rec.anomaly('selected-opponent-piece', 'Black could select a White piece on its own turn', { severity: 'error' });
    const plyNow = async (what) => { const q = (await D.obs()).plies; if (q !== o0.plies) await rec.anomaly('illegal-input-played-a-move', `${what} changed the game (plies ${o0.plies} -> ${q}). Likely cause: a re-click on the upper body of a selected tall piece resolves to the legal destination tile behind it`, { key: what, severity: 'error' }); return q; };
    const p = await D.point('e7');
    await pageDouble(p.x, p.y); await sleep(500);
    rec.act('double-click', 'e7', { x: Math.round(p.x), y: Math.round(p.y), reachable: p.ok, pliesAfter: await plyNow('double-click on e7') });
    await D.resync('after dblclick');
    if ((await D.obs()).turn === o0.turn) {
      await D.clickSq('e7', 'select'); await sleep(250);
      await D.clickSq('e3', 'illegal-destination'); await sleep(300); // pawn cannot go from e7 to e3
      await plyNow('click on illegal destination e3');
      await D.clickSq('a1', 'illegal-destination-far'); await sleep(300);
      await plyNow('click on far illegal destination a1');
    }
    const lifted = await D.liftedCount();
    rec.act('state-after-illegal', 'e7', { lifted });
    const e = await D.emptyPoint(); await D.tap(e.x, e.y); await sleep(250);
    if ((await D.obs()).plies !== o0.plies) await rec.anomaly('illegal-input-played-a-move', `misclicks/illegal destinations changed the game (plies ${o0.plies} -> ${(await D.obs()).plies})`, { severity: 'error' });
    await D.resync('after chaos n1');
    const l2 = await D.liftedCount();
    if (l2) await rec.anomaly('piece-stays-lifted-after-deselect', `${l2} piece(s) still lifted after clicking off-board`, { severity: 'error' });
    await D.integrity('after chaos n1');
  }
  if (n === 2 && ctx.mirror.history().length >= 3) { // undo spam
    say('undo spam');
    const before = await D.obs();
    for (let i = 0; i < 3; i++) { await page.keyboard.press('u'); }
    for (let i = 0; i < 2; i++) await page.click('.ibtn[aria-label="Undo"]', { timeout: 1500, force: true }).catch(() => undefined);
    await sleep(1200);
    const after = await D.obs();
    rec.act('undo-spam', '3xU + 2xclick', { plies_before: before.plies, plies_after: after.plies, ui: after });
    await D.resync('undo spam');
    if (after.plies < before.plies - 5 || after.plies > before.plies) await rec.anomaly('undo-spam-count', `spam undo moved ${before.plies} -> ${after.plies}`, { severity: 'warn' });
    if (!(await D.reconcile('undo spam'))) await rec.shot('undo-spam-fen.png');
    if (after.state !== 'awaitInput') await rec.anomaly('undo-spam-stuck', `state ${after.state} after undo spam`, { severity: 'error', data: after });
    await D.syncCheck('after undo spam');
    return;
  }
  // the move itself
  let mv = chaosMove(ctx.mirror.fen(), rng);
  if (!mv) return;
  const promoName = mv.promotion ? { q: 'queen', r: 'rook', b: 'bishop', n: 'knight' }[mv.promotion] : null;
  const base = { promo: promoName };
  if (n === 3) { say('drag and drop'); await D.humanMove(mv.from, mv.to, { ...base, via: 'drag' }); return; }
  if (n === 4) { // drag onto illegal square, drag outside the canvas, then a click move
    say('bad drags');
    const legalNow = ctx.mirror.moves({ verbose: true });
    const piece = legalNow[0];
    const bad = ['a1', 'h8', 'e4'].find((s) => !legalNow.some((m) => m.from === piece.from && m.to === s) && s !== piece.from) ?? 'a1';
    const c0 = (await D.obs()).plies;
    await D.dragSq(piece.from, bad); await sleep(500);
    if ((await D.obs()).plies !== c0) await rec.anomaly('illegal-drag-accepted', `dragging ${piece.from} to ${bad} changed the game`, { severity: 'error' });
    await D.dragSq(piece.from, null, { toPoint: { x: -40, y: 300 } }); await sleep(500);
    await D.dragSq(piece.from, null, { toPoint: { x: 1300, y: 400 }, steps: 6 }); await sleep(500);
    await D.integrity('after bad drags');
    const lifted = await D.liftedCount();
    rec.act('state-after-bad-drags', piece.from, { lifted });
    const e = await D.emptyPoint(); await D.tap(e.x, e.y); await sleep(300);
    await D.syncCheck('after bad drags');
  }
  if (n === 5) { // pause opens while the sequence runs
    say('pause during sequence');
    await D.humanMove(mv.from, mv.to, { ...base, during: async () => {
      await page.keyboard.press('Escape');
      await page.waitForSelector('.pause:not([hidden])', { timeout: D.T(6000) }).catch(() => undefined);
      await sleep(400);
      const o = await D.obs();
      rec.act('pause-during-sequence', 'Escape', { ui: o });
      await rec.shot('pause-mid-sequence.png');
      await D.audit('pause-mid-sequence');
      await page.keyboard.press('Escape'); await sleep(300);
    } });
    return;
  }
  if (n === 6) { // tap to skip + double-click on the destination
    say('skip taps and double-click destination');
    await D.humanMove(mv.from, mv.to, { ...base, during: async () => {
      const e = await D.emptyPoint();
      for (let i = 0; i < 3; i++) { await D.tap(e.x, e.y); await sleep(70); }
      await page.keyboard.press('Space');
      rec.act('skip-spam', 'tap x3 + Space');
    } });
    return;
  }
  if (n === 7) { // viewport changes mid-move
    say('resize mid-move');
    await D.humanMove(mv.from, mv.to, { ...base, during: async () => {
      for (const name of ['portrait', 'landscape', 'desktop']) {
        await resize(name);
        await D.audit('resize-' + name);
        await rec.shot(`resize-${name}.png`);
      }
    } });
    return;
  }
  if (n === 8) { // settings opened mid-sequence + camera mode flip
    say('settings mid-sequence');
    await D.humanMove(mv.from, mv.to, { ...base, during: async () => {
      if (await D.openSettings('hud')) {
        await D.setRow('Gameplay', 'Camera', 'Fixed', { path: 'cameraMode', value: 'fixed' });
        await D.closeSettings();
      }
    } });
    await D.cameraStable();
    return;
  }
  if (n === 9) { // keyboard spam during sequence, Tab navigation
    say('keyboard spam');
    await D.humanMove(mv.from, mv.to, { ...base, during: async () => {
      for (const k of ['Space', 'Enter', 'Tab', 'Space', 'ArrowLeft', 'Space']) { await page.keyboard.press(k); await sleep(60); }
      rec.act('key-spam', 'Space/Enter/Tab/Arrows');
    } });
    const o = await D.obs();
    if (o.screens.filter((c) => c !== 'loading').length) { await rec.anomaly('keyboard-opened-screen', `key spam left screen open: ${o.screens.join(',')}`, { severity: 'warn' }); await D.closeAllScreens(); }
    if (o.state === 'awaitInput') {
      const f = await page.evaluate(() => { const a = document.activeElement; return a ? a.tagName + '.' + (a.className || '') + '[' + (a.getAttribute('aria-label') || a.textContent || '').slice(0, 20) + ']' : null; });
      rec.act('focus-after-spam', f);
    }
    return;
  }
  if (n === 10) { await D.openSettings('hud').then(async (ok) => { if (ok) { await D.setRow('Gameplay', 'Camera', 'Follow turn', { path: 'cameraMode', value: 'follow' }); await D.closeSettings(); } }); }
  if (n === 11) { // main menu mid-sequence, then Continue
    say('main menu mid-sequence + Continue');
    const moved = await D.humanMove(mv.from, mv.to, { ...base, during: async () => {
      await D.uiClick('.ibtn[aria-label="Pause menu"]', 'hud:pause', { force: true });
      await D.uiClick('.pause .btn:has-text("Main Menu")', 'pause:main-menu');
      await sleep(1500);
      await D.audit('menu-mid-game');
      const o = await D.obs();
      rec.act('main-menu-mid-game', 'state', { ui: o });
      const hasCont = await page.locator('.menu .btn:has-text("Continue")').count();
      if (!hasCont) await rec.anomaly('no-continue-button', 'Main menu mid-game shows no Continue', { severity: 'error' });
      await D.uiClick('.menu .btn:has-text("Continue")', 'menu:continue');
      await sleep(500);
    } });
    await D.cameraStable();
    return;
  }
  // later: random mix of ways to move
  const style = rng();
  const via = style < 0.25 ? 'drag' : 'click';
  await D.humanMove(mv.from, mv.to, { ...base, via });
  if (n % 6 === 0 && style > 0.7) { // random extra chaos: pause flick
    await page.keyboard.press('Escape'); await sleep(200 + Math.floor(rng() * 400)); await page.keyboard.press('Escape'); await sleep(300);
    rec.act('pause-flick', 'Escape x2');
  }
}

async function pageDouble(x, y) { await page.mouse.dblclick(x, y); }

// ---------------------------------------------------------------------------------------------- PHASE: the duel
async function duelPhase() {
  rec.use('careful', 'duel');
  await D.startHotseat('Turn the Board');
  await D.flushFps('duel:start');
  await rec.shot('duel-start.png');
  await D.audit('duel-start');
  await D.hoverTips(['.ibtn[aria-label="Undo"]'], 'hud');
  const t0 = Date.now();
  let mated = false;
  while (true) {
    const s = await D.obs();
    if (s.result) { mated = /checkmate/.test(s.result); break; }
    if (s.plies >= DUEL_PLIES) break;
    if (Date.now() - t0 > 8 * 60000 || D.timeLeft() < 5 * 60000) { rec.note('duel stopped by time cap'); break; }
    if (s.state !== 'awaitInput') { await D.settle('duel wait'); continue; }
    if (s.turn === 'w') await carefulTurn(); else await chaosTurn();
    // hot-seat integrity at each ply boundary
    await D.reconcile('duel loop');
    const q = await D.obs();
    if (D.ctx.mirror.history().length !== q.plies) await D.resync('duel loop');
  }
  await D.flushFps('duel:moves');
  const s = await D.obs();
  rec.game({ label: 'duel hotseat', plies: s.plies, result: s.result, fen: s.fen, mated });
  if (s.result) {
    rec.use('careful');
    await gameOverCheck('duel', { expectTitle: /checkmate|resign|stalemate|draw/.source, dismiss: 'View Board' });
    if (mated) { // careful takes the mate back via Undo from the finished game, replays it, then asks for a Rematch
      const expFen = D.fenBefore(1);
      await D.uiClick('.ibtn[aria-label="Undo"]', 'hud:undo-after-mate');
      await sleep(1200);
      const a = await D.obs();
      if (a.fen !== expFen || a.result || a.state !== 'awaitInput') await rec.anomaly('undo-after-mate', `undo from game over: state ${a.state} result ${a.result} fen ok=${a.fen === expFen}`, { severity: 'error', data: a });
      await D.resync('undo after mate');
      await D.syncCheck('after undo-from-gameover');
      const mv = bestMove(D.ctx.mirror.fen(), { depth: 2, rng });
      if (mv) await D.humanMove(mv.from, mv.to, { via: 'click' });
      await gameOverCheck('duel-replayed-mate', { dismiss: 'Rematch' });
      const r = await D.waitFor((x) => x.state === 'awaitInput' && x.plies === 0 && !x.result, 20000);
      if (!r) await rec.anomaly('rematch-failed', 'Rematch did not start a fresh game', { severity: 'error' });
      D.newCtx(null, 'rematch');
      await D.syncCheck('after rematch');
    }
  } else {
    rec.use('chaos');
    rec.act('resign', 'cap reached - chaos resigns via pause menu');
    if (await togglePause('resign')) {
      await D.uiClick('.pause .btn:has-text("Resign")', 'pause:resign (arm)');
      await sleep(3400); // arm timer is 3 s: label must reset
      const lbl = await page.locator('.pause .btn.danger .lbl').first().textContent().catch(() => '');
      if (/confirm/i.test(lbl ?? '')) await rec.anomaly('resign-arm-not-reset', 'Resign stayed armed after 3 s', { severity: 'warn' });
      await D.uiClick('.pause .btn:has-text("Resign")', 'pause:resign (arm again)');
      await D.uiClick('.pause .btn:has-text("Confirm resign")', 'pause:resign (confirm)');
      await gameOverCheck('duel-resign', { expectTitle: 'Resignation', dismiss: 'View Board' });
    }
  }
}

// ---------------------------------------------------------------------------------------------- PHASE: chaos scenarios
async function scenarioPhase() {
  rec.use('chaos');
  const done = async (label, o = {}) => {
    const s = await D.obs();
    rec.game({ label, plies: s.plies, result: s.result, fen: s.fen });
    if (s.result) await gameOverCheck(label, o);
  };
  const setAnim = async (v) => { if (await D.openSettings('hud')) { await D.setRow('Gameplay', 'Animations', v, { path: 'captureMode', value: v.toLowerCase() }); await D.closeSettings(); } };

  // --- castling, both sides (Quick animations)
  await D.startHotseat('Hold the Board');
  await setAnim('Quick');
  await D.startFen('r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1', 'castle-ks-white-qs-black');
  await D.humanMove('e1', 'g1', { via: 'click' });
  await D.humanMove('e8', 'c8', { via: 'drag' });
  await done('castle-ks-white-qs-black');

  await D.startFen('r3k2r/8/8/8/8/8/8/R3K2R w Kkq - 0 1', 'castle-illegal-then-legal');
  const s0 = await D.obs();
  await D.humanMove('e1', 'c1', { via: 'click', expectIllegal: true }); // no queenside right
  await D.humanMove('e1', 'c1', { via: 'click', expectIllegal: true }).catch(() => undefined);
  await D.reconcile('after illegal castle');
  await D.humanMove('e1', 'g1', { via: 'drag' });
  await D.humanMove('e8', 'c8', { via: 'click' });
  await done('castle-illegal-then-legal');

  // --- en passant (Full animations: the capture cinematic)
  await setAnim('Full');
  await D.startFen('4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1', 'en-passant');
  await D.humanMove('e2', 'e4', { via: 'click' });
  await D.humanMove('d4', 'e3', { via: 'click' });
  const ep = await D.obs();
  if (ep.capsCount < 1) await rec.anomaly('en-passant-tray', 'en passant captured a pawn but the captured tray is empty', { severity: 'warn' });
  await done('en-passant');
  await setAnim('Quick');

  // --- promotions
  const R = 'rook', B = 'bishop', N = 'knight', Q = 'queen';
  await D.startFen('7k/P7/8/8/8/8/8/K7 w - - 0 1', 'promo-queen-cancel');
  await D.humanMove('a7', 'a8', { promo: Q, promoHook: async () => {
    // picker open: board clicks must be ignored; Escape cancels
    const c0 = (await D.obs()).plies;
    await D.tap(6, (await page.evaluate(() => innerHeight)) - 6); await sleep(200); // backdrop, away from the cards
    await D.tap(page.viewportSize().width - 6, 6); await sleep(300);
    const o = await D.obs();
    if (!o.promoOpen) await rec.anomaly('picker-closed-by-backdrop-click', 'clicking outside the cards closed the promotion picker', { severity: 'warn' });
    await rec.shot('promotion-picker.png');
    await D.hoverTips(['.promo .card[aria-label="Knight"]'], 'promotion');
    await page.keyboard.press('Escape'); await sleep(500);
    const o2 = await D.obs();
    rec.act('promotion-cancel', 'Escape', { ui: o2 });
    if (o2.promoOpen || o2.plies !== c0 || o2.state !== 'awaitInput') await rec.anomaly('promotion-cancel-broken', `after Escape: promoOpen=${o2.promoOpen} plies ${c0}->${o2.plies} state ${o2.state}`, { severity: 'error', data: o2 });
    // re-do the move: a7 should be re-selected or need selecting again
    if (!(await D.liftedCount())) { await D.clickSq('a7', 'reselect'); await sleep(250); } // after a cancel the piece stays selected
    await D.clickSq('a8', 'promote-again');
    await D.waitFor((x) => x.promoOpen, 2500);
  } });
  await done('promo-queen-cancel');

  await D.startFen('1r5k/P7/8/8/8/8/6p1/K7 w - - 0 1', 'promo-knight-capture');
  await D.humanMove('a7', 'b8', { promo: N, via: 'click' });
  await done('promo-knight-capture');
  await D.startFen('7k/P7/8/8/8/8/8/K7 w - - 0 1', 'promo-rook');
  await D.humanMove('a7', 'a8', { promo: R, via: 'drag' });
  await done('promo-rook');
  await D.startFen('8/P5k1/8/8/8/8/6p1/K7 w - - 0 1', 'promo-bishop');
  await D.humanMove('a7', 'a8', { promo: B, via: 'click' });
  await done('promo-bishop');
  await D.startFen('4k3/8/8/8/8/8/p5K1/8 b - - 0 1', 'promo-black-queen');
  await D.humanMove('a2', 'a1', { promo: Q, via: 'click' });
  await done('promo-black-queen');

  // --- stalemate, insufficient material
  await D.startFen('7k/8/4Q3/8/8/8/8/K7 w - - 0 1', 'stalemate');
  await D.humanMove('e6', 'f7', { via: 'click' });
  await done('stalemate', { expectTitle: 'Stalemate' });
  // undo out of the stalemate through the HUD, make sure the game reopens
  {
    const expFen = D.fenBefore(1);
    await D.uiClick('.ibtn[aria-label="Undo"]', 'hud:undo-after-stalemate');
    await sleep(1000);
    const a = await D.obs();
    if (a.fen !== expFen || a.result) await rec.anomaly('undo-after-stalemate', `state ${a.state} result ${a.result}`, { severity: 'error', data: a });
    await D.resync('undo after stalemate');
    await D.syncCheck('after undo-from-stalemate');
  }
  await D.startFen('k7/8/8/8/8/8/1p6/K1B5 w - - 0 1', 'insufficient');
  await D.humanMove('a1', 'b2', { via: 'click' });
  await done('insufficient', { expectTitle: 'Draw' });

  // --- careful finishes by mate (mate-in-one)
  rec.use('careful');
  await D.startFen('6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1', 'careful-mate-in-1');
  const mate = bestMove(D.ctx.mirror.fen(), { depth: 2, rng });
  await D.humanMove(mate.from, mate.to, { via: 'click' });
  await done('careful-mate-in-1', { expectTitle: 'Checkmate', dismiss: 'Main Menu' });

  // --- chaos: resign / rematch / main menu mid-game / Continue
  rec.use('chaos');
  await D.startHotseat('Turn the Board');
  await D.humanMove('e2', 'e4', { via: 'click' });
  await D.humanMove('e7', 'e5', { via: 'click' });
  if (await togglePause('resign-flow')) {
    await D.uiClick('.pause .btn:has-text("Resign")', 'pause:resign-arm');
    await D.uiClick('.pause .btn:has-text("Confirm resign")', 'pause:resign-confirm');
  }
  await gameOverCheck('resign-flow', { expectTitle: 'Resignation', dismiss: 'Rematch' });
  const rm = await D.waitFor((x) => x.state === 'awaitInput' && x.plies === 0 && !x.result, 25000);
  if (!rm) await rec.anomaly('rematch-failed', 'Rematch after resignation did not start a fresh game', { severity: 'error' });
  D.newCtx(null, 'rematch');
  await D.syncCheck('after rematch');
  await D.humanMove('d2', 'd4', { via: 'drag' });
  // main menu then Continue
  await D.ensureMainMenu();
  await D.audit('menu-with-game');
  await D.hoverTips(['.menu .btn:has-text("Continue")', '.menu .btn:has-text("Two Players")', '.menu .btn:has-text("Settings")'], 'menu');
  await rec.shot('menu-mid-game.png');
  await D.uiClick('.menu .btn:has-text("Continue")', 'menu:continue');
  await sleep(600);
  const c = await D.obs();
  if (c.state !== 'awaitInput' || c.plies !== 1) await rec.anomaly('continue-broke-game', `after Continue: state ${c.state} plies ${c.plies}`, { severity: 'error', data: c });
  await D.syncCheck('after continue');
  // menu Resign two-step button on the main menu (arm, let it expire)
  await D.ensureMainMenu();
  await D.uiClick('.menu .btn:has-text("Resign")', 'menu:resign-arm');
  await sleep(3400);
  const lbl = await page.locator('.menu .btn.danger .lbl').first().textContent().catch(() => '');
  if (/confirm/i.test(lbl ?? '')) await rec.anomaly('resign-arm-not-reset', 'main-menu Resign stayed armed after 3 s', { severity: 'warn' });
  // credits / how-to pages and back, keyboard-only navigation
  await D.uiClick('.menu .btn:has-text("Credits")', 'menu:credits');
  await sleep(300); await D.audit('credits'); await rec.shot('credits.png'); await page.keyboard.press('Escape'); await sleep(300);
  await D.uiClick('.menu .btn:has-text("How to Play")', 'menu:how-to');
  await sleep(1500); await D.audit('how-to'); await rec.shot('how-to.png');
  await D.closeAllScreens(); await sleep(500);
  if (!(await D.screens()).length) { /* learn closed back to nothing: the menu should be back */ }
  await D.ensureMainMenu();
  for (const k of ['ArrowDown', 'ArrowDown', 'Enter']) { await page.keyboard.press(k); await sleep(250); }
  rec.act('keyboard-menu-nav', 'Down Down Enter', { ui: await D.obs() });
  await D.audit('after-keyboard-nav');
  await D.closeAllScreens();
}

// ---------------------------------------------------------------------------------------------- PHASE: vs computer
async function aiMoveRound(n, who) {
  const s = await D.obs();
  if (s.state === 'aiThinking') await D.settle('ai reply');
}

async function careful_vsAi() {
  rec.use('careful');
  await D.startVsAi('Emberhold', 'Easy');
  await D.audit('vs-ai-start');
  const ctx = D.ctx;
  let sawThinking = false;
  for (let i = 1; i <= 12; i++) {
    const s = await D.obs();
    if (s.result) break;
    if (D.timeLeft() < 0) { rec.note('careful vs-ai cut short by the time budget'); break; }
    if (s.state === 'aiThinking') { await D.settle('ai reply'); }
    const mv = bestMove(D.ctx.mirror.fen(), { depth: 3, rng });
    if (!mv) break;
    await D.humanMove(mv.from, mv.to, { via: 'click', promo: mv.promotion ? 'queen' : null, during: async () => {
      for (let k = 0; k < 40 && !sawThinking; k++) { const o = await D.obs(); if (o.state === 'aiThinking') { sawThinking = true; if (o.hudVisible && !/Thinking/.test(o.turnText ?? '')) await rec.anomaly('hud-thinking-missing', `AI thinking but HUD says "${o.turnText}"`, { severity: 'warn' }); break; } if (o.state === 'awaitInput') break; await sleep(60); }
    } });
    const r = await D.settle('ai reply', {});
    if (r.s.plies !== D.ctx.mirror.history().length) {
      const last = await page.evaluate(() => { const m = window.__bc.controller.snapshot().moves; return m[m.length - 1]; });
      const mm = D.ctx.mirror;
      try { mm.move({ from: last.from, to: last.to, promotion: last.promotion ? { queen: 'q', rook: 'r', bishop: 'b', knight: 'n' }[last.promotion] : undefined }); }
      catch { await rec.anomaly('ai-illegal-move', `AI played ${last.from}${last.to} which chess.js says is illegal at ${mm.fen()}`, { severity: 'error' }); await D.resync('ai'); }
      rec.act('ai-reply', `${last.from}${last.to}`, { san: last.san, observed_fen: r.s.fen, expected_fen: mm.fen(), match: mm.fen() === r.s.fen });
      if (mm.fen() !== r.s.fen) await rec.anomaly('fen-mismatch', `after AI move ${last.san}: mirror ${mm.fen()} vs ${r.s.fen}`, { severity: 'error' });
      await D.syncCheck('after ai reply');
    }
    if (i === 3) { // Quick animations from the pause menu
      if (await togglePause('careful vs-ai')) {
        if (await D.openSettings('pause')) { await D.setRow('Gameplay', 'Animations', 'Quick', { path: 'captureMode', value: 'quick' }); await D.closeSettings(); }
        await D.closeAllScreens();
      }
    }
    if (i === 5) { // undo a full exchange
      const before = await D.obs();
      if (before.canUndo) {
        await D.uiClick('.ibtn[aria-label="Undo"]', 'hud:undo');
        await sleep(1000);
        const a = await D.obs();
        rec.act('undo', 'vs-ai', { plies_before: before.plies, plies_after: a.plies, ui: a });
        if (a.plies !== before.plies - 2) await rec.anomaly('undo-vs-ai-count', `vs-AI undo went ${before.plies} -> ${a.plies} (expected -2)`, { severity: 'warn' });
        await D.resync('undo vs-ai');
        await D.syncCheck('after vs-ai undo');
      }
    }
  }
  const s = await D.obs();
  rec.game({ label: 'careful vs-ai easy', plies: s.plies, result: s.result, fen: s.fen });
  if (!s.result && (await togglePause('vs-ai end'))) {
    await D.uiClick('.pause .btn:has-text("Resign")', 'pause:resign-arm');
    await D.uiClick('.pause .btn:has-text("Confirm resign")', 'pause:resign-confirm');
  }
  await gameOverCheck('careful-vs-ai', { dismiss: 'Main Menu' });
}

async function chaos_vsAi() {
  rec.use('chaos');
  await D.startVsAi('Rime Host', 'Easy'); // Chaos plays Black: the AI opens
  await D.audit('vs-ai-black');
  // clicks while the AI is thinking / moving
  for (let k = 0; k < 6; k++) { const sq = ['e2', 'e7', 'd1', 'a8', 'h2', 'e4'][k]; const o = await D.obs(); if (o.state === 'aiThinking' || o.busy) { await D.clickSq(sq, 'during-ai-turn'); await sleep(100); } }
  rec.act('clicks-during-ai-turn', 'spam');
  if (await D.waitFor((o) => o.state === 'aiThinking', 600)) {
    if (await togglePause('during ai')) { await sleep(900); await D.uiClick('.pause .btn:has-text("Resume")', 'pause:resume'); }
  }
  await D.settle('ai first move');
  await D.resync('ai first move');
  if (!(await D.reconcile('ai first move'))) await rec.shot('ai-first-move.png');
  await D.syncCheck('after AI opening');
  const view = ['desktop', 'portrait', 'landscape', 'desktop'];
  for (let i = 1; i <= 8; i++) {
    let s = await D.obs();
    if (s.result) break;
    if (D.timeLeft() < 0) { rec.note('chaos vs-ai cut short by the time budget'); break; }
    if (s.state === 'aiThinking') s = (await D.settle('ai reply')).s;
    await D.resync('before chaos move');
    const mv = chaosMove(D.ctx.mirror.fen(), rng);
    if (!mv) break;
    const promo = mv.promotion ? 'queen' : null;
    if (i === 2) { await D.humanMove(mv.from, mv.to, { via: 'drag', promo }); }
    else if (i === 3) { // undo while the AI is thinking
      await D.humanMove(mv.from, mv.to, { via: 'click', promo, during: async () => {
        const o = await D.waitFor((x) => x.state === 'aiThinking', 800);
        if (o) {
          await page.keyboard.press('u'); await sleep(1500);
          const a = await D.obs();
          rec.act('undo-during-ai-thinking', 'U', { ui: a });
          await D.resync('undo during thinking');
          if (a.state !== 'awaitInput' && a.state !== 'aiThinking') await rec.anomaly('undo-during-thinking-stuck', `state ${a.state}`, { severity: 'error', data: a });
        }
      } });
    }
    else if (i === 5) { // viewport hop while the AI thinks
      await D.humanMove(mv.from, mv.to, { via: 'click', promo, during: async () => { for (const name of view) { await resize(name); await D.audit('ai-resize-' + name); } } });
    }
    else if (i === 6) { // main menu while the AI is thinking, then Continue
      await D.humanMove(mv.from, mv.to, { via: 'click', promo, during: async () => {
        await D.uiClick('.ibtn[aria-label="Pause menu"]', 'hud:pause', { force: true });
        await D.uiClick('.pause .btn:has-text("Main Menu")', 'pause:main-menu');
        await sleep(2500);
        await D.uiClick('.menu .btn:has-text("Continue")', 'menu:continue');
        await sleep(300);
      } });
    }
    else await D.humanMove(mv.from, mv.to, { via: 'click', promo });
    s = (await D.settle('ai reply after chaos')).s;
    await D.resync('after ai reply');
    await D.reconcile('vs-ai loop');
    await D.syncCheck('vs-ai loop');
  }
  const s = await D.obs();
  rec.game({ label: 'chaos vs-ai easy (black)', plies: s.plies, result: s.result, fen: s.fen });
  if (!s.result && (await togglePause('chaos vs-ai end'))) {
    await D.uiClick('.pause .btn:has-text("Resign")', 'pause:resign-arm');
    await D.uiClick('.pause .btn:has-text("Confirm resign")', 'pause:resign-confirm');
  }
  await gameOverCheck('chaos-vs-ai', { dismiss: 'Rematch' });
  const r = await D.waitFor((x) => (x.state === 'awaitInput' || x.state === 'aiThinking') && x.plies <= 1, 30000);
  if (!r) await rec.anomaly('rematch-failed', 'vs-AI rematch did not start', { severity: 'error' });
  await D.settle('rematch ai opening');
}

// ---------------------------------------------------------------------------------------------- PHASE: phone (touch)
async function phonePhase() {
  rec.use('chaos');
  D.touch = true; D.coarse = true;
  await newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 }, 'phone portrait (touch)');
  await D.audit('phone-menu');
  await rec.shot('phone-menu.png');
  await D.startHotseat('Hold the Board');
  await rec.shot('phone-game-portrait.png');
  await D.audit('phone-game-portrait');
  const tapMoves = [['e2', 'e4'], ['e7', 'e5'], ['g1', 'f3'], ['b8', 'c6'], ['f1', 'c4'], ['g8', 'f6']];
  for (const [i, [f, t]] of tapMoves.entries()) {
    await D.humanMove(f, t, { via: i === 3 ? 'drag' : 'click' });
    if (i === 2) { await resize('landscape'); await D.audit('phone-game-landscape'); await rec.shot('phone-game-landscape.png'); }
  }
  // long-press tooltip on a HUD button must show and must not trigger the button
  await resize('portrait');
  const before = await D.obs();
  const b = await page.locator('.ibtn[aria-label="Pause menu"]').boundingBox();
  if (b) {
    const cdp = await page.context().newCDPSession(page);
    const pt = [{ x: b.x + b.width / 2, y: b.y + b.height / 2, id: 7 }];
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: pt });
    await sleep(750);
    const tip = await page.evaluate(() => { const t = document.getElementById('ui-tip'); return t && !t.hidden ? t.textContent.slice(0, 60) : null; });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await sleep(400);
    const after = await D.obs();
    rec.act('long-press', 'pause button', { tooltip: tip, screensAfter: after.screens });
    if (!tip) await rec.anomaly('long-press-no-tooltip', 'long-press on HUD Pause button shows no tooltip', { severity: 'warn' });
    if (after.screens.includes('pause')) { await rec.anomaly('long-press-activated-button', 'long-press opened the pause menu instead of just showing the tip', { severity: 'warn' }); await D.closeAllScreens(); }
    await cdp.detach().catch(() => undefined);
  }
  // phone menus
  await D.uiClick('.ibtn[aria-label="Settings"]', 'phone:settings');
  await sleep(400); await D.audit('phone-settings'); await rec.shot('phone-settings.png');
  await D.uiClick('.settings .cats .btn:has-text("Video")', 'phone:settings-video'); await sleep(300); await D.audit('phone-settings-video'); await rec.shot('phone-settings-video.png');
  await resize('landscape'); await sleep(300); await D.audit('phone-settings-landscape'); await rec.shot('phone-settings-landscape.png');
  await resize('portrait');
  await D.closeSettings();
  await D.uiClick('.ibtn[aria-label="Pause menu"]', 'phone:pause'); await sleep(300); await D.audit('phone-pause'); await D.closeAllScreens();
  // end: a quick stalemate on the phone for the game-over layout
  await D.startFen('7k/8/4Q3/8/8/8/8/K7 w - - 0 1', 'phone-stalemate');
  await D.humanMove('e6', 'f7', { via: 'click' });
  await gameOverCheck('phone-stalemate', { expectTitle: 'Stalemate', dismiss: 'Main Menu' });
  await resize('landscape');
  await D.audit('phone-menu-landscape');
  await rec.shot('phone-menu-landscape.png');
  const s = await D.obs();
  rec.game({ label: 'phone touch hotseat', plies: s.plies, result: s.result });
}

// ---------------------------------------------------------------------------------------------- main
const t0 = Date.now();
for (const sig of ['SIGTERM', 'SIGINT']) process.on(sig, async () => { // clean up only what we started
  try { rec.summary({ aborted: sig }); await browser?.close(); await server?.close(); } catch { /* ignore */ }
  process.exit(130);
});
try {
  server = await createServer({ root: repo, server: { port: PORT, strictPort: false, host: '127.0.0.1', hmr: false, watch: null }, logLevel: 'warn' });
  await server.listen();
  const realPort = server.config.server.port;
  if (realPort !== PORT) log('note: port', PORT, 'busy, using', realPort);
  if (realPort === 5173) throw new Error('refusing to use 5173');
  log('dev server on', realPort, '| seed', SEED, '| budget', BUDGET_MIN, 'min');
  for (let attempt = 1; !browser; attempt++) {
    try { browser = await chromium.launch({ executablePath: BRAVE, headless: true, timeout: 180000 }); }
    catch (e) { if (attempt >= 3) throw e; log('launch failed, retry', e.message.split('\n')[0]); }
  }
  D.touch = false;
  await newPage({ viewport: { width: 1280, height: 720 }, hasTouch: false }, 'desktop');
  rec.use('careful', 'boot');
  await D.audit('main-menu');
  await D.hoverTips(['.menu .btn:has-text("Two Players")', '.menu .btn:has-text("Play vs Computer")', '.menu .btn:has-text("Settings")'], 'menu');
  await rec.shot('main-menu.png');

  await phase('duel', 'careful', duelPhase);
  await phase('scenarios', 'chaos', scenarioPhase);
  await phase('careful-vs-ai', 'careful', careful_vsAi);
  await phase('chaos-vs-ai', 'chaos', chaos_vsAi);
  await phase('phone', 'chaos', phonePhase);
} catch (e) {
  console.error('[duel] FATAL', e);
  rec.note('fatal: ' + (e.stack || e.message));
  process.exitCode = 1;
} finally {
  const sum = rec.summary({ seed: SEED, phases: phasesRun, totalSeconds: +((Date.now() - t0) / 1000).toFixed(1) });
  const brief = Object.fromEntries(Object.entries(sum).map(([k, v]) => [k, { actions: v.actions, games: v.games.length, anomalies: Object.fromEntries(Object.entries(v.anomalies.byType).map(([t, a]) => [t, a.unique])), consoleErrors: v.console.error, consoleWarnings: v.console.warning, pageErrors: v.console.pageerror }]));
  console.log('\n[duel] SUMMARY', JSON.stringify({ phases: phasesRun, personas: brief }, null, 2));
  try { await context?.close(); } catch { /* ignore */ }
  try { await browser?.close(); } catch { /* ignore */ } // only the browser WE launched
  try { await server?.close(); } catch { /* ignore */ }
  const { writeFileSync } = await import('node:fs');
  writeFileSync(join(OUT, 'summary.json'), JSON.stringify({ seed: SEED, phases: phasesRun, personas: brief, totalSeconds: +((Date.now() - t0) / 1000).toFixed(1) }, null, 2));
  process.exit(process.exitCode ?? 0);
}
