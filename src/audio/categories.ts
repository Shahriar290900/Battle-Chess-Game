// Audio categories: Music / Effects / Ambience / Interface, each with its own persisted gain.
// `Settings` only carries musicVolume / sfxVolume, so the finer split lives here (localStorage) and multiplies
// on top of them:   music   = musicVolume x music category
//                   others  = sfxVolume   x category
// The module has no WebAudio dependency; the bus subscribes with onCategoryChange().

export type AudioCategory = 'music' | 'effects' | 'ambience' | 'interface';
export const AUDIO_CATEGORIES: readonly AudioCategory[] = ['music', 'effects', 'ambience', 'interface'];
export type SfxCategory = Exclude<AudioCategory, 'music'>;

export const CATEGORY_LABEL: Record<AudioCategory, string> = {
  music: 'Music', effects: 'Effects', ambience: 'Ambience', interface: 'Interface',
};

/**
 * Which category a sample key belongs to.
 *  - interface: every ui:* click / hover / page cue and the loading chime
 *  - ambience: locomotion and the world's texture (footsteps, hooves, grinding slides, landings' dust, debris)
 *  - effects: everything else (combat, spells, shields, armour, shatters, fanfares)
 */
export function categoryOf(key: string): SfxCategory {
  if (key.startsWith('ui:') || key.startsWith('loading:')) return 'interface';
  if (key.startsWith('move:step') || key.startsWith('step:') || key.startsWith('gallop:') || key.startsWith('slide:') || key.startsWith('debris:')) return 'ambience';
  return 'effects';
}

const STORAGE_KEY = 'battle-chess.audio.categories';
const clamp01 = (v: number) => (Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 1);

const volumes: Record<AudioCategory, number> = { music: 1, effects: 1, ambience: 1, interface: 1 };
const listeners = new Set<(cat: AudioCategory, v: number) => void>();
let loaded = false;

function load(): void {
  if (loaded) return;
  loaded = true;
  try {
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) return;
    const o = JSON.parse(raw) as Partial<Record<AudioCategory, unknown>>;
    for (const c of AUDIO_CATEGORIES) if (typeof o[c] === 'number') volumes[c] = clamp01(o[c] as number);
  } catch { /* private mode / corrupt value: keep defaults */ }
}

function persist(): void {
  try { if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, JSON.stringify(volumes)); } catch { /* ignore */ }
}

/** 0..1 multiplier for a category (default 1). */
export function getCategoryVolume(cat: AudioCategory): number {
  load();
  return volumes[cat] ?? 1;
}

/** Set + persist a category multiplier (0..1) and notify every live bus. */
export function setCategoryVolume(cat: AudioCategory, v: number): void {
  load();
  if (!AUDIO_CATEGORIES.includes(cat)) return;
  volumes[cat] = clamp01(v);
  persist();
  for (const fn of listeners) fn(cat, volumes[cat]);
}

export function onCategoryChange(fn: (cat: AudioCategory, v: number) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Test hook: forget the in-memory cache so the next read hits storage again. */
export function _resetCategoriesForTest(): void {
  loaded = false;
  for (const c of AUDIO_CATEGORIES) volumes[c] = 1;
  listeners.clear();
}
