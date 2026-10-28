// SettingsStore persisted to localStorage. Every storage access is wrapped in try/catch
// (private windows, blocked storage, node tests) and the store works purely in memory when it fails.
import type { EventBus, GraphicsSettings, QualityTier, Settings, SettingsStore } from '../contracts';
import { AI_ELO_MAX, AI_ELO_MIN, DEFAULT_SETTINGS, GRAPHICS_PRESETS, LEGACY_LEVEL_ELO } from '../contracts';
import { legacyLevelForElo } from './ai/strength';

export const SETTINGS_KEY = 'battle-chess.settings.v1';

const ENUMS: Partial<Record<keyof Settings, readonly unknown[]>> = {
  cameraMode: ['follow', 'fixed', 'free', 'top'],
  captureMode: ['full', 'quick', 'off'],
  quality: ['auto', 'high', 'medium', 'low'],
  aiLevel: ['easy', 'medium', 'hard', 'master'],
  contrast: ['soft', 'standard', 'vivid'],
  playerSide: ['w', 'b'],
  highlightStyle: ['glow', 'brackets', 'tint', 'runes'],
};
const RANGES: Partial<Record<keyof Settings, [number, number]>> = {
  animSpeed: [0.5, 2], musicVolume: [0, 1], sfxVolume: [0, 1], highlightIntensity: [0.2, 1],
};

/** Free-form id strings (registries live elsewhere; consumers fall back for unknown ids). */
const ID_KEYS: ReadonlySet<keyof Settings> = new Set<keyof Settings>(['themeId', 'pieceSetId']);
export const AI_ELO_STEP = 50;
/** Computer strength: clamped to AI_ELO_MIN..AI_ELO_MAX and snapped to the 50-point slider grid. */
export function sanitizeAiElo(value: unknown): number {
  const n = typeof value === 'number' && Number.isFinite(value) ? value : DEFAULT_SETTINGS.aiElo;
  return Math.min(AI_ELO_MAX, Math.max(AI_ELO_MIN, Math.round(n / AI_ELO_STEP) * AI_ELO_STEP));
}

const G_ENUMS = {
  preset: ['low', 'medium', 'high', 'custom'], shadows: ['off', 'low', 'high'], particles: ['low', 'medium', 'high'], physics: ['simple', 'full'],
} as const;

/** Field-by-field validation of the graphics block; invalid or missing fields fall back to the default preset. */
export function sanitizeGraphics(value: unknown): GraphicsSettings {
  const def = DEFAULT_SETTINGS.graphics;
  const v = (value && typeof value === 'object' ? value : {}) as Record<string, unknown>;
  const pick = <T extends string>(k: keyof typeof G_ENUMS, fallback: T): T => ((G_ENUMS[k] as readonly string[]).includes(v[k] as string) ? v[k] : fallback) as T;
  const bool = (k: keyof GraphicsSettings, fallback: boolean) => (typeof v[k] === 'boolean' ? (v[k] as boolean) : fallback);
  const scale = typeof v.resolutionScale === 'number' && Number.isFinite(v.resolutionScale) ? Math.min(1, Math.max(0.5, v.resolutionScale)) : def.resolutionScale;
  return {
    preset: pick('preset', def.preset), resolutionScale: scale, shadows: pick('shadows', def.shadows),
    bloom: bool('bloom', def.bloom), antialias: bool('antialias', def.antialias), particles: pick('particles', def.particles),
    physics: pick('physics', def.physics), ambient: bool('ambient', def.ambient), secondaryMotion: bool('secondaryMotion', def.secondaryMotion),
    showFps: bool('showFps', def.showFps),
    fpsCap: ([0, 30, 60] as const).includes(v.fpsCap as 0) ? (v.fpsCap as 0 | 30 | 60) : def.fpsCap,
  };
}

/** Preset values for a tier, keeping the user's FPS-overlay choice. */
export function graphicsForTier(tier: QualityTier, keep?: Pick<GraphicsSettings, 'showFps'>): GraphicsSettings {
  return { ...GRAPHICS_PRESETS[tier], showFps: keep?.showFps ?? GRAPHICS_PRESETS[tier].showFps };
}

