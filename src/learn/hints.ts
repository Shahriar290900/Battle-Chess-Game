// Beginner move hints: a tiny two-ply search (my move, their best reply) over material with a few positional
// bonuses, so the coach can say "take the free piece", "give check", "develop a knight", "castle". Pure chess.js.
import { Chess, type Move } from 'chess.js';
import type { PromotionRole, Role, Square } from '../contracts';
import { SYMBOL_ROLE } from '../contracts';

export interface Suggestion { from: Square; to: Square; promotion?: PromotionRole; san: string; role: Role; why: string }

const V: Record<string, number> = { p: 1, n: 3, b: 3.2, r: 5, q: 9, k: 0 };
const CENTRE = new Set(['d4', 'e4', 'd5', 'e5']);
const NAME: Record<string, string> = { p: 'pawn', n: 'knight', b: 'bishop', r: 'rook', q: 'queen', k: 'king' };

function material(c: Chess, me: 'w' | 'b'): number {
  let s = 0;
  for (const row of c.board()) for (const p of row) if (p) s += (p.color === me ? 1 : -1) * V[p.type];
  return s;
}

function score(c: Chess, me: 'w' | 'b', last: Move): number {
  if (c.isCheckmate()) return c.turn() === me ? -1000 : 1000;
  if (c.isStalemate() || c.isDraw()) return -5; // a beginner should avoid drawing a won game
  let s = material(c, me);
  if (last.color === me) {
    if (CENTRE.has(last.to) && (last.piece === 'p' || last.piece === 'n')) s += 0.15;
    if ((last.piece === 'n' || last.piece === 'b') && last.from[1] === (me === 'w' ? '1' : '8')) s += 0.2;
    if (last.isKingsideCastle() || last.isQueensideCastle()) s += 0.4;
    if (last.san.includes('+')) s += 0.15;
    if (last.piece === 'q' && last.from[1] === (me === 'w' ? '1' : '8') && !last.captured) s -= 0.1; // early queen sorties
  }
  return s;
}

export function suggestMove(fen: string): Suggestion | null {
  const c = new Chess(fen);
  const me = c.turn();
  const moves = c.moves({ verbose: true });
  if (!moves.length) return null;
  let best: { m: Move; v: number } | null = null;
  for (const m of moves) {
    c.move(m);
    let v: number;
    const replies = c.moves({ verbose: true });
    if (!replies.length || c.isCheckmate()) v = score(c, me, m);
    else {
      v = Infinity; // opponent picks the reply that is worst for me
      for (const r of replies) { c.move(r); v = Math.min(v, score(c, me, m)); c.undo(); }
    }
    c.undo();
    if (!best || v > best.v + 1e-9) best = { m, v };
  }
  const m = best!.m;
  const role = SYMBOL_ROLE[m.piece];
  let why: string;
  if (m.san.endsWith('#')) why = 'Checkmate! This move wins the game.';
  else if (m.isKingsideCastle() || m.isQueensideCastle()) why = 'Castle: tuck your king away and bring a rook into play.';
  else if (m.captured) why = `Win material: capture the ${NAME[m.captured]}.`;
  else if (m.promotion) why = 'Promote your pawn into a queen.';
  else if (m.san.includes('+')) why = 'Give check and keep the initiative.';
  else if ((m.piece === 'n' || m.piece === 'b') && m.from[1] === (me === 'w' ? '1' : '8')) why = `Develop your ${NAME[m.piece]} toward the centre.`;
  else if (CENTRE.has(m.to)) why = 'Take a share of the centre.';
  else why = 'A safe, useful move that improves your position.';
  return { from: m.from, to: m.to, promotion: m.promotion ? (SYMBOL_ROLE[m.promotion] as PromotionRole) : undefined, san: m.san, role, why };
}
