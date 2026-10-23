// Reusable controls: framed buttons, icon buttons and the `<< < value > >>` settings rows.
// Input policy: every control activates on the native `click` (mouse, touch and Enter/Space all produce exactly one),
// `touch-action: manipulation` removes the 300 ms delay, and pressed states are pure CSS (:active). Stepper arrows
// additionally repeat while held; they use pointerdown for that and ignore the click that follows (no double fire).
import { ICON, h, svg } from './dom';

export interface ButtonOpts { cls?: string; hint?: string; tip?: string; tipKey?: string }

/** Attach a shared-tooltip description ("Title|Description") to any element. */
export function tipOn<T extends HTMLElement>(el: T, tip?: string, key?: string): T {
  if (tip) el.dataset.tip = tip;
  if (key) el.dataset.tipKey = key;
  return el;
}

/** A framed text button: dim rough frame, bright on hover/focus, crimson fill when selected, pressed on :active. */
export function button(label: string, onClick: () => void, o: ButtonOpts = {}): HTMLButtonElement {
  const b = h('button', { class: `btn fr ${o.cls ?? ''}`.trim(), type: 'button', 'data-nav': '' },
    h('i', { class: 'fill' }), h('span', { class: 'lbl', text: label }), o.hint ? h('span', { class: 'kbd', text: o.hint }) : null);
  b.addEventListener('click', () => { if (!b.disabled) onClick(); });
  return tipOn(b, o.tip, o.tipKey);
}

export function setLabel(b: HTMLElement, text: string): void {
  const l = b.querySelector('.lbl');
  if (l && l.textContent !== text) l.textContent = text;
}

/** A square framed icon button (HUD). */
export function iconButton(path: string, label: string, onClick: () => void, cls = '', tip?: string, tipKey?: string): HTMLButtonElement {
  const b = h('button', { class: `ibtn fr ${cls}`.trim(), type: 'button', 'aria-label': label, title: label, 'data-nav': '' }, h('i', { class: 'fill' }), svg(path));
  b.addEventListener('click', () => { if (!b.disabled) onClick(); });
  return tipOn(b, tip ?? label, tipKey);
}

/** "Esc BACK" hint: also a real button so touch users can go back. */
export function backHint(onClick: () => void, label = 'Back'): HTMLButtonElement {
  const b = h('button', { class: 'hint-back', type: 'button', 'aria-label': label, 'data-nav': '' }, h('span', { class: 'kbd', text: 'Esc' }), h('span', { class: 'lbl', text: label }));
  b.addEventListener('click', onClick);
  return b;
}

// ------------------------------------------------------------------ settings rows
export interface Row { el: HTMLElement; refresh(): void }

interface StepperSpec {
  label: string;
  /** Text to show now. */
  text(): string;
  /** Move by one (dir ±1) or to the far end (big: ±2 = first/last or a larger jump). Return false to signal "at the end". */
  step(dir: -1 | 1, big: boolean): void;
  /** Whether a direction is still available (drives the disabled look of the arrows). */
  can(dir: -1 | 1): boolean;
  /** Clicking the value itself advances (wrapping for options). */
  cycle?(): void;
  note?: string;
}

