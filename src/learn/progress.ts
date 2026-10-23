// Learn progress persisted in localStorage (every access wrapped in try/catch; works in memory when storage fails).
export const PROGRESS_KEY = 'battle-chess.learn.v1';

export interface StorageLike { getItem(k: string): string | null; setItem(k: string, v: string): void; removeItem?(k: string): void }
export interface LessonRecord { done: boolean; tries: number; at: number }
export interface LearnProgress { lessons: Record<string, LessonRecord>; tutorialDone: boolean; beginnerGames: number }

const blank = (): LearnProgress => ({ lessons: {}, tutorialDone: false, beginnerGames: 0 });

/** Field-by-field validation of whatever was stored. */
export function sanitizeProgress(raw: unknown): LearnProgress {
  const out = blank();
  if (!raw || typeof raw !== 'object') return out;
  const r = raw as Record<string, unknown>;
  if (r.lessons && typeof r.lessons === 'object') {
    for (const [id, v] of Object.entries(r.lessons as Record<string, unknown>)) {
      if (!v || typeof v !== 'object') continue;
      const rec = v as Record<string, unknown>;
      out.lessons[id] = {
        done: rec.done === true,
        tries: typeof rec.tries === 'number' && Number.isFinite(rec.tries) && rec.tries >= 0 ? Math.floor(rec.tries) : 0,
        at: typeof rec.at === 'number' && Number.isFinite(rec.at) ? rec.at : 0,
      };
    }
  }
  out.tutorialDone = r.tutorialDone === true;
  out.beginnerGames = typeof r.beginnerGames === 'number' && r.beginnerGames >= 0 ? Math.floor(r.beginnerGames) : 0;
  return out;
}

export interface ProgressStore {
  get(): Readonly<LearnProgress>;
  isDone(id: string): boolean;
  /** Mark a lesson complete (idempotent). */
  complete(id: string): void;
  /** Count a wrong try. */
  attempt(id: string): void;
  setTutorialDone(): void;
  addBeginnerGame(): void;
  doneCount(ids: readonly string[]): number;
  reset(): void;
  subscribe(fn: (p: Readonly<LearnProgress>) => void): () => void;
}

function defaultStorage(): StorageLike | null {
  try { return typeof localStorage === 'undefined' ? null : localStorage; } catch { return null; }
}

export function createProgressStore(storage: StorageLike | null | undefined = defaultStorage(), now: () => number = Date.now): ProgressStore {
  let data = blank();
  try {
    const text = storage?.getItem(PROGRESS_KEY);
    if (text) data = sanitizeProgress(JSON.parse(text));
  } catch { data = blank(); }
  const listeners = new Set<(p: Readonly<LearnProgress>) => void>();
  const save = () => {
    try { storage?.setItem(PROGRESS_KEY, JSON.stringify(data)); } catch { /* quota / private mode: keep in memory */ }
    listeners.forEach((fn) => { try { fn(data); } catch (e) { console.error('[learn] progress listener failed', e); } });
  };
  const rec = (id: string): LessonRecord => (data.lessons[id] ??= { done: false, tries: 0, at: 0 });
  return {
    get: () => data,
    isDone: (id) => data.lessons[id]?.done === true,
    complete(id) {
      const r = rec(id);
      if (r.done) return;
      r.done = true; r.at = now();
      save();
    },
    attempt(id) { rec(id).tries++; save(); },
    setTutorialDone() { if (data.tutorialDone) return; data.tutorialDone = true; save(); },
    addBeginnerGame() { data.beginnerGames++; save(); },
    doneCount: (ids) => ids.filter((id) => data.lessons[id]?.done).length,
    reset() { data = blank(); try { storage?.removeItem?.(PROGRESS_KEY); } catch { /* ignore */ } listeners.forEach((fn) => fn(data)); },
    subscribe(fn) { listeners.add(fn); return () => { listeners.delete(fn); }; },
  };
}
