// Physical controls for the hi-fi style panels: brass knobs (drag / wheel / arrow keys), toggle switches with a
// metal lever, rotary selectors that click through detents, and depressible push buttons.
import { h, svg } from './dom';

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

export interface Knob { el: HTMLElement; set(v: number): void; get(): number }

export function createKnob(o: {
  label: string; min: number; max: number; step: number; value: number;
  format?: (v: number) => string; onInput(v: number, text: string): void;
}): Knob {
  let value = clamp(o.value, o.min, o.max);
  const fmt = o.format ?? ((v: number) => String(v));
  const mark = h('span', { class: 'knob-mark' });
  const cap = h('div', { class: 'knob-cap' }, mark);
  const body = h('div', { class: 'knob', role: 'slider', tabindex: 0, 'aria-label': o.label, 'aria-valuemin': o.min, 'aria-valuemax': o.max }, cap);
  const readout = h('span', { class: 'ctl-value' });
  const el = h('div', { class: 'ctl ctl-knob' }, body, h('span', { class: 'ctl-label', text: o.label }), readout);
  const snap = (v: number) => clamp(Math.round(v / o.step) * o.step, o.min, o.max);
  const paint = () => {
    const t = (value - o.min) / (o.max - o.min);
    cap.style.transform = `rotate(${-135 + t * 270}deg)`;
    readout.textContent = fmt(value);
    body.setAttribute('aria-valuenow', String(value));
    body.setAttribute('aria-valuetext', fmt(value));
  };
  const apply = (v: number) => { const n = snap(v); if (n === value) return; value = n; paint(); o.onInput(value, fmt(value)); };
  let drag: { y: number; v: number; id: number } | null = null;
  body.addEventListener('pointerdown', (e) => { drag = { y: e.clientY, v: value, id: e.pointerId }; body.setPointerCapture(e.pointerId); e.preventDefault(); });
  body.addEventListener('pointermove', (e) => { if (drag && e.pointerId === drag.id) apply(drag.v + ((drag.y - e.clientY) / 140) * (o.max - o.min)); });
  const end = (e: PointerEvent) => { if (drag?.id === e.pointerId) drag = null; };
  body.addEventListener('pointerup', end); body.addEventListener('pointercancel', end);
  body.addEventListener('wheel', (e) => { e.preventDefault(); apply(value + (e.deltaY < 0 ? 1 : -1) * o.step); }, { passive: false });
  body.addEventListener('keydown', (e) => {
    const d = e.key === 'ArrowUp' || e.key === 'ArrowRight' ? 1 : e.key === 'ArrowDown' || e.key === 'ArrowLeft' ? -1 : 0;
    if (d) { e.preventDefault(); apply(value + d * o.step); }
  });
  body.addEventListener('focus', () => o.onInput(value, fmt(value)));
  paint();
  return { el, get: () => value, set(v) { value = snap(v); paint(); } };
}

export interface Toggle { el: HTMLElement; set(on: boolean): void }

export function createToggle(o: { label: string; value: boolean; onChange(on: boolean): void }): Toggle {
  let on = o.value;
  const btn = h('button', { class: 'toggle', type: 'button', role: 'switch', 'aria-label': o.label }, h('span', { class: 'toggle-lever' }));
  const el = h('div', { class: 'ctl ctl-toggle' }, btn, h('span', { class: 'ctl-label', text: o.label }));
  const paint = () => { btn.setAttribute('aria-checked', String(on)); btn.classList.toggle('on', on); };
  btn.addEventListener('click', () => { on = !on; paint(); o.onChange(on); });
  paint();
  return { el, set(v) { on = v; paint(); } };
}

export interface Selector<T extends string | number> { el: HTMLElement; set(v: T): void }

export function createSelector<T extends string | number>(o: {
  label: string; options: Array<{ value: T; label: string }>; value: T; onChange(v: T, text: string): void;
}): Selector<T> {
  let i = Math.max(0, o.options.findIndex((x) => x.value === o.value));
  const n = o.options.length;
  const mark = h('span', { class: 'knob-mark' });
  const cap = h('div', { class: 'knob-cap' }, mark);
  const ticks = h('div', { class: 'detents' }, ...o.options.map((_, k) => h('i', { style: { transform: `rotate(${-60 + (120 * k) / Math.max(1, n - 1)}deg)` } })));
  const btn = h('button', { class: 'knob selector', type: 'button' }, ticks, cap);
  const readout = h('span', { class: 'ctl-value' });
  const el = h('div', { class: 'ctl ctl-selector' }, btn, h('span', { class: 'ctl-label', text: o.label }), readout);
  const paint = () => {
    cap.style.transform = `rotate(${-60 + (120 * i) / Math.max(1, n - 1)}deg)`;
    readout.textContent = o.options[i].label;
    btn.setAttribute('aria-label', `${o.label}: ${o.options[i].label}`);
  };
  const go = (d: number) => { i = (i + d + n) % n; paint(); o.onChange(o.options[i].value, o.options[i].label); };
  btn.addEventListener('click', (e) => go(e.shiftKey ? -1 : 1));
  btn.addEventListener('contextmenu', (e) => { e.preventDefault(); go(-1); });
  btn.addEventListener('keydown', (e) => { if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') { e.preventDefault(); go(-1); } else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') { e.preventDefault(); go(1); } });
  paint();
  return { el, set(v) { const k = o.options.findIndex((x) => x.value === v); if (k >= 0) { i = k; paint(); } } };
}

/** Depressible brass-bezelled wooden key with an engraved icon. */
export function pushButton(icon: string, label: string, onClick: () => void, cls = ''): HTMLButtonElement {
  return h('button', { class: `pbtn ${cls}`.trim(), type: 'button', title: label, 'aria-label': label, onClick }, h('span', { class: 'pbtn-cap' }, svg(icon)));
}

/** A brass nameplate button (text). */
export function plaque(label: string, onClick: () => void, cls = ''): HTMLButtonElement {
  return h('button', { class: `plaque ${cls}`.trim(), type: 'button', onClick }, h('span', { text: label }));
}
