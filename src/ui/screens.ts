// Loading screen (progress) → "Tap to begin" gate (unlocks audio from a user gesture).
import { h } from './dom';

export interface LoadingScreen {
  el: HTMLElement;
  setProgress(fraction: number, label?: string): void;
  /** Swap the bar for the gate; resolves on the first tap/key. */
  showGate(): Promise<void>;
  fail(message: string): void;
  hide(): void;
}

export function createLoadingScreen(): LoadingScreen {
  const bar = h('div', { class: 'load-bar-fill' });
  const label = h('p', { class: 'load-label', text: 'Loading…' });
  const gate = h('button', { class: 'btn btn-primary gate-btn', type: 'button', hidden: true }, h('span', { class: 'btn-label', text: 'Tap to begin' }));
  const el = h('div', { class: 'loading' },
    h('div', { class: 'loading-inner' },
      h('h1', { class: 'title', text: 'Battle Chess' }),
      h('p', { class: 'subtitle', text: 'Emberhold versus the Rime Host' }),
      h('div', { class: 'load-bar', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': 100 }, bar),
      label, gate));
  return {
    el,
    setProgress(f, text) {
      bar.style.width = `${Math.round(Math.min(Math.max(f, 0), 1) * 100)}%`;
      if (text) label.textContent = text;
    },
    showGate() {
      bar.style.width = '100%';
      label.textContent = 'The hosts are ready.';
      gate.hidden = false;
      gate.focus({ preventScroll: true });
      return new Promise<void>((resolve) => {
        const go = () => { gate.removeEventListener('click', go); window.removeEventListener('keydown', onKey); resolve(); };
        const onKey = (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') go(); };
        gate.addEventListener('click', go);
        el.addEventListener('pointerup', go, { once: true });
        window.addEventListener('keydown', onKey);
      });
    },
    fail(message) {
      label.textContent = message;
      label.classList.add('load-error');
    },
    hide() { el.classList.add('fade-out'); setTimeout(() => el.remove(), 700); },
  };
}
