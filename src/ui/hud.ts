// In-game HUD: a compact turn indicator, captured-piece glyphs, icon-only buttons (with tooltips) and a
// move-list drawer that stays closed until asked for. Pure DOM, driven by GameSnapshot updates.
import type { Role, Side, SettingsStore } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import type { GameController, GameSnapshot } from '../core/game';
import { REASON_LABEL, ROLE_VALUE, resultHeadline, sideName } from './glyphs';
import { ICON, clear, h, pieceIcon, svg } from './dom';

export interface HudHandlers {
  onMenu(): void;
  onSettings(): void;
  onUndo(): void;
  onSkip(): void;
}

export interface Hud {
  el: HTMLElement;
  update(s: GameSnapshot): void;
  setVisible(v: boolean): void;
}

const byValue = (a: Role, b: Role) => ROLE_VALUE[b] - ROLE_VALUE[a];
const adv = (roles: Role[]) => roles.reduce((n, r) => n + ROLE_VALUE[r], 0);

export function createHud(controller: GameController, settings: SettingsStore, handlers: HudHandlers): Hud {
  // ---- turn indicator
  const dot = h('span', { class: 'turn-dot' });
  const name = h('span', { class: 'turn-name' });
  const sub = h('span', { class: 'turn-sub' });
  const check = h('span', { class: 'turn-check', text: 'Check', hidden: true });
  const spinner = h('span', { class: 'spinner', hidden: true, 'aria-hidden': 'true' });
  const turn = h('div', { class: 'turn', role: 'status', 'aria-live': 'polite' }, dot, name, sub, check, spinner);

  // ---- captured glyphs (no labels: row 1 = taken by Emberhold, row 2 = taken by the Rime Host)
  const trayRow = (side: Side) => {
    const icons = h('span', { class: 'tray-icons' });
    const plus = h('span', { class: 'tray-adv' });
    return { el: h('div', { class: `tray tray-${side}`, title: `Taken by ${sideName(side)}`, 'aria-label': `Pieces taken by ${sideName(side)}` }, icons, plus), icons, plus };
  };
  const trayW = trayRow('w'), trayB = trayRow('b');
  const trays = h('div', { class: 'trays' }, trayW.el, trayB.el);

  // ---- buttons (icon only)
  const btn = (icon: string, label: string, cls: string, onClick: () => void) =>
    h('button', { class: `icon-btn ${cls}`, type: 'button', title: label, 'aria-label': label, onClick }, svg(icon));
  const undoBtn = btn(ICON.undo, 'Undo', 'btn-undo', handlers.onUndo);
  const skipBtn = btn(ICON.skip, 'Skip animation', 'btn-skip', handlers.onSkip);
  skipBtn.hidden = true;
  const movesBtn = btn(ICON.list, 'Move list', 'btn-moves', () => toggleMoves());
  movesBtn.setAttribute('aria-expanded', 'false');
  const buttons = h('div', { class: 'hud-buttons' }, skipBtn, undoBtn, movesBtn,
    btn(ICON.gear, 'Settings', 'btn-settings', handlers.onSettings),
    btn(ICON.menu, 'Menu', 'btn-menu', handlers.onMenu));

  // ---- move-list drawer (closed by default)
  const movesBody = h('ol', { class: 'moves-body' });
  const movesHead = h('div', { class: 'moves-head' }, h('span', { class: 'moves-title', text: 'Moves' }),
    h('button', { class: 'icon-btn small', type: 'button', title: 'Close', 'aria-label': 'Close move list', onClick: () => toggleMoves(false) }, svg(ICON.close)));
  const drawer = h('div', { class: 'moves', hidden: true }, movesHead, movesBody);
  function toggleMoves(open?: boolean) {
    const want = open ?? drawer.hidden;
    drawer.hidden = !want;
    movesBtn.setAttribute('aria-expanded', String(want));
  }

  const hint = h('div', { class: 'skip-hint', text: 'Tap to skip', hidden: true });
  const left = h('div', { class: 'hud-left' }, turn, trays);
  const el = h('div', { class: 'hud', hidden: true }, left, buttons, drawer, hint);

  let lastKey = '';
  let movesCount = -1;

  function renderTray(row: ReturnType<typeof trayRow>, roles: Role[], faction: 'emberhold' | 'rime', lead: number) {
    clear(row.icons);
    for (const r of [...roles].sort(byValue)) row.icons.append(pieceIcon(r, faction));
    row.plus.textContent = lead > 0 ? `+${lead}` : '';
    row.el.classList.toggle('empty', roles.length === 0);
  }

  function renderMoves(s: GameSnapshot) {
    if (s.moves.length === movesCount) return;
    movesCount = s.moves.length;
    clear(movesBody);
    for (let i = 0; i < s.moves.length; i += 2) {
      const w = s.moves[i], b = s.moves[i + 1];
      movesBody.append(h('li', { class: 'move-row' },
        h('span', { class: 'move-no', text: `${i / 2 + 1}` }),
        h('span', { class: 'move-w', text: w.san }),
        h('span', { class: 'move-b', text: b ? b.san : '' })));
    }
    movesBody.scrollTop = movesBody.scrollHeight;
  }

  function update(s: GameSnapshot) {
    const inGame = !!s.mode && s.state !== 'boot' && s.state !== 'loading' && s.state !== 'menu';
    el.hidden = !inGame;
    if (!inGame) return;
    renderMoves(s);
    const key = `${s.state}|${s.turn}|${s.check}|${s.result?.reason}|${s.moves.length}|${s.canUndo}`;
    if (key === lastKey) return;
    lastKey = key;

    const vsAi = s.mode?.kind === 'vs-ai';
    const last = s.moves[s.moves.length - 1];
    let faction: string = SIDE_FACTION[s.turn];
    if (s.result) {
      const head = resultHeadline(s.result.result, s.mode);
      faction = s.result.result === '1/2-1/2' ? 'neutral' : s.result.result === '1-0' ? 'emberhold' : 'rime';
      name.textContent = head.title;
      sub.textContent = REASON_LABEL[s.result.reason];
    } else if (s.busy && last) {
      faction = SIDE_FACTION[last.side];
      name.textContent = sideName(last.side);
      sub.textContent = last.san;
    } else if (s.thinking) {
      name.textContent = sideName(s.turn);
      sub.textContent = 'thinking…';
    } else {
      name.textContent = sideName(s.turn);
      sub.textContent = vsAi ? 'your move' : 'to move';
    }
    dot.dataset.faction = faction;
    spinner.hidden = !s.thinking;
    check.hidden = !s.check || !!s.result;

    renderTray(trayW, s.captured.w, 'rime', Math.max(0, adv(s.captured.w) - adv(s.captured.b)));
    renderTray(trayB, s.captured.b, 'emberhold', Math.max(0, adv(s.captured.b) - adv(s.captured.w)));
    trays.classList.toggle('empty', s.captured.w.length + s.captured.b.length === 0);

    undoBtn.disabled = !s.canUndo;
    skipBtn.hidden = !s.busy;
    hint.hidden = !s.busy;
    el.classList.toggle('busy', s.busy);
  }

  const applySettings = () => {
    const on = settings.get().showMoveList;
    movesBtn.hidden = !on;
    if (!on) toggleMoves(false);
  };
  settings.subscribe((_, k) => { if (k === 'showMoveList') applySettings(); });
  applySettings();
  controller.subscribe(update);

  return { el, update, setVisible: (v) => { el.hidden = !v; } };
}
