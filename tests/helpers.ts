import type { AiMove, AiPlayer } from '../src/contracts';

/** AI that never answers (replay tests are hot-seat). */
export function createNullAi(): AiPlayer {
  return {
    async init() {},
    getMove: () => Promise.reject(new Error('null AI has no moves')),
    cancel() {}, newGame() {}, dispose() {},
  };
}

/** AI driven by a script; each call shifts the next move (or falls back to `fallback`). Cancellable. */
export function createScriptedAi(script: AiMove[], opts: { delayMs?: number } = {}): AiPlayer & { calls: string[] } {
  let cancel: (() => void) | null = null;
  const calls: string[] = [];
  return {
    calls,
    async init() {},
    getMove(fen) {
      calls.push(fen);
      return new Promise<AiMove>((resolve, reject) => {
        const t = setTimeout(() => { cancel = null; const m = script.shift(); m ? resolve(m) : reject(new Error('script exhausted')); }, opts.delayMs ?? 0);
        cancel = () => { clearTimeout(t); reject(new Error('cancelled')); };
      });
    },
    cancel() { cancel?.(); cancel = null; },
    newGame() {}, dispose() {},
  };
}
