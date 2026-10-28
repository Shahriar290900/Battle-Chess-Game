import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';
import { fallbackMove, fallbackProfile } from '../../src/core/ai/fallback';
import { mulberry32 } from '../../src/core/ai/strength';
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
    for (const level of [1800, 2000, 2600] as number[]) {
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
    const m = fallbackMove(fen, 2600);
    expect(m.from).toBe('a7');
    expect(m.to).toBe('a8');
    expect(['queen', 'rook', 'bishop', 'knight']).toContain(m.promotion);
    const letter = { queen: 'q', rook: 'r', bishop: 'b', knight: 'n' }[m.promotion!];
    expect(() => new Chess(fen).move({ from: m.from, to: m.to, promotion: letter })).not.toThrow();
  });

  it('accepts Elo numbers and legacy levels alike', () => {
    for (const elo of [400, 1350, 3000]) expect(() => new Chess(MIDDLE).move({ ...fallbackMove(MIDDLE, elo), promotion: undefined })).not.toThrow();
    expect(fallbackProfile('medium').elo).toBe(1200);
  });

  it('profile gets stronger with Elo', () => {
    let prev = fallbackProfile(400);
    for (let e = 450; e <= 3000; e += 50) {
      const p = fallbackProfile(e);
      expect(p.depth).toBeGreaterThanOrEqual(prev.depth);
      expect(p.randomMoveProb).toBeLessThanOrEqual(prev.randomMoveProb);
      expect(p.temperatureCp).toBeLessThanOrEqual(prev.temperatureCp);
      prev = p;
    }
  });

  it('is fast enough on a middlegame position', () => {
    const t = Date.now();
    fallbackMove(MIDDLE, 'master');
    expect(Date.now() - t).toBeLessThan(4000);
  });
});

describe('fallback strength ordering (statistical, seeded)', () => {
  // A hanging queen: how often does each Elo take it? (Beginners miss free material, strong play never does.)
  const HANGING: Array<[string, string]> = [
    ['rnb1kbnr/ppp2ppp/8/3qp3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1', 'e4d5'],
    ['4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1', 'd1d5'],
    ['4k3/8/8/8/3q4/8/8/3QK3 w - - 0 1', 'd1d4'],
  ];
  const hitRate = (elo: number, trials: number) => {
    const rng = mulberry32(elo);
    let hit = 0, n = 0;
    for (let t = 0; t < trials; t++) {
      for (const [fen, want] of HANGING) {
        const m = fallbackMove(fen, elo, { rng, maxDepth: 1 });
        if (m.from + m.to === want) hit++;
        n++;
      }
    }
    return hit / n;
  };
  it('the chance of taking a hanging queen rises with Elo', () => {
    const rates = [400, 1000, 2400].map((e) => hitRate(e, 14));
    for (let i = 1; i < rates.length; i++) expect(rates[i]).toBeGreaterThanOrEqual(rates[i - 1] - 0.05);
    expect(rates[0]).toBeLessThan(0.92);
    expect(rates[2]).toBeGreaterThan(0.95);
    expect(rates[2] - rates[0]).toBeGreaterThan(0.1);
  }, 30000);

  /** Material-adjudicated quick game at depth 1; returns white's score. */
  it('a 1600 beats a 400 more often than not over quick games', () => {
    const val: Record<string, number> = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
    const game = (whiteElo: number, blackElo: number, seed: number) => {
      const g = new Chess();
      const rng = mulberry32(seed);
      while (!g.isGameOver() && g.history().length < 50) {
        const m = fallbackMove(g.fen(), g.turn() === 'w' ? whiteElo : blackElo, { rng, maxDepth: 1 });
        const letter = m.promotion ? { queen: 'q', rook: 'r', bishop: 'b', knight: 'n' }[m.promotion] : undefined;
        g.move({ from: m.from, to: m.to, promotion: letter });
      }
      if (g.isCheckmate()) return g.turn() === 'w' ? 0 : 1;
      let diff = 0;
      for (const row of g.board()) for (const p of row) if (p) diff += (p.color === 'w' ? 1 : -1) * val[p.type];
      return diff >= 2 ? 1 : diff <= -2 ? 0 : 0.5;
    };
    let hi = 0;
    for (let i = 0; i < 2; i++) { hi += game(1600, 400, 21 + i); hi += 1 - game(400, 1600, 121 + i); }
    expect(hi / 4).toBeGreaterThan(0.5);
  }, 45000);
});
