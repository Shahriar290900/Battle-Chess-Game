// The Controls reference (clean tables for mouse, touch, keyboard and camera), shared by Settings -> Controls and
// Pause -> Controls, plus the one-time first-game card.
import { h } from './dom';
import { backHint, button, tipOn } from './controls';
import { CAMERA, KEY, KEYBOARD, MOUSE, TOUCH } from './keys';
import type { Screen } from './screen';
import { isCoarse } from './screen';

function table(title: string, head: [string, string], rows: Array<[string, string]>): HTMLElement {
  return h('section', { class: 'ctl-sec' },
    h('h3', { text: title }),
    h('table', { class: 'ctl-table' },
      h('thead', {}, h('tr', {}, h('th', { text: head[0] }), h('th', { text: head[1] }))),
      h('tbody', {}, ...rows.map(([k, v]) => h('tr', {}, h('th', { scope: 'row' }, h('i', { class: 'kbd', text: k })), h('td', { text: v }))))));
}

/** The four tables. The device's own table (touch on phones, mouse elsewhere) comes first. */
export function createControlsPanel(): HTMLElement {
  const kb: Array<[string, string]> = KEYBOARD.map((s) => [s.key, `${s.action}: ${s.note}`]);
  const sections = [
    table('Mouse', ['Input', 'Action'], MOUSE),
    table('Touch', ['Gesture', 'Action'], TOUCH),
    table('Keyboard', ['Key', 'Action'], kb),
    table('Camera', ['Input', 'Action'], CAMERA),
  ];
  if (isCoarse()) sections.unshift(sections.splice(1, 1)[0]);
  return h('div', { class: 'ctl-grid' }, ...sections);
}

/** Standalone Controls screen (Pause -> Controls). */
export function createControlsScreen(exit: () => void): Screen {
  const sheet = h('div', { class: 'sheet scroll-y' }, createControlsPanel());
  const el = h('div', { class: 'scr page controls-page in', role: 'dialog', 'aria-label': 'Controls' },
    h('div', { class: 'hd' }, h('p', { class: 'kick', text: 'How to command the field' }), h('h2', { class: 'ttl', text: 'Controls' }), h('div', { class: 'rule' })),
    sheet, backHint(exit));
  tipOn(el.querySelector<HTMLElement>('.hint-back')!, 'Back|Return to the previous screen.', KEY.back);
  return { el, onShow() { sheet.scrollTop = 0; }, back() { exit(); return true; } };
}

// ---- first-game card
const SEEN_KEY = 'battle-chess.ui.controlsSeen';
export const firstGameSeen = (): boolean => { try { return localStorage.getItem(SEEN_KEY) === '1'; } catch { return false; } };
const markSeen = () => { try { localStorage.setItem(SEEN_KEY, '1'); } catch { /* storage blocked */ } };

export interface FirstGameCard { el: HTMLElement; show(): void; dismiss(): void; readonly isOpen: boolean }

/** A compact, non-blocking card (the board stays playable): the essentials, dismissable, remembered once dismissed. */
export function createFirstGameCard(openControls: () => void): FirstGameCard {
  const coarse = isCoarse();
  const lines: Array<[string, string]> = coarse
    ? [['Tap', 'a piece, then a lit tile'], ['2 fingers', 'look around, pinch to zoom'], ['Hold', 'a button for help']]
    : [['Click', 'a piece, then a lit tile'], ['U', 'undo'], ['M', 'move list'], ['F', 'free camera'], ['R  G', 'recenter, view fallen'], ['Esc', 'menu']];
  const el = h('div', { class: 'first-card fr', role: 'note', 'aria-label': 'Controls at a glance', hidden: true },
    h('p', { class: 'fc-title', text: 'Controls at a glance' }),
    h('ul', {}, ...lines.map(([k, v]) => h('li', {}, h('i', { class: 'kbd', text: k }), h('span', { text: v })))),
    h('div', { class: 'acts' },
      button('Got it', () => api.dismiss(), { cls: 'small sel', tip: 'Got it|Hide this card. It will not appear again.' }),
      button('Controls', () => { api.dismiss(); openControls(); }, { cls: 'small', tip: 'All controls|Open the full Controls reference.' })));
  let open = false;
  const api: FirstGameCard = {
    el,
    get isOpen() { return open; },
    show() { if (open || firstGameSeen()) return; open = true; el.hidden = false; },
    dismiss() { if (!open) return; open = false; el.hidden = true; markSeen(); },
  };
  return api;
}
