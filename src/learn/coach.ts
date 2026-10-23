// Beginner-game coach: on each of the human's turns it suggests a sensible move (glow on the piece and target square
// plus a short reason). Lives until the game ends, a different game starts, or it is dismissed.
import { gsap } from 'gsap';
import { Rules } from '../core/rules';
import type { AppServices } from '../main';
import { suggestMove } from './hints';
import { btn, h, tip } from './dom';
import { createOwnMarkers } from './stage';

export interface Coach { stop(): void; readonly active: boolean }

export function startCoach(s: AppServices, parent: HTMLElement): Coach {
  const own = createOwnMarkers(s.scene);
  const tick = (t: number) => own.markers.update(t);
  gsap.ticker.add(tick);
  let on = true;
  let timer = 0;
  let stopped = false;
  let expectStart = true; // the first game:start is the beginner game itself

  const text = h('p', { class: 'learn-coach-text', 'aria-live': 'polite' });
  const toggle = btn('Hints on', tip('Move hints', 'Turn the coach\'s suggested move on or off.'), () => {
    on = !on;
    toggle.textContent = on ? 'Hints on' : 'Hints off';
    toggle.setAttribute('aria-pressed', String(on));
    if (on) schedule(); else clear();
  }, 'learn-chip');
  toggle.setAttribute('aria-pressed', 'true');
  const close = btn('Dismiss', tip('Dismiss coach', 'Hide the coach for the rest of this game.'), () => stop(), 'learn-chip');
  const el = h('aside', { class: 'learn-coach', 'aria-label': 'Coach' }, h('span', { class: 'learn-coach-label', text: 'Coach' }), text, h('div', { class: 'learn-coach-actions' }, toggle, close));
  parent.append(el);

  function clear() {
    window.clearTimeout(timer);
    own.markers.clear(); own.markers.setSelected(null);
    text.textContent = on ? '' : 'Hints are off.';
  }

  function schedule() {
    clear();
    if (!on || stopped) return;
    const snap = s.controller.snapshot();
    const mode = snap.mode;
    if (!mode || snap.result) return;
    timer = window.setTimeout(() => {
      if (stopped || !on) return;
      const cur = s.controller.snapshot();
      if (!cur.mode || cur.result || cur.turn !== cur.mode.playerSide || cur.state === 'aiThinking') return;
      const sug = suggestMove(cur.fen);
      if (!sug) return;
      const target = new Rules(cur.fen).pieceAt(sug.to);
      own.markers.setSelected(sug.from);
      own.markers.show([{ square: sug.to, capture: !!target }]);
      const names: Record<string, string> = { pawn: 'pawn', rook: 'rook', knight: 'knight', bishop: 'bishop', queen: 'queen', king: 'king' };
      text.textContent = `Try ${names[sug.role]} ${sug.from} to ${sug.to}. ${sug.why}`;
    }, 600);
  }

  const offs = [
    s.bus.on('turn:start', (e) => { const m = s.controller.gameMode; if (m && e.side === m.playerSide) schedule(); else clear(); }),
    s.bus.on('move:resolved', () => clear()),
    s.bus.on('game:over', () => stop()),
    s.bus.on('game:start', () => { if (expectStart) { expectStart = false; return; } stop(); }),
  ];

  function stop() {
    if (stopped) return;
    stopped = true;
    window.clearTimeout(timer);
    offs.forEach((f) => f());
    gsap.ticker.remove(tick);
    own.dispose();
    el.remove();
  }
  return { stop, get active() { return !stopped; } };
}
