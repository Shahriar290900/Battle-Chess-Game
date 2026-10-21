import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS } from '../src/contracts';
import { createSettingsStore } from '../src/core/settings';

function memStorage(initial: Record<string, string> = {}): Storage {
  const m = new Map(Object.entries(initial));
  return {
    get length() { return m.size; }, clear: () => m.clear(), key: (i) => [...m.keys()][i] ?? null,
    getItem: (k) => m.get(k) ?? null, removeItem: (k) => { m.delete(k); }, setItem: (k, v) => { m.set(k, v); },
  };
}

describe('settings store', () => {
  it('persists and reloads', () => {
    const st = memStorage();
    const a = createSettingsStore({ storage: st });
    a.set('cameraMode', 'top'); a.set('musicVolume', 0.2);
    const b = createSettingsStore({ storage: st });
    expect(b.get().cameraMode).toBe('top');
    expect(b.get().musicVolume).toBe(0.2);
  });
  it('sanitises corrupt or out-of-range data', () => {
    const st = memStorage({ 'battle-chess.settings.v1': JSON.stringify({ animSpeed: 99, aiLevel: 'godlike', colorBlind: 'yes' }) });
    const s = createSettingsStore({ storage: st }).get();
    expect(s.animSpeed).toBe(2);
    expect(s.aiLevel).toBe(DEFAULT_SETTINGS.aiLevel);
    expect(s.colorBlind).toBe(false);
    expect(createSettingsStore({ storage: memStorage({ 'battle-chess.settings.v1': '{nope' }) }).get()).toEqual(DEFAULT_SETTINGS);
  });
  it('survives a storage that throws', () => {
    const bad = { getItem() { throw new Error('x'); }, setItem() { throw new Error('x'); } } as unknown as Storage;
    const s = createSettingsStore({ storage: bad });
    s.set('colorBlind', true);
    expect(s.get().colorBlind).toBe(true);
  });
  it('notifies subscribers', () => {
    const s = createSettingsStore({ storage: null });
    const seen: string[] = [];
    s.subscribe((_, k) => seen.push(k));
    s.set('quality', 'low'); s.set('quality', 'low');
    expect(seen).toEqual(['quality']);
  });
});
