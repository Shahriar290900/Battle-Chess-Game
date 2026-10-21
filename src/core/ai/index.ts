// AI opponent: Stockfish 19 lite (single-thread WASM) in a Worker, with a built-in TS fallback.
import { Chess } from 'chess.js';
import type { AiLevel, AiMove, AiPlayer } from '../../contracts';
import { fallbackMove, randomMove, toAiMove } from './fallback';

const ENGINE_FILE = 'stockfish-19-lite-single';
const INIT_TIMEOUT_MS = 8000;
const MIN_RESPONSE_MS = 600;

interface LevelCfg { skill: number; go: string; minMs: number; blunder: number }
const LEVELS: Record<AiLevel, LevelCfg> = {
  easy: { skill: 1, go: 'go movetime 150', minMs: MIN_RESPONSE_MS, blunder: 0.3 },
  medium: { skill: 8, go: 'go movetime 400', minMs: MIN_RESPONSE_MS, blunder: 0 },
  hard: { skill: 15, go: 'go movetime 1000', minMs: MIN_RESPONSE_MS, blunder: 0 },
  master: { skill: 20, go: 'go movetime 2000', minMs: MIN_RESPONSE_MS, blunder: 0 },
};

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function createAiPlayer(): AiPlayer {
  let worker: Worker | null = null;
  let useFallback = false;
  let initPromise: Promise<void> | null = null;
  let disposed = false;
  let generation = 0; // bumped by cancel()
  let queue: Promise<unknown> = Promise.resolve();
  let staleBestmoves = 0; // bestmove lines still owed from stopped searches
  let lineListener: ((line: string) => void) | null = null;
  let staleWaiter: (() => void) | null = null;
  let searching = false;
  let abortWait: (() => void) | null = null;
  let rejectPending: ((e: Error) => void) | null = null;

  function send(cmd: string) { worker?.postMessage(cmd); }

  function onLine(line: string) {
    if (line.startsWith('bestmove')) {
      if (staleBestmoves === 0) searching = false;
    }
    if (staleBestmoves > 0 && line.startsWith('bestmove')) {
      staleBestmoves--;
      if (staleBestmoves === 0) { staleWaiter?.(); staleWaiter = null; }
      return;
    }
    lineListener?.(line);
  }

  function waitFor(pred: (line: string) => boolean, ms: number): Promise<string> {
    return new Promise((resolve, reject) => {
      const me = (l: string) => {
        if (pred(l)) { clearTimeout(t); lineListener = null; abortWait = null; resolve(l); }
      };
      const t = setTimeout(() => {
        if (lineListener === me) { lineListener = null; abortWait = null; }
        reject(new Error('engine timeout'));
      }, ms);
      lineListener = me;
      abortWait = () => { clearTimeout(t); if (lineListener === me) lineListener = null; abortWait = null; reject(new Error('cancelled')); };
    });
  }

  function startWorker(): Promise<void> {
    const base = import.meta.env.BASE_URL;
    const jsUrl = new URL(`${base}engine/${ENGINE_FILE}.js`, location.href).href;
    const wasmUrl = new URL(`${base}engine/${ENGINE_FILE}.wasm`, location.href).href;
    // The engine reads "#<encoded wasm url>" from its own location to find the wasm.
    const w = new Worker(`${jsUrl}#${encodeURIComponent(wasmUrl)}`);
    worker = w;
    return new Promise<void>((resolve, reject) => {
      const fail = (e: unknown) => reject(e instanceof Error ? e : new Error('worker error'));
      w.onerror = (ev) => { fail(new Error(ev.message || 'worker error')); };
      w.onmessage = (ev) => { if (typeof ev.data === 'string') onLine(ev.data.trim()); };
      const timer = setTimeout(() => fail(new Error('init timeout')), INIT_TIMEOUT_MS);
      (async () => {
        const ok1 = waitFor((l) => l === 'uciok', INIT_TIMEOUT_MS);
        send('uci');
        await ok1;
        send('setoption name Threads value 1');
        send('setoption name Hash value 16');
        const ok2 = waitFor((l) => l === 'readyok', INIT_TIMEOUT_MS);
        send('isready');
        await ok2;
      })().then(() => { clearTimeout(timer); resolve(); }, (e) => { clearTimeout(timer); fail(e); });
    });
  }

  function abandonWorker() {
    useFallback = true;
    try { worker?.terminate(); } catch { /* ignore */ }
    worker = null;
  }

  function init(): Promise<void> {
    if (!initPromise) {
      initPromise = (async () => {
        if (typeof Worker === 'undefined' || typeof WebAssembly === 'undefined' || typeof location === 'undefined') {
          useFallback = true;
          return;
        }
        try {
          await startWorker();
          // Later crashes switch us to the fallback.
          if (worker) worker.onerror = () => { abandonWorker(); lineListener = null; };
        } catch (e) {
          console.warn('[ai] Stockfish unavailable, using built-in engine:', e);
          abandonWorker();
        }
      })();
    }
    return initPromise;
  }

  async function searchStockfish(fen: string, cfg: LevelCfg, gen: number): Promise<string> {
    if (staleBestmoves > 0) {
      await new Promise<void>((r) => { staleWaiter = r; setTimeout(r, 3000); });
      staleBestmoves = 0;
    }
    if (gen !== generation) throw new Error('cancelled');
    send(`setoption name Skill Level value ${cfg.skill}`);
    send(`position fen ${fen}`);
    const done = waitFor((l) => l.startsWith('bestmove'), 15000);
    searching = true;
    send(cfg.go);
    const line = await done;
    return line.split(/\s+/)[1] ?? '';
  }

  async function run(fen: string, level: AiLevel, gen: number): Promise<AiMove> {
    await init();
    if (gen !== generation || disposed) throw new Error('cancelled');
    const cfg = LEVELS[level];
    const started = Date.now();
    const legal = new Chess(fen).moves({ verbose: true });
    if (legal.length === 0) throw new Error('no legal moves');

    let move: AiMove | null = null;
    if (cfg.blunder && Math.random() < cfg.blunder) {
      move = randomMove(fen); // deliberate beginner mistake
    } else if (!useFallback && worker) {
      try {
        const best = await searchStockfish(fen, cfg, gen);
        const m = legal.find((x) => x.from === best.slice(0, 2) && x.to === best.slice(2, 4) &&
          (best.length < 5 || x.promotion === best[4]));
        if (m) move = toAiMove(m);
        else if (best.length >= 4) move = null; // illegal/none -> fallback below
      } catch (e) {
        if ((e as Error).message === 'cancelled') throw e;
        console.warn('[ai] engine search failed, using built-in engine:', e);
        abandonWorker();
      }
    }
    if (gen !== generation || disposed) throw new Error('cancelled');
    if (!move) {
      await sleep(0); // let the UI paint before the synchronous search
      move = fallbackMove(fen, level);
    }
    const wait = cfg.minMs - (Date.now() - started);
    if (wait > 0) await sleep(wait);
    if (gen !== generation || disposed) throw new Error('cancelled');
    return move;
  }

  return {
    init,
    getMove(fen, level) {
      const gen = generation;
      const job = queue.then(() => new Promise<AiMove>((resolve, reject) => {
        rejectPending = reject;
        run(fen, level, gen).then(resolve, reject);
      }));
      queue = job.catch(() => undefined);
      // A cancel while queued rejects when its turn comes (gen mismatch).
      return job.then((m) => { rejectPending = null; return m; }, (e) => { rejectPending = null; throw e; });
    },
    cancel() {
      generation++;
      if (rejectPending) { rejectPending(new Error('cancelled')); rejectPending = null; }
      if (searching) abortWait?.();
      if (worker && !useFallback && searching) {
        searching = false;
        staleBestmoves++;
        send('stop');
      }
    },
    newGame() {
      if (worker && !useFallback) send('ucinewgame');
    },
    dispose() {
      disposed = true;
      generation++;
      rejectPending?.(new Error('cancelled'));
      try { worker?.terminate(); } catch { /* ignore */ }
      worker = null;
      useFallback = true;
    },
  };
}
