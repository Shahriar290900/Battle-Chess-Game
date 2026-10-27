// A small, deterministic, strength-limited chess engine for the playtest personas (chess.js + material/PST eval,
// alpha-beta with MVV-LVA ordering). It lives in Node, NOT in the page: the page only sees real UI input.
import { Chess } from 'chess.js';

export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const VAL = { p: 100, n: 320, b: 335, r: 500, q: 900, k: 0 };
const ORDER = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 10 };

function evaluate(chess) {
  // positive = good for white
  let s = 0;
  const board = chess.board();
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const p = board[r][f];
      if (!p) continue;
      const rankFromWhite = 7 - r;
      const cf = 3.5 - Math.abs(f - 3.5), cr = 3.5 - Math.abs(r - 3.5);
      let v = VAL[p.type];
      const centre = (cf + cr) * (p.type === 'p' ? 6 : p.type === 'n' || p.type === 'b' ? 8 : p.type === 'k' ? 0 : 2);
      v += centre;
      if (p.type === 'p') v += (p.color === 'w' ? rankFromWhite : 7 - rankFromWhite) * 7;
      if (p.type === 'k') { const back = p.color === 'w' ? rankFromWhite === 0 : rankFromWhite === 7; if (back) v += 18; }
      s += p.color === 'w' ? v : -v;
    }
  }
  // mop-up: when well ahead, drive the enemy king to the edge and bring our king close
  let wk = null, bk = null;
  for (let r = 0; r < 8; r++) for (let f = 0; f < 8; f++) { const p = board[r][f]; if (p && p.type === 'k') { if (p.color === 'w') wk = [f, r]; else bk = [f, r]; } }
  if (wk && bk && Math.abs(s) > 350) {
    const lead = s > 0 ? 'w' : 'b';
    const loser = lead === 'w' ? bk : wk, winner = lead === 'w' ? wk : bk;
    const edge = (3.5 - Math.abs(loser[0] - 3.5)) + (3.5 - Math.abs(loser[1] - 3.5));
    const dist = Math.abs(winner[0] - loser[0]) + Math.abs(winner[1] - loser[1]);
    const bonus = (6 - edge) * 12 + (14 - dist) * 5;
    s += lead === 'w' ? bonus : -bonus;
  }
  return s;
}

function orderMoves(moves) {
  return moves.sort((a, b) => {
    const sa = (a.captured ? 10 * ORDER[a.captured] - ORDER[a.piece] : 0) + (a.promotion ? 8 : 0) + (a.san.includes('+') ? 2 : 0);
    const sb = (b.captured ? 10 * ORDER[b.captured] - ORDER[b.piece] : 0) + (b.promotion ? 8 : 0) + (b.san.includes('+') ? 2 : 0);
    return sb - sa;
  });
}

function search(chess, depth, alpha, beta, ply) {
  if (chess.isCheckmate()) return -100000 + ply;
  if (chess.isDraw()) return 0;
  if (depth === 0) return (chess.turn() === 'w' ? 1 : -1) * evaluate(chess);
  const moves = orderMoves(chess.moves({ verbose: true }));
  let best = -Infinity;
  for (const m of moves) {
    chess.move(m);
    const sc = -search(chess, depth - 1, -beta, -alpha, ply + 1);
    chess.undo();
    if (sc > best) best = sc;
    if (best > alpha) alpha = best;
    if (alpha >= beta) break;
  }
  return best;
}

/** Best move for the side to move. `noise` (centipawns) adds a little seeded variety so replays differ by seed. */
export function bestMove(fen, { depth = 3, rng = Math.random, noise = 12 } = {}) {
  const chess = new Chess(fen);
  const moves = orderMoves(chess.moves({ verbose: true }));
  if (!moves.length) return null;
  let best = null, bestScore = -Infinity;
  for (const m of moves) {
    chess.move(m);
    let sc = -search(chess, depth - 1, -Infinity, Infinity, 1);
    chess.undo();
    if (sc > 90000) { return toMove(m, true); } // mate in one: take it
    sc += (rng() - 0.5) * 2 * noise;
    if (m.promotion && m.promotion !== 'q') sc -= 500; // sensible players queen
    if (sc > bestScore) { bestScore = sc; best = m; }
  }
  return toMove(best, false);
}

/** Chaotic mover: random legal move, biased towards captures/checks/promotions so games reach interesting spots. */
export function chaosMove(fen, rng = Math.random) {
  const chess = new Chess(fen);
  const moves = chess.moves({ verbose: true });
  if (!moves.length) return null;
  const caps = moves.filter((m) => m.captured || m.promotion);
  const checks = moves.filter((m) => m.san.includes('+') || m.san.includes('#'));
  const roll = rng();
  let pool = moves;
  if (roll < 0.35 && caps.length) pool = caps;
  else if (roll < 0.5 && checks.length) pool = checks;
  const m = pool[Math.floor(rng() * pool.length)];
  return toMove(m, false);
}

function toMove(m, mate) {
  return { from: m.from, to: m.to, promotion: m.promotion, san: m.san, capture: !!m.captured, mate: mate || m.san.includes('#') };
}
