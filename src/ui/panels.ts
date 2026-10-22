// Modal panels in the physical style: settings (hi-fi cabinet with brass knobs, toggles and rotary selectors),
// game over (wax-sealed parchment on a wooden board) and the promotion picker (wooden tokens on a tray).
import type { AudioBus, GameModeConfig, GraphicsSettings, PromotionRole, QualityTier, SettingsStore, Side } from '../contracts';
import { SIDE_FACTION } from '../contracts';
import { choosePreset, patchGraphics } from '../core/settings';
import type { GameEnd } from '../core/rules';
import { ICON, clear, h, pieceIcon, svg } from './dom';
import { REASON_LABEL, ROLE_LABEL, resultHeadline } from './glyphs';
import { createKnob, createSelector, createToggle, plaque } from './controls';
import { createLcd } from './lcd';

export interface Panel { el: HTMLElement; readonly isOpen: boolean; open(): void; close(): void }

function modal(label: string, cls: string): { el: HTMLElement; card: HTMLElement } {
  const card = h('div', { class: `card ${cls}`, role: 'dialog', 'aria-modal': 'true', 'aria-label': label });
  return { el: h('div', { class: 'overlay', hidden: true }, card), card };
}

// ------------------------------------------------------------------ settings (hi-fi cabinet)
export function createSettingsPanel(settings: SettingsStore, audio: AudioBus): Panel {
  const { el, card } = modal('Settings', 'cabinet-radio');
  let open = false;
  let refreshers: Array<() => void> = [];

  function build() {
    clear(card);
    refreshers = [];
    const lcd = createLcd(30, 3, 'amber', 'radio-lcd');
    const show = (name: string, value: string) => lcd.set([`${name}`, `${value}`, `PRESET ${settings.get().graphics.preset.toUpperCase()}`]);
    const gfx = <K extends keyof GraphicsSettings>(k: K, v: GraphicsSettings[K]) => patchGraphics(settings, { [k]: v } as Partial<GraphicsSettings>);
    const g = () => settings.get().graphics;

    const knob = (label: string, lcdName: string, min: number, max: number, step: number, get: () => number, set: (v: number) => void, fmt: (v: number) => string) => {
      const k = createKnob({ label, min, max, step, value: get(), format: fmt, onInput: (v, t) => { set(v); show(lcdName, t); } });
      refreshers.push(() => k.set(get()));
      return k.el;
    };
    const toggle = (label: string, get: () => boolean, set: (v: boolean) => void) => {
      const t = createToggle({ label, value: get(), onChange: (v) => { set(v); show(label, v ? 'ON' : 'OFF'); } });
      refreshers.push(() => t.set(get()));
      return t.el;
    };
    const sel = <T extends string | number>(label: string, options: Array<{ value: T; label: string }>, get: () => T, set: (v: T) => void) => {
      const s = createSelector<T>({ label, options, value: get(), onChange: (v, t) => { set(v); show(label, t); } });
      refreshers.push(() => s.set(get()));
      return s.el;
    };

    const pct = (v: number) => `${Math.round(v * 100)}%`;
    const presetValue = (): QualityTier | 'auto' => (settings.get().quality === 'auto' ? 'auto' : (settings.get().quality as QualityTier));

    const file = h('input', { type: 'file', accept: 'audio/*', class: 'file-input', 'aria-label': 'Load your own music' }) as HTMLInputElement;
    file.addEventListener('change', async () => {
      const f = file.files?.[0];
      if (!f) return;
      try { await audio.loadCustomTrack(f); show('TAPE', 'LOADED'); } catch { show('TAPE', 'FAILED'); }
    });
    const tape = audio.hasMusic() ? null : h('label', { class: 'tape' }, h('span', { text: 'Load your own music' }), file);

    card.append(
      h('div', { class: 'radio-head' }, h('h2', { class: 'card-title', text: 'Settings' }),
        h('button', { class: 'pbtn small', type: 'button', title: 'Close', 'aria-label': 'Close settings', onClick: () => api.close() }, h('span', { class: 'pbtn-cap' }, svg(ICON.close)))),
      h('div', { class: 'faceplate' },
        lcd.el,
        h('div', { class: 'ctl-row knobs' },
          knob('Music', 'MUSIC VOLUME', 0, 1, 0.05, () => settings.get().musicVolume, (v) => settings.set('musicVolume', v), pct),
          knob('Effects', 'EFFECTS VOLUME', 0, 1, 0.05, () => settings.get().sfxVolume, (v) => settings.set('sfxVolume', v), pct),
          knob('Anim speed', 'ANIMATION SPEED', 0.5, 2, 0.1, () => settings.get().animSpeed, (v) => settings.set('animSpeed', v), (v) => `${v.toFixed(1)}X`),
          knob('Resolution', 'RESOLUTION SCALE', 0.5, 1, 0.05, () => g().resolutionScale, (v) => gfx('resolutionScale', v), pct)),
      ),
      h('div', { class: 'radio-scroll' },
        h('h3', { class: 'group', text: 'Play' }),
        h('div', { class: 'ctl-row selectors' },
          sel('Camera', [{ value: 'follow', label: 'FOLLOW' }, { value: 'fixed', label: 'FIXED' }, { value: 'free', label: 'FREE' }, { value: 'top', label: 'TOP-DOWN' }], () => settings.get().cameraMode, (v) => settings.set('cameraMode', v)),
          sel('Animations', [{ value: 'full', label: 'FULL' }, { value: 'quick', label: 'QUICK' }, { value: 'off', label: 'OFF' }], () => settings.get().captureMode, (v) => settings.set('captureMode', v)),
          sel('Computer', [{ value: 'easy', label: 'EASY' }, { value: 'medium', label: 'MEDIUM' }, { value: 'hard', label: 'HARD' }, { value: 'master', label: 'MASTER' }], () => settings.get().aiLevel, (v) => settings.set('aiLevel', v))),
        h('div', { class: 'ctl-row switches' },
          toggle('Rotate board', () => settings.get().cameraMode === 'follow', (v) => settings.set('cameraMode', v ? 'follow' : 'fixed')),
          toggle('Move list', () => settings.get().showMoveList, (v) => settings.set('showMoveList', v)),
          toggle('Colour-blind', () => settings.get().colorBlind, (v) => settings.set('colorBlind', v)),
          toggle('Music', () => settings.get().musicEnabled, (v) => settings.set('musicEnabled', v))),
        h('h3', { class: 'group', text: 'Graphics' }),
        h('div', { class: 'ctl-row selectors' },
          sel('Preset', [{ value: 'auto', label: 'AUTO' }, { value: 'low', label: 'LOW' }, { value: 'medium', label: 'MEDIUM' }, { value: 'high', label: 'HIGH' }], presetValue, (v) => choosePreset(settings, v)),
          sel('Shadows', [{ value: 'off', label: 'OFF' }, { value: 'low', label: 'LOW' }, { value: 'high', label: 'HIGH' }], () => g().shadows, (v) => gfx('shadows', v)),
          sel('Particles', [{ value: 'low', label: 'LOW' }, { value: 'medium', label: 'MEDIUM' }, { value: 'high', label: 'HIGH' }], () => g().particles, (v) => gfx('particles', v)),
          sel('Physics', [{ value: 'simple', label: 'SIMPLE' }, { value: 'full', label: 'FULL' }], () => g().physics, (v) => gfx('physics', v)),
          sel('FPS cap', [{ value: 30, label: '30' }, { value: 60, label: '60' }, { value: 0, label: 'UNLIMITED' }], () => g().fpsCap, (v) => gfx('fpsCap', v))),
        h('div', { class: 'ctl-row switches' },
          toggle('Bloom', () => g().bloom, (v) => gfx('bloom', v)),
          toggle('Anti-alias', () => g().antialias, (v) => gfx('antialias', v)),
          toggle('Ambient', () => g().ambient, (v) => gfx('ambient', v)),
          toggle('Secondary motion', () => g().secondaryMotion, (v) => gfx('secondaryMotion', v)),
          toggle('Show FPS', () => g().showFps, (v) => gfx('showFps', v))),
        tape),
      h('div', { class: 'radio-foot' }, plaque('Done', () => api.close())),
    );
    lcd.set(['SETTINGS', 'TURN A KNOB OR FLIP A SWITCH', `PRESET ${g().preset.toUpperCase()}`]);
  }

  settings.subscribe((_, key) => { if (open && (key === 'graphics' || key === 'quality' || key === 'cameraMode' || key === 'showMoveList')) refreshers.forEach((r) => r()); });
  const api: Panel = {
    el,
    get isOpen() { return open; },
    open() { build(); open = true; el.hidden = false; },
    close() { open = false; el.hidden = true; },
  };
  return api;
}

