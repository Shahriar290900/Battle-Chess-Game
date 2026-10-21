// Built-in alpha-beta used when the Stockfish worker cannot load. Pure TS, chess.js move generation.
import { Chess } from 'chess.js';
import type { Move, PieceSymbol } from 'chess.js';
import type { AiLevel, AiMove } from '../../contracts';
import type { PromotionRole } from '../../contracts';

const PROMO: Record<string, PromotionRole> = { q: 'queen', r: 'rook', b: 'bishop', n: 'knight' };
const VALUE: Record<PieceSymbol, number> = { p: 100, n: 320, b: 330, r: 500, q: 900, k: 0 };
const MATE = 100000;

// Piece-square tables, white's view, index 0 = a8 (rank 8) ... 63 = h1.
const PST: Record<PieceSymbol, number[]> = {
  p: [0,0,0,0,0,0,0,0, 50,50,50,50,50,50,50,50, 10,10,20,30,30,20,10,10, 5,5,10,25,25,10,5,5,
      0,0,0,20,20,0,0,0, 5,-5,-10,0,0,-10,-5,5, 5,10,10,-20,-20,10,10,5, 0,0,0,0,0,0,0,0],
  n: [-50,-40,-30,-30,-30,-30,-40,-50, -40,-20,0,0,0,0,-20,-40, -30,0,10,15,15,10,0,-30, -30,5,15,20,20,15,5,-30,
      -30,0,15,20,20,15,0,-30, -30,5,10,15,15,10,5,-30, -40,-20,0,5,5,0,-20,-40, -50,-40,-30,-30,-30,-30,-40,-50],
  b: [-20,-10,-10,-10,-10,-10,-10,-20, -10,0,0,0,0,0,0,-10, -10,0,5,10,10,5,0,-10, -10,5,5,10,10,5,5,-10,
      -10,0,10,10,10,10,0,-10, -10,10,10,10,10,10,10,-10, -10,5,0,0,0,0,5,-10, -20,-10,-10,-10,-10,-10,-10,-20],
  r: [0,0,0,0,0,0,0,0, 5,10,10,10,10,10,10,5, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5,
      -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, 0,0,0,5,5,0,0,0],
  q: [-20,-10,-10,-5,-5,-10,-10,-20, -10,0,0,0,0,0,0,-10, -10,0,5,5,5,5,0,-10, -5,0,5,5,5,5,0,-5,
      0,0,5,5,5,5,0,-5, -10,5,5,5,5,5,0,-10, -10,0,5,0,0,0,0,-10, -20,-10,-10,-5,-5,-10,-10,-20],
  k: [-30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30,
      -20,-30,-30,-40,-40,-30,-30,-20, -10,-20,-20,-20,-20,-20,-20,-10, 20,20,0,0,0,0,20,20, 20,30,10,0,0,10,30,20],
};

/** Static eval in centipawns from the side-to-move's point of view. */
function evaluate(g: Chess): number {
  let score = 0;
  const board = g.board();
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const p = board[r][f];
      if (!p) continue;
      // white indexes straight; black mirrors vertically
      const idx = p.color === 'w' ? r * 8 + f : (7 - r) * 8 + f;
      const v = VALUE[p.type] + PST[p.type][idx];
      score += p.color === 'w' ? v : -v;
    }
  }
  return g.turn() === 'w' ? score : -score;
}

function order(moves: Move[]): Move[] {
  const key = (m: Move) =>
    (m.captured ? 10 * VALUE[m.captured] - VALUE[m.piece] / 10 + 1000 : 0) + (m.promotion ? 800 : 0);
  return moves.sort((a, b) => key(b) - key(a));
}

class Timeout extends Error {}

interface Ctx { deadline: number; nodes: number }

function check(ctx: Ctx) {
  if ((++ctx.nodes & 15) === 0 && Date.now() > ctx.deadline) throw new Timeout();
}

