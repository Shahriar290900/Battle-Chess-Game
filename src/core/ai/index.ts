// STUB (lead) — replaced by ai-opponent. Picks a random legal move.
import { Chess } from 'chess.js';
import type { AiPlayer } from '../../contracts';
import { SYMBOL_ROLE } from '../../contracts';

export function createAiPlayer(): AiPlayer {
  return {
    async init() {},
    async getMove(fen) {
      const moves = new Chess(fen).moves({ verbose: true });
      const m = moves[Math.floor(Math.random() * moves.length)];
      return { from: m.from, to: m.to, promotion: m.promotion ? (SYMBOL_ROLE[m.promotion] as any) : undefined };
    },
    cancel() {},
    newGame() {},
    dispose() {},
  };
}
