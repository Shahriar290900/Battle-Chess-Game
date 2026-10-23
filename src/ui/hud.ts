// In-game HUD: minimal so the board dominates. Top-left: faction crest, side to move, status (Check in crimson,
// "thinking..."), captured-piece rows. Top-right (bottom in portrait): thin-framed icon buttons. Optional slim move
// journal. Text nodes are updated in place; the DOM is never rebuilt per frame.
import type { Faction, Role, Side, SettingsStore } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import type { GameController, GameSnapshot } from '../core/game';
import { REASON_LABEL, ROLE_VALUE, sideName } from './glyphs';
import { ICON, crest, h, pieceIcon } from './dom';
import { iconButton } from './controls';
import { isCoarse } from './screen';

export interface HudHandlers { onMenu(): void; onSettings(): void; onUndo(): void; onSkip(): void }
export interface Hud {
  el: HTMLElement;
  update(s: GameSnapshot): void;
  /** Hide the HUD while a full-screen layer is open (keeps the camera reserve untouched). */
  setSuspended(v: boolean): void;
  /** Called with the bottom pixels the HUD occupies (portrait only), so the camera can leave room. */
  onLayout(fn: (bottomPx: number) => void): void;
  toggleJournal(): void;
}

const byValue = (a: Role, b: Role) => ROLE_VALUE[b] - ROLE_VALUE[a];
const adv = (roles: Role[]) => roles.reduce((n, r) => n + ROLE_VALUE[r], 0);

