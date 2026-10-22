// Main menu: Resume / Play vs Computer (side + difficulty) / Two Players / Settings / music toggle.
import type { AiLevel, GameModeConfig, SettingsStore, Side } from '../contracts';
import { FACTION_NAME } from '../contracts';
import type { GameController } from '../core/game';
import { clear, h } from './dom';
import { LEVEL_LABEL } from './glyphs';

export interface MenuHandlers {
  onStart(config: GameModeConfig): void;
  onResume(): void;
  onSettings(): void;
  onResign(): void;
}

export interface Menu {
  el: HTMLElement;
  readonly isOpen: boolean;
  open(): void;
  close(): void;
  /** Android back / Esc: returns true if it consumed the event. */
  back(): boolean;
}

export function segmented<T extends string>(name: string, options: Array<{ value: T; label: string; sub?: string }>, value: T, onChange: (v: T) => void): { el: HTMLElement; set(v: T): void } {
  const el = h('div', { class: 'segmented', role: 'radiogroup', 'aria-label': name });
  const btns = new Map<T, HTMLButtonElement>();
  const set = (v: T) => btns.forEach((b, k) => { b.setAttribute('aria-checked', String(k === v)); b.classList.toggle('on', k === v); });
  for (const o of options) {
    const b = h('button', { class: 'seg', type: 'button', role: 'radio', onClick: () => { set(o.value); onChange(o.value); } },
      h('span', { class: 'seg-label', text: o.label }), o.sub ? h('span', { class: 'seg-sub', text: o.sub }) : null);
    btns.set(o.value, b);
    el.append(b);
  }
  set(value);
  return { el, set };
}

export function createMenu(controller: GameController, settings: SettingsStore, hd: MenuHandlers): Menu {
  const root = h('div', { class: 'menu-view' });
  const aiView = h('div', { class: 'menu-view', hidden: true });
  const card = h('div', { class: 'card menu-card', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Main menu' });
  const el = h('div', { class: 'overlay menu-overlay', hidden: true }, card);
  let open = false;
  let view: 'root' | 'ai' = 'root';

  const title = h('div', { class: 'title-block' },
    h('h1', { class: 'title', text: 'Battle Chess' }),
    h('p', { class: 'subtitle', text: 'Emberhold versus the Rime Host' }));
  card.append(title, root, aiView);

  const big = (label: string, cls: string, onClick: () => void, sub?: string) =>
    h('button', { class: `btn row-btn ${cls}`, type: 'button', onClick }, h('span', { class: 'btn-label', text: label }), sub ? h('span', { class: 'btn-sub', text: sub }) : null);

  function renderRoot() {
    clear(root);
    const s = controller.snapshot();
    const running = !!s.mode && s.state !== 'menu' && s.state !== 'boot' && s.state !== 'loading';
    const live = running && !s.result;
    if (running) root.append(big(s.result ? 'View Board' : 'Resume', 'btn-primary', () => { api.close(); hd.onResume(); }));
    root.append(
      big('Play vs Computer', running ? '' : 'btn-primary', () => show('ai')),
      big('Two Players', '', () => { api.close(); hd.onStart({ kind: 'hotseat', playerSide: 'w', aiLevel: settings.get().aiLevel }); }, 'Pass and play'),
    );
    root.append(
      h('button', { class: 'btn row-btn', type: 'button', onClick: () => { hd.onSettings(); } }, h('span', { class: 'btn-label', text: 'Settings' })),
      musicButton(),
    );
    if (live) root.append(h('button', { class: 'btn row-btn btn-danger', type: 'button', onClick: () => { api.close(); hd.onResign(); } }, h('span', { class: 'btn-label', text: 'Resign' })));
  }

  function musicButton() {
    const on = settings.get().musicEnabled;
    const b = h('button', { class: 'btn row-btn', type: 'button', 'aria-pressed': String(on),
      onClick: () => { settings.set('musicEnabled', !settings.get().musicEnabled); renderRoot(); } },
      h('span', { class: 'btn-label', text: 'Music' }), h('span', { class: 'btn-sub', text: on ? 'On' : 'Off' }));
    return b;
  }

  function renderAi() {
    clear(aiView);
    const st = settings.get();
    let side: Side = st.playerSide;
    let level: AiLevel = st.aiLevel;
    const sideSeg = segmented<Side>('Your host', [
      { value: 'w', label: FACTION_NAME.emberhold, sub: 'White' },
      { value: 'b', label: FACTION_NAME.rime, sub: 'Black' },
    ], side, (v) => { side = v; });
    const levelSeg = segmented<AiLevel>('Difficulty', (Object.keys(LEVEL_LABEL) as AiLevel[]).map((l) => ({ value: l, label: LEVEL_LABEL[l] })), level, (v) => { level = v; });
    aiView.append(
      h('h2', { class: 'section', text: 'Your host' }), sideSeg.el,
      h('h2', { class: 'section', text: 'Difficulty' }), levelSeg.el,
      big('Begin', 'btn-primary', () => {
        settings.set('playerSide', side);
        settings.set('aiLevel', level);
        api.close();
        hd.onStart({ kind: 'vs-ai', playerSide: side, aiLevel: level });
      }),
      h('button', { class: 'btn row-btn', type: 'button', onClick: () => show('root') }, h('span', { class: 'btn-label', text: 'Back' })),
    );
  }

  function show(v: 'root' | 'ai') {
    view = v;
    root.hidden = v !== 'root';
    aiView.hidden = v !== 'ai';
    if (v === 'root') renderRoot(); else renderAi();
  }

  const api: Menu = {
    el,
    get isOpen() { return open; },
    open() { open = true; el.hidden = false; show('root'); (card.querySelector('button') as HTMLElement | null)?.focus({ preventScroll: true }); },
    close() { open = false; el.hidden = true; },
    back() {
      if (!open) return false;
      if (view === 'ai') { show('root'); return true; }
      const s = controller.snapshot();
      if (s.mode && s.state !== 'menu') { api.close(); hd.onResume(); return true; }
      return false;
    },
  };
  settings.subscribe((_, k) => { if (open && view === 'root' && k === 'musicEnabled') renderRoot(); });
  return api;
}