function quiesce(g: Chess, alpha: number, beta: number, ctx: Ctx, qd: number): number {
  check(ctx);
  const stand = evaluate(g);
  if (qd <= 0) return stand;
  if (stand >= beta) return stand;
  if (stand > alpha) alpha = stand;
  const caps = order(g.moves({ verbose: true }).filter((m) => m.captured || m.promotion));
  for (const m of caps) {
    g.move(m);
    const s = -quiesce(g, -beta, -alpha, ctx, qd - 1);
    g.undo();
    if (s >= beta) return s;
    if (s > alpha) alpha = s;
  }
  return alpha;
}

function negamax(g: Chess, depth: number, alpha: number, beta: number, ply: number, ctx: Ctx): number {
  check(ctx);
  const moves = g.moves({ verbose: true });
  if (moves.length === 0) return g.inCheck() ? -MATE + ply : 0;
  if (depth <= 0) return quiesce(g, alpha, beta, ctx, 4);
  let best = -Infinity;
  for (const m of order(moves)) {
    g.move(m);
    const s = -negamax(g, depth - 1, -beta, -alpha, ply + 1, ctx);
    g.undo();
    if (s > best) best = s;
    if (best > alpha) alpha = best;
    if (alpha >= beta) break;
  }
  return best;
}

const LEVEL: Record<AiLevel, { depth: number; ms: number; noise: number; blunder: number }> = {
  easy: { depth: 1, ms: 150, noise: 60, blunder: 0.25 },
  medium: { depth: 2, ms: 600, noise: 15, blunder: 0 },
  hard: { depth: 3, ms: 1500, noise: 0, blunder: 0 },
  master: { depth: 3, ms: 2000, noise: 0, blunder: 0 },
};

export function toAiMove(m: Move): AiMove {
  return { from: m.from, to: m.to, promotion: m.promotion ? PROMO[m.promotion] : undefined };
}

/** Random legal move (used for deliberate easy-mode mistakes). */
export function randomMove(fen: string): AiMove {
  const moves = new Chess(fen).moves({ verbose: true });
  if (!moves.length) throw new Error('no legal moves');
  return toAiMove(moves[Math.floor(Math.random() * moves.length)]);
}

/** Synchronous best-move search. Throws if the position has no legal moves. */
export function fallbackMove(fen: string, level: AiLevel): AiMove {
  const cfg = LEVEL[level];
  const g = new Chess(fen);
  const root = order(g.moves({ verbose: true }));
  if (root.length === 0) throw new Error('no legal moves');
  if (cfg.blunder && Math.random() < cfg.blunder) return toAiMove(root[Math.floor(Math.random() * root.length)]);

  const ctx: Ctx = { deadline: Date.now() + cfg.ms, nodes: 0 };
  let bestMoves = [root[0]];
  // iterative deepening; keep last completed iteration if time runs out
  for (let d = 1; d <= cfg.depth; d++) {
    const scored: { m: Move; s: number }[] = [];
    try {
      let alpha = -Infinity;
      for (const m of root) {
        g.move(m);
        // with noise we need exact-ish scores, so don't narrow the window fully
        const s = -negamax(g, d - 1, -Infinity, cfg.noise ? Infinity : -alpha, 1, ctx);
        g.undo();
        scored.push({ m, s });
        if (s > alpha) alpha = s;
      }
    } catch (e) {
      if (!(e instanceof Timeout)) throw e;
      // restore board state after aborted search
      while (g.history().length) g.undo();
      break;
    }
    scored.sort((a, b) => b.s - a.s);
    const top = scored[0].s;
    bestMoves = scored.filter((x) => x.s >= top - cfg.noise).map((x) => x.m);
    // float best to front for next iteration's ordering
    root.splice(root.indexOf(scored[0].m), 1);
    root.unshift(scored[0].m);
    if (top > MATE / 2) break;
  }
  return toAiMove(bestMoves[Math.floor(Math.random() * bestMoves.length)]);
}