export function createHud(controller: GameController, settings: SettingsStore, handlers: HudHandlers): Hud {
  // ---- turn card
  let crestFaction: Faction | null = null;
  const crestHost = h('span', { class: 'crest-host' });
  const who = h('span', { class: 'who' });
  const st = h('span', { class: 'st' });
  const turn = h('div', { class: 'turn', role: 'status', 'aria-live': 'polite' }, crestHost, h('span', { class: 'txt' }, who, st));

  // ---- captured rows
  const rowW = h('div', { class: 'tray', 'aria-label': 'Pieces taken by Emberhold' }), rowB = h('div', { class: 'tray', 'aria-label': 'Pieces taken by the Rime Host' });
  const caps = h('div', { class: 'caps' }, rowW, rowB);

  // ---- tools
  const undoBtn = iconButton(ICON.undo, 'Undo', handlers.onUndo, '', 'Undo|Take back your last move (and the computer\'s reply).', 'U');
  const skipBtn = iconButton(ICON.skip, 'Skip animation', handlers.onSkip, '', 'Skip|Jump to the end of the current animation.', 'Space');
  skipBtn.hidden = true;
  const journalBtn = iconButton(ICON.list, 'Move list', () => settings.set('showMoveList', !settings.get().showMoveList), '', 'Move list|Show or hide the journal of moves.', 'J');
  const tools = h('div', { class: 'tools' }, skipBtn, undoBtn, journalBtn,
    iconButton(ICON.gear, 'Settings', handlers.onSettings, '', 'Settings|Graphics, audio and gameplay options.'),
    iconButton(ICON.menu, 'Pause menu', handlers.onMenu, '', 'Pause menu|Resume, resign, or return to the main menu.', 'Esc'));

  // ---- journal
  const movesGrid = h('div', { class: 'moves' });
  const journal = h('div', { class: 'journal scroll-y', 'aria-label': 'Move list', role: 'log' }, h('p', { class: 'jh', text: 'Journal' }), movesGrid);
  const skipHint = h('div', { class: 'skip-hint', hidden: true, text: isCoarse() ? 'Tap to skip' : 'Click or press Space to skip' });
  const el = h('div', { class: 'hud', hidden: true }, turn, caps, tools, journal, skipHint);

  let suspended = false, inGame = false;
  let layoutCb: ((px: number) => void) | null = null;
  let lastBottom = -1, layoutRaf = 0;
  const portrait = () => window.innerHeight >= window.innerWidth;
  function notifyLayout() {
    layoutRaf = 0;
    if (!layoutCb || el.hidden) return;
    let b = 0;
    if (portrait()) {
      const top = Math.min(tools.getBoundingClientRect().top, journal.hidden ? Infinity : journal.getBoundingClientRect().top);
      b = Math.round(window.innerHeight - top + 8);
    }
    if (b !== lastBottom) { lastBottom = b; layoutCb(b); }
  }
  const queueLayout = () => { if (!layoutRaf) layoutRaf = requestAnimationFrame(notifyLayout); };
  window.addEventListener('resize', queueLayout);

  // ---- state
  const text = (node: HTMLElement, t: string) => { if (node.textContent !== t) node.textContent = t; };
  function renderTurn(s: GameSnapshot) {
    const side: Side = s.result ? (s.result.result === '1-0' ? 'w' : s.result.result === '0-1' ? 'b' : s.turn) : s.busy && s.moves.length ? s.moves[s.moves.length - 1].side : s.turn;
    const faction = SIDE_FACTION[side];
    if (faction !== crestFaction) { crestFaction = faction; crestHost.replaceChildren(crest(faction)); }
    const vsAi = s.mode?.kind === 'vs-ai';
    text(who, sideName(side));
    let status: string;
    if (s.result) status = s.result.result === '1/2-1/2' ? 'Drawn game' : REASON_LABEL[s.result.reason].replace(/: .*/, '');
    else if (s.thinking) status = 'Thinking';
    else if (s.check) status = 'Check';
    else if (s.busy) status = 'Moving';
    else status = vsAi ? 'Your move' : 'To move';
    text(st, status);
    turn.classList.toggle('check', !!s.check && !s.result);
    turn.classList.toggle('thinking', s.thinking);
  }

  const capState = { w: '', b: '' };
  function renderCaps(s: GameSnapshot) {
    const kw = s.captured.w.join(','), kb = s.captured.b.join(',');
    if (kw === capState.w && kb === capState.b) return;
    capState.w = kw; capState.b = kb;
    const fill = (row: HTMLElement, roles: Role[], faction: Faction, lead: number) => {
      row.replaceChildren(...[...roles].sort(byValue).map((r) => pieceIcon(r, faction)));
      if (lead > 0 && roles.length) row.append(h('span', { class: 'adv', text: `+${lead}` }));
    };
    fill(rowW, s.captured.w, 'rime', Math.max(0, adv(s.captured.w) - adv(s.captured.b)));
    fill(rowB, s.captured.b, 'emberhold', Math.max(0, adv(s.captured.b) - adv(s.captured.w)));
  }

  let movesCount = -1; // -1 = the grid is stale and must be rebuilt
  let emptyShown = false;
  let blackSlot: HTMLElement | null = null;
  let lastMoveEl: HTMLElement | null = null;
  function renderMoves(s: GameSnapshot) {
    if (s.moves.length === movesCount) return;
    if (movesCount < 0 || s.moves.length < movesCount || emptyShown) { movesGrid.replaceChildren(); movesCount = 0; blackSlot = null; lastMoveEl = null; emptyShown = false; }
    for (let i = movesCount; i < s.moves.length; i++) {
      const m = s.moves[i];
      if (i % 2 === 0) {
        movesGrid.append(h('span', { class: 'no', text: `${i / 2 + 1}.` }));
        lastMoveEl = h('span', { class: 'mv', text: m.san });
        blackSlot = h('span', { class: 'mv ph' });
        movesGrid.append(lastMoveEl, blackSlot);
      } else if (blackSlot) {
        blackSlot.textContent = m.san; blackSlot.classList.remove('ph'); lastMoveEl = blackSlot; blackSlot = null;
      }
    }
    movesGrid.querySelector('.last')?.classList.remove('last');
    lastMoveEl?.classList.add('last');
    movesCount = s.moves.length;
    if (!s.moves.length) { movesGrid.replaceChildren(h('span', { class: 'empty', text: 'No moves yet' })); emptyShown = true; }
    journal.scrollTop = journal.scrollHeight; journal.scrollLeft = journal.scrollWidth;
  }

  function update(s: GameSnapshot) {
    const was = inGame;
    inGame = !!s.mode && s.state !== 'boot' && s.state !== 'loading' && s.state !== 'menu';
    el.hidden = !inGame || suspended;
    if (!inGame) { if (was && layoutCb) { lastBottom = 0; layoutCb(0); } return; }
    renderTurn(s); renderCaps(s);
    if (!journal.hidden) renderMoves(s);
    else movesCount = -1; // rebuild when it is shown again
    undoBtn.disabled = !s.canUndo;
    const busy = s.busy;
    skipBtn.hidden = !busy;
    skipHint.hidden = !busy;
    queueLayout();
  }

  const applySettings = () => {
    const on = settings.get().showMoveList;
    journal.hidden = !on;
    journalBtn.classList.toggle('lit', on);
    journalBtn.setAttribute('aria-pressed', String(on));
    if (on) { movesCount = -1; update(controller.snapshot()); }
    queueLayout();
  };
  settings.subscribe((_, k) => { if (k === 'showMoveList') applySettings(); });
  journal.hidden = !settings.get().showMoveList;
  journalBtn.classList.toggle('lit', !journal.hidden);
  controller.subscribe(update);

  return {
    el, update,
    setSuspended(v) { suspended = v; el.hidden = !inGame || suspended; if (!el.hidden) queueLayout(); },
    onLayout(fn) { layoutCb = fn; queueLayout(); },
    toggleJournal() { settings.set('showMoveList', !settings.get().showMoveList); },
  };
}
