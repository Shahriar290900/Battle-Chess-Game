// Local player rating (Elo). Only games against the computer count; nothing leaves the device.
//
// Rules
//   * Start 1000, floor 100.
//   * Expected score E = 1 / (1 + 10^((opponent - rating) / 400)); change = round(K * (S - E)), S = 1 / 0.5 / 0.
//   * K = 40 for the first 20 rated games (provisional, shown as "1000?"), then K = 20.
//   * Results: win, draw, loss, resign (the player resigned: scored as a loss).
//   * CASUAL GAMES (decision): if the player took back a move (Undo) during the game it is logged in the history, flagged
//     `casual`, but the rating does not change and it does not count towards the 20 provisional games. Otherwise a
//     take-back would let the player undo every blunder and farm rating against strong opponents. A game that already
//     ended and was recorded stays recorded even if the player then undoes from the game-over screen.
//   * History: the last 50 results (date, opponent Elo, delta, rating after) under a namespaced localStorage key,
//     every storage access inside try/catch (private windows, blocked storage, node tests).
//
// The module emits nothing on the bus; `attachRatingTracker` only listens to `game:over`.
import type { EventBus } from '../contracts';

export const RATING_KEY = 'battle-chess.rating.v1';
export const RATING_START = 1000;
export const RATING_FLOOR = 100;
export const PROVISIONAL_GAMES = 20;
export const K_PROVISIONAL = 40;
export const K_ESTABLISHED = 20;
export const HISTORY_MAX = 50;

export type GameOutcome = 'win' | 'draw' | 'loss' | 'resign';

export interface RatingEntry {
  /** ISO date-time. */
  date: string;
  /** Computer Elo that was faced. */
  opponent: number;
  result: GameOutcome;
  /** Rating points gained (+) or lost (-); 0 for casual games. */
  delta: number;
  /** Rating after this game. */
  rating: number;
  /** Take-backs were used: logged, not rated. */
  casual: boolean;
}

export interface RatingState {
  rating: number;
  /** Rated (non-casual) games played. */
  rated: number;
  provisional: boolean;
  /** "1000?" while provisional, "1012" afterwards. */
  label: string;
}

// ------------------------------------------------------------------ pure maths
/** Expected score of a player rated `rating` against an opponent rated `opponent`. */
export function expectedScore(rating: number, opponent: number): number {
  return 1 / (1 + Math.pow(10, (opponent - rating) / 400));
}

export function kFactor(ratedGames: number): number {
  return ratedGames < PROVISIONAL_GAMES ? K_PROVISIONAL : K_ESTABLISHED;
}

export const scoreOf = (r: GameOutcome): number => (r === 'win' ? 1 : r === 'draw' ? 0.5 : 0);

/** Points gained or lost, after the floor is applied. */
export function ratingDelta(rating: number, opponent: number, result: GameOutcome, ratedGames: number): number {
  const raw = Math.round(kFactor(ratedGames) * (scoreOf(result) - expectedScore(rating, opponent)));
  return Math.max(RATING_FLOOR, rating + raw) - rating;
}

export const formatRating = (rating: number, provisional: boolean): string => `${Math.round(rating)}${provisional ? '?' : ''}`;

// ------------------------------------------------------------------ store
export interface RatingStore {
  current(): RatingState;
  /** Newest last. */
  history(): readonly RatingEntry[];
  /** Points a result would be worth right now (no side effects). */
  preview(opponent: number, result: GameOutcome): number;
  /** Win probability against an opponent, 0..1. */
  winChance(opponent: number): number;
  /** Record a finished vs-computer game; returns the history entry. */
  record(game: { opponent: number; result: GameOutcome; casual?: boolean; date?: Date }): RatingEntry;
  reset(): void;
  subscribe(fn: (s: RatingState) => void): () => void;
}

export interface RatingStoreOptions { storage?: Storage | null; key?: string }

function safeStorage(): Storage | null {
  try { return typeof localStorage !== 'undefined' ? localStorage : null; } catch { return null; }
}

const isResult = (v: unknown): v is GameOutcome => v === 'win' || v === 'draw' || v === 'loss' || v === 'resign';
const num = (v: unknown, fallback: number) => (typeof v === 'number' && Number.isFinite(v) ? v : fallback);

