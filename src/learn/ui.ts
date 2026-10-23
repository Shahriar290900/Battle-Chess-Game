// Shared Learn widgets (semantic markup, `learn-` classes; themed by learn.css variables).
import { clear, h } from './dom';
import type { Session } from './session';

export interface Caption {
  el: HTMLElement;
  setKicker(text: string): void;
  setTitle(text: string): void;
  setText(paragraphs: string[]): void;
  /** Feedback line: 'info' neutral, 'hint' gentle correction, 'ok' success. */
  setStatus(text: string, kind?: 'info' | 'hint' | 'ok'): void;
  readonly extra: HTMLElement;
  readonly actions: HTMLElement;
  /** The "lesson complete" stamp. */
  stamp(text: string): void;
  clearStamp(): void;
  dispose(): void;
}

/** Bottom-docked caption card. It reserves its own height so the camera frames the board above it. */
export function createCaption(session: Session): Caption {
  const kicker = h('p', { class: 'learn-kicker' });
  const title = h('h2', { class: 'learn-card-title' });
  const text = h('div', { class: 'learn-text' });
  const status = h('p', { class: 'learn-status', role: 'status', 'aria-live': 'polite' });
  const extra = h('div', { class: 'learn-extra' });
  const actions = h('div', { class: 'learn-actions' });
  const stampEl = h('div', { class: 'learn-stamp', hidden: true, 'aria-hidden': 'true' });
  const el = h('section', { class: 'learn-card learn-caption' }, kicker, title, text, status, extra, actions, stampEl);
  session.root.append(el);
  const report = () => session.setReserve(Math.ceil(el.getBoundingClientRect().height) + 10);
  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(report) : null;
  ro?.observe(el);
  requestAnimationFrame(report);
  return {
    el, extra, actions,
    setKicker: (t) => { kicker.textContent = t; },
    setTitle: (t) => { title.textContent = t; },
    setText(ps) { clear(text); for (const p of ps) text.append(h('p', { text: p })); },
    setStatus(t, kind = 'info') { status.textContent = t; status.dataset.kind = kind; status.hidden = !t; },
    stamp(t) { stampEl.textContent = t; stampEl.hidden = false; stampEl.classList.remove('learn-stamp-in'); void stampEl.offsetWidth; stampEl.classList.add('learn-stamp-in'); },
    clearStamp() { stampEl.hidden = true; stampEl.classList.remove('learn-stamp-in'); },
    dispose() { ro?.disconnect(); el.remove(); },
  };
}

/** A row of segmented toggle buttons (single choice). */
export function segmented<T extends string | number>(label: string, tipTitle: string, options: Array<{ value: T; label: string; tip: string }>, value: T, onChange: (v: T) => void): { el: HTMLElement; set(v: T): void } {
  const buttons = options.map((o) => h('button', { class: 'learn-seg', type: 'button', 'aria-pressed': 'false', 'data-tip': `${tipTitle}: ${o.label}|${o.tip}`, onClick: () => { set(o.value); onChange(o.value); } }, o.label));
  const set = (v: T) => buttons.forEach((b, i) => b.setAttribute('aria-pressed', String(options[i].value === v)));
  set(value);
  return { el: h('div', { class: 'learn-field', role: 'group', 'aria-label': label }, h('span', { class: 'learn-field-label', text: label }), h('div', { class: 'learn-segs' }, ...buttons)), set };
}

export function slider(label: string, tipText: string, min: number, max: number, step: number, value: number, fmt: (v: number) => string, onInput: (v: number) => void): HTMLElement {
  const out = h('output', { class: 'learn-field-value', text: fmt(value) });
  const input = h('input', { class: 'learn-range', type: 'range', min, max, step, value, 'aria-label': label, 'data-tip': tipText }) as HTMLInputElement;
  input.addEventListener('input', () => { const v = Number(input.value); out.textContent = fmt(v); onInput(v); });
  return h('label', { class: 'learn-field' }, h('span', { class: 'learn-field-label', text: label }), input, out);
}

/** Seven-by-seven mini movement diagram. */
export function diagramEl(d: { size: number; piece: { x: number; y: number }; cells: Array<{ x: number; y: number; kind: string }> }): HTMLElement {
  const grid = h('div', { class: 'learn-diagram', role: 'img', 'aria-label': 'Movement diagram' });
  grid.style.setProperty('--n', String(d.size));
  for (let y = d.size - 1; y >= 0; y--) for (let x = 0; x < d.size; x++) {
    const cell = d.cells.find((c) => c.x === x && c.y === y);
    const isPiece = d.piece.x === x && d.piece.y === y;
    grid.append(h('i', { class: `learn-dg ${(x + y) % 2 ? 'light' : 'dark'}${cell ? ` ${cell.kind}` : ''}${isPiece ? ' piece' : ''}` }));
  }
  return grid;
}
