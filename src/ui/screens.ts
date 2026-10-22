// Loading screen: a wooden plaque with a brass-rimmed gauge (needle sweeps 0→100 %), a retro LCD with the current
// stage and a percent counter, and a "Tap to begin" brass plaque. Driven by real loading work (loading:progress).
import { h } from './dom';
import { createLcd, meterText } from './lcd';
import { plaque } from './controls';

export interface LoadingScreen {
  el: HTMLElement;
  /** Target progress 0..1 (the needle eases toward it) and the current stage label. */
  setProgress(fraction: number, stage?: string): void;
  /** Show the screen again for a new load (resets to 0). */
  show(stage?: string): void;
  /** Swap the gauge for the gate; resolves on the first tap/key. */
  showGate(): Promise<void>;
  fail(message: string): void;
  hide(): void;
}

function drawDial(): HTMLCanvasElement {
  const S = 360;
  const c = document.createElement('canvas');
  c.width = c.height = S;
  c.className = 'dial-face';
  const g = c.getContext('2d')!;
  g.fillStyle = '#d6c59a';
  g.beginPath(); g.arc(S / 2, S / 2, S / 2, 0, Math.PI * 2); g.fill();
  const rg = g.createRadialGradient(S / 2, S / 2, S * 0.3, S / 2, S / 2, S / 2);
  rg.addColorStop(0, 'rgba(0,0,0,0)'); rg.addColorStop(1, 'rgba(70,45,10,0.35)');
  g.fillStyle = rg; g.fill();
  g.strokeStyle = '#2a1a0a'; g.fillStyle = '#2a1a0a';
  for (let i = 0; i <= 50; i++) {
    const a = ((-135 + (270 * i) / 50) * Math.PI) / 180 - Math.PI / 2;
    const major = i % 10 === 0, mid = i % 5 === 0;
    const r0 = S * 0.43, r1 = r0 - (major ? S * 0.085 : mid ? S * 0.055 : S * 0.03);
    g.lineWidth = major ? 4 : 2;
    g.beginPath(); g.moveTo(S / 2 + Math.cos(a) * r0, S / 2 + Math.sin(a) * r0); g.lineTo(S / 2 + Math.cos(a) * r1, S / 2 + Math.sin(a) * r1); g.stroke();
    if (major) {
      g.font = `bold ${S * 0.07}px Georgia, serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
      const rt = S * 0.3;
      g.fillText(String(i * 2), S / 2 + Math.cos(a) * rt, S / 2 + Math.sin(a) * rt);
    }
  }
  g.font = `italic ${S * 0.06}px Georgia, serif`; g.textAlign = 'center';
  g.fillText('forge', S / 2, S * 0.68);
  return c;
}

export function createLoadingScreen(): LoadingScreen {
  const lcd = createLcd(22, 2, 'amber', 'loading-lcd');
  const needle = h('div', { class: 'dial-needle' });
  const dial = h('div', { class: 'dial' }, drawDial(), needle, h('div', { class: 'dial-hub' }), h('div', { class: 'dial-glass' }));
  const gate = plaque('Tap to begin', () => {}, 'gate-btn');
  gate.hidden = true;
  const msg = h('p', { class: 'load-error-text', hidden: true });
  const el = h('div', { class: 'loading' },
    h('div', { class: 'loading-board' },
      h('h1', { class: 'title', text: 'Battle Chess' }),
      h('p', { class: 'subtitle', text: 'Emberhold versus the Rime Host' }),
      dial, lcd.el, gate, msg));

  let target = 0, shown = 0, stage = 'Loading…', raf = 0, visible = true;
  const paint = () => {
    needle.style.transform = `rotate(${-135 + shown * 270}deg)`;
    lcd.set([stage.toUpperCase(), `${meterText(14, shown)} ${String(Math.round(shown * 100)).padStart(3, ' ')}%`]);
  };
  const loop = () => {
    raf = 0;
    shown += (target - shown) * 0.12;
    if (Math.abs(target - shown) < 0.002) shown = target;
    paint();
    if (visible && shown !== target) raf = requestAnimationFrame(loop);
  };
  const kick = () => { if (!raf) raf = requestAnimationFrame(loop); };
  paint();

  return {
    el,
    setProgress(f, s) {
      target = Math.min(Math.max(f, 0), 1);
      if (s) stage = s;
      kick();
    },
    show(s) {
      visible = true; target = 0; shown = 0; stage = s ?? 'Loading…';
      el.classList.remove('fade-out'); el.hidden = false; gate.hidden = true; msg.hidden = true;
      paint();
    },
    showGate() {
      target = 1; stage = 'Ready'; kick();
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
    fail(message) { msg.hidden = false; msg.textContent = message; stage = 'Error'; paint(); },
    hide() { visible = false; el.classList.add('fade-out'); window.setTimeout(() => { if (!visible) el.hidden = true; }, 600); },
  };
}