function sanitizeEntry(raw: unknown): RatingEntry | null {
  if (!raw || typeof raw !== 'object') return null;
  const e = raw as Record<string, unknown>;
  if (!isResult(e.result) || typeof e.date !== 'string') return null;
  return {
    date: e.date, opponent: Math.round(num(e.opponent, 1200)), result: e.result,
    delta: Math.round(num(e.delta, 0)), rating: Math.max(RATING_FLOOR, Math.round(num(e.rating, RATING_START))), casual: e.casual === true,
  };
}

export function createRatingStore(opts: RatingStoreOptions = {}): RatingStore {
  const key = opts.key ?? RATING_KEY;
  const storage = opts.storage === undefined ? safeStorage() : opts.storage;
  let rating = RATING_START;
  let rated = 0;
  let history: RatingEntry[] = [];
  const subs = new Set<(s: RatingState) => void>();

  try {
    const raw = storage?.getItem(key);
    if (raw) {
      const p = JSON.parse(raw) as Record<string, unknown>;
      rating = Math.max(RATING_FLOOR, Math.round(num(p.rating, RATING_START)));
      rated = Math.max(0, Math.floor(num(p.rated, 0)));
      if (Array.isArray(p.history)) history = p.history.map(sanitizeEntry).filter((e): e is RatingEntry => !!e).slice(-HISTORY_MAX);
    }
  } catch { /* corrupt or unavailable: start fresh */ }

  const persist = () => {
    try { storage?.setItem(key, JSON.stringify({ v: 1, rating, rated, history })); } catch { /* quota / blocked: stay in memory */ }
  };
  const state = (): RatingState => {
    const provisional = rated < PROVISIONAL_GAMES;
    return { rating, rated, provisional, label: formatRating(rating, provisional) };
  };
  const emit = () => { const s = state(); subs.forEach((fn) => { try { fn(s); } catch (e) { console.error('[rating] subscriber failed', e); } }); };

  return {
    current: state,
    history: () => history,
    preview: (opponent, result) => ratingDelta(rating, opponent, result, rated),
    winChance: (opponent) => expectedScore(rating, opponent),
    record({ opponent, result, casual = false, date = new Date() }) {
      const delta = casual ? 0 : ratingDelta(rating, opponent, result, rated);
      if (!casual) { rating += delta; rated++; }
      const entry: RatingEntry = { date: date.toISOString(), opponent: Math.round(opponent), result, delta, rating, casual };
      history = [...history, entry].slice(-HISTORY_MAX);
      persist();
      emit();
      return entry;
    },
    reset() { rating = RATING_START; rated = 0; history = []; persist(); emit(); },
    subscribe(fn) { subs.add(fn); return () => { subs.delete(fn); }; },
  };
}

// ------------------------------------------------------------------ tracker (game:over -> record)
/** What the tracker needs from the game controller. */
export interface RatedGameSource {
  readonly gameMode: { kind: string; playerSide: 'w' | 'b' } | null;
  /** Computer Elo of a rated vs-computer game; null for hot-seat games and tutorial duels. */
  readonly ratedElo: number | null;
  /** True once the player took back a move in the current game. */
  readonly tookBack: boolean;
}

export interface RatingTracker {
  /** Entry recorded for the game that just ended (null until one ends, or for unrated games). */
  last(): RatingEntry | null;
  dispose(): void;
}

/** Records exactly one entry per rated game when `game:over` fires. Emits nothing. */
export function attachRatingTracker(src: RatedGameSource, bus: Pick<EventBus, 'on'>, store: RatingStore): RatingTracker {
  let last: RatingEntry | null = null;
  let recorded = false;
  const offStart = bus.on('game:start', () => { last = null; recorded = false; });
  const offOver = bus.on('game:over', (end) => {
    // The controller can announce one ending twice (mate sequence, then the loop); the first record stands.
    const mode = src.gameMode;
    const elo = src.ratedElo;
    if (recorded || !mode || mode.kind !== 'vs-ai' || elo === null) return;
    recorded = true;
    const mine = mode.playerSide === 'w' ? '1-0' : '0-1';
    const result: GameOutcome = end.result === '1/2-1/2' ? 'draw' : end.reason === 'resign' ? 'resign' : end.result === mine ? 'win' : 'loss';
    last = store.record({ opponent: elo, result, casual: src.tookBack });
  });
  return { last: () => last, dispose() { offStart(); offOver(); } };
}
