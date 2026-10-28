import { describe, expect, it } from 'vitest';
import { EventBus } from '../../src/contracts';
import {
  HISTORY_MAX, K_ESTABLISHED, K_PROVISIONAL, PROVISIONAL_GAMES, RATING_FLOOR, RATING_KEY, RATING_START,
  attachRatingTracker, createRatingStore, expectedScore, formatRating, kFactor, ratingDelta,
} from '../../src/core/rating';

function memStorage(initial: Record<string, string> = {}): Storage {
  const m = new Map(Object.entries(initial));
  return {
    get length() { return m.size; }, clear: () => m.clear(), key: (i) => [...m.keys()][i] ?? null,
    getItem: (k) => m.get(k) ?? null, removeItem: (k) => { m.delete(k); }, setItem: (k, v) => { m.set(k, v); },
  };
}

describe('rating maths', () => {
  it('expected score is 0.5 for equals and follows the 400-point rule', () => {
    expect(expectedScore(1200, 1200)).toBeCloseTo(0.5, 6);
    expect(expectedScore(1600, 1200)).toBeCloseTo(10 / 11, 6);
    expect(expectedScore(1200, 1600)).toBeCloseTo(1 / 11, 6);
    expect(expectedScore(1000, 2000) + expectedScore(2000, 1000)).toBeCloseTo(1, 9);
  });
  it('K is 40 for the first 20 rated games, then 20', () => {
    expect(kFactor(0)).toBe(K_PROVISIONAL);
    expect(kFactor(PROVISIONAL_GAMES - 1)).toBe(40);
    expect(kFactor(PROVISIONAL_GAMES)).toBe(K_ESTABLISHED);
    expect(ratingDelta(1000, 1000, 'win', 0)).toBe(20);
    expect(ratingDelta(1000, 1000, 'win', 20)).toBe(10);
    expect(ratingDelta(1000, 1000, 'loss', 5)).toBe(-20);
    expect(ratingDelta(1000, 1000, 'draw', 5)).toBe(0);
  });
  it('beating a stronger foe pays more; losing to a weaker one costs more', () => {
    expect(ratingDelta(1000, 2000, 'win', 30)).toBeGreaterThan(ratingDelta(1000, 1000, 'win', 30));
    expect(ratingDelta(1000, 400, 'loss', 30)).toBeLessThan(ratingDelta(1000, 1000, 'loss', 30));
    expect(ratingDelta(1000, 400, 'resign', 30)).toBe(ratingDelta(1000, 400, 'loss', 30));
  });
  it('never drops below the floor', () => {
    expect(ratingDelta(110, 3000, 'loss', 0)).toBe(0);
    expect(ratingDelta(105, 400, 'loss', 0)).toBe(RATING_FLOOR - 105);
    const s = createRatingStore({ storage: memStorage({ [RATING_KEY]: JSON.stringify({ rating: 103, rated: 3, history: [] }) }) });
    s.record({ opponent: 400, result: 'loss' });
    expect(s.current().rating).toBe(RATING_FLOOR);
    s.record({ opponent: 400, result: 'loss' });
    expect(s.current().rating).toBe(RATING_FLOOR);
    expect(s.history()[1].delta).toBe(0);
  });
  it('formats provisional ratings with a question mark', () => {
    expect(formatRating(1200, true)).toBe('1200?');
    expect(formatRating(1200.4, false)).toBe('1200');
  });
});

