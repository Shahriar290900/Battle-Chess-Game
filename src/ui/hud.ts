// In-game HUD: a carved wood + brass "chronicle box" docked at the bottom. Retro LCD (turn, last move, check / AI
// meter), depressible keys, felt-lined capture trays, and a paper move-list scroll that stays on screen when enabled.
import type { Role, Side, SettingsStore } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import type { GameController, GameSnapshot } from '../core/game';
import { REASON_LABEL, ROLE_VALUE, sideName } from './glyphs';
import { ICON, clear, h, pieceIcon } from './dom';
import { createLcd, meterText } from './lcd';
import { pushButton } from './controls';

export interface HudHandlers { onMenu(): void; onSettings(): void; onUndo(): void; onSkip(): void }
export interface Hud {
  el: HTMLElement;
  update(s: GameSnapshot): void;
  setVisible(v: boolean): void;
  /** Called with the height (px) the HUD occupies at the bottom, so the camera can leave room. */
  onLayout(fn: (bottomPx: number) => void): void;
}

const byValue = (a: Role, b: Role) => ROLE_VALUE[b] - ROLE_VALUE[a];
const adv = (roles: Role[]) => roles.reduce((n, r) => n + ROLE_VALUE[r], 0);

export function createHud(controller: GameController, settings: SettingsStore, handlers: HudHandlers): Hud {
  const lcd = createLcd(24, 3, 'amber', 'device-lcd');

  const trayRow = (side: Side, felt: string) => {
    const icons = h('span', { class: 'tray-icons' });
    const plus = h('span', { class: 'tray-adv' });
    return { icons, plus, el: h('div', { class: `tray ${felt}`, title: `Taken by ${sideName(side)}`, 'aria-label': `Pieces taken by ${sideName(side)}` }, icons, plus) };
  };
  const trayW = trayRow('w', 'felt-green'), trayB = trayRow('b', 'felt-red');
  const trays = h('div', { class: 'trays' }, trayW.el, trayB.el);

  const undoBtn = pushButton(ICON.undo, 'Undo', handlers.onUndo, 'k-undo');
  const skipBtn = pushButton(ICON.skip, 'Skip animation', handlers.onSkip, 'k-skip');
  skipBtn.hidden = true;
  const movesBtn = pushButton(ICON.list, 'Move list', () => settings.set('showMoveList', !settings.get().showMoveList), 'k-moves');
  const keys = h('div', { class: 'keys' }, skipBtn, undoBtn, movesBtn,
    pushButton(ICON.gear, 'Settings', handlers.onSettings, 'k-settings'), pushButton(ICON.menu, 'Menu', handlers.onMenu, 'k-menu'));

  const device = h('div', { class: 'device' }, h('div', { class: 'device-trim' }), trays, lcd.el, keys);

  // paper move-list scroll
  const scrollBody = h('div', { class: 'scroll-body', 'aria-label': 'Move list', role: 'log' });
  const scroll = h('button', { class: 'scroll', type: 'button', title: 'Tap to expand the move list', 'aria-expanded': 'false', onClick: () => {
    const open = scroll.classList.toggle('open');
    scroll.setAttribute('aria-expanded', String(open));
    notifyLayout();
  } }, scrollBody);
  const hint = h('div', { class: 'skip-hint', text: 'Tap to skip', hidden: true });
  const el = h('div', { class: 'hud', hidden: true }, hint, scroll, device);

  let layoutCb: ((px: number) => void) | null = null;
  let lastBottom = -1;
  function notifyLayout() {
    if (!layoutCb || el.hidden) return;
    const b = Math.round(window.innerHeight - el.getBoundingClientRect().top + 6);
    if (b !== lastBottom) { lastBottom = b; layoutCb(b); }
  }
  window.addEventListener('resize', () => requestAnimationFrame(notifyLayout));

  // ---- LCD state machine (timers only run while something animates)
  let snap: GameSnapshot | null = null;
  let tick = 0;
  let timer = 0;
  function renderLcd() {
    const s = snap;
    if (!s) return;
    const side = s.result ? (s.result.result === '1-0' ? 'w' : s.result.result === '0-1' ? 'b' : s.turn) : s.busy && s.moves.length ? s.moves[s.moves.length - 1].side : s.turn;
    lcd.setTheme(SIDE_FACTION[side] === 'emberhold' ? 'amber' : 'ice');
    const vsAi = s.mode?.kind === 'vs-ai';
    const name = sideName(side).toUpperCase();
    const last = s.moves[s.moves.length - 1];
    const l0 = s.result ? (s.result.result === '1/2-1/2' ? 'DRAWN GAME' : `${name} WINS`) : s.busy ? `${name} MOVES` : s.thinking ? `${name}` : vsAi ? 'YOUR MOVE' : `${name} TO MOVE`;
    const l1 = last ? `LAST ${Math.ceil(s.moves.length / 2)}${last.side === 'w' ? '.' : '..'} ${last.san}` : 'NEW GAME';
    let l2 = '';
    if (s.result) l2 = REASON_LABEL[s.result.reason].replace(/: .*/, '');
    else if (s.thinking) l2 = `THINKING ${meterText(10, ((tick % 12) / 11))}`;
    else if (s.check) l2 = tick % 2 === 0 ? '** CHECK **' : '';
    else l2 = `MOVE ${Math.floor(s.moves.length / 2) + 1}`;
    lcd.set([l0, l1, l2]);
  }
  function schedule() {
    const need = !!snap && (snap.thinking || (!!snap.check && !snap.result));
    if (need && !timer) timer = window.setInterval(() => { tick++; renderLcd(); }, 200);
    if (!need && timer) { clearInterval(timer); timer = 0; }
  }

  function renderTray(row: ReturnType<typeof trayRow>, roles: Role[], faction: 'emberhold' | 'rime', lead: number) {
    clear(row.icons);
    for (const r of [...roles].sort(byValue)) row.icons.append(pieceIcon(r, faction));
    row.plus.textContent = lead > 0 ? `+${lead}` : '';
  }

  let movesCount = -1;
  function renderMoves(s: GameSnapshot) {
    if (s.moves.length === movesCount) return;
    movesCount = s.moves.length;
    clear(scrollBody);
    s.moves.forEach((m, i) => {
      if (i % 2 === 0) scrollBody.append(h('span', { class: 'mv-no', text: `${i / 2 + 1}.` }));
      scrollBody.append(h('span', { class: `mv ${m.side}`, text: m.san }));
    });
    if (!s.moves.length) scrollBody.append(h('span', { class: 'mv-empty', text: 'No moves yet' }));
    scrollBody.scrollLeft = scrollBody.scrollWidth;
    scrollBody.scrollTop = scrollBody.scrollHeight;
  }

  function update(s: GameSnapshot) {
    snap = s;
    const inGame = !!s.mode && s.state !== 'boot' && s.state !== 'loading' && s.state !== 'menu';
    const wasHidden = el.hidden;
    el.hidden = !inGame;
    if (!inGame) { if (!wasHidden && layoutCb) { lastBottom = 0; layoutCb(0); } return; }
    renderMoves(s);
    renderLcd(); schedule();
    renderTray(trayW, s.captured.w, 'rime', Math.max(0, adv(s.captured.w) - adv(s.captured.b)));
    renderTray(trayB, s.captured.b, 'emberhold', Math.max(0, adv(s.captured.b) - adv(s.captured.w)));
    undoBtn.disabled = !s.canUndo;
    skipBtn.hidden = !s.busy;
    hint.hidden = !s.busy;
    el.classList.toggle('busy', s.busy);
    requestAnimationFrame(notifyLayout);
  }

  const applySettings = () => {
    const on = settings.get().showMoveList;
    scroll.hidden = !on;
    movesBtn.classList.toggle('lit', on);
    movesBtn.setAttribute('aria-pressed', String(on));
    if (!on) { scroll.classList.remove('open'); scroll.setAttribute('aria-expanded', 'false'); }
    requestAnimationFrame(notifyLayout);
  };
  settings.subscribe((_, k) => { if (k === 'showMoveList') applySettings(); });
  applySettings();
  controller.subscribe(update);

  return { el, update, setVisible: (v) => { el.hidden = !v; if (v) notifyLayout(); }, onLayout(fn) { layoutCb = fn; notifyLayout(); } };
}
