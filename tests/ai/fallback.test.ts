import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';
import { fallbackMove } from '../../src/core/ai/fallback';
import type { AiLevel } from '../../src/contracts';

const LEVELS: AiLevel[] = ['easy', 'medium', 'hard', 'master'];
const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const MIDDLE = 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4';

describe('fallback engine', () => {
  for (const level of LEVELS) {
    it(`returns legal moves at ${level}`, () => {
      for (const fen of [START, MIDDLE]) {
        const m = fallbackMove(fen, level);
        const g = new Chess(fen);
        expect(() => g.move({ from: m.from, to: m.to })).not.toThrow();
      }
    });
  }

  it('finds mate in 1 (back rank)', () => {
    const fen = '6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1';
    for (const level of ['medium', 'hard', 'master'] as AiLevel[]) {
      const m = fallbackMove(fen, level);
      expect(m).toMatchObject({ from: 'a1', to: 'a8' });
    }
  });

  it('finds mate in 1 as black', () => {
    const fen = 'r5k1/8/8/8/8/8/5PPP/6K1 b - - 0 1';
    expect(fallbackMove(fen, 'hard')).toMatchObject({ from: 'a8', to: 'a1' });
  });

  it('handles promotion', () => {
    const fen = '8/P6k/8/8/8/8/8/K7 w - - 0 1';
    const m = fallbackMove(fen, 'hard');
    expect(m.from).toBe('a7');
    expect(m.to).toBe('a8');
    expect(['queen', 'rook', 'bishop', 'knight']).toContain(m.promotion);
    const letter = { queen: 'q', rook: 'r', bishop: 'b', knight: 'n' }[m.promotion!];
    expect(() => new Chess(fen).move({ from: m.from, to: m.to, promotion: letter })).not.toThrow();
  });

  it('is fast enough on a middlegame position', () => {
    const t = Date.now();
    fallbackMove(MIDDLE, 'master');
    expect(Date.now() - t).toBeLessThan(4000);
  });
});
