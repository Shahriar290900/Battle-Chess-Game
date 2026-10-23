// Loading screen: title, a thin progress line with % and stage text (driven by the real loading:progress), rotating
// tips, then "Press any key" / "Tap to begin". The same screen is reused while a new game is prepared.
import { h } from './dom';
import { button } from './controls';
import { isCoarse } from './screen';

export interface LoadingScreen {
  el: HTMLElement;
  /** Target progress 0..1 and the current stage label. */
  setProgress(fraction: number, stage?: string): void;
  show(stage?: string): void;
  /** Replace the meter with the gate; resolves on the first key or tap. */
  showGate(): Promise<void>;
  fail(message: string): void;
  hide(): void;
}

const TIPS = [
  'Pieces face their enemy. Emberhold marches first.',
  'Tap or press Space during a fight to skip the animation.',
  'A knight is the only piece that can leap over others.',
  'Castle early: it tucks your king away and wakes a rook.',
  'In Settings, lower Shadows or Resolution for a smoother game on older devices.',
  'Control the centre and the board opens up for you.',
  'A stalemate is a draw: leave the enemy king one safe move.',
];

export function createLoadingScreen(): LoadingScreen {
  const fillBar = h('i');
  const stageEl = h('span', { text: 'Loading' });
  const pctEl = h('span', { text: '0%' });
  const tipEl = h('p', { class: 'tip-line tip', text: TIPS[0] });
  tipEl.classList.remove('tip'); // (the shared tooltip owns .tip)
  const gate = button(isCoarse() ? 'Tap to begin' : 'Press any key', () => {}, { cls: 'gate-btn' });
  gate.hidden = true;
  const err = h('p', { class: 'err', hidden: true });
  const meter = h('div', { class: 'meter' }, h('div', { class: 'bar' }, fillBar), h('div', { class: 'meta' }, stageEl, pctEl));
  const el = h('div', { class: 'scr loading', role: 'status' },
    h('div', { class: 'logo' }, h('h1', { class: 'title', text: 'Battle Chess' }), h('p', { class: 'subtitle', text: 'Emberhold versus the Rime Host' })),
    meter, tipEl, gate, err);

  let target = 0, shown = 0, raf = 0, visible = true, tipTimer = 0, tipIdx = 0, hideTimer = 0, lastPct = -1;
  const paint = () => {
    fillBar.style.transform = `scaleX(${shown.toFixed(4)})`;
    const p = Math.round(shown * 100);
    if (p !== lastPct) { lastPct = p; pctEl.textContent = `${p}%`; }
  };
  const loop = () => {
    raf = 0;
    shown += (target - shown) * 0.16;
    if (Math.abs(target - shown) < 0.002) shown = target;
    paint();
    if (visible && shown !== target) raf = requestAnimationFrame(loop);
  };
  const kick = () => { if (!raf && visible) raf = requestAnimationFrame(loop); };
  const startTips = () => {
    clearInterval(tipTimer);
    tipTimer = window.setInterval(() => { tipIdx = (tipIdx + 1) % TIPS.length; tipEl.textContent = TIPS[tipIdx]; }, 5200);
  };
  startTips();

  return {
    el,
    setProgress(f, s) {
      target = Math.min(Math.max(f, 0), 1);
      if (s && stageEl.textContent !== s) stageEl.textContent = s;
      kick();
    },
    show(s) {
      clearTimeout(hideTimer);
      visible = true; target = 0; shown = 0; lastPct = -1;
      stageEl.textContent = s ?? 'Loading';
      el.classList.remove('fade-out'); el.hidden = false; gate.hidden = true; err.hidden = true; meter.hidden = false;
      tipIdx = (tipIdx + 1) % TIPS.length; tipEl.textContent = TIPS[tipIdx];
      startTips(); paint();
    },
    showGate() {
      target = 1; kick();
      stageEl.textContent = 'Ready';
      meter.hidden = true; gate.hidden = false;
      gate.focus({ preventScroll: true });
      return new Promise<void>((resolve) => {
        const done = () => { window.removeEventListener('keydown', onKey, true); el.removeEventListener('pointerdown', done); resolve(); };
        const onKey = (e: KeyboardEvent) => { if (!['Shift', 'Control', 'Alt', 'Meta', 'Tab'].includes(e.key)) { e.preventDefault(); done(); } };
        window.addEventListener('keydown', onKey, true);
        el.addEventListener('pointerdown', done);
      });
    },
    fail(message) { err.hidden = false; err.textContent = message; stageEl.textContent = 'Error'; meter.hidden = false; },
    hide() {
      visible = false; clearInterval(tipTimer);
      el.classList.add('fade-out');
      clearTimeout(hideTimer);
      hideTimer = window.setTimeout(() => { if (!visible) el.hidden = true; }, 260);
    },
  };
}
