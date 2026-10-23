// Game over (large title, winner subtitle, Rematch / Main menu) and the promotion picker (four framed cards).
import type { GameModeConfig, PromotionRole, Side } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import type { GameEnd } from '../core/rules';
import { clear, h, pieceIcon } from './dom';
import { button, tipOn } from './controls';
import { ROLE_LABEL, REASON_LABEL, resultHeadline } from './glyphs';
import { focusFirst } from './nav';

export interface Overlay { el: HTMLElement; readonly isOpen: boolean; open(): void; close(): void }

const TITLE: Record<string, string> = {
  checkmate: 'Checkmate', stalemate: 'Stalemate', draw: 'Draw', resign: 'Resignation', threefold: 'Draw', insufficient: 'Draw', 'fifty-move': 'Draw',
};

export interface GameOverPanel extends Overlay { show(end: GameEnd, mode: GameModeConfig | null): void }

export function createGameOverPanel(handlers: { onRematch(): void; onMenu(): void; onToggle?(open: boolean): void }): GameOverPanel {
  const kick = h('p', { class: 'kick' });
  const title = h('h2', { class: 'ttl' });
  const sub = h('p', { class: 'sub' });
  const acts = h('div', { class: 'acts' });
  const el = h('div', { class: 'scr over in', hidden: true, role: 'dialog', 'aria-label': 'Game over' }, kick, title, h('div', { class: 'rule' }), sub, acts);
  let open = false;
  const api: GameOverPanel = {
    el,
    get isOpen() { return open; },
    show(end, mode) {
      const head = resultHeadline(end.result, mode);
      el.dataset.win = end.result === '1/2-1/2' ? 'none' : end.result === '1-0' ? 'emberhold' : 'rime';
      kick.textContent = end.reason === 'checkmate' || end.reason === 'resign' ? head.title : REASON_LABEL[end.reason];
      title.textContent = TITLE[end.reason] ?? 'Game over';
      sub.textContent = end.result === '1/2-1/2' ? `${REASON_LABEL[end.reason]}. Neither host yields.` : head.sub;
      clear(acts);
      const rematch = button('Rematch', () => { api.close(); handlers.onRematch(); }, { cls: 'sel', tip: 'Rematch|Start a new game with the same settings.' });
      rematch.setAttribute('data-autofocus', '');
      acts.append(rematch, button('Main Menu', () => { api.close(); handlers.onMenu(); }, { tip: 'Main Menu|Leave to the title screen.' }),
        button('View Board', () => api.close(), { cls: 'small', tip: 'View Board|Look over the final position. Open the menu from the top bar.', tipKey: 'Esc' }));
      open = true; el.hidden = false;
      handlers.onToggle?.(true);
      focusFirst(el);
    },
    open() { el.hidden = false; open = true; handlers.onToggle?.(true); },
    close() { const was = open; open = false; el.hidden = true; if (was) handlers.onToggle?.(false); },
  };
  return api;
}

export interface PromotionPicker extends Overlay { choose(side: Side): Promise<PromotionRole | null>; cancel(): void }
const PROMO_ROLES: PromotionRole[] = ['queen', 'rook', 'bishop', 'knight'];
const PROMO_TIP: Record<PromotionRole, string> = {
  queen: 'Queen|The strongest piece: moves like a rook and a bishop.', rook: 'Rook|Slides any distance along ranks and files.',
  bishop: 'Bishop|Slides any distance on diagonals.', knight: 'Knight|Leaps in an L shape, over other pieces.',
};

export function createPromotionPicker(): PromotionPicker {
  const cards = h('div', { class: 'cards four', role: 'list' });
  const el = h('div', { class: 'scr promo in', hidden: true, role: 'dialog', 'aria-label': 'Choose promotion' },
    h('div', { class: 'hd' }, h('p', { class: 'kick', text: 'Choose' }), h('h2', { class: 'ttl', text: 'Your Promotion' })), cards);
  let open = false;
  let resolve: ((r: PromotionRole | null) => void) | null = null;
  const done = (r: PromotionRole | null) => { const f = resolve; resolve = null; api.close(); f?.(r); };
  const api: PromotionPicker = {
    el,
    get isOpen() { return open; },
    choose(side) {
      resolve?.(null);
      const faction = SIDE_FACTION[side];
      clear(cards);
      PROMO_ROLES.forEach((r, i) => {
        const b = h('button', { class: `card fr lv${i}`, type: 'button', role: 'listitem', 'data-nav': '', 'data-faction': faction, 'aria-label': ROLE_LABEL[r] },
          h('div', { class: 'art' }, pieceIcon(r, faction, 'big')), h('div', { class: 'meta' }, h('h3', { class: 'nm', text: ROLE_LABEL[r] })));
        b.addEventListener('click', () => done(r));
        tipOn(b, PROMO_TIP[r]);
        if (i === 0) b.setAttribute('data-autofocus', '');
        cards.append(b);
      });
      open = true; el.hidden = false;
      focusFirst(el);
      return new Promise<PromotionRole | null>((res) => { resolve = res; });
    },
    cancel() { done(null); },
    open() { el.hidden = false; open = true; },
    close() { open = false; el.hidden = true; },
  };
  return api;
}
