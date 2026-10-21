// Rules wrapper around chess.js (architecture §5). The game never implements its own rules:
// every position change goes through here, and the resulting MoveResult is authoritative
// before any animation runs.
import { Chess, type Move } from 'chess.js';
import type { GameEvents, MoveResult, PieceSymbol, PromotionRole, Role, Side, Square } from '../contracts';
import { ROLE_SYMBOL, SYMBOL_ROLE } from '../contracts';

export type GameResult = GameEvents['game:over']['result'];
export type GameOverReason = GameEvents['game:over']['reason'];
export interface GameEnd { result: GameResult; reason: GameOverReason }

/** One legal destination for a piece (promotion variants are folded into `promotions`). */
export interface LegalMove {
  from: Square;
  to: Square;
  role: Role;
  captured?: Role;
  capturedSquare?: Square;
  isCastle: boolean;
  isEnPassant: boolean;
  isPromotion: boolean;
  /** Present for promotion moves: the legal promotion roles. */
  promotions?: PromotionRole[];
  san: string;
}

export const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

const CASTLE_ROOKS: Record<string, { from: Square; to: Square }> = {
  wk: { from: 'h1', to: 'f1' }, wq: { from: 'a1', to: 'd1' },
  bk: { from: 'h8', to: 'f8' }, bq: { from: 'a8', to: 'd8' },
};

const roleOf = (p: string): Role => SYMBOL_ROLE[p as PieceSymbol];

export class Rules {
  private chess: Chess;
  // chess.js history() replays the whole game on every call (tens of ms late in a game), so the
  // wrapper keeps its own incremental move list.
  private log: MoveResult[] = [];

  constructor(fen?: string) {
    this.chess = fen ? new Chess(fen) : new Chess();
  }

  reset(fen?: string): void {
    this.chess = fen ? new Chess(fen) : new Chess();
    this.log = [];
  }

  fen(): string { return this.chess.fen(); }
  turn(): Side { return this.chess.turn(); }
  pgn(): string { return this.chess.pgn(); }
  inCheck(): boolean { return this.chess.inCheck(); }

  /** Piece standing on a square, or null. */
  pieceAt(sq: Square): { side: Side; role: Role } | null {
    const p = this.chess.get(sq as never);
    return p ? { side: p.color, role: roleOf(p.type) } : null;
  }

  /** All pieces on the board (for tests and syncing). */
  pieces(): Array<{ square: Square; side: Side; role: Role }> {
    const out: Array<{ square: Square; side: Side; role: Role }> = [];
    for (const row of this.chess.board()) {
      for (const cell of row) if (cell) out.push({ square: cell.square, side: cell.color, role: roleOf(cell.type) });
    }
    return out;
  }

  kingSquare(side: Side): Square | null {
    for (const p of this.pieces()) if (p.role === 'king' && p.side === side) return p.square;
    return null;
  }

  /** Legal destinations of the piece on `sq` (empty if none / not the side to move). */
  legalMovesFrom(sq: Square): LegalMove[] {
    let verbose: Move[];
    try { verbose = this.chess.moves({ square: sq as never, verbose: true }); } catch { return []; }
    const byTo = new Map<Square, LegalMove>();
    for (const m of verbose) {
      let lm = byTo.get(m.to);
      if (!lm) {
        lm = {
          from: m.from, to: m.to, role: roleOf(m.piece),
          captured: m.captured ? roleOf(m.captured) : undefined,
          capturedSquare: m.captured ? (m.isEnPassant() ? m.to[0] + m.from[1] : m.to) : undefined,
          isCastle: m.isKingsideCastle() || m.isQueensideCastle(),
          isEnPassant: m.isEnPassant(),
          isPromotion: !!m.promotion,
          promotions: m.promotion ? [] : undefined,
          san: m.san,
        };
        byTo.set(m.to, lm);
      }
      if (m.promotion) lm.promotions!.push(roleOf(m.promotion) as PromotionRole);
    }
    return [...byTo.values()];
  }

  /** Every legal move for the side to move, one entry per promotion choice. */
  allLegalMoves(): Array<{ from: Square; to: Square; promotion?: PromotionRole }> {
    return this.chess.moves({ verbose: true }).map((m) => ({
      from: m.from, to: m.to, promotion: m.promotion ? (roleOf(m.promotion) as PromotionRole) : undefined,
    }));
  }

  isLegal(from: Square, to: Square, promotion?: PromotionRole): boolean {
    const mv = this.legalMovesFrom(from).find((m) => m.to === to);
    if (!mv) return false;
    if (mv.isPromotion) return !!promotion && mv.promotions!.includes(promotion);
    return true;
  }

