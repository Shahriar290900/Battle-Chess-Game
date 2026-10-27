// Real-UI driver: clicks/taps/drags on screen coordinates, menus, settings, plus the per-action checks and latency math.
import { Chess } from 'chess.js';
import { loadavg } from 'node:os';
import { boardSync, busProbe, findPoint, observe, tooltipState, uiAudit } from './page.mjs';

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export class Stuck extends Error {}
const firstLine = (s) => String(s).split('\n')[0].slice(0, 200);
const ROLE_CODE = { queen: 'q', rook: 'r', bishop: 'b', knight: 'n' };

export function createDriver(rec, opts = {}) {
  const D = {
    page: null, touch: false, coarse: false,
    ctx: { mirror: new Chess(), startFen: new Chess().fen(), label: 'none' },
    deadline: Infinity,
    rng: opts.rng ?? Math.random,
  };
  const log = (...a) => console.log(`[duel ${rec.now()}s ${rec.cur}/${rec.phase}]`, ...a);
  D.log = log;
  const pg = () => D.page;
  D.timeLeft = () => D.deadline - Date.now();
  /** Scale a timeout by machine load (the dev box is often shared by many agents; software GL makes everything slow). */
  D.T = (ms) => Math.round(ms * Math.min(6, Math.max(1, loadavg()[0] / 15)));
  D.load = () => +loadavg()[0].toFixed(1);
  /** FEN before the last k plies of the current mirror (new Chess(fen) loses history, so replay from the start). */
  D.fenBefore = (k = 1) => {
    const hist = D.ctx.mirror.history({ verbose: true });
    const c = new Chess(D.ctx.startFen);
    for (const h of hist.slice(0, hist.length - k)) c.move({ from: h.from, to: h.to, promotion: h.promotion });
    return c.fen();
  };

  // ------------------------------------------------------------------ observation
  D.obs = () => pg().evaluate(observe);
  D.takeEvents = () => pg().evaluate(() => window.__pt.take());
  D.peekEvents = () => pg().evaluate(() => window.__pt.ev.slice());
  D.evCount = (name) => pg().evaluate((n) => window.__pt.cnt[n] || 0, name);
  D.probeBus = async () => { for (let i = 0; i < 20; i++) { if (await pg().evaluate(busProbe)) return; await sleep(250); } };

  D.waitFor = async (pred, timeout = 5000, poll = 80) => {
    const t0 = Date.now();
    for (;;) {
      const s = await D.obs();
      if (pred(s)) return s;
      if (Date.now() - t0 > timeout) return null;
      await sleep(poll);
    }
  };

  D.flushFps = async (label) => {
    try { const s = await pg().evaluate(() => window.__pt.fpsTake()); rec.fpsSample(label, s); return s; } catch { return null; }
  };

  // ------------------------------------------------------------------ mirror (chess.js shadow of the rules engine)
  D.newCtx = (fen, label) => {
    const mirror = fen ? new Chess(fen) : new Chess();
    D.ctx = { mirror, startFen: mirror.fen(), label, cn: 0, xn: 0, captures: 0 };
    return D.ctx;
  };
  /** Rebuild the mirror from the page's move list (after undo, AI replies, unexpected changes). */
  D.resync = async (why) => {
    const moves = await pg().evaluate(() => window.__bc.controller.snapshot().moves.map((m) => ({ from: m.from, to: m.to, promotion: m.promotion })));
    const m = new Chess(D.ctx.startFen);
    for (const mv of moves) {
      try { m.move({ from: mv.from, to: mv.to, promotion: mv.promotion ? ROLE_CODE[mv.promotion] : undefined }); }
      catch { await rec.anomaly('rules-illegal-in-history', `${why}: game history has a move chess.js rejects: ${JSON.stringify(mv)} at ply ${m.history().length}`, { severity: 'error' }); break; }
    }
    D.ctx.mirror = m;
    return m;
  };
  /** Mirror vs the game's observed FEN; resync from history if the ply counts differ. */
  D.reconcile = async (why, o) => {
    const s = o ?? (await D.obs());
    if (s.plies !== D.ctx.mirror.history().length) await D.resync(why);
    if (s.fen !== D.ctx.mirror.fen()) {
      await rec.anomaly('fen-mismatch', `${why}: observed ${s.fen} != expected ${D.ctx.mirror.fen()}`, { key: why + s.plies, severity: 'error', data: { observed: s.fen, expected: D.ctx.mirror.fen() } });
      return false;
    }
    return true;
  };

  // ------------------------------------------------------------------ checks
  D.audit = async (where) => {
    let list = [];
    try { list = await pg().evaluate(uiAudit, { coarse: D.coarse }); } catch (e) { rec.note(`audit failed at ${where}: ${firstLine(e.message)}`); return; }
    const vp = await pg().evaluate(() => `${innerWidth}x${innerHeight}`);
    for (const f of list) {
      await rec.anomaly(f.type, `${f.key} @${vp} [${f.layer}]: ${f.detail}`, { key: f.key, scope: `${vp}|${f.layer}`, severity: f.type === 'no-tooltip' || f.type === 'touch-target' ? 'info' : 'warn', data: { where, ...f } });
    }
  };

  D.integrity = async (where, s) => {
    s = s ?? (await D.obs());
    if (s.ghostModal) await rec.anomaly('invisible-modal-blocks-input', `${where}: ui.modalOpen but no visible screen (state ${s.state})`, { key: where, severity: 'error', data: s });
    if (s.deadScreen) await rec.anomaly('screen-visible-but-input-live', `${where}: a screen is visible (${s.screens.join(',')}) but ui.modalOpen is false`, { key: where, data: s });
    if (s.state === 'awaitInput' && s.mode) {
      const who = s.turn === 'w' ? 'Emberhold' : 'Rime Host';
      if (s.hudVisible && s.turnText && !s.turnText.includes(who)) await rec.anomaly('hud-turn-mismatch', `${where}: turn is ${s.turn} but HUD says "${s.turnText}"`, { key: s.turn + s.turnText, severity: 'error', data: s });
      if (s.hudVisible && s.check && s.turnText && !/Check/.test(s.turnText)) await rec.anomaly('hud-check-missing', `${where}: side to move is in check but HUD says "${s.turnText}"`, { key: where, data: s });
      if (s.hudVisible) {
        const left = D.ctx.mirror.board().flat().filter(Boolean).length;
        if (D.ctx.mirror.fen() === s.fen && s.capsCount !== 32 - left && D.ctx.startFen === new Chess().fen())
          await rec.anomaly('captured-tray-mismatch', `${where}: ${32 - left} pieces captured but tray shows ${s.capsCount}`, { key: where + s.plies, data: s });
        if (s.journalVisible && s.journalCount !== s.plies) await rec.anomaly('journal-mismatch', `${where}: ${s.plies} plies but journal lists ${s.journalCount}`, { key: where + s.plies, data: s });
      }
    }
    return s;
  };

  /** 3D board vs rules FEN. Retries once (transient tweens) before reporting. */
  D.syncCheck = async (where) => {
    let o = await D.obs();
    if (o.state !== 'awaitInput' && o.state !== 'gameOver') return true;
    await sleep(250);
    let bad = await pg().evaluate(boardSync, o.fen);
    if (bad.length) { await sleep(700); o = await D.obs(); bad = await pg().evaluate(boardSync, o.fen); }
    if (bad.length) {
      await rec.anomaly('board-desync', `${where}: ${bad.length} mismatch(es): ${bad.slice(0, 4).map((b) => `${b.kind}@${b.square} ${b.detail}`).join('; ')}`, { key: bad.map((b) => b.kind + b.square).join(','), severity: 'error', data: { fen: o.fen, bad } });
      return false;
    }
    return true;
  };

  // ------------------------------------------------------------------ waits
  D.settle = async (label, o = {}) => {
    const t0 = Date.now();
    let flagged = false, step = 0;
    for (;;) {
      const s = await D.obs();
      if (s.state === 'awaitInput' || s.state === 'gameOver' || s.state === 'menu' || (o.allowPromo && s.state === 'promotion')) return { s, ms: Date.now() - t0 };
      const el = Date.now() - t0;
      if (el > 8000 && !flagged) { flagged = true; await rec.anomaly('stuck-sequence', `${label}: still '${s.state}' after 8 s (anim=${s.anim}, host load avg ${D.load()})`, { key: label.replace(/\d+/g, '#') + s.state, data: s }); }
      if (el > 14000 && step < 1) { step = 1; rec.act('recovery', 'space-skip', { label }); await pg().keyboard.press('Space'); }
      if (el > 22000 && step < 2) { step = 2; rec.act('recovery', 'skip-button', { label }); await pg().click('.ibtn[aria-label="Skip animation"]', { timeout: 1500 }).catch(() => undefined); }
      if (el > 32000 && step < 3) { step = 3; rec.act('recovery', 'escape', { label }); await pg().keyboard.press('Escape'); }
      if (el > 50000) { await rec.anomaly('stuck-sequence-fatal', `${label}: stuck in '${s.state}' for 50 s`, { severity: 'error', data: s }); throw new Stuck(`stuck in ${s.state} at ${label}`); }
      await sleep(100);
    }
  };

  D.cameraStable = async () => {
    let prev = null;
    for (let i = 0; i < 40; i++) {
      let p;
      try { p = await pg().evaluate(() => window.__bc.squareToScreen('e4')); } catch { return; }
      if (prev && Math.hypot(p.x - prev.x, p.y - prev.y) < 4) return;
      prev = p;
      await sleep(220);
    }
  };

  // ------------------------------------------------------------------ pointer input on the board
  D.point = (sq) => pg().evaluate(findPoint, sq);
  D.tap = async (x, y) => {
    if (D.touch) await pg().touchscreen.tap(x, y);
    else await pg().mouse.click(x, y);
  };
  D.clickSq = async (sq, why = '') => {
    const p = await D.point(sq);
    if (!p.ok && why !== 'destination' && !why.startsWith('destination')) await rec.anomaly('square-unreachable', `${sq}: no point on screen resolves to this square (${JSON.stringify(p.why)})`, { key: sq + JSON.stringify(p.why && p.why.top), data: p.why });
    await D.tap(p.x, p.y);
    rec.act(D.touch ? 'tap-square' : 'click-square', sq, { x: Math.round(p.x), y: Math.round(p.y), reachable: p.ok, why });
    return p;
  };
  D.cdpTouchDrag = async (pts) => {
    const cdp = await pg().context().newCDPSession(pg());
    const tp = (p) => [{ x: p.x, y: p.y, id: 1 }];
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: tp(pts[0]) });
    for (const p of pts.slice(1)) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: tp(p) }); await sleep(16); }
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await cdp.detach().catch(() => undefined);
  };
  /** Drag from a square to a screen point (default: the centre of `to`). */
  D.dragSq = async (from, to, o = {}) => {
    const a = await D.point(from);
    const b = o.toPoint ?? (await D.point(to)).base;
    const steps = o.steps ?? 14;
    if (D.touch) {
      const pts = [{ x: a.x, y: a.y }];
      for (let i = 1; i <= steps; i++) pts.push({ x: a.x + ((b.x - a.x) * i) / steps, y: a.y + ((b.y - a.y) * i) / steps });
      await D.cdpTouchDrag(pts);
    } else {
      await pg().mouse.move(a.x, a.y);
      await pg().mouse.down();
      await pg().mouse.move(a.x + 12, a.y - 6, { steps: 3 });
      await pg().mouse.move(b.x, b.y, { steps });
      await sleep(90);
      await pg().mouse.up();
    }
    rec.act(D.touch ? 'touch-drag' : 'drag-drop', `${from}->${to ?? 'point'}`, { from: [Math.round(a.x), Math.round(a.y)], to: [Math.round(b.x), Math.round(b.y)] });
  };
  /** A canvas point that is neither a board square nor covered by UI. */
  D.emptyPoint = () => pg().evaluate(() => {
    const B = window.__bc;
    const vw = innerWidth, vh = innerHeight;
    for (const [fx, fy] of [[0.5, 0.97], [0.97, 0.5], [0.03, 0.5], [0.5, 0.03], [0.97, 0.9], [0.03, 0.9], [0.9, 0.5], [0.5, 0.92]]) {
      const x = vw * fx, y = vh * fy;
      const e = document.elementFromPoint(x, y);
      const r = B.pick(x, y);
      if (e && e.tagName === 'CANVAS' && !r.square && !r.actor) return { x, y };
    }
    return { x: vw * 0.5, y: vh * 0.02 };
  });
  D.liftedCount = () => pg().evaluate(() => window.__bc.board.allActors().filter((a) => a.root.position.y > 0.04).length);

  // ------------------------------------------------------------------ UI clicks, settings, navigation
  D.uiClick = async (sel, label = sel, o = {}) => {
    const t = Date.now();
    try {
      if (D.touch) await pg().locator(sel).first().tap({ timeout: o.timeout ?? 20000 });
      else await pg().click(sel, { timeout: o.timeout ?? 20000, force: !!o.force });
      rec.act(D.touch ? 'ui-tap' : 'ui-click', label, { sel, ms: Date.now() - t });
      return true;
    } catch (e) {
      await rec.anomaly('ui-click-failed', `${label} (${sel}): ${firstLine(e.message)}`, { key: sel, severity: 'error' });
      return false;
    }
  };
  D.frames2 = () => pg().evaluate(() => new Promise((r) => { const t = performance.now(); requestAnimationFrame(() => requestAnimationFrame(() => r(performance.now() - t))); }));
  D.getSetting = (path) => pg().evaluate((p) => p.split('.').reduce((o, k) => (o == null ? o : o[k]), window.__bc.settings.get()), path);

  D.openSettings = async (from = 'hud') => {
    const sel = from === 'hud' ? '.ibtn[aria-label="Settings"]' : from === 'pause' ? '.pause .btn:has-text("Settings")' : '.menu .btn:has-text("Settings")';
    if (!(await D.uiClick(sel, `open-settings(${from})`))) return false;
    const ok = await pg().waitForSelector('.settings:not([hidden])', { timeout: D.T(5000) }).then(() => true).catch(() => false);
    if (!ok) { await rec.anomaly('settings-not-opening', `settings did not open from ${from}`, { severity: 'error' }); return false; }
    await sleep(250);
    return true;
  };
  D.closeSettings = async () => {
    if (!(await pg().click('.settings .back-cat', { timeout: 1500 }).then(() => true).catch(() => false))) await pg().keyboard.press('Escape');
    const ok = await pg().waitForSelector('.settings', { state: 'hidden', timeout: D.T(4000) }).then(() => true).catch(() => false);
    if (!ok) await rec.anomaly('settings-not-closing', 'Settings screen stayed open after Back/Escape', { severity: 'error' });
    await sleep(150);
  };
  /** Step an option row to the wanted text by clicking its value (cycles). Verifies the setting afterwards. */
  D.setRow = async (cat, label, want, verify) => {
    await D.uiClick(`.settings .cats .btn:has-text("${cat}")`, `settings-tab:${cat}`);
    await sleep(120);
    const row = `.row[aria-label="${label}"]`;
    for (let i = 0; i < 8; i++) {
      const txt = (await pg().textContent(`${row} .val`, { timeout: 2000 }).catch(() => null))?.trim();
      if (txt == null) { await rec.anomaly('settings-row-missing', `${cat} > ${label} not found`, { key: label, severity: 'error' }); return false; }
      if (txt.toLowerCase() === String(want).toLowerCase()) break;
      const t0 = Date.now();
      await D.uiClick(`${row} .val`, `${label}: cycle`);
      rec.lat('setting-apply-2frames', (Date.now() - t0) + (await D.frames2()));
    }
    if (verify) {
      const got = await D.getSetting(verify.path);
      if (JSON.stringify(got) !== JSON.stringify(verify.value)) await rec.anomaly('setting-not-applied', `${label}=${want}: settings.${verify.path} is ${JSON.stringify(got)} (wanted ${JSON.stringify(verify.value)})`, { key: label + want, severity: 'error' });
    }
    return true;
  };
  D.setRange = async (cat, label, end /* 'maximum' | 'minimum' */, verify) => {
    await D.uiClick(`.settings .cats .btn:has-text("${cat}")`, `settings-tab:${cat}`);
    await sleep(120);
    await D.uiClick(`.row[aria-label="${label}"] .arr[aria-label$="${end}"]`, `${label}: ${end}`);
    await sleep(120);
    if (verify) {
      const got = await D.getSetting(verify.path);
      if (verify.min != null ? got < verify.min : Math.abs(got - verify.value) > 0.051) await rec.anomaly('setting-not-applied', `${label} ${end}: settings.${verify.path} is ${got} (wanted ${verify.min != null ? '>= ' + verify.min : verify.value})`, { key: label + end, severity: 'error' });
    }
  };
  D.screens = async () => (await D.obs()).screens.filter((c) => c !== 'loading');
  D.closeAllScreens = async () => {
    for (let i = 0; i < 6; i++) {
      if (!(await D.screens()).length) return true;
      await pg().keyboard.press('Escape');
      await sleep(280);
    }
    return !(await D.screens()).length;
  };
  D.ensureMainMenu = async () => {
    for (let i = 0; i < 8; i++) {
      const o = await D.obs();
      const s = o.screens.filter((c) => c !== 'loading');
      if (s.includes('menu')) return true;
      if (o.loadingVisible) { await sleep(500); continue; }
      if (s.includes('over')) await D.uiClick('.over .btn:has-text("Main Menu")', 'gameover:main-menu');
      else if (s.includes('pause')) await D.uiClick('.pause .btn:has-text("Main Menu")', 'pause:main-menu');
      else if (s.length) await pg().keyboard.press('Escape');
      else if (o.mode) await D.uiClick('.ibtn[aria-label="Pause menu"]', 'hud:pause');
      await sleep(400);
    }
    await rec.anomaly('cannot-reach-main-menu', 'could not return to the main menu', { severity: 'error' });
    return false;
  };
  /** Wait for the loading veil to leave and the controller to park in a game. */
  D.waitInGame = async (label, timeout = 90000) => {
    const s = await D.waitFor((o) => !o.loadingVisible && (o.state === 'awaitInput' || o.state === 'aiThinking'), timeout, 150);
    if (!s) { await rec.anomaly('game-not-starting', `${label}: game did not reach awaitInput/aiThinking within ${timeout / 1000}s`, { severity: 'error' }); throw new Stuck('game not starting: ' + label); }
    return s;
  };
  D.startHotseat = async (cardText = 'Turn the Board') => {
    if (!(await D.ensureMainMenu())) throw new Stuck('no menu');
    await D.uiClick('.menu .btn:has-text("Two Players")', 'menu:two-players');
    await pg().waitForSelector('.flow:not([hidden]) .card', { timeout: 4000 }).catch(() => undefined);
    await sleep(300);
    await D.audit('flow-table');
    await D.uiClick(`.flow .card:has-text("${cardText}")`, `flow:${cardText}`);
    const t0 = Date.now();
    await D.waitInGame('hotseat start');
    rec.lat('game-start-to-ready', Date.now() - t0);
    D.newCtx(null, 'hotseat');
    await sleep(600);
  };
  D.startVsAi = async (faction, level) => {
    if (!(await D.ensureMainMenu())) throw new Stuck('no menu');
    await D.uiClick('.menu .btn:has-text("Play vs Computer")', 'menu:vs-computer');
    await pg().waitForSelector(`.flow .card:has-text("${faction}")`, { timeout: 4000 }).catch(() => undefined);
    await sleep(300);
    await D.audit('flow-allegiance');
    await D.uiClick(`.flow .card:has-text("${faction}")`, `flow:${faction}`);
    await pg().waitForSelector(`.flow .card:has-text("${level}")`, { timeout: 4000 }).catch(() => undefined);
    await sleep(250);
    await D.audit('flow-foe');
    await D.uiClick(`.flow .card:has-text("${level}")`, `flow:${level}`);
    const t0 = Date.now();
    await D.waitInGame('vs-ai start');
    rec.lat('game-start-to-ready', Date.now() - t0);
    D.newCtx(null, `vs-ai ${faction} ${level}`);
    await sleep(600);
  };
  /** Start a scenario position. SETUP ONLY goes through the debug hook (no UI exists for custom FENs); every move is real UI input. */
  D.startFen = async (fen, label, { kind = 'hotseat', side = 'w' } = {}) => {
    await D.closeAllScreens();
    await pg().evaluate((a) => window.__bc.controller.newGame({ kind: a.kind, playerSide: a.side, aiLevel: 'easy', fen: a.fen }), { kind, side, fen });
    rec.act('scenario-setup', label, { fen, note: 'controller.newGame(fen) via __bc: setup only' });
    D.newCtx(fen, label);
    await D.waitInGame('scenario ' + label, 30000);
    await sleep(400);
    await D.cameraStable();
  };

  // ------------------------------------------------------------------ latency math from probe events
  function analyse(evs, expectCapture) {
    const out = {};
    const pds = evs.filter((e) => e.n === 'pd');
    const lastPdBefore = (t) => { let r = null; for (const p of pds) if (p.t <= t + 1) r = p; return r; };
    const sel = evs.find((e) => e.n === 'ui:select');
    if (sel) { const pd = lastPdBefore(sel.now ?? sel.t); if (pd) { out.select = sel.t - pd.t; const fr = evs.find((e) => e.n === 'frame-after-select' && e.t >= sel.t); if (fr) out.selectVisual = fr.t - pd.t; } }
    const res = evs.find((e) => e.n === 'move:resolved');
    if (res) {
      const pd = lastPdBefore(res.t);
      if (pd) {
        out.moveAccept = res.t - pd.t;
        const start = evs.find((e) => ['move:step', 'capture:begin', 'attack:whoosh', 'castle', 'promotion'].includes(e.n) && e.t >= res.t);
        if (start) out.moveStart = start.t - pd.t;
        const fr = evs.find((e) => e.n === 'frame-after-resolved' && e.t >= res.t);
        if (fr) out.moveFirstFrame = fr.t - pd.t;
      }
      const done = evs.find((e) => e.n === 'state' && (e.s === 'awaitInput' || e.s === 'gameOver') && e.t >= res.t);
      if (done) out.sequence = done.t - res.t;
    }
    out.captureEvents = evs.filter((e) => e.n === 'capture:begin').length;
    return out;
  }
  D.recordLatency = (evs, tag = '') => {
    const a = analyse(evs);
    if (a.select != null) rec.lat('select' + tag, a.select);
    if (a.selectVisual != null) rec.lat('select-visual' + tag, a.selectVisual);
    if (a.moveAccept != null) rec.lat('move-accept' + tag, a.moveAccept);
    if (a.moveStart != null) rec.lat('move-start' + tag, a.moveStart);
    if (a.moveFirstFrame != null) rec.lat('move-first-frame' + tag, a.moveFirstFrame);
    if (a.sequence != null) rec.lat(a.captureEvents ? 'sequence-capture' + tag : 'sequence-quiet' + tag, a.sequence);
    return a;
  };

  // ------------------------------------------------------------------ the human move
  /**
   * Make a move through the real UI. via: 'click' (click-click) | 'drag' | 'touch' semantic is chosen by D.touch.
   * Returns { ok, accepted }. Verifies selection feedback, acceptance, FEN, 3D sync and layout.
   */
  D.humanMove = async (from, to, o = {}) => {
    const { via = 'click', promo = null, during = null, expectIllegal = false, keepCamera = false } = o;
    const m = D.ctx.mirror;
    const cand = m.moves({ verbose: true }).find((x) => x.from === from && x.to === to && (!promo || x.promotion === ROLE_CODE[promo]));
    let expFen = null, isCapture = false, san = null;
    if (cand) { const t = new Chess(m.fen()); const r = t.move({ from, to, promotion: promo ? ROLE_CODE[promo] : cand.promotion }); expFen = t.fen(); isCapture = !!r.captured; san = r.san; }
    if (!cand && !expectIllegal) await rec.anomaly('harness-illegal-move', `harness tried ${from}${to} which chess.js says is illegal in ${m.fen()}`, { severity: 'error' });
    let pre = await D.obs();
    if (pre.plies !== m.history().length) { await D.resync('before move'); pre = await D.obs(); }
    if (pre.screens.filter((c) => c !== 'loading').length) {
      await rec.anomaly('unexpected-screen-open', `before ${from}${to}: screen(s) still open: ${pre.screens.join(',')}`, { key: pre.screens.join(','), data: pre });
      await D.closeAllScreens();
    }
    if (!keepCamera) await D.cameraStable();
    await D.takeEvents();
    const sel0 = await D.evCount('ui:select');
    const t0 = Date.now();
    if (via === 'drag') {
      await D.dragSq(from, to);
    } else {
      await D.clickSq(from, 'select');
      let got = null;
      for (let i = 0; i < 15; i++) { if ((await D.evCount('ui:select')) > sel0) { got = true; break; } await sleep(100); }
      if (!got && !expectIllegal) {
        await rec.anomaly('no-select-feedback', `click on ${from} (own piece, ${pre.turn} to move) produced no selection`, { key: from + pre.turn, severity: 'error' });
        await D.clickSq(from, 'select-retry');
        await sleep(300);
      } else if (got) {
        const ls = await pg().evaluate(() => { const e = window.__pt.ev.filter((x) => x.n === 'ui:select'); return e.length ? e[e.length - 1].sq : null; });
        if (ls && ls !== from) await rec.anomaly('wrong-piece-selected', `clicked ${from} but ${ls} got selected (neighbouring piece body won the click)`, { key: from + '>' + ls, data: { from, got: ls } });
        await sleep(330);
        const lifted = await D.liftedCount();
        if (!lifted) await rec.anomaly('selected-piece-not-lifted', `${from} selected but no piece lifted`, { key: 'lift', data: { from } });
        if (o.afterSelect) await o.afterSelect();
      }
      await sleep(40 + Math.floor(D.rng() * 120));
      await D.clickSq(to, 'destination');
    }
    const handlePromotion = async () => {
      if (!(cand && cand.promotion)) return;
      const open = await D.waitFor((s) => s.promoOpen, D.T(4000));
      if (!open) {
        await rec.anomaly('promotion-picker-missing', `${from}${to}: promotion move did not open the picker`, { severity: 'error' });
      } else {
        await sleep(250);
        await D.audit('promotion-picker');
        if (o.promoHook) await o.promoHook();
        const role = promo ?? 'queen';
        const label = role[0].toUpperCase() + role.slice(1);
        await D.uiClick(`.promo .card[aria-label="${label}"]`, `promotion:${label}`);
      }
    };
    await handlePromotion();
    let accepted = await D.waitFor((s) => s.plies === pre.plies + 1 || s.plies !== pre.plies, expectIllegal ? D.T(1200) : D.T(6000));
    if (!accepted && via === 'drag' && cand) { // a failed drag is a finding; fall back to click-click so the game goes on
      await rec.anomaly(D.touch ? 'touch-drag-not-accepted' : 'drag-not-accepted', `dragging ${from} to ${to} (a legal move) did not play it`, { key: `${from}${to}${D.touch}`, severity: 'error', data: { pre, pointerEvents: (await D.peekEvents()).filter((e) => /^p|lost/.test(e.n) && e.n !== 'ui:select').slice(0, 14) } });
      const e0 = await D.emptyPoint(); await D.tap(e0.x, e0.y); await sleep(300);
      await D.clickSq(from, 'select(drag-fallback)'); await sleep(350);
      await D.clickSq(to, 'destination(drag-fallback)');
      await handlePromotion();
      accepted = await D.waitFor((s) => s.plies === pre.plies + 1 || s.plies !== pre.plies, D.T(6000));
    }
    const ms = Date.now() - t0;
    if (!accepted) {
      if (!expectIllegal) {
        await rec.anomaly('move-not-accepted', `${from}${to} was legal (${pre.turn} to move, state ${pre.state}) but the UI did not play it`, { key: `${from}${to}${via}`, severity: 'error', data: { pre, via } });
      }
      rec.act('move-rejected', `${from}${to}`, { via, expectIllegal, expected_fen: pre.fen, observed_fen: (await D.obs()).fen, ui: await D.obs() });
      const e = await D.emptyPoint();
      await D.tap(e.x, e.y); // deselect
      await sleep(250);
      return { ok: false, accepted: false };
    }
    if (expectIllegal) await rec.anomaly('illegal-move-accepted', `${from}${to} should be illegal but the game played it`, { severity: 'error' });
    if (cand) D.ctx.mirror.move({ from, to, promotion: promo ? ROLE_CODE[promo] : cand.promotion });
    if (isCapture) D.ctx.captures++;
    if (during) await during();
    const { s, ms: seq } = await D.settle(`${from}${to}`);
    const evs = await D.takeEvents();
    const lat = D.recordLatency(evs);
    await sleep(120);
    const post = await D.obs();
    const atAccept = accepted && accepted.plies === pre.plies + 1 ? accepted.fen : post.fen;
    const same = expFen ? atAccept === expFen : true;
    rec.act('move', `${from}${to}${promo ? '=' + promo[0] : ''}`, { via, san, capture: isCapture, expected_fen: expFen, observed_fen: atAccept, observed_fen_after_settle: post.fen, match: same, ui: post, latency: lat, ms_total: ms, ms_sequence: seq });
    if (!same) await rec.anomaly('fen-mismatch', `${from}${to}: observed ${atAccept} != expected ${expFen}`, { key: `${from}${to}${post.plies}`, severity: 'error', data: { observed: atAccept, expected: expFen } });
    await D.syncCheck(`after ${san ?? from + to}`);
    await D.integrity(`after ${san ?? from + to}`, await D.obs());
    await D.audit('in-game');
    return { ok: true, accepted: true, san, capture: isCapture, state: s.state };
  };

  // ------------------------------------------------------------------ tooltips (real hover)
  D.hoverTips = async (selectors, tag) => {
    for (const sel of selectors) {
      const el = pg().locator(sel).first();
      if (!(await el.isVisible().catch(() => false))) continue;
      const hasTip = await el.evaluate((e) => !!e.closest('[data-tip]')).catch(() => false);
      await el.hover({ timeout: 2500 }).catch(() => undefined);
      await sleep(650);
      let t = await pg().evaluate(tooltipState);
      if (!t && hasTip) { await sleep(900); t = await pg().evaluate(tooltipState); } // slow machine: one retry
      if (hasTip && !t) await rec.anomaly('tooltip-not-shown', `${tag}: hovering ${sel} 650 ms shows no tooltip although it has data-tip`, { key: sel, scope: tag });
      else if (t && !t.inViewport) await rec.anomaly('tooltip-clipped', `${tag}: tooltip for ${sel} leaves the viewport ${JSON.stringify(t.rect)}`, { key: sel, scope: tag });
      rec.act('hover', sel, { tooltip: t ? t.text : null });
    }
    await pg().mouse.move(5, 5);
  };

  return D;
}
