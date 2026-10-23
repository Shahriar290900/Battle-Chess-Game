// Scripted positions for the first-launch tutorial. SAN lines are replayed with chess.js so every FEN is
// guaranteed consistent; tests check each final move is legal and has the flags the tutorial claims.
import { Chess } from 'chess.js';

export interface ScriptPos { line: string[]; move: string }
export const TUTORIAL_POSITIONS: Record<'capture' | 'check' | 'mate', ScriptPos> = {
  // Ruy Lopez: the bishop captures the knight on c6.
  capture: { line: ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6'], move: 'Bxc6' },
  // 1.e4 e5 2.Nf3 d6: Bb5+ checks along the diagonal.
  check: { line: ['e4', 'e5', 'Nf3', 'd6'], move: 'Bb5+' },
  // Scholar's mate: Qxf7#.
  mate: { line: ['e4', 'e5', 'Bc4', 'Nc6', 'Qh5', 'Nf6'], move: 'Qxf7#' },
};

export function fenForLine(line: readonly string[]): string {
  const c = new Chess();
  for (const san of line) c.move(san);
  return c.fen();
}

export interface PosMove { fen: string; from: string; to: string; san: string }
export function scriptMove(p: ScriptPos): PosMove {
  const c = new Chess();
  for (const san of p.line) c.move(san);
  const fen = c.fen();
  const m = c.move(p.move);
  return { fen, from: m.from, to: m.to, san: m.san };
}