function stepperRow(spec: StepperSpec, tip?: string, compact = false): Row {
  const val = h('span', { class: 'val', role: 'button', tabindex: -1, text: spec.text() });
  const arrow = (path: string, dir: -1 | 1, big: boolean, name: string) => {
    const a = h('button', { class: `arr${big ? ' big' : ''}`, type: 'button', tabindex: -1, 'aria-label': `${spec.label}: ${name}` }, svg(path, 'ic'));
    let timer = 0, rep = 0, fired = false;
    const stop = () => { clearTimeout(timer); clearInterval(rep); timer = 0; rep = 0; };
    const go = () => { if (spec.can(dir)) { spec.step(dir, big); row.refresh(); } };
    a.addEventListener('pointerdown', (e) => {
      if (e.button > 0) return;
      fired = true; go();
      if (!big) timer = window.setTimeout(() => { rep = window.setInterval(go, 70); }, 380);
    });
    a.addEventListener('pointerup', stop);
    for (const ev of ['pointerleave', 'pointercancel'] as const) a.addEventListener(ev, () => { stop(); fired = false; });
    a.addEventListener('click', (e) => { if (fired) { fired = false; e.preventDefault(); return; } go(); }); // keyboard/AT click: detail 0, no pointerdown
    return a;
  };
  const arrows = {
    ll: arrow(ICON.chev2L, -1, true, 'minimum'), l: arrow(ICON.chevL, -1, false, 'previous'),
    r: arrow(ICON.chevR, 1, false, 'next'), rr: arrow(ICON.chev2R, 1, true, 'maximum'),
  };
  const el = h('div', { class: `row${compact ? ' compact' : ''}`, role: 'group', tabindex: 0, 'aria-label': spec.label, 'data-nav': '' },
    h('span', { class: 'row-label' }, spec.label, spec.note ? h('small', { text: spec.note }) : null),
    h('span', { class: 'stp' }, arrows.ll, arrows.l, val, arrows.r, arrows.rr));
  const row: Row = {
    el,
    refresh() {
      const t = spec.text();
      if (val.textContent !== t) val.textContent = t;
      arrows.ll.disabled = arrows.l.disabled = !spec.can(-1);
      arrows.r.disabled = arrows.rr.disabled = !spec.can(1);
    },
  };
  val.addEventListener('click', () => { (spec.cycle ?? (() => spec.step(1, false)))(); row.refresh(); });
  el.addEventListener('keydown', (e) => {
    if (e.target !== el) return;
    const k = e.key;
    const dir = k === 'ArrowLeft' ? -1 : k === 'ArrowRight' ? 1 : 0;
    if (dir) { e.preventDefault(); if (spec.can(dir)) { spec.step(dir, e.shiftKey); row.refresh(); } }
    else if (k === 'Enter' || k === ' ') { e.preventDefault(); (spec.cycle ?? (() => spec.step(1, false)))(); row.refresh(); }
    else if (k === 'Home') { e.preventDefault(); spec.step(-1, true); row.refresh(); }
    else if (k === 'End') { e.preventDefault(); spec.step(1, true); row.refresh(); }
  });
  row.refresh();
  tipOn(el, tip);
  return row;
}

export interface Opt<T> { value: T; label: string }

/** Discrete choices. `<<`/`>>` jump to the first/last option. */
export function optionRow<T>(label: string, options: Opt<T>[], get: () => T, set: (v: T) => void, note?: string, tip?: string): Row {
  const idx = () => Math.max(0, options.findIndex((o) => o.value === get()));
  return stepperRow({
    label, note,
    text: () => options[idx()].label,
    can: (d) => (d < 0 ? idx() > 0 : idx() < options.length - 1),
    step: (d, big) => set(options[big ? (d < 0 ? 0 : options.length - 1) : Math.min(options.length - 1, Math.max(0, idx() + d))].value),
    cycle: () => set(options[(idx() + 1) % options.length].value),
  }, tip);
}

/** Numeric range; `<<`/`>>` move by 4 steps (hold `<`/`>` to sweep). */
export function rangeRow(label: string, min: number, max: number, step: number, get: () => number, set: (v: number) => void, fmt: (v: number) => string, tip?: string): Row {
  const clamp = (v: number) => Math.round(Math.min(max, Math.max(min, v)) / step) * step;
  return stepperRow({
    label,
    text: () => fmt(get()),
    can: (d) => (d < 0 ? get() > min + step / 2 : get() < max - step / 2),
    step: (d, big) => set(Math.round(clamp(get() + d * step * (big ? 4 : 1)) * 1000) / 1000),
    cycle: () => set(get() >= max - step / 2 ? min : Math.round(clamp(get() + step) * 1000) / 1000),
  }, tip);
}

export function toggleRow(label: string, get: () => boolean, set: (v: boolean) => void, note?: string, tip?: string): Row {
  return stepperRow({
    label, note,
    text: () => (get() ? 'On' : 'Off'),
    can: () => true,
    step: () => set(!get()),
    cycle: () => set(!get()),
  }, tip);
}

/** A row holding one action button (e.g. "Load your own track"). */
export function actionRow(label: string, buttonLabel: string, onClick: () => void, o: { note?: () => string; cls?: string; tip?: string } = {}): Row {
  const b = button(buttonLabel, onClick, { cls: `small ${o.cls ?? ''}`.trim() });
  const note = h('small', { class: 'row-note', text: o.note?.() ?? '' });
  const el = h('div', { class: 'row action' }, h('span', { class: 'row-label' }, label, note), b);
  tipOn(el, o.tip);
  return { el, refresh() { const t = o.note?.() ?? ''; if (note.textContent !== t) note.textContent = t; } };
}
