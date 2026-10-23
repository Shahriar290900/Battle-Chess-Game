import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';
import { START_FEN } from '../../src/core/rules';
import { suggestMove } from '../../src/learn/hints';

describe('beginner hints', () => {
  it('always suggests a legal move', () => {
    for (const fen of [START_FEN, 'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3', '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1']) {
      const s = suggestMove(fen)!;
      expect(new Chess(fen).moves({ verbose: true }).some((m) => m.from === s.from && m.to === s.to)).toBe(true);
      expect(s.why.length).toBeGreaterThan(5);
    }
  });
  it('finds mate in one and free material', () => {
    expect(suggestMove('6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1')!.san).toBe('Rd8#');
    const free = suggestMove('4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1')!;
    expect(free.san).toBe('Rxd5');
  });
  it('returns null when there are no moves', () => {
    expect(suggestMove('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1')).toBeNull();
  });
});
