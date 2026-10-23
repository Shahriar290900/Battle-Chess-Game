import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';
import { Rules } from '../../src/core/rules';
import { GROUP_ORDER, LESSONS, isSolved, lessonsInGroup, playReference, successText } from '../../src/learn/lessons';

const SQUARE = /^[a-h][1-8]$/;

describe('lesson definitions', () => {
  it('covers the required topics', () => {
    const ids = LESSONS.map((l) => l.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const need of ['pawn-step', 'rook', 'knight', 'bishop', 'queen', 'king', 'capture', 'check', 'escape', 'castle-k', 'castle-q', 'en-passant', 'promotion', 'mate-back-rank', 'mate-two-rooks', 'stalemate', 'fork', 'pin', 'protect', 'open-centre']) {
      expect(ids, need).toContain(need);
    }
    for (const g of GROUP_ORDER) expect(lessonsInGroup(g).length).toBeGreaterThan(0);
  });

  for (const lesson of LESSONS) {
    describe(lesson.id, () => {
      it('has a legal FEN with moves for the side to move', () => {
        expect(() => new Chess(lesson.fen)).not.toThrow();
        const rules = new Rules(lesson.fen);
        expect(rules.allLegalMoves().length).toBeGreaterThan(0);
        expect(rules.gameOver()).toBeNull();
      });

      it('has well-formed text and squares', () => {
        for (const s of [...lesson.focus, ...lesson.goal]) expect(s).toMatch(SQUARE);
        expect(lesson.task.length).toBeGreaterThan(5);
        expect(lesson.intro.length).toBeGreaterThan(0);
        expect(lesson.illegalHint.length).toBeGreaterThan(5);
        expect(lesson.wrongHint.length).toBeGreaterThan(5);
        expect(lesson.tip.length).toBeGreaterThan(5);
        const rules = new Rules(lesson.fen);
        for (const s of lesson.focus) expect(rules.pieceAt(s), `focus ${s}`).not.toBeNull();
      });

      it('reference solutions are legal and solve the lesson', () => {
        expect(lesson.solutions.length).toBeGreaterThan(0);
        for (const sol of lesson.solutions) {
          const { res, rules } = playReference(lesson, sol);
          expect(res, `${sol.from}${sol.to} legal`).not.toBeNull();
          const before = new Rules(lesson.fen);
          expect(isSolved(lesson, res!, before), `${sol.from}${sol.to} solves`).toBe(true);
          expect(successText(lesson, res!).length).toBeGreaterThan(5);
          expect(rules.fen()).toBe(res!.fenAfter);
        }
      });

      it('has at least one legal move that does not solve it (unless every move is accepted)', () => {
        const rules = new Rules(lesson.fen);
        const wrong = rules.allLegalMoves().filter((m) => {
          const r = new Rules(lesson.fen);
          const res = r.move(m.from, m.to, m.promotion ?? (r.pieceAt(m.from)?.role === 'pawn' && (m.to[1] === '8' || m.to[1] === '1') ? 'queen' : undefined));
          return res && !isSolved(lesson, res, rules);
        });
        if (lesson.id === 'escape') expect(wrong.length).toBe(0);
        else expect(wrong.length).toBeGreaterThan(0);
      });
    });
  }

  it('lesson-specific outcomes', () => {
    const get = (id: string) => LESSONS.find((l) => l.id === id)!;
    expect(playReference(get('mate-back-rank')).res!.mate).toBe(true);
    expect(playReference(get('mate-two-rooks')).res!.mate).toBe(true);
    expect(playReference(get('stalemate')).res!.mate).toBe(true);
    expect(playReference(get('castle-k')).res!.isCastle).toBe(true);
    expect(playReference(get('castle-q')).res!.isCastle).toBe(true);
    expect(playReference(get('en-passant')).res!.isEnPassant).toBe(true);
    expect(playReference(get('promotion')).res!.promotion).toBe('queen');
    expect(playReference(get('check')).res!.check).toBe(true);
    // the stalemate trap really exists in the position and is explained
    const st = get('stalemate');
    const trap = new Rules(st.fen).move('d1', 'b3');
    expect(trap?.stalemate).toBe(true);
    expect(st.explainWrong!(trap!)?.demo).toBe(true);
    // escape check: every legal move is a real escape; there are king moves, blocks and a capture
    const esc = get('escape');
    const moves = new Rules(esc.fen).allLegalMoves();
    expect(moves.length).toBeGreaterThanOrEqual(4);
    const kinds = new Set(moves.map((m) => { const r = new Rules(esc.fen); const x = r.move(m.from, m.to)!; return x.role === 'king' ? 'move' : x.captured ? 'capture' : 'block'; }));
    expect(kinds).toEqual(new Set(['move', 'block', 'capture']));
  });

  it('lets a wrong-but-legal try be detected', () => {
    const l = LESSONS.find((x) => x.id === 'pawn-step')!;
    const r = new Rules(l.fen);
    const res = r.move('e2', 'e3')!;
    expect(isSolved(l, res, new Rules(l.fen))).toBe(false);
    expect(l.hints!['e2e3']).toBeTruthy();
  });
});
