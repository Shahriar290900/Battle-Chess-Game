// Headless GamePresenter: no rendering, instant "sequences". It tracks its own piece placement by
// applying each MoveResult (en passant square, castling rook, promotion) and, whenever the controller
// calls syncToFen, compares that placement with the authoritative FEN. Any mismatch is recorded in
// `desyncs`, which makes replay tests a check of MoveResult correctness as well as of the controller.
import type { MoveResult, PromotionRole, Role, Side, Square } from '../contracts';
import { parsePlacement, START_FEN } from './rules';
import type { GamePresenter } from './presenter';

type Cell = { side: Side; role: Role };

export interface HeadlessPresenter extends GamePresenter {
  readonly calls: string[];
  readonly desyncs: string[];
  /** Role returned by choosePromotion (null = dismiss). */
  promotionChoice: PromotionRole | null;
  placement(): Map<Square, Cell>;
}

export function createHeadlessPresenter(startFen = START_FEN): HeadlessPresenter {
  let pieces = parsePlacement(startFen);
  const calls: string[] = [];
  const desyncs: string[] = [];

  const apply = (m: MoveResult) => {
    const mover = pieces.get(m.from);
    if (!mover) { desyncs.push(`no piece on ${m.from} for ${m.san}`); return; }
    if (m.captured) {
      const sq = m.capturedSquare ?? m.to;
      const victim = pieces.get(sq);
      if (!victim || victim.role !== m.captured) desyncs.push(`${m.san}: expected ${m.captured} on ${sq}`);
      pieces.delete(sq);
    }
    pieces.delete(m.from);
    pieces.set(m.to, mover);
    if (m.isCastle) {
      const rook = m.rookFrom ? pieces.get(m.rookFrom) : undefined;
      if (!rook || rook.role !== 'rook' || !m.rookFrom || !m.rookTo) desyncs.push(`${m.san}: bad castle rook`);
      else { pieces.delete(m.rookFrom); pieces.set(m.rookTo, rook); }
    }
  };

  const api: HeadlessPresenter = {
    calls, desyncs, promotionChoice: 'queen',
    running: false,
    placement: () => pieces,
    reset(fen) {
      pieces = parsePlacement(fen);
      calls.length = 0;
      desyncs.length = 0;
    },
    syncToFen(fen) {
      calls.push('sync');
      const want = parsePlacement(fen);
      const same = want.size === pieces.size && [...want].every(([sq, p]) => {
        const have = pieces.get(sq);
        return have && have.side === p.side && have.role === p.role;
      });
      if (!same) desyncs.push(`placement mismatch against ${fen}`);
      pieces = want;
    },
    async playMove(m) {
      calls.push(m.captured ? 'capture' : m.isCastle ? 'castle' : 'move');
      apply(m);
    },
    async playPromotion(m, role) {
      calls.push('promote');
      const p = pieces.get(m.to);
      if (!p || p.role !== 'pawn') desyncs.push(`${m.san}: promotion without pawn on ${m.to}`);
      else pieces.set(m.to, { side: p.side, role });
    },
    async playCheck() { calls.push('check'); },
    async playCheckmate() { calls.push('checkmate'); },
    async playStalemate() { calls.push('stalemate'); },
    skip() { calls.push('skip'); },
    async seatCamera(side) { calls.push(`seat:${side}`); },
    markCheck(sq) { calls.push(`markCheck:${sq ?? 'null'}`); },
    async choosePromotion() { calls.push('choosePromotion'); return api.promotionChoice; },
  };
  return api;
}
