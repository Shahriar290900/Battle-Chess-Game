import { Chess } from 'chess.js';
import { createAiPlayer } from '../src/core/ai';
import type { AiLevel } from '../src/contracts';

const FENS = [
  'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
  '8/P6k/8/8/8/8/8/K7 w - - 0 1',
];
const LEVELS: AiLevel[] = ['easy', 'medium', 'hard', 'master'];
const out = document.getElementById('out')!;
const results: { fen: string; level: AiLevel; move: string; legal: boolean; ms: number }[] = [];

(async () => {
  const ai = createAiPlayer();
  await ai.init();
  ai.newGame();
  for (const fen of FENS) {
    for (const level of LEVELS) {
      const t = performance.now();
      const m = await ai.getMove(fen, level);
      const ms = Math.round(performance.now() - t);
      let legal = true;
      try {
        new Chess(fen).move({ from: m.from, to: m.to, promotion: m.promotion ? ({ queen: 'q', rook: 'r', bishop: 'b', knight: 'n' } as const)[m.promotion] : undefined });
      } catch { legal = false; }
      results.push({ fen, level, move: m.from + m.to + (m.promotion ?? ''), legal, ms });
      out.textContent = results.map((r) => `${r.level.padEnd(7)} ${r.move.padEnd(10)} ${r.legal ? 'ok ' : 'ILLEGAL'} ${r.ms}ms  ${r.fen}`).join('\n');
    }
  }
  // cancel test
  let cancelled = false;
  const p = ai.getMove(FENS[1], 'master').catch((e: Error) => { cancelled = e.message === 'cancelled'; });
  setTimeout(() => ai.cancel(), 200);
  await p;
  const after = await ai.getMove(FENS[0], 'medium');
  (window as any).__aiResult = { results, cancelled, afterCancel: after, done: true };
  ai.dispose();
})().catch((e) => { (window as any).__aiResult = { error: String(e), done: true }; });
