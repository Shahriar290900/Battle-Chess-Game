// Functions that run INSIDE the page (serialised by Playwright, so each must be fully self-contained).

/** addInitScript: frame-time / long-task sampler + input timestamp recorder. Runs before the app boots. */
export function probeInit() {
  const P = (window.__pt = {
    ev: [], cnt: {}, lt: [], lastFrame: 0,
    frames: { idle: [], sequence: [], ai: [], other: [] },
    stalls: 0, busProbed: false,
  });
  const push = (o) => { if (P.ev.length < 4000) P.ev.push(o); P.cnt[o.n] = (P.cnt[o.n] || 0) + 1; };
  P.push = push;
  const group = () => {
    const s = window.__bc && window.__bc.controller && window.__bc.controller.state;
    if (s === 'awaitInput' || s === 'menu' || s === 'gameOver' || s === 'turnStart' || s === 'turnEnd' || s === 'promotion') return 'idle';
    if (s === 'resolving' || s === 'sequence' || s === 'postMove') return 'sequence';
    if (s === 'aiThinking') return 'ai';
    return 'other';
  };
  const loop = (t) => {
    if (P.lastFrame) {
      const dt = t - P.lastFrame;
      const arr = P.frames[group()];
      if (arr.length < 30000) arr.push(dt);
      if (dt > 1000) P.stalls++;
    }
    P.lastFrame = t;
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  try {
    new PerformanceObserver((list) => { for (const e of list.getEntries()) if (P.lt.length < 5000) P.lt.push({ start: e.startTime, dur: e.duration }); }).observe({ type: 'longtask', buffered: true });
  } catch { /* longtask unsupported */ }
  const tgt = (e) => { const t = e.target; return t && t.tagName ? `${t.tagName.toLowerCase()}${t.className && typeof t.className === 'string' ? '.' + t.className.split(' ')[0] : ''}` : ''; };
  window.addEventListener('pointerdown', (e) => push({ n: 'pd', t: e.timeStamp, now: performance.now(), pt: e.pointerType, x: Math.round(e.clientX), y: Math.round(e.clientY), tg: tgt(e) }), true);
  for (const t of ['pointerup', 'pointercancel', 'lostpointercapture']) window.addEventListener(t, (e) => push({ n: t, t: e.timeStamp, now: performance.now(), pt: e.pointerType, x: Math.round(e.clientX), y: Math.round(e.clientY), tg: tgt(e) }), true);
  let moves = 0;
  window.addEventListener('pointermove', (e) => { if (e.buttons || e.pointerType === 'touch') { moves++; if (moves % 4 === 1) push({ n: 'pm', t: e.timeStamp, now: performance.now(), pt: e.pointerType, x: Math.round(e.clientX), y: Math.round(e.clientY) }); } }, true);
  window.addEventListener('keydown', (e) => push({ n: 'key', t: e.timeStamp, now: performance.now(), k: e.key }), true);
  P.take = () => { const e = P.ev; P.ev = []; return e; };
  P.fpsTake = () => {
    const out = {};
    for (const [k, arr] of Object.entries(P.frames)) {
      if (!arr.length) continue;
      const a = arr.slice().sort((x, y) => x - y);
      const n = a.length, mean = a.reduce((s, v) => s + v, 0) / n;
      const sd = Math.sqrt(a.reduce((s, v) => s + (v - mean) ** 2, 0) / n);
      const q = (p) => a[Math.min(n - 1, Math.floor(p * n))];
      out[k] = { frames: n, mean: +mean.toFixed(2), sd: +sd.toFixed(2), p50: +q(0.5).toFixed(2), p95: +q(0.95).toFixed(2), p99: +q(0.99).toFixed(2), max: +a[n - 1].toFixed(1), over100ms: a.filter((v) => v > 100).length, over250ms: a.filter((v) => v > 250).length };
      P.frames[k] = [];
    }
    const lt = P.lt; P.lt = [];
    out.longtasks = { n: lt.length, totalMs: Math.round(lt.reduce((s, l) => s + l.dur, 0)), maxMs: Math.round(lt.reduce((m, l) => Math.max(m, l.dur), 0)) };
    out.stalls = P.stalls; P.stalls = 0;
    return out;
  };
}

/** After boot: record bus events and controller state changes with timestamps. */
export function busProbe() {
  const P = window.__pt, B = window.__bc;
  if (!P || !B || P.busProbed) return !!P && P.busProbed;
  P.busProbed = true;
  const names = ['game:start', 'turn:start', 'move:resolved', 'move:step', 'capture:begin', 'capture:impact', 'capture:end', 'attack:whoosh', 'promotion', 'castle', 'check', 'game:over', 'ui:select', 'ai:thinking'];
  for (const n of names) {
    B.bus.on(n, (p) => {
      P.push({ n, t: performance.now(), sq: p && p.square, san: p && p.san });
      if (n === 'ui:select') requestAnimationFrame(() => P.push({ n: 'frame-after-select', t: performance.now() }));
      if (n === 'move:resolved') requestAnimationFrame(() => P.push({ n: 'frame-after-resolved', t: performance.now() }));
    });
  }
  let last = '';
  B.controller.subscribe((s) => {
    const key = s.state + ':' + s.moves.length;
    if (key === last) return;
    last = key;
    P.push({ n: 'state', t: performance.now(), s: s.state, plies: s.moves.length });
  });
  return true;
}

/** Compact observation of the game + UI. */
export function observe() {
  const B = window.__bc;
  const vis = (el) => !!el && !el.hidden && el.getClientRects().length > 0;
  const s = B.controller.snapshot();
  const screens = Array.from(document.querySelectorAll('#ui-root > .scr')).filter((e) => !e.hidden && e.getClientRects().length > 0).map((e) => e.className.replace(/\b(scr|in|fr)\b/g, '').trim() || 'scr');
  const hud = document.querySelector('.hud');
  const sel = document.querySelector('.hud .turn');
  return {
    state: s.state, plies: s.moves.length, turn: s.turn, fen: s.fen, result: s.result ? s.result.result + ':' + s.result.reason : null,
    check: s.check, busy: s.busy, canUndo: s.canUndo, mode: s.mode ? s.mode.kind : null, san: s.moves.slice(-1)[0] ? s.moves.slice(-1)[0].san : null,
    modalOpen: B.ui.modalOpen, screens, hudVisible: vis(hud), turnText: sel ? sel.textContent : null,
    promoOpen: B.ui.promotion.isOpen, overOpen: B.ui.gameOver.isOpen,
    vw: innerWidth, vh: innerHeight,
    anim: B.settings.get().captureMode, loadingVisible: !!document.querySelector('.scr.loading:not([hidden]):not(.fade-out)'),
    capsCount: document.querySelectorAll('.caps .piece-ic').length,
    journalVisible: vis(document.querySelector('.hud .journal')),
    journalCount: document.querySelectorAll('.hud .journal .moves .mv:not(.ph)').length,
    ghostModal: B.ui.modalOpen && screens.filter((c) => c !== 'loading').length === 0,
    deadScreen: !B.ui.modalOpen && screens.filter((c) => c !== 'loading').length > 0,
  };
}

/** Find a screen point that really resolves to `sq` (a piece standing there, or the bare tile). */
export function findPoint(sq) {
  const b = window.__bc;
  const base = b.squareToScreen(sq);
  const canvas = document.querySelector('canvas');
  const cr = canvas ? canvas.getBoundingClientRect() : { left: 0, top: 0, right: innerWidth, bottom: innerHeight };
  const topIsCanvas = (x, y) => { const e = document.elementFromPoint(x, y); return !!e && e.tagName === 'CANVAS'; };
  for (const dy of [0, -14, -28, -42, -56, -70, 14, 28, -84, 42])
    for (const dx of [0, -10, 10, -22, 22]) {
      const x = base.x + dx, y = base.y + dy;
      if (x < cr.left || x > cr.right || y < cr.top || y > cr.bottom) continue;
      const r = b.pick(x, y);
      if ((r.actor ? r.actor.endsWith('@' + sq) : r.square === sq) && topIsCanvas(x, y)) return { x, y, base, ok: true };
    }
  // Fallback: a point whose TILE is `sq` even though a taller piece's body may win the click (reported as unreachable).
  for (const dy of [0, 10, 20, -10, 30, 40, -20])
    for (const dx of [0, -14, 14, -26, 26]) {
      const x = base.x + dx, y = base.y + dy;
      if (x < cr.left || x > cr.right || y < cr.top || y > cr.bottom) continue;
      const r = b.pick(x, y);
      if (r.square === sq && topIsCanvas(x, y)) return { x, y, base, ok: false, why: { top: r.top, square: r.square, actor: r.actor, blocked: r.blocked, note: 'only the bare tile resolves; a piece body occludes it' } };
    }
  const r = b.pick(base.x, base.y);
  return { x: base.x, y: base.y, base, ok: false, why: { top: r.top, square: r.square, actor: r.actor, blocked: r.blocked } };
}

/** 3D board vs the rules FEN. Returns a list of mismatches (empty = in sync). */
export function boardSync(fen) {
  const B = window.__bc;
  const out = [];
  const place = fen.split(' ')[0].split('/');
  const exp = {};
  const ROLE = { p: 'pawn', n: 'knight', b: 'bishop', r: 'rook', q: 'queen', k: 'king' };
  place.forEach((row, ri) => {
    let f = 0;
    for (const ch of row) {
      if (/\d/.test(ch)) { f += +ch; continue; }
      exp['abcdefgh'[f] + (8 - ri)] = { role: ROLE[ch.toLowerCase()], side: ch === ch.toLowerCase() ? 'b' : 'w' };
      f++;
    }
  });
  const actors = B.board.allActors();
  const seen = {};
  for (const a of actors) {
    const e = exp[a.square];
    if (seen[a.square]) out.push({ kind: 'duplicate-actor', square: a.square, detail: a.id + ' & ' + seen[a.square] });
    seen[a.square] = a.id;
    if (!e) { out.push({ kind: 'ghost-actor', square: a.square, detail: `${a.side}:${a.role} (${a.id}) has no piece in FEN` }); continue; }
    if (e.role !== a.role || e.side !== a.side) out.push({ kind: 'wrong-piece', square: a.square, detail: `3D ${a.side}:${a.role} vs rules ${e.side}:${e.role}` });
    const f = 'abcdefgh'.indexOf(a.square[0]), r = +a.square[1] - 1;
    const wx = f - 3.5, wz = 3.5 - r;
    const p = a.root.position;
    if (Math.abs(p.x - wx) > 0.08 || Math.abs(p.z - wz) > 0.08) out.push({ kind: 'actor-off-square', square: a.square, detail: `${a.id} at (${p.x.toFixed(2)},${p.z.toFixed(2)}) expected (${wx},${wz})` });
    if (!a.root.visible || !a.root.parent) out.push({ kind: 'actor-invisible', square: a.square, detail: a.id + (a.root.parent ? ' not visible' : ' detached') });
    if (p.y > 0.05 && p.y < 0.5) out.push({ kind: 'actor-left-lifted', square: a.square, detail: `${a.id} y=${p.y.toFixed(2)}` });
    if (p.y > 0.5 || p.y < -0.2) out.push({ kind: 'actor-wrong-height', square: a.square, detail: `${a.id} y=${p.y.toFixed(2)}` });
  }
  for (const sq of Object.keys(exp)) if (!seen[sq]) out.push({ kind: 'missing-actor', square: sq, detail: `rules has ${exp[sq].side}:${exp[sq].role}, 3D board has none` });
  return out;
}

/** Layout / UX audit of the visible UI. */
export function uiAudit(opts) {
  const out = [];
  const root = document.getElementById('ui-root');
  if (!root) return out;
  const vw = innerWidth, vh = innerHeight;
  const phone = Math.min(vw, vh) <= 500 || !!opts.coarse;
  const isVis = (el) => {
    for (let p = el; p && p !== document.body; p = p.parentElement) {
      if (p.hidden) return false;
      const cs = getComputedStyle(p);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.05) return false;
      if (p.getAttribute && p.getAttribute('aria-hidden') === 'true') return false;
    }
    const r = el.getBoundingClientRect();
    return r.width >= 1 && r.height >= 1;
  };
  const sig = (el) => {
    const cls = typeof el.className === 'string' ? el.className.split(/\s+/).filter((c) => c && !/^(fr|in|on|sel|lit)$/.test(c)).slice(0, 2).join('.') : '';
    const label = el.getAttribute('aria-label') || (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 24);
    return `${el.tagName.toLowerCase()}${cls ? '.' + cls : ''}[${label}]`;
  };
  const scrollParent = (el) => { for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) { const cs = getComputedStyle(p); if (((cs.overflowY === 'auto' || cs.overflowY === 'scroll') && p.scrollHeight > p.clientHeight + 1) || ((cs.overflowX === 'auto' || cs.overflowX === 'scroll') && p.scrollWidth > p.clientWidth + 1)) return p; } return null; };
  const layers = Array.from(root.children).filter((e) => e instanceof HTMLElement && isVis(e) && !e.classList.contains('loading'));
  const layerName = layers.map((l) => (l.className || l.id || l.tagName).toString().split(' ').filter((c) => c !== 'scr' && c !== 'in' && c !== 'fr')[0]).join('+') || 'none';
  const interactive = [];
  for (const l of layers) l.querySelectorAll('button, [role=button], [data-nav], a[href], input:not([hidden]), select').forEach((e) => { if (isVis(e)) interactive.push(e); });
  const add = (type, el, detail) => out.push({ type, key: sig(el), detail, layer: layerName });

  for (const el of interactive) {
    const r = el.getBoundingClientRect();
    if (!scrollParent(el) && (r.left < -1 || r.top < -1 || r.right > vw + 1 || r.bottom > vh + 1)) add('offscreen', el, `rect ${Math.round(r.left)},${Math.round(r.top)}..${Math.round(r.right)},${Math.round(r.bottom)} vs viewport ${vw}x${vh}`);
    if (phone && Math.min(r.width, r.height) < 40 && !el.disabled) add('touch-target', el, `${Math.round(r.width)}x${Math.round(r.height)}px (< 40)`);
    if (!el.closest('[data-tip]') && !el.getAttribute('title') && !el.closest('.stp')) add('no-tooltip', el, 'interactive element has no tooltip (data-tip/title)');
  }
  // text overflow / clipping
  for (const l of layers) {
    l.querySelectorAll('*').forEach((el) => {
      if (el instanceof SVGElement || !isVis(el)) return;
      const cs = getComputedStyle(el);
      const ox = cs.overflowX;
      if (ox === 'auto' || ox === 'scroll') return;
      const ownText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim());
      if (!ownText && ox === 'visible') return;
      if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1) add('text-overflow', el, `scrollWidth ${el.scrollWidth} > clientWidth ${el.clientWidth} ("${(el.textContent || '').trim().slice(0, 40)}")`);
      else if (ownText && ox !== 'visible' && el.clientHeight > 0 && el.scrollHeight > el.clientHeight + 2 && cs.overflowY !== 'auto' && cs.overflowY !== 'scroll') add('text-clipped-y', el, `scrollHeight ${el.scrollHeight} > clientHeight ${el.clientHeight}`);
    });
  }
  // overlap between interactive leaves
  const rects = interactive.map((e) => ({ e, r: e.getBoundingClientRect() }));
  for (let i = 0; i < rects.length; i++)
    for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i], b = rects[j];
      if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
      const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left), h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (w > 3 && h > 3 && (w * h) / Math.min(a.r.width * a.r.height, b.r.width * b.r.height) > 0.1) add('overlap', a.e, `overlaps ${sig(b.e)} by ${Math.round(w)}x${Math.round(h)}px`);
    }
  // HUD blocks
  const hud = root.querySelector('.hud');
  const blocks = [];
  if (hud && isVis(hud)) {
    Array.from(hud.children).forEach((c) => { if (c instanceof HTMLElement && isVis(c)) blocks.push({ e: c, r: c.getBoundingClientRect() }); });
    for (let i = 0; i < blocks.length; i++)
      for (let j = i + 1; j < blocks.length; j++) {
        const a = blocks[i], b = blocks[j];
        const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left), h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        if (w > 3 && h > 3) add('overlap', a.e, `HUD block overlaps ${sig(b.e)} by ${Math.round(w)}x${Math.round(h)}px`);
      }
    for (const b of blocks) if (b.r.left < -1 || b.r.top < -1 || b.r.right > vw + 1 || b.r.bottom > vh + 1) add('offscreen', b.e, `HUD block rect ${Math.round(b.r.left)},${Math.round(b.r.top)}..${Math.round(b.r.right)},${Math.round(b.r.bottom)} vs ${vw}x${vh}`);
    // does the HUD hide board squares / is the board clipped?
    const B = window.__bc;
    if (B && B.squareToScreen) {
      let off = 0, covered = 0; const coveredSq = [];
      for (const f of 'abcdefgh') for (let r = 1; r <= 8; r++) {
        const p = B.squareToScreen(f + r);
        if (p.x < 0 || p.y < 0 || p.x > vw || p.y > vh) { off++; continue; }
        if (blocks.some((b) => p.x > b.r.left && p.x < b.r.right && p.y > b.r.top && p.y < b.r.bottom)) { covered++; coveredSq.push(f + r); }
      }
      if (off) out.push({ type: 'board-clipped', key: 'board', detail: `${off} of 64 square centres are outside the ${vw}x${vh} viewport`, layer: layerName });
      if (covered) out.push({ type: 'hud-covers-board', key: 'board', detail: `${covered} square centres hidden under HUD blocks: ${coveredSq.slice(0, 10).join(',')}`, layer: layerName });
    }
  }
  return out;
}

/** Hover an element and report whether the shared tooltip shows up and fits the viewport. */
export function tooltipState() {
  const t = document.getElementById('ui-tip');
  if (!t || t.hidden) return null;
  const r = t.getBoundingClientRect();
  return { text: t.textContent.slice(0, 80), inViewport: r.left >= -1 && r.top >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1, rect: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)] };
}
