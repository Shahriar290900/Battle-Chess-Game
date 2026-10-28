// Settings in the reference layout: a dark category column (General / Video / Audio / Gameplay / Controls / Back) and
// a right panel of `label  << < value > >>` rows. Everything works with mouse, touch and keyboard (arrows change the
// focused row, Q/E switch category). Every row carries a tooltip explaining the option and its performance cost.
import type { AudioBus, GraphicsSettings, HighlightStyle, QualityTier, Settings, SettingsStore } from '../contracts';
import { AI_ELO_MAX, AI_ELO_MIN, DEFAULT_SETTINGS } from '../contracts';
import { tierForElo } from '../core/ai/strength';
import { AI_ELO_STEP, choosePreset, patchGraphics } from '../core/settings';
import { h } from './dom';
import { actionRow, backHint, button, optionRow, rangeRow, toggleRow, type Row } from './controls';
import type { Screen } from './screen';
import { setTooltipsEnabled, tooltipsEnabled } from './tooltip';

export interface SettingsDeps {
  settings: SettingsStore;
  audio: AudioBus;
  learnAvailable(): boolean;
  replayLesson(): void;
  exit(): void;
}

type Cat = 'general' | 'video' | 'audio' | 'gameplay' | 'controls';
const CATS: Array<{ id: Cat; label: string; tip: string }> = [
  { id: 'general', label: 'General', tip: 'General|Hints, tooltips and the intro lesson.' },
  { id: 'video', label: 'Video', tip: 'Video|Quality presets and performance options.' },
  { id: 'audio', label: 'Audio', tip: 'Audio|Music and sound-effect volume.' },
  { id: 'gameplay', label: 'Gameplay', tip: 'Gameplay|Animations, camera, highlights and the computer.' },
  { id: 'controls', label: 'Controls', tip: 'Controls|How to play with mouse, touch and keyboard.' },
];

const HL_TEXT: Record<HighlightStyle, string> = {
  glow: 'A soft pool of light on the tile.',
  brackets: 'Four crisp corner brackets frame the tile.',
  tint: 'A flat coloured wash over the whole tile.',
  runes: 'A glowing rune ring is drawn on the tile.',
};

