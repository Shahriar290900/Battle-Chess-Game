import { describe, expect, it } from 'vitest';
import { PROGRESS_KEY, createProgressStore, sanitizeProgress, type StorageLike } from '../../src/learn/progress';

const mem = (): StorageLike & { data: Map<string, string> } => {
  const data = new Map<string, string>();
  return { data, getItem: (k) => data.get(k) ?? null, setItem: (k, v) => { data.set(k, v); }, removeItem: (k) => { data.delete(k); } };
};

describe('learn progress', () => {
  it('persists and reloads completed lessons', () => {
    const st = mem();
    const a = createProgressStore(st, () => 123);
    expect(a.isDone('rook')).toBe(false);
    a.attempt('rook'); a.complete('rook'); a.complete('rook'); a.setTutorialDone(); a.addBeginnerGame();
    const b = createProgressStore(st);
    expect(b.isDone('rook')).toBe(true);
    expect(b.get().lessons.rook).toEqual({ done: true, tries: 1, at: 123 });
    expect(b.get().tutorialDone).toBe(true);
    expect(b.get().beginnerGames).toBe(1);
    expect(b.doneCount(['rook', 'king'])).toBe(1);
  });

  it('notifies subscribers and resets', () => {
    const st = mem();
    const a = createProgressStore(st);
    let n = 0;
    const off = a.subscribe(() => { n++; });
    a.complete('x'); expect(n).toBe(1);
    off(); a.complete('y'); expect(n).toBe(1);
    a.reset();
    expect(a.isDone('x')).toBe(false);
    expect(st.data.has(PROGRESS_KEY)).toBe(false);
  });

  it('survives corrupt, hostile or unavailable storage', () => {
    const bad = mem(); bad.data.set(PROGRESS_KEY, '{not json');
    expect(createProgressStore(bad).get().lessons).toEqual({});
    const throwing: StorageLike = { getItem() { throw new Error('denied'); }, setItem() { throw new Error('quota'); } };
    const s = createProgressStore(throwing);
    expect(() => s.complete('a')).not.toThrow();
    expect(s.isDone('a')).toBe(true); // in memory
    expect(createProgressStore(null).get().tutorialDone).toBe(false);
    expect(sanitizeProgress({ lessons: { a: { done: 'yes', tries: -3 }, b: 5 }, tutorialDone: 1 })).toEqual({ lessons: { a: { done: false, tries: 0, at: 0 } }, tutorialDone: false, beginnerGames: 0 });
  });
});