  /** Apply a move. Returns null (position untouched) if it is illegal. */
  move(from: Square, to: Square, promotion?: PromotionRole): MoveResult | null {
    let m: Move;
    try {
      m = this.chess.move({ from, to, promotion: promotion ? ROLE_SYMBOL[promotion] : undefined });
    } catch {
      return null;
    }
    const res = this.toResult(m, true);
    this.log.push(res);
    return res;
  }

  undo(): MoveResult | null {
    const m = this.chess.undo();
    if (!m) return null;
    return this.log.pop() ?? this.toResult(m, false);
  }

  history(): MoveResult[] { return this.log.slice(); }

  /** Number of plies played. */
  plyCount(): number { return this.log.length; }

  /** SAN list, e.g. ["e4", "e5", "Nf3"]. */
  sanHistory(): string[] { return this.log.map((m) => m.san); }

  /** Roles captured BY each side, in capture order. */
  captured(): Record<Side, Role[]> {
    const out: Record<Side, Role[]> = { w: [], b: [] };
    for (const m of this.log) if (m.captured) out[m.side].push(m.captured);
    return out;
  }

  /** Replace the game with the given PGN (may carry SetUp/FEN headers). Throws on invalid PGN. */
  loadPgn(pgn: string): void {
    const next = new Chess();
    next.loadPgn(pgn);
    const verbose = next.history({ verbose: true });
    this.chess = next;
    this.log = verbose.map((m, i) => this.toResult(m, i === verbose.length - 1));
  }

  /** Terminal state of the current position (null while the game goes on). */
  gameOver(): GameEnd | null {
    const c = this.chess;
    if (c.isCheckmate()) return { result: c.turn() === 'w' ? '0-1' : '1-0', reason: 'checkmate' };
    if (c.isStalemate()) return { result: '1/2-1/2', reason: 'stalemate' };
    if (c.isInsufficientMaterial()) return { result: '1/2-1/2', reason: 'insufficient' };
    if (c.isThreefoldRepetition()) return { result: '1/2-1/2', reason: 'threefold' };
    if (c.isDrawByFiftyMoves()) return { result: '1/2-1/2', reason: 'fifty-move' };
    if (c.isDraw() || c.isGameOver()) return { result: '1/2-1/2', reason: 'draw' };
    return null;
  }

  /** Bulk-counted perft on a scratch copy (does not disturb the game). */
  perft(depth: number): number {
    const scratch = new Chess(this.chess.fen());
    const walk = (d: number): number => {
      const moves = scratch.moves();
      if (d === 1) return moves.length;
      let n = 0;
      for (const m of moves) { scratch.move(m); n += walk(d - 1); scratch.undo(); }
      return n;
    };
    return depth <= 0 ? 1 : walk(depth);
  }

  private toResult(m: Move, latest: boolean): MoveResult {
    const isCastle = m.isKingsideCastle() || m.isQueensideCastle();
    const rook = isCastle ? CASTLE_ROOKS[m.color + (m.isKingsideCastle() ? 'k' : 'q')] : undefined;
    const isEnPassant = m.isEnPassant();
    // "latest" results inspect the live position; older history entries rely on the SAN suffix.
    // Undo results describe the move just taken back, so they use SAN only as well.
    const mate = latest ? this.chess.isCheckmate() : m.san.endsWith('#');
    const check = latest ? this.chess.inCheck() : m.san.includes('+') || m.san.endsWith('#');
    const stalemate = latest ? this.chess.isStalemate() : false;
    const draw = latest ? this.chess.isDraw() : false;
    return {
      from: m.from, to: m.to, san: m.san, side: m.color, role: roleOf(m.piece),
      captured: m.captured ? roleOf(m.captured) : undefined,
      capturedSquare: m.captured ? (isEnPassant ? m.to[0] + m.from[1] : m.to) : undefined,
      flags: m.flags, isCastle, rookFrom: rook?.from, rookTo: rook?.to, isEnPassant,
      promotion: m.promotion ? (roleOf(m.promotion) as PromotionRole) : undefined,
      check, mate, stalemate, draw, fenAfter: m.after,
    };
  }
}

/** FEN piece-placement field → map of square → piece (shared by board syncing and tests). */
export function parsePlacement(fen: string): Map<Square, { side: Side; role: Role }> {
  const out = new Map<Square, { side: Side; role: Role }>();
  const rows = fen.split(' ')[0].split('/');
  for (let r = 0; r < 8; r++) {
    let file = 0;
    for (const ch of rows[r]) {
      if (ch >= '1' && ch <= '8') { file += Number(ch); continue; }
      const side: Side = ch === ch.toUpperCase() ? 'w' : 'b';
      out.set('abcdefgh'[file] + String(8 - r), { side, role: SYMBOL_ROLE[ch.toLowerCase() as PieceSymbol] });
      file++;
    }
  }
  return out;
}