describe('rating store', () => {
  it('starts at 1000, provisional', () => {
    const s = createRatingStore({ storage: null });
    expect(s.current()).toMatchObject({ rating: RATING_START, rated: 0, provisional: true, label: '1000?' });
  });
  it('turns established after 20 rated games and switches K', () => {
    const s = createRatingStore({ storage: null });
    for (let i = 0; i < 20; i++) s.record({ opponent: s.current().rating, result: 'draw' });
    expect(s.current()).toMatchObject({ rated: 20, provisional: false });
    const before = s.current().rating;
    expect(s.record({ opponent: before, result: 'win' }).delta).toBe(10);
  });
  it('casual games are logged but neither rated nor counted', () => {
    const s = createRatingStore({ storage: null });
    const e = s.record({ opponent: 3000, result: 'win', casual: true });
    expect(e).toMatchObject({ delta: 0, casual: true, rating: 1000 });
    expect(s.current()).toMatchObject({ rating: 1000, rated: 0 });
    expect(s.history()).toHaveLength(1);
  });
  it('keeps the last 50 results and persists them under a namespaced key', () => {
    const st = memStorage();
    const a = createRatingStore({ storage: st });
    for (let i = 0; i < 60; i++) a.record({ opponent: 1000 + i, result: i % 2 ? 'win' : 'loss', date: new Date(2026, 0, 1 + (i % 28)) });
    expect(a.history()).toHaveLength(HISTORY_MAX);
    expect(st.getItem(RATING_KEY)).toBeTruthy();
    const b = createRatingStore({ storage: st });
    expect(b.current()).toEqual(a.current());
    expect(b.history()).toEqual(a.history());
    expect(b.history()[49]).toMatchObject({ opponent: 1059, result: 'win' });
  });
  it('sanitises corrupt data and survives throwing storage', () => {
    expect(createRatingStore({ storage: memStorage({ [RATING_KEY]: '{nope' }) }).current().rating).toBe(RATING_START);
    const bad = createRatingStore({ storage: memStorage({ [RATING_KEY]: JSON.stringify({ rating: -5, rated: 'x', history: [1, { result: 'win', date: 'd' }, { result: 'nope' }] }) }) });
    expect(bad.current()).toMatchObject({ rating: RATING_FLOOR, rated: 0 });
    expect(bad.history()).toHaveLength(1);
    const throwing = { getItem() { throw new Error('x'); }, setItem() { throw new Error('x'); } } as unknown as Storage;
    const s = createRatingStore({ storage: throwing });
    s.record({ opponent: 1000, result: 'win' });
    expect(s.current().rating).toBe(1020);
  });
  it('preview and winChance have no side effects; subscribers hear records', () => {
    const s = createRatingStore({ storage: null });
    const seen: number[] = [];
    s.subscribe((st) => seen.push(st.rating));
    expect(s.preview(1000, 'win')).toBe(20);
    expect(s.winChance(1000)).toBeCloseTo(0.5, 6);
    expect(seen).toEqual([]);
    s.record({ opponent: 1000, result: 'win' });
    expect(seen).toEqual([1020]);
  });
});

describe('rating tracker', () => {
  const src = (over: Partial<{ ratedElo: number | null; tookBack: boolean; side: 'w' | 'b'; kind: string }> = {}) => ({
    get gameMode() { return { kind: over.kind ?? 'vs-ai', playerSide: over.side ?? 'w' } as { kind: string; playerSide: 'w' | 'b' }; },
    get ratedElo() { return over.ratedElo === undefined ? 1200 : over.ratedElo; },
    get tookBack() { return over.tookBack ?? false; },
  });
  it('records win, loss, draw and resign once per game', () => {
    const bus = new EventBus(); const store = createRatingStore({ storage: null });
    const t = attachRatingTracker(src(), bus, store);
    bus.emit('game:start', { mode: 'vs-ai', fen: '' });
    bus.emit('game:over', { result: '1-0', reason: 'checkmate' });
    bus.emit('game:over', { result: '1-0', reason: 'checkmate' }); // duplicate (undo from game over then replay): ignored
    expect(store.history().map((h) => h.result)).toEqual(['win']);
    expect(t.last()?.result).toBe('win'); // the duplicate keeps the first entry
    bus.emit('game:start', { mode: 'vs-ai', fen: '' });
    bus.emit('game:over', { result: '0-1', reason: 'checkmate' });
    expect(t.last()?.result).toBe('loss');
    bus.emit('game:start', { mode: 'vs-ai', fen: '' });
    bus.emit('game:over', { result: '1/2-1/2', reason: 'stalemate' });
    expect(t.last()?.result).toBe('draw');
    bus.emit('game:start', { mode: 'vs-ai', fen: '' });
    bus.emit('game:over', { result: '0-1', reason: 'resign' });
    expect(t.last()?.result).toBe('resign');
    expect(store.history()).toHaveLength(4);
  });
  it('plays as black, flags take-backs as casual, ignores hot-seat and unrated games', () => {
    const bus = new EventBus(); const store = createRatingStore({ storage: null });
    attachRatingTracker(src({ side: 'b' }), bus, store);
    bus.emit('game:over', { result: '0-1', reason: 'checkmate' });
    expect(store.history()[0].result).toBe('win');
    const bus2 = new EventBus(); const store2 = createRatingStore({ storage: null });
    attachRatingTracker(src({ tookBack: true }), bus2, store2);
    bus2.emit('game:over', { result: '1-0', reason: 'checkmate' });
    expect(store2.history()[0]).toMatchObject({ casual: true, delta: 0 });
    for (const o of [{ kind: 'hotseat' }, { ratedElo: null }]) {
      const b = new EventBus(); const s = createRatingStore({ storage: null });
      attachRatingTracker(src(o), b, s);
      b.emit('game:over', { result: '1-0', reason: 'checkmate' });
      expect(s.history()).toHaveLength(0);
    }
  });
});