/** Edit one graphics option: the preset becomes 'custom'. */
export function patchGraphics(store: SettingsStore, patch: Partial<GraphicsSettings>): void {
  store.set('graphics', { ...store.get().graphics, ...patch, preset: patch.preset ?? 'custom' });
}

/** Choose a preset ('auto' resolves to the device tier elsewhere). */
export function choosePreset(store: SettingsStore, preset: QualityTier | 'auto'): void {
  if (preset === 'auto') { store.set('quality', 'auto'); return; }
  store.set('quality', preset);
  store.set('graphics', graphicsForTier(preset, store.get().graphics));
}

/** Validate one value against the schema; returns the default when invalid. */
function sanitize<K extends keyof Settings>(key: K, value: unknown): Settings[K] {
  if (key === 'graphics') return sanitizeGraphics(value) as Settings[K];
  if (key === 'aiElo') return sanitizeAiElo(value) as Settings[K];
  if (ID_KEYS.has(key)) return (typeof value === 'string' && value.length > 0 && value.length <= 64 ? value : DEFAULT_SETTINGS[key]) as Settings[K];
  const def = DEFAULT_SETTINGS[key];
  if (typeof def === 'boolean') return (typeof value === 'boolean' ? value : def) as Settings[K];
  if (typeof def === 'number') {
    const r = RANGES[key] ?? [-Infinity, Infinity];
    const n = typeof value === 'number' && Number.isFinite(value) ? value : def;
    return Math.min(r[1], Math.max(r[0], n)) as Settings[K];
  }
  const allowed = ENUMS[key];
  return (allowed && allowed.includes(value) ? value : def) as Settings[K];
}

/** Settings saved before contract v1.4 only have `aiLevel`: carry it over to `aiElo` once (an explicit `aiElo` wins). */
export function migrateAiLevel(stored: Record<string, unknown>, into: Settings): void {
  if ('aiElo' in stored) { into.aiLevel = legacyLevelForElo(into.aiElo); return; }
  const level = stored.aiLevel as keyof typeof LEGACY_LEVEL_ELO;
  if (typeof level === 'string' && Object.prototype.hasOwnProperty.call(LEGACY_LEVEL_ELO, level)) into.aiElo = sanitizeAiElo(LEGACY_LEVEL_ELO[level]);
}

function safeStorage(): Storage | null {
  try { return typeof localStorage !== 'undefined' ? localStorage : null; } catch { return null; }
}

export interface SettingsStoreOptions {
  storage?: Storage | null;
  key?: string;
  bus?: EventBus;
}

export function createSettingsStore(opts: SettingsStoreOptions = {}): SettingsStore {
  const key = opts.key ?? SETTINGS_KEY;
  const storage = opts.storage === undefined ? safeStorage() : opts.storage;
  let current: Settings = { ...DEFAULT_SETTINGS };
  const subs = new Set<(s: Readonly<Settings>, k: keyof Settings) => void>();

  try {
    const raw = storage?.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      for (const k of Object.keys(DEFAULT_SETTINGS) as (keyof Settings)[]) {
        if (k in parsed) (current as unknown as Record<string, unknown>)[k] = sanitize(k, parsed[k]);
      }
      migrateAiLevel(parsed, current);
    }
  } catch { /* corrupt or unavailable: keep defaults */ }

  let snapshot: Readonly<Settings> = Object.freeze({ ...current });

  const persist = () => {
    try { storage?.setItem(key, JSON.stringify(current)); } catch { /* quota / blocked: stay in memory */ }
  };

  return {
    get: () => snapshot,
    set(k, value) {
      const next = sanitize(k, value);
      if (k === 'graphics' ? JSON.stringify(current[k]) === JSON.stringify(next) : current[k] === next) return;
      current = { ...current, [k]: next };
      if (k === 'aiElo') current.aiLevel = legacyLevelForElo(next as number); // keep the deprecated field in step
      snapshot = Object.freeze({ ...current });
      persist();
      subs.forEach((fn) => { try { fn(snapshot, k); } catch (e) { console.error('[settings] subscriber failed', e); } });
      opts.bus?.emit('settings:changed', { key: k });
    },
    subscribe(fn) {
      subs.add(fn);
      return () => { subs.delete(fn); };
    },
  };
}