export function createSettings(d: SettingsDeps): Screen & { open(cat?: Cat): void; readonly isOpen: boolean } {
  const { settings: S, audio } = d;
  const g = () => S.get().graphics;
  const gfx = <K extends keyof GraphicsSettings>(k: K, v: GraphicsSettings[K]) => patchGraphics(S, { [k]: v } as Partial<GraphicsSettings>);
  const set = <K extends keyof Settings>(k: K) => (v: Settings[K]) => S.set(k, v);
  const pct = (v: number) => `${Math.round(v * 100)}%`;

  const rowsByCat: Record<Cat, Row[]> = { general: [], video: [], audio: [], gameplay: [], controls: [] };
  const all: Row[] = [];
  const add = (c: Cat, r: Row) => { rowsByCat[c].push(r); all.push(r); return r; };

  const resetAll = () => {
    const D = DEFAULT_SETTINGS;
    for (const k of Object.keys(D) as Array<keyof Settings>) {
      if (k === 'tutorialSeen' || k === 'graphics' || k === 'quality') continue;
      (S.set as (k: keyof Settings, v: unknown) => void)(k, D[k]);
    }
    S.set('quality', 'auto');
    S.set('graphics', { ...D.graphics });
    setTooltipsEnabled(true);
    refresh();
  };

  // ---- General
  add('general', toggleRow('Show tooltips', tooltipsEnabled, setTooltipsEnabled, undefined, 'Show tooltips|Small help panels on hover, focus or long-press. No performance cost.'));
  add('general', toggleRow('Offer the intro lesson', () => !S.get().tutorialSeen, (v) => S.set('tutorialSeen', !v), 'On the main menu', 'Intro lesson prompt|Shows the "New to the field?" note on the main menu.'));
  if (d.learnAvailable()) add('general', actionRow('Replay the intro lesson', 'Begin', d.replayLesson, { tip: 'Intro lesson|A short guided tour of the pieces on the real board.' }));

  // ---- Video
  const presetValue = (): QualityTier | 'auto' | 'custom' => (g().preset === 'custom' ? 'custom' : S.get().quality === 'auto' ? 'auto' : g().preset);
  add('video', optionRow<QualityTier | 'auto' | 'custom'>('Preset', [
    { value: 'auto', label: 'Auto' }, { value: 'low', label: 'Low' }, { value: 'medium', label: 'Medium' }, { value: 'high', label: 'High' }, { value: 'custom', label: 'Custom' },
  ], presetValue, (v) => (v === 'custom' ? patchGraphics(S, { preset: 'custom' }) : choosePreset(S, v)), undefined,
  'Quality preset|Auto picks for your device. Low suits phones and older laptops, High needs a dedicated GPU. Changing any option below makes it Custom.'));
  add('video', rangeRow('Resolution scale', 0.5, 1, 0.05, () => g().resolutionScale, (v) => gfx('resolutionScale', v), pct,
    'Resolution scale|Renders fewer pixels and stretches them. Lower is the biggest speed-up on weak GPUs and phones.'));
  add('video', optionRow<GraphicsSettings['shadows']>('Shadows', [{ value: 'off', label: 'Off' }, { value: 'low', label: 'Low' }, { value: 'high', label: 'High' }], () => g().shadows, (v) => gfx('shadows', v), undefined,
    'Shadows|Soft shadows under pieces. Off is fastest on older laptops and phones; High is the most demanding.'));
  add('video', toggleRow('Bloom', () => g().bloom, (v) => gfx('bloom', v), undefined, 'Bloom|A soft glow around bright flames and sparks. Moderate cost; turn off for speed.'));
  add('video', toggleRow('Anti-aliasing', () => g().antialias, (v) => gfx('antialias', v), undefined, 'Anti-aliasing|Smooths jagged edges (SMAA). Small cost on desktop, noticeable on integrated graphics.'));
  add('video', optionRow<GraphicsSettings['particles']>('Particles', [{ value: 'low', label: 'Low' }, { value: 'medium', label: 'Medium' }, { value: 'high', label: 'High' }], () => g().particles, (v) => gfx('particles', v), undefined,
    'Particles|How many sparks, embers and shards fly during fights. Higher looks richer and costs more.'));
  add('video', optionRow<GraphicsSettings['physics']>('Physics', [{ value: 'simple', label: 'Simple' }, { value: 'full', label: 'Full' }], () => g().physics, (v) => gfx('physics', v), undefined,
    'Physics|Full lets debris collide with pieces and each other. Simple only bounces on the floor and is cheaper.'));
  add('video', toggleRow('Ambient effects', () => g().ambient, (v) => gfx('ambient', v), undefined, 'Ambient effects|Drifting motes, flickering braziers and fog. Purely cosmetic; off saves a little.'));
  add('video', toggleRow('Secondary motion', () => g().secondaryMotion, (v) => gfx('secondaryMotion', v), undefined, 'Secondary motion|Cloaks, banners and pieces sway and recoil. Off saves CPU on phones.'));
  add('video', optionRow<30 | 60 | 0>('Frame rate cap', [{ value: 30, label: '30' }, { value: 60, label: '60' }, { value: 0, label: 'Unlimited' }], () => g().fpsCap, (v) => gfx('fpsCap', v), undefined,
    'Frame rate cap|30 saves battery and heat. 60 is smooth. Unlimited follows your display.'));
  add('video', toggleRow('Show FPS', () => g().showFps, (v) => gfx('showFps', v), undefined, 'Show FPS|A small frames-per-second counter in the corner.'));

  // ---- Audio
  const file = h('input', { type: 'file', accept: 'audio/*', hidden: true, 'aria-label': 'Load your own music' }) as HTMLInputElement;
  let trackNote = '';
  file.addEventListener('change', async () => {
    const f = file.files?.[0];
    if (!f) return;
    try { await audio.loadCustomTrack(f); trackNote = `Loaded: ${f.name}`; } catch { trackNote = 'That file could not be played.'; }
    file.value = '';
    refresh();
  });
  add('audio', toggleRow('Music', () => S.get().musicEnabled, set('musicEnabled'), undefined, 'Music|Turns the background score on or off.'));
  add('audio', rangeRow('Music volume', 0, 1, 0.05, () => S.get().musicVolume, set('musicVolume'), pct, 'Music volume|How loud the score plays.'));
  add('audio', rangeRow('Effects volume', 0, 1, 0.05, () => S.get().sfxVolume, set('sfxVolume'), pct, 'Effects volume|Moves, clashes, shattering and interface sounds.'));
  add('audio', actionRow('Your own music', 'Load a track', () => file.click(), { note: () => trackNote || (audio.hasMusic() ? 'A theme is loaded' : 'No track loaded'), tip: 'Your own music|Pick an audio file from your device. It stays on this device.' }));

  // ---- Gameplay
  add('gameplay', optionRow<Settings['captureMode']>('Animations', [{ value: 'full', label: 'Full' }, { value: 'quick', label: 'Quick' }, { value: 'off', label: 'Off' }], () => S.get().captureMode, set('captureMode'), undefined,
    'Animations|Full plays every cinematic capture. Quick shortens them. Off moves pieces instantly and is fastest.'));
  add('gameplay', rangeRow('Animation speed', 0.5, 2, 0.1, () => S.get().animSpeed, set('animSpeed'), (v) => `${v.toFixed(1)}x`, 'Animation speed|Multiplies the speed of piece movement and camera swings.'));
  add('gameplay', optionRow<Settings['cameraMode']>('Camera', [{ value: 'follow', label: 'Follow turn' }, { value: 'fixed', label: 'Fixed' }, { value: 'free', label: 'Free orbit' }, { value: 'top', label: 'Top-down' }], () => S.get().cameraMode, set('cameraMode'), undefined,
    'Camera|Follow turn swings to the side to move. Fixed stays behind your pieces. Free lets you orbit. Top-down looks straight down.'));
  add('gameplay', toggleRow('Rotate board for two players', () => S.get().cameraMode === 'follow', (v) => S.set('cameraMode', v ? 'follow' : 'fixed'), undefined,
    'Rotate board|In pass-and-play the camera turns to face each player. Same as Camera: Follow turn.'));
  add('gameplay', toggleRow('Move list', () => S.get().showMoveList, set('showMoveList'), undefined, 'Move list|A slim journal of moves beside the board.'));
  add('gameplay', toggleRow('Colour-blind mode', () => S.get().colorBlind, set('colorBlind'), undefined, 'Colour-blind mode|Marks captures and checks with shapes as well as colour.'));
  add('gameplay', rangeRow('Computer strength (Elo)', AI_ELO_MIN, AI_ELO_MAX, AI_ELO_STEP, () => S.get().aiElo, set('aiElo'), (v) => `${v} \u00b7 ${tierForElo(v).name}`,
    'Computer strength|Rating of the computer opponent, 400 to 3000 in steps of 50 (Squire 400, Footman 800, Knight 1200, Captain 1600, Champion 2000, Warlord 2400, Grandmaster 2800). Higher ratings think longer and are slower on weak devices. Used for the next game you start.'));
  const styles: Array<{ value: HighlightStyle; label: string }> = [{ value: 'glow', label: 'Glow' }, { value: 'brackets', label: 'Brackets' }, { value: 'tint', label: 'Tint' }, { value: 'runes', label: 'Runes' }];
  add('gameplay', optionRow('Tile highlights', styles, () => S.get().highlightStyle, set('highlightStyle'), undefined,
    'Tile highlights|How legal moves and the selected piece are marked on the board. Glow: soft light. Brackets: corner marks. Tint: flat wash. Runes: glowing rings.'));
  add('gameplay', rangeRow('Highlight strength', 0.2, 1, 0.1, () => S.get().highlightIntensity, set('highlightIntensity'), pct, 'Highlight strength|How strongly tiles are marked. Raise it if they are hard to see.'));
  const tile = h('span', { class: 'tile glow' }, h('i'));
  const previewText = h('span', { text: HL_TEXT.glow });
  const preview = h('div', { class: 'preview' }, tile, previewText);
  const previewRow: Row = {
    el: preview,
    refresh() {
      const st = S.get().highlightStyle;
      if (tile.className !== `tile ${st}`) { tile.className = `tile ${st}`; previewText.textContent = HL_TEXT[st]; }
      (tile.firstElementChild as HTMLElement).style.opacity = String(0.35 + S.get().highlightIntensity * 0.65);
    },
  };
  add('gameplay', previewRow);

  // ---- Controls (text)
  const group = (title: string, items: Array<[string, string]>) => h('div', {}, h('h3', { text: title }), h('ul', {}, ...items.map(([k, v]) => h('li', {}, h('b', { text: k }), h('span', { text: v })))));
  const controls = h('div', { class: 'ctl-grid' },
    group('Mouse', [['Click', 'Select a piece, then click a lit tile to move'], ['Drag', 'Drag a piece onto a lit tile'], ['Right-drag', 'Orbit the camera (Free camera)'], ['Wheel', 'Zoom'], ['Click', 'Skip a fight animation']]),
    group('Touch', [['Tap', 'Select a piece, tap a lit tile to move'], ['Drag', 'Optional: drag a piece to a tile'], ['Swipe', 'Orbit (Free camera)'], ['Pinch', 'Zoom'], ['Hold', 'Show a tooltip'], ['Tap', 'Skip a fight animation']]),
    group('Keyboard', [['Arrows', 'Move between buttons; change a value'], ['Enter', 'Choose'], ['Esc', 'Back / pause'], ['Q  E', 'Switch settings tabs'], ['U', 'Undo'], ['J', 'Toggle the move list'], ['Space', 'Skip a fight animation']]));

  // ---- layout
  const panels: Record<Cat, HTMLElement> = {} as Record<Cat, HTMLElement>;
  const rowsHost = h('div', { class: 'rows scroll-y' });
  for (const c of CATS) {
    const p = h('div', { class: 'cat-panel', role: 'tabpanel', hidden: true });
    if (c.id === 'controls') p.append(controls);
    else {
      p.append(...rowsByCat[c.id].map((r) => r.el));
      p.append(h('div', { class: 'reset-wrap' }, button('Reset all to default', resetAll, { cls: 'small', tip: 'Reset all|Restores every setting to its default value.' })));
    }
    panels[c.id] = p;
    rowsHost.append(p);
  }
  rowsHost.append(file);
  const kick = h('p', { class: 'kick', text: 'General' });
  const catBtns = new Map<Cat, HTMLButtonElement>();
  let cat: Cat = 'general';
  const choose = (c: Cat) => {
    cat = c;
    for (const x of CATS) { panels[x.id].hidden = x.id !== c; catBtns.get(x.id)!.classList.toggle('sel', x.id === c); catBtns.get(x.id)!.setAttribute('aria-selected', String(x.id === c)); catBtns.get(x.id)!.toggleAttribute('data-autofocus', x.id === c); }
    kick.textContent = CATS.find((x) => x.id === c)!.label;
    rowsHost.scrollTop = 0;
    refresh();
  };
  const cats = h('div', { class: 'cats', role: 'tablist' });
  for (const c of CATS) {
    const b = button(c.label, () => choose(c.id), { tip: c.tip });
    b.setAttribute('role', 'tab');
    catBtns.set(c.id, b);
    cats.append(b);
  }
  cats.append(h('div', { class: 'spacer' }), (() => { const b = button('Back', () => d.exit(), { cls: 'back-cat', tip: 'Back|Return to the previous screen.', tipKey: 'Esc' }); return b; })());
  const el = h('div', { class: 'scr settings in', role: 'dialog', 'aria-label': 'Settings' },
    h('aside', { class: 'side' }, h('h2', { class: 'ttl', text: 'Settings' }), cats),
    h('section', { class: 'panel' }, h('div', { class: 'hd' }, kick, h('h2', { class: 'ttl', text: 'Settings' }), h('div', { class: 'rule' })), rowsHost),
    backHint(() => d.exit()));

  function refresh() { for (const r of all) r.refresh(); }
  let open = false;
  S.subscribe(() => { if (open) refresh(); });
  window.addEventListener('keydown', (e) => {
    if (!open || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
    const i = CATS.findIndex((c) => c.id === cat);
    const k = e.key.toLowerCase();
    if (k === 'q' || e.key === 'PageUp') { choose(CATS[(i + CATS.length - 1) % CATS.length].id); e.preventDefault(); }
    else if (k === 'e' || e.key === 'PageDown') { choose(CATS[(i + 1) % CATS.length].id); e.preventDefault(); }
  });

  choose('general');
  const api = {
    el,
    get isOpen() { return open; },
    open(c?: Cat) { if (c) choose(c); },
    onShow() { open = true; refresh(); },
    back() { open = false; d.exit(); return true; },
    /** Called by the stack when the screen is hidden. */
    onHide() { open = false; },
  };
  return api;
}
