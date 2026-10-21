// In-game HUD: turn banner (faction name, check, "thinking…"), captured trays, collapsible move list
// and the Menu / Undo / Settings / Skip buttons. Pure DOM, driven by GameSnapshot updates.
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

export function createHud(controller: GameController, settings: SettingsStore, handlers: HudHandlers): Hud {
  // ---- banner
  const bannerName = h('span', { class: 'banner-name' });
  const bannerSub = h('span', { class: 'banner-sub' });
  const checkChip = h('span', { class: 'chip chip-check', text: 'Check', hidden: true });
  const spinner = h('span', { class: 'spinner', hidden: true, 'aria-hidden': 'true' });
  const swatch = h('span', { class: 'banner-swatch' });
  const banner = h('div', { class: 'turn-banner', role: 'status', 'aria-live': 'polite' },
    swatch, h('div', { class: 'banner-text' }, bannerName, bannerSub), spinner, checkChip);

  // ---- trays
  const trayRow = (side: Side) => {
    const icons = h('span', { class: 'tray-icons' });
    const adv = h('span', { class: 'tray-adv' });
    const el = h('div', { class: `tray tray-${side}`, 'aria-label': `Pieces taken by ${sideName(side)}` },
      h('span', { class: 'tray-label', text: sideName(side) }), icons, adv);
    return { el, icons, adv };
  };
  const trayW = trayRow('w'), trayB = trayRow('b');
  const trays = h('div', { class: 'trays' }, trayW.el, trayB.el);

  // ---- move list
  const movesBody = h('ol', { class: 'moves-body' });
  const movesTitle = h('span', { class: 'moves-title', text: 'Moves' });
  const movesLast = h('span', { class: 'moves-last' });
  const movesToggle = h('button', { class: 'moves-toggle', type: 'button', 'aria-expanded': 'false', onClick: () => toggleMoves() }, movesTitle, movesLast, svg(ICON.chevron, 'ic chev'));
  const movesEl = h('div', { class: 'movelist collapsed' }, movesToggle, movesBody);
  function toggleMoves() {
    const c = movesEl.classList.toggle('collapsed');
    movesToggle.setAttribute('aria-expanded', String(!c));
  }

  // ---- buttons
  const btn = (icon: string, label: string, cls: string, onClick: () => void) =>
    h('button', { class: `hud-btn ${cls}`, type: 'button', 'aria-label': label, onClick }, svg(icon), h('span', { class: 'hud-btn-label', text: label }));
  const undoBtn = btn(ICON.undo, 'Undo', 'btn-undo', handlers.onUndo);
  const skipBtn = btn(ICON.skip, 'Skip', 'btn-skip', handlers.onSkip);
  skipBtn.hidden = true;
  const buttons = h('div', { class: 'hud-buttons' },
    btn(ICON.menu, 'Menu', 'btn-menu', handlers.onMenu), undoBtn,
    btn(ICON.gear, 'Settings', 'btn-settings', handlers.onSettings), skipBtn);

  const hint = h('div', { class: 'skip-hint', text: 'Tap anywhere to skip', hidden: true });

  const left = h('div', { class: 'hud-left hud-side' }, banner, trays);
  const right = h('div', { class: 'hud-right hud-side' }, buttons, movesEl);
  const el = h('div', { class: 'hud', hidden: true }, left, right, hint);

  let lastKey = '';
  let movesCount = -1;

  function renderTray(row: ReturnType<typeof trayRow>, roles: Role[], faction: 'emberhold' | 'rime', adv: number) {
    clear(row.icons);
    for (const r of [...roles].sort(byValue)) row.icons.append(pieceIcon(r, faction));
    row.adv.textContent = adv > 0 ? `+${adv}` : '';
  }

  function renderMoves(s: GameSnapshot) {
    if (s.moves.length === movesCount) return;
    movesCount = s.moves.length;
    clear(movesBody);
    for (let i = 0; i < s.moves.length; i += 2) {
      const w = s.moves[i], b = s.moves[i + 1];
      movesBody.append(h('li', { class: 'move-row' },
        h('span', { class: 'move-no', text: `${i / 2 + 1}.` }),
        h('span', { class: 'move-w', text: w.san }),
        h('span', { class: 'move-b', text: b ? b.san : '' })));
    }
    movesBody.scrollTop = movesBody.scrollHeight;
    const last = s.moves[s.moves.length - 1];
    movesLast.textContent = last ? `${Math.ceil(s.moves.length / 2)}${last.side === 'w' ? '.' : '...'} ${last.san}` : '';
    movesTitle.textContent = `Moves (${s.moves.length})`;
  }

  function update(s: GameSnapshot) {
    const inGame = !!s.mode && s.state !== 'boot' && s.state !== 'loading' && s.state !== 'menu';
    el.hidden = !inGame;
    if (!inGame) return;
    const key = `${s.state}|${s.turn}|${s.check}|${s.result?.reason}|${s.moves.length}|${s.canUndo}`;
    renderMoves(s);
    if (key === lastKey) return;
    lastKey = key;

    const faction = SIDE_FACTION[s.turn];
    const vsAi = s.mode?.kind === 'vs-ai';
    el.dataset.turn = s.turn;
    banner.dataset.faction = faction;
    swatch.dataset.faction = faction;
    spinner.hidden = !s.thinking;
    checkChip.hidden = !s.check || !!s.result;
    const last = s.moves[s.moves.length - 1];
    if (s.result) {
      const head = resultHeadline(s.result.result, s.mode);
      banner.dataset.faction = s.result.result === '1/2-1/2' ? 'neutral' : s.result.result === '1-0' ? 'emberhold' : 'rime';
      swatch.dataset.faction = banner.dataset.faction;
      bannerName.textContent = head.title;
      bannerSub.textContent = REASON_LABEL[s.result.reason];
    } else if (s.busy && last) {
      banner.dataset.faction = SIDE_FACTION[last.side];
      swatch.dataset.faction = SIDE_FACTION[last.side];
      bannerName.textContent = sideName(last.side);
      bannerSub.textContent = last.captured ? 'strikes!' : last.isCastle ? 'castles' : last.promotion ? 'ascends' : 'advances';
    } else if (s.thinking) {
      bannerName.textContent = sideName(s.turn);
      bannerSub.textContent = 'is thinking…';
    } else {
      bannerName.textContent = sideName(s.turn);
      bannerSub.textContent = vsAi ? 'Your move' : 'to move';
    }

    renderTray(trayW, s.captured.w, 'rime', Math.max(0, adv(s.captured.w) - adv(s.captured.b)));
    renderTray(trayB, s.captured.b, 'emberhold', Math.max(0, adv(s.captured.b) - adv(s.captured.w)));

    undoBtn.disabled = !s.canUndo;
    skipBtn.hidden = !s.busy;
    hint.hidden = !s.busy;
    el.classList.toggle('busy', s.busy);
  }
  const adv = (roles: Role[]) => roles.reduce((n, r) => n + ROLE_VALUE[r], 0);

  const applySettings = () => { el.classList.toggle('no-moves', !settings.get().showMoveList); };
  settings.subscribe((_, k) => { if (k === 'showMoveList') applySettings(); });
  applySettings();
  controller.subscribe(update);

  return { el, update, setVisible: (v) => { el.hidden = !v; } };
}
