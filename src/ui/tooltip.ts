// Shared tooltip: ONE element, positioned with a transform, driven by delegated document listeners. Any element with
// `data-tip="Title|Description"` (+ optional `data-tip-key="U"`) gets one, including elements added later and the Learn
// screens. Desktop: after ~350 ms of hover. Keyboard: on focus (only after keyboard use). Touch: long-press ~450 ms,
// which then swallows the click so the button underneath is not triggered. aria-describedby points at the tip.
const KEY = 'battle-chess.ui.tooltips';
let enabled = true;
try { enabled = localStorage.getItem(KEY) !== 'off'; } catch { /* storage blocked */ }

export const tooltipsEnabled = () => enabled;
export function setTooltipsEnabled(on: boolean): void {
  enabled = on;
  try { localStorage.setItem(KEY, on ? 'on' : 'off'); } catch { /* ignore */ }
  if (!on) hideNow();
}

let tip: HTMLElement, tt: HTMLElement, td: HTMLElement, tk: HTMLElement;
let current: HTMLElement | null = null;
let showTimer = 0, hideTimer = 0;
let suppressClick = false;
let suppressUntil = 0;

function hideNow(): void {
  clearTimeout(showTimer); clearTimeout(hideTimer);
  if (current) current.removeAttribute('aria-describedby');
  current = null;
  if (tip) tip.hidden = true;
}

function show(el: HTMLElement): void {
  const raw = el.dataset.tip;
  if (!raw || !enabled || !el.isConnected) return;
  const [title, ...rest] = raw.split('|');
  tt.textContent = title;
  td.textContent = rest.join('|');
  td.hidden = !rest.length;
  const key = el.dataset.tipKey;
  tk.textContent = key ?? '';
  tk.hidden = !key;
  if (current && current !== el) current.removeAttribute('aria-describedby');
  current = el;
  el.setAttribute('aria-describedby', 'ui-tip');
  tip.hidden = false;
  // read phase, then one write
  const r = el.getBoundingClientRect();
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  const vw = window.innerWidth, vh = window.innerHeight, gap = 10, pad = 8;
  let y = r.bottom + gap;
  if (y + th > vh - pad) y = r.top - gap - th; // flip above
  if (y < pad) y = Math.min(vh - th - pad, Math.max(pad, r.bottom + gap));
  const x = Math.min(vw - tw - pad, Math.max(pad, r.left + r.width / 2 - tw / 2));
  tip.style.transform = `translate3d(${Math.round(x)}px, ${Math.round(y)}px, 0)`;
}

const find = (t: EventTarget | null): HTMLElement | null => (t instanceof Element ? t.closest<HTMLElement>('[data-tip]') : null);

export function installTooltips(root: HTMLElement): void {
  tip = document.createElement('div');
  tip.id = 'ui-tip'; tip.className = 'tip fr'; tip.setAttribute('role', 'tooltip'); tip.hidden = true;
  tt = document.createElement('b'); tt.className = 'tt';
  td = document.createElement('span'); td.className = 'td';
  tk = document.createElement('span'); tk.className = 'kbd';
  const head = document.createElement('div'); head.className = 'th';
  head.append(tt, tk);
  tip.append(head, td);
  root.append(tip);

  const schedule = (el: HTMLElement, ms: number) => {
    clearTimeout(showTimer); clearTimeout(hideTimer);
    if (current === el && !tip.hidden) return;
    showTimer = window.setTimeout(() => show(el), ms);
  };

  document.addEventListener('pointerover', (e) => {
    if (e.pointerType !== 'mouse') return;
    const el = find(e.target);
    if (!el) { if (current || showTimer) hideNow(); return; }
    if (el !== current) { if (current) hideNow(); schedule(el, 350); }
  }, { passive: true });
  document.addEventListener('pointerout', (e) => {
    if (e.pointerType === 'mouse' && !find(e.relatedTarget)) hideNow();
  }, { passive: true });
  document.addEventListener('focusin', (e) => {
    if (document.documentElement.dataset.input !== 'kbd') return;
    const el = find(e.target);
    if (el) schedule(el, 120); else hideNow();
  });
  document.addEventListener('focusout', () => hideNow());
  document.addEventListener('keydown', (e) => { if (!e.key.startsWith('Arrow') && e.key !== 'Tab') hideNow(); }, true);
  window.addEventListener('scroll', hideNow, { capture: true, passive: true });
  window.addEventListener('resize', hideNow);

  // touch: long-press shows the tip and cancels the tap
  document.addEventListener('pointerdown', (e) => {
    suppressClick = false;
    if (e.pointerType === 'mouse') { hideNow(); return; }
    const el = find(e.target);
    if (!el || (e.target as Element).closest('.stp')) return;
    clearTimeout(showTimer);
    showTimer = window.setTimeout(() => { suppressClick = true; suppressUntil = performance.now() + 900; show(el); }, 450);
  }, { capture: true, passive: true });
  const release = (e: PointerEvent) => {
    if (e.pointerType === 'mouse') return;
    clearTimeout(showTimer);
    if (!tip.hidden) { clearTimeout(hideTimer); hideTimer = window.setTimeout(hideNow, 1800); }
  };
  document.addEventListener('pointerup', release, { capture: true, passive: true });
  document.addEventListener('pointercancel', release, { capture: true, passive: true });
  document.addEventListener('contextmenu', (e) => { if (find(e.target)) e.preventDefault(); });
  document.addEventListener('click', (e) => {
    if (suppressClick && performance.now() < suppressUntil) { e.stopImmediatePropagation(); e.preventDefault(); }
    suppressClick = false;
  }, true);
}
