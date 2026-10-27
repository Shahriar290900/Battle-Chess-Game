import { describe, expect, it } from 'vitest';
import { capturedFromFen } from '../../src/render/graveyard';

const count = (list: ReturnType<typeof capturedFromFen>, faction: string, role: string) => list.filter((c) => c.faction === faction && c.role === role).length;

describe('capturedFromFen', () => {
  it('is empty at the start position', () => {
    expect(capturedFromFen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')).toEqual([]);
  });
  it('lists missing pieces per side', () => {
    // White lost a knight and a pawn; Black lost the queen
    const c = capturedFromFen('rnb1kbnr/pppppppp/8/8/8/8/PPPPPPP1/RNBQKB1R w KQkq - 0 1');
    expect(count(c, 'emberhold', 'knight')).toBe(1);
    expect(count(c, 'emberhold', 'pawn')).toBe(1);
    expect(count(c, 'rime', 'queen')).toBe(1);
    expect(c).toHaveLength(3);
  });
  it('does not count promoted pawns as captured', () => {
    // White pawn promoted to a second queen (a-pawn gone, two white queens)
    const c = capturedFromFen('rnbqkbnr/pppppppp/8/8/8/8/1PPPPPPP/QNBQKBNR w KQkq - 0 1');
    expect(count(c, 'emberhold', 'pawn')).toBe(0);
    expect(count(c, 'emberhold', 'rook')).toBe(1); // the a1 rook is gone: it was captured
  });
});
