import { describe, expect, it } from 'vitest';
import { Rules, START_FEN } from '../src/core/rules';

const KIWIPETE = 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1';

/** Full-width perft through the public wrapper API (legalMovesFrom / move / undo). */
function wrapperPerft(rules: Rules, depth: number): number {
  if (depth === 0) return 1;
  let n = 0;
  for (const p of rules.pieces()) {
    if (p.side !== rules.turn()) continue;
    for (const m of rules.legalMovesFrom(p.square)) {
      const promos = m.isPromotion ? m.promotions! : [undefined];
      for (const promo of promos) {
        const res = rules.move(m.from, m.to, promo);
        expect(res).not.toBeNull();
        n += wrapperPerft(rules, depth - 1);
        rules.undo();
      }
    }
  }
  return n;
}

describe('perft: start position', () => {
  const expected = [20, 400, 8902, 197281];
  expected.forEach((nodes, i) => {
    it(`depth ${i + 1} = ${nodes}`, () => {
      expect(new Rules(START_FEN).perft(i + 1)).toBe(nodes);
    });
  });
});

describe('perft: Kiwipete', () => {
  const expected = [48, 2039, 97862];
  expected.forEach((nodes, i) => {
    it(`depth ${i + 1} = ${nodes}`, () => {
      expect(new Rules(KIWIPETE).perft(i + 1)).toBe(nodes);
    });
  });
});

describe('perft through the wrapper API (legalMovesFrom / move / undo)', () => {
  it('start position depth 1-3', () => {
    const r = new Rules();
    expect(wrapperPerft(r, 1)).toBe(20);
    expect(wrapperPerft(r, 2)).toBe(400);
    expect(wrapperPerft(r, 3)).toBe(8902);
    expect(r.fen()).toBe(START_FEN);
  });
  it('Kiwipete depth 1-2 (castling, en passant, promotions in the tree)', () => {
    const r = new Rules(KIWIPETE);
    expect(wrapperPerft(r, 1)).toBe(48);
    expect(wrapperPerft(r, 2)).toBe(2039);
    expect(r.fen()).toBe(KIWIPETE);
  });
});
