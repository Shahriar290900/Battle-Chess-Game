// Modal panels: settings, game over, promotion picker.
import type { AudioBus, PromotionRole, Settings, SettingsStore, Side } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import type { GameModeConfig } from '../contracts';
import type { GameEnd } from '../core/rules';
import { ICON, clear, h, pieceIcon, svg } from './dom';
import { REASON_LABEL, ROLE_LABEL, resultHeadline, sideName } from './glyphs';
import { segmented } from './menu';

export interface Panel {
  el: HTMLElement;
  readonly isOpen: boolean;
  open(): void;
  close(): void;
}

function modal(label: string, cls: string): { el: HTMLElement; card: HTMLElement } {
  const card = h('div', { class: `card ${cls}`, role: 'dialog', 'aria-modal': 'true', 'aria-label': label });
  const el = h('div', { class: 'overlay', hidden: true }, card);
  return { el, card };
}

// ------------------------------------------------------------------ settings
export function createSettingsPanel(settings: SettingsStore, audio: AudioBus): Panel {
  const { el, card } = modal('Settings', 'settings-card');
  let open = false;

  const row = (label: string, control: HTMLElement, hint?: string) =>
    h('div', { class: 'row' }, h('div', { class: 'row-text' }, h('span', { class: 'row-label', text: label }), hint ? h('span', { class: 'row-hint', text: hint }) : null), control);

  function toggle<K extends keyof Settings>(key: K, label: string, hint?: string) {
    const input = h('input', { type: 'checkbox', class: 'switch-input', role: 'switch' }) as HTMLInputElement;
    input.checked = Boolean(settings.get()[key]);
    input.addEventListener('change', () => settings.set(key, input.checked as Settings[K]));
    return row(label, h('label', { class: 'switch' }, input, h('span', { class: 'switch-track' }, h('span', { class: 'switch-thumb' }))), hint);
  }

  function slider<K extends keyof Settings>(key: K, label: string, min: number, max: number, step: number, fmt: (v: number) => string) {
    const out = h('span', { class: 'slider-out', text: fmt(Number(settings.get()[key])) });
    const input = h('input', { type: 'range', class: 'slider', min, max, step, 'aria-label': label }) as HTMLInputElement;
    input.value = String(settings.get()[key]);
    input.addEventListener('input', () => { const v = Number(input.value); out.textContent = fmt(v); settings.set(key, v as Settings[K]); });
    return row(label, h('div', { class: 'slider-wrap' }, input, out));
  }

  function choice<K extends keyof Settings, V extends string & Settings[K]>(key: K, label: string, options: Array<{ value: V; label: string }>, hint?: string) {
    const seg = segmented<V>(label, options, settings.get()[key] as V, (v) => settings.set(key, v as Settings[K]));
    return h('div', { class: 'row row-stack' }, h('div', { class: 'row-text' }, h('span', { class: 'row-label', text: label }), hint ? h('span', { class: 'row-hint', text: hint }) : null), seg.el);
  }

  const customRow = h('div', { class: 'row', hidden: true });
  function renderCustom() {
    clear(customRow);
    customRow.hidden = audio.hasMusic();
    if (customRow.hidden) return;
    const input = h('input', { type: 'file', accept: 'audio/*', class: 'file-input', 'aria-label': 'Load your own music' }) as HTMLInputElement;
    input.addEventListener('change', async () => {
      const f = input.files?.[0];
      if (!f) return;
      try { await audio.loadCustomTrack(f); } catch (e) { console.warn('[settings] custom track failed', e); }
      renderCustom();
    });
    customRow.append(h('div', { class: 'row-text' }, h('span', { class: 'row-label', text: 'Load your own music' }), h('span', { class: 'row-hint', text: 'Pick an audio file; it is kept on this device.' })), input);
  }

  const pct = (v: number) => `${Math.round(v * 100)}%`;
  function build() {
    clear(card);
    card.append(
      h('div', { class: 'card-head' }, h('h2', { class: 'card-title', text: 'Settings' }),
        h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Close settings', onClick: () => api.close() }, svg(ICON.close))),
      h('div', { class: 'card-scroll' },
        h('h3', { class: 'group', text: 'Battle' }),
        choice('cameraMode', 'Camera', [{ value: 'follow', label: 'Follow' }, { value: 'fixed', label: 'Fixed' }, { value: 'free', label: 'Free' }, { value: 'top', label: 'Top-down' }], 'Follow swings to the side to move (vs Computer it stays on your side).'),
        choice('captureMode', 'Capture scenes', [{ value: 'full', label: 'Full' }, { value: 'quick', label: 'Quick' }, { value: 'off', label: 'Off' }]),
        slider('animSpeed', 'Animation speed', 0.5, 2, 0.1, (v) => `${v.toFixed(1)}x`),
        choice('aiLevel', 'Computer strength', [{ value: 'easy', label: 'Easy' }, { value: 'medium', label: 'Medium' }, { value: 'hard', label: 'Hard' }, { value: 'master', label: 'Master' }], 'Applies to the next game.'),
        choice('playerSide', 'Your host vs Computer', [{ value: 'w', label: 'Emberhold' }, { value: 'b', label: 'Rime Host' }], 'Applies to the next game.'),
        h('h3', { class: 'group', text: 'Display' }),
        choice('quality', 'Quality', [{ value: 'auto', label: 'Auto' }, { value: 'high', label: 'High' }, { value: 'medium', label: 'Medium' }, { value: 'low', label: 'Low' }]),
        toggle('colorBlind', 'Colour-blind move marks', 'Blue diamonds and orange crossed rings.'),
        toggle('showMoveList', 'Show move list'),
        h('h3', { class: 'group', text: 'Sound' }),
        toggle('musicEnabled', 'Music'),
        slider('musicVolume', 'Music volume', 0, 1, 0.05, pct),
        slider('sfxVolume', 'Effects volume', 0, 1, 0.05, pct),
        customRow,
      ),
      h('div', { class: 'card-foot' }, h('button', { class: 'btn btn-primary', type: 'button', onClick: () => api.close() }, h('span', { class: 'btn-label', text: 'Done' }))),
    );
    renderCustom();
  }

  const api: Panel = {
    el,
    get isOpen() { return open; },
    open() { build(); open = true; el.hidden = false; },
    close() { open = false; el.hidden = true; },
  };
  return api;
}

// ------------------------------------------------------------------ game over
export interface GameOverPanel extends Panel {
  show(end: GameEnd, mode: GameModeConfig | null): void;
}

export function createGameOverPanel(handlers: { onRematch(): void; onMenu(): void }): GameOverPanel {
  const { el, card } = modal('Game over', 'over-card');
  let open = false;
  const api: GameOverPanel = {
    el,
    get isOpen() { return open; },
    show(end, mode) {
      const head = resultHeadline(end.result, mode);
      const win = end.result === '1/2-1/2' ? 'neutral' : end.result === '1-0' ? 'emberhold' : 'rime';
      card.dataset.faction = win;
      clear(card);
      card.append(
        h('p', { class: 'over-kicker', text: REASON_LABEL[end.reason] }),
        h('h2', { class: 'over-title', text: head.title }),
        h('p', { class: 'over-sub', text: head.sub }),
        h('div', { class: 'over-score', text: end.result }),
        h('div', { class: 'btn-col' },
          h('button', { class: 'btn btn-primary', type: 'button', onClick: () => { api.close(); handlers.onRematch(); } }, h('span', { class: 'btn-label', text: 'Rematch' })),
          h('button', { class: 'btn', type: 'button', onClick: () => { api.close(); handlers.onMenu(); } }, h('span', { class: 'btn-label', text: 'Menu' })),
          h('button', { class: 'btn btn-quiet', type: 'button', onClick: () => api.close() }, h('span', { class: 'btn-label', text: 'View board' }))),
      );
      open = true; el.hidden = false;
    },
    open() { el.hidden = false; open = true; },
    close() { open = false; el.hidden = true; },
  };
  return api;
}

// ------------------------------------------------------------------ promotion
export interface PromotionPicker extends Panel {
  choose(side: Side): Promise<PromotionRole | null>;
  cancel(): void;
}

const PROMO_ROLES: PromotionRole[] = ['queen', 'rook', 'bishop', 'knight'];

export function createPromotionPicker(): PromotionPicker {
  const { el, card } = modal('Choose promotion', 'promo-card');
  el.classList.add('overlay-light');
  let open = false;
  let resolve: ((r: PromotionRole | null) => void) | null = null;
  const done = (r: PromotionRole | null) => { const f = resolve; resolve = null; api.close(); f?.(r); };
  el.addEventListener('pointerdown', (e) => { if (e.target === el) done(null); });

  const api: PromotionPicker = {
    el,
    get isOpen() { return open; },
    choose(side) {
      resolve?.(null);
      const faction = SIDE_FACTION[side];
      card.dataset.faction = faction;
      clear(card);
      card.append(
        h('h2', { class: 'card-title small', text: `Raise your ${sideName(side)} pawn` }),
        h('div', { class: 'promo-grid' }, ...PROMO_ROLES.map((r) =>
          h('button', { class: 'promo-btn', type: 'button', 'aria-label': ROLE_LABEL[r], onClick: () => done(r) },
            pieceIcon(r, faction, 'promo-ic'), h('span', { class: 'promo-name', text: ROLE_LABEL[r] })))),
        h('button', { class: 'btn btn-quiet', type: 'button', onClick: () => done(null) }, h('span', { class: 'btn-label', text: 'Cancel move' })),
      );
      open = true; el.hidden = false;
      return new Promise<PromotionRole | null>((r) => { resolve = r; });
    },
    cancel() { if (open) done(null); },
    open() {},
    close() { open = false; el.hidden = true; },
  };
  return api;
}
