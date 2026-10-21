// SettingsStore persisted to localStorage. Every storage access is wrapped in try/catch
// (private windows, blocked storage, node tests) and the store works purely in memory when it fails.
import type { EventBus, Settings, SettingsStore } from '../contracts';
import { DEFAULT_SETTINGS } from '../contracts';

export const SETTINGS_KEY = 'battle-chess.settings.v1';

const ENUMS: Partial<Record<keyof Settings, readonly unknown[]>> = {
  cameraMode: ['follow', 'fixed', 'free', 'top'],
  captureMode: ['full', 'quick', 'off'],
  quality: ['auto', 'high', 'medium', 'low'],
  aiLevel: ['easy', 'medium', 'hard', 'master'],
  playerSide: ['w', 'b'],
};
const RANGES: Partial<Record<keyof Settings, [number, number]>> = {
  animSpeed: [0.5, 2], musicVolume: [0, 1], sfxVolume: [0, 1],
};

/** Validate one value against the schema; returns the default when invalid. */
function sanitize<K extends keyof Settings>(key: K, value: unknown): Settings[K] {
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
      if (current[k] === next) return;
      current = { ...current, [k]: next };
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