// ------------------------------------------------------------------ game over (wax-sealed parchment)
export interface GameOverPanel extends Panel { show(end: GameEnd, mode: GameModeConfig | null): void }

export function createGameOverPanel(handlers: { onRematch(): void; onMenu(): void }): GameOverPanel {
  const { el, card } = modal('Game over', 'parchment-card');
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
        h('div', { class: 'parchment' },
          h('p', { class: 'over-kicker', text: REASON_LABEL[end.reason] }),
          h('h2', { class: 'over-title', text: head.title }),
          h('p', { class: 'over-sub', text: head.sub }),
          h('div', { class: 'over-score', text: end.result }),
          h('div', { class: 'wax', 'aria-hidden': 'true' }, h('span', { text: win === 'neutral' ? '=' : win === 'emberhold' ? 'E' : 'R' }))),
        h('div', { class: 'board-actions' },
          plaque('Rematch', () => { api.close(); handlers.onRematch(); }),
          plaque('Menu', () => { api.close(); handlers.onMenu(); }),
          plaque('View board', () => api.close(), 'quiet')));
      open = true; el.hidden = false;
    },
    open() { el.hidden = false; open = true; },
    close() { open = false; el.hidden = true; },
  };
  return api;
}

// ------------------------------------------------------------------ promotion (wooden tokens)
export interface PromotionPicker extends Panel { choose(side: Side): Promise<PromotionRole | null>; cancel(): void }
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
        h('h2', { class: 'card-title small', text: 'Promote to' }),
        h('div', { class: 'promo-grid' }, ...PROMO_ROLES.map((r) =>
          h('button', { class: 'token', type: 'button', 'aria-label': ROLE_LABEL[r], onClick: () => done(r) },
            h('span', { class: 'token-face' }, pieceIcon(r, faction, 'promo-ic')), h('span', { class: 'token-name', text: ROLE_LABEL[r] })))),
        plaque('Cancel move', () => done(null), 'quiet'));
      open = true; el.hidden = false;
      return new Promise<PromotionRole | null>((r) => { resolve = r; });
    },
    cancel() { if (open) done(null); },
    open() {},
    close() { open = false; el.hidden = true; },
  };
  return api;
}
